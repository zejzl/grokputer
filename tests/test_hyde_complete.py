"""
Tests for HyDE (Hypothetical Document Embeddings) components.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from src.memory.hyde_generator import HyDEGenerator
from src.memory.backends.pinecone_store import PineconeStore
from src.memory.interfaces import MemoryConfig

# Skip Pinecone tests if not available
pytest.importorskip("pinecone", reason="Pinecone library not installed")


class TestHyDEGenerator:
    """Test HyDE generator functionality."""

    @pytest.fixture
    def hyde_generator(self):
        return HyDEGenerator(num_hypotheticals=2)

    @pytest.mark.asyncio
    async def test_generate_hypotheticals_success(self, hyde_generator):
        """Test successful hypothetical generation."""
        with patch.object(hyde_generator.client, 'chat', new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = "Document 1 content---Document 2 content"

            result = await hyde_generator.generate_hypotheticals("test query")

            assert len(result) == 2
            assert "Document 1 content" in result[0]
            assert "Document 2 content" in result[1]
            mock_chat.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_hypotheticals_error(self, hyde_generator):
        """Test error handling in hypothetical generation."""
        with patch.object(hyde_generator.client, 'chat', new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = "Error: API unavailable"

            result = await hyde_generator.generate_hypotheticals("test query")

            assert result == []
            mock_chat.assert_called_once()

    def test_generate_hypotheticals_sync(self, hyde_generator):
        """Test synchronous wrapper."""
        with patch.object(hyde_generator, 'generate_hypotheticals', new_callable=AsyncMock) as mock_async:
            mock_async.return_value = ["doc1", "doc2"]

            result = hyde_generator.generate_hypotheticals_sync("test")

            assert result == ["doc1", "doc2"]
            mock_async.assert_called_once()


class TestPineconeStore:
    """Test Pinecone store with HyDE."""

    @pytest.fixture
    def memory_config(self):
        config = MemoryConfig()
        config.pinecone_key = "test_key"
        config.pinecone_env = "test_env"
        config.pinecone_index = "test_index"
        config.enable_hyde = True
        return config

    @pytest.fixture
    def mock_pinecone(self):
        with patch('src.memory.backends.pinecone_store.pinecone') as mock_pine:
            mock_index = Mock()
            mock_pine.Index.return_value = mock_index
            mock_pine.init.return_value = None
            yield mock_pine, mock_index

    @pytest.fixture
    def mock_embedder(self):
        with patch('src.memory.backends.pinecone_store.SentenceTransformer') as mock_transformer:
            mock_embedder = Mock()
            mock_transformer.return_value = mock_embedder
            mock_embedder.encode.return_value = [0.1] * 384  # Mock embedding
            yield mock_embedder

    def test_pinecone_store_init_with_hyde(self, memory_config, mock_pinecone, mock_embedder):
        """Test PineconeStore initialization with HyDE enabled."""
        mock_pine, mock_index = mock_pinecone

        store = PineconeStore(memory_config)

        assert store.pinecone_available
        assert store.enable_hyde
        assert store.hyde_generator is not None
        assert store.index == mock_index

    def test_pinecone_store_init_hyde_disabled(self, memory_config, mock_pinecone, mock_embedder):
        """Test PineconeStore initialization with HyDE disabled."""
        memory_config.enable_hyde = False
        mock_pine, mock_index = mock_pinecone

        store = PineconeStore(memory_config)

        assert store.pinecone_available
        assert not store.enable_hyde
        assert store.hyde_generator is None

    def test_embed_and_store(self, memory_config, mock_pinecone, mock_embedder):
        """Test embedding and storing text."""
        mock_pine, mock_index = mock_pinecone
        mock_index.upsert.return_value = None

        store = PineconeStore(memory_config)
        vec_id = store.embed_and_store("test text", {"meta": "data"})

        assert vec_id.startswith("vec_")
        mock_embedder.encode.assert_called_with("test text")
        mock_index.upsert.assert_called_once()

    def test_query_similar_standard(self, memory_config, mock_pinecone, mock_embedder):
        """Test standard vector similarity search."""
        memory_config.enable_hyde = False
        mock_pine, mock_index = mock_pinecone
        mock_index.query.return_value = {
            "matches": [{"metadata": {"result": "data"}}]
        }

        store = PineconeStore(memory_config)
        results = store.query_similar("test query")

        assert len(results) == 1
        assert results[0] == {"result": "data"}
        mock_embedder.encode.assert_called_with("test query")

    @pytest.mark.asyncio
    async def test_query_similar_hyde(self, memory_config, mock_pinecone, mock_embedder):
        """Test HyDE-enhanced search."""
        mock_pine, mock_index = mock_pinecone
        mock_index.query.return_value = {
            "matches": [{"id": "1", "score": 0.9, "metadata": {"result": "data"}}]
        }

        store = PineconeStore(memory_config)

        # Mock HyDE generation
        with patch.object(store.hyde_generator, 'generate_hypotheticals_sync') as mock_hyde:
            mock_hyde.return_value = ["hypothetical doc 1", "hypothetical doc 2"]

            results = store.query_similar("test query")

            assert len(results) == 1
            mock_hyde.assert_called_with("test query")
            # Should call encode for each hypothetical
            assert mock_embedder.encode.call_count >= 2

    def test_store_episode(self, memory_config, mock_pinecone, mock_embedder):
        """Test storing episode as vector."""
        mock_pine, mock_index = mock_pinecone
        mock_index.upsert.return_value = None

        store = PineconeStore(memory_config)
        episode_data = {
            "type": "action",
            "content": "test action performed",
            "timestamp": 1234567890
        }

        store.store_episode("test_agent", episode_data)

        mock_index.upsert.assert_called_once()
        call_args = mock_index.upsert.call_args[1]["vectors"][0]
        assert "metadata" in call_args
        assert call_args["metadata"]["agent_id"] == "test_agent"

    def test_retrieve_context(self, memory_config, mock_pinecone, mock_embedder):
        """Test retrieving context."""
        mock_pine, mock_index = mock_pinecone
        mock_index.query.return_value = {
            "matches": [{"metadata": {"agent_id": "test_agent", "content": "test"}}]
        }

        store = PineconeStore(memory_config)
        results = store.retrieve_context("test_agent", "test query")

        assert len(results) == 1
        mock_index.query.assert_called_once()

    def test_consolidate(self, memory_config, mock_pinecone, mock_embedder):
        """Test memory consolidation."""
        store = PineconeStore(memory_config)
        stats = store.consolidate("test_agent")

        assert stats["status"] == "success"
        assert stats["agent_id"] == "test_agent"
        assert stats["hyde_enabled"] == True


class TestHyDEIntegration:
    """Test HyDE integration with hierarchical memory."""

    @pytest.fixture
    def memory_config(self):
        config = MemoryConfig()
        config.enable_hyde = True
        config.consolidation_threshold = 10
        return config

    @pytest.mark.asyncio
    async def test_hierarchical_memory_with_hyde(self, memory_config):
        """Test hierarchical memory with HyDE enabled."""
        from src.memory.hierarchical_memory import HierarchicalMemoryManager

        # Mock long-term backend
        mock_backend = Mock()
        mock_backend.retrieve_context = AsyncMock(return_value=[])

        manager = HierarchicalMemoryManager(memory_config, mock_backend)

        assert manager.hyde_generator is not None
        assert hasattr(manager, 'fusion_weights')
        assert 'hyde' in manager.fusion_weights

    @pytest.mark.asyncio
    async def test_retrieve_context_with_hyde(self, memory_config):
        """Test retrieve_context with HyDE results."""
        from src.memory.hierarchical_memory import HierarchicalMemoryManager

        mock_backend = Mock()
        mock_backend.retrieve_context = AsyncMock(return_value=[])

        manager = HierarchicalMemoryManager(memory_config, mock_backend)

        # Mock HyDE generation
        with patch.object(manager.hyde_generator, 'generate_hypotheticals', new_callable=AsyncMock) as mock_hyde:
            mock_hyde.return_value = ["hypothetical content"]

            results = await manager.retrieve_context("test_agent", "test query")

            # Should have called HyDE generator
            mock_hyde.assert_called_with("test query")
            # Results should include fusion scores
            assert isinstance(results, list)