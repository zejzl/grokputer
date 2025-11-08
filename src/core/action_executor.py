import threading
from queue import Queue, Empty
from typing import Dict, Any, Optional
import asyncio
import time
import pyautogui
from PIL import Image
import io
import base64

class ActionExecutor:
    """
    Single-threaded executor for PyAutoGUI operations to ensure thread safety.
    Agents submit actions via queue; executor processes serially in a dedicated thread.
    Provides async interface for non-blocking calls from asyncio agents.
    """
    def __init__(self, max_queue_size: int = 100):
        self.action_queue: Queue = Queue(maxsize=max_queue_size)
        self.result_queues: Dict[str, Queue] = {}
        self.executor_thread = threading.Thread(
            target=self._executor_loop,
            daemon=True
        )
        self.executor_thread.start()
        self.shutdown = False

    def _executor_loop(self):
        """Dedicated thread: Dequeue and execute actions serially."""
        while not self.shutdown:
            try:
                action, agent_id, request_id = self.action_queue.get(timeout=1.0)
                try:
                    result = self._execute_action(action)
                    if agent_id in self.result_queues:
                        self.result_queues[agent_id].put((request_id, result))
                except Exception as e:
                    if agent_id in self.result_queues:
                        self.result_queues[agent_id].put((request_id, {"error": str(e)}))
                finally:
                    self.action_queue.task_done()
            except Empty:
                continue  # No actions, keep polling

    def _execute_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the specific PyAutoGUI action (runs in executor thread)."""
        action_type = action.get("type")
        if action_type == "click":
            x, y = action["x"], action["y"]
            pyautogui.click(x, y)
            return {"status": "success", "action": "click", "coords": (x, y)}

        elif action_type == "type":
            text = action["text"]
            pyautogui.write(text)
            return {"status": "success", "action": "type", "text": text}

        elif action_type == "key":
            key = action["key"]
            modifiers = action.get("modifiers", [])
            if modifiers:
                pyautogui.hotkey(key, *modifiers)
            else:
                pyautogui.press(key)
            return {"status": "success", "action": "key", "key": key}

        elif action_type == "screenshot":
            region = action.get("region", None)  # (x, y, width, height) or None for full
            if region:
                screenshot = pyautogui.screenshot(region=region)
            else:
                screenshot = pyautogui.screenshot()
            
            # Encode to base64 for easy transmission (as per plan)
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
            amount = action["amount"]
            pyautogui.scroll(amount)
            return {"status": "success", "action": "scroll", "amount": amount}

        else:
            raise ValueError(f"Unknown action type: {action_type}")

    def submit_action(self, action: Dict[str, Any], agent_id: str, request_id: str):
        """Synchronous submit (internal use)."""
        if agent_id not in self.result_queues:
            self.result_queues[agent_id] = Queue()
        self.action_queue.put((action, agent_id, request_id))

    async def execute_async(
        self,
        agent_id: str,
        action: Dict[str, Any],
        timeout: float = 10.0
    ) -> Dict[str, Any]:
        """
        Async interface: Submit action and wait for result without blocking event loop.
        Uses asyncio.to_thread for waiting on queue.
        """
        request_id = f"{agent_id}_{int(time.time() * 1000)}"

        # Ensure result queue exists
        if agent_id not in self.result_queues:
            self.result_queues[agent_id] = Queue()

        # Submit to queue (thread-safe)
        self.submit_action(action, agent_id, request_id)

        # Wait for result in thread pool to avoid blocking asyncio
        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(self._wait_for_result, agent_id, request_id, timeout),
                timeout=timeout
            )
            return result
        except asyncio.TimeoutError:
            return {"status": "timeout", "error": f"Action timed out after {timeout}s"}

    def _wait_for_result(self, agent_id: str, request_id: str, timeout: float) -> Dict[str, Any]:
        """Blocking wait on result queue (runs in thread pool)."""
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
        
        raise asyncio.TimeoutError("Result wait timeout")

    def shutdown(self):
        """Graceful shutdown: Stop executor thread."""
        self.shutdown = True
        if self.executor_thread.is_alive():
            self.executor_thread.join(timeout=5.0)

    def queue_size(self, agent_id: Optional[str] = None) -> int:
        """Get current queue size (for monitoring)."""
        if agent_id:
            return len(self.result_queues.get(agent_id, Queue()).queue) if agent_id in self.result_queues else 0
        return self.action_queue.qsize()