"""
Base Node for GG Workflow Framework

This module defines the abstract base class for all workflow nodes.
Each node performs a specific operation and can be chained together.

Author: Grokputer Team
Date: 2025-11-14
"""

import asyncio
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional


class NodeStatus(Enum):
    """Status of node execution."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class NodeContext:
    """
    Context passed between nodes during workflow execution.

    Attributes:
        data: Current data being processed
        metadata: Workflow metadata (run_id, timestamps, etc.)
        state: Workflow state (variables, cache, etc.)
    """

    def __init__(
        self,
        data: Any = None,
        metadata: Optional[Dict] = None,
        state: Optional[Dict] = None,
    ):
        self.data = data or {}
        self.metadata = metadata or {}
        self.state = state or {}

    def get(self, key: str, default: Any = None) -> Any:
        """Get data value by key."""
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set data value."""
        self.data[key] = value

    def get_state(self, key: str, default: Any = None) -> Any:
        """Get state value."""
        return self.state.get(key, default)

    def set_state(self, key: str, value: Any) -> None:
        """Set state value."""
        self.state[key] = value


class BaseNode(ABC):
    """
    Abstract base class for all workflow nodes.

    Each node:
    - Has a unique ID
    - Performs one specific operation
    - Receives input context
    - Returns output context
    - Can be connected to other nodes
    """

    def __init__(
        self,
        node_id: str,
        name: Optional[str] = None,
        config: Optional[Dict] = None,
    ):
        """
        Initialize the node.

        Args:
            node_id: Unique identifier for this node
            name: Human-readable name (defaults to node_id)
            config: Node-specific configuration
        """
        self.node_id = node_id
        self.name = name or node_id
        self.config = config or {}
        self.status = NodeStatus.PENDING
        self.error: Optional[str] = None
        self.result: Any = None

        # Connections
        self.inputs: List["BaseNode"] = []
        self.outputs: List["BaseNode"] = []

    @abstractmethod
    async def execute(self, context: NodeContext) -> NodeContext:
        """
        Execute the node's operation.

        This is the main method each node must implement.

        Args:
            context: Input context with data

        Returns:
            Output context with results

        Raises:
            Exception: If execution fails
        """
        pass

    async def run(self, context: NodeContext) -> NodeContext:
        """
        Run the node with error handling and status tracking.

        Args:
            context: Input context

        Returns:
            Output context

        Raises:
            Exception: If execution fails and error handling is not configured
        """
        try:
            self.status = NodeStatus.RUNNING
            result_context = await self.execute(context)
            self.status = NodeStatus.SUCCESS
            self.result = result_context.data
            return result_context

        except Exception as e:
            self.status = NodeStatus.FAILED
            self.error = str(e)

            # Check if we should raise or continue
            if self.config.get("continue_on_error", False):
                # Return context with error info
                context.set_state(f"{self.node_id}_error", str(e))
                return context
            else:
                raise

    def connect_to(self, node: "BaseNode") -> "BaseNode":
        """
        Connect this node's output to another node's input.

        Args:
            node: Node to connect to

        Returns:
            The connected node (for chaining)
        """
        if node not in self.outputs:
            self.outputs.append(node)
        if self not in node.inputs:
            node.inputs.append(self)
        return node

    def disconnect_from(self, node: "BaseNode") -> None:
        """Disconnect from a node."""
        if node in self.outputs:
            self.outputs.remove(node)
        if self in node.inputs:
            node.inputs.remove(self)

    def get_config(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self.config.get(key, default)

    def set_config(self, key: str, value: Any) -> None:
        """Set configuration value."""
        self.config[key] = value

    def reset(self) -> None:
        """Reset node status for re-execution."""
        self.status = NodeStatus.PENDING
        self.error = None
        self.result = None

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id='{self.node_id}', status={self.status.value})"

    def to_dict(self) -> Dict:
        """Serialize node to dictionary."""
        return {
            "node_id": self.node_id,
            "name": self.name,
            "type": self.__class__.__name__,
            "status": self.status.value,
            "error": self.error,
            "config": self.config,
            "inputs": [n.node_id for n in self.inputs],
            "outputs": [n.node_id for n in self.outputs],
        }


class StartNode(BaseNode):
    """Special node that marks the start of a workflow."""

    async def execute(self, context: NodeContext) -> NodeContext:
        """Pass through context unchanged."""
        return context


class EndNode(BaseNode):
    """Special node that marks the end of a workflow."""

    async def execute(self, context: NodeContext) -> NodeContext:
        """Pass through context unchanged."""
        return context


class NoOpNode(BaseNode):
    """Node that does nothing (useful for testing)."""

    async def execute(self, context: NodeContext) -> NodeContext:
        """Pass through context unchanged."""
        return context
