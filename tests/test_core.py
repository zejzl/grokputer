import asyncio
import pytest
from src.core.base_agent import BaseAgent, AgentState
from src.core.message_bus import MessageBus  # Assume implemented
from src.core.action_executor import ActionExecutor
from unittest.mock import AsyncMock, Mock
import time


# Stub classes for testing
class StubLogger:
    def log_agent_start(self, agent_id):
        pass

    def log_agent_stop(self, agent_id):
        pass

    def log_agent_error(self, agent_id, error):
        pass

    def log_agent_wait(self, agent_id):
        pass

    def log_heartbeat(self, agent_id):
        pass


class StubConfig:
    def get(self, key, default=None):
        return getattr(self, key, default)


class TestBaseAgent:
    @pytest.mark.asyncio
    async def test_base_agent_lifecycle(self):
        """Test basic lifecycle: run, process, stop."""
        bus = MessageBus()
        logger = StubLogger()
        config = StubConfig()

        # Concrete subclass for testing
        class TestAgent(BaseAgent):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.message_processed = False

            async def process_message(self, message):
                self.message_processed = True
                return None  # No response message

        agent = TestAgent("test_agent", bus, logger, config)
        agent.deadlock_detector = Mock()  # Stub

        # Register agent with bus
        bus.register_agent("test_agent")

        # Start and run briefly
        task = asyncio.create_task(agent.run())
        await asyncio.sleep(0.1)  # Let it start

        # Send message via bus
        from src.core.message_bus import Message

        message = Message(from_agent="test", to_agent="test_agent", message_type="test", content={"type": "test"})
        await bus.send(message)

        await asyncio.sleep(0.2)  # Let it process

        # Stop the agent
        agent.running = False
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        assert agent.message_processed  # Verify message was processed

    @pytest.mark.asyncio
    async def test_agent_health(self):
        """Test is_healthy method."""
        bus = MessageBus()
        logger = StubLogger()
        config = StubConfig()

        class TestAgent(BaseAgent):
            async def process_message(self, message):
                return None

        agent = TestAgent("health_test", bus, logger, config)
        assert not agent.is_healthy()  # Not running

        agent.running = True
        agent.state.last_activity = time.time()
        assert agent.is_healthy()

        # Simulate error
        agent.state.status = "error"
        assert not agent.is_healthy()

        # Simulate idle too long
        agent.state.status = "idle"
        agent.state.last_activity = time.time() - 70
        assert not agent.is_healthy()


class TestActionExecutor:
    @pytest.mark.asyncio
    async def test_execute_sync(self):
        """Test action execution."""
        executor = ActionExecutor()

        # Execute action
        action = {"type": "click", "x": 100, "y": 200}
        result = await executor.execute_async("test_agent", action, timeout=2.0)

        assert result["status"] == "success"
        assert result["action"] == "click"

        executor.shutdown()

    @pytest.mark.asyncio
    async def test_async_execute(self):
        """Test async execution with timeout."""
        executor = ActionExecutor()

        action = {"type": "type", "text": "test"}
        result = await executor.execute_async("test_agent", action, timeout=2.0)

        assert result["status"] == "success"
        assert "text" in result

        executor.shutdown()


# Run with: pytest tests/test_core.py -v --asyncio-mode=auto
