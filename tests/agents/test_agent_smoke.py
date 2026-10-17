"""Smoke tests: each Pantheon agent answers a basic MessageBus Message without crashing.

No network or Redis is used (Redis connection attempts fall back to in-memory state).
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.agents.analyzer_agent import AnalyzerAgent
from src.agents.executor_agent import ExecutorAgent
from src.agents.improver_agent import ImproverAgent
from src.agents.learner import LearnerAgent
from src.agents.memory_agent import MemoryAgent
from src.agents.validator import ValidatorAgent
from src.core.message_bus import Message, MessageBus


def make_agent(cls, **kwargs):
    return cls("smoke", MessageBus(), MagicMock(), kwargs.pop("config", {}), **kwargs)


def msg(message_type, content=None):
    return Message(from_agent="tester", to_agent="smoke", message_type=message_type, content=content or {})


class TestValidator:
    @pytest.mark.asyncio
    async def test_safe_command_is_valid(self):
        res = await make_agent(ValidatorAgent).process_message(msg("validate_bash", {"command": "ls -la"}))
        assert res["valid"] is True

    @pytest.mark.asyncio
    async def test_dangerous_command_is_rejected(self):
        res = await make_agent(ValidatorAgent).process_message(msg("validate_bash", {"command": "rm -rf /"}))
        assert res["valid"] is False and res["issues"]

    @pytest.mark.asyncio
    async def test_check_safety_replies_to_coordinator(self):
        res = await make_agent(ValidatorAgent).process_message(msg("check_safety", {"content": "hello"}))
        assert res["type"] == "safety_result" and res["content"]["safe"] is True


class TestLearner:
    @pytest.mark.asyncio
    async def test_record_and_stats(self):
        agent = make_agent(LearnerAgent)
        res = await agent.process_message(msg("record_execution", {"task": "t", "success": True, "duration": 1.0}))
        assert res["status"] == "recorded" and res["history_size"] == 1
        stats = await agent.process_message(msg("get_stats"))
        assert "stats" in stats


class TestMemory:
    @pytest.mark.asyncio
    async def test_unknown_type_is_an_error_not_a_crash(self):
        res = await make_agent(MemoryAgent).process_message(msg("bogus"))
        assert res["status"] == "error"

    @pytest.mark.asyncio
    async def test_accepts_bus_message_and_validates_key(self):
        res = await make_agent(MemoryAgent).process_message(msg("store_state", {"data": {"a": 1}}))
        assert res == {"status": "error", "reason": "Missing key"}

    @pytest.mark.asyncio
    async def test_still_accepts_plain_dict(self):
        res = await make_agent(MemoryAgent).process_message({"type": "recall_state"})
        assert res == {"status": "error", "reason": "Missing key"}

    @pytest.mark.asyncio
    async def test_store_with_fake_redis(self):
        agent = make_agent(MemoryAgent)
        agent.redis_client = MagicMock()
        res = await agent.process_message(msg("store_state", {"key": "k", "data": {"a": 1}}))
        assert res == {"status": "success", "key": "k"}
        agent.redis_client.set.assert_called_once()


class TestAnalyzer:
    @pytest.mark.asyncio
    async def test_system_metrics(self):
        res = await make_agent(AnalyzerAgent).process_message(msg("get_system_metrics"))
        assert res["status"] == "success" and "cpu" in res["metrics"]

    @pytest.mark.asyncio
    async def test_health_without_metrics(self):
        res = await make_agent(AnalyzerAgent).process_message(msg("get_health_status"))
        assert res["status"] == "success" and "health" in res


class TestImprover:
    @pytest.mark.asyncio
    async def test_stats_with_empty_config(self):
        res = await make_agent(ImproverAgent).process_message(msg("get_improvement_stats"))
        assert res["status"] == "success"

    @pytest.mark.asyncio
    async def test_apply_improvements_with_empty_config(self):
        res = await make_agent(ImproverAgent).process_message(
            msg("apply_improvements", {"task": "t", "recommendations": ["increase ocr threshold"]})
        )
        assert res["status"] in ("success", "skipped")

    @pytest.mark.asyncio
    async def test_requires_task_and_recommendations(self):
        res = await make_agent(ImproverAgent).process_message(msg("apply_improvements", {}))
        assert res["status"] == "error"


class TestExecutor:
    @pytest.mark.asyncio
    async def test_empty_workflow_is_an_error(self):
        res = await make_agent(ExecutorAgent).process_message(msg("execute_workflow", {"steps": []}))
        assert res["status"] == "error"

    @pytest.mark.asyncio
    async def test_execute_step_uses_action_executor_execute_async(self):
        action_executor = MagicMock()
        action_executor.execute_async = AsyncMock(return_value={"status": "success"})
        agent = make_agent(ExecutorAgent, action_executor=action_executor)

        res = await agent._execute_single_step(
            "wf", {"type": "execute", "params": {"action": {"type": "bash", "command": "echo hi"}}}, {}
        )
        assert res == {"status": "success"}
        action_executor.execute_async.assert_awaited_once_with("smoke", {"type": "bash", "command": "echo hi"})

    @pytest.mark.asyncio
    async def test_workflow_runs_to_completion(self):
        action_executor = MagicMock()
        action_executor.execute_async = AsyncMock(return_value={"status": "success"})
        agent = make_agent(ExecutorAgent, action_executor=action_executor, config={"timeout_per_step": 5})

        res = await agent.process_message(
            msg(
                "execute_workflow",
                {
                    "workflow_id": "wf1",
                    "steps": [{"id": "s1", "type": "execute", "params": {"action": {"type": "bash", "command": "ls"}}}],
                },
            )
        )
        assert res == {"status": "started", "workflow_id": "wf1"}
        for _ in range(50):
            if agent.workflow_history:
                break
            await asyncio.sleep(0.05)
        assert agent.workflow_history[0]["final_result"]["results"]["s1"] == {"status": "success"}

    @pytest.mark.asyncio
    async def test_delegate_step_sends_a_valid_message(self):
        agent = make_agent(ExecutorAgent)
        agent.message_bus.register_agent("actor")
        res = await agent._execute_single_step(
            "wf", {"type": "delegate", "params": {"agent": "actor", "message": {"type": "act_task", "task": "x"}}}, {}
        )
        assert res["status"] == "completed"
        delivered = await agent.message_bus.receive("actor", timeout=1)
        assert delivered.message_type == "act_task" and delivered.content == {"task": "x"}

    @pytest.mark.asyncio
    async def test_rollback_uses_flat_action_shape(self):
        action_executor = MagicMock()
        action_executor.execute_async = AsyncMock(return_value={"status": "success"})
        agent = make_agent(ExecutorAgent, action_executor=action_executor)
        agent._record_rollback_action("wf", {"type": "bash", "command": "mkdir build"})

        res = await agent.rollback_workflow("wf")
        assert res["status"] == "completed"
        action_executor.execute_async.assert_awaited_once_with("smoke", {"type": "bash", "command": "rmdir build"})
