"""
MAF-MessageBus Integration Layer

Connects the Multi-Agent Framework (MAF) orchestration system with the core MessageBus
for unified agent communication and coordination.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from src.collaboration.message_models import CollaborationMessage, MessageType
from src.collaboration.multi_provider_coordinator import (
    CollaborationConfig,
    ProviderRole,
)
from src.collaboration.orchestrator import OrchestrationResult, Orchestrator
from src.core.message_bus import Message, MessageBus, MessagePriority

logger = logging.getLogger(__name__)


@dataclass
class MAFMessageBusAdapter:
    """
    Adapter to bridge MAF orchestration with MessageBus communication.

    This allows MAF providers to communicate through the unified MessageBus
    instead of their own messaging system.
    """

    message_bus: MessageBus
    orchestrator: Orchestrator

    def __init__(self, message_bus: MessageBus, orchestrator: Orchestrator):
        self.message_bus = message_bus
        self.orchestrator = orchestrator
        self._task_mappings: Dict[str, str] = {}  # MAF task ID -> MessageBus task ID

    async def orchestrate_with_messagebus(
        self, task_prompt: str, collaboration_config: CollaborationConfig, task_type: str = "general"
    ) -> OrchestrationResult:
        """
        Run MAF orchestration with MessageBus integration.

        Args:
            task_prompt: The task to execute
            collaboration_config: MAF collaboration configuration
            task_type: Type of task for role assignment

        Returns:
            OrchestrationResult with MessageBus-integrated execution
        """

        # Create a unique MessageBus task ID for this MAF orchestration
        messagebus_task_id = f"maf_{task_type}_{hash(task_prompt) % 10000}"

        # Register this task mapping
        self._task_mappings[task_prompt] = messagebus_task_id

        # Send initial task message to MessageBus
        initial_message = Message(
            message_type="task_request",
            content={
                "task": task_prompt,
                "task_type": task_type,
                "providers": [p.provider_id for p in collaboration_config.providers],
                "maf_config": collaboration_config.__dict__,
            },
            priority=MessagePriority.HIGH,
            task_id=messagebus_task_id,
            source_agent="maf_orchestrator",
        )

        await self.message_bus.send_message(initial_message)

        # Run MAF orchestration with MessageBus monitoring
        try:
            result = await self.orchestrator.orchestrate_task(
                task_prompt=task_prompt, collaboration_config=collaboration_config, task_type=task_type
            )

            # Send completion message to MessageBus
            completion_message = Message(
                message_type="task_complete",
                content={
                    "task_id": messagebus_task_id,
                    "success": result.success,
                    "execution_time": result.execution_time,
                    "message_count": len(result.messages) if result.messages else 0,
                    "consensus": result.consensus_result.__dict__ if result.consensus_result else None,
                    "error": result.error_message,
                },
                priority=MessagePriority.NORMAL,
                task_id=messagebus_task_id,
                source_agent="maf_orchestrator",
            )

            await self.message_bus.send_message(completion_message)

            return result

        except Exception as e:
            # Send error message to MessageBus
            error_message = Message(
                message_type="task_error",
                content={"task_id": messagebus_task_id, "error": str(e), "task": task_prompt},
                priority=MessagePriority.URGENT,
                task_id=messagebus_task_id,
                source_agent="maf_orchestrator",
            )

            await self.message_bus.send_message(error_message)
            raise

    async def handle_messagebus_messages(self):
        """
        Listen for MessageBus messages and forward relevant ones to MAF orchestration.
        """
        while True:
            try:
                message = await self.message_bus.receive_message("maf_orchestrator")

                if message.message_type == "maf_status_request":
                    # Respond with current MAF status
                    status_message = Message(
                        message_type="maf_status_response",
                        content={"active_tasks": len(self._task_mappings), "orchestrator_status": "active"},
                        priority=MessagePriority.NORMAL,
                        task_id=message.task_id,
                        source_agent="maf_orchestrator",
                    )
                    await self.message_bus.send_message(status_message)

                elif message.message_type == "maf_task_cancel":
                    # Cancel a running MAF task
                    task_id = message.content.get("task_id")
                    if task_id in self._task_mappings:
                        # Note: Current orchestrator doesn't support cancellation
                        # This would need to be implemented in the orchestrator
                        logger.warning(f"MAF task cancellation requested for {task_id} but not implemented")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error handling MessageBus message in MAF adapter: {e}")


class MAFMessageBusCoordinator:
    """
    Coordinator that manages MAF operations through the MessageBus.

    This provides a unified interface for MAF operations that integrates
    with the broader agent ecosystem.
    """

    def __init__(self, message_bus: MessageBus):
        self.message_bus = message_bus
        self.orchestrator = None
        self.adapter = None

    async def initialize(self):
        """Initialize MAF components and MessageBus integration."""
        try:
            from src.collaboration import orchestrator as maf_orchestrator

            self.orchestrator = maf_orchestrator.orchestrator

            # Create adapter for MessageBus integration
            self.adapter = MAFMessageBusAdapter(self.message_bus, self.orchestrator)

            # Start MessageBus message handler
            asyncio.create_task(self.adapter.handle_messagebus_messages())

            logger.info("MAF-MessageBus integration initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize MAF-MessageBus integration: {e}")
            raise

    async def execute_maf_task(
        self, task: str, providers: List[str], config_name: str = "grok_claude_dual"
    ) -> Dict[str, Any]:
        """
        Execute a MAF task through the MessageBus-integrated system.

        Args:
            task: Task description
            providers: List of provider names
            config_name: MAF configuration preset

        Returns:
            Task execution results
        """

        if not self.adapter:
            raise RuntimeError("MAF-MessageBus integration not initialized")

        try:
            # Load MAF configuration
            from src.collaboration import maf_config_loader

            collaboration_config = maf_config_loader.load_config(config_name)

            # Configure providers
            from src.collaboration import ProviderCapability, ProviderRole

            provider_roles = []
            for provider_name in providers:
                base_capabilities = {
                    "grok": {
                        ProviderCapability.TEXT_GENERATION,
                        ProviderCapability.CRITICAL_THINKING,
                        ProviderCapability.RESEARCH,
                    },
                    "claude": {
                        ProviderCapability.TEXT_GENERATION,
                        ProviderCapability.VALIDATION,
                        ProviderCapability.CREATIVE_WRITING,
                    },
                    "openai": {
                        ProviderCapability.TEXT_GENERATION,
                        ProviderCapability.CODE_ANALYSIS,
                        ProviderCapability.MATHEMATICAL,
                    },
                    "gemini": {
                        ProviderCapability.TEXT_GENERATION,
                        ProviderCapability.RESEARCH,
                        ProviderCapability.CREATIVE_WRITING,
                    },
                }

                role = "primary_agent" if len(provider_roles) == 0 else f"agent_{len(provider_roles) + 1}"

                provider_role = ProviderRole(
                    provider_id=provider_name,
                    role=role,
                    weight=1.0,
                    capabilities=base_capabilities.get(provider_name, {ProviderCapability.TEXT_GENERATION}),
                )
                provider_roles.append(provider_role)

            collaboration_config.providers = provider_roles

            # Execute through MessageBus-integrated orchestrator
            result = await self.adapter.orchestrate_with_messagebus(
                task_prompt=task, collaboration_config=collaboration_config, task_type="general"
            )

            return {
                "success": result.success,
                "execution_time": result.execution_time,
                "message_count": len(result.messages) if result.messages else 0,
                "consensus": result.consensus_result.__dict__ if result.consensus_result else None,
                "error": result.error_message,
                "task_id": self.adapter._task_mappings.get(task),
            }

        except Exception as e:
            logger.error(f"MAF task execution failed: {e}")
            return {"success": False, "error": str(e), "execution_time": 0.0}


# Global instance for easy access
maf_messagebus_coordinator = None


async def initialize_maf_messagebus_integration(message_bus: MessageBus) -> MAFMessageBusCoordinator:
    """
    Initialize the MAF-MessageBus integration system.

    Args:
        message_bus: The core MessageBus instance

    Returns:
        Configured MAFMessageBusCoordinator
    """
    global maf_messagebus_coordinator

    if maf_messagebus_coordinator is None:
        maf_messagebus_coordinator = MAFMessageBusCoordinator(message_bus)
        await maf_messagebus_coordinator.initialize()

    return maf_messagebus_coordinator
