from abc import ABC, abstractmethod
from typing import Dict, Optional, Any
import asyncio
import time
from dataclasses import dataclass

@dataclass
class AgentState:
    """Simple state machine for agent status."""
    status: str  # idle, processing, waiting, error
    last_activity: float = 0.0
    error: Optional[str] = None

class BaseAgent(ABC):
    """
    Abstract base class for all agents. Provides common interface, lifecycle management,
    and integration with MessageBus. Enforces consistency across agents.
    """
    def __init__(
        self,
        agent_id: str,
        message_bus: 'MessageBus',  # Forward reference to avoid import cycle
        session_logger: 'SessionLogger',
        config: Dict[str, Any],
        heartbeat_interval: float = 10.0  # Seconds between heartbeats
    ):
        self.agent_id = agent_id
        self.message_bus = message_bus
        self.session_logger = session_logger
        self.config = config
        self.heartbeat_interval = heartbeat_interval
        
        # State management
        self.state = AgentState(status="idle")
        self.running = False
        self.heartbeat_task: Optional[asyncio.Task] = None
        
        # Deadlock detector integration (stub - will be injected in Phase 1)
        self.deadlock_detector = None  # To be set externally if available
        
        # Register agent with message bus
        self.message_bus.register_agent(self.agent_id)

    @abstractmethod
    async def process_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process incoming message and return response or None.
        Must be implemented by subclasses.
        Updates state to 'processing' during execution.
        """
        pass

    async def on_start(self):
        """Hook for agent-specific startup logic. Override in subclasses."""
        pass

    async def on_stop(self):
        """Hook for agent-specific shutdown logic. Override in subclasses."""
        pass

    async def on_error(self, error: Exception):
        """Hook for error handling. Override in subclasses."""
        self.session_logger.log_agent_error(self.agent_id, str(error))
        self.state = AgentState(status="error", error=str(error))

    def _update_state(self, status: str, last_activity: Optional[float] = None):
        """Update agent state and notify detector if available."""
        self.state.status = status
        if last_activity is not None:
            self.state.last_activity = last_activity
        
        # Notify deadlock detector
        if self.deadlock_detector:
            self.deadlock_detector.update_activity(self.agent_id)
        else:
            # Stub: Log activity for now
            self.session_logger.log_agent_activity(self.agent_id, status)

    async def _heartbeat(self):
        """Periodic heartbeat to coordinator/detector."""
        while self.running:
            await asyncio.sleep(self.heartbeat_interval)
            heartbeat_msg = {
                "type": "heartbeat",
                "from": self.agent_id,
                "timestamp": time.time(),
                "state": self.state.status
            }
            await self.message_bus.send("coordinator", heartbeat_msg)
            self.session_logger.log_heartbeat(self.agent_id)

    async def run(self):
        """Main agent loop: Receive messages, process, and respond."""
        self.running = True
        self._update_state("idle")
        self.session_logger.log_agent_start(self.agent_id)

        # Start hooks and heartbeat
        await self.on_start()
        self.heartbeat_task = asyncio.create_task(self._heartbeat())

        try:
            while self.running:
                try:
                    # Receive message with timeout (prevents indefinite blocking)
                    message = await self.message_bus.receive(
                        self.agent_id,
                        timeout=30.0  # 30s timeout to detect stalls
                    )
                    
                    # Update state and process
                    self._update_state("processing", time.time())
                    response = await self.process_message(message)
                    
                    # Send response if any
                    if response:
                        await self.message_bus.send(
                            response.get("to", "coordinator"),
                            response.get("content", response)
                        )
                    
                    self._update_state("idle")
                    
                except asyncio.TimeoutError:
                    # No message - stay idle, log if prolonged
                    self._update_state("waiting")
                    self.session_logger.log_agent_wait(self.agent_id)
                    continue
                except Exception as e:
                    await self.on_error(e)
                    if not self.config.get("auto_restart", True):
                        raise  # Re-raise if no auto-restart

        except asyncio.CancelledError:
            pass  # Graceful shutdown
        finally:
            await self.stop()

    async def stop(self):
        """Graceful shutdown: Stop heartbeat, call hooks, unregister."""
        if self.running:
            self.running = False
            if self.heartbeat_task:
                self.heartbeat_task.cancel()
                try:
                    await self.heartbeat_task
                except asyncio.CancelledError:
                    pass
            
            await self.on_stop()
            self._update_state("stopped")
            self.session_logger.log_agent_stop(self.agent_id)
            self.message_bus.unregister_agent(self.agent_id)

    def is_healthy(self) -> bool:
        """Check if agent is running without errors."""
        return (
            self.running and
            self.state.status != "error" and
            (time.time() - self.state.last_activity) < 60.0  # Active in last minute
        )