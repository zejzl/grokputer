# Validator Agent - Safety and quality verification for Pantheon
# Part of ORAM Pantheon/Swarm.

import logging
from typing import Any, Dict, Optional

from src.core.base_agent import BaseAgent
from src.core.message_bus import Message, MessagePriority

logger = logging.getLogger(__name__)


class ValidatorAgent(BaseAgent):
    """
    Validator Agent - Verifies outputs and ensures safety in the Pantheon system.

    Responsibilities:
    - Validate task outputs for correctness and safety
    - Check for potential security issues
    - Verify completion criteria are met
    - Send validation results back to coordinator

    Message Types Handled:
    - 'validate_output': Validate a completed task output
    - 'check_safety': Perform security validation
    """

    def __init__(self, agent_id: str, message_bus, session_logger, config: Dict[str, Any], action_executor=None):
        super().__init__(agent_id, message_bus, session_logger, config)
        self.action_executor = action_executor
        logger.info(f"[{self.agent_id}] Validator agent initialized")

    async def process_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process validation requests.

        Args:
            message: Message dict with 'type' and validation parameters

        Returns:
            Validation result dict or None
        """
        msg_type = message.get("type")

        if msg_type == "validate_output":
            return await self._validate_output(message)

        elif msg_type == "check_safety":
            return await self._check_safety(message)

        elif msg_type == "validate_bash":
            return await self._validate_bash_command(message)

        else:
            logger.warning(f"[{self.agent_id}] Unknown message type: {msg_type}")
            return None

    async def _validate_output(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate task output for correctness and completion.
        """
        output = message.get("output", {})
        task_context = message.get("task_context", {})

        # Basic validation checks
        validation_result = {"status": "valid", "score": 100, "checks": []}

        # Check for errors
        if "error" in str(output).lower():
            validation_result["status"] = "invalid"
            validation_result["score"] = 0
            validation_result["checks"].append("error_detected")

        # Check success indicators
        if output.get("status") == "success":
            validation_result["checks"].append("success_status")
        else:
            validation_result["score"] -= 20

        # Check for required fields
        required_fields = task_context.get("required_fields", [])
        for field in required_fields:
            if field not in output:
                validation_result["status"] = "invalid"
                validation_result["checks"].append(f"missing_field_{field}")
                validation_result["score"] -= 30

        logger.info(
            f"[{self.agent_id}] Validation complete: {validation_result['status']} ({validation_result['score']}%)"
        )

        return {
            "to": "coordinator",
            "type": "validation_result",
            "content": validation_result,
            "correlation_id": message.get("correlation_id"),
        }

    async def _check_safety(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform safety validation on commands or outputs.
        """
        content = message.get("content", "")

        # Basic safety checks
        safety_issues = []

        # Check for dangerous commands
        dangerous_patterns = ["rm -rf /", "sudo rm", "format", "dd if=", "shutdown", "reboot"]

        content_str = str(content).lower()
        for pattern in dangerous_patterns:
            if pattern in content_str:
                safety_issues.append(f"dangerous_command_{pattern}")

        # Check for sensitive data exposure
        if "password" in content_str or "api_key" in content_str:
            safety_issues.append("potential_data_exposure")

        result = {"safe": len(safety_issues) == 0, "issues": safety_issues}

        logger.info(f"[{self.agent_id}] Safety check: {'PASS' if result['safe'] else 'FAIL'}")

        return {
            "to": "coordinator",
            "type": "safety_result",
            "content": result,
            "correlation_id": message.get("correlation_id"),
        }

    async def _validate_bash_command(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate bash commands for safety, including godmode prevention.
        """
        command = message.get("command", "")

        # Import godmode safety protocols
        try:
            from src.safety.godmode_protocols import check_operation_safety
        except ImportError:
            logger.warning("Godmode safety protocols not available")
            check_operation_safety = lambda op, res: True

        # Basic safety checks
        safety_issues = []

        # Check for dangerous commands
        dangerous_patterns = [
            "rm -rf /",
            "sudo rm",
            "format",
            "dd if=",
            "shutdown",
            "reboot",
            "mkfs",
            "fdisk",
            ":(){ :|:& };:",  # Fork bomb
        ]

        command_str = str(command).lower()
        for pattern in dangerous_patterns:
            if pattern in command_str:
                safety_issues.append(f"dangerous_command_{pattern}")

        # Check for godmode triggers
        godmode_keywords = [
            "godmode",
            "unlimited",
            "infinite",
            "over_9000",
            "reality_warp",
            "time_rewind",
            "dimension_shift",
        ]

        for keyword in godmode_keywords:
            if keyword in command_str:
                safety_issues.append(f"godmode_trigger_{keyword}")

        # Check operation safety with godmode protocols
        operation_safe = check_operation_safety(
            "bash_command",
            {
                "cpu_percent": 5.0,  # Estimated CPU usage
                "memory_mb": 50,  # Estimated memory usage
                "max_execution_time": 30,
            },
        )

        if not operation_safe:
            safety_issues.append("godmode_safety_violation")

        result = {
            "valid": len(safety_issues) == 0 and operation_safe,
            "issues": safety_issues,
            "godmode_check": operation_safe,
        }

        logger.info(f"[{self.agent_id}] Bash validation: {'PASS' if result['valid'] else 'FAIL'}")

        return result
