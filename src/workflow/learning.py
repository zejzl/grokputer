"""
Learning Loop for GG Workflow Framework

Provides reinforcement learning and optimization for workflows:
- Tracks workflow execution performance
- Learns optimal node configurations
- Suggests improvements based on historical data
- Integrates with Pantheon Learner agent for advanced RL

Author: Grokputer Team
Date: 2026-01-01
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Tuple

from .engine import WorkflowEngine
from .nodes.base import NodeContext, NodeStatus
from .state import StateManager

logger = logging.getLogger(__name__)


@dataclass
class WorkflowMetrics:
    """Performance metrics for a workflow execution."""

    workflow_id: str
    execution_time: float
    node_count: int
    success_count: int
    failure_count: int
    node_times: Dict[str, float]
    total_retries: int
    timestamp: float

    def success_rate(self) -> float:
        """Calculate success rate."""
        total = self.success_count + self.failure_count
        return (self.success_count / total) if total > 0 else 0.0


@dataclass
class OptimizationSuggestion:
    """Suggestion for workflow optimization."""

    suggestion_type: str  # "node_config", "parallelization", "timeout", "retry"
    confidence: float  # 0-1
    description: str
    target_node: Optional[str] = None
    proposed_change: Optional[Dict[str, Any]] = None
    expected_improvement: Optional[str] = None


class WorkflowLearner:
    """
    Learning system for workflow optimization.

    Tracks execution patterns and suggests improvements.
    """

    def __init__(
        self,
        state: Optional[StateManager] = None,
        history_size: int = 100,
        min_samples: int = 5,
    ):
        """
        Initialize workflow learner.

        Args:
            state: StateManager for persistence
            history_size: Number of executions to track
            min_samples: Minimum samples before making suggestions
        """
        self.state = state
        self.history_size = history_size
        self.min_samples = min_samples

        # Execution history
        self.execution_history: deque = deque(maxlen=history_size)

        # Performance tracking
        self.node_performance: Dict[str, List[float]] = defaultdict(list)
        self.node_failures: Dict[str, int] = defaultdict(int)
        self.node_retries: Dict[str, int] = defaultdict(int)

        # Configuration effectiveness
        self.config_effectiveness: Dict[str, List[Tuple[Dict, bool]]] = defaultdict(list)

        logger.info(f"[Learning] Initialized with history_size={history_size}")

    async def record_execution(
        self, workflow: WorkflowEngine, success: bool, error: Optional[str] = None
    ) -> WorkflowMetrics:
        """
        Record workflow execution for learning.

        Args:
            workflow: Executed workflow
            success: Whether execution succeeded
            error: Error message if failed

        Returns:
            WorkflowMetrics for this execution
        """
        # Calculate metrics
        execution_time = 0.0
        if workflow.end_time and workflow.start_time:
            execution_time = (workflow.end_time - workflow.start_time).total_seconds()

        node_times = {}
        success_count = 0
        failure_count = 0
        total_retries = 0

        for node_id, node in workflow.nodes.items():
            # Track node performance
            if hasattr(node, "result") and node.result:
                node_time = getattr(node, "execution_time", 0.0)
                node_times[node_id] = node_time
                self.node_performance[node_id].append(node_time)

            # Track status
            if node.status == NodeStatus.SUCCESS:
                success_count += 1
            elif node.status == NodeStatus.FAILED:
                failure_count += 1
                self.node_failures[node_id] += 1

            # Track retries
            if node.get_config("max_retries"):
                total_retries += node.get_config("max_retries", 0)
                self.node_retries[node_id] += 1

        # Create metrics
        metrics = WorkflowMetrics(
            workflow_id=workflow.workflow_id,
            execution_time=execution_time,
            node_count=len(workflow.nodes),
            success_count=success_count,
            failure_count=failure_count,
            node_times=node_times,
            total_retries=total_retries,
            timestamp=time.time(),
        )

        # Store in history
        self.execution_history.append(metrics)

        # Persist to state if available
        if self.state:
            await self.state.set(f"metrics_{metrics.workflow_id}_{int(metrics.timestamp)}", asdict(metrics))

        logger.info(
            f"[Learning] Recorded execution: {workflow.workflow_id} "
            f"(success={success}, time={execution_time:.2f}s)"
        )

        return metrics

    async def get_suggestions(
        self, workflow_id: str, min_confidence: float = 0.6
    ) -> List[OptimizationSuggestion]:
        """
        Get optimization suggestions for a workflow.

        Args:
            workflow_id: Workflow to optimize
            min_confidence: Minimum confidence threshold

        Returns:
            List of optimization suggestions
        """
        suggestions = []

        # Check if we have enough samples
        workflow_executions = [m for m in self.execution_history if m.workflow_id == workflow_id]
        if len(workflow_executions) < self.min_samples:
            logger.debug(
                f"[Learning] Not enough samples for {workflow_id} "
                f"({len(workflow_executions)}/{self.min_samples})"
            )
            return suggestions

        # Analyze slow nodes
        slow_nodes = self._detect_slow_nodes(workflow_executions)
        for node_id, avg_time in slow_nodes:
            suggestions.append(
                OptimizationSuggestion(
                    suggestion_type="timeout",
                    confidence=0.8,
                    description=f"Node '{node_id}' is slow (avg {avg_time:.2f}s)",
                    target_node=node_id,
                    proposed_change={"timeout": avg_time * 1.5},
                    expected_improvement="Better timeout handling",
                )
            )

        # Analyze failing nodes
        failing_nodes = self._detect_failing_nodes()
        for node_id, failure_rate in failing_nodes:
            if failure_rate > 0.3:  # > 30% failure rate
                suggestions.append(
                    OptimizationSuggestion(
                        suggestion_type="retry",
                        confidence=0.9,
                        description=f"Node '{node_id}' fails often ({failure_rate*100:.1f}%)",
                        target_node=node_id,
                        proposed_change={"max_retries": 3, "retry_delay": 2.0},
                        expected_improvement="Increased reliability",
                    )
                )

        # Analyze parallelization opportunities
        parallel_suggestions = self._detect_parallelization_opportunities(workflow_executions)
        suggestions.extend(parallel_suggestions)

        # Filter by confidence
        suggestions = [s for s in suggestions if s.confidence >= min_confidence]

        logger.info(f"[Learning] Generated {len(suggestions)} suggestions for {workflow_id}")
        return suggestions

    def _detect_slow_nodes(
        self, executions: List[WorkflowMetrics]
    ) -> List[Tuple[str, float]]:
        """Detect nodes that are consistently slow."""
        node_times = defaultdict(list)

        for metrics in executions:
            for node_id, time_val in metrics.node_times.items():
                node_times[node_id].append(time_val)

        slow_nodes = []
        for node_id, times in node_times.items():
            if len(times) >= self.min_samples:
                avg_time = sum(times) / len(times)
                # Consider slow if > 5 seconds
                if avg_time > 5.0:
                    slow_nodes.append((node_id, avg_time))

        return sorted(slow_nodes, key=lambda x: x[1], reverse=True)

    def _detect_failing_nodes(self) -> List[Tuple[str, float]]:
        """Detect nodes with high failure rates."""
        failing_nodes = []

        for node_id, failure_count in self.node_failures.items():
            total_count = failure_count + len(self.node_performance.get(node_id, []))
            if total_count >= self.min_samples:
                failure_rate = failure_count / total_count
                failing_nodes.append((node_id, failure_rate))

        return sorted(failing_nodes, key=lambda x: x[1], reverse=True)

    def _detect_parallelization_opportunities(
        self, executions: List[WorkflowMetrics]
    ) -> List[OptimizationSuggestion]:
        """Detect nodes that could be parallelized."""
        suggestions = []

        # This is a simplified heuristic - in reality, would analyze node dependencies
        if executions:
            avg_node_count = sum(m.node_count for m in executions) / len(executions)
            avg_time = sum(m.execution_time for m in executions) / len(executions)

            # If many nodes and slow execution, suggest parallelization
            if avg_node_count >= 5 and avg_time > 10.0:
                suggestions.append(
                    OptimizationSuggestion(
                        suggestion_type="parallelization",
                        confidence=0.7,
                        description=f"Workflow has {avg_node_count:.0f} nodes taking {avg_time:.1f}s",
                        proposed_change={"parallel": True},
                        expected_improvement="Faster execution through parallelization",
                    )
                )

        return suggestions

    async def apply_suggestions(
        self, workflow: WorkflowEngine, suggestions: List[OptimizationSuggestion]
    ) -> int:
        """
        Apply optimization suggestions to a workflow.

        Args:
            workflow: Workflow to optimize
            suggestions: Suggestions to apply

        Returns:
            Number of suggestions applied
        """
        applied = 0

        for suggestion in suggestions:
            if suggestion.target_node and suggestion.proposed_change:
                node = workflow.nodes.get(suggestion.target_node)
                if node:
                    # Apply config changes
                    for key, value in suggestion.proposed_change.items():
                        node.set_config(key, value)
                    applied += 1
                    logger.info(
                        f"[Learning] Applied {suggestion.suggestion_type} to {suggestion.target_node}"
                    )

        return applied

    def get_statistics(self) -> Dict[str, Any]:
        """Get learning statistics."""
        return {
            "total_executions": len(self.execution_history),
            "tracked_nodes": len(self.node_performance),
            "total_failures": sum(self.node_failures.values()),
            "avg_execution_time": (
                sum(m.execution_time for m in self.execution_history)
                / len(self.execution_history)
                if self.execution_history
                else 0.0
            ),
        }


class PantheonLearnerIntegration:
    """
    Integration with Pantheon Learner agent for advanced RL.

    Delegates complex learning tasks to the Pantheon Learner.
    """

    def __init__(self, pantheon_integration=None):
        """
        Initialize Pantheon learner integration.

        Args:
            pantheon_integration: PantheonIntegration instance
        """
        self.pantheon = pantheon_integration

    async def request_optimization(
        self, workflow_id: str, metrics: List[WorkflowMetrics]
    ) -> List[OptimizationSuggestion]:
        """
        Request optimization suggestions from Pantheon Learner.

        Args:
            workflow_id: Workflow to optimize
            metrics: Historical metrics

        Returns:
            List of suggestions from Pantheon Learner
        """
        if not self.pantheon:
            logger.warning("[Learning] Pantheon integration not available")
            return []

        # Prepare context for Pantheon Learner
        context = {
            "workflow_id": workflow_id,
            "metrics": [asdict(m) for m in metrics[-10:]],  # Last 10 executions
        }

        try:
            response = await self.pantheon.invoke_agent(
                "learner",
                f"Analyze workflow '{workflow_id}' and suggest optimizations",
                context,
                timeout=15.0,
            )

            # Parse suggestions from response
            suggestions = []
            if "suggestions" in response:
                for s in response["suggestions"]:
                    suggestions.append(
                        OptimizationSuggestion(
                            suggestion_type=s.get("type", "unknown"),
                            confidence=s.get("confidence", 0.5),
                            description=s.get("description", ""),
                            target_node=s.get("target_node"),
                            proposed_change=s.get("proposed_change"),
                            expected_improvement=s.get("expected_improvement"),
                        )
                    )

            logger.info(
                f"[Learning] Received {len(suggestions)} suggestions from Pantheon Learner"
            )
            return suggestions

        except Exception as e:
            logger.error(f"[Learning] Pantheon Learner error: {e}")
            return []
