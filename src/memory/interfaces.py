"""
Memory system interfaces for Grokputer.
"""

from typing import Dict, Any, Protocol
from dataclasses import dataclass
from pathlib import Path

@dataclass
class MemoryConfig:
    """Configuration for memory system."""
    backend: str = "sqlite"  # or "pinecone", "redis"
    db_path: str = ""  # Will be set dynamically
    max_episodes: int = 1000
    consolidation_threshold: int = 100

    def __post_init__(self):
        if not self.db_path:
            # Set default path relative to project root
            project_root = Path(__file__).parent.parent.parent
            self.db_path = str(project_root / "db" / "memory.db")

class MemoryBackend(Protocol):
    """Protocol for memory backends."""

    def store_episode(self, agent_id: str, episode_data: Dict[str, Any]) -> None:
        """Store an episode for an agent."""
        ...

    def retrieve_context(self, agent_id: str, query: str = None, top_k: int = 5) -> list[Dict[str, Any]]:
        """Retrieve context for an agent."""
        ...

    def consolidate(self, agent_id: str) -> Dict[str, Any]:
        """Consolidate memory for an agent."""
        ...