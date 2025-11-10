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

class StubConfig:
    pass

class TestBaseAgent:
    @pytest.mark.asyncio
    async def test_base_agent_lifecycle(self):
        """Test basic lifecycle: run, process, stop."""
        bus = MessageBus()
        logger = StubLogger()
        config = StubConfig()
        
        # Concrete subclass for testing
        class TestAgent(BaseAgent):
            async def process_message(self, message):
                return {"to": "test", "content": "processed"}
        
        agent = TestAgent("test_agent", bus, logger, config)
        agent.deadlock_detector = Mock()  # Stub
        
        # Start and run briefly
        task = asyncio.create_task(agent.run())
        await asyncio.sleep(0.1)  # Let it start
        
        # Send message via bus (stub)
        await bus.send("test_agent", {"type": "test"})
        
        await asyncio.sleep(0.2)  # Let it process
        
        agent.running = False  # Stop
        await task
        
        assert agent.state.status == "stopped"
        agent.deadlock_detector.update_activity.assert_called()  # Heartbeat/state updates

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
    def test_execute_sync(self):
        """Test synchronous action submission (internal)."""
        executor = ActionExecutor()
        
        # Submit and wait (simple click stub)
        request_id = "test1"
        action = {"type": "click", "x": 100, "y": 200}
        executor.submit_action(action, "test_agent", request_id)
        
        # Wait for result (in test, queue will process)
        import time
        time.sleep(0.1)  # Allow thread to process
        
        result_queue = executor.result_queues["test_agent"]
        assert not result_queue.empty()
        
        executor.shutdown()

    @pytest.mark.asyncio
    async def test_async_execute(self):
        """Test async execution with timeout."""
        executor = ActionExecutor()
        
        action = {"type": "type", "text": "test"}
        result = await executor.execute_async("test_agent", action, timeout=2.0)
        
        assert result["status"] == "success"
        assert "text" in result
        
        # Test timeout
        long_action = {"type": "screenshot"}  # Longer op
        result = await executor.execute_async("test_agent", long_action, timeout=0.1)
        assert result["status"] == "timeout"
        
        executor.shutdown()

# Run with: pytest tests/test_core.py -v --asyncio-mode=auto
