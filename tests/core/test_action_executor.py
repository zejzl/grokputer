"""
Unit tests for ActionExecutor.

Tests PyAutoGUI wrapper with mocked PyAutoGUI to avoid
actual mouse/keyboard interactions during testing.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock
from PIL import Image
import io

from src.core.action_executor import (
    ActionExecutor,
    ActionPriority,
    Action,
    ActionHistory
)


@pytest.fixture
def mock_pyautogui():
    """Mock PyAutoGUI to prevent actual mouse/keyboard actions."""
    with patch('src.core.action_executor.pyautogui') as mock:
        # Mock screenshot
        mock_image = Image.new('RGB', (100, 100), color='red')
        mock.screenshot.return_value = mock_image

        yield mock


@pytest.fixture
def executor(mock_pyautogui):
    """Create ActionExecutor instance with mocked PyAutoGUI."""
    executor = ActionExecutor(max_queue_size=10, history_size=5)
    yield executor
    executor.shutdown()


def test_action_priority_ordering():
    """Test that Action priorities are ordered correctly."""
    high = Action("click", {"x": 0, "y": 0}, "agent1", "req1", ActionPriority.HIGH)
    normal = Action("click", {"x": 0, "y": 0}, "agent2", "req2", ActionPriority.NORMAL)
    low = Action("click", {"x": 0, "y": 0}, "agent3", "req3", ActionPriority.LOW)

    assert high < normal
    assert normal < low
    assert high < low


@pytest.mark.asyncio
async def test_single_click_action(executor, mock_pyautogui):
    """Test single click action execution."""
    result = await executor.execute_async(
        agent_id="test_agent",
        action={"type": "click", "x": 100, "y": 200}
    )

    assert result["status"] == "success"
    assert result["action"] == "click"
    assert result["coords"] == (100, 200)

    # Verify PyAutoGUI was called
    mock_pyautogui.click.assert_called_once_with(100, 200, button="left", clicks=1)


@pytest.mark.asyncio
async def test_type_action(executor, mock_pyautogui):
    """Test keyboard typing action."""
    result = await executor.execute_async(
        agent_id="test_agent",
        action={"type": "type", "text": "Hello World"}
    )

    assert result["status"] == "success"
    assert result["action"] == "type"
    assert result["text"] == "Hello World"

    mock_pyautogui.write.assert_called_once_with("Hello World", interval=0.0)


@pytest.mark.asyncio
async def test_key_press_action(executor, mock_pyautogui):
    """Test key press action."""
    result = await executor.execute_async(
        agent_id="test_agent",
        action={"type": "key", "key": "enter"}
    )

    assert result["status"] == "success"
    assert result["action"] == "key"
    assert result["key"] == "enter"

    mock_pyautogui.press.assert_called_once_with("enter")


@pytest.mark.asyncio
async def test_statistics_tracking(executor, mock_pyautogui):
    """Test execution statistics."""
    # Execute various actions
    await executor.execute_async(
        agent_id="agent1",
        action={"type": "click", "x": 10, "y": 10}
    )

    await executor.execute_async(
        agent_id="agent1",
        action={"type": "type", "text": "test"}
    )

    stats = executor.get_stats()

    assert stats["total_actions"] == 2
    assert stats["successful"] == 2
    assert stats["failed"] == 0
