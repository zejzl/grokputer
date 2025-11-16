import re
from typing import Any, Dict, List

from src.core.base_agent import BaseAgent
from src.core.message_bus import Message, MessagePriority
from src.ethics.ethical_bounds import ethical_bounds


class GuardianAgent(BaseAgent):
    """Guardian Agent: Safety scanning for actions before execution.

    Intercepts proposed actions from other agents, assesses risks, and approves/rejects.
    Uses regex for dangerous commands, ethical checks, and context analysis.
    """

    def __init__(self, agent_id: str = "guardian", message_bus=None, session_logger=None, config=None):
        super().__init__(agent_id, message_bus, session_logger, config)
        self.dangerous_patterns = [
            r"rm\s+-rf\s+/",  # Unix delete all
            r"del\s+/f\s+/s\s+",  # Windows delete recursive
            r"format\s+c:",  # Disk format
            r"shutdown\s+-s",  # System shutdown
            r"net\s+user\s+.*\s+/delete",  # User deletion
            r"\\system32",  # Sensitive system dir
            r"\\windows\\system32",  # Windows system
            r"password",  # Sensitive keywords
            r"credit card",  # PII
        ]
        self.ethical_checker = ethical_bounds

    async def process_message(self, message: Message) -> List[Message]:
        """Process incoming messages, intercept actions."""
        responses = []

        if message.message_type == "proposed_action":
            action_data = message.content
            assessment = self.assess_risk(action_data)

            if assessment["risk_level"] == "low":
                # Approve
                approval_msg = Message(
                    from_agent=self.agent_id,
                    to_agent=message.from_agent,
                    message_type="action_approved",
                    content={"action_id": action_data.get("action_id"), "reason": "Approved - low risk"},
                    priority=MessagePriority.NORMAL,
                )
                responses.append(approval_msg)
                self.session_logger.log_agent_activity(
                    self.agent_id, f"Approved action: {action_data.get('command', 'N/A')}"
                )
            else:
                # Reject
                rejection_msg = Message(
                    from_agent=self.agent_id,
                    to_agent=message.from_agent,
                    message_type="action_rejected",
                    content={
                        "action_id": action_data.get("action_id"),
                        "reason": assessment["reason"],
                        "risk_level": assessment["risk_level"],
                    },
                    priority=MessagePriority.HIGH,
                )
                responses.append(rejection_msg)
                self.session_logger.log_agent_activity(
                    self.agent_id, f"Rejected action: {action_data.get('command', 'N/A')} - {assessment['reason']}"
                )

        return responses

    def assess_risk(self, action_data: Dict[str, Any]) -> Dict[str, Any]:
        """Assess risk of proposed action."""
        command = action_data.get("command", "")
        context = action_data.get("context", "")
        full_text = f"{command} {context}"

        # Regex scan for dangerous patterns
        for pattern in self.dangerous_patterns:
            if re.search(pattern, full_text, re.IGNORECASE):
                return {
                    "risk_level": "high",
                    "reason": f"Dangerous pattern detected: {pattern}",
                    "suggestion": "Review or modify action",
                }

        # Ethical check
        ethical_score = self.ethical_checker.evaluate_action(command)
        if ethical_score < 0.5:
            return {
                "risk_level": "medium",
                "reason": f"Ethical score low: {ethical_score}",
                "suggestion": "Ethical review needed",
            }

        # Context analysis (simple keyword check)
        sensitive_keywords = ["delete", "remove", "shutdown", "password", "secret"]
        if any(keyword in full_text.lower() for keyword in sensitive_keywords):
            return {
                "risk_level": "low_medium",
                "reason": "Sensitive keywords detected, but no high-risk patterns",
                "suggestion": "Double-check intent",
            }

        return {"risk_level": "low", "reason": "Action appears safe", "suggestion": "Proceed"}

    async def run(self):
        """Run the guardian agent."""
        self.session_logger.log_agent_start(self.agent_id)
        print(f"[{self.agent_id}] Guardian agent started - monitoring for risks")

        while True:
            message = await self.message_bus.receive_message(to_agent=self.agent_id)
            if message:
                responses = await self.process_message(message)
                for response in responses:
                    await self.message_bus.send(response)

            await asyncio.sleep(0.1)  # Poll interval

        self.session_logger.log_agent_stop(self.agent_id)
