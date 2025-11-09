"""
Tool execution module for Grokputer.
Executes tool calls from Grok including computer control, bash, and custom tools.
"""

import json
import logging
import subprocess
import shlex
import os
from typing import Dict, Any, List
import pyautogui
from src import config
from src.tools import execute_tool as execute_custom_tool

logger = logging.getLogger(__name__)


class ToolExecutor:
    """
    Handles execution of all tool calls from Grok.
    """

    def __init__(self, require_confirmation: bool = None):
        """
        Initialize the tool executor.

        Args:
            require_confirmation: Whether to require confirmation for destructive actions
        """
        self.require_confirmation = (
            require_confirmation
            if require_confirmation is not None
            else config.REQUIRE_CONFIRMATION
        )

        logger.info(f"Tool executor initialized: require_confirmation={self.require_confirmation}")

    def execute_tool_calls(self, tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Execute a list of tool calls and return results.

        Args:
            tool_calls: List of tool call dictionaries from Grok

        Returns:
            List of results for each tool call
        """
        results = []

        for tool_call in tool_calls:
            try:
                tool_call_id = tool_call.get("id", "")
                tool_type = tool_call.get("type", "function")
                function_info = tool_call.get("function", {})
                function_name = function_info.get("name", "")

                # Parse arguments (may be JSON string)
                arguments = function_info.get("arguments", {})
                if isinstance(arguments, str):
                    try:
                        arguments = json.loads(arguments)
                    except json.JSONDecodeError:
                        arguments = {}

                logger.info(f"Executing tool: {function_name} with args: {arguments}")

                # Route to appropriate handler
                if function_name == "bash":
                    result = self._execute_bash(arguments)
                elif function_name == "computer":
                    result = self._execute_computer(arguments)
                elif function_name in ["scan_vault", "invoke_prayer", "get_vault_stats", "mcp_vault_operation"]:
                    result = execute_custom_tool(function_name, **arguments)
                else:
                    result = {
                        "status": "error",
                        "error": f"Unknown tool: {function_name}"
                    }

                results.append({
                    "tool_call_id": tool_call_id,
                    "function_name": function_name,
                    "result": result
                })

            except Exception as e:
                logger.error(f"Error executing tool call: {e}")
                results.append({
                    "tool_call_id": tool_call.get("id", ""),
                    "function_name": tool_call.get("function", {}).get("name", "unknown"),
                    "result": {
                        "status": "error",
                        "error": str(e)
                    }
                })

        return results

    def _execute_bash(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a bash command with safety scoring and shell injection prevention.

        Args:
            arguments: Dictionary with 'command' key

        Returns:
            Execution result
        """
        command = arguments.get("command", "")

        if not command:
            return {"status": "error", "error": "No command provided"}

        # Calculate safety score
        safety_score = config.get_command_safety_score(command)
        risk_level = "LOW" if safety_score <= 30 else "MEDIUM" if safety_score <= 70 else "HIGH"

        # Log safety assessment
        logger.info(f"Command safety score: {safety_score}/100 (risk: {risk_level}) - {command}")

        # SECURITY: Sanitize input to prevent shell injection
        dangerous_chars = [';', '&', '|', '<', '>', '$', '`', '\\', '\n']
        if any(char in command for char in dangerous_chars):
            logger.error(f"Command contains dangerous shell metacharacters: {command}")
            return {
                "status": "error",
                "error": "Command contains dangerous shell metacharacters (;, &, |, <, >, $, `, \\). Use shell=False with explicit arguments instead.",
                "safety_score": 100,  # Maximum risk
                "risk_level": "CRITICAL"
            }

        # Determine if confirmation is needed
        needs_confirmation = config.requires_confirmation(command)

        # Confirm if required
        if needs_confirmation:
            confirm = self._confirm_action(
                f"Execute bash command (risk: {risk_level}, score: {safety_score}/100): {command}"
            )
            if not confirm:
                logger.warning(f"User cancelled high-risk command: {command}")
                return {
                    "status": "cancelled",
                    "message": "User cancelled bash execution",
                    "safety_score": safety_score,
                    "risk_level": risk_level
                }

        try:
            logger.info(f"Executing bash: {command}")

            # SECURITY FIX: Parse command safely and execute without shell
            # This prevents shell injection attacks by avoiding shell interpretation
            try:
                # Use shlex to safely parse command into argument list
                argv = shlex.split(command)
            except ValueError as e:
                logger.error(f"Failed to parse command: {e}")
                return {
                    "status": "error",
                    "error": f"Malformed command: {str(e)}",
                    "safety_score": safety_score
                }

            # Execute with shell=False (SECURE: no shell interpretation)
            result = subprocess.run(
                argv,  # List of arguments instead of string
                shell=False,  # SECURE: Prevents shell injection
                capture_output=True,
                text=True,
                timeout=30,
                env={**os.environ}  # Explicit environment passing
            )

            return {
                "status": "success",
                "command": command,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
                "safety_score": safety_score,
                "risk_level": risk_level
            }

        except subprocess.TimeoutExpired:
            return {
                "status": "error",
                "error": "Command timed out (30s limit)",
                "safety_score": safety_score
            }
        except FileNotFoundError:
            # Command not found in PATH
            return {
                "status": "error",
                "error": f"Command not found: {argv[0] if argv else command}",
                "safety_score": safety_score
            }
        except Exception as e:
            logger.error(f"Error executing bash: {e}")
            return {
                "status": "error",
                "error": str(e),
                "safety_score": safety_score
            }

    def _execute_computer(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute computer control actions (mouse, keyboard, etc.).

        Args:
            arguments: Dictionary with action, coordinate, text, etc.

        Returns:
            Execution result
        """
        action = arguments.get("action", "")

        if not action:
            return {"status": "error", "error": "No action specified"}

        try:
            # Mouse actions
            if action == "mouse_move":
                coordinate = arguments.get("coordinate", [])
                if len(coordinate) != 2:
                    return {"status": "error", "error": "Invalid coordinate"}

                x, y = coordinate
                pyautogui.moveTo(x, y, duration=0.2)
                logger.info(f"Mouse moved to ({x}, {y})")

                return {
                    "status": "success",
                    "action": "mouse_move",
                    "coordinate": [x, y]
                }

            elif action == "left_click":
                coordinate = arguments.get("coordinate")

                # Confirm if required
                if self.require_confirmation:
                    msg = f"Click at {coordinate}" if coordinate else "Click at current position"
                    confirm = self._confirm_action(msg)
                    if not confirm:
                        return {"status": "cancelled", "message": "User cancelled click"}

                if coordinate and len(coordinate) == 2:
                    x, y = coordinate
                    pyautogui.click(x, y)
                    logger.info(f"Left click at ({x}, {y})")
                else:
                    pyautogui.click()
                    logger.info("Left click at current position")

                return {"status": "success", "action": "left_click"}

            elif action == "right_click":
                coordinate = arguments.get("coordinate")

                if coordinate and len(coordinate) == 2:
                    x, y = coordinate
                    pyautogui.rightClick(x, y)
                    logger.info(f"Right click at ({x}, {y})")
                else:
                    pyautogui.rightClick()
                    logger.info("Right click at current position")

                return {"status": "success", "action": "right_click"}

            elif action == "double_click":
                coordinate = arguments.get("coordinate")

                if coordinate and len(coordinate) == 2:
                    x, y = coordinate
                    pyautogui.doubleClick(x, y)
                    logger.info(f"Double click at ({x}, {y})")
                else:
                    pyautogui.doubleClick()
                    logger.info("Double click at current position")

                return {"status": "success", "action": "double_click"}

            elif action == "type":
                text = arguments.get("text", "")

                if not text:
                    return {"status": "error", "error": "No text provided"}

                pyautogui.typewrite(text, interval=0.05)
                logger.info(f"Typed text: {text[:50]}...")

                return {
                    "status": "success",
                    "action": "type",
                    "text": text
                }

            elif action == "key":
                key = arguments.get("text", "")

                if not key:
                    return {"status": "error", "error": "No key specified"}

                pyautogui.press(key)
                logger.info(f"Pressed key: {key}")

                return {"status": "success", "action": "key", "key": key}

            elif action == "scroll":
                amount = arguments.get("amount", 0)

                pyautogui.scroll(amount)
                logger.info(f"Scrolled: {amount}")

                return {"status": "success", "action": "scroll", "amount": amount}

            elif action == "screenshot":
                # This is handled by screen_observer, return success
                return {
                    "status": "success",
                    "action": "screenshot",
                    "message": "Screenshot is handled by observer"
                }

            else:
                return {
                    "status": "error",
                    "error": f"Unknown computer action: {action}"
                }

        except Exception as e:
            logger.error(f"Error executing computer action: {e}")
            return {
                "status": "error",
                "error": str(e),
                "action": action
            }

    def _confirm_action(self, message: str) -> bool:
        """
        Ask user to confirm an action.

        Args:
            message: Confirmation message

        Returns:
            True if confirmed, False otherwise
        """
        try:
            response = input(f"\n[CONFIRM] {message}\nConfirm? (y/n): ").strip().lower()
            return response in ['y', 'yes']
        except (KeyboardInterrupt, EOFError):
            return False
