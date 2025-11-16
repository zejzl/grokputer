"""
Flow Definition DSL for GG Framework

Provides a Pythonic way to define workflows.

Author: Grokputer Team
Date: 2025-11-14
"""

from typing import Any, Dict, List, Optional

from .engine import WorkflowEngine
from .nodes.base import BaseNode, NodeContext


class Workflow:
    """
    High-level workflow builder using Python DSL.

    Example:
        workflow = Workflow("my_workflow")
        workflow.add_node(http_node)
        workflow.add_node(transform_node)
        workflow.add_edge(http_node, transform_node)
        result = await workflow.run({"url": "https://api.example.com"})
    """

    def __init__(self, name: str, config: Optional[Dict] = None):
        """
        Initialize workflow.

        Args:
            name: Workflow name
            config: Configuration options
        """
        self.name = name
        self.config = config or {}
        self.engine = WorkflowEngine(name, config)

    def add_node(self, node: BaseNode) -> "Workflow":
        """
        Add a node to the workflow.

        Args:
            node: Node to add

        Returns:
            Self for chaining
        """
        self.engine.add_node(node)
        return self

    def add_edge(
        self,
        from_node: BaseNode,
        to_node: BaseNode,
        condition: Optional[str] = None,
    ) -> "Workflow":
        """
        Connect two nodes.

        Args:
            from_node: Source node
            to_node: Target node
            condition: Optional condition (for conditional nodes)

        Returns:
            Self for chaining
        """
        from_node.connect_to(to_node)

        # Store condition if provided (for conditional nodes)
        if condition:
            if not hasattr(from_node, "conditions"):
                from_node.conditions = {}
            from_node.conditions[condition] = to_node

        return self

    def remove_node(self, node_id: str) -> "Workflow":
        """Remove a node."""
        self.engine.remove_node(node_id)
        return self

    async def run(
        self,
        initial_data: Optional[Dict] = None,
        parallel: bool = True,
    ) -> Dict[str, Any]:
        """
        Execute the workflow.

        Args:
            initial_data: Initial data
            parallel: Use parallel execution

        Returns:
            Final context data
        """
        return await self.engine.run(initial_data, parallel)

    def get_status(self) -> Dict:
        """Get workflow status."""
        return self.engine.get_status()

    def reset(self) -> None:
        """Reset workflow for re-execution."""
        self.engine.reset()

    # Hooks
    def on_start(self, callback):
        """Set start callback."""
        self.engine.on_start = callback
        return self

    def on_complete(self, callback):
        """Set completion callback."""
        self.engine.on_complete = callback
        return self

    def on_node_start(self, callback):
        """Set node start callback."""
        self.engine.on_node_start = callback
        return self

    def on_node_complete(self, callback):
        """Set node complete callback."""
        self.engine.on_node_complete = callback
        return self

    def on_error(self, callback):
        """Set error callback."""
        self.engine.on_error = callback
        return self

    def __repr__(self) -> str:
        return f"Workflow(name='{self.name}', nodes={len(self.engine.nodes)})"
