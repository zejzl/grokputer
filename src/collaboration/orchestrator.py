"""
Orchestrator for Multi-Agent Framework (MAF)

Async orchestration with role assignment, timeouts, and concurrent provider execution.
Manages the flow of multi-provider collaboration with proper error handling and coordination.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
import time

from .provider_registry import ProviderRegistry, ProviderInstance, ProviderCapability, provider_registry
from .provider_pool import ProviderPool, provider_pool
from .multi_provider_coordinator import ProviderRole, CollaborationConfig
from .message_models import CollaborationMessage, MessageType, AgentRole
from .consensus_manager import ConsensusManager, ConsensusResult

logger = logging.getLogger(__name__)


class OrchestrationStrategy(Enum):
    """Strategies for orchestrating multi-provider execution."""

    SEQUENTIAL = "sequential"  # One provider at a time
    CONCURRENT = "concurrent"  # All providers simultaneously
    ROLE_BASED = "role_based"  # Execute by role groups
    PIPELINED = "pipelined"  # Pass results between providers


@dataclass
class OrchestrationConfig:
    """Configuration for orchestration behavior."""

    strategy: OrchestrationStrategy = OrchestrationStrategy.CONCURRENT
    max_concurrent_providers: int = 6
    timeout_per_provider: float = 60.0
    retry_attempts: int = 2
    enable_circuit_breaker: bool = True
    role_execution_order: List[str] = field(
        default_factory=lambda: ["analyzer", "researcher", "critic", "synthesizer", "validator", "implementer"]
    )


@dataclass
class RoleAssignment:
    """Assignment of providers to roles for a task."""

    role: str
    providers: List[ProviderInstance] = field(default_factory=list)
    required_capabilities: Set[ProviderCapability] = field(default_factory=set)
    min_providers: int = 1
    max_providers: int = 3
    priority: int = 1  # Higher priority roles execute first


@dataclass
class OrchestrationResult:
    """Result of an orchestration execution."""

    success: bool
    messages: List[CollaborationMessage] = field(default_factory=list)
    failed_providers: List[str] = field(default_factory=list)
    execution_time: float = 0.0
    consensus_result: Optional[ConsensusResult] = None
    error_message: str = ""


class RoleAssigner:
    """
    Assigns providers to roles based on capabilities and availability.
    """

    def __init__(self, registry: ProviderRegistry = None):
        self.registry = registry or provider_registry

    def assign_roles_for_task(
        self,
        task_description: str,
        available_providers: List[ProviderInstance],
        role_requirements: Dict[str, RoleAssignment],
    ) -> Dict[str, List[ProviderInstance]]:
        """
        Assign providers to roles based on task requirements.

        Args:
            task_description: Description of the task
            available_providers: List of available provider instances
            role_requirements: Requirements for each role

        Returns:
            Dictionary mapping role names to assigned providers
        """
        assignments = {}

        # Sort roles by priority (higher priority first)
        sorted_roles = sorted(role_requirements.items(), key=lambda x: x[1].priority, reverse=True)

        # Track assigned providers to avoid double assignment
        assigned_providers = set()

        for role_name, role_req in sorted_roles:
            candidates = []

            # Find providers that match the role requirements
            for provider in available_providers:
                if provider.metadata.name in assigned_providers:
                    continue

                # Check if provider has required capabilities
                if role_req.required_capabilities.issubset(provider.metadata.capabilities):
                    candidates.append(provider)

            # Sort candidates by suitability (reliability, speed, etc.)
            candidates.sort(
                key=lambda p: (
                    p.metadata.reliability_score * p.weight,
                    -p.metadata.response_time_ms,  # Faster is better
                ),
                reverse=True,
            )

            # Assign top candidates up to max_providers
            assigned = candidates[: role_req.max_providers]
            assignments[role_name] = assigned

            # Mark providers as assigned
            for provider in assigned:
                assigned_providers.add(provider.metadata.name)

            logger.debug(
                f"Assigned {len(assigned)} providers to role '{role_name}': " f"{[p.metadata.name for p in assigned]}"
            )

        return assignments

    def create_default_role_requirements(self, task_type: str = "general") -> Dict[str, RoleAssignment]:
        """
        Create default role requirements based on task type.

        Args:
            task_type: Type of task (general, code_review, creative, etc.)

        Returns:
            Dictionary of role requirements
        """
        base_requirements = {
            "analyzer": RoleAssignment(
                role="analyzer",
                required_capabilities={ProviderCapability.CRITICAL_THINKING, ProviderCapability.TEXT_GENERATION},
                min_providers=1,
                max_providers=2,
                priority=5,
            ),
            "critic": RoleAssignment(
                role="critic",
                required_capabilities={ProviderCapability.CRITICAL_THINKING, ProviderCapability.VALIDATION},
                min_providers=1,
                max_providers=2,
                priority=4,
            ),
            "synthesizer": RoleAssignment(
                role="synthesizer",
                required_capabilities={ProviderCapability.SYNTHESIS, ProviderCapability.TEXT_GENERATION},
                min_providers=1,
                max_providers=1,
                priority=3,
            ),
            "validator": RoleAssignment(
                role="validator",
                required_capabilities={ProviderCapability.VALIDATION},
                min_providers=1,
                max_providers=2,
                priority=2,
            ),
        }

        # Adjust requirements based on task type
        if task_type == "code_review":
            base_requirements["analyzer"].required_capabilities.add(ProviderCapability.CODE_ANALYSIS)
            base_requirements["critic"].required_capabilities.add(ProviderCapability.CODE_ANALYSIS)
            base_requirements["validator"].required_capabilities.add(ProviderCapability.CODE_ANALYSIS)

        elif task_type == "creative":
            base_requirements["synthesizer"].required_capabilities.add(ProviderCapability.CREATIVE_WRITING)
            base_requirements["analyzer"].required_capabilities.add(ProviderCapability.RESEARCH)

        elif task_type == "research":
            base_requirements["analyzer"].required_capabilities.add(ProviderCapability.RESEARCH)
            base_requirements["critic"].required_capabilities.add(ProviderCapability.RESEARCH)

        return base_requirements


class Orchestrator:
    """
    Orchestrates multi-provider execution with role assignment and async coordination.
    """

    def __init__(
        self, config: OrchestrationConfig = None, registry: ProviderRegistry = None, pool: ProviderPool = None
    ):
        """
        Initialize the orchestrator.

        Args:
            config: Orchestration configuration
            registry: Provider registry
            pool: Provider pool
        """
        self.config = config or OrchestrationConfig()
        self.registry = registry or provider_registry
        self.pool = pool or provider_pool

        self.role_assigner = RoleAssigner(self.registry)
        self.consensus_manager = ConsensusManager()

        # Performance tracking
        self._orchestration_count = 0
        self._successful_orchestrations = 0
        self._failed_orchestrations = 0
        self._execution_times = []
        self._providers_used_history = []

        logger.info(f"Orchestrator initialized with strategy: {self.config.strategy.value}")

    async def orchestrate_task(
        self, task_prompt: str, collaboration_config: CollaborationConfig, task_type: str = "general"
    ) -> OrchestrationResult:
        """
        Orchestrate a multi-provider task execution.

        Args:
            task_prompt: The task to execute
            collaboration_config: Configuration for the collaboration
            task_type: Type of task for role assignment

        Returns:
            OrchestrationResult with execution results
        """
        start_time = time.time()

        try:
            # Get available providers
            available_providers = self.registry.get_all_providers(only_healthy=True)
            if len(available_providers) < collaboration_config.min_providers:
                return OrchestrationResult(
                    success=False,
                    error_message=f"Only {len(available_providers)} healthy providers available, "
                    f"need at least {collaboration_config.min_providers}",
                )

            # Assign roles to providers
            role_requirements = self.role_assigner.create_default_role_requirements(task_type)
            role_assignments = self.role_assigner.assign_roles_for_task(
                task_prompt, available_providers, role_requirements
            )

            # Convert to provider roles for coordinator
            provider_roles = []
            for role_name, providers in role_assignments.items():
                for provider in providers:
                    # Find the provider ID from the registry
                    provider_id = None
                    for pid, p in self.registry._providers.items():
                        if p == provider:
                            provider_id = pid
                            break

                    if not provider_id:
                        logger.error(f"Could not find provider ID for {provider.metadata.name}")
                        continue

                    provider_roles.append(
                        ProviderRole(
                            provider_id=provider_id,
                            role=role_name,
                            weight=provider.weight,
                            capabilities=provider.metadata.capabilities,
                        )
                    )

            # Update collaboration config with assigned providers
            updated_config = CollaborationConfig(
                providers=provider_roles,
                max_rounds=collaboration_config.max_rounds,
                convergence_threshold=collaboration_config.convergence_threshold,
                review_mode=collaboration_config.review_mode,
                consensus_strategy=collaboration_config.consensus_strategy,
                timeout_per_round=self.config.timeout_per_provider,
            )

            # Execute based on strategy
            if self.config.strategy == OrchestrationStrategy.CONCURRENT:
                result = await self._execute_concurrent(task_prompt, updated_config)
            elif self.config.strategy == OrchestrationStrategy.ROLE_BASED:
                result = await self._execute_role_based(task_prompt, updated_config, role_assignments)
            elif self.config.strategy == OrchestrationStrategy.SEQUENTIAL:
                result = await self._execute_sequential(task_prompt, updated_config)
            else:
                result = await self._execute_concurrent(task_prompt, updated_config)

            # Update performance metrics
            self._orchestration_count += 1
            self._execution_times.append(result.execution_time)
            self._providers_used_history.append(len(updated_config.providers))

            if result.success:
                self._successful_orchestrations += 1
            else:
                self._failed_orchestrations += 1

            # Log to global MAF performance tracking
            try:
                from db.analytics_performance_tools import log_maf_orchestration

                log_maf_orchestration(
                    success=result.success,
                    execution_time=result.execution_time,
                    providers_used=len(updated_config.providers),
                )
            except ImportError:
                pass  # MAF performance tracking not available

            result.execution_time = time.time() - start_time
            return result

        except Exception as e:
            logger.error(f"Orchestration failed: {e}", exc_info=True)
            execution_time = time.time() - start_time

            # Update failure metrics
            self._orchestration_count += 1
            self._failed_orchestrations += 1
            self._execution_times.append(execution_time)

            return OrchestrationResult(success=False, error_message=str(e), execution_time=execution_time)

    async def _execute_concurrent(self, task_prompt: str, config: CollaborationConfig) -> OrchestrationResult:
        """
        Execute all providers concurrently.
        """
        from .multi_provider_coordinator import MultiProviderCoordinator

        coordinator = MultiProviderCoordinator(config, self.registry, self.pool)

        try:
            final_plan = await coordinator.run_collaboration(task_prompt)

            # Extract messages from coordinator
            messages = coordinator.message_history

            # Analyze final consensus
            consensus_signal = coordinator.consensus_detector.analyze_round(
                messages, max(m.round_number for m in messages) if messages else 1
            )

            consensus_result = ConsensusResult(
                is_consensus=consensus_signal.is_consensus,
                confidence=consensus_signal.confidence,
                convergence_score=consensus_signal.convergence_score,
                agreement_indicators=consensus_signal.agreement_indicators,
                disagreement_indicators=consensus_signal.disagreement_indicators,
            )

            return OrchestrationResult(success=True, messages=messages, consensus_result=consensus_result)

        except Exception as e:
            return OrchestrationResult(success=False, error_message=str(e))

    async def _execute_role_based(
        self, task_prompt: str, config: CollaborationConfig, role_assignments: Dict[str, List[ProviderInstance]]
    ) -> OrchestrationResult:
        """
        Execute providers by role groups in order.
        """
        all_messages = []
        failed_providers = []

        # Execute roles in priority order
        for role_name in self.config.role_execution_order:
            if role_name not in role_assignments:
                continue

            providers = role_assignments[role_name]
            if not providers:
                continue

            logger.info(f"Executing role '{role_name}' with {len(providers)} providers")

            # Create config for this role
            role_provider_roles = [
                ProviderRole(
                    provider_id=p.metadata.name, role=role_name, weight=p.weight, capabilities=p.metadata.capabilities
                )
                for p in providers
            ]

            role_config = CollaborationConfig(
                providers=role_provider_roles,
                max_rounds=1,  # Single round per role
                convergence_threshold=config.convergence_threshold,
                consensus_strategy=config.consensus_strategy,
                timeout_per_round=self.config.timeout_per_provider,
            )

            # Execute this role
            role_result = await self._execute_concurrent(task_prompt, role_config)

            all_messages.extend(role_result.messages)
            failed_providers.extend(role_result.failed_providers)

            if not role_result.success:
                logger.warning(f"Role '{role_name}' execution failed: {role_result.error_message}")

        # Analyze overall consensus
        if all_messages:
            consensus_signal = self.consensus_manager.analyze_round(all_messages, 1)  # Treat as single round
            consensus_result = ConsensusResult(
                is_consensus=consensus_signal.is_consensus,
                confidence=consensus_signal.confidence,
                convergence_score=consensus_signal.convergence_score,
                agreement_indicators=consensus_signal.agreement_indicators,
                disagreement_indicators=consensus_signal.disagreement_indicators,
            )
        else:
            consensus_result = None

        return OrchestrationResult(
            success=len(all_messages) > 0,
            messages=all_messages,
            failed_providers=failed_providers,
            consensus_result=consensus_result,
        )

    async def _execute_sequential(self, task_prompt: str, config: CollaborationConfig) -> OrchestrationResult:
        """
        Execute providers one at a time sequentially.
        """
        messages = []
        failed_providers = []

        for provider_role in config.providers:
            logger.info(f"Executing provider '{provider_role.provider_id}' sequentially")

            # Create single-provider config
            single_config = CollaborationConfig(
                providers=[provider_role], max_rounds=1, timeout_per_round=self.config.timeout_per_provider
            )

            result = await self._execute_concurrent(task_prompt, single_config)
            messages.extend(result.messages)
            failed_providers.extend(result.failed_providers)

        return OrchestrationResult(success=len(messages) > 0, messages=messages, failed_providers=failed_providers)

    def get_orchestration_stats(self) -> Dict[str, Any]:
        """Get statistics about orchestration performance."""
        avg_execution_time = sum(self._execution_times) / len(self._execution_times) if self._execution_times else 0.0
        avg_providers = (
            sum(self._providers_used_history) / len(self._providers_used_history)
            if self._providers_used_history
            else 0.0
        )

        return {
            "strategy": self.config.strategy.value,
            "max_concurrent_providers": self.config.max_concurrent_providers,
            "timeout_per_provider": self.config.timeout_per_provider,
            "retry_attempts": self.config.retry_attempts,
            "circuit_breaker_enabled": self.config.enable_circuit_breaker,
            "performance_metrics": {
                "total_orchestrations": self._orchestration_count,
                "successful_orchestrations": self._successful_orchestrations,
                "failed_orchestrations": self._failed_orchestrations,
                "success_rate": self._successful_orchestrations / max(self._orchestration_count, 1),
                "average_execution_time": avg_execution_time,
                "average_providers_per_task": avg_providers,
                "total_providers_used": sum(self._providers_used_history),
            },
        }


# Global orchestrator instance
orchestrator = Orchestrator()
