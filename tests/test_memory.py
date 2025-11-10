import pytest
from unittest.mock import Mock, patch
from src.memory.interfaces import MemoryConfig
from src.memory.managers.persistent_manager import PersistentMemoryManager
from src.memory.backends.redis_store import RedisStore
from src.memory.backends.pinecone_store import PineconeStore
from typing import Dict, Any, List

@pytest.fixture
def memory_config():
    return MemoryConfig(redis_url="redis://localhost:6379", pinecone_key="mock_key")

@pytest.fixture
def mock_redis_client():
    client = Mock()
    client.keys.return_value = b"mock_keys"
    client.hgetall.return_value = b"mock_data"
    return client

@pytest.fixture
def mock_pinecone_index():
    index = Mock()
    index.upsert.return_value = None
    index.query.return_value = {"matches": [{"metadata": {"test": "data"}}]}
    return index

def test_persistent_memory_manager_init(memory_config):
    manager = PersistentMemoryManager(memory_config)
    assert isinstance(manager.kv_store, RedisStore)
    assert isinstance(manager.vector_store, PineconeStore)

@patch('src.memory.backends.redis_store.redis')
def test_store_episode(mock_redis, memory_config):
    mock_redis.from_url.return_value = Mock(keys=lambda p: [], hset=lambda k, m: None, expire=lambda k, t: None)
    manager = PersistentMemoryManager(memory_config)
    
    data = {"action": "test", "outcome": "success"}
    manager.store_episode("test_agent", data)
    
    mock_redis.from_url.return_value.hset.assert_called_once()
    assert mock_redis.from_url.return_value.keys.called

@patch('src.memory.backends.pinecone_store.pinecone')
@patch('src.memory.backends.pinecone_store.SentenceTransformer')
def test_retrieve_context_vector(mock_embedder, mock_pinecone, memory_config):
    mock_client = Mock()
    mock_pinecone.Index.return_value = mock_client
    mock_embedder.return_value.encode.return_value.tolist.return_value = [0.1, 0.2]
    
    manager = PersistentMemoryManager(memory_config)
    context = manager.retrieve_context("test_agent", query="test query", top_k=1)
    
    mock_client.query.assert_called_once()
    assert len(context) == 1

def test_consolidate(memory_config):
    # Requires actual Redis for full test, but mock simple case
    with patch('src.memory.managers.persistent_manager.PersistentMemoryManager.store_episode'):
        manager = PersistentMemoryManager(memory_config)
        # Mock episodes
        manager.kv_store.client.keys.return_value = []
        consolidated = manager.consolidate("test_agent")
        assert consolidated == {}