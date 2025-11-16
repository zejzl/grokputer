try:
    import pinecone

    PINECONE_AVAILABLE = True
except ImportError:
    pinecone = None
    PINECONE_AVAILABLE = False

import json
import logging
import time
from typing import Any, Dict, List, Optional

from sentence_transformers import SentenceTransformer

from ..hyde_generator import HyDEGenerator
from ..interfaces import BaseVectorStore, MemoryBackend, MemoryConfig

logger = logging.getLogger(__name__)


class PineconeStore(BaseVectorStore, MemoryBackend):
    """
    Enhanced Pinecone vector store with HyDE support and MemoryBackend implementation.

    Features:
    - HyDE-augmented retrieval for improved semantic matching
    - MemoryBackend protocol for integration with hierarchical memory
    - Fallback to standard vector search when HyDE unavailable
    """

    def __init__(self, config: MemoryConfig, enable_hyde: bool = True):
        # Pinecone setup
        if not PINECONE_AVAILABLE:
            logger.warning("Pinecone library not installed, PineconeStore will be unavailable")
            self.pinecone_available = False
            self.index = None
            self.embedder = None
        else:
            try:
                pinecone.init(api_key=config.pinecone_key, environment=config.pinecone_env)
                self.index = pinecone.Index(config.pinecone_index)
                self.embedder = SentenceTransformer("all-MiniLM-L6-v2")
                self.pinecone_available = True
            except Exception as e:
                logger.warning(f"Pinecone initialization failed: {e}")
                self.pinecone_available = False
                self.index = None
                self.embedder = None

        # HyDE setup
        self.enable_hyde = enable_hyde and self.pinecone_available
        self.hyde_generator = HyDEGenerator() if self.enable_hyde else None

        # Memory config
        self.config = config

    def embed_and_store(self, text: str, metadata: Dict[str, Any]) -> str:
        """Embed text and store in vector database."""
        if not self.pinecone_available:
            logger.warning("Pinecone unavailable, skipping embed_and_store")
            return ""

        vec = self.embedder.encode(text).tolist()
        vec_id = f"vec_{hash(text) % 1000000}_{int(time.time())}"  # More unique ID
        self.index.upsert(vectors=[{"id": vec_id, "values": vec, "metadata": metadata}])
        return vec_id

    def query_similar(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Query for similar vectors with optional HyDE enhancement."""
        if not self.pinecone_available:
            logger.warning("Pinecone unavailable, returning empty results")
            return []

        results = []

        if self.enable_hyde and self.hyde_generator:
            # HyDE-enhanced search
            try:
                hypotheticals = self.hyde_generator.generate_hypotheticals_sync(query)
                if hypotheticals:
                    # Embed and search each hypothetical
                    all_matches = []
                    for hypo in hypotheticals:
                        hypo_vec = self.embedder.encode(hypo).tolist()
                        hypo_results = self.index.query(vector=hypo_vec, top_k=top_k * 2, include_metadata=True)
                        all_matches.extend(hypo_results["matches"])

                    # Deduplicate and rank by score
                    seen_ids = set()
                    unique_matches = []
                    for match in sorted(all_matches, key=lambda x: x["score"], reverse=True):
                        if match["id"] not in seen_ids:
                            unique_matches.append(match)
                            seen_ids.add(match["id"])
                            if len(unique_matches) >= top_k:
                                break

                    results = [match["metadata"] for match in unique_matches]
                    logger.debug(f"HyDE search returned {len(results)} results")
                else:
                    # Fallback to standard search
                    logger.warning("HyDE generation failed, falling back to standard search")
                    results = self._standard_query(query, top_k)
            except Exception as e:
                logger.error(f"HyDE search failed: {e}, falling back to standard search")
                results = self._standard_query(query, top_k)
        else:
            # Standard vector search
            results = self._standard_query(query, top_k)

        return results

    def _standard_query(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """Standard vector similarity search."""
        q_vec = self.embedder.encode(query).tolist()
        results = self.index.query(vector=q_vec, top_k=top_k, include_metadata=True)
        return [match["metadata"] for match in results["matches"]]

    # MemoryBackend implementation
    def store_episode(self, agent_id: str, episode_data: Dict[str, Any]) -> None:
        """Store episode in Pinecone as vector."""
        if not self.pinecone_available:
            return

        # Create searchable text from episode
        text_content = self._episode_to_text(episode_data)
        if not text_content:
            return

        # Add agent and episode metadata
        metadata = episode_data.copy()
        metadata.update(
            {
                "agent_id": agent_id,
                "episode_type": episode_data.get("type", "general"),
                "timestamp": episode_data.get("timestamp", time.time()),
                "importance": episode_data.get("importance", 1.0),
            }
        )

        try:
            self.embed_and_store(text_content, metadata)
            logger.debug(f"Stored episode for agent {agent_id}")
        except Exception as e:
            logger.error(f"Failed to store episode: {e}")

    def retrieve_context(self, agent_id: str, query: str = None, top_k: int = 5) -> List[Dict[str, Any]]:
        """Retrieve context using vector search."""
        if not self.pinecone_available:
            return []

        if not query:
            # Return recent episodes for agent
            query = f"agent {agent_id} recent activity"

        try:
            results = self.query_similar(query, top_k)
            # Filter by agent if possible (Pinecone metadata filtering)
            agent_results = [r for r in results if r.get("agent_id") == agent_id]
            return agent_results[:top_k] if agent_results else results[:top_k]
        except Exception as e:
            logger.error(f"Failed to retrieve context: {e}")
            return []

    def consolidate(self, agent_id: str) -> Dict[str, Any]:
        """Consolidate memory - return statistics since Pinecone doesn't support direct consolidation."""
        if not self.pinecone_available:
            return {"status": "no_data", "reason": "Pinecone unavailable"}

        # For now, return basic stats - could implement more sophisticated consolidation
        return {
            "status": "success",
            "agent_id": agent_id,
            "backend": "pinecone",
            "hyde_enabled": self.enable_hyde,
            "pinecone_available": True,
        }

    def _episode_to_text(self, episode_data: Dict[str, Any]) -> str:
        """Convert episode data to searchable text."""
        text_parts = []

        # Extract from common fields
        for field in ["content", "message", "description", "text", "query", "response", "action"]:
            if field in episode_data and isinstance(episode_data[field], str):
                text_parts.append(episode_data[field])

        # Extract from nested structures
        def extract_nested_text(data):
            if isinstance(data, str):
                return data
            elif isinstance(data, dict):
                return " ".join(extract_nested_text(v) for v in data.values() if v)
            elif isinstance(data, list):
                return " ".join(extract_nested_text(item) for item in data if item)
            return ""

        text_parts.append(extract_nested_text(episode_data))
        return " ".join(text_parts).strip()
