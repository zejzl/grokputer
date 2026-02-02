"""
Workflow Execution Engine for GG Framework

This module provides async execution of workflow graphs with:
- DAG execution (topological ordering)
- Parallel execution of independent nodes
- Error handling and retries
- State management
- Event hooks

Author: Grokputer Team
Date: 2025-11-14
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from .nodes.base import BaseNode, NodeContext, NodeStatus

logger = logging.getLogger(__name__)


class WorkflowEngine:
    """
    Async workflow execution engine.

    Executes nodes in a workflow graph, handling:
    - Dependency resolution (topological sort)
    - Parallel execution where possible
    - Error handling and retries
    - State persistence
    - Progress tracking
    """

    def __init__(self, workflow_id: str, config: Optional[Dict] = None):
        """
        Initialize the engine.

        Args:
            workflow_id: Unique identifier for this workflow
            config: Engine configuration
        """
        self.workflow_id = workflow_id
        self.config = config or {}
        self.nodes: Dict[str, BaseNode] = {}
        self.start_nodes: List[BaseNode] = []
        self.end_nodes: List[BaseNode] = []

        # Execution state
        self.context: Optional[NodeContext] = None
        self.execution_order: List[BaseNode] = []
        self.is_running = False
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None

        # Hooks
        self.on_start: Optional[Callable] = None
        self.on_complete: Optional[Callable] = None
        self.on_node_start: Optional[Callable] = None
        self.on_node_complete: Optional[Callable] = None
        self.on_error: Optional[Callable] = None

    def add_node(self, node: BaseNode) -> None:
        """
        Add a node to the workflow.

        Args:
            node: Node to add
        """
        self.nodes[node.node_id] = node
        self._update_start_end_nodes()

    def _update_start_end_nodes(self) -> None:
        """Update start and end node lists based on current connections."""
        self.start_nodes = [node for node in self.nodes.values() if len(node.inputs) == 0]
        self.end_nodes = [node for node in self.nodes.values() if len(node.outputs) == 0]

    def remove_node(self, node_id: str) -> None:
        """Remove a node from the workflow."""
        if node_id in self.nodes:
            node = self.nodes[node_id]

            # Disconnect from other nodes
            for inp in node.inputs:
                inp.disconnect_from(node)
            for out in node.outputs:
                node.disconnect_from(out)

            del self.nodes[node_id]
            self._update_start_end_nodes()

    def get_execution_order(self) -> List[BaseNode]:
        """
        Get topological sort of nodes for execution.

        Returns:
            List of nodes in execution order

        Raises:
            ValueError: If workflow has cycles
        """
        # Kahn's algorithm for topological sort
        in_degree = {node.node_id: len(node.inputs) for node in self.nodes.values()}

        queue = [node for node in self.nodes.values() if in_degree[node.node_id] == 0]
        result = []

        while queue:
            node = queue.pop(0)
            result.append(node)

            for output in node.outputs:
                in_degree[output.node_id] -= 1
                if in_degree[output.node_id] == 0:
                    queue.append(output)

        if len(result) != len(self.nodes):
            # Debug info
            logger.error(f"Result: {len(result)} nodes, Expected: {len(self.nodes)} nodes")
            logger.error(f"In-degrees: {in_degree}")
            raise ValueError("Workflow has cycles - cannot execute")

        return result

    def get_parallel_batches(self) -> List[List[BaseNode]]:
        """
        Group nodes into batches that can execute in parallel.

        Returns:
            List of batches (each batch can run in parallel)
        """
        execution_order = self.get_execution_order()
        batches = []
        executed = set()

        while len(executed) < len(execution_order):
            batch = []
            for node in execution_order:
                if node in executed:
                    continue

                # Check if all inputs are executed
                if all(inp in executed or inp not in self.nodes.values() for inp in node.inputs):
                    batch.append(node)

            if not batch:
                raise ValueError("Cannot create execution batches - workflow error")

            batches.append(batch)
            executed.update(batch)

        return batches

    async def execute_node(self, node: BaseNode, context: NodeContext) -> NodeContext:
        """
        Execute a single node with hooks and error handling.

        Args:
            node: Node to execute
            context: Current context

        Returns:
            Updated context
        """
        logger.info(f"[{self.workflow_id}] Executing node: {node.node_id}")

        # Call pre-hook
        if self.on_node_start:
            await self.on_node_start(node, context)

        try:
            # Execute with retries if configured
            max_retries = node.get_config("max_retries", 0)
            retry_delay = node.get_config("retry_delay", 1.0)

            for attempt in range(max_retries + 1):
                try:
                    result_context = await node.run(context)
                    break
                except Exception as e:
                    if attempt < max_retries:
                        logger.warning(f"Node {node.node_id} failed (attempt {attempt + 1}/{max_retries + 1}), retrying...")
                        await asyncio.sleep(retry_delay)
                    else:
                        raise

            # Call post-hook
            if self.on_node_complete:
                await self.on_node_complete(node, result_context)

            return result_context

        except Exception as e:
            logger.error(f"Node {node.node_id} failed: {e}")

            # Call error hook
            if self.on_error:
                await self.on_error(node, e, context)

            raise

    async def execute_batch(self, batch: List[BaseNode], context: NodeContext) -> NodeContext:
        """
        Execute a batch of nodes in parallel.

        Args:
            batch: Nodes to execute
            context: Current context

        Returns:
            Updated context (merged from all nodes)
        """
        if len(batch) == 1:
            # Single node - execute directly
            return await self.execute_node(batch[0], context)

        # Multiple nodes - execute in parallel
        logger.info(f"[{self.workflow_id}] Executing batch of {len(batch)} nodes in parallel")

        tasks = [self.execute_node(node, context) for node in batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Check for errors
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                node = batch[i]
                raise Exception(f"Node {node.node_id} failed in batch: {result}")

        # Merge results (last node wins for conflicting keys)
        merged_context = context
        for result in results:
            if isinstance(result, NodeContext):
                merged_context.data.update(result.data)
                merged_context.state.update(result.state)

        return merged_context

    async def run(
        self,
        initial_data: Optional[Dict] = None,
        parallel: bool = True,
    ) -> Dict[str, Any]:
        """
        Execute the entire workflow.

        Args:
            initial_data: Initial data to pass to workflow
            parallel: Whether to execute independent nodes in parallel

        Returns:
            Final workflow context data

        Raises:
            Exception: If workflow execution fails
        """
        if self.is_running:
            raise RuntimeError("Workflow is already running")

        if not self.nodes:
            raise ValueError("Workflow has no nodes")

        self.is_running = True
        self.start_time = datetime.now()

        try:
            # Initialize context
            self.context = NodeContext(
                data=initial_data or {},
                metadata={
                    "workflow_id": self.workflow_id,
                    "start_time": self.start_time.isoformat(),
                },
                state={},
            )

            logger.info(f"[{self.workflow_id}] Starting workflow execution")

            # Call start hook
            if self.on_start:
                await self.on_start(self.context)

            # Execute workflow
            if parallel:
                # Parallel execution by batches
                batches = self.get_parallel_batches()
                logger.info(f"[{self.workflow_id}] Executing {len(batches)} batches")

                for i, batch in enumerate(batches):
                    logger.info(f"[{self.workflow_id}] Batch {i + 1}/{len(batches)}")
                    self.context = await self.execute_batch(batch, self.context)
            else:
                # Sequential execution
                execution_order = self.get_execution_order()
                for node in execution_order:
                    self.context = await self.execute_node(node, self.context)

            self.end_time = datetime.now()
            duration = (self.end_time - self.start_time).total_seconds()

            logger.info(f"[{self.workflow_id}] Workflow completed in {duration:.2f}s")

            # Call completion hook
            if self.on_complete:
                await self.on_complete(self.context)

            return self.context.data

        except Exception as e:
            self.end_time = datetime.now()
            logger.error(f"[{self.workflow_id}] Workflow failed: {e}")
            raise

        finally:
            self.is_running = False

    def get_status(self) -> Dict[str, Any]:
        """Get current workflow status."""
        return {
            "workflow_id": self.workflow_id,
            "is_running": self.is_running,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "node_count": len(self.nodes),
            "nodes": {node_id: node.status.value for node_id, node in self.nodes.items()},
        }

    def reset(self) -> None:
        """Reset workflow for re-execution."""
        for node in self.nodes.values():
            node.reset()
        self.context = None
        self.is_running = False
        self.start_time = None
        self.end_time = None
