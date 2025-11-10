#!/usr/bin/env python3
# MemoryAgent: Handles state recall, storage, and search for distributed swarm.
# Integrates Redis for fast key-value, Pinecone for vector search (memory across sessions/instances).
# Broadcasts updates via MessageBus for sync (e.g., 'memory_update' to all agents).

import asyncio
import json
import os
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

load_dotenv()

from src.agents.base_agent import BaseAgent
from src.core.message_bus import MessageBus

try:
    import redis
    from pinecone import Pinecone, ServerlessSpec
    PINECONE_AVAILABLE = True
except ImportError:
    PINECONE_AVAILABLE = False
    redis = None  # Fallback warning in init

class MemoryAgent(BaseAgent):
    def __init__(self, name: str = "MemoryAgent", agent_type: str = "memory"):
        super().__init__(name=name, agent_type=agent_type)
        self.bus = MessageBus(backend=os.getenv('MESSAGE_BUS_BACKEND', 'redis'))
        self.redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
        self.pinecone_key = os.getenv('PINECONE_KEY')
        self.pinecone_env = os.getenv('PINECONE_ENV', 'us-west1-gcp')
        self.pinecone_index = os.getenv('PINECONE_INDEX', 'grokputer-memory')
        
        # Init Redis client (always)
        self.redis_client = redis.from_url(self.redis_url) if redis else None
        
        # Init Pinecone (optional, for vector search)
        self.pinecone_client = None
        if PINECONE_AVAILABLE and self.pinecone_key:
            self.pinecone_client = Pinecone(api_key=self.pinecone_key)
            # Ensure index exists (upsert if needed)
            if self.pinecone_index not in self.pinecone_client.list_indexes().names():
                self.pinecone_client.create_index(
                    name=self.pinecone_index,
                    dimension=1536,  # Default for sentence-transformers
                    metric='cosine',
                    spec=ServerlessSpec(cloud='aws', region='us-west-2')
                )
            self.index = self.pinecone_client.Index(self.pinecone_index)
        else:
            self.logger.warning("Pinecone not available – falling back to Redis only.")
        
        self.priority_map = {"HIGH": 0, "NORMAL": 1, "LOW": 2}

    async def recall_state(self, key: str, priority: str = "HIGH") -> Optional[Dict[str, Any]]:
        """Recall state from Redis/Pinecone. Urgent (HIGH) broadcasts request for sync."""
        prio = self.priority_map.get(priority, 1)
        
        # Check local Redis first (fast)
        if self.redis_client:
            state = self.redis_client.get(key)
            if state:
                return json.loads(state)
        
        # If not found, query Pinecone (vector search for similar keys)
        if self.pinecone_client:
            # Embed query (simple key as text; in prod, use sentence-transformers)
            query_embedding = [0.1] * 1536  # Placeholder – integrate real embedding
            results = self.index.query(vector=query_embedding, top_k=1, include_metadata=True)
            if results.matches:
                return results.matches[0].metadata
        
        # For HIGH priority, broadcast request to sync from other instances
        if priority == "HIGH":
            corr_id = str(uuid.uuid4())
            req_msg = {
                "type": "memory_recall_request",
                "key": key,
                "corr_id": corr_id,
                "from": self.agent_type,
                "priority": priority
            }
            try:
                resp = await self.bus.request_response(req_msg, timeout=5.0, priority=priority)
                if resp and resp.get("type") == "memory_recall_response":
                    # Cache response
                    if self.redis_client:
                        self.redis_client.set(key, json.dumps(resp["data"]), ex=3600)  # 1h TTL
                    return resp["data"]
            except asyncio.TimeoutError:
                self.logger.warning(f"High-priority recall for {key} timed out – no response from swarm.")
        
        return None  # Not found

    async def store_state(self, key: str, data: Dict[str, Any], priority: str = "NORMAL"):
        """Store to Redis/Pinecone, broadcast update for distributed sync."""
        # Store to Redis (fast access)
        if self.redis_client:
            self.redis_client.set(key, json.dumps(data), ex=86400)  # 24h TTL
        
        # Upsert to Pinecone (vector store)
        if self.pinecone_client:
            # Embed data (placeholder; use real embedding in prod)
            embedding = [0.2] * 1536
            self.index.upsert(vectors=[{"id": key, "values": embedding, "metadata": data}])
        
        # Broadcast update via MessageBus (sync other instances/agents)
        prio = self.priority_map.get(priority, 1)
        update_msg = {
            "type": "memory_update",
            "key": key,
            "data": data,
            "from": self.agent_type,
            "priority": priority
        }
        await self.bus.broadcast(update_msg, priority=priority)
        self.logger.info(f"Stored and broadcasted memory update for key: {key}")

    async def search_memory(self, query: str, top_k: int = 5, priority: str = "NORMAL") -> List[Dict[str, Any]]:
        """Search memory (vector in Pinecone, fallback to Redis keys)."""
        results = []
        
        if self.pinecone_client:
            # Embed query
            query_embedding = [0.1] * 1536  # Placeholder
            pinecone_results = self.index.query(vector=query_embedding, top_k=top_k, include_metadata=True)
            results = [match.metadata for match in pinecone_results.matches]
        
        # Fallback: Redis key scan (limited)
        if self.redis_client and not results:
            keys = self.redis_client.keys(f"*{query}*")
            for key in keys[:top_k]:
                data = self.redis_client.get(key)
                if data:
                    results.append({"key": key.decode(), "data": json.loads(data)})
        
        # For HIGH priority, broadcast search request if results < top_k
        if priority == "HIGH" and len(results) < top_k:
            corr_id = str(uuid.uuid4())
            search_msg = {
                "type": "memory_search_request",
                "query": query,
                "top_k": top_k,
                "corr_id": corr_id,
                "from": self.agent_type,
                "priority": priority
            }
            try:
                resp = await self.bus.request_response(search_msg, timeout=10.0, priority=priority)
                if resp and resp.get("type") == "memory_search_response":
                    results.extend(resp.get("results", []))
            except asyncio.TimeoutError:
                self.logger.warning(f"High-priority search for '{query}' timed out.")
        
        return results[:top_k]

    async def handle_message(self, msg: Dict[str, Any]):
        """Override BaseAgent: Handle memory-specific messages (e.g., recall requests)."""
        msg_type = msg.get("type")
        if msg_type == "memory_recall_request":
            key = msg["key"]
            data = await self.recall_state(key, priority="HIGH")  # Urgent recall
            if data:
                resp = {
                    "type": "memory_recall_response",
                    "corr_id": msg["corr_id"],
                    "data": data,
                    "from": self.agent_type
                }
                await self.bus.send_response(resp)  # Or broadcast if needed
        elif msg_type == "memory_search_request":
            query = msg["query"]
            top_k = msg["top_k"]
            search_results = await self.search_memory(query, top_k, priority="HIGH")
            resp = {
                "type": "memory_search_response",
                "corr_id": msg["corr_id"],
                "results": search_results,
                "from": self.agent_type
            }
            await self.bus.send_response(resp)
        else:
            # Delegate to BaseAgent
            await super().handle_message(msg)

# Example usage (for testing)
if __name__ == "__main__":
    async def test_memory():
        agent = MemoryAgent()
        # Store
        await agent.store_state("test_key", {"status": "active", "last_update": "2025-11-09"})
        # Recall
        recalled = await agent.recall_state("test_key", priority="HIGH")
        print(f"Recalled: {recalled}")
        # Search
        search = await agent.search_memory("test", top_k=3)
        print(f"Search results: {search}")

    asyncio.run(test_memory())
