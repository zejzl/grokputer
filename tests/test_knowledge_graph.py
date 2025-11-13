"""
Unit tests for knowledge graph.
"""

import pytest
from unittest.mock import patch, MagicMock
from src.knowledge_graph import KnowledgeGraph, Entity, Relationship


class TestKnowledgeGraph:
    def test_initialization(self):
        """Test knowledge graph initialization."""
        kg = KnowledgeGraph()
        assert kg is not None
        assert len(kg.entities) == 0
        assert len(kg.relationships) == 0

    def test_add_entity(self):
        """Test adding an entity."""
        kg = KnowledgeGraph()

        entity = Entity(id="alice_001", label="Alice", entity_type="person", properties={"age": 30})
        kg.add_entity(entity)

        # Check if added
        assert "alice_001" in kg.entities
        assert kg.entities["alice_001"].label == "Alice"
        assert kg.entities["alice_001"].properties["age"] == 30

    def test_add_relationship(self):
        """Test adding a relationship."""
        kg = KnowledgeGraph()

        alice = Entity(id="alice_001", label="Alice", entity_type="person")
        bob = Entity(id="bob_001", label="Bob", entity_type="person")

        kg.add_entity(alice)
        kg.add_entity(bob)

        relationship = Relationship(
            id="alice_knows_bob", source_id="alice_001", target_id="bob_001", type="knows", properties={"since": 2020}
        )
        kg.add_relationship(relationship)

        # Check if added
        assert len(kg.relationships) == 1
        assert "alice_knows_bob" in kg.relationships

    def test_find_entities_by_type(self):
        """Test finding entities by type."""
        kg = KnowledgeGraph()

        alice = Entity(id="alice_001", label="Alice", entity_type="person")
        bob = Entity(id="bob_001", label="Bob", entity_type="person")
        cat = Entity(id="whiskers_001", label="Whiskers", entity_type="animal")

        kg.add_entity(alice)
        kg.add_entity(bob)
        kg.add_entity(cat)

        persons = kg.find_entities_by_type("person")
        assert len(persons) == 2
        assert all(p.entity_type == "person" for p in persons)

    def test_find_entities_by_label(self):
        """Test finding entities by label."""
        kg = KnowledgeGraph()

        alice = Entity(id="alice_001", label="Alice", entity_type="person")
        kg.add_entity(alice)

        found = kg.find_entities_by_label("Alice")
        assert len(found) == 1
        assert found[0].id == "alice_001"

    def test_semantic_search(self):
        """Test semantic search functionality."""
        kg = KnowledgeGraph()

        alice = Entity(id="alice_001", label="Alice", entity_type="person", properties={"occupation": "developer"})
        kg.add_entity(alice)

        results = kg.semantic_search("developer", top_k=5)
        assert len(results) > 0
        assert results[0][0].id == "alice_001"

    def test_relationship_extraction(self):
        """Test extracting relationships from text."""
        kg = KnowledgeGraph()

        text = "Alice is a developer. Alice knows Bob. Bob has a cat."
        relationships = kg.extract_relationships_from_text(text, "test")

        # Should extract some relationships
        assert len(relationships) > 0

        # Check that entities were created
        assert len(kg.entities) > 0

    def test_graph_statistics(self):
        """Test getting graph statistics."""
        kg = KnowledgeGraph()

        alice = Entity(id="alice_001", label="Alice", entity_type="person")
        bob = Entity(id="bob_001", label="Bob", entity_type="person")

        kg.add_entity(alice)
        kg.add_entity(bob)

        relationship = Relationship(id="alice_knows_bob", source_id="alice_001", target_id="bob_001", type="knows")
        kg.add_relationship(relationship)

        stats = kg.get_graph_statistics()
        assert stats["total_entities"] == 2
        assert stats["total_relationships"] == 1
        assert "person" in stats["entity_types"]
        assert "knows" in stats["relationship_types"]

    def test_save_load(self, tmp_path):
        """Test saving and loading knowledge graph."""
        kg = KnowledgeGraph()

        alice = Entity(id="alice_001", label="Alice", entity_type="person")
        kg.add_entity(alice)

        # Save
        filepath = tmp_path / "test_graph.json"
        kg.save_to_file(str(filepath))

        # Load into new graph
        kg2 = KnowledgeGraph()
        kg2.load_from_file(str(filepath))

        # Check loaded data
        assert len(kg2.entities) == 1
        assert "alice_001" in kg2.entities

    def test_traverse_graph(self):
        """Test graph traversal functionality."""
        kg = KnowledgeGraph()

        alice = Entity(id="alice_001", label="Alice", entity_type="person")
        bob = Entity(id="bob_001", label="Bob", entity_type="person")
        charlie = Entity(id="charlie_001", label="Charlie", entity_type="person")

        kg.add_entity(alice)
        kg.add_entity(bob)
        kg.add_entity(charlie)

        # Add relationships
        knows_ab = Relationship(id="alice_knows_bob", source_id="alice_001", target_id="bob_001", type="knows")
        knows_bc = Relationship(id="bob_knows_charlie", source_id="bob_001", target_id="charlie_001", type="knows")

        kg.add_relationship(knows_ab)
        kg.add_relationship(knows_bc)

        # Traverse from Alice
        traversal = kg.traverse_graph("alice_001", max_depth=2)
        assert traversal["start_entity"] == "alice_001"
        assert len(traversal["paths"]) > 0

    def test_bidirectional_relationships(self):
        """Test bidirectional relationship handling."""
        kg = KnowledgeGraph()

        alice = Entity(id="alice_001", label="Alice", entity_type="person")
        bob = Entity(id="bob_001", label="Bob", entity_type="person")

        kg.add_entity(alice)
        kg.add_entity(bob)

        # Add bidirectional relationship
        friends = Relationship(
            id="alice_friends_bob", source_id="alice_001", target_id="bob_001", type="friends", bidirectional=True
        )
        kg.add_relationship(friends)

        # Check both directions
        assert len(kg.relationships) == 2  # Original + reverse
        assert "alice_friends_bob" in kg.relationships
        assert "alice_friends_bob_reverse" in kg.relationships

    def test_relationship_extraction_edge_cases(self):
        """Test relationship extraction with edge cases."""
        kg = KnowledgeGraph()

        # Test with empty text
        relationships = kg.extract_relationships_from_text("", "test")
        assert len(relationships) == 0

        # Test with text that doesn't match patterns
        relationships = kg.extract_relationships_from_text("The quick brown fox jumps over the lazy dog.", "test")
        assert len(relationships) == 0

        # Test with valid patterns
        text = "Alice is a developer. Alice works with Bob. Bob has a project."
        relationships = kg.extract_relationships_from_text(text, "test")
        assert len(relationships) > 0

    def test_semantic_search_edge_cases(self):
        """Test semantic search with various queries."""
        kg = KnowledgeGraph()

        alice = Entity(
            id="alice_001",
            label="Alice",
            entity_type="person",
            properties={"occupation": "developer", "location": "New York"},
        )
        kg.add_entity(alice)

        # Test exact match
        results = kg.semantic_search("developer", top_k=5)
        assert len(results) > 0
        assert results[0][0].id == "alice_001"

        # Test property match
        results = kg.semantic_search("New York", top_k=5)
        assert len(results) > 0

        # Test no match
        results = kg.semantic_search("nonexistent", top_k=5)
        assert len(results) == 0

    def test_get_entity_relationships(self):
        """Test getting relationships for a specific entity."""
        kg = KnowledgeGraph()

        alice = Entity(id="alice_001", label="Alice", entity_type="person")
        bob = Entity(id="bob_001", label="Bob", entity_type="person")

        kg.add_entity(alice)
        kg.add_entity(bob)

        # Add relationships
        knows = Relationship(id="alice_knows_bob", source_id="alice_001", target_id="bob_001", type="knows")
        kg.add_relationship(knows)

        # Test outgoing relationships
        outgoing = kg.get_entity_relationships("alice_001", direction="outgoing")
        assert len(outgoing) == 1
        assert outgoing[0].id == "alice_knows_bob"

        # Test incoming relationships
        incoming = kg.get_entity_relationships("bob_001", direction="incoming")
        assert len(incoming) == 1

        # Test both directions
        both = kg.get_entity_relationships("alice_001", direction="both")
        assert len(both) == 1
