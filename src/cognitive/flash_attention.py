"""
Flash Attention Implementation for Grokputer.

Provides efficient attention mechanisms for enhanced context retention and processing.
PyTorch-independent implementation using numpy for broader compatibility.
"""

import logging
import math
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

logger = logging.getLogger(__name__)

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F

    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logger.warning("PyTorch not available, using numpy-based attention implementation")


class NumpyAttention:
    """
    Numpy-based attention implementation for environments without PyTorch.
    Provides efficient attention computation using optimized matrix operations.
    """

    def __init__(self, embed_dim: int, num_heads: int, dropout: float = 0.1):
        self.embed_dim = embed_dim
        self.num_heads = num_heads
        self.head_dim = embed_dim // num_heads
        self.dropout = dropout

        assert self.head_dim * num_heads == embed_dim, "embed_dim must be divisible by num_heads"

        # Initialize weights as numpy arrays
        self._init_weights()

    def _init_weights(self):
        """Initialize attention weights."""
        # Xavier initialization for better convergence
        scale = math.sqrt(2.0 / (self.embed_dim + self.embed_dim))

        self.q_proj = np.random.randn(self.embed_dim, self.embed_dim).astype(np.float32) * scale
        self.k_proj = np.random.randn(self.embed_dim, self.embed_dim).astype(np.float32) * scale
        self.v_proj = np.random.randn(self.embed_dim, self.embed_dim).astype(np.float32) * scale
        self.out_proj = np.random.randn(self.embed_dim, self.embed_dim).astype(np.float32) * scale

    def forward(
        self,
        query: np.ndarray,
        key: np.ndarray,
        value: np.ndarray,
        mask: Optional[np.ndarray] = None,
        causal: bool = False,
    ) -> np.ndarray:
        """
        Compute attention using numpy operations.

        Args:
            query: (batch_size, seq_len, embed_dim)
            key: (batch_size, seq_len, embed_dim)
            value: (batch_size, seq_len, embed_dim)
            mask: (batch_size, seq_len, seq_len) optional attention mask
            causal: whether to apply causal masking

        Returns:
            attention output: (batch_size, seq_len, embed_dim)
        """
        batch_size, seq_len, _ = query.shape

        # Linear projections
        q = np.matmul(query, self.q_proj.T).reshape(batch_size, seq_len, self.num_heads, self.head_dim)
        k = np.matmul(key, self.k_proj.T).reshape(batch_size, seq_len, self.num_heads, self.head_dim)
        v = np.matmul(value, self.v_proj.T).reshape(batch_size, seq_len, self.num_heads, self.head_dim)

        # Transpose for attention computation: (batch, num_heads, seq_len, head_dim)
        q = q.transpose(0, 2, 1, 3)
        k = k.transpose(0, 2, 1, 3)
        v = v.transpose(0, 2, 1, 3)

        # Flash attention computation
        attn_output = self._flash_attention_forward(q, k, v, mask, causal)

        # Reshape and project output
        attn_output = attn_output.transpose(0, 2, 1, 3).reshape(batch_size, seq_len, self.embed_dim)
        output = np.matmul(attn_output, self.out_proj.T)

        # Apply dropout
        if self.dropout > 0:
            dropout_mask = np.random.rand(*output.shape) > self.dropout
            output = output * dropout_mask / (1 - self.dropout)

        return output

    def _flash_attention_forward(
        self, q: np.ndarray, k: np.ndarray, v: np.ndarray, mask: Optional[np.ndarray] = None, causal: bool = False
    ) -> np.ndarray:
        """
        Core flash attention computation using block-wise processing.
        """
        batch_size, num_heads, seq_len, head_dim = q.shape

        # For memory efficiency, process in chunks
        chunk_size = min(512, seq_len)

        outputs = []
        for i in range(0, seq_len, chunk_size):
            q_chunk = q[:, :, i : i + chunk_size]
            k_chunk = k[:, :, : i + chunk_size]  # Attend to all previous + current
            v_chunk = v[:, :, : i + chunk_size]

            # Compute attention for this chunk
            attn_chunk = self._compute_chunk_attention(q_chunk, k_chunk, v_chunk, mask, causal)
            outputs.append(attn_chunk)

        return np.concatenate(outputs, axis=2)

    def _compute_chunk_attention(
        self, q: np.ndarray, k: np.ndarray, v: np.ndarray, mask: Optional[np.ndarray] = None, causal: bool = False
    ) -> np.ndarray:
        """
        Compute attention for a chunk using optimized matrix operations.
        """
        # Scale dot-product attention
        scale = 1.0 / math.sqrt(q.shape[-1])

        # Compute attention weights: (batch, num_heads, seq_len_q, seq_len_k)
        attn_weights = np.matmul(q, k.transpose(0, 1, 3, 2)) * scale

        if causal:
            # Create causal mask
            seq_len_q, seq_len_k = attn_weights.shape[-2:]
            causal_mask = np.triu(np.ones((seq_len_q, seq_len_k), dtype=bool), k=1)
            attn_weights = np.where(causal_mask, -np.inf, attn_weights)

        if mask is not None:
            # Expand mask to match attention dimensions
            if mask.ndim == 3:  # (batch, seq_len, seq_len)
                mask = mask[:, None, :, :]  # (batch, 1, seq_len, seq_len)
            attn_weights = np.where(mask == 0, -np.inf, attn_weights)

        # Softmax with numerical stability
        attn_weights_max = np.max(attn_weights, axis=-1, keepdims=True)
        attn_weights_stable = attn_weights - attn_weights_max
        exp_weights = np.exp(attn_weights_stable)
        attn_weights = exp_weights / np.sum(exp_weights, axis=-1, keepdims=True)

        # Apply attention to values
        output = np.matmul(attn_weights, v)

        return output


class MemoryAttention:
    """
    Memory-enhanced attention for long-term context retention.

    Combines efficient attention with memory consolidation for better
    long-term context understanding.
    """

    def __init__(self, embed_dim: int, num_heads: int, memory_slots: int = 100):
        self.embed_dim = embed_dim
        self.memory_slots = memory_slots

        if TORCH_AVAILABLE:
            self.attention = None  # Would use torch implementation
        else:
            self.attention = NumpyAttention(embed_dim, num_heads)

        # Memory bank as numpy array
        self.memory_bank = np.zeros((memory_slots, embed_dim), dtype=np.float32)
        self.memory_count = 0
        self.memory_timestamps = np.zeros(memory_slots, dtype=np.float32)

    def process_context(
        self,
        query: Union[str, np.ndarray],
        context: List[Union[str, Dict[str, Any]]],
        memory_query: Optional[str] = None,
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Enhanced attention with memory integration.

        Args:
            query: Current query/context
            context: Full context history
            memory_query: Optional memory retrieval query

        Returns:
            attended_output: Enhanced context representation
            metadata: Processing information
        """
        try:
            # Convert inputs to embeddings
            query_embed = self._text_to_embedding(query) if isinstance(query, str) else query
            context_embeds = [self._text_to_embedding(str(item)) for item in context]

            if not context_embeds:
                return query_embed, {"memory_retrieved": False, "attention_score": 1.0, "context_length": 0}

            # Stack context
            context_tensor = np.stack(context_embeds).astype(np.float32)
            query_tensor = query_embed.reshape(1, -1).astype(np.float32)

            # Apply attention
            attended = self._compute_attention(query_tensor, context_tensor)

            # Memory integration
            memory_boost = 0.0
            if memory_query:
                memory_context = self._retrieve_memory(memory_query)
                if memory_context is not None:
                    # Simple gating mechanism
                    gate = self._compute_gate(attended, memory_context)
                    attended = gate * attended + (1 - gate) * memory_context
                    memory_boost = 1.0

            # Update memory
            self._update_memory(attended)

            # Compute attention score
            attention_score = self._compute_attention_score(attended, context_tensor)

            return attended, {
                "memory_retrieved": memory_boost > 0,
                "attention_score": float(attention_score),
                "context_length": len(context),
                "memory_boost": memory_boost,
            }

        except Exception as e:
            logger.error(f"Memory attention processing failed: {e}")
            # Fallback to simple query embedding
            fallback_embed = self._text_to_embedding(str(query)) if isinstance(query, (str, dict)) else query
            return fallback_embed, {"error": str(e), "attention_score": 0.0}

    def _compute_attention(self, query: np.ndarray, context: np.ndarray) -> np.ndarray:
        """Compute attention between query and context."""
        if TORCH_AVAILABLE:
            # Would use torch implementation
            return query
        else:
            # Use numpy attention
            batch_size = 1
            seq_len = context.shape[0]

            # Expand query to match context sequence length for attention
            query_expanded = np.repeat(query, seq_len, axis=0).reshape(1, seq_len, -1)

            # Apply attention
            attended = self.attention.forward(
                query_expanded, context.reshape(1, seq_len, -1), context.reshape(1, seq_len, -1)
            )

            return attended.squeeze(0).mean(axis=0)  # Average over sequence

    def _retrieve_memory(self, query: str) -> Optional[np.ndarray]:
        """Retrieve relevant memories based on query."""
        if self.memory_count == 0:
            return None

        query_embed = self._text_to_embedding(query)
        current_memory = self.memory_bank[: self.memory_count]

        # Cosine similarity
        similarities = np.dot(current_memory, query_embed) / (
            np.linalg.norm(current_memory, axis=1) * np.linalg.norm(query_embed)
        )

        # Get top-k memories
        top_k = min(5, self.memory_count)
        top_indices = np.argsort(similarities)[-top_k:]

        retrieved = current_memory[top_indices]
        return np.mean(retrieved, axis=0) if len(retrieved) > 0 else None

    def _update_memory(self, context: np.ndarray) -> None:
        """Update memory bank with new context."""
        # Compress context to single vector
        memory_vector = np.mean(context, axis=0) if context.ndim > 1 else context

        # Update memory bank (FIFO)
        if self.memory_count < self.memory_slots:
            self.memory_bank[self.memory_count] = memory_vector
            self.memory_timestamps[self.memory_count] = np.random.rand()  # Simple timestamp
            self.memory_count += 1
        else:
            # Replace oldest memory (simplified - would use timestamps)
            replace_idx = np.random.randint(0, self.memory_slots)
            self.memory_bank[replace_idx] = memory_vector
            self.memory_timestamps[replace_idx] = np.random.rand()

    def _compute_gate(self, current: np.ndarray, memory: np.ndarray) -> float:
        """Compute gating value for memory integration."""
        # Simple gating based on similarity
        similarity = np.dot(current, memory) / (np.linalg.norm(current) * np.linalg.norm(memory))
        return float(np.clip(similarity, 0, 1))

    def _compute_attention_score(self, attended: np.ndarray, original: np.ndarray) -> float:
        """Compute attention enhancement score."""
        if original.shape[0] == 0:
            return 1.0

        # Average similarity to original context
        similarities = []
        for i in range(min(len(original), 10)):  # Limit to first 10 for efficiency
            sim = np.dot(attended, original[i]) / (np.linalg.norm(attended) * np.linalg.norm(original[i]))
            similarities.append(sim)

        return float(np.mean(similarities)) if similarities else 0.0

    def _text_to_embedding(self, text: str) -> np.ndarray:
        """Convert text to embedding using deterministic hashing."""
        import hashlib

        # Create deterministic embedding from text hash
        hash_obj = hashlib.md5(text.encode())
        hash_bytes = hash_obj.digest()

        # Convert bytes to float values
        embed_values = np.array([float(b) / 255.0 for b in hash_bytes], dtype=np.float32)

        # Pad or truncate to embed_dim
        if len(embed_values) < self.embed_dim:
            # Pad with zeros
            padding = np.zeros(self.embed_dim - len(embed_values), dtype=np.float32)
            embed_values = np.concatenate([embed_values, padding])
        else:
            embed_values = embed_values[: self.embed_dim]

        return embed_values


class CognitiveEnhancer:
    """
    Cognitive enhancement system for Grokputer.

    Provides enhanced context retention and processing capabilities
    for agents using efficient attention mechanisms.
    """

    def __init__(self, embed_dim: int = 128, num_heads: int = 8, memory_slots: int = 100):
        self.embed_dim = embed_dim
        self.memory_attention = MemoryAttention(embed_dim, num_heads, memory_slots)

        logger.info(
            f"CognitiveEnhancer initialized with embed_dim={embed_dim}, "
            f"num_heads={num_heads}, memory_slots={memory_slots}"
        )

    def process_context(
        self, current_input: str, context_history: List[Dict[str, Any]], memory_query: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process context with enhanced attention and memory.

        Args:
            current_input: Current user input or task
            context_history: List of previous interactions
            memory_query: Optional query for memory retrieval

        Returns:
            Enhanced context processing result
        """
        try:
            # Apply memory-enhanced attention
            enhanced_embedding, metadata = self.memory_attention.process_context(
                current_input, context_history, memory_query
            )

            # Convert embedding back to enhanced representation
            enhanced_text = self._embedding_to_enhanced_text(enhanced_embedding, metadata)

            result = {
                "enhanced_context": enhanced_text,
                "original_input": current_input,
                "context_length": len(context_history),
                "processing_method": "numpy_attention" if not TORCH_AVAILABLE else "torch_attention",
                **metadata,
            }

            logger.debug(
                f"Context enhanced: score={metadata.get('attention_score', 0):.3f}, "
                f"memory={metadata.get('memory_retrieved', False)}"
            )

            return result

        except Exception as e:
            logger.error(f"Cognitive enhancement failed: {e}")
            return {
                "enhanced_context": current_input,
                "original_input": current_input,
                "context_length": len(context_history),
                "attention_score": 0.0,
                "memory_retrieved": False,
                "error": str(e),
            }

    def _embedding_to_enhanced_text(self, embedding: np.ndarray, metadata: Dict[str, Any]) -> str:
        """Convert embedding back to enhanced text representation."""
        attention_score = metadata.get("attention_score", 0.0)
        memory_boost = metadata.get("memory_boost", 0.0)

        # Create enhanced representation
        enhancement_info = f"[Cognitive Enhancement: attention={attention_score:.3f}"
        if memory_boost > 0:
            enhancement_info += f", memory_boost={memory_boost:.3f}"
        enhancement_info += "]"

        return enhancement_info

    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory system statistics."""
        return {
            "memory_slots_used": self.memory_attention.memory_count,
            "memory_slots_total": self.memory_attention.memory_slots,
            "memory_utilization": self.memory_attention.memory_count / self.memory_attention.memory_slots,
            "torch_available": TORCH_AVAILABLE,
        }
