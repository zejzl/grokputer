"""
Tests for the workflow self-healing system (WorkflowHealer).

Magic healing is disabled in every healer here so strategy selection is deterministic.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.workflow.engine import WorkflowEngine
from src.workflow.healing import HealingAction, HealingStrategy, WorkflowHealer, with_healing
from src.workflow.nodes.base import BaseNode, NodeContext, NodeStatus


class FlakyNode(BaseNode):
    """Fails the first `fail_count` runs, then succeeds."""

    def __init__(self, node_id: str, fail_count: int = 1, error_type=RuntimeError, config=None):
        super().__init__(node_id=node_id, config=config)
        self.fail_count = fail_count
        self.error_type = error_type
        self.attempts = 0

    async def execute(self, context: NodeContext) -> NodeContext:
        self.attempts += 1
        if self.attempts <= self.fail_count:
            raise self.error_type(f"flaky failure {self.attempts}")
        context.set("healed_by", self.node_id)
        return context


class OkNode(BaseNode):
    async def execute(self, context: NodeContext) -> NodeContext:
        context.set("fallback_ran", True)
        return context


@pytest.fixture
def healer():
    return WorkflowHealer(max_healing_attempts=3, retry_delay=0.001, enable_magic_healing=False)


@pytest.fixture
def context():
    return NodeContext(data={"x": 1})


class TestRetry:
    @pytest.mark.asyncio
    async def test_retry_succeeds_after_transient_failures(self, healer, context):
        node = FlakyNode("n1", fail_count=2)
        error = RuntimeError("boom")

        result = await healer.heal_node(node, context, error, HealingStrategy.RETRY)

        assert result.get("healed_by") == "n1"
        assert node.attempts == 3
        assert node.status == NodeStatus.SUCCESS
        assert healer.healing_actions[-1].success is True

    @pytest.mark.asyncio
    async def test_retry_exhausted_raises_and_records_failure(self, healer, context):
        node = FlakyNode("n1", fail_count=99)

        with pytest.raises(RuntimeError, match="flaky failure"):
            await healer.heal_node(node, context, RuntimeError("boom"), HealingStrategy.RETRY)

        assert node.attempts == healer.max_healing_attempts
        action = healer.healing_actions[-1]
        assert action.success is False
        assert "flaky failure" in action.error

    @pytest.mark.asyncio
    async def test_backoff_delay_grows(self, context, monkeypatch):
        sleeps = []

        async def fake_sleep(delay):
            sleeps.append(delay)

        monkeypatch.setattr("src.workflow.healing.asyncio.sleep", fake_sleep)
        healer = WorkflowHealer(
            max_healing_attempts=4, retry_delay=1.0, backoff_multiplier=2.0, enable_magic_healing=False
        )

        with pytest.raises(RuntimeError):
            await healer.heal_node(FlakyNode("n1", fail_count=99), context, RuntimeError(), HealingStrategy.RETRY)

        assert sleeps == [1.0, 2.0, 4.0]


class TestSkipAndReplace:
    @pytest.mark.asyncio
    async def test_skip_marks_node_and_state(self, healer, context):
        node = FlakyNode("n1", fail_count=99)
        node.error = "original failure"

        result = await healer.heal_node(node, context, RuntimeError("boom"), HealingStrategy.SKIP)

        assert node.status == NodeStatus.SKIPPED
        assert result.get_state("n1_skipped") is True
        assert result.get_state("n1_skip_reason") == "original failure"

    @pytest.mark.asyncio
    async def test_replace_runs_registered_fallback(self, healer, context):
        node = FlakyNode("n1", fail_count=99)
        healer.register_fallback("n1", OkNode("fallback"))

        result = await healer.heal_node(node, context, RuntimeError("boom"), HealingStrategy.REPLACE)

        assert result.get("fallback_ran") is True
        assert result.get_state("n1_used_fallback") is True

    @pytest.mark.asyncio
    async def test_replace_without_fallback_raises(self, healer, context):
        with pytest.raises(ValueError, match="No fallback registered"):
            await healer.heal_node(FlakyNode("n1"), context, RuntimeError("boom"), HealingStrategy.REPLACE)
        assert healer.healing_actions[-1].success is False


class TestStrategySelection:
    @pytest.mark.parametrize("error", [TimeoutError("slow"), ConnectionError("down")])
    def test_transient_errors_retry(self, healer, error):
        assert healer._select_strategy(FlakyNode("n1"), error) == HealingStrategy.RETRY

    def test_fallback_used_when_registered(self, healer):
        healer.register_fallback("n1", OkNode("fallback"))
        assert healer._select_strategy(FlakyNode("n1"), ValueError("bad")) == HealingStrategy.REPLACE

    def test_improver_used_when_pantheon_available(self):
        healer = WorkflowHealer(pantheon_integration=MagicMock(), enable_magic_healing=False)
        assert healer._select_strategy(FlakyNode("n1"), ValueError("bad")) == HealingStrategy.INVOKE_IMPROVER

    def test_default_is_retry(self, healer):
        assert healer._select_strategy(FlakyNode("n1"), ValueError("bad")) == HealingStrategy.RETRY

    def test_transient_error_beats_registered_fallback(self, healer):
        healer.register_fallback("n1", OkNode("fallback"))
        assert healer._select_strategy(FlakyNode("n1"), TimeoutError()) == HealingStrategy.RETRY

    @pytest.mark.asyncio
    async def test_strategy_auto_selected_when_none_given(self, healer, context):
        node = FlakyNode("n1", fail_count=1)

        await healer.heal_node(node, context, ConnectionError("down"))

        assert healer.healing_actions[-1].strategy == HealingStrategy.RETRY


class TestImprover:
    @pytest.mark.asyncio
    async def test_fixed_config_is_applied_then_node_retried(self, context):
        pantheon = MagicMock()
        pantheon.invoke_agent = AsyncMock(return_value={"fixed_config": {"max_retries": 5}})
        healer = WorkflowHealer(pantheon_integration=pantheon, enable_magic_healing=False)
        node = FlakyNode("n1", fail_count=1)
        node.attempts = 1  # the node already failed once before healing was requested

        result = await healer.heal_node(node, context, RuntimeError("boom"), HealingStrategy.INVOKE_IMPROVER)

        assert node.get_config("max_retries") == 5
        assert result.get_state("n1_improver_fixed") is True
        pantheon.invoke_agent.assert_awaited_once()
        assert pantheon.invoke_agent.await_args.args[0] == "improver"

    @pytest.mark.asyncio
    async def test_alternative_approach_skips_node(self, context):
        pantheon = MagicMock()
        pantheon.invoke_agent = AsyncMock(return_value={"alternative_approach": "use cache"})
        healer = WorkflowHealer(pantheon_integration=pantheon, enable_magic_healing=False)
        node = FlakyNode("n1", fail_count=99)

        await healer.heal_node(node, context, RuntimeError("boom"), HealingStrategy.INVOKE_IMPROVER)

        assert node.status == NodeStatus.SKIPPED

    @pytest.mark.asyncio
    async def test_unactionable_response_raises(self, context):
        pantheon = MagicMock()
        pantheon.invoke_agent = AsyncMock(return_value={})
        healer = WorkflowHealer(pantheon_integration=pantheon, enable_magic_healing=False)

        with pytest.raises(Exception, match="actionable"):
            await healer.heal_node(
                FlakyNode("n1"), context, RuntimeError("boom"), HealingStrategy.INVOKE_IMPROVER
            )

    @pytest.mark.asyncio
    async def test_improver_without_pantheon_raises(self, healer, context):
        with pytest.raises(ValueError, match="Pantheon integration not available"):
            await healer.heal_node(
                FlakyNode("n1"), context, RuntimeError("boom"), HealingStrategy.INVOKE_IMPROVER
            )

    @pytest.mark.asyncio
    async def test_magic_heal_unavailable_raises(self, healer, context):
        with pytest.raises(ValueError, match="Magic healer not available"):
            await healer.heal_node(FlakyNode("n1"), context, RuntimeError("boom"), HealingStrategy.MAGIC_HEAL)


class TestStats:
    def test_empty_stats(self, healer):
        stats = healer.get_healing_stats()
        assert stats["total_healing_attempts"] == 0
        assert stats["success_rate"] == 0.0
        assert stats["magic_healing"] is None

    @pytest.mark.asyncio
    async def test_stats_count_successes_and_failures(self, healer, context):
        await healer.heal_node(FlakyNode("a", fail_count=0), context, RuntimeError(), HealingStrategy.RETRY)
        await healer.heal_node(FlakyNode("b"), context, RuntimeError(), HealingStrategy.SKIP)
        with pytest.raises(ValueError):
            await healer.heal_node(FlakyNode("c"), context, RuntimeError(), HealingStrategy.REPLACE)

        stats = healer.get_healing_stats()

        assert stats["total_healing_attempts"] == 3
        assert stats["successful_healings"] == 2
        assert stats["success_rate"] == pytest.approx(2 / 3)
        assert stats["strategy_usage"] == {"retry": 1, "skip": 1, "replace": 1}

    def test_healing_action_defaults(self):
        action = HealingAction(node_id="n", strategy=HealingStrategy.RETRY, attempts=0, success=False)
        assert action.error is None
        assert action.recovery_time == 0.0


class TestWithHealing:
    @pytest.mark.asyncio
    async def test_workflow_recovers_from_transient_node_failure(self, healer):
        engine = WorkflowEngine("heal_test")
        node = FlakyNode("flaky", fail_count=1)
        engine.add_node(node)

        result = await with_healing(engine, healer, {"x": 1})

        assert result["healed_by"] == "flaky"
        assert healer.healing_actions and healer.healing_actions[0].node_id == "flaky"

    @pytest.mark.asyncio
    async def test_unhealable_workflow_still_raises(self, healer):
        engine = WorkflowEngine("heal_fail_test")
        engine.add_node(FlakyNode("broken", fail_count=99))

        with pytest.raises(RuntimeError, match="flaky failure"):
            await with_healing(engine, healer)
