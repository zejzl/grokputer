"""
Executor Agent - Specialized action execution with advanced retry and circuit breaker patterns.

A specialized variant of Actor with:
- Advanced retry strategies (exponential backoff, jitter)
- Circuit breaker pattern for failing operations
- Execution prioritization and scheduling
- Batch execution optimization
- Fallback strategies
- Execution telemetry
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, asdict
import time
from collections import defaultdict, deque

from src.agents.actor import Actor
from src.core.message_bus import MessageBus, Message, MessagePriority
from src.core.action_executor import ActionExecutor

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitBreaker:
    """Circuit breaker for failing operations."""
    operation_name: str
    state: CircuitState
    failure_count: int
    success_count: int
    last_failure_time: float
    threshold: int  # Failures to trip circuit
    timeout: float  # Seconds before trying again
    half_open_max_attempts: int = 3


@dataclass
class ExecutionPlan:
    """Optimized execution plan."""
    plan_id: str
    actions: List[Dict]
    strategy: str  # sequential, parallel, batch
    priority: str  # critical, high, normal, low
    deadline: Optional[float]
    dependencies: Dict[str, List[str]]  # action_id -> [dependent_action_ids]


@dataclass
class ExecutionResult:
    """Result of action execution."""
    action_id: str
    success: bool
    result: Any
    execution_time: float
    retry_count: int
    circuit_state: str
    error: Optional[str] = None


class ExecutorAgent(Actor):
    """
    Executor Agent (Phase 2): Advanced action execution with retry and circuit breaker patterns.

    Extends Actor with:
    - Circuit breakers for failing operations
    - Advanced retry strategies
    - Batch execution optimization
    - Execution scheduling
    - Fallback mechanisms
    - Comprehensive telemetry
    """

    def __init__(
        self,
        message_bus: MessageBus,
        session_logger: 'SessionLogger',
        config_dict: Dict[str, Any],
        action_executor: ActionExecutor,
        heartbeat_interval: float = 10.0
    ):
        super().__init__(
            message_bus,
            session_logger,
            config_dict,
            action_executor,
            heartbeat_interval
        )

        # Override agent_id
        self.agent_id = "executor"

        # Circuit breakers per operation type
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}

        # Execution queue with priority
        self.execution_queue: Dict[str, List[Dict]] = {
            "critical": [],
            "high": [],
            "normal": [],
            "low": []
        }

        # Execution history for telemetry
        self.execution_history: deque = deque(maxlen=1000)

        # Configuration
        self.circuit_failure_threshold = config_dict.get("circuit_failure_threshold", 5)
        self.circuit_timeout = config_dict.get("circuit_timeout", 60.0)  # 1 minute
        self.max_retry_attempts = config_dict.get("max_retry_attempts", 5)
        self.retry_base_delay = config_dict.get("retry_base_delay", 1.0)
        self.enable_circuit_breakers = config_dict.get("enable_circuit_breakers", True)
        self.batch_size = config_dict.get("batch_size", 10)

        # Statistics
        self.stats = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "retries_performed": 0,
            "circuit_breaks_triggered": 0,
            "batch_executions": 0
        }

        self.session_logger.log_agent_init(
            self.agent_id,
            f"Executor ready (circuit_breakers={self.enable_circuit_breakers})"
        )

    async def process_message(self, message: Message) -> Optional[Dict]:
        """
        Process execution messages.

        Additional message types beyond Actor:
        - execute_with_retry: Execute with retry strategy
        - execute_batch: Execute batch of actions
        - execute_plan: Execute optimized plan
        - get_circuit_status: Get circuit breaker status
        - reset_circuit: Reset circuit breaker
        """
        msg_type = message.message_type

        if msg_type == "execute_with_retry":
            return await self._execute_with_retry(message.content)

        elif msg_type == "execute_batch":
            return await self._execute_batch(message.content)

        elif msg_type == "execute_plan":
            return await self._execute_plan(message.content)

        elif msg_type == "get_circuit_status":
            return self._get_circuit_status(message.content)

        elif msg_type == "reset_circuit":
            return self._reset_circuit(message.content)

        elif msg_type == "get_stats":
            return self._get_executor_stats()

        else:
            # Delegate to parent Actor
            return await super().process_message(message)

    async def _execute_with_retry(self, content: Dict) -> Dict:
        """
        Execute action with advanced retry strategy.

        Includes:
        - Exponential backoff with jitter
        - Circuit breaker integration
        - Fallback strategies
        """
        action = content.get("action")
        operation_name = content.get("operation_name", action.get("type", "unknown"))
        max_retries = content.get("max_retries", self.max_retry_attempts)
        fallback = content.get("fallback")  # Optional fallback action

        # Check circuit breaker
        if self.enable_circuit_breakers:
            circuit_check = await self._check_circuit(operation_name)
            if not circuit_check["allowed"]:
                return {
                    "status": "rejected",
                    "reason": f"Circuit breaker is {circuit_check['state']}",
                    "circuit_state": circuit_check["state"]
                }

        # Execute with retry
        retry_count = 0
        last_error = None
        start_time = time.time()

        while retry_count <= max_retries:
            try:
                # Execute action
                result = await self._execute_action(action)

                # Success
                execution_time = time.time() - start_time

                await self._record_success(operation_name)

                exec_result = ExecutionResult(
                    action_id=action.get("id", "unknown"),
                    success=True,
                    result=result,
                    execution_time=execution_time,
                    retry_count=retry_count,
                    circuit_state=self._get_circuit_state(operation_name)
                )

                self.execution_history.append(exec_result)
                self.stats["total_executions"] += 1
                self.stats["successful_executions"] += 1
                if retry_count > 0:
                    self.stats["retries_performed"] += retry_count

                return {
                    "status": "success",
                    "result": asdict(exec_result)
                }

            except Exception as e:
                last_error = str(e)
                retry_count += 1

                await self._record_failure(operation_name)

                if retry_count <= max_retries:
                    # Calculate backoff with jitter
                    delay = self._calculate_backoff(retry_count)
                    self.session_logger.log_agent_activity(
                        self.agent_id,
                        f"Retry {retry_count}/{max_retries} after {delay:.2f}s: {operation_name}"
                    )
                    await asyncio.sleep(delay)

        # All retries exhausted - try fallback
        if fallback:
            self.session_logger.log_agent_activity(
                self.agent_id,
                f"Attempting fallback for {operation_name}"
            )
            try:
                fallback_result = await self._execute_action(fallback)
                exec_result = ExecutionResult(
                    action_id=action.get("id", "unknown"),
                    success=True,
                    result=fallback_result,
                    execution_time=time.time() - start_time,
                    retry_count=retry_count,
                    circuit_state="fallback",
                    error=f"Primary failed: {last_error}"
                )
                return {"status": "success_fallback", "result": asdict(exec_result)}
            except Exception as e:
                last_error = f"Fallback also failed: {str(e)}"

        # Complete failure
        execution_time = time.time() - start_time
        exec_result = ExecutionResult(
            action_id=action.get("id", "unknown"),
            success=False,
            result=None,
            execution_time=execution_time,
            retry_count=retry_count,
            circuit_state=self._get_circuit_state(operation_name),
            error=last_error
        )

        self.execution_history.append(exec_result)
        self.stats["total_executions"] += 1
        self.stats["failed_executions"] += 1
        self.stats["retries_performed"] += retry_count

        return {
            "status": "failed",
            "result": asdict(exec_result)
        }

    async def _execute_action(self, action: Dict) -> Any:
        """Execute a single action."""
        # Delegate to parent Actor's execution methods
        action_type = action.get("type")
        params = action.get("params", {})

        # Create message for Actor execution
        message = Message(
            message_type="subtask",
            from_agent=self.agent_id,
            to_agent="actor",
            priority=MessagePriority.NORMAL,
            content={
                "action": action_type,
                "params": params,
                "task_id": action.get("id", "unknown")
            }
        )

        result = await self._handle_subtask(message)
        return result

    def _calculate_backoff(self, retry_count: int) -> float:
        """Calculate exponential backoff with jitter."""
        import random

        # Exponential backoff: base_delay * (2 ^ retry_count)
        backoff = self.retry_base_delay * (2 ** (retry_count - 1))

        # Add jitter (±25%)
        jitter = random.uniform(0.75, 1.25)
        delay = backoff * jitter

        # Cap at 60 seconds
        return min(delay, 60.0)

    async def _check_circuit(self, operation_name: str) -> Dict:
        """Check circuit breaker state."""
        if operation_name not in self.circuit_breakers:
            # Create new circuit breaker
            self.circuit_breakers[operation_name] = CircuitBreaker(
                operation_name=operation_name,
                state=CircuitState.CLOSED,
                failure_count=0,
                success_count=0,
                last_failure_time=0.0,
                threshold=self.circuit_failure_threshold,
                timeout=self.circuit_timeout
            )

        circuit = self.circuit_breakers[operation_name]
        current_time = time.time()

        if circuit.state == CircuitState.OPEN:
            # Check if timeout elapsed
            if current_time - circuit.last_failure_time > circuit.timeout:
                circuit.state = CircuitState.HALF_OPEN
                circuit.success_count = 0
                return {"allowed": True, "state": "half_open"}
            else:
                return {"allowed": False, "state": "open"}

        elif circuit.state == CircuitState.HALF_OPEN:
            # Allow limited attempts
            if circuit.success_count < circuit.half_open_max_attempts:
                return {"allowed": True, "state": "half_open"}
            else:
                # Recovered - close circuit
                circuit.state = CircuitState.CLOSED
                circuit.failure_count = 0
                return {"allowed": True, "state": "closed"}

        else:  # CLOSED
            return {"allowed": True, "state": "closed"}

    async def _record_success(self, operation_name: str):
        """Record successful execution."""
        if operation_name in self.circuit_breakers:
            circuit = self.circuit_breakers[operation_name]

            if circuit.state == CircuitState.HALF_OPEN:
                circuit.success_count += 1
                if circuit.success_count >= circuit.half_open_max_attempts:
                    circuit.state = CircuitState.CLOSED
                    circuit.failure_count = 0
                    self.session_logger.log_agent_activity(
                        self.agent_id,
                        f"Circuit recovered: {operation_name}"
                    )
            elif circuit.state == CircuitState.CLOSED:
                # Reset failure count on success
                circuit.failure_count = 0

    async def _record_failure(self, operation_name: str):
        """Record failed execution."""
        if operation_name not in self.circuit_breakers:
            await self._check_circuit(operation_name)

        circuit = self.circuit_breakers[operation_name]
        circuit.failure_count += 1
        circuit.last_failure_time = time.time()

        if circuit.state == CircuitState.CLOSED:
            if circuit.failure_count >= circuit.threshold:
                circuit.state = CircuitState.OPEN
                self.stats["circuit_breaks_triggered"] += 1
                self.session_logger.log_agent_activity(
                    self.agent_id,
                    f"Circuit opened: {operation_name} ({circuit.failure_count} failures)"
                )

        elif circuit.state == CircuitState.HALF_OPEN:
            # Failure during recovery - reopen
            circuit.state = CircuitState.OPEN
            circuit.success_count = 0

    def _get_circuit_state(self, operation_name: str) -> str:
        """Get current circuit state."""
        if operation_name in self.circuit_breakers:
            return self.circuit_breakers[operation_name].state.value
        return "unknown"

    async def _execute_batch(self, content: Dict) -> Dict:
        """Execute batch of actions."""
        actions = content.get("actions", [])
        parallel = content.get("parallel", False)

        if not actions:
            return {"status": "error", "reason": "No actions provided"}

        results = []
        start_time = time.time()

        if parallel:
            # Execute in parallel
            tasks = [
                self._execute_with_retry({"action": action})
                for action in actions
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
        else:
            # Execute sequentially
            for action in actions:
                result = await self._execute_with_retry({"action": action})
                results.append(result)

        execution_time = time.time() - start_time
        self.stats["batch_executions"] += 1

        return {
            "status": "completed",
            "results": results,
            "total_actions": len(actions),
            "successful": sum(1 for r in results if isinstance(r, dict) and r.get("status") == "success"),
            "execution_time": execution_time
        }

    async def _execute_plan(self, content: Dict) -> Dict:
        """Execute optimized execution plan with dependencies."""
        plan = content.get("plan")

        if not isinstance(plan, dict):
            return {"status": "error", "reason": "Invalid plan format"}

        # Parse plan
        actions = plan.get("actions", [])
        strategy = plan.get("strategy", "sequential")
        dependencies = plan.get("dependencies", {})

        # Execute based on strategy
        if strategy == "parallel":
            return await self._execute_batch({"actions": actions, "parallel": True})

        elif strategy == "sequential":
            return await self._execute_batch({"actions": actions, "parallel": False})

        elif strategy == "dependency_aware":
            # Topological sort and execute
            return await self._execute_with_dependencies(actions, dependencies)

        else:
            return {"status": "error", "reason": f"Unknown strategy: {strategy}"}

    async def _execute_with_dependencies(self, actions: List[Dict], dependencies: Dict) -> Dict:
        """Execute actions respecting dependencies."""
        # Build dependency graph
        action_map = {a.get("id"): a for a in actions}
        completed = set()
        results = {}

        while len(completed) < len(actions):
            # Find actions with satisfied dependencies
            ready = [
                action for action in actions
                if action.get("id") not in completed and
                all(dep in completed for dep in dependencies.get(action.get("id"), []))
            ]

            if not ready:
                return {
                    "status": "error",
                    "reason": "Circular dependency or no ready actions",
                    "completed": len(completed),
                    "total": len(actions)
                }

            # Execute ready actions in parallel
            tasks = [
                self._execute_with_retry({"action": action})
                for action in ready
            ]

            batch_results = await asyncio.gather(*tasks)

            for action, result in zip(ready, batch_results):
                action_id = action.get("id")
                completed.add(action_id)
                results[action_id] = result

        return {
            "status": "completed",
            "results": results,
            "total_actions": len(actions),
            "successful": sum(1 for r in results.values() if r.get("status") == "success")
        }

    def _get_circuit_status(self, content: Dict) -> Dict:
        """Get status of all circuit breakers."""
        operation_filter = content.get("operation")

        if operation_filter:
            if operation_filter in self.circuit_breakers:
                circuit = self.circuit_breakers[operation_filter]
                return {
                    "status": "success",
                    "circuit": asdict(circuit)
                }
            else:
                return {"status": "not_found", "operation": operation_filter}
        else:
            return {
                "status": "success",
                "circuits": {
                    name: asdict(circuit)
                    for name, circuit in self.circuit_breakers.items()
                }
            }

    def _reset_circuit(self, content: Dict) -> Dict:
        """Reset circuit breaker."""
        operation = content.get("operation")

        if not operation:
            return {"status": "error", "reason": "operation required"}

        if operation in self.circuit_breakers:
            circuit = self.circuit_breakers[operation]
            circuit.state = CircuitState.CLOSED
            circuit.failure_count = 0
            circuit.success_count = 0

            self.session_logger.log_agent_activity(
                self.agent_id,
                f"Circuit reset: {operation}"
            )

            return {"status": "reset", "operation": operation}
        else:
            return {"status": "not_found", "operation": operation}

    def _get_executor_stats(self) -> Dict:
        """Get executor statistics."""
        return {
            "agent_id": self.agent_id,
            "stats": self.stats,
            "circuit_breakers": len(self.circuit_breakers),
            "open_circuits": sum(
                1 for c in self.circuit_breakers.values() if c.state == CircuitState.OPEN
            ),
            "execution_history_size": len(self.execution_history),
            "recent_success_rate": self._calculate_recent_success_rate()
        }

    def _calculate_recent_success_rate(self) -> float:
        """Calculate success rate from recent executions."""
        if not self.execution_history:
            return 0.0

        recent = list(self.execution_history)[-100:]  # Last 100
        successes = sum(1 for r in recent if r.success)
        return (successes / len(recent) * 100) if recent else 0.0

    async def on_start(self):
        """Executor-specific startup."""
        await super().on_start()
        self.session_logger.log_agent_ready(
            self.agent_id,
            "Executor active - advanced retry and circuit breaker enabled"
        )
