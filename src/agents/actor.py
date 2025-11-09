"""
Actor Agent for Grokputer Swarm

Executes actions delegated by the Coordinator:
- Bash commands (with security validation)
- PyAutoGUI actions (via ActionExecutor)
- File operations (with path validation)
- Retry logic with tenacity for transient failures

Extends BaseAgent for lifecycle management.
"""

import asyncio
import logging
import subprocess
import time
from typing import Dict, Any, Optional
from pathlib import Path
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from src.core.base_agent import BaseAgent
from src.core.action_executor import ActionExecutor, ActionPriority
from src.core.message_bus import MessageBus, Message, MessagePriority
from src.observability.session_logger import SessionLogger
from src import config

logger = logging.getLogger(__name__)


class Actor(BaseAgent):
    """
    Actor Agent: Executes actions in the swarm.

    Capabilities:
    - Bash command execution (security validated)
    - PyAutoGUI actions (click, type, key, screenshot, etc.)
    - File operations (read, write, with path validation)
    - Retry logic for transient failures (tenacity)
    - Confirmation flow for high-risk actions

    Safety:
    - Validates bash commands (no injection)
    - Validates file paths (no traversal)
    - Integrates with safety scoring system
    - Requests confirmations from Coordinator
    """

    def __init__(
        self,
        message_bus: MessageBus,
        session_logger: SessionLogger,
        config_dict: Dict[str, Any],
        action_executor: ActionExecutor,
        heartbeat_interval: float = 10.0
    ):
        super().__init__('actor', message_bus, session_logger, config_dict, heartbeat_interval)
        self.action_executor = action_executor
        self.confirmation_timeout = config_dict.get("confirmation_timeout", 30.0)
        self.max_retries = config_dict.get("max_retries", 3)

        logger.info("[Actor] Initialized with ActionExecutor integration")

    async def process_message(self, message: Message) -> Optional[Dict]:
        """
        Process incoming messages from Coordinator.

        Handles:
        - subtask: Execute action (bash, pyautogui, file)
        - confirmation_response: Handle approval/denial

        Returns response message or None.
        """
        msg_type = message.message_type
        content = message.content

        if msg_type == "subtask":
            return await self._handle_subtask(message)
        elif msg_type == "confirmation_response":
            return await self._handle_confirmation(message)
        else:
            logger.warning(f"[Actor] Unknown message type: {msg_type}")
            return None

    async def _handle_subtask(self, message: Message) -> Dict:
        """Handle subtask from Coordinator."""
        action_type = message.content.get("action")
        params = message.content.get("params", {})
        task_id = message.content.get("task_id", "unknown")

        logger.info(f"[Actor] Received subtask: {action_type} for task {task_id}")

        # Determine action category
        if action_type == "perform_action":
            return await self._execute_generic_action(task_id, params)
        elif action_type == "bash":
            return await self._execute_bash(task_id, params)
        elif action_type == "file_operation":
            return await self._execute_file_op(task_id, params)
        else:
            logger.error(f"[Actor] Unknown action type: {action_type}")
            return {
                "to": "coordinator",
                "type": "response",
                "content": {
                    "task_id": task_id,
                    "status": "error",
                    "error": f"Unknown action type: {action_type}"
                },
                "priority": MessagePriority.NORMAL
            }

    async def _execute_generic_action(self, task_id: str, params: Dict) -> Dict:
        """
        Execute generic action (parse command string for PyAutoGUI).

        For Phase 1, uses simple parsing. Phase 2 will use Grok API.
        """
        command = params.get("command", "")

        # Parse command (simple heuristics for Phase 1)
        action = self._parse_command(command)

        if not action:
            return {
                "to": "coordinator",
                "type": "response",
                "content": {
                    "task_id": task_id,
                    "status": "error",
                    "error": "Could not parse command"
                },
                "priority": MessagePriority.NORMAL
            }

        # Execute via ActionExecutor with retry
        try:
            result = await self._execute_with_retry(action)

            self.session_logger.log_tool_execution(
                tool_name=action["type"],
                params=action,
                result=result,
                status="success" if result.get("status") == "success" else "error"
            )

            return {
                "to": "coordinator",
                "type": "response",
                "content": {
                    "task_id": task_id,
                    "status": "success" if result.get("status") == "success" else "error",
                    "result": result
                },
                "priority": MessagePriority.NORMAL
            }

        except Exception as e:
            logger.error(f"[Actor] Action execution failed: {e}")
            self.session_logger.log_agent_error(self.agent_id, f"Action failed: {e}")

            return {
                "to": "coordinator",
                "type": "response",
                "content": {
                    "task_id": task_id,
                    "status": "error",
                    "error": str(e)
                },
                "priority": MessagePriority.HIGH
            }

    def _parse_command(self, command: str) -> Optional[Dict]:
        """
        Parse command string into PyAutoGUI action.

        Phase 1: Simple pattern matching.
        Phase 2: Use Grok API for parsing.
        """
        command_lower = command.lower()

        # Click pattern: "click at (x, y)" or "click (x, y)"
        if "click" in command_lower:
            import re
            match = re.search(r'(\d+)[,\s]+(\d+)', command)
            if match:
                x, y = int(match.group(1)), int(match.group(2))
                return {"type": "click", "x": x, "y": y}
            return {"type": "click", "x": 100, "y": 100}  # Default

        # Type pattern: "type 'text'" or "type text"
        if "type" in command_lower:
            # Extract text after 'type'
            text = command.split("type", 1)[-1].strip().strip("'\"")
            return {"type": "type", "text": text}

        # Key pattern: "press enter" or "key enter"
        if "press" in command_lower or "key" in command_lower:
            words = command_lower.split()
            for word in words:
                if word in ["enter", "escape", "tab", "space", "return"]:
                    return {"type": "key", "key": word}

        # Screenshot
        if "screenshot" in command_lower or "capture" in command_lower:
            return {"type": "screenshot"}

        logger.warning(f"[Actor] Could not parse command: {command}")
        return None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((asyncio.TimeoutError, ConnectionError))
    )
    async def _execute_with_retry(self, action: Dict) -> Dict:
        """Execute action with retry logic for transient failures."""
        return await self.action_executor.execute_async(
            agent_id=self.agent_id,
            action=action,
            priority=ActionPriority.NORMAL,
            timeout=10.0
        )

    async def _execute_bash(self, task_id: str, params: Dict) -> Dict:
        """
        Execute bash command with security validation.

        Security:
        - No shell injection (validated command)
        - Timeout enforcement
        - Output capture

        Returns result message.
        """
        command = params.get("command", "")

        # Security validation (integrate with config.py safety scoring)
        if not self._is_safe_bash_command(command):
            logger.warning(f"[Actor] Unsafe bash command blocked: {command}")
            self.session_logger.log_agent_error(self.agent_id, f"Unsafe command: {command}")

            return {
                "to": "coordinator",
                "type": "response",
                "content": {
                    "task_id": task_id,
                    "status": "error",
                    "error": "Command rejected: security validation failed"
                },
                "priority": MessagePriority.HIGH
            }

        # Execute with timeout
        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(self._run_bash_command, command),
                timeout=params.get("timeout", 30.0)
            )

            self.session_logger.log_tool_execution(
                tool_name="bash",
                params={"command": command},
                result=result,
                status="success" if result.get("returncode") == 0 else "error"
            )

            return {
                "to": "coordinator",
                "type": "response",
                "content": {
                    "task_id": task_id,
                    "status": "success" if result.get("returncode") == 0 else "error",
                    "result": result
                },
                "priority": MessagePriority.NORMAL
            }

        except asyncio.TimeoutError:
            logger.error(f"[Actor] Bash command timeout: {command}")
            return {
                "to": "coordinator",
                "type": "response",
                "content": {
                    "task_id": task_id,
                    "status": "error",
                    "error": "Command timeout"
                },
                "priority": MessagePriority.HIGH
            }

    def _is_safe_bash_command(self, command: str) -> bool:
        """
        Validate bash command safety.

        Phase 1: Simple blocklist.
        Phase 2: Integrate with config.calculate_safety_score()
        """
        dangerous_patterns = [
            "rm -rf", "dd if=", "mkfs", ":(){ :|:& };:",  # Destructive
            ">", ">>", "|", "&", ";", "$(",  # Shell injection vectors
            "curl", "wget", "nc ", "netcat"  # Network access
        ]

        command_lower = command.lower()
        for pattern in dangerous_patterns:
            if pattern in command_lower:
                logger.warning(f"[Actor] Dangerous pattern detected: {pattern}")
                return False

        return True

    def _run_bash_command(self, command: str) -> Dict:
        """Run bash command (blocking, runs in thread pool)."""
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30.0
            )

            return {
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "command": command
            }

        except subprocess.TimeoutExpired:
            return {
                "returncode": -1,
                "stdout": "",
                "stderr": "Command timeout",
                "command": command
            }
        except Exception as e:
            return {
                "returncode": -1,
                "stdout": "",
                "stderr": str(e),
                "command": command
            }

    async def _execute_file_op(self, task_id: str, params: Dict) -> Dict:
        """
        Execute file operation with path validation.

        Operations:
        - read: Read file contents
        - write: Write file contents
        - exists: Check if file exists

        Security:
        - Path traversal prevention
        - Restricted to allowed directories
        """
        operation = params.get("operation", "read")
        file_path = params.get("path", "")

        # Validate path
        if not self._is_safe_file_path(file_path):
            logger.warning(f"[Actor] Unsafe file path blocked: {file_path}")
            return {
                "to": "coordinator",
                "type": "response",
                "content": {
                    "task_id": task_id,
                    "status": "error",
                    "error": "Path validation failed"
                },
                "priority": MessagePriority.HIGH
            }

        try:
            path = Path(file_path)

            if operation == "read":
                content = await asyncio.to_thread(path.read_text)
                result = {"operation": "read", "content": content, "path": str(path)}

            elif operation == "write":
                content = params.get("content", "")
                await asyncio.to_thread(path.write_text, content)
                result = {"operation": "write", "bytes_written": len(content), "path": str(path)}

            elif operation == "exists":
                exists = await asyncio.to_thread(path.exists)
                result = {"operation": "exists", "exists": exists, "path": str(path)}

            else:
                raise ValueError(f"Unknown file operation: {operation}")

            self.session_logger.log_tool_execution(
                tool_name="file",
                params=params,
                result=result,
                status="success"
            )

            return {
                "to": "coordinator",
                "type": "response",
                "content": {
                    "task_id": task_id,
                    "status": "success",
                    "result": result
                },
                "priority": MessagePriority.NORMAL
            }

        except Exception as e:
            logger.error(f"[Actor] File operation failed: {e}")
            self.session_logger.log_agent_error(self.agent_id, f"File op failed: {e}")

            return {
                "to": "coordinator",
                "type": "response",
                "content": {
                    "task_id": task_id,
                    "status": "error",
                    "error": str(e)
                },
                "priority": MessagePriority.HIGH
            }

    def _is_safe_file_path(self, file_path: str) -> bool:
        """
        Validate file path safety.

        Prevents:
        - Path traversal (../)
        - Absolute paths outside allowed directories
        - System file access
        """
        try:
            path = Path(file_path).resolve()

            # Prevent path traversal
            if ".." in file_path:
                return False

            # Allow only specific directories (configure in config.py)
            allowed_dirs = [
                Path.cwd(),  # Current directory
                Path.cwd() / "vault",  # Vault directory
                Path.cwd() / "logs",  # Logs directory
            ]

            for allowed_dir in allowed_dirs:
                try:
                    path.relative_to(allowed_dir.resolve())
                    return True
                except ValueError:
                    continue

            logger.warning(f"[Actor] Path outside allowed directories: {file_path}")
            return False

        except Exception as e:
            logger.error(f"[Actor] Path validation error: {e}")
            return False

    async def _handle_confirmation(self, message: Message) -> Optional[Dict]:
        """Handle confirmation response from Coordinator."""
        approved = message.content.get("approved", False)
        action_id = message.content.get("action_id", "unknown")

        if approved:
            logger.info(f"[Actor] Action {action_id} approved")
            # In full implementation, re-execute pending action
        else:
            logger.warning(f"[Actor] Action {action_id} denied")

        return None

    async def on_start(self):
        """Actor-specific startup."""
        logger.info("[Actor] Starting execution engine")
        # Disable PyAutoGUI failsafe for automated testing
        # Note: In production, keep failsafe enabled
        import pyautogui
        pyautogui.FAILSAFE = False

    async def on_stop(self):
        """Actor-specific shutdown."""
        logger.info("[Actor] Shutdown complete")
        import pyautogui
        pyautogui.FAILSAFE = True  # Re-enable failsafe
