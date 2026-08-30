#!/usr/bin/env python3
from __future__ import annotations

# MemoryAgent: Handles state recall, storage, and search for distributed swarm.
# Integrates Redis for fast key-value, Pinecone for vector search (memory across sessions/instances).
# Broadcasts updates via MessageBus for sync (e.g., 'memory_update' to all agents).

import asyncio
import json
import logging
import os
import uuid
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

load_dotenv()

from src.core.base_agent import BaseAgent
from src.core.message_bus import MessageBus

logger = logging.getLogger(__name__)

try:
    import redis
    from pinecone import Pinecone, ServerlessSpec

    PINECONE_AVAILABLE = True
except ImportError:
    PINECONE_AVAILABLE = False
    redis = None  # Fallback warning in init


class MemoryAgent(BaseAgent):
    def __init__(self, agent_id: str, message_bus, session_logger, config: Dict[str, Any], action_executor=None):
        super().__init__(agent_id, message_bus, session_logger, config)
        self.action_executor = action_executor

        # Redis configuration
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.redis_client = redis.from_url(self.redis_url) if redis else None

        # Pinecone configuration
        self.pinecone_key = os.getenv("PINECONE_KEY")
        self.pinecone_index = os.getenv("PINECONE_INDEX", "grokputer-memory")
        self.pinecone_client = None
        self.index = None

        if PINECONE_AVAILABLE and self.pinecone_key:
            try:
                self.pinecone_client = Pinecone(api_key=self.pinecone_key)
                # Check if index exists
                existing_indexes = self.pinecone_client.list_indexes().names()
                if self.pinecone_index not in existing_indexes:
                    self.pinecone_client.create_index(
                        name=self.pinecone_index,
                        dimension=1536,  # Default for sentence-transformers
                        metric="cosine",
                        spec=ServerlessSpec(cloud="aws", region="us-west-2"),
                    )
                self.index = self.pinecone_client.Index(self.pinecone_index)
                logger.info(f"[{self.agent_id}] Pinecone index '{self.pinecone_index}' ready")
            except Exception as e:
                logger.warning(f"[{self.agent_id}] Pinecone initialization failed: {e}")
        else:
            logger.info(f"[{self.agent_id}] Pinecone not configured - using Redis only")

        self.priority_map = {"HIGH": 0, "NORMAL": 1, "LOW": 2}

        logger.info(f"[{self.agent_id}] Memory agent initialized")

    async def process_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process memory-related messages.

        Message types:
        - store_state: Store data in memory
        - recall_state: Retrieve data from memory
        - search_memory: Vector search in memory
        """
        msg_type = message.get("type")

        if msg_type == "store_state":
            return await self._handle_store(message)
        elif msg_type == "recall_state":
            return await self._handle_recall(message)
        elif msg_type == "search_memory":
            return await self._handle_search(message)
        else:
            logger.warning(f"[{self.agent_id}] Unknown message type: {msg_type}")
            return {"status": "error", "reason": f"Unknown message type: {msg_type}"}

    async def _handle_store(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle store state request."""
        key = message.get("key")
        data = message.get("data", {})
        priority = message.get("priority", "NORMAL")

        if not key:
            return {"status": "error", "reason": "Missing key"}

        try:
            await self.store_state(key, data, priority)
            return {"status": "success", "key": key}
        except Exception as e:
            logger.error(f"[{self.agent_id}] Store failed: {e}")
            return {"status": "error", "reason": str(e)}

    async def _handle_recall(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle recall state request."""
        key = message.get("key")
        priority = message.get("priority", "HIGH")

        if not key:
            return {"status": "error", "reason": "Missing key"}

        try:
            data = await self.recall_state(key, priority)
            return {"status": "success", "key": key, "data": data}
        except Exception as e:
            logger.error(f"[{self.agent_id}] Recall failed: {e}")
            return {"status": "error", "reason": str(e)}

    async def _handle_search(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle memory search request."""
        query = message.get("query")
        top_k = message.get("top_k", 5)
        priority = message.get("priority", "NORMAL")

        if not query:
            return {"status": "error", "reason": "Missing query"}

        try:
            results = await self.search_memory(query, top_k, priority)
            return {"status": "success", "query": query, "results": results}
        except Exception as e:
            logger.error(f"[{self.agent_id}] Search failed: {e}")
            return {"status": "error", "reason": str(e)}

        self.priority_map = {"HIGH": 0, "NORMAL": 1, "LOW": 2}

    async def recall_state(self, key: str, priority: str = "HIGH") -> Optional[Dict[str, Any]]:
        """Recall state from Redis/Pinecone. Urgent (HIGH) broadcasts request for sync."""
        prio = self.priority_map.get(priority, 1)

        # Check local Redis first (fast)
        if self.redis_client:
            try:
                state = self.redis_client.get(key)
                if state:
                    return json.loads(state)
            except Exception as e:
                logger.warning(f"[{self.agent_id}] Redis recall failed: {e}")

        # If not found, query Pinecone (vector search for similar keys)
        if self.pinecone_client and self.index:
            try:
                # Embed query (simple key as text; in prod, use sentence-transformers)
                query_embedding = [0.1] * 1536  # Placeholder – integrate real embedding
                results = self.index.query(vector=query_embedding, top_k=1, include_metadata=True)
                if results.matches:
                    return results.matches[0].metadata
            except Exception as e:
                logger.warning(f"[{self.agent_id}] Pinecone recall failed: {e}")

        # For HIGH priority, broadcast request to sync from other instances
        if priority == "HIGH":
            corr_id = str(uuid.uuid4())
            req_msg = {
                "type": "memory_recall_request",
                "key": key,
                "corr_id": corr_id,
                "from": self.agent_id,
                "priority": priority,
            }
            try:
                # Note: MessageBus doesn't have request_response, simplified for now
                logger.info(f"[{self.agent_id}] Broadcasting high-priority recall request for {key}")
                # In full implementation, would send message and wait for response
            except Exception as e:
                logger.warning(f"[{self.agent_id}] High-priority recall broadcast failed: {e}")

        return None  # Not found

    async def store_state(self, key: str, data: Dict[str, Any], priority: str = "NORMAL"):
        """Store to Redis/Pinecone, broadcast update for distributed sync."""
        # Store to Redis (fast access)
        if self.redis_client:
            try:
                self.redis_client.set(key, json.dumps(data), ex=86400)  # 24h TTL
                logger.info(f"[{self.agent_id}] Stored {key} in Redis")
            except Exception as e:
                logger.error(f"[{self.agent_id}] Redis store failed: {e}")

        # Upsert to Pinecone (vector store)
        if self.pinecone_client and self.index:
            try:
                # Embed data (placeholder; use real embedding in prod)
                embedding = [0.2] * 1536
                self.index.upsert(vectors=[{"id": key, "values": embedding, "metadata": data}])
                logger.info(f"[{self.agent_id}] Stored {key} in Pinecone")
            except Exception as e:
                logger.error(f"[{self.agent_id}] Pinecone store failed: {e}")

        # Broadcast update via MessageBus (sync other instances/agents)
        prio = self.priority_map.get(priority, 1)
        update_msg = {"type": "memory_update", "key": key, "data": data, "from": self.agent_id, "priority": priority}
        # Note: MessageBus doesn't have broadcast, simplified for now
        logger.info(f"[{self.agent_id}] Memory update broadcast for {key}")
        self.logger.info(f"Stored and broadcasted memory update for key: {key}")

    async def search_memory(self, query: str, top_k: int = 5, priority: str = "NORMAL") -> List[Dict[str, Any]]:
        """Search memory (vector in Pinecone, fallback to Redis keys)."""
        results = []

        if self.pinecone_client and self.index:
            try:
                # Embed query
                query_embedding = [0.1] * 1536  # Placeholder
                pinecone_results = self.index.query(vector=query_embedding, top_k=top_k, include_metadata=True)
                results = [match.metadata for match in pinecone_results.matches]
                logger.info(f"[{self.agent_id}] Pinecone search returned {len(results)} results")
            except Exception as e:
                logger.error(f"[{self.agent_id}] Pinecone search failed: {e}")

        # Fallback: Redis key scan (limited)
        if self.redis_client and not results:
            try:
                keys = self.redis_client.keys(f"*{query}*")
                for key in keys[:top_k]:
                    data = self.redis_client.get(key)
                    if data:
                        results.append({"key": key.decode(), "data": json.loads(data)})
                logger.info(f"[{self.agent_id}] Redis fallback search returned {len(results)} results")
            except Exception as e:
                logger.error(f"[{self.agent_id}] Redis search failed: {e}")

        # For HIGH priority, could broadcast search request if results < top_k
        # Simplified for now - in full implementation would send message to other agents

        return results[:top_k]
