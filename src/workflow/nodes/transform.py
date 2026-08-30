"""
Transform Node for GG Workflow Framework

Applies transformations to data using custom functions.

Author: Grokputer Team
Date: 2025-11-14
"""
from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from .base import BaseNode, NodeContext


class TransformNode(BaseNode):
    """
    Node that transforms data using a custom function.

    The function receives the context data and returns transformed data.
    """

    def __init__(
        self,
        node_id: str,
        transform_func: Optional[Callable] = None,
        name: Optional[str] = None,
        config: Optional[Dict] = None,
    ):
        """
        Initialize transform node.

        Args:
            node_id: Node identifier
            transform_func: Function to transform data (data -> data)
            name: Node name
            config: Configuration
        """
        super().__init__(node_id, name, config)
        self.transform_func = transform_func or (lambda x: x)

    async def execute(self, context: NodeContext) -> NodeContext:
        """
        Apply transformation to context data.

        Args:
            context: Input context

        Returns:
            Context with transformed data
        """
        # Apply transformation
        if callable(self.transform_func):
            transformed_data = self.transform_func(context.data)
        else:
            # If not callable, use as-is
            transformed_data = context.data

        # Create new context with transformed data
        new_context = NodeContext(
            data=transformed_data,
            metadata=context.metadata,
            state=context.state,
        )

        return new_context


class MapNode(TransformNode):
    """Transform node that maps a function over a list."""

    async def execute(self, context: NodeContext) -> NodeContext:
        """Map function over input list."""
        input_key = self.get_config("input_key", "items")
        output_key = self.get_config("output_key", "results")

        items = context.get(input_key, [])
        results = [self.transform_func(item) for item in items]

        context.set(output_key, results)
        return context


class FilterNode(TransformNode):
    """Transform node that filters a list."""

    async def execute(self, context: NodeContext) -> NodeContext:
        """Filter items based on function."""
        input_key = self.get_config("input_key", "items")
        output_key = self.get_config("output_key", "filtered")

        items = context.get(input_key, [])
        filtered = [item for item in items if self.transform_func(item)]

        context.set(output_key, filtered)
        return context


class MergeNode(BaseNode):
    """Node that merges data from multiple inputs."""

    async def execute(self, context: NodeContext) -> NodeContext:
        """Merge data from inputs."""
        # All input data should already be merged by engine
        return context
