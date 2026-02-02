from __future__ import annotations

import pytest
from unittest.mock import Mock, patch
from src.memory.interfaces import MemoryConfig
from src.memory.managers.persistent_manager import PersistentMemoryManager
from src.memory.backends.redis_store import RedisMemoryBackend

try:
    from src.memory.backends.pinecone_store import PineconeStore
except ImportError:
    PineconeStore = None
from typing import Dict, Any, List


@pytest.fixture
def memory_config(tmp_path):
    config = MemoryConfig(redis_url="redis://localhost:6379")
    config.db_path = str(tmp_path / "test_memory.db")
    return config


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
    assert hasattr(manager, "config")
    assert hasattr(manager, "db_path")
    assert manager.db_path.exists()


def test_store_episode(memory_config):
    manager = PersistentMemoryManager(memory_config)

    data = {"action": "test", "outcome": "success"}
    manager.store_episode("test_agent", data)

    # Verify data was stored
    context = manager.retrieve_context("test_agent", top_k=10)
    assert len(context) > 0
    assert context[0]["action"] == "test"


def test_retrieve_context_no_data(memory_config):
    manager = PersistentMemoryManager(memory_config)
    context = manager.retrieve_context("nonexistent_agent", top_k=1)
    assert len(context) == 0


def test_consolidate(memory_config):
    manager = PersistentMemoryManager(memory_config)
    # Test consolidate with no data
    consolidated = manager.consolidate("test_agent")
    assert consolidated["status"] == "no_data"
