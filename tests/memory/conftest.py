"""
Pytest fixtures for memory tests with Redis mocking.
"""

import pytest
from unittest.mock import Mock, MagicMock


@pytest.fixture
def mock_redis():
    """Mock Redis client for offline testing."""
    mock_client = MagicMock()
    mock_client.ping.return_value = True
    mock_client.set.return_value = True
    mock_client.get.return_value = '{"test": "data"}'
    mock_client.zadd.return_value = 1
    mock_client.zrevrange.return_value = []
    mock_client.incr.return_value = 1
    mock_client.time.return_value = (1699999999, 0)
    return mock_client


@pytest.fixture
def mock_redis_unavailable():
    """Mock unavailable Redis for testing graceful degradation."""
    mock_client = MagicMock()
    mock_client.ping.side_effect = ConnectionError("Redis unavailable")
    return mock_client
