"""
Self-Healing for GG Workflow Framework

Provides automatic error recovery and workflow healing:
- Detects and recovers from node failures
- Implements retry strategies with exponential backoff
- Routes around failing nodes
- Integrates with Pantheon Improver agent for intelligent fixes

Author: Grokputer Team
Date: 2026-01-01
"""

import asyncio
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from .engine import WorkflowEngine
from .nodes.base import BaseNode, NodeContext, NodeStatus

logger = logging.getLogger(__name__)


class HealingStrategy(Enum):
    """Available healing strategies."""

    RETRY = "retry"  # Retry with exponential backoff
    SKIP = "skip"  # Skip failing node and continue
    REPLACE = "replace"  # Replace with fallback node
    INVOKE_IMPROVER = "invoke_improver"  # Ask Pantheon Improver for fix


@dataclass
class HealingAction:
    """Action taken by healing system."""

    node_id: str
    strategy: HealingStrategy
    attempts: int
    success: bool
    error: Optional[str] = None
    recovery_time: float = 0.0


class WorkflowHealer:
    """
    Self-healing system for workflows.

    Automatically recovers from failures using various strategies.
    """

    def __init__(
        self,
        max_healing_attempts: int = 3,
        retry_delay: float = 1.0,
        backoff_multiplier: float = 2.0,
        pantheon_integration=None,
    ):
        """
        Initialize workflow healer.

        Args:
            max_healing_attempts: Maximum healing attempts per node
            retry_delay: Initial retry delay in seconds
            backoff_multiplier: Exponential backoff multiplier
            pantheon_integration: PantheonIntegration for Improver access
        """
        self.max_healing_attempts = max_healing_attempts
        self.retry_delay = retry_delay
        self.backoff_multiplier = backoff_multiplier
        self.pantheon = pantheon_integration

        # Healing history
        self.healing_actions: List[HealingAction] = []

        # Fallback nodes registry
        self.fallback_nodes: Dict[str, BaseNode] = {}

        logger.info(
            f"[Healing] Initialized with max_attempts={max_healing_attempts}, "
            f"retry_delay={retry_delay}s"
        )

    def register_fallback(self, node_id: str, fallback_node: BaseNode) -> None:
        """
        Register a fallback node for a specific node.

        Args:
            node_id: ID of the node to replace
            fallback_node: Fallback node to use
        """
        self.fallback_nodes[node_id] = fallback_node
        logger.info(f"[Healing] Registered fallback for {node_id}")

    async def heal_node(
        self,
        node: BaseNode,
        context: NodeContext,
        error: Exception,
        strategy: Optional[HealingStrategy] = None,
    ) -> NodeContext:
        """
        Attempt to heal a failing node.

        Args:
            node: Failed node
            context: Current context
            error: Error that occurred
            strategy: Healing strategy to use (auto-selected if None)

        Returns:
            Healed context

        Raises:
            Exception: If healing fails
        """
        logger.warning(f"[Healing] Node {node.node_id} failed: {error}")

        # Auto-select strategy if not provided
        if strategy is None:
            strategy = self._select_strategy(node, error)

        start_time = asyncio.get_event_loop().time()
        action = HealingAction(
            node_id=node.node_id,
            strategy=strategy,
            attempts=0,
            success=False,
        )

        try:
            if strategy == HealingStrategy.RETRY:
                result_context = await self._retry_with_backoff(node, context)
            elif strategy == HealingStrategy.SKIP:
                result_context = await self._skip_node(node, context)
            elif strategy == HealingStrategy.REPLACE:
                result_context = await self._replace_with_fallback(node, context)
            elif strategy == HealingStrategy.INVOKE_IMPROVER:
                result_context = await self._invoke_improver(node, context, error)
            else:
                raise ValueError(f"Unknown strategy: {strategy}")

            action.success = True
            action.recovery_time = asyncio.get_event_loop().time() - start_time

            logger.info(
                f"[Healing] Successfully healed {node.node_id} using {strategy.value} "
                f"in {action.recovery_time:.2f}s"
            )

            return result_context

        except Exception as e:
            action.error = str(e)
            action.recovery_time = asyncio.get_event_loop().time() - start_time
            logger.error(f"[Healing] Failed to heal {node.node_id}: {e}")
            raise

        finally:
            self.healing_actions.append(action)

    def _select_strategy(self, node: BaseNode, error: Exception) -> HealingStrategy:
        """Auto-select best healing strategy for the error."""
        error_type = type(error).__name__

        # Timeout errors -> retry
        if "timeout" in error_type.lower() or "TimeoutError" in error_type:
            return HealingStrategy.RETRY

        # Connection errors -> retry
        if "connection" in error_type.lower() or "ConnectionError" in error_type:
            return HealingStrategy.RETRY

        # If fallback available -> replace
        if node.node_id in self.fallback_nodes:
            return HealingStrategy.REPLACE

        # If Pantheon available -> invoke improver
        if self.pantheon:
            return HealingStrategy.INVOKE_IMPROVER

        # Default -> retry
        return HealingStrategy.RETRY

    async def _retry_with_backoff(
        self, node: BaseNode, context: NodeContext
    ) -> NodeContext:
        """Retry node execution with exponential backoff."""
        delay = self.retry_delay

        for attempt in range(1, self.max_healing_attempts + 1):
            logger.info(
                f"[Healing] Retry attempt {attempt}/{self.max_healing_attempts} "
                f"for {node.node_id}"
            )

            try:
                # Reset node status
                node.reset()

                # Retry execution
                result = await node.run(context)
                logger.info(f"[Healing] Retry successful for {node.node_id}")
                return result

            except Exception as e:
                if attempt < self.max_healing_attempts:
                    logger.warning(
                        f"[Healing] Retry {attempt} failed, waiting {delay:.1f}s..."
                    )
                    await asyncio.sleep(delay)
                    delay *= self.backoff_multiplier
                else:
                    logger.error(f"[Healing] All retries exhausted for {node.node_id}")
                    raise

        raise Exception(f"Failed to heal {node.node_id} after {self.max_healing_attempts} attempts")

    async def _skip_node(self, node: BaseNode, context: NodeContext) -> NodeContext:
        """Skip the failing node and continue with current context."""
        logger.info(f"[Healing] Skipping node {node.node_id}")

        # Mark node as skipped
        node.status = NodeStatus.SKIPPED

        # Set error info in state
        context.set_state(f"{node.node_id}_skipped", True)
        context.set_state(f"{node.node_id}_skip_reason", node.error)

        return context

    async def _replace_with_fallback(
        self, node: BaseNode, context: NodeContext
    ) -> NodeContext:
        """Replace failing node with registered fallback."""
        fallback = self.fallback_nodes.get(node.node_id)

        if not fallback:
            raise ValueError(f"No fallback registered for {node.node_id}")

        logger.info(f"[Healing] Replacing {node.node_id} with fallback")

        try:
            result = await fallback.run(context)
            context.set_state(f"{node.node_id}_used_fallback", True)
            return result
        except Exception as e:
            logger.error(f"[Healing] Fallback also failed: {e}")
            raise

    async def _invoke_improver(
        self, node: BaseNode, context: NodeContext, error: Exception
    ) -> NodeContext:
        """Invoke Pantheon Improver agent to fix the issue."""
        if not self.pantheon:
            raise ValueError("Pantheon integration not available")

        logger.info(f"[Healing] Invoking Pantheon Improver for {node.node_id}")

        try:
            # Prepare diagnostic info
            diagnostic = {
                "node_id": node.node_id,
                "node_type": type(node).__name__,
                "error": str(error),
                "error_type": type(error).__name__,
                "node_config": node.config,
                "context_data": context.data,
            }

            # Request fix from Improver
            response = await self.pantheon.invoke_agent(
                "improver",
                f"Fix failing workflow node: {node.node_id}",
                diagnostic,
                timeout=20.0,
            )

            # Apply suggested fix
            if "fixed_config" in response:
                logger.info(f"[Healing] Applying Improver fix to {node.node_id}")
                for key, value in response["fixed_config"].items():
                    node.set_config(key, value)

                # Retry with fixed config
                node.reset()
                result = await node.run(context)
                context.set_state(f"{node.node_id}_improver_fixed", True)
                return result

            elif "alternative_approach" in response:
                logger.info(f"[Healing] Improver suggested alternative approach")
                # In a real implementation, would execute alternative approach
                # For now, just skip
                return await self._skip_node(node, context)

            else:
                raise Exception("Improver did not provide actionable fix")

        except Exception as e:
            logger.error(f"[Healing] Improver invocation failed: {e}")
            raise

    def get_healing_stats(self) -> Dict[str, Any]:
        """Get healing statistics."""
        total = len(self.healing_actions)
        successful = sum(1 for a in self.healing_actions if a.success)

        strategy_counts = {}
        for action in self.healing_actions:
            strategy_counts[action.strategy.value] = (
                strategy_counts.get(action.strategy.value, 0) + 1
            )

        return {
            "total_healing_attempts": total,
            "successful_healings": successful,
            "success_rate": (successful / total) if total > 0 else 0.0,
            "strategy_usage": strategy_counts,
            "avg_recovery_time": (
                sum(a.recovery_time for a in self.healing_actions) / total
                if total > 0
                else 0.0
            ),
        }


async def with_healing(
    workflow: WorkflowEngine,
    healer: WorkflowHealer,
    initial_data: Optional[Dict] = None,
) -> Dict[str, Any]:
    """
    Execute workflow with automatic healing.

    Args:
        workflow: Workflow to execute
        healer: Healer instance
        initial_data: Initial workflow data

    Returns:
        Workflow result

    Raises:
        Exception: If workflow fails and cannot be healed
    """
    try:
        return await workflow.run(initial_data)
    except Exception as e:
        logger.warning(f"[Healing] Workflow failed, attempting recovery...")

        # Try to identify failed node
        failed_nodes = [
            node for node in workflow.nodes.values() if node.status == NodeStatus.FAILED
        ]

        if not failed_nodes:
            logger.error("[Healing] No failed nodes identified")
            raise

        # Attempt to heal each failed node
        for node in failed_nodes:
            try:
                await healer.heal_node(node, workflow.context, e)
            except Exception as heal_error:
                logger.error(f"[Healing] Could not heal {node.node_id}: {heal_error}")

        # Retry workflow after healing
        logger.info("[Healing] Retrying workflow after healing...")
        return await workflow.run(initial_data)
