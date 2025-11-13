from abc import ABC, abstractmethod
from typing import Dict, Optional, Any, List
import asyncio
import time
import logging
from dataclasses import dataclass
from datetime import datetime


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
        message_bus: "MessageBus",  # Forward reference to avoid import cycle
        session_logger: "SessionLogger",
        config: Dict[str, Any],
        heartbeat_interval: float = 10.0,  # Seconds between heartbeats
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
        self.idle_task: Optional[asyncio.Task] = None

        # Task management integration
        self.current_tasks: Dict[str, Dict[str, Any]] = {}  # task_id -> task_data
        self.capabilities: List[str] = []
        self.task_client_enabled = False

        # Deadlock detector integration (stub - will be injected in Phase 1)
        self.deadlock_detector = None  # To be set externally if available

        # Register agent with message bus
        self.message_bus.register_agent(self.agent_id)

    @abstractmethod
    async def process_message(self, message) -> Optional[Dict[str, Any]]:
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
                "state": self.state.status,
            }
            # Send heartbeat (simplified - in real system would use Message object)
            # For now, just log it
            pass
            self.session_logger.log_heartbeat(self.agent_id)

    async def run(self):
        """Main agent loop: Receive messages, process, and respond."""
        self.running = True
        self._update_state("idle")
        self.session_logger.log_agent_start(self.agent_id)

        # Start hooks and heartbeat
        await self.on_start()
        self.heartbeat_task = asyncio.create_task(self._heartbeat())

        # Start task client loop if enabled
        if self.task_client_enabled:
            self.idle_task = asyncio.create_task(self.start_idle_task_loop())
            await self.register_capabilities()

        try:
            while self.running:
                try:
                    # Receive message with timeout (prevents indefinite blocking)
                    message = await self.message_bus.receive(
                        self.agent_id, timeout=30.0  # 30s timeout to detect stalls
                    )

                    # Update state and process
                    self._update_state("processing", time.time())
                    response = await self.process_message(message)

                    # Send response if any
                    if response:
                        await self.message_bus.send(
                            response.get("to", "coordinator"), response.get("content", response)
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
            if self.idle_task:
                self.idle_task.cancel()
                try:
                    await self.idle_task
                except asyncio.CancelledError:
                    pass

            await self.on_stop()
            self._update_state("stopped")
            self.session_logger.log_agent_stop(self.agent_id)
            self.message_bus.unregister_agent(self.agent_id)

    def is_healthy(self) -> bool:
        """Check if agent is running without errors."""
        return (
            self.running
            and self.state.status != "error"
            and (time.time() - self.state.last_activity) < 60.0  # Active in last minute
        )

    # Task Management Integration Methods

    def enable_task_client(self, capabilities: List[str]):
        """Enable TaskClient functionality for this agent."""
        self.capabilities = capabilities
        self.task_client_enabled = True

    async def register_capabilities(self):
        """Register agent capabilities with TaskMaster."""
        if not self.task_client_enabled:
            return

        response = await self._send_task_message("agent_capabilities", {"capabilities": self.capabilities})

        logger = logging.getLogger(__name__)
        logger.info(f"[TaskClient:{self.agent_id}] Registered capabilities: {self.capabilities}")
        return response

    async def send_task_heartbeat(self):
        """Send heartbeat to TaskMaster."""
        if not self.task_client_enabled:
            return

        response = await self._send_task_message(
            "agent_heartbeat", {"timestamp": datetime.now().timestamp(), "status": self.state.status}
        )
        return response

    async def request_task(self, priority: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Request a task from TaskMaster when idle."""
        if not self.task_client_enabled:
            return None

        response = await self._send_task_message("task_request", {"priority": priority or "medium"})

        if response and response.get("task"):
            task = response["task"]
            self.current_tasks[task["id"]] = task
            return task
        return None

    async def update_task_status(self, task_id: str, status: str, notes: str = ""):
        """Update task status with TaskMaster."""
        if not self.task_client_enabled:
            return

        response = await self._send_task_message(
            "task_status_update", {"task_id": task_id, "status": status, "notes": notes}
        )

        if status in ["completed", "failed", "cancelled"]:
            self.current_tasks.pop(task_id, None)

        return response

    async def get_available_tasks(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get list of available tasks."""
        if not self.task_client_enabled:
            return []

        response = await self._send_task_message("get_available_tasks", {"limit": limit})

        return response.get("tasks", []) if response else []

    async def create_task(
        self, title: str, description: str, priority: str = "medium", tags: Optional[List[str]] = None
    ) -> Optional[str]:
        """Create a new task."""
        if not self.task_client_enabled:
            return None

        response = await self._send_task_message(
            "create_task", {"title": title, "description": description, "priority": priority, "tags": tags or []}
        )

        return response.get("task_id") if response else None

    async def _send_task_message(self, message_type: str, content: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Send a message to TaskMaster and wait for response."""
        try:
            # Send message to taskmaster
            from src.core.message_bus import Message, MessagePriority

            message = Message(
                message_type=message_type,
                content=content,
                from_agent=self.agent_id,
                to_agent="taskmaster",
                priority=MessagePriority.NORMAL,
            )

            await self.message_bus.send("taskmaster", message)

            # Wait for response (simplified - in practice would need correlation ID)
            # For now, return success
            return {"status": "sent"}

        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send task message {message_type}: {e}")
            return None

    async def start_idle_task_loop(self, check_interval: float = 30.0):
        """Start loop to request tasks when idle."""
        if not self.task_client_enabled:
            return

        while self.running:
            try:
                await asyncio.sleep(check_interval)

                # Only request tasks if idle and no current tasks
                if self.state.status == "idle" and not self.current_tasks and self.task_client_enabled:

                    task = await self.request_task()
                    if task:
                        logger = logging.getLogger(__name__)
                        logger.info(f"[TaskClient:{self.agent_id}] Received task: {task['title']}")

                        # Process the task
                        await self._process_assigned_task(task)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger = logging.getLogger(__name__)
                logger.error(f"Error in idle task loop: {e}")

    async def _process_assigned_task(self, task: Dict[str, Any]):
        """Process a task assigned by TaskMaster."""
        task_id = task["id"]

        try:
            self._update_state("processing")

            # Create a message for the task
            task_message = Message(
                message_type="task_execution",
                content={"task_id": task_id, "task": task, "instruction": task.get("description", "")},
                from_agent="taskmaster",
                to_agent=self.agent_id,
                priority=MessagePriority.NORMAL,
            )

            # Process the task using existing message processing
            result = await self.process_message(task_message)

            # Update task status
            if result and result.get("status") == "success":
                await self.update_task_status(task_id, "completed", "Task completed successfully")
            else:
                await self.update_task_status(
                    task_id, "failed", result.get("error", "Unknown error") if result else "No result"
                )

        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Error processing assigned task {task_id}: {e}")
            await self.update_task_status(task_id, "failed", str(e))
        finally:
            self._update_state("idle")
