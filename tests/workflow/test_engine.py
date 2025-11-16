"""
Unit tests for workflow engine.

Author: Grokputer Team
Date: 2025-11-16
"""

import pytest
from unittest.mock import AsyncMock

from src.workflow.engine import WorkflowEngine
from src.workflow.flow import Workflow
from src.workflow.nodes.base import BaseNode, NodeContext, NodeStatus


class SimpleNode(BaseNode):
    """Simple node for testing."""

    async def execute(self, context: NodeContext) -> NodeContext:
        value = context.get("value", 0)
        context.set("value", value + 1)
        context.set(f"{self.node_id}_executed", True)
        return context


class SlowNode(BaseNode):
    """Simulates a slow operation."""

    async def execute(self, context: NodeContext) -> NodeContext:
        import asyncio

        await asyncio.sleep(0.1)
        context.set("slow_done", True)
        return context


class FailNode(BaseNode):
    """Node that fails."""

    async def execute(self, context: NodeContext) -> NodeContext:
        raise RuntimeError("Node failed intentionally")


class TestWorkflowEngine:
    """Test WorkflowEngine execution."""

    @pytest.mark.asyncio
    async def test_simple_linear_workflow(self):
        """Test executing a simple linear workflow."""
        workflow = Workflow("linear_test")

        node1 = SimpleNode("node1")
        node2 = SimpleNode("node2")
        node3 = SimpleNode("node3")

        workflow.add_node(node1)
        workflow.add_node(node2)
        workflow.add_node(node3)

        workflow.add_edge(node1, node2)
        workflow.add_edge(node2, node3)

        engine = WorkflowEngine()
        result = await engine.execute(workflow, initial_data={"value": 0})

        assert result["status"] == "success"
        assert result["data"]["value"] == 3
        assert result["data"]["node1_executed"] is True
        assert result["data"]["node2_executed"] is True
        assert result["data"]["node3_executed"] is True

    @pytest.mark.asyncio
    async def test_parallel_workflow(self):
        """Test executing parallel nodes."""
        workflow = Workflow("parallel_test")

        start = SimpleNode("start")
        parallel1 = SimpleNode("p1")
        parallel2 = SimpleNode("p2")
        parallel3 = SimpleNode("p3")
        end = SimpleNode("end")

        workflow.add_node(start)
        workflow.add_node(parallel1)
        workflow.add_node(parallel2)
        workflow.add_node(parallel3)
        workflow.add_node(end)

        # Start -> 3 parallel paths -> End
        workflow.add_edge(start, parallel1)
        workflow.add_edge(start, parallel2)
        workflow.add_edge(start, parallel3)
        workflow.add_edge(parallel1, end)
        workflow.add_edge(parallel2, end)
        workflow.add_edge(parallel3, end)

        engine = WorkflowEngine()
        result = await engine.execute(workflow, initial_data={"value": 0})

        assert result["status"] == "success"
        # All parallel nodes should execute
        assert result["data"]["p1_executed"] is True
        assert result["data"]["p2_executed"] is True
        assert result["data"]["p3_executed"] is True
        assert result["data"]["end_executed"] is True

    @pytest.mark.asyncio
    async def test_workflow_with_failure(self):
        """Test workflow handles node failures."""
        workflow = Workflow("fail_test")

        node1 = SimpleNode("node1")
        fail_node = FailNode("fail")
        node2 = SimpleNode("node2")

        workflow.add_node(node1)
        workflow.add_node(fail_node)
        workflow.add_node(node2)

        workflow.add_edge(node1, fail_node)
        workflow.add_edge(fail_node, node2)

        engine = WorkflowEngine()

        with pytest.raises(RuntimeError, match="Node failed intentionally"):
            await engine.execute(workflow)

    @pytest.mark.asyncio
    async def test_workflow_execution_order(self):
        """Test nodes execute in correct order."""
        workflow = Workflow("order_test")

        execution_order = []

        class OrderNode(BaseNode):
            async def execute(self, context: NodeContext) -> NodeContext:
                execution_order.append(self.node_id)
                return context

        a = OrderNode("A")
        b = OrderNode("B")
        c = OrderNode("C")
        d = OrderNode("D")

        workflow.add_node(a)
        workflow.add_node(b)
        workflow.add_node(c)
        workflow.add_node(d)

        # A -> B -> D
        #   -> C -> D
        workflow.add_edge(a, b)
        workflow.add_edge(a, c)
        workflow.add_edge(b, d)
        workflow.add_edge(c, d)

        engine = WorkflowEngine()
        await engine.execute(workflow)

        # A should be first, D should be last
        assert execution_order[0] == "A"
        assert execution_order[-1] == "D"
        # B and C should execute after A but before D
        assert "B" in execution_order[1:-1]
        assert "C" in execution_order[1:-1]

    @pytest.mark.asyncio
    async def test_workflow_timeout(self):
        """Test workflow respects timeout."""
        workflow = Workflow("timeout_test")

        slow1 = SlowNode("slow1")
        slow2 = SlowNode("slow2")
        slow3 = SlowNode("slow3")

        workflow.add_node(slow1)
        workflow.add_node(slow2)
        workflow.add_node(slow3)

        workflow.add_edge(slow1, slow2)
        workflow.add_edge(slow2, slow3)

        engine = WorkflowEngine(timeout=0.15)  # Less than total execution time

        with pytest.raises(TimeoutError):
            await engine.execute(workflow)

    @pytest.mark.asyncio
    async def test_empty_workflow(self):
        """Test executing empty workflow."""
        workflow = Workflow("empty")
        engine = WorkflowEngine()

        result = await engine.execute(workflow)

        assert result["status"] == "success"
        assert result["nodes_executed"] == 0

    @pytest.mark.asyncio
    async def test_workflow_state_persistence(self):
        """Test workflow state is maintained across nodes."""
        workflow = Workflow("state_test")

        class StateNode(BaseNode):
            async def execute(self, context: NodeContext) -> NodeContext:
                # Each node increments counter in state
                counter = context.get_state("counter", 0)
                context.set_state("counter", counter + 1)
                return context

        node1 = StateNode("n1")
        node2 = StateNode("n2")
        node3 = StateNode("n3")

        workflow.add_node(node1)
        workflow.add_node(node2)
        workflow.add_node(node3)

        workflow.add_edge(node1, node2)
        workflow.add_edge(node2, node3)

        engine = WorkflowEngine()
        result = await engine.execute(workflow)

        # Counter should be 3 after all nodes
        assert result["state"]["counter"] == 3


class TestWorkflowValidation:
    """Test workflow validation."""

    def test_detect_cycle(self):
        """Test cycle detection."""
        workflow = Workflow("cycle_test")

        node1 = SimpleNode("n1")
        node2 = SimpleNode("n2")
        node3 = SimpleNode("n3")

        workflow.add_node(node1)
        workflow.add_node(node2)
        workflow.add_node(node3)

        workflow.add_edge(node1, node2)
        workflow.add_edge(node2, node3)
        workflow.add_edge(node3, node1)  # Creates cycle

        with pytest.raises(ValueError, match="cycle"):
            workflow.validate()

    def test_validate_missing_nodes(self):
        """Test validation catches missing nodes in edges."""
        workflow = Workflow("missing_test")

        node1 = SimpleNode("n1")
        workflow.add_node(node1)

        # Try to add edge with non-existent node
        with pytest.raises(ValueError):
            workflow.add_edge(node1, SimpleNode("n2"))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
