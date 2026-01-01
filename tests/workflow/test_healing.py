"""
Tests for Self-Healing System (Task 15)

Ultra high priority testing for automatic workflow recovery.
"""

import asyncio
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.workflow.healing import (
    HealingStrategy,
    SelfHealingSystem,
    FailurePattern,
    CircuitBreakerState
)
from src.workflow.nodes.base import (
    BaseNode,
    NodeContext,
    NodeResult,
    NodeStatus
)


class MockFailingNode(BaseNode):
    """Mock node that fails predictably for testing"""

    def __init__(self, node_id: str, fail_count: int = 1, error_type: Exception = RuntimeError):
        super().__init__(node_id=node_id, config={"type": "mock_failing"})
        self.fail_count = fail_count
        self.error_type = error_type
        self.attempt_count = 0

    async def execute(self, context: NodeContext) -> NodeContext:
        self.attempt_count += 1
        if self.attempt_count <= self.fail_count:
            raise self.error_type(f"Mock failure {self.attempt_count}")

        result_context = NodeContext(
            data={"healed": True, "attempts": self.attempt_count},
            metadata=context.metadata,
            state=context.state
        )
        return result_context


class MockSuccessNode(BaseNode):
    """Mock node that always succeeds"""

    def __init__(self, node_id: str):
        super().__init__(node_id=node_id, config={"type": "mock_success"})

    async def execute(self, context: NodeContext) -> NodeContext:
        result_context = NodeContext(
            data={"success": True},
            metadata=context.metadata,
            state=context.state
        )
        return result_context


@pytest.fixture
def healing_system():
    """Create healing system for testing"""
    config = {
        "max_retries": 3,
        "retry_delay": 0.01,  # Fast for testing
        "circuit_breaker_threshold": 3,
        "circuit_breaker_timeout": 1,
        "pattern_detection_threshold": 2
    }
    return SelfHealingSystem(config=config)


@pytest.fixture
def node_context():
    """Create node context for testing"""
    return NodeContext(
        data={"test": "data"},
        metadata={"workflow_id": "test_workflow", "execution_id": "test_execution"}
    )


@pytest.mark.asyncio
async def test_healing_retry_success(healing_system, node_context):
    """Test successful healing through retry"""
    node = MockFailingNode("test_node", fail_count=1)

    result = await healing_system.heal_node_failure(
        node, node_context, RuntimeError("Test error")
    )

    assert result is not None
    assert result.success
    assert result.metadata["healing"] == "retry"
    assert healing_system.total_heals == 1


@pytest.mark.asyncio
async def test_healing_retry_exhaustion(healing_system, node_context):
    """Test healing with SKIP when retries exhausted"""
    node = MockFailingNode("test_node", fail_count=10)  # Will fail more than max_retries

    result = await healing_system.heal_node_failure(
        node, node_context, RuntimeError("Test error")
    )

    # Should fall back to SKIP strategy after retries fail
    assert result is not None
    assert result.status == NodeStatus.SKIPPED
    assert healing_system.total_failures == 1
    assert healing_system.total_heals == 1  # SKIP counts as healing


@pytest.mark.asyncio
async def test_healing_fallback(healing_system, node_context):
    """Test fallback strategy"""
    failing_node = MockFailingNode("failing", fail_count=10)
    fallback_node = MockSuccessNode("fallback")

    healing_system.register_fallback("failing", fallback_node)

    # Manually set strategy to use fallback first
    healing_system.set_recovery_strategies(
        "failing",
        [HealingStrategy.FALLBACK, HealingStrategy.RETRY]
    )

    result = await healing_system.heal_node_failure(
        failing_node, node_context, RuntimeError("Test error")
    )

    assert result is not None
    assert result.success
    assert result.metadata["healing"] == "fallback"


@pytest.mark.asyncio
async def test_healing_skip_strategy(healing_system, node_context):
    """Test skip strategy"""
    node = MockFailingNode("test_node", fail_count=10)

    # Set strategy to skip immediately
    healing_system.set_recovery_strategies("test_node", [HealingStrategy.SKIP])

    result = await healing_system.heal_node_failure(
        node, node_context, RuntimeError("Test error")
    )

    assert result is not None
    assert result.status == NodeStatus.SKIPPED
    assert result.metadata["healing"] == "skip"


@pytest.mark.asyncio
async def test_circuit_breaker(healing_system, node_context):
    """Test circuit breaker functionality"""
    node = MockFailingNode("test_node", fail_count=10)

    # Only allow RETRY strategy (not SKIP) so circuit breaker can trip
    healing_system.set_recovery_strategies("test_node", [HealingStrategy.RETRY])

    # Cause multiple failures to trip circuit breaker
    for _ in range(3):
        await healing_system.heal_node_failure(
            node, node_context, RuntimeError("Test error")
        )

    # Check circuit breaker is open
    breaker = healing_system.circuit_breakers["test_node"]
    assert breaker.state == "OPEN"
    assert breaker.failure_count >= 3

    # Try to heal - should be blocked by circuit breaker
    result = await healing_system.heal_node_failure(
        node, node_context, RuntimeError("Test error")
    )
    assert result is None


@pytest.mark.asyncio
async def test_circuit_breaker_reset(healing_system, node_context):
    """Test circuit breaker reset after success"""
    node = MockFailingNode("test_node", fail_count=1)

    # Record failure
    healing_system._trip_circuit_breaker("test_node")

    # Successful heal should reset breaker
    await healing_system.heal_node_failure(
        node, node_context, RuntimeError("Test error")
    )

    breaker = healing_system.circuit_breakers["test_node"]
    assert breaker.state == "CLOSED"
    assert breaker.failure_count == 0


def test_failure_pattern_recording(healing_system, node_context):
    """Test failure pattern detection"""
    # Record same error multiple times
    for _ in range(3):
        healing_system._record_failure_pattern(
            "test_node",
            ValueError("Same error"),
            node_context
        )

    patterns = healing_system.get_recurring_patterns()
    assert len(patterns) > 0

    pattern = patterns[0]
    assert pattern.node_id == "test_node"
    assert pattern.error_type == "ValueError"
    assert pattern.occurrence_count == 3


@pytest.mark.asyncio
async def test_healing_with_improver_agent(node_context):
    """Test healing with ImproverAgent integration"""
    mock_improver = MagicMock()
    mock_messagebus = MagicMock()
    mock_messagebus.publish = AsyncMock()

    healing_system = SelfHealingSystem(
        improver_agent=mock_improver,
        message_bus=mock_messagebus,
        config={"enable_agent_delegation": True}
    )

    node = MockFailingNode("test_node", fail_count=10)

    # Set strategy to delegate to agent
    healing_system.set_recovery_strategies(
        "test_node",
        [HealingStrategy.DELEGATE_TO_AGENT]
    )

    await healing_system.heal_node_failure(
        node, node_context, RuntimeError("Test error")
    )

    # Verify message was sent to ImproverAgent
    assert mock_messagebus.publish.called


def test_healing_statistics(healing_system, node_context):
    """Test healing statistics tracking"""
    stats = healing_system.get_stats()

    assert "total_failures" in stats
    assert "total_heals" in stats
    assert "success_rate" in stats
    assert "circuit_breakers" in stats


@pytest.mark.asyncio
async def test_timeout_reconfiguration(node_context):
    """Test automatic timeout reconfiguration"""
    class TimeoutNode(BaseNode):
        def __init__(self):
            super().__init__(node_id="timeout_node", config={"timeout": 1.0})

        async def execute(self, context):
            raise TimeoutError("Request timeout")

    node = TimeoutNode()
    healing_system = SelfHealingSystem()

    # First timeout should trigger reconfiguration
    original_timeout = node.config["timeout"]

    result = await healing_system._strategy_reconfigure(
        node, node_context, TimeoutError("Request timeout")
    )

    # Timeout should be increased
    assert node.config["timeout"] == original_timeout * 2


@pytest.mark.asyncio
async def test_replace_data_strategy(healing_system, node_context):
    """Test data replacement healing strategy"""
    node = MockFailingNode("test_node")
    node.config["error_value"] = "safe_default"

    result = await healing_system._strategy_replace_data(
        node, node_context, ValueError("Bad data")
    )

    assert result is not None
    assert result.success
    assert result.metadata["healing"] == "replace_data"


@pytest.mark.asyncio
async def test_exponential_backoff(node_context):
    """Test exponential backoff in retry strategy"""
    healing_system = SelfHealingSystem(config={
        "max_retries": 3,
        "retry_delay": 0.1,
        "exponential_backoff": True
    })

    node = MockFailingNode("test_node", fail_count=2)

    start_time = datetime.now()

    await healing_system._strategy_retry(node, node_context)

    elapsed = (datetime.now() - start_time).total_seconds()

    # Should have delays: 0.1, 0.2 (exponential)
    # Total >= 0.3 seconds
    assert elapsed >= 0.3


@pytest.mark.asyncio
async def test_healing_action_recording(healing_system, node_context):
    """Test that healing actions are recorded"""
    node = MockFailingNode("test_node", fail_count=1)

    await healing_system.heal_node_failure(
        node, node_context, RuntimeError("Test")
    )

    assert len(healing_system.healing_actions) > 0
    action = healing_system.healing_actions[0]
    assert action.node_id == "test_node"
    assert action.strategy in HealingStrategy


@pytest.mark.asyncio
async def test_analyze_and_improve(node_context):
    """Test pattern analysis and improvement delegation"""
    mock_improver = MagicMock()
    mock_messagebus = MagicMock()
    mock_messagebus.publish = AsyncMock()

    healing_system = SelfHealingSystem(
        improver_agent=mock_improver,
        message_bus=mock_messagebus
    )

    # Create recurring pattern
    for _ in range(3):
        healing_system._record_failure_pattern(
            "test_node",
            RuntimeError("Recurring error"),
            node_context
        )

    await healing_system.analyze_and_improve()

    # Should have published analysis request
    assert mock_messagebus.publish.called


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
