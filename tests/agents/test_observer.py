"""
Unit tests for Observer agent.

Tests screenshot capture, caching, and Grok integration with mocks.
"""

import pytest
import pytest_asyncio
import asyncio
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from PIL import Image

from src.agents.observer import Observer, ScreenshotCache
from src.core.message_bus import MessageBus, Message, MessagePriority
from src.observability.session_logger import SessionLogger


@pytest.fixture
def session_logger():
    """Create SessionLogger mock."""
    logger = Mock(spec=SessionLogger)
    logger.log_tool_execution = Mock()
    logger.log_agent_error = Mock()
    return logger


@pytest.fixture
def message_bus():
    """Create MessageBus instance."""
    return MessageBus()


@pytest.fixture
def mock_screen_observer():
    """Mock ScreenObserver to avoid actual screenshots."""
    with patch('src.agents.observer.ScreenObserver') as mock:
        instance = mock.return_value
        instance.screenshot_to_base64 = Mock(return_value="base64_screenshot_data")
        instance.get_screen_size = Mock(return_value=(1920, 1080))
        yield instance


@pytest.fixture
def mock_grok_client():
    """Mock GrokClient to avoid actual API calls."""
    with patch('src.agents.observer.GrokClient') as mock:
        instance = mock.return_value
        instance.create_message = Mock(return_value={
            "status": "success",
            "content": "This is a test screen showing desktop.",
            "model": "grok-vision-beta",
            "finish_reason": "stop"
        })
        instance.test_connection = Mock(return_value=True)
        yield instance


@pytest_asyncio.fixture
async def observer(message_bus, session_logger, mock_screen_observer, mock_grok_client):
    """Create Observer instance with mocked dependencies."""
    config = {
        "screenshot_quality": 85,
        "max_screenshot_width": 1920,
        "max_screenshot_height": 1080,
        "screenshot_cache_size": 5
    }

    obs = Observer(message_bus, session_logger, config, heartbeat_interval=30.0)
    yield obs

    # Cleanup
    if obs.running:
        await obs.stop()


def test_screenshot_cache_basic():
    """Test ScreenshotCache basic operations."""
    cache = ScreenshotCache(max_size=3)
    
    # Add entries
    cache.put("hash1", "screenshot1", {"content": "analysis1"})
    cache.put("hash2", "screenshot2", {"content": "analysis2"})
    
    # Retrieve
    entry1 = cache.get("hash1")
    assert entry1 is not None
    assert entry1['screenshot'] == "screenshot1"
    assert entry1['analysis']['content'] == "analysis1"
    
    # Non-existent
    entry_none = cache.get("nonexistent")
    assert entry_none is None


def test_screenshot_cache_eviction():
    """Test ScreenshotCache evicts oldest entries."""
    cache = ScreenshotCache(max_size=2)
    
    cache.put("hash1", "screenshot1", {"content": "analysis1"})
    cache.put("hash2", "screenshot2", {"content": "analysis2"})
    cache.put("hash3", "screenshot3", {"content": "analysis3"})  # Should evict hash1
    
    assert cache.get("hash1") is None  # Evicted
    assert cache.get("hash2") is not None
    assert cache.get("hash3") is not None


@pytest.mark.asyncio
async def test_observer_initialization(observer):
    """Test Observer initialization."""
    assert observer.agent_id == "observer"
    assert observer.cache is not None
    assert observer.stats["screenshots_captured"] == 0
    assert observer.stats["cache_hits"] == 0


@pytest.mark.asyncio
async def test_observer_capture_screenshot(observer):
    """Test screenshot capture."""
    screenshot_b64 = await observer._capture_screenshot()
    
    assert screenshot_b64 == "base64_screenshot_data"
    observer.screen_observer.screenshot_to_base64.assert_called_once()


@pytest.mark.asyncio
async def test_observer_cache_hit(observer):
    """Test Observer cache hit behavior."""
    # First capture (cache miss)
    message1 = Message(
        from_agent="coordinator",
        to_agent="observer",
        message_type="subtask",
        content={
            "task_id": "task1",
            "action": "capture_screen",
            "params": {}
        }
    )
    
    response1 = await observer._handle_subtask(message1)
    
    assert response1['content']['status'] == "success"
    assert observer.stats["cache_misses"] == 1
    assert observer.stats["screenshots_captured"] == 1
    
    # Second capture with same screen (cache hit)
    message2 = Message(
        from_agent="coordinator",
        to_agent="observer",
        message_type="subtask",
        content={
            "task_id": "task2",
            "action": "capture_screen",
            "params": {}
        }
    )
    
    response2 = await observer._handle_subtask(message2)
    
    assert response2['content']['status'] == "success"
    assert response2['content']['result']['from_cache'] is True
    assert observer.stats["cache_hits"] == 1


@pytest.mark.asyncio
async def test_observer_get_stats(observer):
    """Test Observer statistics."""
    # Simulate capture
    observer.stats["screenshots_captured"] = 5
    observer.stats["cache_hits"] = 2
    observer.stats["cache_misses"] = 3
    observer.stats["grok_calls"] = 3
    observer.stats["total_capture_time"] = 1.0  # 1 second total
    observer.stats["total_analysis_time"] = 6.0  # 6 seconds total
    
    stats = observer.get_stats()
    
    assert stats["screenshots_captured"] == 5
    assert stats["cache_hit_rate"] == "40.0%"
    assert stats["avg_capture_time_ms"] == 200  # 1000ms / 5
    assert stats["avg_analysis_time_ms"] == 2000  # 6000ms / 3
