"""
Multi-Provider Coordinator for MAF (Multi-Agent Framework)

Orchestrates collaboration between multiple AI providers with dynamic provider selection,
weighted voting, and consensus-based decision making.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from .consensus import ConsensusDetector
from .message_models import (
    AgentRole,
    CollaborationMessage,
    ConsensusSignal,
    FinalPlan,
    MessageType,
)
from .output_generator import OutputGenerator
from .provider_pool import ProviderPool, provider_pool
from .provider_registry import (
    ProviderCapability,
    ProviderInstance,
    ProviderRegistry,
    provider_registry,
)

logger = logging.getLogger(__name__)


@dataclass
class ProviderRole:
    """Defines a provider's role in the collaboration."""

    provider_id: str
    role: str  # analyzer, critic, synthesizer, validator, etc.
    weight: float = 1.0  # Voting weight for this role
    capabilities: Set[ProviderCapability] = field(default_factory=set)


@dataclass
class CollaborationConfig:
    """Configuration for multi-provider collaboration."""

    providers: List[ProviderRole] = field(default_factory=list)
    max_rounds: int = 5
    convergence_threshold: float = 0.6
    review_mode: bool = False
    consensus_strategy: str = "weighted_vote"  # weighted_vote, majority, expert_consensus
    min_providers: int = 2
    max_providers: int = 6
    timeout_per_round: float = 60.0  # seconds


class MultiProviderCoordinator:
    """
    Orchestrates collaboration between multiple AI providers.

    Supports dynamic provider selection, role assignment, weighted voting,
    and consensus-based decision making for true multi-agent orchestration.
    """

    def __init__(self, config: CollaborationConfig, registry: ProviderRegistry = None, pool: ProviderPool = None):
        """
        Initialize multi-provider coordinator.

        Args:
            config: Collaboration configuration with providers and settings
            registry: Provider registry (uses global if None)
            pool: Provider pool (uses global if None)
        """
        self.config = config
        self.registry = registry or provider_registry
        self.pool = pool or provider_pool

        # Initialize infrastructure
        self.consensus_detector = ConsensusDetector(convergence_threshold=config.convergence_threshold)
        self.output_generator = OutputGenerator()

        # Collaboration state
        self.correlation_id = f"maf_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.message_history: List[CollaborationMessage] = []
        self.active_providers: Dict[str, ProviderInstance] = {}

        # Validate configuration
        self._validate_config()
        self._initialize_providers()

        logger.info(
            f"Multi-Provider Coordinator initialized: {self.correlation_id} "
            f"({len(self.active_providers)} providers, {config.max_rounds} max rounds)"
        )

    def _validate_config(self):
        """Validate collaboration configuration."""
        logger.info(f"Validating config with providers: {[p.provider_id for p in self.config.providers]}")
        if len(self.config.providers) < self.config.min_providers:
            raise ValueError(
                f"Need at least {self.config.min_providers} providers, " f"got {len(self.config.providers)}"
            )

        if len(self.config.providers) > self.config.max_providers:
            raise ValueError(f"Too many providers: {len(self.config.providers)} > {self.config.max_providers}")

        # Check provider availability
        for provider_role in self.config.providers:
            provider = self.registry.get_provider(provider_role.provider_id)
            if not provider:
                logger.error(
                    f"Provider {provider_role.provider_id} not found in registry. Available: {list(self.registry._providers.keys())}"
                )
                raise ValueError(f"Provider {provider_role.provider_id} not found in registry")
            logger.debug(f"Provider {provider_role.provider_id} validated: {provider.metadata.name}")

    def _initialize_providers(self):
        """Initialize active providers from configuration."""
        for provider_role in self.config.providers:
            provider = self.registry.get_provider(provider_role.provider_id)
            if provider:
                self.active_providers[provider_role.provider_id] = provider
                logger.debug(f"Activated provider: {provider_role.provider_id} ({provider_role.role})")

    async def run_collaboration(self, task_prompt: str) -> FinalPlan:
        """
        Main multi-provider collaboration loop.

        Args:
            task_prompt: User's task/prompt for collaboration

        Returns:
            FinalPlan with synthesized output from all providers
        """
        logger.info(f"Starting multi-provider collaboration: {task_prompt[:100]}...")

        try:
            # Run conversation rounds
            for round_num in range(1, self.config.max_rounds + 1):
                logger.info(f"Round {round_num}/{self.config.max_rounds}")

                # All providers respond in parallel
                await self._run_round(task_prompt, round_num)

                # Analyze for consensus
                consensus_signal = self.consensus_detector.analyze_round(self.message_history, round_num)

                logger.info(
                    f"Consensus check: {consensus_signal.recommendation} "
                    f"(confidence: {consensus_signal.confidence:.2f}, "
                    f"convergence: {consensus_signal.convergence_score:.2f})"
                )

                # Check if we should finalize
                if consensus_signal.recommendation == "FINALIZE":
                    logger.info(f"Consensus reached in round {round_num}")
                    break
                elif consensus_signal.recommendation == "MEDIATE":
                    logger.warning(f"Mediation recommended: {consensus_signal.reasoning}")
                    # Continue for multi-provider resolution

            # Generate final plan from all providers
            final_plan = await self._finalize_collaboration(task_prompt, consensus_signal)

            logger.info(
                f"Multi-provider collaboration complete. "
                f"Providers: {len(self.active_providers)}, Rounds: {round_num}"
            )

            return final_plan

        except Exception as e:
            logger.error(f"Multi-provider collaboration failed: {e}", exc_info=True)
            raise

    async def _run_round(self, task_prompt: str, round_number: int) -> None:
        """Execute a single conversation round with all providers."""

        # Create trigger message (broadcast to all providers)
        trigger = CollaborationMessage(
            message_id=f"msg_{round_number:03d}_trigger",
            correlation_id=self.correlation_id,
            message_type=MessageType.PROPOSAL if round_number == 1 else MessageType.FEEDBACK,
            sender=AgentRole.COORDINATOR,
            recipient=None,  # Broadcast
            round_number=round_number,
            content=task_prompt if round_number == 1 else "Continue discussion based on previous messages",
        )

        # Prepare provider tasks
        provider_tasks = []
        provider_ids = []

        for provider_role in self.config.providers:
            provider_id = provider_role.provider_id
            provider = self.active_providers.get(provider_id)

            if provider and provider.is_active:
                # Create a task for this provider
                task = self._process_provider_message(provider, provider_role, trigger, task_prompt)
                provider_tasks.append(task)
                provider_ids.append(provider_id)

        if not provider_tasks:
            raise RuntimeError("No active providers available for this round")

        logger.info(f"Round {round_number}: Processing {len(provider_tasks)} providers")

        # Execute all provider tasks concurrently with timeout
        try:
            responses = await asyncio.wait_for(
                asyncio.gather(*provider_tasks, return_exceptions=True), timeout=self.config.timeout_per_round
            )
        except asyncio.TimeoutError:
            logger.error(f"Round {round_number} timed out after {self.config.timeout_per_round}s")
            # Create error responses for timeout
            responses = []
            for i, provider_id in enumerate(provider_ids):
                error_msg = CollaborationMessage(
                    message_id=f"msg_{round_number:03d}_{provider_id}_timeout",
                    correlation_id=self.correlation_id,
                    message_type=MessageType.FEEDBACK,
                    sender=AgentRole.from_provider_id(provider_id),
                    round_number=round_number,
                    content=f"[Timeout: Provider {provider_id} exceeded {self.config.timeout_per_round}s limit]",
                )
                responses.append(error_msg)

        # Process responses
        for i, response in enumerate(responses):
            provider_id = provider_ids[i]

            if isinstance(response, Exception):
                logger.error(f"Provider {provider_id} failed in round {round_number}: {response}")
                # Create error message
                error_msg = CollaborationMessage(
                    message_id=f"msg_{round_number:03d}_{provider_id}_error",
                    correlation_id=self.correlation_id,
                    message_type=MessageType.FEEDBACK,
                    sender=AgentRole.from_provider_id(provider_id),
                    round_number=round_number,
                    content=f"[Error: Provider {provider_id} failed. See logs.]",
                )
                self.message_history.append(error_msg)
            else:
                # Valid response
                self.message_history.append(response)

        # Print responses for review mode
        if self.config.review_mode:
            self._print_round_review(round_number)

        logger.info(f"Round {round_number} complete. Messages: {len(self.message_history)}")

    async def _process_provider_message(
        self, provider: ProviderInstance, provider_role: ProviderRole, trigger: CollaborationMessage, task_prompt: str
    ) -> CollaborationMessage:
        """
        Process a message for a specific provider using the pool.

        This method adapts the existing agent interface to work with the new provider system.
        """
        try:
            # Use the provider pool to execute the operation
            # For now, we'll simulate the agent interface
            # TODO: Create a proper adapter layer

            # Create a mock agent-like interface
            provider_prompt = self._create_provider_prompt(provider_role, trigger, task_prompt)

            # Execute via pool (this would need the actual agent implementation)
            # For now, return a placeholder response
            response_content = await self._simulate_provider_response(provider, provider_role, provider_prompt)

            return CollaborationMessage(
                message_id=f"msg_{trigger.round_number:03d}_{provider_role.provider_id}",
                correlation_id=self.correlation_id,
                message_type=MessageType.FEEDBACK,
                sender=AgentRole.from_provider_id(provider_role.provider_id),
                round_number=trigger.round_number,
                content=response_content,
                metadata={
                    "provider_role": provider_role.role,
                    "provider_weight": provider_role.weight,
                    "capabilities": [cap.value for cap in provider_role.capabilities],
                },
            )

        except Exception as e:
            logger.error(f"Failed to process message for provider {provider_role.provider_id}: {e}")
            raise

    async def _simulate_provider_response(
        self, provider: ProviderInstance, provider_role: ProviderRole, prompt: str
    ) -> str:
        """
        Generate provider response using the provider's client.

        Uses the actual provider client (real or mock) to generate responses.
        """
        try:
            # Use the provider's client to generate a response
            if hasattr(provider.client, "generate_response"):
                # Mock provider client
                response = await provider.client.generate_response(prompt, provider_role.role)
            else:
                # Fallback for real providers (not implemented yet)
                response = f"Provider {provider.metadata.name} would respond here. Role: {provider_role.role}"

            return response

        except Exception as e:
            logger.error(f"Error generating response from provider {provider.metadata.name}: {e}")
            # Fallback response
            return f"As {provider_role.role} using {provider.metadata.name}, I acknowledge the task but encountered an error generating a full response."

    def _create_provider_prompt(
        self, provider_role: ProviderRole, trigger: CollaborationMessage, task_prompt: str
    ) -> str:
        """Create a role-specific prompt for the provider."""
        role_instructions = {
            "analyzer": "Analyze the task from multiple perspectives and identify key requirements.",
            "critic": "Critically evaluate the proposed approaches and identify potential issues.",
            "synthesizer": "Synthesize information from other providers and create unified solutions.",
            "validator": "Validate proposals for correctness, feasibility, and best practices.",
            "researcher": "Research additional information and provide data-driven insights.",
            "implementer": "Focus on practical implementation details and actionable steps.",
        }

        instruction = role_instructions.get(provider_role.role, f"Act as {provider_role.role}")

        prompt = f"""You are participating in a multi-provider collaboration as {provider_role.role}.

{instruction}

Task: {task_prompt}

Previous discussion context:
{self._get_recent_context()}

Provide your {provider_role.role} perspective on this task."""

        return prompt

    def _get_recent_context(self, max_messages: int = 10) -> str:
        """Get recent message context for provider prompts."""
        recent_messages = self.message_history[-max_messages:]
        if not recent_messages:
            return "No previous messages."

        context = []
        for msg in recent_messages:
            context.append(f"{msg.sender.value}: {msg.content[:200]}...")

        return "\n".join(context)

    async def _finalize_collaboration(self, task_prompt: str, final_consensus: ConsensusSignal) -> FinalPlan:
        """Generate final plan from all provider message history."""

        # Group messages by provider
        provider_messages = {}
        for provider_role in self.config.providers:
            provider_id = provider_role.provider_id
            messages = [m for m in self.message_history if m.sender.value == provider_id]
            provider_messages[provider_id] = messages

        # Synthesize unified plan from all providers
        unified_plan = await self.output_generator.synthesize_multi_provider_plan(
            provider_messages=provider_messages,
            consensus_signal=final_consensus,
            provider_roles={pr.provider_id: pr.role for pr in self.config.providers},
        )

        # Extract perspectives
        perspectives = {}
        for provider_id, messages in provider_messages.items():
            perspectives[provider_id] = "\n\n".join(m.content for m in messages)

        final_plan = FinalPlan(
            task_description=task_prompt,
            consensus_reached=final_consensus.is_consensus,
            total_rounds=max(m.round_number for m in self.message_history) if self.message_history else 0,
            claude_perspective="",  # Legacy field, keep empty
            grok_perspective="",  # Legacy field, keep empty
            unified_plan=unified_plan,
            key_agreements=final_consensus.agreement_indicators,
            key_disagreements=final_consensus.disagreement_indicators,
            metadata={
                "correlation_id": self.correlation_id,
                "convergence_score": final_consensus.convergence_score,
                "confidence": final_consensus.confidence,
                "total_messages": len(self.message_history),
                "providers_used": list(self.active_providers.keys()),
                "provider_roles": {pr.provider_id: pr.role for pr in self.config.providers},
                "framework": "MAF",  # Multi-Agent Framework
            },
        )

        return final_plan

    def _print_round_review(self, round_number: int):
        """Print round review for human inspection."""
        print(f"\n{'='*60}")
        print(f"ROUND {round_number} REVIEW")
        print(f"{'='*60}")

        round_messages = [m for m in self.message_history if m.round_number == round_number]

        for msg in round_messages:
            print(f"\n{msg.sender.value.upper()} ({msg.metadata.get('provider_role', 'unknown')}):")
            print(f"{msg.content}")
            print("-" * 40)

        input("Press Enter to continue...")

    def get_collaboration_stats(self) -> Dict[str, Any]:
        """Get statistics about the collaboration."""
        return {
            "correlation_id": self.correlation_id,
            "total_rounds": max(m.round_number for m in self.message_history) if self.message_history else 0,
            "total_messages": len(self.message_history),
            "active_providers": len(self.active_providers),
            "provider_roles": {pr.provider_id: pr.role for pr in self.config.providers},
            "message_types": {
                msg_type.value: len([m for m in self.message_history if m.message_type == msg_type])
                for msg_type in MessageType
            },
        }


# Backward compatibility - keep the old coordinator
class CollaborationCoordinator(MultiProviderCoordinator):
    """
    Legacy coordinator for backward compatibility with existing -mb mode.

    Automatically configures for Grok + Claude dual-agent collaboration.
    """

    def __init__(
        self,
        claude_api_key: str = None,
        grok_api_key: str = None,
        max_rounds: int = 5,
        convergence_threshold: float = 0.6,
        review_mode: bool = False,
    ):
        # Create legacy config
        providers = []
        if grok_api_key:
            providers.append(
                ProviderRole(
                    provider_id="grok",
                    role="primary_agent",
                    weight=1.0,
                    capabilities={ProviderCapability.TEXT_GENERATION, ProviderCapability.CRITICAL_THINKING},
                )
            )
        if claude_api_key:
            providers.append(
                ProviderRole(
                    provider_id="claude",
                    role="secondary_agent",
                    weight=1.0,
                    capabilities={ProviderCapability.TEXT_GENERATION, ProviderCapability.VALIDATION},
                )
            )

        config = CollaborationConfig(
            providers=providers,
            max_rounds=max_rounds,
            convergence_threshold=convergence_threshold,
            review_mode=review_mode,
            min_providers=1,  # Allow Grok-only mode
            max_providers=2,  # Legacy dual-agent limit
        )

        super().__init__(config)
