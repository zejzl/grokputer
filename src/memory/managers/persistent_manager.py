"""
Persistent Memory Manager for Grokputer.
Handles storage and retrieval of agent memories using SQLite.
"""

import sqlite3
import json
from typing import Dict, Any, List
from pathlib import Path
from ..interfaces import MemoryConfig, MemoryBackend

class PersistentMemoryManager(MemoryBackend):
    """Manages persistent storage of agent memories."""

    def __init__(self, config: MemoryConfig):
        self.config = config
        self.db_path = Path(config.db_path)
        self.db_path.parent.mkdir(exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize the database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS episodes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_id TEXT NOT NULL,
                    episode_data TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS consolidated_memory (
                    agent_id TEXT PRIMARY KEY,
                    memory_data TEXT NOT NULL,
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')

    def store_episode(self, agent_id: str, episode_data: Dict[str, Any]) -> None:
        """Store an episode for an agent."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                'INSERT INTO episodes (agent_id, episode_data) VALUES (?, ?)',
                (agent_id, json.dumps(episode_data))
            )

    def retrieve_context(self, agent_id: str, query: str = None, top_k: int = 5) -> List[Dict[str, Any]]:
        """Retrieve context for an agent."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                'SELECT episode_data FROM episodes WHERE agent_id = ? ORDER BY timestamp DESC LIMIT ?',
                (agent_id, top_k)
            )
            episodes = []
            for row in cursor:
                try:
                    episode = json.loads(row[0])
                    episodes.append(episode)
                except json.JSONDecodeError:
                    continue
            return episodes

    def consolidate(self, agent_id: str) -> Dict[str, Any]:
        """Consolidate memory for an agent."""
        episodes = self.retrieve_context(agent_id, top_k=self.config.consolidation_threshold)

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
            "last_consolidated": episodes[0] if episodes else None
        }

        # Store consolidated memory
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                'INSERT OR REPLACE INTO consolidated_memory (agent_id, memory_data) VALUES (?, ?)',
                (agent_id, json.dumps(consolidated))
            )

        return consolidated