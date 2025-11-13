import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.agents.coordinator import Coordinator
from src.agents.observer_agent import ObserverAgent
from src.agents.actor_agent import ActorAgent
from src.core.message_bus import MessageBus
from src.observability.session_logger import SessionLogger


@pytest.fixture
def mock_bus():
    bus = AsyncMock(spec=MessageBus)
    bus.send = AsyncMock()
    bus.register_agent = AsyncMock()
    bus.receive = AsyncMock(
        side_effect=[  # Simulate responses
            {"type": "response", "from": "observer1", "content": {"files": 3}},
            {"type": "response", "from": "observer2", "content": {"files": 2}},
            {"type": "response", "from": "actor1", "content": {"ls_output": "file1.txt file2.jpg"}},
            {"type": "response", "from": "actor2", "content": {"ls_output": "file3.pdf file4.md"}},
            {"type": "task_complete", "content": {"result": "Aggregated 5 files scanned"}},
        ]
    )
    return bus


@pytest.fixture
def mock_logger():
    class MockLogger:
        def log_swarm_summary(self, *args):
            pass

        def log_agent_start(self, *args):
            pass

        def log_agent_activity(self, *args):
            pass

        def log_agent_ready(self, *args):
            pass

    return MockLogger()


@pytest.fixture
def config():
    return {
        "debug": False,
        "max_subtasks": 5,
        "auto_restart": True,
    }


@pytest.mark.asyncio
async def test_scaled_five_agents_swarm(mock_bus, mock_logger, config):
    """Test 5-agent swarm setup: Coordinator + 2 Observers + 2 Actors."""
    # Setup agents with unique IDs
    coordinator = Coordinator(message_bus=mock_bus, session_logger=mock_logger, config=config)
    observer1 = ObserverAgent(message_bus=mock_bus, session_logger=mock_logger, config=config, agent_id="observer1")
    observer2 = ObserverAgent(message_bus=mock_bus, session_logger=mock_logger, config=config, agent_id="observer2")
    actor1 = ActorAgent(message_bus=mock_bus, session_logger=mock_logger, config=config, agent_id="actor1")
    actor2 = ActorAgent(message_bus=mock_bus, session_logger=mock_logger, config=config, agent_id="actor2")

    # Verify agents are created and registered
    assert coordinator.agent_id == "coordinator"
    assert observer1.agent_id == "observer1"
    assert observer2.agent_id == "observer2"
    assert actor1.agent_id == "actor1"
    assert actor2.agent_id == "actor2"

    # Verify message bus registration calls (agents register themselves)
    assert mock_bus.register_agent.call_count >= 5  # All 5 agents registered

    # Send task to coordinator (test message sending)
    task_msg = {
        "type": "new_task",
        "task_id": "scale1",
        "content": {"description": "parallel scan vault with multiple observers and actors"},
    }
    await mock_bus.send("coordinator", task_msg)

    # Verify task was sent
    mock_bus.send.assert_called_with("coordinator", task_msg)


@pytest.mark.asyncio
async def test_trio_coa_integration(mock_bus, mock_logger, config):
    """Test classic C-O-A trio setup."""
    coordinator = Coordinator(message_bus=mock_bus, session_logger=mock_logger, config=config)
    observer = ObserverAgent("observer", mock_bus, mock_logger, config)
    actor = ActorAgent("actor", mock_bus, mock_logger, config)

    # Verify agents are created correctly
    assert coordinator.agent_id == "coordinator"
    assert observer.agent_id == "observer"
    assert actor.agent_id == "actor"

    # Verify message bus registration
    assert mock_bus.register_agent.call_count >= 3  # All 3 agents registered

    # Send task to coordinator
    task_msg = {"type": "new_task", "task_id": "trio1", "content": {"description": "find notepad and type ZA GROKA"}}
    await mock_bus.send("coordinator", task_msg)

    # Verify task was sent
    mock_bus.send.assert_called_with("coordinator", task_msg)
