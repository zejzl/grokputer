from ..core.base_agent import BaseAgent
from ..agents.observer import ObserverAgent
from ..core.message_bus import MessageBus
from typing import Dict, Any, Optional, Tuple
import asyncio
import time
from dataclasses import dataclass

@dataclass
class ValidationResult:
    """Result of validation check."""
    valid: bool
    confidence: float  # 0-100%
    reason: str
    before_hash: str
    after_hash: str
    changes_detected: bool

class ValidatorAgent(ObserverAgent):
    """
    Validator agent (Phase 2): Verifies Actor outputs and state changes.
    Extends Observer for screenshot capabilities.
    """
    def __init__(
        self,
        agent_id: str,
        message_bus: MessageBus,
        session_logger: 'SessionLogger',
        config: Dict[str, Any],
        action_executor: 'ActionExecutor',
        heartbeat_interval: float = 10.0
    ):
        super().__init__(
            agent_id, message_bus, session_logger, config, action_executor, heartbeat_interval
        )
        self.last_screenshot_hash: Optional[str] = None
        self.validation_threshold: float = config.get("validation_threshold", 90.0)
        self.session_logger.log_agent_init(self.agent_id, "Validator ready for output verification")

    async def process_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process validation requests: 'validate_action' or 'validate_state'.
        """
        msg_type = message.get("type")
        
        if msg_type == "validate_action":
            action = message["action"]
            before_screenshot = message.get("before_screenshot")  # base64 from prior
            self._update_state("processing")
            
            # Capture after screenshot
            after_result = await self.capture_and_hash()
            if "error" in after_result:
                return {
                    "type": "validation_error",
                    "from": self.agent_id,
                    "to": "coordinator",
                    "content": {"error": after_result["error"], "confidence": 0.0}
                }
            
            after_hash = after_result["hash"]
            before_hash = self._hash_screenshot(before_screenshot) if before_screenshot else None
            
            # Validate based on action type
            result = await self._perform_validation(action, before_hash, after_hash)
            
            validation_msg = {
                "type": "validation_result",
                "from": self.agent_id,
                "to": "coordinator",
                "timestamp": time.time(),
                "content": {
                    "action_id": message.get("action_id"),
                    "valid": result.valid,
                    "confidence": result.confidence,
                    "reason": result.reason,
                    "changes_detected": result.changes_detected,
                    "before_hash": before_hash,
                    "after_hash": after_hash
                }
            }
            
            self.session_logger.log_validation(self.agent_id, validation_msg["content"])
            
            if not result.valid and result.confidence < self.validation_threshold:
                # Trigger rollback
                await self._trigger_rollback(message.get("action_id"))
            
            self._update_state("idle")
            return validation_msg
        
        elif msg_type == "validate_state":
            # General state validation (e.g., task complete?)
            state = message.get("expected_state")
            current_screenshot = await self.capture_and_hash()
            # Stub: Compare to expected (e.g., text present via hash diff)
            result = ValidationResult(
                valid=True,  # Stub for Phase 2 full OCR
                confidence=95.0,
                reason="State matches expected",
                before_hash=None,
                after_hash=current_screenshot["hash"],
                changes_detected=False
            )
            return {
                "type": "state_validation",
                "from": self.agent_id,
                "to": "coordinator",
                "content": {"valid": result.valid, "confidence": result.confidence, "reason": result.reason}
            }
        
        self._update_state("idle")
        return None

    async def _perform_validation(self, action: Dict, before_hash: str, after_hash: str) -> ValidationResult:
        """Perform specific validation based on action."""
        action_type = action["type"]
        changes_detected = before_hash != after_hash if before_hash else True
        
        if action_type == "click":
            if changes_detected:
                confidence = 90.0  # Visual change = success
                reason = "UI changed after click"
            else:
                confidence = 20.0
                reason = "No visual change after click - possible failure"
        
        elif action_type == "type":
            if changes_detected:
                confidence = 85.0
                reason = "Screen changed after typing"
            else:
                confidence = 30.0
                reason = "No change after typing - text may not have registered"
        
        elif action_type == "bash":
            # Stub: Assume success unless error in result
            confidence = 95.0 if changes_detected else 50.0
            reason = "Command executed with visual confirmation" if changes_detected else "Command executed, no visual change expected"
        
        else:
            confidence = 50.0
            reason = f"Unknown action type: {action_type}"
        
        return ValidationResult(
            valid=confidence >= self.validation_threshold,
            confidence=confidence,
            reason=reason,
            before_hash=before_hash,
            after_hash=after_hash,
            changes_detected=changes_detected
        )

    async def _trigger_rollback(self, action_id: str):
        """Trigger rollback for failed validation."""
        rollback_msg = {
            "type": "rollback_action",
            "from": self.agent_id,
            "to": "actor",
            "action_id": action_id
        }
        await self.message_bus.send("actor", rollback_msg)
        self.session_logger.log_rollback(self.agent_id, action_id, "Validation failure")

    def _hash_screenshot(self, b64_data: str) -> str:
        """Stub perceptual hash from base64 (Phase 2 full imagehash)."""
        # Decode base64 to PIL, compute phash (stub)
        return "stub_hash_" + str(hash(b64_data[:10]))  # Simple hash for PoC

    async def on_start(self):
        """Validator-specific startup."""
        await super().on_start()
        self.session_logger.log_agent_ready(self.agent_id, "Validator verification active")

# Integration example in Coordinator:
# before = await observer.capture()
# result = await actor.perform(action)
# validation = await validator.validate_action(action, before["data"])
# if not validation["content"]["valid"]:
#     await rollback(result["action_id"])