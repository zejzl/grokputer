"""
Knowledge Graph System for Grokputer.

Provides semantic understanding and relationship mapping capabilities
for advanced reasoning and multi-modal understanding.
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import re
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class Entity:
    """Represents a knowledge graph entity (node)."""

    id: str
    label: str
    properties: Dict[str, Any] = field(default_factory=dict)
    entity_type: str = "generic"
    confidence: float = 1.0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    source: str = "unknown"

    def update_property(self, key: str, value: Any) -> None:
        """Update an entity property."""
        self.properties[key] = value
        self.updated_at = time.time()

    def to_dict(self) -> Dict[str, Any]:
        """Convert entity to dictionary."""
        return {
            "id": self.id,
            "label": self.label,
            "properties": self.properties,
            "entity_type": self.entity_type,
            "confidence": self.confidence,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "source": self.source,
        }


@dataclass
class Relationship:
    """Represents a relationship between entities (edge)."""

    id: str
    source_id: str
    target_id: str
    type: str
    properties: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    bidirectional: bool = False
    created_at: float = field(default_factory=time.time)
    source: str = "unknown"

    def to_dict(self) -> Dict[str, Any]:
        """Convert relationship to dictionary."""
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "type": self.type,
            "properties": self.properties,
            "confidence": self.confidence,
            "bidirectional": self.bidirectional,
            "created_at": self.created_at,
            "source": self.source,
        }


class KnowledgeGraph:
    """
    Knowledge graph for semantic understanding and relationship mapping.

    Features:
    - Entity and relationship storage
    - Graph traversal and querying
    - Relationship extraction from text
    - Semantic search and reasoning
    """

    def __init__(self):
        self.entities: Dict[str, Entity] = {}
        self.relationships: Dict[str, Relationship] = {}

        # Indexes for efficient querying
        self.entity_by_type: Dict[str, Set[str]] = defaultdict(set)
        self.entity_by_label: Dict[str, Set[str]] = defaultdict(set)
        self.relationships_by_type: Dict[str, Set[str]] = defaultdict(set)
        self.outgoing_relationships: Dict[str, Set[str]] = defaultdict(set)
        self.incoming_relationships: Dict[str, Set[str]] = defaultdict(set)

        # NLP patterns for relationship extraction
        self.relationship_patterns = self._load_relationship_patterns()

    def _load_relationship_patterns(self) -> Dict[str, List[str]]:
        """Load patterns for extracting relationships from text."""
        return {
            "is_a": [
                r"(\w+)\s+is\s+a\s+(\w+)",
                r"(\w+)\s+is\s+an\s+(\w+)",
                r"(\w+)\s+are\s+(\w+)",
            ],
            "has_property": [
                r"(\w+)\s+has\s+(\w+)",
                r"(\w+)\s+contains\s+(\w+)",
                r"(\w+)\s+includes\s+(\w+)",
            ],
            "related_to": [
                r"(\w+)\s+related\s+to\s+(\w+)",
                r"(\w+)\s+connected\s+to\s+(\w+)",
                r"(\w+)\s+linked\s+to\s+(\w+)",
            ],
            "causes": [
                r"(\w+)\s+causes\s+(\w+)",
                r"(\w+)\s+leads\s+to\s+(\w+)",
                r"(\w+)\s+results\s+in\s+(\w+)",
            ],
            "part_of": [
                r"(\w+)\s+is\s+part\s+of\s+(\w+)",
                r"(\w+)\s+belongs\s+to\s+(\w+)",
            ],
        }

    def add_entity(self, entity: Entity) -> None:
        """Add an entity to the knowledge graph."""
        self.entities[entity.id] = entity

        # Update indexes
        self.entity_by_type[entity.entity_type].add(entity.id)
        self.entity_by_label[entity.label.lower()].add(entity.id)

        logger.debug(f"Added entity: {entity.label} ({entity.entity_type})")

    def add_relationship(self, relationship: Relationship) -> None:
        """Add a relationship to the knowledge graph."""
        self.relationships[relationship.id] = relationship

        # Update indexes
        self.relationships_by_type[relationship.type].add(relationship.id)
        self.outgoing_relationships[relationship.source_id].add(relationship.id)
        self.incoming_relationships[relationship.target_id].add(relationship.id)

        # Add reverse relationship if bidirectional
        if relationship.bidirectional:
            reverse_id = f"{relationship.id}_reverse"
            reverse_relationship = Relationship(
                id=reverse_id,
                source_id=relationship.target_id,
                target_id=relationship.source_id,
                type=relationship.type,
                properties=relationship.properties.copy(),
                confidence=relationship.confidence,
                bidirectional=True,
                source=relationship.source,
            )
            self.relationships[reverse_id] = reverse_relationship
            self.relationships_by_type[relationship.type].add(reverse_id)
            self.outgoing_relationships[relationship.target_id].add(reverse_id)
            self.incoming_relationships[relationship.source_id].add(reverse_id)

        logger.debug(f"Added relationship: {relationship.source_id} --{relationship.type}--> {relationship.target_id}")

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Get an entity by ID."""
        return self.entities.get(entity_id)

    def get_relationship(self, relationship_id: str) -> Optional[Relationship]:
        """Get a relationship by ID."""
        return self.relationships.get(relationship_id)

    def find_entities_by_type(self, entity_type: str) -> List[Entity]:
        """Find entities by type."""
        entity_ids = self.entity_by_type.get(entity_type, set())
        return [self.entities[eid] for eid in entity_ids if eid in self.entities]

    def find_entities_by_label(self, label: str, fuzzy: bool = False) -> List[Entity]:
        """Find entities by label."""
        if fuzzy:
            # Simple fuzzy matching
            matching_ids = set()
            search_label = label.lower()
            for stored_label, entity_ids in self.entity_by_label.items():
                if search_label in stored_label or stored_label in search_label:
                    matching_ids.update(entity_ids)
            return [self.entities[eid] for eid in matching_ids if eid in self.entities]
        else:
            entity_ids = self.entity_by_label.get(label.lower(), set())
            return [self.entities[eid] for eid in entity_ids if eid in self.entities]

    def get_entity_relationships(self, entity_id: str, direction: str = "both") -> List[Relationship]:
        """Get relationships for an entity."""
        relationship_ids = set()

        if direction in ["outgoing", "both"]:
            relationship_ids.update(self.outgoing_relationships.get(entity_id, set()))

        if direction in ["incoming", "both"]:
            relationship_ids.update(self.incoming_relationships.get(entity_id, set()))

        return [self.relationships[rid] for rid in relationship_ids if rid in self.relationships]

    def traverse_graph(
        self, start_entity_id: str, relationship_types: Optional[List[str]] = None, max_depth: int = 2
    ) -> Dict[str, Any]:
        """Traverse the graph from a starting entity."""
        visited = set()
        path = []

        def dfs(current_id: str, depth: int, current_path: List[str]):
            if depth > max_depth or current_id in visited:
                return

            visited.add(current_id)
            current_path.append(current_id)

            if depth > 0:  # Don't include start node in results
                path.append(current_path.copy())

            # Get relationships
            relationships = self.get_entity_relationships(current_id)
            for rel in relationships:
                if relationship_types is None or rel.type in relationship_types:
                    next_id = rel.target_id if rel.source_id == current_id else rel.source_id
                    dfs(next_id, depth + 1, current_path)

            current_path.pop()
            visited.remove(current_id)

        dfs(start_entity_id, 0, [])
        return {"start_entity": start_entity_id, "paths": path}

    def extract_relationships_from_text(self, text: str, source: str = "text_extraction") -> List[Relationship]:
        """Extract relationships from text using pattern matching."""
        relationships = []
        text_lower = text.lower()

        for rel_type, patterns in self.relationship_patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, text_lower)
                for match in matches:
                    if isinstance(match, tuple) and len(match) == 2:
                        entity1, entity2 = match

                        # Create entities if they don't exist
                        entity1_id = self._get_or_create_entity_id(entity1, "extracted_entity", source)
                        entity2_id = self._get_or_create_entity_id(entity2, "extracted_entity", source)

                        # Create relationship
                        rel_id = f"rel_{entity1_id}_{rel_type}_{entity2_id}"
                        if rel_id not in self.relationships:
                            relationship = Relationship(
                                id=rel_id,
                                source_id=entity1_id,
                                target_id=entity2_id,
                                type=rel_type,
                                properties={"extracted_from": text[:100]},
                                confidence=0.7,  # Lower confidence for extracted relationships
                                source=source,
                            )
                            relationships.append(relationship)
                            self.add_relationship(relationship)

        return relationships

    def _get_or_create_entity_id(self, label: str, entity_type: str, source: str) -> str:
        """Get existing entity ID or create a new entity."""
        # Check if entity already exists
        existing_entities = self.find_entities_by_label(label)
        if existing_entities:
            return existing_entities[0].id

        # Create new entity
        entity_id = f"entity_{hashlib.md5(label.encode()).hexdigest()[:8]}"
        entity = Entity(id=entity_id, label=label, entity_type=entity_type, source=source)
        self.add_entity(entity)
        return entity_id

    def semantic_search(self, query: str, top_k: int = 5) -> List[Tuple[Entity, float]]:
        """Perform semantic search across the knowledge graph."""
        query_lower = query.lower()
        scored_entities = []

        for entity in self.entities.values():
            score = 0.0

            # Label matching
            if query_lower in entity.label.lower():
                score += 1.0
            elif entity.label.lower() in query_lower:
                score += 0.8

            # Property matching
            for prop_value in entity.properties.values():
                if isinstance(prop_value, str) and query_lower in prop_value.lower():
                    score += 0.5

            # Type relevance
            if entity.entity_type in query_lower:
                score += 0.3

            if score > 0:
                scored_entities.append((entity, score))

        # Sort by score and return top_k
        scored_entities.sort(key=lambda x: x[1], reverse=True)
        return scored_entities[:top_k]

    def get_graph_statistics(self) -> Dict[str, Any]:
        """Get knowledge graph statistics."""
        entity_types = defaultdict(int)
        relationship_types = defaultdict(int)

        for entity in self.entities.values():
            entity_types[entity.entity_type] += 1

        for relationship in self.relationships.values():
            relationship_types[relationship.type] += 1

        return {
            "total_entities": len(self.entities),
            "total_relationships": len(self.relationships),
            "entity_types": dict(entity_types),
            "relationship_types": dict(relationship_types),
            "avg_relationships_per_entity": len(self.relationships) / max(len(self.entities), 1),
        }

    def save_to_file(self, filepath: str) -> None:
        """Save knowledge graph to JSON file."""
        data = {
            "entities": [entity.to_dict() for entity in self.entities.values()],
            "relationships": [rel.to_dict() for rel in self.relationships.values()],
        }

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def load_from_file(self, filepath: str) -> None:
        """Load knowledge graph from JSON file."""
        with open(filepath, "r") as f:
            data = json.load(f)

        # Load entities
        for entity_data in data.get("entities", []):
            entity = Entity(**entity_data)
            self.add_entity(entity)

        # Load relationships
        for rel_data in data.get("relationships", []):
            relationship = Relationship(**rel_data)
            self.add_relationship(relationship)

    def find_related_entities(
        self, entity_id: str, relationship_types: Optional[List[str]] = None, max_depth: int = 2
    ) -> List[Tuple[Entity, str]]:
        """Find entities related to the given entity within specified depth."""
        visited = set()
        related = []

        def dfs(current_id: str, depth: int, relationship_path: str):
            if depth > max_depth or current_id in visited:
                return

            visited.add(current_id)

            if depth > 0 and current_id != entity_id:  # Don't include self
                entity = self.entities.get(current_id)
                if entity:
                    related.append((entity, relationship_path))

            # Explore relationships
            relationships = self.get_entity_relationships(current_id)
            for rel in relationships:
                if relationship_types is None or rel.type in relationship_types:
                    next_id = rel.target_id if rel.source_id == current_id else rel.source_id
                    next_path = f"{relationship_path} -> {rel.type}" if relationship_path else rel.type
                    dfs(next_id, depth + 1, next_path)

        dfs(entity_id, 0, "")
        return related

    def infer_relationships(self, entity1_id: str, entity2_id: str) -> List[Dict[str, Any]]:
        """Infer possible relationships between two entities based on graph patterns."""
        inferences = []

        # Check for common neighbors (triangles)
        entity1_neighbors = set()
        entity2_neighbors = set()

        for rel in self.get_entity_relationships(entity1_id):
            neighbor_id = rel.target_id if rel.source_id == entity1_id else rel.source_id
            entity1_neighbors.add((neighbor_id, rel.type))

        for rel in self.get_entity_relationships(entity2_id):
            neighbor_id = rel.target_id if rel.source_id == entity2_id else rel.source_id
            entity2_neighbors.add((neighbor_id, rel.type))

        # Find common neighbors
        common_neighbors = entity1_neighbors & entity2_neighbors
        for neighbor_id, rel_type in common_neighbors:
            neighbor = self.entities.get(neighbor_id)
            if neighbor:
                inferences.append(
                    {
                        "type": "common_connection",
                        "relationship": f"both_connected_to_{neighbor.label}",
                        "confidence": 0.6,
                        "evidence": f"Both entities connected to {neighbor.label} via {rel_type}",
                    }
                )

        # Check for transitive relationships
        paths = self.find_paths(entity1_id, entity2_id, max_length=3)
        for path in paths:
            if len(path) > 2:  # More than direct connection
                inferences.append(
                    {
                        "type": "transitive_relationship",
                        "relationship": "indirectly_connected",
                        "confidence": 0.4,
                        "evidence": f"Connected through path: {' -> '.join(path)}",
                    }
                )

        return inferences

    def find_paths(self, start_id: str, end_id: str, max_length: int = 3) -> List[List[str]]:
        """Find all paths between two entities up to max_length."""
        paths = []

        def dfs(current_id: str, target_id: str, path: List[str], visited: set):
            if len(path) > max_length:
                return

            if current_id == target_id and len(path) > 1:
                paths.append(path.copy())
                return

            visited.add(current_id)

            relationships = self.get_entity_relationships(current_id)
            for rel in relationships:
                next_id = rel.target_id if rel.source_id == current_id else rel.source_id
                if next_id not in visited:
                    path.append(rel.type)
                    dfs(next_id, target_id, path, visited)
                    path.pop()

            visited.remove(current_id)

        dfs(start_id, end_id, [start_id], set())
        return paths

    def cluster_entities(self, similarity_threshold: float = 0.7) -> List[List[Entity]]:
        """Cluster entities based on shared relationships and properties."""
        clusters = []
        processed = set()

        for entity_id, entity in self.entities.items():
            if entity_id in processed:
                continue

            cluster = [entity]
            processed.add(entity_id)

            # Find similar entities
            for other_id, other_entity in self.entities.items():
                if other_id in processed:
                    continue

                similarity = self.calculate_entity_similarity(entity_id, other_id)
                if similarity >= similarity_threshold:
                    cluster.append(other_entity)
                    processed.add(other_id)

            if len(cluster) > 1:  # Only include clusters with multiple entities
                clusters.append(cluster)

        return clusters

    def calculate_entity_similarity(self, entity1_id: str, entity2_id: str) -> float:
        """Calculate similarity between two entities."""
        if entity1_id not in self.entities or entity2_id not in self.entities:
            return 0.0

        entity1 = self.entities[entity1_id]
        entity2 = self.entities[entity2_id]

        similarity = 0.0
        factors = 0

        # Type similarity
        if entity1.entity_type == entity2.entity_type:
            similarity += 0.3
        factors += 0.3

        # Shared properties
        shared_props = set(entity1.properties.keys()) & set(entity2.properties.keys())
        if shared_props:
            prop_similarity = len(shared_props) / max(len(entity1.properties), len(entity2.properties))
            similarity += prop_similarity * 0.3
            factors += 0.3

        # Shared relationships
        rel1 = set(self.outgoing_relationships.get(entity1_id, set()))
        rel2 = set(self.outgoing_relationships.get(entity2_id, set()))
        shared_rels = rel1 & rel2
        if shared_rels:
            rel_similarity = len(shared_rels) / max(len(rel1), len(rel2))
            similarity += rel_similarity * 0.4
            factors += 0.4

        return similarity / factors if factors > 0 else 0.0
