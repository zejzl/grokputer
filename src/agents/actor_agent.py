# src/agents/actor_agent.py
"""
Actor Agent: Executes actions based on Coordinator delegation.
Part of ORAM Pantheon/Swarm.
"""

import asyncio
import logging
from typing import Dict, Any
from pathlib import Path

# Existing imports (assume src path added)
from src.core.message_bus import MessageBus, Message, MessagePriority
from src.core.action_executor import ActionExecutor
from src.observability.session_logger import SessionLogger
from src.observability.deadlock_detector import DeadlockDetector


class ActorAgent:
    def __init__(
        self,
        agent_id: str = "actor",
        message_bus: MessageBus = None,
        action_executor: ActionExecutor = None,
        session_logger: SessionLogger = None,
        deadlock_detector: DeadlockDetector = None,
        config: Dict[str, Any] = None,
    ):
        self.agent_id = agent_id
        self.message_bus = message_bus
        self.action_executor = action_executor or ActionExecutor()
        self.session_logger = session_logger
        self.deadlock_detector = deadlock_detector
        self.config = config or {"debug": False, "max_retries": 3, "safety_threshold": 0.8}

        self.logger = logging.getLogger(__name__)
        self.running = False
        self.action_queue = asyncio.Queue()

    def is_healthy(self) -> bool:
        return True

        # Register with message bus
        self.message_bus.register_agent(self.agent_id)

        if self.deadlock_detector:
            self.deadlock_detector.register_agent(self.agent_id)

        self.logger.info(f"[ACTOR] {self.agent_id} initialized")

    async def run(self):
        """
        Main agent loop: Listen for messages, execute actions.
        """
        self.running = True
        self.session_logger.log_agent_start(self.agent_id)
        self.logger.info(f"[ACTOR] {self.agent_id} starting run loop")

        # Task to process queue
        process_task = asyncio.create_task(self._process_actions())

        # Listen for incoming messages (subscribe to act commands)
        async for message in self.message_bus.subscribe(self.agent_id):
            if not self.running:
                break

            self.logger.info(f"[ACTOR] Received act message: {message.content}")
            self.session_logger.log_agent_activity(self.agent_id, "received_act", message.content)

            # Update activity for deadlock detection
            if self.deadlock_detector:
                self.deadlock_detector.update_activity(self.agent_id, state="processing")

            # Queue the action
            await self.action_queue.put(message.content)

        # Cleanup
        self.running = False
        self.action_queue.put_nowait(None)  # Signal end
        await process_task
        self.session_logger.log_agent_stop(self.agent_id)
        self.logger.info(f"[ACTOR] {self.agent_id} stopped")

    async def _process_actions(self):
        """
        Process queued actions asynchronously.
        """
        while True:
            action_data = await self.action_queue.get()
            if action_data is None:  # End signal
                break

            try:
                result = await self._execute_action(action_data)

                # Broadcast result
                result_msg = Message(
                    from_agent=self.agent_id,
                    to_agent="coordinator",  # Or "all" for swarm
                    message_type="action_result",
                    content={"action": action_data, "result": result, "timestamp": asyncio.get_event_loop().time()},
                    priority=MessagePriority.NORMAL,
                )
                await self.message_bus.send("coordinator", result_msg)

                self.session_logger.log_agent_activity(
                    self.agent_id, "executed_action", {"action": action_data, "result": result}
                )

                if self.config["debug"]:
                    print(f"[ACTOR] Executed: {action_data} -> {result['status']}")

            except Exception as e:
                self.logger.error(f"[ACTOR] Action error: {e}", exc_info=True)
                self.session_logger.log_agent_error(self.agent_id, str(e))

                # Retry logic
                retries = action_data.get("retries", 0)
                if retries < self.config["max_retries"]:
                    action_data["retries"] = retries + 1
                    await self.action_queue.put(action_data)
                    self.logger.info(f"[ACTOR] Retrying action (attempt {retries + 1})")
                else:
                    # Escalate to validator
                    error_msg = Message(
                        from_agent=self.agent_id,
                        to_agent="validator",
                        message_type="action_failed",
                        content={"action": action_data, "error": str(e)},
                        priority=MessagePriority.HIGH,
                    )
                    await self.message_bus.send("validator", error_msg)

            finally:
                if self.deadlock_detector:
                    self.deadlock_detector.update_activity(self.agent_id, state="idle")

                self.action_queue.task_done()

    async def _execute_action(self, action_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a single action via ActionExecutor.
        Supports: bash, file ops, PyAutoGUI (type/click).

        Args:
            action_data: e.g., {"type": "bash", "command": "ls -la", "safety_level": "low"}

        Returns:
            Execution result.
        """
        action_type = action_data.get("type", "bash")
        params = action_data.get("params", {})
        safety_level = action_data.get("safety_level", "low")

        # Simple safety check (extend with full Validator integration)
        if safety_level == "high_risk" and self.config["safety_threshold"] < 0.9:
            raise ValueError(f"[ACTOR] High-risk action rejected: {action_data}")

        # Execute based on type
        if action_type == "bash":
            result = await self.action_executor.execute_bash(params.get("command", ""))
        elif action_type == "file_create":
            result = await self.action_executor.create_file(
                path=params.get("path", ""), content=params.get("content", "")
            )
        elif action_type == "file_edit":
            result = await self.action_executor.str_replace_editor(
                path=params.get("path", ""), old_str=params.get("old_str", ""), new_str=params.get("new_str", "")
            )
        elif action_type == "pyautogui_type":
            result = await self.action_executor.type_text(params.get("text", ""))
        elif action_type == "pyautogui_click":
            result = await self.action_executor.click_at(params.get("x", 0), params.get("y", 0))
        else:
            raise ValueError(f"[ACTOR] Unknown action type: {action_type}")

        return {
            "status": "success" if result.get("status") == "success" else "failed",
            "output": result.get("output", ""),
            "error": result.get("error", None),
        }


# Example usage (for testing)
if __name__ == "__main__":
    # Stub setup for standalone test
    from src.core.message_bus import MessageBus
    from src.observability.session_logger import SessionLogger
    from src.observability.deadlock_detector import DeadlockDetector
    from src.core.action_executor import ActionExecutor
    import logging

    logging.basicConfig(level=logging.INFO)

    bus = MessageBus()
    logger = SessionLogger(session_id="test", task="actor_test", log_dir=Path("./logs"), swarm_mode=True)
    detector = DeadlockDetector()
    executor = ActionExecutor()

    actor = ActorAgent(
        message_bus=bus,
        action_executor=executor,
        session_logger=logger,
        deadlock_detector=detector,
        config={"debug": True},
    )

    async def test_actor():
        # Simulate message
        action_data = {"type": "bash", "params": {"command": "echo 'ZA GROKA'"}, "safety_level": "low"}
        await actor.action_queue.put(action_data)
        await actor._process_actions()

    asyncio.run(test_actor())
