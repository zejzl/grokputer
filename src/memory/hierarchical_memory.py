"""
Hierarchical Memory System for Grokputer.

Implements a three-tier memory architecture:
- Short-term: Fast working memory for immediate tasks
- Context: Session-level memory with decay mechanisms
- Long-term: Persistent Redis storage with consolidation
"""

import asyncio
import time
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import deque, defaultdict
import threading
from .interfaces import MemoryConfig, MemoryBackend
from ..knowledge_graph import KnowledgeGraph, Entity, Relationship
from ..exceptions import MemoryError, handle_error
from ..encryption import get_encryptor, randomize_encrypt, randomize_decrypt

logger = logging.getLogger(__name__)


@dataclass
class MemoryEntry:
    """Represents a single memory entry with metadata."""

    content: Dict[str, Any]
    timestamp: float
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    importance_score: float = 1.0
    decay_factor: float = 1.0  # For context memory decay

    def update_access(self):
        """Update access metadata."""
        self.access_count += 1
        self.last_accessed = time.time()

    def calculate_relevance(self, current_time: float) -> float:
        """Calculate relevance score based on recency, frequency, and importance."""
        time_since_access = current_time - self.last_accessed
        recency_score = 1.0 / (1.0 + time_since_access / 3600.0)  # Decay over hours
        frequency_score = min(self.access_count / 10.0, 1.0)  # Cap at 10 accesses

        return (recency_score * 0.4 + frequency_score * 0.3 + self.importance_score * 0.3) * self.decay_factor


class ShortTermMemory:
    """
    Short-term working memory for immediate task processing.

    Features:
    - Fast access (in-memory)
    - Limited capacity with LRU eviction
    - Task-specific context storage
    """

    def __init__(self, max_entries: int = 100):
        self.max_entries = max_entries
        self.entries: Dict[str, MemoryEntry] = {}
        self.access_order: deque = deque()  # For LRU tracking
        self._lock = threading.RLock()

    def store(self, key: str, content: Dict[str, Any], importance: float = 1.0) -> None:
        """Store content in short-term memory."""
        with self._lock:
            entry = MemoryEntry(content=content, timestamp=time.time(), importance_score=importance)

            # Remove existing entry if present
            if key in self.entries:
                self.access_order.remove(key)

            self.entries[key] = entry
            self.access_order.append(key)

            # Evict if over capacity
            self._evict_if_needed()

    def retrieve(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve content from short-term memory."""
        with self._lock:
            if key in self.entries:
                entry = self.entries[key]
                entry.update_access()

                # Move to end (most recently used)
                self.access_order.remove(key)
                self.access_order.append(key)

                return entry.content
            return None

    def search(self, query: str = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Search short-term memory for relevant entries."""
        with self._lock:
            current_time = time.time()
            scored_entries = []

            for key, entry in self.entries.items():
                relevance = entry.calculate_relevance(current_time)
                scored_entries.append((relevance, entry.content))

            # Sort by relevance and return top results
            scored_entries.sort(key=lambda x: x[0], reverse=True)
            return [content for _, content in scored_entries[:limit]]

    def _evict_if_needed(self) -> None:
        """Evict least recently used entries if over capacity."""
        while len(self.entries) > self.max_entries:
            # Remove least recently used
            lru_key = self.access_order.popleft()
            if lru_key in self.entries:
                del self.entries[lru_key]

    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        with self._lock:
            return {
                "total_entries": len(self.entries),
                "max_entries": self.max_entries,
                "utilization": len(self.entries) / self.max_entries,
                "oldest_entry_age": time.time()
                - min((e.timestamp for e in self.entries.values()), default=time.time()),
            }


class ContextMemory:
    """
    Context memory with decay mechanisms for session-level memory.

    Features:
    - Time-based decay
    - Importance-based retention
    - Automatic consolidation to long-term memory
    """

    def __init__(self, decay_rate: float = 0.95, consolidation_threshold: int = 50):
        self.decay_rate = decay_rate  # How much to decay per hour
        self.consolidation_threshold = consolidation_threshold
        self.entries: Dict[str, MemoryEntry] = {}
        self.session_start = time.time()
        self._lock = threading.RLock()

    def store(self, key: str, content: Dict[str, Any], importance: float = 1.0) -> None:
        """Store content in context memory."""
        with self._lock:
            entry = MemoryEntry(content=content, timestamp=time.time(), importance_score=importance, decay_factor=1.0)

            self.entries[key] = entry

            # Check if consolidation needed
            if len(self.entries) >= self.consolidation_threshold:
                self._consolidate_entries()

    def retrieve(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve content from context memory."""
        with self._lock:
            if key in self.entries:
                entry = self.entries[key]
                entry.update_access()
                return entry.content
            return None

    def search(self, query: str = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Search context memory with decay applied."""
        with self._lock:
            self._apply_decay()
            current_time = time.time()
            scored_entries = []

            for key, entry in self.entries.items():
                relevance = entry.calculate_relevance(current_time)
                scored_entries.append((relevance, entry.content))

            scored_entries.sort(key=lambda x: x[0], reverse=True)
            return [content for _, content in scored_entries[:limit]]

    def _apply_decay(self) -> None:
        """Apply time-based decay to all entries."""
        current_time = time.time()
        decay_factor = self.decay_rate ** ((current_time - self.session_start) / 3600.0)  # Decay per hour

        for entry in self.entries.values():
            entry.decay_factor = decay_factor

    def _consolidate_entries(self) -> List[Dict[str, Any]]:
        """Consolidate low-relevance entries for long-term storage."""
        current_time = time.time()
        self._apply_decay()

        # Find entries to consolidate (low relevance)
        consolidation_candidates = []
        keep_entries = {}

        for key, entry in self.entries.items():
            relevance = entry.calculate_relevance(current_time)
            if relevance < 0.3:  # Low relevance threshold
                consolidation_candidates.append(entry.content)
            else:
                keep_entries[key] = entry

        # Keep only high-relevance entries
        self.entries = keep_entries

        logger.info(f"Consolidated {len(consolidation_candidates)} entries from context memory")
        return consolidation_candidates

    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        with self._lock:
            self._apply_decay()
            current_time = time.time()

            total_relevance = sum(entry.calculate_relevance(current_time) for entry in self.entries.values())
            avg_relevance = total_relevance / len(self.entries) if self.entries else 0

            return {
                "total_entries": len(self.entries),
                "avg_relevance": avg_relevance,
                "session_duration": current_time - self.session_start,
                "decay_rate": self.decay_rate,
            }


class HierarchicalMemoryManager(MemoryBackend):
    """
    Hierarchical memory manager coordinating short-term, context, and long-term memory.

    Architecture:
    - Short-term: Fast, limited working memory
    - Context: Session memory with decay
    - Long-term: Persistent storage with consolidation
    """

    def __init__(self, config: MemoryConfig, long_term_backend: Optional[MemoryBackend] = None):
        self.config = config
        self.long_term_backend = long_term_backend

        # Initialize memory layers
        self.short_term = ShortTermMemory(max_entries=50)  # Fast working memory
        self.context = ContextMemory(
            decay_rate=0.9, consolidation_threshold=config.consolidation_threshold  # Decay to 90% per hour
        )

        # Initialize knowledge graph for semantic understanding
        self.knowledge_graph = KnowledgeGraph()

        # Memory fusion settings
        self.fusion_weights = {
            "short_term": 0.5,
            "context": 0.3,
            "long_term": 0.2,
            "knowledge_graph": 0.4,  # Higher weight for semantic relevance
        }

        # Background consolidation task
        self._consolidation_task = None
        self._running = False

    async def start(self):
        """Start background memory management tasks."""
        if self._running:
            return

        self._running = True
        self._consolidation_task = asyncio.create_task(self._background_consolidation())

    async def stop(self):
        """Stop background tasks."""
        self._running = False
        if self._consolidation_task:
            self._consolidation_task.cancel()
            try:
                await self._consolidation_task
            except asyncio.CancelledError:
                pass

    async def _background_consolidation(self):
        """Background task for memory consolidation and cleanup."""
        try:
            while self._running:
                await asyncio.sleep(300)  # Consolidate every 5 minutes

                # Consolidate context memory to long-term
                consolidated_entries = self.context._consolidate_entries()

                if consolidated_entries and self.long_term_backend:
                    # Store consolidated entries in long-term memory
                    for entry in consolidated_entries:
                        try:
                            self.long_term_backend.store_episode("consolidated_context", entry)
                        except Exception as e:
                            handle_error(e, "HierarchicalMemory._background_consolidation", "error")

                # Periodic cleanup of expired entries
                await self._cleanup_expired_entries()

        except asyncio.CancelledError:
            logger.info("Background consolidation stopped")
            raise

    async def _cleanup_expired_entries(self) -> int:
        """Clean up expired entries from memory layers.

        Returns:
            Number of entries cleaned up
        """
        current_time = time.time()
        cleanup_count = 0

        # Clean short-term memory (remove entries older than 1 hour)
        expired_short_term = []
        for key, entry in self.short_term.entries.items():
            if current_time - entry.timestamp > 3600:  # 1 hour
                expired_short_term.append(key)

        for key in expired_short_term:
            del self.short_term.entries[key]
            cleanup_count += 1

        # Clean context memory (remove entries with very low relevance)
        expired_context = []
        for key, entry in self.context.entries.items():
            relevance = entry.calculate_relevance(current_time)
            if relevance < 0.1:  # Very low relevance threshold
                expired_context.append(key)

        for key in expired_context:
            del self.context.entries[key]
            cleanup_count += 1

        if cleanup_count > 0:
            logger.info(f"[MEMORY CLEANUP] Cleaned up {cleanup_count} expired memory entries")
            # Analytics: track cleanup metrics
            cleanup_metrics = {
                "short_term_cleaned": len(expired_short_term),
                "context_cleaned": len(expired_context),
                "total_cleaned": cleanup_count,
                "timestamp": current_time,
            }
            # Could integrate with analytics system here
            logger.debug(f"[MEMORY CLEANUP] Details: {cleanup_metrics}")

        return cleanup_count

    def _encrypt_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Encrypt sensitive data in memory entries."""
        encryptor = get_encryptor()

        # Keys that contain sensitive information
        sensitive_keys = ["api_key", "password", "token", "secret", "key", "auth"]

        encrypted_data = data.copy()

        # Encrypt sensitive string values
        for key, value in encrypted_data.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                if isinstance(value, str) and len(value) > 10:  # Only encrypt substantial strings
                    try:
                        encrypted_data[key] = randomize_encrypt(value)
                    except Exception as e:
                        handle_error(e, f"MemoryDataEncryption.{key}", "warning")
                        # Keep original if encryption fails

        return encrypted_data

    def _decrypt_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Decrypt sensitive data when retrieving from memory."""
        encryptor = get_encryptor()

        sensitive_keys = ["api_key", "password", "token", "secret", "key", "auth"]

        decrypted_data = data.copy()

        # Decrypt sensitive values
        for key, value in decrypted_data.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                if isinstance(value, str) and value.startswith("RND:"):
                    try:
                        decrypted_data[key] = randomize_decrypt(value)
                    except Exception as e:
                        handle_error(e, f"MemoryDataDecryption.{key}", "warning")
                        # Keep encrypted if decryption fails

        return decrypted_data

    def store_episode(self, agent_id: str, episode_data: Dict[str, Any]) -> None:
        """Store episode across memory hierarchy and extract relationships."""
        importance = episode_data.get("importance", 1.0)
        content_type = episode_data.get("type", "general")

        # Encrypt sensitive data before storage
        encrypted_data = self._encrypt_sensitive_data(episode_data)

        # Store in short-term memory (fast access)
        short_term_key = f"{agent_id}_{content_type}_{hash(str(encrypted_data)) % 1000}"
        self.short_term.store(short_term_key, encrypted_data, importance)

        # Store in context memory (session-level)
        context_key = f"context_{agent_id}_{len(self.context.entries)}"
        self.context.store(context_key, episode_data, importance)

        # Store in long-term if important or periodic
        if importance > 0.8 or len(self.context.entries) % 10 == 0:
            if self.long_term_backend:
                try:
                    self.long_term_backend.store_episode(agent_id, episode_data)
                except Exception as e:
                    logger.error(f"Failed to store in long-term memory: {e}")

        # Extract relationships from episode content
        self._extract_relationships_from_episode(episode_data, agent_id)

    def retrieve_context(self, agent_id: str, query: str = None, top_k: int = 5) -> List[Dict[str, Any]]:
        """Retrieve context using memory fusion including knowledge graph."""
        results = []

        # Query each memory layer
        short_term_results = self.short_term.search(query, top_k * 2)
        context_results = self.context.search(query, top_k * 2)

        long_term_results = []
        if self.long_term_backend:
            try:
                long_term_results = self.long_term_backend.retrieve_context(agent_id, query, top_k * 2)
            except Exception as e:
                logger.error(f"Failed to retrieve from long-term memory: {e}")

        # Get knowledge graph semantic search results
        kg_results = self.knowledge_graph.semantic_search(query or "", top_k * 2)

        # Apply fusion weights and combine results
        all_results = []

        # Add short-term results with weight
        for result in short_term_results:
            result_copy = result.copy()
            result_copy["_memory_layer"] = "short_term"
            result_copy["_fusion_score"] = self.fusion_weights["short_term"]
            all_results.append(result_copy)

        # Add context results with weight
        for result in context_results:
            result_copy = result.copy()
            result_copy["_memory_layer"] = "context"
            result_copy["_fusion_score"] = self.fusion_weights["context"]
            all_results.append(result_copy)

        # Add long-term results with weight
        for result in long_term_results:
            result_copy = result.copy()
            result_copy["_memory_layer"] = "long_term"
            result_copy["_fusion_score"] = self.fusion_weights["long_term"]
            all_results.append(result_copy)

        # Add knowledge graph results with semantic scoring
        for entity, semantic_score in kg_results:
            kg_result = {
                "type": "entity",
                "entity_id": entity.id,
                "entity_label": entity.label,
                "entity_type": entity.entity_type,
                "properties": entity.properties,
                "confidence": entity.confidence,
                "_memory_layer": "knowledge_graph",
                "_fusion_score": semantic_score * self.fusion_weights["knowledge_graph"],
            }
            all_results.append(kg_result)

        # Sort by fusion score and return top_k
        all_results.sort(key=lambda x: x.get("_fusion_score", 0), reverse=True)

        # Decrypt sensitive data before returning
        decrypted_results = []
        for result in all_results[:top_k]:
            decrypted_results.append(self._decrypt_sensitive_data(result))

        return decrypted_results

    def consolidate(self, agent_id: str) -> Dict[str, Any]:
        """Consolidate memory across all layers including knowledge graph."""
        consolidation_stats = {
            "short_term": self.short_term.get_stats(),
            "context": self.context.get_stats(),
            "knowledge_graph": self.get_knowledge_stats(),
            "long_term": {},
        }

        # Consolidate long-term memory if available
        if self.long_term_backend:
            try:
                consolidation_stats["long_term"] = self.long_term_backend.consolidate(agent_id)
            except Exception as e:
                logger.error(f"Failed to consolidate long-term memory: {e}")
                consolidation_stats["long_term"] = {"error": str(e)}

        # Trigger context consolidation
        consolidated_count = len(self.context._consolidate_entries())
        consolidation_stats["consolidated_entries"] = consolidated_count

        return consolidation_stats

    def save_knowledge_graph(self, filepath: str) -> None:
        """Save knowledge graph to file."""
        self.knowledge_graph.save_to_file(filepath)

    def load_knowledge_graph(self, filepath: str) -> None:
        """Load knowledge graph from file."""
        self.knowledge_graph.load_from_file(filepath)

    def _extract_relationships_from_episode(self, episode_data: Dict[str, Any], agent_id: str) -> None:
        """Extract relationships from episode data and store in knowledge graph."""
        try:
            # Extract text content for relationship extraction
            text_content = self._extract_text_from_episode(episode_data)

            if text_content and len(text_content.strip()) > 10:  # Minimum length check
                source = f"episode_{agent_id}_{episode_data.get('type', 'unknown')}"
                relationships = self.extract_and_store_relationships(text_content, source)

                if relationships:
                    logger.debug(f"Extracted {len(relationships)} relationships from episode")

        except Exception as e:
            logger.error(f"Failed to extract relationships from episode: {e}")

    def _extract_text_from_episode(self, episode_data: Dict[str, Any]) -> str:
        """Extract searchable text content from episode data."""
        text_parts = []

        # Extract from common fields
        for field in ["content", "message", "description", "text", "query", "response"]:
            if field in episode_data and isinstance(episode_data[field], str):
                text_parts.append(episode_data[field])

        # Extract from properties if it's an entity/relationship
        if "properties" in episode_data and isinstance(episode_data["properties"], dict):
            for prop_value in episode_data["properties"].values():
                if isinstance(prop_value, str):
                    text_parts.append(prop_value)

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

    def store_entity(self, entity: Entity) -> None:
        """Store an entity in the knowledge graph."""
        self.knowledge_graph.add_entity(entity)

        # Also store as episode for memory layers
        episode_data = {
            "type": "entity",
            "entity_id": entity.id,
            "entity_label": entity.label,
            "entity_type": entity.entity_type,
            "properties": entity.properties,
            "importance": 0.8,  # Entities are generally important
        }
        self.store_episode("knowledge_graph", episode_data)

    def store_relationship(self, relationship: Relationship) -> None:
        """Store a relationship in the knowledge graph."""
        self.knowledge_graph.add_relationship(relationship)

        # Also store as episode for memory layers
        episode_data = {
            "type": "relationship",
            "relationship_id": relationship.id,
            "source_id": relationship.source_id,
            "target_id": relationship.target_id,
            "relationship_type": relationship.type,
            "properties": relationship.properties,
            "importance": 0.7,  # Relationships are important for connections
        }
        self.store_episode("knowledge_graph", episode_data)

    def extract_and_store_relationships(self, text: str, source: str = "memory_extraction") -> List[Relationship]:
        """Extract relationships from text and store them."""
        relationships = self.knowledge_graph.extract_relationships_from_text(text, source)

        # Store extracted relationships as episodes
        for rel in relationships:
            episode_data = {
                "type": "extracted_relationship",
                "text_source": text[:200],  # Store snippet of source text
                "relationship_id": rel.id,
                "source_entity": rel.source_id,
                "target_entity": rel.target_id,
                "relationship_type": rel.type,
                "importance": 0.6,  # Lower importance for extracted relationships
            }
            self.store_episode("relationship_extraction", episode_data)

        return relationships

    def semantic_search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Perform semantic search combining memory and knowledge graph."""
        results = []

        # Get memory results
        memory_results = self.retrieve_context("knowledge_graph", query, top_k * 2)

        # Get knowledge graph semantic search results
        kg_results = self.knowledge_graph.semantic_search(query, top_k * 2)

        # Convert KG results to dict format
        kg_dict_results = []
        for entity, score in kg_results:
            kg_dict_results.append(
                {
                    "type": "entity",
                    "entity_id": entity.id,
                    "entity_label": entity.label,
                    "entity_type": entity.entity_type,
                    "properties": entity.properties,
                    "confidence": entity.confidence,
                    "_memory_layer": "knowledge_graph",
                    "_fusion_score": score * self.fusion_weights["knowledge_graph"],
                }
            )

        # Combine all results
        all_results = memory_results + kg_dict_results

        # Sort by fusion score and return top_k
        all_results.sort(key=lambda x: x.get("_fusion_score", 0), reverse=True)
        return all_results[:top_k]

    def traverse_knowledge(
        self, entity_id: str, relationship_types: Optional[List[str]] = None, max_depth: int = 2
    ) -> Dict[str, Any]:
        """Traverse knowledge graph from an entity."""
        return self.knowledge_graph.traverse_graph(entity_id, relationship_types, max_depth)

    def get_knowledge_stats(self) -> Dict[str, Any]:
        """Get knowledge graph statistics."""
        return self.knowledge_graph.get_graph_statistics()

    def get_hierarchical_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics across all memory layers."""
        return {
            "short_term": self.short_term.get_stats(),
            "context": self.context.get_stats(),
            "knowledge_graph": self.get_knowledge_stats(),
            "fusion_weights": self.fusion_weights,
            "background_consolidation": self._running,
        }
