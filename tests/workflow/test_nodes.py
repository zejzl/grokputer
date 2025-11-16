"""
Unit tests for workflow nodes.

Author: Grokputer Team
Date: 2025-11-16
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch

from src.workflow.nodes.base import BaseNode, NodeContext, NodeStatus
from src.workflow.nodes.conditional import ConditionalNode
from src.workflow.nodes.http import HTTPNode
from src.workflow.nodes.transform import TransformNode


class TestNodeContext:
    """Test NodeContext functionality."""

    def test_context_initialization(self):
        """Test context can be initialized with data."""
        ctx = NodeContext(data={"key": "value"}, metadata={"run_id": "123"})
        assert ctx.get("key") == "value"
        assert ctx.metadata["run_id"] == "123"

    def test_context_set_get(self):
        """Test setting and getting values."""
        ctx = NodeContext()
        ctx.set("name", "test")
        assert ctx.get("name") == "test"
        assert ctx.get("missing", "default") == "default"

    def test_context_state(self):
        """Test state management."""
        ctx = NodeContext()
        ctx.set_state("counter", 42)
        assert ctx.get_state("counter") == 42


class DummyNode(BaseNode):
    """Simple test node."""

    async def execute(self, context: NodeContext) -> NodeContext:
        context.set("executed", True)
        return context


class FailingNode(BaseNode):
    """Node that always fails."""

    async def execute(self, context: NodeContext) -> NodeContext:
        raise ValueError("Intentional failure")


class TestBaseNode:
    """Test BaseNode functionality."""

    @pytest.mark.asyncio
    async def test_node_execution(self):
        """Test basic node execution."""
        node = DummyNode("test_node")
        ctx = NodeContext()

        result = await node.run(ctx)

        assert node.status == NodeStatus.SUCCESS
        assert result.get("executed") is True

    @pytest.mark.asyncio
    async def test_node_failure(self):
        """Test node handles failures."""
        node = FailingNode("fail_node")
        ctx = NodeContext()

        with pytest.raises(ValueError, match="Intentional failure"):
            await node.run(ctx)

        assert node.status == NodeStatus.FAILED
        assert "Intentional failure" in node.error

    @pytest.mark.asyncio
    async def test_node_continue_on_error(self):
        """Test node can continue on error."""
        node = FailingNode("fail_node", config={"continue_on_error": True})
        ctx = NodeContext()

        result = await node.run(ctx)

        assert node.status == NodeStatus.FAILED
        assert result.get_state("fail_node_error") is not None

    def test_node_connections(self):
        """Test node connections."""
        node1 = DummyNode("node1")
        node2 = DummyNode("node2")

        node1.connect_to(node2)

        assert node2 in node1.outputs
        assert node1 in node2.inputs

    def test_node_reset(self):
        """Test node reset."""
        node = DummyNode("test")
        node.status = NodeStatus.SUCCESS
        node.error = "some error"
        node.result = {"data": "value"}

        node.reset()

        assert node.status == NodeStatus.PENDING
        assert node.error is None
        assert node.result is None


class TestConditionalNode:
    """Test ConditionalNode functionality."""

    @pytest.mark.asyncio
    async def test_simple_condition_true(self):
        """Test simple condition evaluates to true."""
        node = ConditionalNode(
            "check",
            config={"conditions": [{"field": "age", "operator": ">", "value": 18}]},
        )

        ctx = NodeContext(data={"age": 25})
        result = await node.run(ctx)

        assert result.get("branch") == "true"

    @pytest.mark.asyncio
    async def test_simple_condition_false(self):
        """Test simple condition evaluates to false."""
        node = ConditionalNode(
            "check",
            config={"conditions": [{"field": "age", "operator": ">", "value": 18}]},
        )

        ctx = NodeContext(data={"age": 15})
        result = await node.run(ctx)

        assert result.get("branch") == "false"

    @pytest.mark.asyncio
    async def test_multiple_conditions_and(self):
        """Test multiple conditions with AND logic."""
        node = ConditionalNode(
            "check",
            config={
                "conditions": [
                    {"field": "age", "operator": ">=", "value": 18},
                    {"field": "name", "operator": "contains", "value": "John"},
                ],
                "logic": "and",
            },
        )

        ctx = NodeContext(data={"age": 25, "name": "John Doe"})
        result = await node.run(ctx)

        assert result.get("branch") == "true"

        # Test failure case
        ctx2 = NodeContext(data={"age": 25, "name": "Jane Doe"})
        result2 = await node.run(ctx2)
        assert result2.get("branch") == "false"

    @pytest.mark.asyncio
    async def test_multiple_conditions_or(self):
        """Test multiple conditions with OR logic."""
        node = ConditionalNode(
            "check",
            config={
                "conditions": [
                    {"field": "role", "operator": "==", "value": "admin"},
                    {"field": "permissions", "operator": "contains", "value": "write"},
                ],
                "logic": "or",
            },
        )

        ctx = NodeContext(data={"role": "user", "permissions": ["read", "write"]})
        result = await node.run(ctx)

        assert result.get("branch") == "true"

    @pytest.mark.asyncio
    async def test_nested_field_access(self):
        """Test accessing nested fields with dot notation."""
        node = ConditionalNode(
            "check",
            config={
                "conditions": [
                    {"field": "user.profile.verified", "operator": "==", "value": True}
                ]
            },
        )

        ctx = NodeContext(data={"user": {"profile": {"verified": True}}})
        result = await node.run(ctx)

        assert result.get("branch") == "true"


class TestHTTPNode:
    """Test HTTPNode functionality."""

    @pytest.mark.asyncio
    async def test_http_get_request(self):
        """Test HTTP GET request."""
        node = HTTPNode(
            "fetch",
            config={
                "url": "https://api.example.com/data",
                "method": "GET",
                "headers": {"Accept": "application/json"},
            },
        )

        # Mock aiohttp
        with patch("aiohttp.ClientSession") as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.headers = {"Content-Type": "application/json"}
            mock_response.json = AsyncMock(return_value={"result": "success"})

            mock_session.return_value.__aenter__.return_value.request.return_value.__aenter__.return_value = (
                mock_response
            )

            ctx = NodeContext()
            result = await node.run(ctx)

            assert result.get("status_code") == 200
            assert result.get("body")["result"] == "success"

    @pytest.mark.asyncio
    async def test_http_post_with_body(self):
        """Test HTTP POST with JSON body."""
        node = HTTPNode(
            "create",
            config={
                "url": "https://api.example.com/items",
                "method": "POST",
                "body": {"name": "{{item_name}}", "value": 42},
            },
        )

        with patch("aiohttp.ClientSession") as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 201
            mock_response.headers = {"Content-Type": "application/json"}
            mock_response.json = AsyncMock(return_value={"id": "123"})

            mock_session.return_value.__aenter__.return_value.request.return_value.__aenter__.return_value = (
                mock_response
            )

            ctx = NodeContext(data={"item_name": "TestItem"})
            result = await node.run(ctx)

            assert result.get("status_code") == 201

    @pytest.mark.asyncio
    async def test_http_authentication(self):
        """Test HTTP with Bearer token auth."""
        node = HTTPNode(
            "auth_fetch",
            config={
                "url": "https://api.example.com/protected",
                "method": "GET",
                "auth": {"bearer_token": "{{api_token}}"},
            },
        )

        with patch("aiohttp.ClientSession") as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.headers = {"Content-Type": "application/json"}
            mock_response.json = AsyncMock(return_value={"data": "secured"})

            mock_session.return_value.__aenter__.return_value.request.return_value.__aenter__.return_value = (
                mock_response
            )

            ctx = NodeContext(data={"api_token": "secret123"})
            result = await node.run(ctx)

            assert result.get("status_code") == 200


class TestTransformNode:
    """Test TransformNode functionality."""

    @pytest.mark.asyncio
    async def test_transform_with_function(self):
        """Test transform node with custom function."""

        def double_value(data):
            return {**data, "value": data.get("value", 0) * 2}

        node = TransformNode("double", transform_func=double_value)

        ctx = NodeContext(data={"value": 5})
        result = await node.run(ctx)

        assert result.get("value") == 10

    @pytest.mark.asyncio
    async def test_transform_jq_extract(self):
        """Test JQ-style extraction."""
        node = TransformNode(
            "extract", config={"operation": "jq", "expression": ".user.name"}
        )

        ctx = NodeContext(data={"user": {"name": "Alice", "age": 30}})
        result = await node.run(ctx)

        assert result.get("result") == "Alice"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
