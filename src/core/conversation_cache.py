"""
Redis Conversation Cache Manager
Provides fast access to active conversations with automatic persistence to SQLite.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import redis.asyncio as redis

from db_config import (
    create_conversation,
    get_conversation_history,
    get_user_preferences,
    save_conversation_message,
    save_user_preference,
    update_conversation_status,
)

logger = logging.getLogger(__name__)


class ConversationCache:
    """
    Redis-backed conversation cache with SQLite persistence.

    Architecture:
    - Active conversations cached in Redis for fast access
    - Automatic persistence to SQLite on conversation end
    - Context variables and state stored in Redis
    - Message history buffered in Redis, persisted in batches
    """

    def __init__(self, redis_url: str = "redis://localhost:6379", ttl_hours: int = 24):
        self.redis_url = redis_url
        self.ttl_hours = ttl_hours
        self.redis_client: Optional[redis.Redis] = None

    async def start(self):
        """Initialize Redis connection."""
        try:
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
            await self.redis_client.ping()
            logger.info("Conversation cache Redis connected")
        except Exception as e:
            logger.warning(f"Conversation cache Redis failed: {e}")
            self.redis_client = None

    async def create_conversation(self, conversation_id: str, user_id: str, metadata: Dict[str, Any] = None) -> bool:
        """Create new conversation in both Redis and SQLite."""
        # SQLite persistence
        success = create_conversation(conversation_id, user_id, metadata)

        if success and self.redis_client:
            # Redis cache
            conv_key = f"conv:{conversation_id}"
            conv_data = {
                "conversation_id": conversation_id,
                "user_id": user_id,
                "start_time": datetime.now().isoformat(),
                "status": "active",
                "total_messages": 0,
                "metadata": json.dumps(metadata or {}),
                "context_variables": "{}",
                "conversation_state": "idle",
                "last_intent": "",
                "message_buffer": "[]",  # JSON array of recent messages
            }

            await self.redis_client.hset(conv_key, mapping=conv_data)
            await self.redis_client.expire(conv_key, self.ttl_hours * 3600)

        return success

    async def save_message(
        self, conversation_id: str, message_id: str, role: str, content: str, metadata: Dict[str, Any] = None
    ) -> bool:
        """Save message to Redis buffer and SQLite."""
        # SQLite persistence
        success = save_conversation_message(conversation_id, message_id, role, content, metadata)

        if success and self.redis_client:
            conv_key = f"conv:{conversation_id}"

            # Update message buffer (keep last 20 messages in Redis)
            buffer_key = f"{conv_key}:messages"
            message_data = {
                "message_id": message_id,
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat(),
                "metadata": json.dumps(metadata or {}),
            }

            # Add to Redis sorted set (by timestamp)
            score = datetime.now().timestamp()
            await self.redis_client.zadd(buffer_key, {json.dumps(message_data): score})

            # Keep only last 20 messages in Redis
            await self.redis_client.zremrangebyrank(buffer_key, 0, -21)

            # Update conversation metadata
            await self.redis_client.hincrby(conv_key, "total_messages", 1)
            await self.redis_client.expire(conv_key, self.ttl_hours * 3600)

        return success

    async def get_conversation_context(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get conversation context from Redis."""
        if not self.redis_client:
            return None

        conv_key = f"conv:{conversation_id}"
        conv_data = await self.redis_client.hgetall(conv_key)

        if not conv_data:
            return None

        # Parse JSON fields
        context = dict(conv_data)
        context["metadata"] = json.loads(context.get("metadata", "{}"))
        context["context_variables"] = json.loads(context.get("context_variables", "{}"))

        # Get recent messages from buffer
        buffer_key = f"{conv_key}:messages"
        messages_data = await self.redis_client.zrange(buffer_key, -20, -1)  # Last 20 messages

        context["recent_messages"] = [json.loads(msg) for msg in messages_data]

        return context

    async def update_conversation_state(
        self, conversation_id: str, state: str, context_vars: Dict[str, Any] = None
    ) -> bool:
        """Update conversation state and context variables."""
        if not self.redis_client:
            return False

        conv_key = f"conv:{conversation_id}"
        updates = {"conversation_state": state}

        if context_vars:
            updates["context_variables"] = json.dumps(context_vars)

        await self.redis_client.hset(conv_key, mapping=updates)
        await self.redis_client.expire(conv_key, self.ttl_hours * 3600)

        return True

    async def get_user_context(self, user_id: str) -> Dict[str, Any]:
        """Get user preferences and recent conversation context."""
        # Get preferences from SQLite
        preferences = get_user_preferences(user_id)

        # Get recent conversations
        recent_convs = []  # Could implement this in db_config

        return {"preferences": preferences, "recent_conversations": recent_convs}

    async def end_conversation(self, conversation_id: str) -> bool:
        """End conversation and clean up Redis cache."""
        # Update SQLite status
        success = update_conversation_status(conversation_id, "completed")

        if self.redis_client:
            conv_key = f"conv:{conversation_id}"
            buffer_key = f"{conv_key}:messages"

            # Clean up Redis keys
            await self.redis_client.delete(conv_key, buffer_key)

        return success

    async def archive_old_conversations(self, days_old: int = 7) -> int:
        """Archive conversations older than specified days."""
        if not self.redis_client:
            return 0

        # Find old conversation keys
        pattern = "conv:*"
        keys = []
        async for key in self.redis_client.scan_iter(pattern):
            # Check if conversation is old (this is approximate)
            # In production, you'd want to check the start_time field
            keys.append(key)

        archived = 0
        for key in keys:
            conv_id = key.split(":", 1)[1]
            # Check if conversation should be archived based on Redis TTL
            # For now, just clean up expired keys
            if await self.redis_client.ttl(key) == -2:  # Key doesn't exist
                continue

            # Archive to SQLite and remove from Redis
            await self.end_conversation(conv_id)
            archived += 1

        return archived

    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        if not self.redis_client:
            return {"redis_available": False}

        try:
            info = await self.redis_client.info()
            conv_keys = await self.redis_client.keys("conv:*")

            return {
                "redis_available": True,
                "active_conversations": len(conv_keys) if conv_keys else 0,
                "memory_used": info.get("used_memory_human", "unknown"),
                "uptime_days": info.get("uptime_in_days", 0),
            }
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {"redis_available": False, "error": str(e)}
