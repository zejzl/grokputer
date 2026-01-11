"""
Orchestrator for Multi-Agent Framework (MAF)

Async orchestration with role assignment, timeouts, and concurrent provider execution.
Manages the flow of multi-provider collaboration with proper error handling and coordination.
"""

import asyncio
import logging
import random
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from .consensus_manager import ConsensusManager, ConsensusResult
from .message_models import AgentRole, CollaborationMessage, MessageType
from .multi_provider_coordinator import CollaborationConfig, ProviderRole
from .provider_pool import ProviderPool, provider_pool
from .provider_registry import (
    CircuitBreakerOpenException,
    ProviderCapability,
    ProviderInstance,
    ProviderRegistry,
    provider_registry,
)

logger = logging.getLogger(__name__)


class OrchestrationError(Exception):
    """Base exception for orchestration errors."""
    pass


class ProviderFailureError(OrchestrationError):
    """Exception raised when a provider fails."""
    def __init__(self, provider_id: str, original_error: Exception):
        self.provider_id = provider_id
        self.original_error = original_error
        super().__init__(f"Provider {provider_id} failed: {original_error}")


class ConsensusFailureError(OrchestrationError):
    """Exception raised when consensus cannot be reached."""
    pass


class TimeoutError(OrchestrationError):
    """Exception raised when operation times out."""
    pass


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    max_attempts: int = 3
    base_delay: float = 1.0  # Base delay in seconds
    max_delay: float = 30.0  # Maximum delay
    backoff_factor: float = 2.0  # Exponential backoff multiplier
    jitter: bool = True  # Add random jitter to delay


@dataclass
class FallbackConfig:
    """Configuration for fallback behavior."""

    enable_fallbacks: bool = True
    max_fallback_providers: int = 2
    fallback_delay: float = 0.5  # Delay before trying fallback


class RetryManager:
    """Manages retry logic with exponential backoff."""

    def __init__(self, config: RetryConfig = None):
        self.config = config or RetryConfig()

    async def execute_with_retry(self, func: callable, *args, **kwargs) -> Any:
        """
        Execute function with retry logic.

        Args:
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            Exception: Last exception if all retries fail
        """
        last_exception = None

        for attempt in range(self.config.max_attempts):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < self.config.max_attempts - 1:
                    delay = self._calculate_delay(attempt)
                    logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay:.2f}s")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"All {self.config.max_attempts} attempts failed. Last error: {e}")

        raise last_exception

    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for next retry attempt."""
        delay = self.config.base_delay * (self.config.backoff_factor ** attempt)
        delay = min(delay, self.config.max_delay)

        if self.config.jitter:
            # Add random jitter (±25%)
            jitter_range = delay * 0.25
            delay += random.uniform(-jitter_range, jitter_range)

        return max(0.1, delay)  # Minimum 100ms delay


class FallbackManager:
    """Manages fallback provider selection."""

    def __init__(self, registry: ProviderRegistry, config: FallbackConfig = None):
        self.registry = registry
        self.config = config or FallbackConfig()

    def get_fallback_providers(
        self,
        failed_provider_ids: Set[str],
        required_capabilities: List[ProviderCapability],
        max_providers: int = 3
    ) -> List[ProviderInstance]:
        """
        Get fallback providers that can replace failed ones.

        Args:
            failed_provider_ids: IDs of providers that failed
            required_capabilities: Capabilities needed
            max_providers: Maximum fallback providers to return

        Returns:
            List of fallback provider instances
        """
        if not self.config.enable_fallbacks:
            logger.debug("Fallbacks disabled, returning empty list")
            return []

        candidates = []
        for capability in required_capabilities:
            providers = self.registry.get_providers_by_capability(capability, only_healthy=True)
            for provider in providers:
                if (provider.metadata.name not in failed_provider_ids and
                    provider not in candidates):
                    candidates.append(provider)

        # Sort by reliability
        candidates.sort(key=lambda p: p.metadata.reliability_score, reverse=True)

        selected = candidates[:min(max_providers, self.config.max_fallback_providers)]
        logger.info(f"Selected {len(selected)} fallback providers from {len(candidates)} candidates")
        return selected


class MAFLogger:
    """Enhanced logging utility for MAF operations."""

    @staticmethod
    def log_orchestration_start(task_prompt: str, config: OrchestrationConfig, provider_count: int):
        """Log the start of an orchestration."""
        logger.info(
            "Starting orchestration",
            extra={
                "operation": "orchestration_start",
                "task_length": len(task_prompt),
                "strategy": config.strategy.value,
                "provider_count": provider_count,
                "max_concurrent": config.max_concurrent_providers,
                "timeout_per_provider": config.timeout_per_provider,
                "retry_attempts": config.retry_config.max_attempts,
                "fallbacks_enabled": config.fallback_config.enable_fallbacks,
            }
        )

    @staticmethod
    def log_orchestration_end(result: OrchestrationResult, execution_time: float, provider_count: int):
        """Log the end of an orchestration."""
        logger.info(
            "Orchestration completed",
            extra={
                "operation": "orchestration_end",
                "success": result.success,
                "execution_time": execution_time,
                "provider_count": provider_count,
                "messages_count": len(result.messages),
                "failed_providers_count": len(result.failed_providers),
                "error_message": result.error_message[:200] if result.error_message else None,
                "consensus_reached": result.consensus_result.is_consensus if result.consensus_result else False,
                "consensus_confidence": result.consensus_result.confidence if result.consensus_result else 0.0,
            }
        )

    @staticmethod
    def log_provider_failure(provider_id: str, error: Exception, attempt: int = None):
        """Log provider failure."""
        logger.warning(
            f"Provider {provider_id} failed",
            extra={
                "operation": "provider_failure",
                "provider_id": provider_id,
                "error_type": type(error).__name__,
                "error_message": str(error)[:200],
                "attempt": attempt,
            },
            exc_info=True
        )

    @staticmethod
    def log_retry_attempt(attempt: int, max_attempts: int, delay: float, error: Exception):
        """Log retry attempt."""
        logger.info(
            f"Retry attempt {attempt}/{max_attempts} after {delay:.2f}s delay",
            extra={
                "operation": "retry_attempt",
                "attempt": attempt,
                "max_attempts": max_attempts,
                "delay": delay,
                "last_error": str(error)[:200],
            }
        )

    @staticmethod
    def log_fallback_activation(original_count: int, fallback_count: int, failed_providers: List[str]):
        """Log fallback provider activation."""
        logger.info(
            f"Activating {fallback_count} fallback providers to replace {len(failed_providers)} failed providers",
            extra={
                "operation": "fallback_activation",
                "original_provider_count": original_count,
                "fallback_provider_count": fallback_count,
                "failed_providers": failed_providers,
            }
        )

    @staticmethod
    def log_performance_metrics(stats: Dict[str, Any]):
        """Log performance metrics."""
        logger.info(
            "MAF performance metrics",
            extra={
                "operation": "performance_metrics",
                **stats,
            }
        )


class PerformanceMonitor:
    """Performance monitoring and metrics collection for MAF operations."""

    def __init__(self):
        self.metrics = {
            "orchestration": {
                "total_count": 0,
                "success_count": 0,
                "failure_count": 0,
                "average_execution_time": 0.0,
                "p95_execution_time": 0.0,
                "execution_times": [],
            },
            "providers": {
                "total_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0,
                "circuit_breaker_trips": 0,
                "fallback_activations": 0,
            },
            "consensus": {
                "rounds_analyzed": 0,
                "consensus_reached": 0,
                "average_confidence": 0.0,
                "average_convergence": 0.0,
            },
            "errors": {
                "by_type": {},
                "total_count": 0,
            }
        }
        self._lock = threading.Lock()

    def record_orchestration(self, success: bool, execution_time: float, provider_count: int):
        """Record orchestration performance metrics."""
        with self._lock:
            self.metrics["orchestration"]["total_count"] += 1
            if success:
                self.metrics["orchestration"]["success_count"] += 1
            else:
                self.metrics["orchestration"]["failure_count"] += 1

            self.metrics["orchestration"]["execution_times"].append(execution_time)

            # Keep only last 1000 execution times for memory efficiency
            if len(self.metrics["orchestration"]["execution_times"]) > 1000:
                self.metrics["orchestration"]["execution_times"] = self.metrics["orchestration"]["execution_times"][-1000:]

            # Update averages
            times = self.metrics["orchestration"]["execution_times"]
            if times:
                self.metrics["orchestration"]["average_execution_time"] = sum(times) / len(times)
                self.metrics["orchestration"]["p95_execution_time"] = sorted(times)[int(len(times) * 0.95)] if len(times) > 1 else max(times)

    def record_provider_request(self, success: bool):
        """Record provider request metrics."""
        with self._lock:
            self.metrics["providers"]["total_requests"] += 1
            if success:
                self.metrics["providers"]["successful_requests"] += 1
            else:
                self.metrics["providers"]["failed_requests"] += 1

    def record_circuit_breaker_trip(self):
        """Record circuit breaker trip."""
        with self._lock:
            self.metrics["providers"]["circuit_breaker_trips"] += 1

    def record_fallback_activation(self):
        """Record fallback activation."""
        with self._lock:
            self.metrics["providers"]["fallback_activations"] += 1

    def record_consensus_analysis(self, is_consensus: bool, confidence: float, convergence: float):
        """Record consensus analysis metrics."""
        with self._lock:
            self.metrics["consensus"]["rounds_analyzed"] += 1
            if is_consensus:
                self.metrics["consensus"]["consensus_reached"] += 1

            # Update running averages
            current_avg_conf = self.metrics["consensus"]["average_confidence"]
            current_avg_conv = self.metrics["consensus"]["average_convergence"]
            count = self.metrics["consensus"]["rounds_analyzed"]

            self.metrics["consensus"]["average_confidence"] = (current_avg_conf * (count - 1) + confidence) / count
            self.metrics["consensus"]["average_convergence"] = (current_avg_conv * (count - 1) + convergence) / count

    def record_error(self, error_type: str):
        """Record error by type."""
        with self._lock:
            self.metrics["errors"]["total_count"] += 1
            if error_type not in self.metrics["errors"]["by_type"]:
                self.metrics["errors"]["by_type"][error_type] = 0
            self.metrics["errors"]["by_type"][error_type] += 1

    def get_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        with self._lock:
            return self.metrics.copy()

    def reset_metrics(self):
        """Reset all metrics."""
        with self._lock:
            self.metrics = {
                "orchestration": {
                    "total_count": 0,
                    "success_count": 0,
                    "failure_count": 0,
                    "average_execution_time": 0.0,
                    "p95_execution_time": 0.0,
                    "execution_times": [],
                },
                "providers": {
                    "total_requests": 0,
                    "successful_requests": 0,
                    "failed_requests": 0,
                    "circuit_breaker_trips": 0,
                    "fallback_activations": 0,
                },
                "consensus": {
                    "rounds_analyzed": 0,
                    "consensus_reached": 0,
                    "average_confidence": 0.0,
                    "average_convergence": 0.0,
                },
                "errors": {
                    "by_type": {},
                    "total_count": 0,
                }
            }


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
    retry_config: RetryConfig = field(default_factory=RetryConfig)
    fallback_config: FallbackConfig = field(default_factory=FallbackConfig)


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
        self.retry_manager = RetryManager(self.config.retry_config)
        self.fallback_manager = FallbackManager(self.registry, self.config.fallback_config)
        self.performance_monitor = PerformanceMonitor()

        # Phase 4: RL-based self-improvement
        try:
            from .rl_optimizer import get_maf_optimizer
            self.rl_optimizer = get_maf_optimizer(self.performance_monitor)
            self.enable_rl_optimization = True
            logger.info("RL optimizer enabled for self-improvement")
        except ImportError:
            self.rl_optimizer = None
            self.enable_rl_optimization = False
            logger.warning("RL optimizer not available, running without self-improvement")

        # Performance tracking (legacy - kept for backward compatibility)
        self._orchestration_count = 0
        self._successful_orchestrations = 0
        self._failed_orchestrations = 0
        self._execution_times = []
        self._providers_used_history = []
        self._error_counts: Dict[str, int] = {}

        logger.info(f"Orchestrator initialized with strategy: {self.config.strategy.value}, retries: {self.config.retry_config.max_attempts}, fallbacks: {self.config.fallback_config.enable_fallbacks}")

    async def orchestrate_task(
        self, task_prompt: str, collaboration_config: CollaborationConfig, task_type: str = "general"
    ) -> OrchestrationResult:
        """
        Orchestrate a multi-provider task execution with comprehensive error handling.

        Args:
            task_prompt: The task to execute
            collaboration_config: Configuration for the collaboration
            task_type: Type of task for role assignment

        Returns:
            OrchestrationResult with execution results
        """
        start_time = time.time()

        try:
            # Log orchestration start
            MAFLogger.log_orchestration_start(task_prompt, self.config, collaboration_config.min_providers)

            # Get available providers with error handling
            available_providers = await self._get_available_providers_with_retry(collaboration_config.min_providers)
            if not available_providers:
                error_msg = f"Unable to get minimum required providers ({collaboration_config.min_providers}) after retries"
                logger.error(error_msg)
                return OrchestrationResult(
                    success=False,
                    error_message=error_msg,
                )

            # Phase 4: Dynamic provider selection using RL
            if self.enable_rl_optimization and self.rl_optimizer:
                available_providers = await self._rl_based_provider_selection(
                    task_prompt, available_providers, task_type
                )

            # Assign roles to providers with fallback support
            role_assignments = await self._assign_roles_with_fallback(
                task_prompt, available_providers, task_type, collaboration_config.min_providers
            )
            if not role_assignments:
                error_msg = "Failed to assign roles to providers"
                logger.error(error_msg)
                return OrchestrationResult(
                    success=False,
                    error_message=error_msg,
                )

            # Convert to provider roles for coordinator
            provider_roles = self._convert_to_provider_roles(role_assignments)

            # Update collaboration config with assigned providers
            updated_config = CollaborationConfig(
                providers=provider_roles,
                max_rounds=collaboration_config.max_rounds,
                convergence_threshold=collaboration_config.convergence_threshold,
                review_mode=collaboration_config.review_mode,
                consensus_strategy=collaboration_config.consensus_strategy,
                timeout_per_round=self.config.timeout_per_provider,
            )

            # Execute with retry logic
            result = await self.retry_manager.execute_with_retry(
                self._execute_with_strategy,
                task_prompt,
                updated_config,
                role_assignments
            )

            # Update performance metrics
            self._update_performance_metrics(result, len(updated_config.providers))
            execution_time = time.time() - start_time
            self.performance_monitor.record_orchestration(result.success, execution_time, len(updated_config.providers))

            # Phase 4: RL learning and optimization
            if self.enable_rl_optimization and self.rl_optimizer:
                await self._rl_learning_and_optimization(
                    task_prompt, result, execution_time, len(updated_config.providers), task_type
                )

            # Log orchestration end
            MAFLogger.log_orchestration_end(result, execution_time, len(updated_config.providers))

            # Log to global MAF performance tracking
            await self._log_performance_metrics(result, len(updated_config.providers))

            result.execution_time = execution_time
            return result

        except Exception as e:
            logger.error(f"Orchestration failed: {e}", exc_info=True)
            execution_time = time.time() - start_time

            # Track error types
            error_type = type(e).__name__
            self._error_counts[error_type] = self._error_counts.get(error_type, 0) + 1
            self.performance_monitor.record_error(error_type)

            # Update failure metrics
            self._update_performance_metrics(
                OrchestrationResult(success=False, error_message=str(e), execution_time=execution_time),
                0
            )

            return OrchestrationResult(success=False, error_message=str(e), execution_time=execution_time)

    async def _get_available_providers_with_retry(self, min_providers: int) -> List[ProviderInstance]:
        """Get available providers with retry logic."""
        try:
            return await self.retry_manager.execute_with_retry(
                self._get_available_providers_once,
                min_providers
            )
        except Exception as e:
            logger.error(f"Failed to get available providers after retries: {e}")
            return []

    async def _get_available_providers_once(self, min_providers: int) -> List[ProviderInstance]:
        """Get available providers once (used by retry manager)."""
        available_providers = self.registry.get_all_providers(only_healthy=True)
        if len(available_providers) < min_providers:
            raise OrchestrationError(
                f"Only {len(available_providers)} healthy providers available, "
                f"need at least {min_providers}"
            )
        return available_providers

    async def _assign_roles_with_fallback(
        self,
        task_prompt: str,
        available_providers: List[ProviderInstance],
        task_type: str,
        min_providers: int
    ) -> Dict[str, List[ProviderInstance]]:
        """Assign roles with fallback support."""
        try:
            role_requirements = self.role_assigner.create_default_role_requirements(task_type)
            role_assignments = self.role_assigner.assign_roles_for_task(
                task_prompt, available_providers, role_requirements
            )

            # Check if we have minimum providers across all roles
            total_assigned = sum(len(providers) for providers in role_assignments.values())
            if total_assigned < min_providers:
                logger.warning(f"Only {total_assigned} providers assigned, need {min_providers}. Attempting fallback.")

                # Try to get fallback providers
                failed_provider_ids = set()
                for providers in role_assignments.values():
                    for provider in providers:
                        failed_provider_ids.add(provider.metadata.name)

                fallback_providers = self.fallback_manager.get_fallback_providers(
                    failed_provider_ids,
                    [cap for req in role_requirements.values() for cap in req.required_capabilities]
                )

                if fallback_providers:
                    logger.info(f"Adding {len(fallback_providers)} fallback providers")
                    available_providers.extend(fallback_providers)

                    # Retry assignment with fallbacks
                    role_assignments = self.role_assigner.assign_roles_for_task(
                        task_prompt, available_providers, role_requirements
                    )

            return role_assignments

        except Exception as e:
            logger.error(f"Role assignment failed: {e}")
            return {}

    def _convert_to_provider_roles(self, role_assignments: Dict[str, List[ProviderInstance]]) -> List[ProviderRole]:
        """Convert role assignments to provider roles for coordinator."""
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
        return provider_roles

    async def _execute_with_strategy(
        self,
        task_prompt: str,
        config: CollaborationConfig,
        role_assignments: Dict[str, List[ProviderInstance]]
    ) -> OrchestrationResult:
        """Execute orchestration based on configured strategy."""
        try:
            if self.config.strategy == OrchestrationStrategy.CONCURRENT:
                result = await self._execute_concurrent(task_prompt, config)
            elif self.config.strategy == OrchestrationStrategy.ROLE_BASED:
                result = await self._execute_role_based(task_prompt, config, role_assignments)
            elif self.config.strategy == OrchestrationStrategy.SEQUENTIAL:
                result = await self._execute_sequential(task_prompt, config)
            else:
                result = await self._execute_concurrent(task_prompt, config)

            return result

        except Exception as e:
            logger.error(f"Strategy execution failed: {e}")
            raise OrchestrationError(f"Execution failed: {e}") from e

    def _update_performance_metrics(self, result: OrchestrationResult, providers_used: int):
        """Update internal performance metrics."""
        self._orchestration_count += 1
        self._execution_times.append(result.execution_time)
        self._providers_used_history.append(providers_used)

        if result.success:
            self._successful_orchestrations += 1
        else:
            self._failed_orchestrations += 1

    async def _rl_learning_and_optimization(
        self, task_prompt: str, result: OrchestrationResult,
        execution_time: float, provider_count: int, task_type: str
    ):
        """Perform RL learning and apply optimizations."""
        try:
            from .rl_optimizer import RLState, RLAction, Experience

            # Create current state
            current_time = time.time()
            metrics = self.performance_monitor.get_metrics()

            # Calculate task complexity (simple heuristic)
            task_complexity = min(len(task_prompt.split()) / 100.0, 1.0)

            # Get provider health
            provider_health = 0.9  # Default healthy
            providers = self.registry.get_all_providers(only_healthy=True)
            if providers:
                healthy_count = len([p for p in providers if p.metadata.health_status == "healthy"])
                provider_health = healthy_count / len(providers)

            # Previous success rate
            orchestration = metrics.get("orchestration", {})
            prev_success_rate = orchestration.get("success_count", 0) / max(orchestration.get("total_count", 1), 1)

            current_state = RLState(
                task_complexity=task_complexity,
                provider_count=provider_count,
                provider_health=provider_health,
                previous_success_rate=prev_success_rate,
                time_of_day=time.localtime(current_time).tm_hour,
                strategy_used=self.config.strategy,
            )

            # Calculate reward based on performance
            reward = self._calculate_rl_reward(result, execution_time, provider_count)

            # Create action taken
            action_taken = RLAction(
                strategy=self.config.strategy,
                max_concurrent_providers=self.config.max_concurrent_providers,
                timeout_per_provider=self.config.timeout_per_provider,
                retry_attempts=self.config.retry_attempts,
            )

            # For learning, we need previous state and action
            # This is a simplified implementation - in practice, we'd track state across orchestrations
            if hasattr(self, '_previous_rl_state') and hasattr(self, '_previous_rl_action'):
                experience = Experience(
                    state=self._previous_rl_state,
                    action=self._previous_rl_action,
                    reward=reward,
                    next_state=current_state,
                    done=False
                )
                self.rl_optimizer.q_agent.learn(experience)

            # Store current state and action for next learning step
            self._previous_rl_state = current_state
            self._previous_rl_action = action_taken

            # Apply optimizations periodically
            optimization_result = self.rl_optimizer.analyze_performance_and_optimize()
            if optimization_result.get("optimizations_applied", 0) > 0:
                logger.info(f"Applied {optimization_result['optimizations_applied']} RL-based optimizations")

        except Exception as e:
            logger.warning(f"RL learning failed: {e}")

    async def _rl_based_provider_selection(
        self, task_prompt: str, available_providers: List[ProviderInstance], task_type: str
    ) -> List[ProviderInstance]:
        """Select optimal providers using RL-based performance patterns."""
        try:
            # Get performance metrics for provider selection
            metrics = self.performance_monitor.get_metrics()
            orchestration = metrics.get("orchestration", {})

            # Calculate task complexity
            task_complexity = min(len(task_prompt.split()) / 100.0, 1.0)

            # Get provider performance history
            provider_performance = {}
            for provider in available_providers:
                # Simple performance scoring based on health and capabilities
                health_score = 1.0 if provider.metadata.health_status == "healthy" else 0.5
                capability_score = len(provider.metadata.capabilities) / 8.0  # Normalize by max capabilities
                reliability_score = provider.metadata.reliability_score

                # Combine scores with learned weights (simplified)
                performance_score = (health_score * 0.4 + capability_score * 0.3 + reliability_score * 0.3)

                provider_performance[provider] = performance_score

            # Sort providers by performance score
            sorted_providers = sorted(
                available_providers,
                key=lambda p: provider_performance.get(p, 0.5),
                reverse=True
            )

            # RL-based selection: prefer top performers but maintain diversity
            selected_providers = []

            # Always include the top performer
            if sorted_providers:
                selected_providers.append(sorted_providers[0])

            # Add more providers based on task complexity
            additional_needed = max(2, int(task_complexity * 4))  # 2-4 providers based on complexity

            for provider in sorted_providers[1:]:
                if len(selected_providers) >= additional_needed:
                    break
                # Add with some probability to maintain exploration
                if random.random() < 0.7:  # 70% chance to include good performers
                    selected_providers.append(provider)

            # Ensure minimum providers
            while len(selected_providers) < 2 and sorted_providers:
                for provider in sorted_providers:
                    if provider not in selected_providers:
                        selected_providers.append(provider)
                        break

            logger.info(f"RL-based provider selection: {len(selected_providers)} providers selected from {len(available_providers)} available")
            return selected_providers[:len(available_providers)]  # Don't exceed original count

        except Exception as e:
            logger.warning(f"RL-based provider selection failed, using default: {e}")
            return available_providers

    def _calculate_rl_reward(self, result: OrchestrationResult, execution_time: float, provider_count: int) -> float:
        """Calculate reward for RL learning."""
        reward = 0.0

        # Success bonus
        if result.success:
            reward += 10.0
        else:
            reward -= 5.0

        # Execution time penalty (faster is better)
        if execution_time < 5.0:
            reward += 2.0
        elif execution_time > 15.0:
            reward -= 3.0

        # Provider efficiency bonus (fewer providers for success is better)
        if result.success and provider_count <= 3:
            reward += 1.0

        # Consensus quality bonus
        if result.consensus_result and result.consensus_result.confidence > 0.8:
            reward += 2.0

        return reward

    async def _log_performance_metrics(self, result: OrchestrationResult, providers_used: int):
        """Log performance metrics to external systems."""
        try:
            from db.analytics_performance_tools import log_maf_orchestration

            # Check if the function is async
            import inspect
            if inspect.iscoroutinefunction(log_maf_orchestration):
                await log_maf_orchestration(
                    success=result.success,
                    execution_time=result.execution_time,
                    providers_used=providers_used,
                )
            else:
                # Call synchronously
                log_maf_orchestration(
                    success=result.success,
                    execution_time=result.execution_time,
                    providers_used=providers_used,
                )
        except ImportError:
            pass  # MAF performance tracking not available

    async def _execute_concurrent(self, task_prompt: str, config: CollaborationConfig) -> OrchestrationResult:
        """
        Execute all providers concurrently with error handling.
        """
        from .multi_provider_coordinator import MultiProviderCoordinator

        try:
            # Check circuit breakers before execution
            failed_providers = []
            for provider_role in config.providers:
                instance = self.registry.get_provider(provider_role.provider_id)
                if instance and instance.circuit_breaker:
                    try:
                        # Test circuit breaker state
                        instance.circuit_breaker.call(lambda: None)
                    except CircuitBreakerOpenException:
                        failed_providers.append(provider_role.provider_id)
                        logger.warning(f"Provider {provider_role.provider_id} circuit breaker is OPEN, skipping")

            if failed_providers:
                # Try fallback providers
                fallback_providers = self.fallback_manager.get_fallback_providers(
                    set(failed_providers),
                    [cap for role in config.providers for cap in role.capabilities],
                    len(failed_providers)
                )

                if fallback_providers:
                    logger.info(f"Replacing {len(failed_providers)} failed providers with {len(fallback_providers)} fallbacks")
                    # Remove failed providers and add fallbacks
                    config.providers = [
                        role for role in config.providers
                        if role.provider_id not in failed_providers
                    ]

                    for fallback in fallback_providers:
                        # Find provider ID for fallback
                        for pid, p in self.registry._providers.items():
                            if p == fallback:
                                config.providers.append(ProviderRole(
                                    provider_id=pid,
                                    role="fallback",
                                    weight=fallback.weight,
                                    capabilities=fallback.metadata.capabilities,
                                ))
                                break

            coordinator = MultiProviderCoordinator(config, self.registry, self.pool)

            # Execute with timeout
            try:
                final_plan = await asyncio.wait_for(
                    coordinator.run_collaboration(task_prompt),
                    timeout=self.config.timeout_per_provider * len(config.providers)
                )
            except asyncio.TimeoutError:
                raise TimeoutError(f"Concurrent execution timed out after {self.config.timeout_per_provider * len(config.providers)}s")

            # Extract messages from coordinator
            messages = coordinator.message_history

            # Analyze final consensus
            if messages:
                consensus_signal = coordinator.consensus_detector.analyze_round(
                    messages, max(m.round_number for m in messages)
                )

                consensus_result = ConsensusResult(
                    is_consensus=consensus_signal.is_consensus,
                    confidence=consensus_signal.confidence,
                    convergence_score=consensus_signal.convergence_score,
                    agreement_indicators=consensus_signal.agreement_indicators,
                    disagreement_indicators=consensus_signal.disagreement_indicators,
                )
            else:
                consensus_result = ConsensusResult(
                    is_consensus=False,
                    confidence=0.0,
                    convergence_score=0.0,
                    disagreement_indicators=["No messages generated"],
                )

            return OrchestrationResult(
                success=consensus_result.is_consensus,
                messages=messages,
                consensus_result=consensus_result,
                failed_providers=failed_providers
            )

        except (CircuitBreakerOpenException, TimeoutError, ConsensusFailureError) as e:
            logger.error(f"Concurrent execution failed with known error: {e}")
            return OrchestrationResult(success=False, error_message=str(e))
        except Exception as e:
            logger.error(f"Concurrent execution failed with unexpected error: {e}", exc_info=True)
            return OrchestrationResult(success=False, error_message=f"Unexpected error: {str(e)}")

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
            "retry_config": {
                "max_attempts": self.config.retry_config.max_attempts,
                "base_delay": self.config.retry_config.base_delay,
                "max_delay": self.config.retry_config.max_delay,
                "backoff_factor": self.config.retry_config.backoff_factor,
                "jitter": self.config.retry_config.jitter,
            },
            "fallback_config": {
                "enable_fallbacks": self.config.fallback_config.enable_fallbacks,
                "max_fallback_providers": self.config.fallback_config.max_fallback_providers,
                "fallback_delay": self.config.fallback_config.fallback_delay,
            },
            "performance_metrics": {
                "total_orchestrations": self._orchestration_count,
                "successful_orchestrations": self._successful_orchestrations,
                "failed_orchestrations": self._failed_orchestrations,
                "success_rate": self._successful_orchestrations / max(self._orchestration_count, 1),
                "average_execution_time": avg_execution_time,
                "average_providers_per_task": avg_providers,
                "total_providers_used": sum(self._providers_used_history),
            },
            "error_tracking": {
                "error_counts": self._error_counts,
                "total_errors": sum(self._error_counts.values()),
            },
            "performance_monitor": self.performance_monitor.get_metrics(),
        }


# Global orchestrator instance
orchestrator = Orchestrator()
