"""
Redis-based Memory Backend for Grokputer.
Provides Redis-based storage for agent memories with connection handling and graceful failure.
"""

import json
import logging
from typing import Any, Dict, List, Optional

import redis

from ..interfaces import MemoryBackend, MemoryConfig

logger = logging.getLogger(__name__)


class RedisMemoryBackend(MemoryBackend):
    """Redis-based memory backend with connection handling and graceful failure."""

    def __init__(self, config: MemoryConfig):
        self.config = config
        self.redis_client: Optional[redis.Redis] = None
        self._connect()

    def _connect(self) -> None:
        """Establish Redis connection with error handling."""
        try:
            # Parse Redis URL from config or use defaults
            redis_url = getattr(self.config, "redis_url", "redis://localhost:6380/0")

            self.redis_client = redis.from_url(redis_url, decode_responses=True)

            # Test connection
            self.redis_client.ping()
            logger.info("Redis connection established successfully")

        except redis.ConnectionError as e:
            logger.warning(f"Failed to connect to Redis: {e}. Falling back to no-op mode.")
            self.redis_client = None
        except Exception as e:
            logger.error(f"Unexpected error connecting to Redis: {e}")
            self.redis_client = None

    def _ensure_connection(self) -> bool:
        """Ensure Redis connection is active, attempt reconnect if needed."""
        if self.redis_client is None:
            return False

        try:
            self.redis_client.ping()
            return True
        except redis.ConnectionError:
            logger.warning("Redis connection lost, attempting reconnect...")
            self._connect()
            return self.redis_client is not None

    def _serialize_episode(self, episode_data: Dict[str, Any]) -> str:
        """Serialize episode data to JSON string."""
        try:
            return json.dumps(episode_data, default=str)
        except (TypeError, ValueError) as e:
            logger.error(f"Failed to serialize episode data: {e}")
            return json.dumps({"error": "serialization_failed", "original_data": str(episode_data)})

    def _deserialize_episode(self, episode_json: str) -> Optional[Dict[str, Any]]:
        """Deserialize episode data from JSON string."""
        try:
            return json.loads(episode_json)
        except (json.JSONDecodeError, TypeError) as e:
            logger.error(f"Failed to deserialize episode data: {e}")
            return None

    def store_episode(self, agent_id: str, episode_data: Dict[str, Any]) -> None:
        """Store an episode for an agent in Redis."""
        if not self._ensure_connection():
            logger.warning("Redis unavailable, skipping episode storage")
            return

        try:
            episode_key = f"episode:{agent_id}:{self.redis_client.incr(f'counter:{agent_id}')}"
            episode_json = self._serialize_episode(episode_data)

            # Store episode with expiration (optional, based on config)
            expire_time = getattr(self.config, "episode_ttl", None)
            if expire_time:
                self.redis_client.setex(episode_key, expire_time, episode_json)
            else:
                self.redis_client.set(episode_key, episode_json)

            # Maintain a sorted set for ordering by timestamp
            timestamp = episode_data.get("timestamp", self.redis_client.time()[0])
            self.redis_client.zadd(f"episodes:{agent_id}", {episode_key: timestamp})

            # Trim to max episodes
            max_episodes = getattr(self.config, "max_episodes", 1000)
            self.redis_client.zremrangebyrank(f"episodes:{agent_id}", 0, -max_episodes - 1)

            logger.debug(f"Stored episode for agent {agent_id}")

        except Exception as e:
            logger.error(f"Failed to store episode for {agent_id}: {e}")

    def retrieve_context(self, agent_id: str, query: str = None, top_k: int = 5) -> List[Dict[str, Any]]:
        """Retrieve context for an agent from Redis."""
        if not self._ensure_connection():
            logger.warning("Redis unavailable, returning empty context")
            return []

        try:
            # Get the most recent episode keys
            episode_keys = self.redis_client.zrevrange(f"episodes:{agent_id}", 0, top_k - 1)

            episodes = []
            for key in episode_keys:
                episode_json = self.redis_client.get(key)
                if episode_json:
                    episode = self._deserialize_episode(episode_json)
                    if episode:
                        episodes.append(episode)

            logger.debug(f"Retrieved {len(episodes)} episodes for agent {agent_id}")
            return episodes

        except Exception as e:
            logger.error(f"Failed to retrieve context for {agent_id}: {e}")
            return []

    def consolidate(self, agent_id: str) -> Dict[str, Any]:
        """Consolidate memory for an agent in Redis."""
        if not self._ensure_connection():
            logger.warning("Redis unavailable, returning no_data status")
            return {"status": "no_data"}

        try:
            episodes = self.retrieve_context(agent_id, top_k=getattr(self.config, "consolidation_threshold", 100))

            if not episodes:
                return {"status": "no_data"}

            # Simple consolidation: count patterns
            tool_usage = {}
            successful_tasks = 0
            total_tasks = len(episodes)

            for episode in episodes:
                if episode.get("success", False):
                    successful_tasks += 1
                tool = episode.get("tool_used")
                if tool:
                    tool_usage[tool] = tool_usage.get(tool, 0) + 1

            consolidated = {
                "agent_id": agent_id,
                "total_episodes": total_tasks,
                "success_rate": successful_tasks / total_tasks if total_tasks > 0 else 0,
                "tool_usage": tool_usage,
                "last_consolidated": episodes[0] if episodes else None,
            }

            # Store consolidated memory
            consolidated_key = f"consolidated:{agent_id}"
            consolidated_json = self._serialize_episode(consolidated)
            self.redis_client.set(consolidated_key, consolidated_json)

            logger.debug(f"Consolidated memory for agent {agent_id}")
            return consolidated

        except Exception as e:
            logger.error(f"Failed to consolidate memory for {agent_id}: {e}")
            return {"status": "error", "error": str(e)}
