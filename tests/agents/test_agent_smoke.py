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


async def _roundtrip(agent, message_type, content):
    """Run the agent's real run() loop on its bus and return the reply sent to 'coordinator'."""
    bus = agent.message_bus
    bus.register_agent("coordinator")
    task = asyncio.create_task(agent.run())
    try:
        await asyncio.sleep(0.05)
        await bus.send(
            Message(
                from_agent="coordinator",
                to_agent=agent.agent_id,
                message_type=message_type,
                content=content,
                correlation_id="corr-1",
            )
        )
        return await asyncio.wait_for(bus.receive("coordinator", timeout=5), 6)
    finally:
        agent.running = False
        task.cancel()
        try:
            await task
        except BaseException:
            pass


class TestRunLoop:
    """process_message through BaseAgent.run(): reply is delivered and keeps the request's correlation_id."""

    @pytest.mark.parametrize(
        "cls, message_type, content",
        [
            (ValidatorAgent, "validate_bash", {"command": "ls"}),
            (LearnerAgent, "get_stats", {}),
            (MemoryAgent, "recall_state", {}),
            (AnalyzerAgent, "get_system_metrics", {}),
            (ImproverAgent, "get_improvement_stats", {}),
            (ExecutorAgent, "execute_workflow", {"steps": []}),
        ],
    )
    @pytest.mark.asyncio
    async def test_reply_keeps_correlation_id(self, cls, message_type, content):
        reply = await _roundtrip(make_agent(cls), message_type, content)
        assert reply.from_agent == "smoke"
        assert reply.correlation_id == "corr-1"


class TestActorAgent:
    def _actor(self, executor):
        from src.agents.actor_agent import ActorAgent

        return ActorAgent(
            agent_id="actor", message_bus=MessageBus(), action_executor=executor, session_logger=MagicMock()
        )

    @pytest.mark.asyncio
    async def test_result_reaches_coordinator(self):
        executor = MagicMock()
        executor.execute_bash = AsyncMock(return_value={"status": "success", "output": "hi"})
        actor = self._actor(executor)

        reply = await _roundtrip(actor, "act", {"type": "bash", "params": {"command": "echo hi"}})
        assert reply.message_type == "action_result"
        assert reply.content["result"] == {"status": "success", "output": "hi", "error": None}
        executor.execute_bash.assert_awaited_once_with("echo hi")

    @pytest.mark.asyncio
    async def test_click_and_type_use_execute_async(self):
        executor = MagicMock()
        executor.execute_async = AsyncMock(return_value={"status": "success"})
        actor = self._actor(executor)

        await actor._execute_action({"type": "pyautogui_click", "params": {"x": 3, "y": 4}})
        executor.execute_async.assert_awaited_with("actor", {"type": "click", "x": 3, "y": 4})
        await actor._execute_action({"type": "pyautogui_type", "params": {"text": "abc"}})
        executor.execute_async.assert_awaited_with("actor", {"type": "type", "text": "abc"})

    @pytest.mark.asyncio
    async def test_failed_action_escalates_to_validator(self):
        executor = MagicMock()
        executor.execute_bash = AsyncMock(side_effect=RuntimeError("boom"))
        actor = self._actor(executor)
        actor.config = {**actor.config, "max_retries": 0}
        actor.message_bus.register_agent("validator")

        task = asyncio.create_task(actor.run())
        try:
            await asyncio.sleep(0.05)
            await actor.message_bus.send(
                Message(
                    from_agent="coordinator",
                    to_agent="actor",
                    message_type="act",
                    content={"type": "bash", "params": {"command": "x"}},
                )
            )
            escalated = await actor.message_bus.receive("validator", timeout=5)
        finally:
            actor.running = False
            task.cancel()
            try:
                await task
            except BaseException:
                pass
        assert escalated.message_type == "action_failed" and "boom" in escalated.content["error"]
