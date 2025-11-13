# src/core/memory_manager.py
"""
Memory Manager: Persistent state for ORAM agents (Redis live + SQLite eternal).
Phase 2: Enables recall, learning from history.
"""

import asyncio
import logging
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from pathlib import Path
import os
import redis.asyncio as redis  # pip install redis

from src.core.message_bus import MessageBus  # For pub/sub integration


class MemoryManager:
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {
            "redis_url": os.getenv("REDIS_URL", "redis://localhost:6379"),
            "sqlite_db": "vault/memory.db",
            "ttl_hours": 1,  # Ephemeral TTL
            "debug": False,
        }
        self.logger = logging.getLogger(__name__)
        self.redis_client: Optional[redis.Redis] = None
        self.sqlite_conn: Optional[sqlite3.Connection] = None
        self.db_path = Path(self.config["sqlite_db"])
        self.db_path.parent.mkdir(exist_ok=True)

        self.message_bus = MessageBus()  # Optional integration
        self.running = False

        self.logger.info("[MEMORY] Initialized - Redis + SQLite")

    async def start(self):
        """Connect to backends."""
        try:
            # Redis for live
            self.redis_client = redis.from_url(self.config["redis_url"])
            await self.redis_client.ping()
            self.logger.info("[MEMORY] Redis connected")
        except Exception as e:
            self.logger.warning(f"[MEMORY] Redis failed: {e} - Fallback to SQLite only")
            self.redis_client = None

        # SQLite for eternal
        self.sqlite_conn = sqlite3.connect(self.db_path)
        self._init_schema()
        self.logger.info("[MEMORY] SQLite ready")

        self.running = True

    def _init_schema(self):
        """Create tables."""
        cursor = self.sqlite_conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                value TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                agent_id TEXT,
                type TEXT  -- 'observation', 'result', 'failure'
            )
        """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                task TEXT,
                status TEXT,
                created DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """
        )
        self.sqlite_conn.commit()

    async def store(
        self,
        key: str,
        value: Dict[str, Any],
        agent_id: str = "system",
        mem_type: str = "general",
        ttl: Optional[int] = None,
    ):
        """Store to Redis (live) + SQLite (eternal)."""
        if not self.running:
            raise RuntimeError("[MEMORY] Not started")

        # Serialize
        serialized = json.dumps(value)
        timestamp = datetime.now()

        # Redis (ephemeral, pub if bus)
        if self.redis_client:
            ttl_sec = ttl or (self.config["ttl_hours"] * 3600)
            await self.redis_client.set(key, serialized, ex=ttl_sec)
            if self.message_bus:
                # Broadcast update
                from src.core.message_bus import Message, MessagePriority

                mem_msg = Message(
                    from_agent="memory",
                    to_agent="all",
                    message_type="memory_update",
                    content={"key": key, "type": mem_type, "agent": agent_id},
                    priority=MessagePriority.LOW,
                )
                await self.message_bus.broadcast(mem_msg)
            self.logger.debug(f"[MEMORY] Stored to Redis: {key}")

        # SQLite (durable)
        cursor = self.sqlite_conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO memories (key, value, timestamp, agent_id, type) VALUES (?, ?, ?, ?, ?)",
            (key, serialized, timestamp, agent_id, mem_type),
        )
        self.sqlite_conn.commit()
        self.logger.info(f"[MEMORY] Stored eternal: {key} ({mem_type}) by {agent_id}")

    async def retrieve(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve from Redis (fast) or SQLite (fallback)."""
        if self.redis_client:
            val = await self.redis_client.get(key)
            if val:
                return json.loads(val)

        # Fallback SQLite
        cursor = self.sqlite_conn.cursor()
        cursor.execute("SELECT value FROM memories WHERE key = ? ORDER BY timestamp DESC LIMIT 1", (key,))
        row = cursor.fetchone()
        return json.loads(row[0]) if row else None

    async def search(self, query: str, limit: int = 10, mem_type: str = None) -> List[Dict[str, Any]]:
        """Search SQLite (e.g., 'failures' or keyword)."""
        cursor = self.sqlite_conn.cursor()
        sql = "SELECT key, value, timestamp, agent_id FROM memories WHERE type = ? OR value LIKE ? ORDER BY timestamp DESC LIMIT ?"
        params = (mem_type, f"%{query}%", limit) if mem_type else ("general", f"%{query}%", limit)
        cursor.execute(sql, params)
        results = []
        for row in cursor.fetchall():
            results.append({"key": row[0], "value": json.loads(row[1]), "timestamp": row[2], "agent_id": row[3]})
        return results

    async def archive_daily(self):
        """Daily requiem: Backup SQLite to vault, prune old."""
        if not self.running:
            return

        timestamp = datetime.now().strftime("%Y%m%d")
        backup = self.db_path.parent / f"memory_backup_{timestamp}.db"
        shutil.copy2(self.db_path, backup)
        self.logger.info(f"[MEMORY] Daily archive: {backup}")

        # Prune old (>7 days)
        cutoff = datetime.now() - timedelta(days=7)
        cursor = self.sqlite_conn.cursor()
        cursor.execute("DELETE FROM memories WHERE timestamp < ?", (cutoff,))
        self.sqlite_conn.commit()
        pruned = cursor.rowcount
        self.logger.info(f"[MEMORY] Pruned {pruned} old memories")

    async def stop(self):
        """Cleanup."""
        if self.redis_client:
            await self.redis_client.close()
        if self.sqlite_conn:
            self.sqlite_conn.close()
        self.running = False
        self.logger.info("[MEMORY] Stopped")


# Example/Integration
async def example_usage():
    mem = MemoryManager(config={"debug": True})
    await mem.start()

    # Store
    await mem.store(
        "observation_1", {"screen": "desktop idle", "time": "now"}, agent_id="observer", mem_type="observation"
    )

    # Retrieve
    obs = await mem.retrieve("observation_1")
    print(f"Retrieved: {obs}")

    # Search
    failures = await mem.search("error", mem_type="failure")
    print(f"Failures: {len(failures)}")

    # Archive sim
    await mem.archive_daily()

    await mem.stop()


if __name__ == "__main__":
    asyncio.run(example_usage())
