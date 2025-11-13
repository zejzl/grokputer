"""
Tests for Cognitive Enhancement System
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch

from src.cognitive.flash_attention import CognitiveEnhancer, MemoryAttention, NumpyAttention


class TestNumpyAttention:
    """Test numpy-based attention implementation."""

    def test_attention_init(self):
        """Test attention initialization."""
        attention = NumpyAttention(embed_dim=64, num_heads=4)
        assert attention.embed_dim == 64
        assert attention.num_heads == 4
        assert attention.head_dim == 16

    def test_attention_forward(self):
        """Test attention forward pass."""
        attention = NumpyAttention(embed_dim=64, num_heads=4)

        # Create test inputs
        batch_size, seq_len, embed_dim = 2, 10, 64
        query = np.random.randn(batch_size, seq_len, embed_dim).astype(np.float32)
        key = np.random.randn(batch_size, seq_len, embed_dim).astype(np.float32)
        value = np.random.randn(batch_size, seq_len, embed_dim).astype(np.float32)

        # Forward pass
        output = attention.forward(query, key, value)

        assert output.shape == (batch_size, seq_len, embed_dim)
        assert not np.isnan(output).any()

    def test_attention_with_mask(self):
        """Test attention with attention mask."""
        attention = NumpyAttention(embed_dim=32, num_heads=2)

        batch_size, seq_len = 1, 5
        embed_dim = 32
        query = np.random.randn(batch_size, seq_len, embed_dim).astype(np.float32)
        key = np.random.randn(batch_size, seq_len, embed_dim).astype(np.float32)
        value = np.random.randn(batch_size, seq_len, embed_dim).astype(np.float32)

        # Create mask (mask out last 2 positions)
        mask = np.ones((batch_size, seq_len, seq_len), dtype=bool)
        mask[:, :, -2:] = False

        output = attention.forward(query, key, value, mask=mask)
        assert output.shape == (batch_size, seq_len, embed_dim)


class TestMemoryAttention:
    """Test memory-enhanced attention."""

    def test_memory_init(self):
        """Test memory attention initialization."""
        memory_attn = MemoryAttention(embed_dim=64, num_heads=4, memory_slots=10)
        assert memory_attn.embed_dim == 64
        assert memory_attn.memory_slots == 10
        assert memory_attn.memory_count == 0

    def test_memory_processing(self):
        """Test memory-enhanced context processing."""
        memory_attn = MemoryAttention(embed_dim=32, num_heads=2, memory_slots=5)

        # Test input
        query = "test query"
        context = [{"action": "test1"}, {"action": "test2"}]

        embedding, metadata = memory_attn.process_context(query, context)

        assert isinstance(embedding, np.ndarray)
        assert embedding.shape[-1] == 32  # embed_dim (last dimension)
        assert "attention_score" in metadata
        assert "memory_retrieved" in metadata
        assert metadata["context_length"] == 2

    def test_memory_update(self):
        """Test memory bank updates."""
        memory_attn = MemoryAttention(embed_dim=16, num_heads=1, memory_slots=3)

        # Add some context
        context1 = np.random.randn(16).astype(np.float32)
        context2 = np.random.randn(16).astype(np.float32)

        memory_attn._update_memory(context1)
        assert memory_attn.memory_count == 1

        memory_attn._update_memory(context2)
        assert memory_attn.memory_count == 2

    def test_memory_retrieval(self):
        """Test memory retrieval."""
        memory_attn = MemoryAttention(embed_dim=16, num_heads=1, memory_slots=5)

        # Add memory
        test_memory = np.random.randn(16).astype(np.float32)
        memory_attn.memory_bank[0] = test_memory
        memory_attn.memory_count = 1

        # Retrieve similar memory
        query = "test query"
        retrieved = memory_attn._retrieve_memory(query)

        assert retrieved is not None
        assert retrieved.shape == (16,)


class TestCognitiveEnhancer:
    """Test cognitive enhancement system."""

    def test_enhancer_init(self):
        """Test cognitive enhancer initialization."""
        enhancer = CognitiveEnhancer(embed_dim=64, num_heads=4, memory_slots=20)
        assert enhancer.embed_dim == 64
        assert enhancer.memory_attention.memory_slots == 20

    def test_context_processing(self):
        """Test full context processing."""
        enhancer = CognitiveEnhancer(embed_dim=32, num_heads=2, memory_slots=5)

        current_input = "analyze this data"
        context_history = [
            {"task": "previous analysis", "result": "success"},
            {"task": "data processing", "result": "completed"},
        ]

        result = enhancer.process_context(current_input, context_history)

        assert "enhanced_context" in result
        assert "attention_score" in result
        assert "memory_retrieved" in result
        assert result["context_length"] == 2
        assert result["original_input"] == current_input

    def test_empty_context(self):
        """Test processing with empty context."""
        enhancer = CognitiveEnhancer(embed_dim=16, num_heads=1, memory_slots=3)

        result = enhancer.process_context("test input", [])

        assert result["enhanced_context"] is not None
        assert result["context_length"] == 0
        assert result["attention_score"] == 1.0  # Default for empty context

    def test_memory_query(self):
        """Test processing with memory query."""
        enhancer = CognitiveEnhancer(embed_dim=16, num_heads=1, memory_slots=3)

        result = enhancer.process_context("current task", [{"previous": "work"}], memory_query="relevant memories")

        assert "memory_retrieved" in result
        assert isinstance(result["memory_retrieved"], bool)

    def test_error_handling(self):
        """Test error handling in processing."""
        enhancer = CognitiveEnhancer(embed_dim=16, num_heads=1, memory_slots=3)

        # Test with None input (should handle gracefully)
        result = enhancer.process_context(None, [])

        assert "error" in result or result["enhanced_context"] is not None

    def test_memory_stats(self):
        """Test memory statistics retrieval."""
        enhancer = CognitiveEnhancer(embed_dim=16, num_heads=1, memory_slots=10)

        stats = enhancer.get_memory_stats()

        assert "memory_slots_used" in stats
        assert "memory_slots_total" in stats
        assert "memory_utilization" in stats
        assert stats["memory_slots_total"] == 10
        assert 0 <= stats["memory_utilization"] <= 1


class TestCognitiveIntegration:
    """Test cognitive system integration."""

    def test_torch_availability(self):
        """Test torch availability detection."""
        # This test verifies the system works regardless of torch availability
        enhancer = CognitiveEnhancer(embed_dim=16, num_heads=1)

        # Should work even without torch
        result = enhancer.process_context("test", [])
        assert result is not None

    def test_deterministic_embedding(self):
        """Test that same input produces consistent embeddings."""
        enhancer1 = CognitiveEnhancer(embed_dim=16, num_heads=1)
        enhancer2 = CognitiveEnhancer(embed_dim=16, num_heads=1)

        input_text = "consistent test input"

        embed1 = enhancer1.memory_attention._text_to_embedding(input_text)
        embed2 = enhancer2.memory_attention._text_to_embedding(input_text)

        # Same input should produce same embedding
        np.testing.assert_array_equal(embed1, embed2)

    def test_attention_score_range(self):
        """Test that attention scores are in valid range."""
        enhancer = CognitiveEnhancer(embed_dim=16, num_heads=1, memory_slots=5)

        # Test various contexts
        test_cases = [
            ("test", []),
            ("test", [{"item": "one"}]),
            ("test", [{"item": "one"}, {"item": "two"}, {"item": "three"}]),
        ]

        for input_text, context in test_cases:
            result = enhancer.process_context(input_text, context)
            score = result["attention_score"]

            assert 0.0 <= score <= 1.0, f"Invalid attention score: {score}"
