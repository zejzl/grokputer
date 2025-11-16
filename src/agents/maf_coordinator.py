# src/agents/maf_coordinator.py
"""
MAF Coordinator Agent: Integrates Multi-Agent Framework with Pantheon.
Uses MAF orchestrator for complex multi-perspective tasks.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.collaboration.message_models import (
    AgentRole,
    CollaborationMessage,
    MessageType,
)
from src.collaboration.multi_provider_coordinator import (
    CollaborationConfig,
    ProviderRole,
)
from src.collaboration.orchestrator import (
    OrchestrationConfig,
    OrchestrationStrategy,
    Orchestrator,
)
from src.core.base_agent import BaseAgent
from src.core.message_bus import Message, MessageBus, MessagePriority
from src.observability.session_logger import SessionLogger


class MAFCoordinator(BaseAgent):
    """Coordinator agent that integrates MAF orchestration capabilities."""

    def __init__(
        self,
        agent_id: str,
        message_bus: MessageBus,
        session_logger: SessionLogger,
        config: Dict[str, Any] = None,
    ):
        super().__init__(agent_id, message_bus, session_logger, config)
        self.logger = logging.getLogger(__name__)
        self.orchestrator = Orchestrator(
            OrchestrationConfig(
                strategy=OrchestrationStrategy.CONCURRENT,
                max_concurrent_providers=6,
                timeout_per_provider=60.0,
            )
        )
        self.logger.info("MAF Coordinator initialized with concurrent orchestration")

    async def process_message(self, message: Message) -> Optional[Dict[str, Any]]:
        """Process incoming messages and orchestrate MAF tasks when appropriate."""
        content = message.content
        task_type = content.get("task_type", "general")
        task_prompt = content.get("task", "")

        if not task_prompt:
            return {"status": "error", "message": "No task provided for MAF orchestration"}

        # Determine if this task needs MAF orchestration
        if self._should_use_maf(task_type, content):
            return await self._orchestrate_maf_task(task_prompt, task_type, content)
        else:
            # For simple tasks, delegate to regular coordinator
            return {
                "status": "delegated",
                "message": f"Task delegated to regular coordinator (not MAF)",
                "task_type": task_type,
            }

    def _should_use_maf(self, task_type: str, content: Dict[str, Any]) -> bool:
        """Determine if MAF orchestration is needed."""
        # Use MAF for complex tasks requiring multiple perspectives
        maf_task_types = ["creative", "research", "code_review", "analysis", "planning"]
        explicit_maf = content.get("use_maf", False)

        return task_type in maf_task_types or explicit_maf

    async def _orchestrate_maf_task(self, task_prompt: str, task_type: str, content: Dict[str, Any]) -> Dict[str, Any]:
        """Orchestrate a task using MAF."""
        try:
            # Create collaboration config
            collab_config = CollaborationConfig(
                providers=[],  # Will be assigned by orchestrator
                max_rounds=content.get("max_rounds", 3),
                convergence_threshold=content.get("convergence_threshold", 0.7),
                review_mode=content.get("review_mode", False),
            )

            # Run orchestration
            result = await self.orchestrator.orchestrate_task(task_prompt, collab_config, task_type)

            if result.success:
                # Extract final consensus
                consensus = result.consensus_result
                final_content = ""

                if consensus and consensus.is_consensus:
                    # Find the most recent synthesizer or final message
                    synthesizer_msgs = [
                        msg
                        for msg in result.messages
                        if hasattr(msg, "sender_role") and msg.sender_role == "synthesizer"
                    ]
                    if synthesizer_msgs:
                        final_content = synthesizer_msgs[-1].content
                    else:
                        # Use last message as fallback
                        final_content = result.messages[-1].content if result.messages else "No content generated"
                else:
                    # Aggregate all messages
                    final_content = "\n\n".join([msg.content for msg in result.messages[-3:]])  # Last 3 messages

                return {
                    "status": "success",
                    "content": final_content,
                    "consensus_reached": consensus.is_consensus if consensus else False,
                    "confidence": consensus.confidence if consensus else 0.0,
                    "messages_processed": len(result.messages),
                    "execution_time": result.execution_time,
                }
            else:
                return {
                    "status": "error",
                    "message": f"MAF orchestration failed: {result.error_message}",
                    "failed_providers": result.failed_providers,
                }

        except Exception as e:
            self.logger.error(f"MAF orchestration error: {e}", exc_info=True)
            return {"status": "error", "message": f"MAF orchestration failed: {str(e)}"}

    async def get_status(self) -> Dict[str, Any]:
        """Get MAF coordinator status."""
        stats = self.orchestrator.get_orchestration_stats()
        return {
            "agent_id": self.agent_id,
            "status": "active",
            "maf_stats": stats,
            "supported_task_types": ["creative", "research", "code_review", "analysis", "planning"],
        }
