"""
Memory system interfaces for Grokputer.
"""

from typing import Dict, Any, Protocol, Optional
from dataclasses import dataclass
from pathlib import Path


@dataclass
class MemoryConfig:
    """Configuration for memory system."""

    backend: str = "sqlite"  # or "pinecone", "redis", "hierarchical"
    db_path: str = ""  # Will be set dynamically
    redis_url: str = "redis://localhost:6379/0"  # Redis connection URL
    max_episodes: int = 1000
    consolidation_threshold: int = 100
    episode_ttl: Optional[int] = None  # Time-to-live for episodes in seconds

    # Pinecone configuration
    pinecone_key: Optional[str] = None
    pinecone_env: str = "us-west1-gcp"
    pinecone_index: str = "grokputer-memory"

    # HyDE configuration
    enable_hyde: bool = True
    hyde_num_hypotheticals: int = 3
    hyde_model: str = "grok-beta"

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


class BaseVectorStore(Protocol):
    """Protocol for vector store backends."""

    def embed_and_store(self, text: str, metadata: Dict[str, Any]) -> str:
        """Embed text and store in vector database, return vector ID."""
        ...

    def query_similar(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Query for similar vectors and return metadata."""
        ...
