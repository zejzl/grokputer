"""
Test Redis Memory Backend
"""

import pytest
from unittest.mock import Mock, patch
from src.memory.backends.redis_store import RedisMemoryBackend
from src.memory.interfaces import MemoryConfig


@pytest.fixture
def redis_config():
    return MemoryConfig(backend="redis", redis_url="redis://localhost:6379/0")


def test_redis_backend_init(redis_config):
    """Test Redis backend initialization."""
    with patch("redis.from_url") as mock_redis:
        mock_client = Mock()
        mock_redis.return_value = mock_client
        mock_client.ping.return_value = True

        backend = RedisMemoryBackend(redis_config)

        mock_redis.assert_called_once_with("redis://localhost:6379/0", decode_responses=True)
        mock_client.ping.assert_called_once()
        assert backend.redis_client == mock_client


def test_redis_backend_connection_failure(redis_config):
    """Test graceful handling of Redis connection failure."""
    with patch("redis.from_url") as mock_redis:
        mock_client = Mock()
        mock_redis.return_value = mock_client
        mock_client.ping.side_effect = Exception("Connection failed")

        backend = RedisMemoryBackend(redis_config)

        assert backend.redis_client is None


def test_store_episode_success(redis_config):
    """Test storing episode when Redis is available."""
    with patch("redis.from_url") as mock_redis:
        mock_client = Mock()
        mock_redis.return_value = mock_client
        mock_client.ping.return_value = True
        mock_client.incr.return_value = 1
        mock_client.time.return_value = (1234567890, 0)

        backend = RedisMemoryBackend(redis_config)
        episode_data = {"task": "test", "success": True}

        backend.store_episode("agent1", episode_data)

        mock_client.incr.assert_called_once_with("counter:agent1")
        mock_client.set.assert_called_once()
        mock_client.zadd.assert_called_once_with("episodes:agent1", {"episode:agent1:1": 1234567890})


def test_store_episode_no_connection(redis_config):
    """Test storing episode when Redis is unavailable."""
    with patch("redis.from_url") as mock_redis:
        mock_client = Mock()
        mock_redis.return_value = mock_client
        mock_client.ping.side_effect = Exception("Connection failed")

        backend = RedisMemoryBackend(redis_config)
        episode_data = {"task": "test", "success": True}

        # Should not raise exception
        backend.store_episode("agent1", episode_data)

        # No Redis calls should be made
        mock_client.incr.assert_not_called()


def test_retrieve_context_success(redis_config):
    """Test retrieving context when Redis is available."""
    with patch("redis.from_url") as mock_redis:
        mock_client = Mock()
        mock_redis.return_value = mock_client
        mock_client.ping.return_value = True
        mock_client.zrevrange.return_value = ["episode:agent1:1"]
        mock_client.get.return_value = '{"task": "test", "success": true}'

        backend = RedisMemoryBackend(redis_config)

        result = backend.retrieve_context("agent1", top_k=1)

        assert len(result) == 1
        assert result[0]["task"] == "test"
        assert result[0]["success"] is True


def test_retrieve_context_no_connection(redis_config):
    """Test retrieving context when Redis is unavailable."""
    with patch("redis.from_url") as mock_redis:
        mock_client = Mock()
        mock_redis.return_value = mock_client
        mock_client.ping.side_effect = Exception("Connection failed")

        backend = RedisMemoryBackend(redis_config)

        result = backend.retrieve_context("agent1")

        assert result == []
