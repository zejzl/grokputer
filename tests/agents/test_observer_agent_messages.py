"""ObserverAgent must accept Message objects (what PantheonCoordinator sends) as well as plain dicts."""
import asyncio
from unittest.mock import AsyncMock, Mock

from src.agents.observer_agent import ObserverAgent
from src.core.message_bus import Message, MessageBus, MessagePriority


def _agent():
    agent = ObserverAgent(agent_id="observer", message_bus=MessageBus(), session_logger=Mock(), config={})
    agent.screen = Mock()
    agent.screen.screenshot_to_base64 = AsyncMock(return_value="B64")
    agent.screen.get_screen_size = Mock(return_value=(1920, 1080))
    return agent


def test_capture_message_object():
    agent = _agent()
    msg = Message(
        message_type="capture",
        from_agent="pantheon_coordinator",
        to_agent="observer",
        priority=MessagePriority.NORMAL,
        content={},
    )
    result = asyncio.run(agent.process_message(msg))
    assert result["status"] == "success"
    assert result["data"] == "B64"
    assert result["to"] == "pantheon_coordinator"


def test_observe_screen_plain_dict():
    agent = _agent()
    result = asyncio.run(agent.process_message({"type": "observe_screen", "from": "coordinator", "content": {}}))
    assert result["status"] == "success"
    assert result["to"] == "coordinator"
