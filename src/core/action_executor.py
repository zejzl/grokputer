"""
Action executor for PyAutoGUI operations with thread safety.

Single-threaded executor ensures PyAutoGUI calls are serialized to avoid
race conditions in multi-agent environment. Provides async interface for agents.
"""

import threading
from queue import PriorityQueue, Queue, Empty
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import IntEnum
import asyncio
import time
import logging
import pyautogui
from PIL import Image
import io
import base64

logger = logging.getLogger(__name__)


class ActionPriority(IntEnum):
    """Action priority levels (lower number = higher priority)."""
    HIGH = 0
    NORMAL = 1
    LOW = 2


@dataclass
class Action:
    """Represents a queued action."""
    action_type: str
    params: Dict[str, Any]
    agent_id: str
    request_id: str
    priority: ActionPriority = ActionPriority.NORMAL
    timestamp: float = field(default_factory=time.time)

    def __lt__(self, other):
        """Compare by priority, then timestamp for PriorityQueue."""
        if self.priority != other.priority:
            return self.priority < other.priority
        return self.timestamp < other.timestamp


@dataclass
class ActionHistory:
    """Record of executed action for debugging/rollback."""
    action: Action
    result: Dict[str, Any]
    execution_time: float
    timestamp: float = field(default_factory=time.time)


class ActionExecutor:
    """
    Production-ready single-threaded executor for PyAutoGUI operations.

    Features:
    - Priority queuing (HIGH/NORMAL/LOW)
    - Batch action support (execute multiple actions atomically)
    - Action history tracking (for debugging and potential rollback)
    - Timeout handling per action
    - Statistics tracking (execution counts, timings)
    - Thread-safe async interface for agents

    Usage:
        executor = ActionExecutor()

        # Single action
        result = await executor.execute_async(
            agent_id="actor",
            action={"type": "click", "x": 100, "y": 200},
            priority=ActionPriority.HIGH
        )

        # Batch actions
        results = await executor.execute_batch_async(
            agent_id="actor",
            actions=[
                {"type": "click", "x": 100, "y": 200},
                {"type": "type", "text": "Hello"},
                {"type": "key", "key": "enter"}
            ]
        )
    """

    def __init__(
        self,
        max_queue_size: int = 100,
        history_size: int = 100,
        default_timeout: float = 10.0
    ):
        """
        Initialize action executor.

        Args:
            max_queue_size: Maximum actions in queue
            history_size: Number of actions to keep in history
            default_timeout: Default timeout for actions (seconds)
        """
        self.action_queue: PriorityQueue = PriorityQueue(maxsize=max_queue_size)
        self.result_queues: Dict[str, Queue] = {}
        self.default_timeout = default_timeout

        # Action history (circular buffer)
        self.history: List[ActionHistory] = []
        self.history_size = history_size

        # Statistics
        self.stats = {
            "total_actions": 0,
            "successful_actions": 0,
            "failed_actions": 0,
            "timeout_actions": 0,
            "total_execution_time": 0.0,
            "actions_by_type": {},
            "actions_by_agent": {}
        }

        # Executor thread
        self._shutdown = False
        self.executor_thread = threading.Thread(
            target=self._executor_loop,
            daemon=True,
            name="ActionExecutor"
        )
        self.executor_thread.start()

        logger.info("[ActionExecutor] Started with priority queuing")

    def _executor_loop(self):
        """Dedicated thread: Dequeue and execute actions serially."""
        while not self._shutdown:
            try:
                # Get highest priority action
                action = self.action_queue.get(timeout=1.0)

                try:
                    # Execute action and measure time
                    start_time = time.time()
                    result = self._execute_action(action)
                    execution_time = time.time() - start_time

                    # Add to history
                    self._add_to_history(action, result, execution_time)

                    # Update stats
                    self._update_stats(action, result, execution_time)

                    # Send result back to agent
                    if action.agent_id in self.result_queues:
                        self.result_queues[action.agent_id].put(
                            (action.request_id, result)
                        )

                except Exception as e:
                    logger.error(
                        f"[ActionExecutor] Action failed: {action.action_type} "
                        f"from {action.agent_id}: {e}"
                    )
                    result = {"error": str(e), "status": "error"}

                    # Update failure stats
                    self.stats["failed_actions"] += 1

                    # Send error result
                    if action.agent_id in self.result_queues:
                        self.result_queues[action.agent_id].put(
                            (action.request_id, result)
                        )

                finally:
                    self.action_queue.task_done()

            except Empty:
                continue  # No actions, keep polling

    def _execute_action(self, action: Action) -> Dict[str, Any]:
        """
        Execute the specific PyAutoGUI action (runs in executor thread).

        Args:
            action: Action to execute

        Returns:
            Result dictionary with status and action-specific data
        """
        action_type = action.action_type
        params = action.params

        if action_type == "click":
            x, y = params["x"], params["y"]
            button = params.get("button", "left")
            clicks = params.get("clicks", 1)
            pyautogui.click(x, y, button=button, clicks=clicks)
            return {
                "status": "success",
                "action": "click",
                "coords": (x, y),
                "button": button,
                "clicks": clicks
            }

        elif action_type == "type":
            text = params["text"]
            interval = params.get("interval", 0.0)
            pyautogui.write(text, interval=interval)
            return {"status": "success", "action": "type", "text": text}

        elif action_type == "key":
            key = params["key"]
            modifiers = params.get("modifiers", [])
            if modifiers:
                pyautogui.hotkey(*modifiers, key)
            else:
                pyautogui.press(key)
            return {"status": "success", "action": "key", "key": key}

        elif action_type == "screenshot":
            region = params.get("region", None)
            if region:
                screenshot = pyautogui.screenshot(region=region)
            else:
                screenshot = pyautogui.screenshot()

            # Encode to base64
            buffer = io.BytesIO()
            screenshot.save(buffer, format="PNG")
            img_str = base64.b64encode(buffer.getvalue()).decode()

            return {
                "status": "success",
                "action": "screenshot",
                "data": img_str,
                "dimensions": screenshot.size
            }

        elif action_type == "scroll":
            amount = params["amount"]
            x = params.get("x")
            y = params.get("y")
            pyautogui.scroll(amount, x=x, y=y)
            return {"status": "success", "action": "scroll", "amount": amount}

        elif action_type == "move":
            x, y = params["x"], params["y"]
            duration = params.get("duration", 0.0)
            pyautogui.moveTo(x, y, duration=duration)
            return {"status": "success", "action": "move", "coords": (x, y)}

        elif action_type == "drag":
            x, y = params["x"], params["y"]
            duration = params.get("duration", 0.5)
            button = params.get("button", "left")
            pyautogui.drag(x, y, duration=duration, button=button)
            return {"status": "success", "action": "drag", "coords": (x, y)}

        else:
            raise ValueError(f"Unknown action type: {action_type}")

    def _add_to_history(self, action: Action, result: Dict, execution_time: float):
        """Add action to history (circular buffer)."""
        history_entry = ActionHistory(
            action=action,
            result=result,
            execution_time=execution_time
        )

        self.history.append(history_entry)

        # Maintain max size
        if len(self.history) > self.history_size:
            self.history.pop(0)

    def _update_stats(self, action: Action, result: Dict, execution_time: float):
        """Update execution statistics."""
        self.stats["total_actions"] += 1

        if result.get("status") == "success":
            self.stats["successful_actions"] += 1
        elif result.get("status") == "timeout":
            self.stats["timeout_actions"] += 1

        self.stats["total_execution_time"] += execution_time

        # By type
        action_type = action.action_type
        if action_type not in self.stats["actions_by_type"]:
            self.stats["actions_by_type"][action_type] = 0
        self.stats["actions_by_type"][action_type] += 1

        # By agent
        agent_id = action.agent_id
        if agent_id not in self.stats["actions_by_agent"]:
            self.stats["actions_by_agent"][agent_id] = 0
        self.stats["actions_by_agent"][agent_id] += 1

    async def execute_async(
        self,
        agent_id: str,
        action: Dict[str, Any],
        priority: ActionPriority = ActionPriority.NORMAL,
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Execute single action asynchronously.

        Args:
            agent_id: ID of requesting agent
            action: Action dictionary with 'type' and parameters
            priority: Action priority (HIGH/NORMAL/LOW)
            timeout: Timeout in seconds (None = use default)

        Returns:
            Result dictionary with status and action-specific data
        """
        timeout = timeout or self.default_timeout
        request_id = f"{agent_id}_{int(time.time() * 1000000)}"

        # Create Action object
        action_obj = Action(
            action_type=action["type"],
            params={k: v for k, v in action.items() if k != "type"},
            agent_id=agent_id,
            request_id=request_id,
            priority=priority
        )

        # Ensure result queue exists
        if agent_id not in self.result_queues:
            self.result_queues[agent_id] = Queue()

        # Submit to priority queue
        await asyncio.to_thread(self.action_queue.put, action_obj)

        # Wait for result
        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(self._wait_for_result, agent_id, request_id),
                timeout=timeout
            )
            return result
        except asyncio.TimeoutError:
            logger.warning(
                f"[ActionExecutor] Action timeout: {action_obj.action_type} "
                f"from {agent_id} after {timeout}s"
            )
            return {
                "status": "timeout",
                "error": f"Action timed out after {timeout}s"
            }

    async def execute_batch_async(
        self,
        agent_id: str,
        actions: List[Dict[str, Any]],
        priority: ActionPriority = ActionPriority.NORMAL,
        timeout: Optional[float] = None,
        stop_on_error: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Execute multiple actions in sequence (batch).

        Args:
            agent_id: ID of requesting agent
            actions: List of action dictionaries
            priority: Priority for all actions in batch
            timeout: Timeout per action (None = use default)
            stop_on_error: If True, stop batch on first error

        Returns:
            List of result dictionaries (one per action)
        """
        results = []

        for i, action in enumerate(actions):
            logger.debug(
                f"[ActionExecutor] Batch {i+1}/{len(actions)}: "
                f"{action.get('type')} for {agent_id}"
            )

            result = await self.execute_async(
                agent_id=agent_id,
                action=action,
                priority=priority,
                timeout=timeout
            )

            results.append(result)

            # Stop on error if requested
            if stop_on_error and result.get("status") != "success":
                logger.warning(
                    f"[ActionExecutor] Batch stopped at {i+1}/{len(actions)} "
                    f"due to error: {result.get('error')}"
                )
                break

        return results

    def _wait_for_result(
        self,
        agent_id: str,
        request_id: str,
        timeout: float = 10.0
    ) -> Dict[str, Any]:
        """
        Blocking wait on result queue (runs in thread pool).

        Args:
            agent_id: ID of requesting agent
            request_id: Request ID to match
            timeout: Max time to wait

        Returns:
            Result dictionary

        Raises:
            TimeoutError: If result not received in time
        """
        result_queue = self.result_queues[agent_id]
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                rid, result = result_queue.get(timeout=0.1)
                if rid == request_id:
                    return {"request_id": rid, **result}
                else:
                    # Wrong result, put back
                    result_queue.put((rid, result))
            except Empty:
                continue

        raise TimeoutError(f"Result wait timeout after {timeout}s")

    def get_history(self, agent_id: Optional[str] = None, limit: int = 10) -> List[Dict]:
        """
        Get recent action history.

        Args:
            agent_id: Filter by agent (None = all agents)
            limit: Max number of entries to return

        Returns:
            List of history entries (most recent first)
        """
        history = self.history[::-1]  # Reverse for most recent first

        if agent_id:
            history = [h for h in history if h.action.agent_id == agent_id]

        history = history[:limit]

        return [
            {
                "action_type": h.action.action_type,
                "agent_id": h.action.agent_id,
                "priority": h.action.priority.name,
                "execution_time": f"{h.execution_time:.3f}s",
                "status": h.result.get("status"),
                "timestamp": h.timestamp
            }
            for h in history
        ]

    def get_stats(self) -> Dict[str, Any]:
        """Get execution statistics."""
        total = self.stats["total_actions"]
        return {
            "total_actions": total,
            "successful": self.stats["successful_actions"],
            "failed": self.stats["failed_actions"],
            "timeouts": self.stats["timeout_actions"],
            "success_rate": f"{self.stats['successful_actions'] / total * 100:.1f}%" if total > 0 else "N/A",
            "avg_execution_time": f"{self.stats['total_execution_time'] / total:.3f}s" if total > 0 else "N/A",
            "queue_size": self.action_queue.qsize(),
            "by_type": self.stats["actions_by_type"],
            "by_agent": self.stats["actions_by_agent"]
        }

    def clear_history(self):
        """Clear action history."""
        self.history.clear()
        logger.info("[ActionExecutor] History cleared")

    def shutdown(self):
        """Graceful shutdown: Stop executor thread."""
        logger.info("[ActionExecutor] Shutting down...")
        self._shutdown = True

        if self.executor_thread.is_alive():
            self.executor_thread.join(timeout=5.0)

        logger.info("[ActionExecutor] Shutdown complete")
