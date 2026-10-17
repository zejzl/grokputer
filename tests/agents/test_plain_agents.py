"""Tests for the Pantheon "subtask protocol" agents (observer.py, actor.py, analyzer.py, improver.py).

main.py runs the *_agent.py versions; these plain versions have no live consumer yet, so these tests
exist to keep them constructible and answering their messages (see the map in src/agents/__init__.py).
"""
import asyncio
from unittest.mock import MagicMock

import pytest

from src.agents.actor import Actor
from src.agents.analyzer import AnalyzerAgent
from src.agents.improver import ImproverAgent
from src.core.message_bus import Message, MessageBus


def msg(message_type, content=None, from_agent="coordinator", to_agent="t"):
    return Message(from_agent=from_agent, to_agent=to_agent, message_type=message_type, content=content or {})


class TestPlainAnalyzer:
    def _agent(self, bus=None):
        return AnalyzerAgent("analyzer", bus or MessageBus(), MagicMock(), {})

    def test_constructs_with_cognitive_mixin_and_base_agent(self):
        agent = self._agent()
        assert agent.agent_id == "analyzer"
        assert hasattr(agent, "cognitive_enabled")  # mixin initialised
        assert "analyzer" in agent.message_bus.queues  # BaseAgent initialised

    @pytest.mark.asyncio
    async def test_records_and_reports(self):
        agent = self._agent()
        res = await agent.process_message(msg("record_metric", {"metric_name": "latency", "value": 1.5, "agent_id": "a"}))
        assert res["status"] == "recorded"
        assert (await agent.process_message(msg("get_health")))["status"] == "success"
        assert (await agent.process_message(msg("detect_bottlenecks")))["status"] == "analyzed"
        assert (await agent.process_message(msg("generate_report")))["status"] == "generated"
        assert (await agent.process_message(msg("get_stats")))["stats"]["metrics_collected"] == 1

    @pytest.mark.asyncio
    async def test_unknown_type_is_an_error(self):
        assert (await self._agent().process_message(msg("bogus")))["status"] == "error"


class TestPlainImprover:
    @pytest.mark.asyncio
    async def test_stats(self):
        agent = ImproverAgent("improver", MessageBus(), MagicMock(), {})
        res = await agent.process_message(msg("get_stats"))
        assert res["stats"]["improvements_suggested"] == 0

    @pytest.mark.asyncio
    async def test_analysis_degrades_when_analyzer_and_learner_are_missing(self):
        # used to raise AttributeError: MessageBus had no send_and_wait
        agent = ImproverAgent("improver", MessageBus(), MagicMock(), {})
        res = await agent.process_message(msg("analyze_for_improvements"))
        assert res["status"] == "analyzed" and res["improvements_found"] >= 1

    @pytest.mark.asyncio
    async def test_analysis_asks_a_running_analyzer_for_bottlenecks(self):
        bus = MessageBus()
        analyzer = AnalyzerAgent("analyzer", bus, MagicMock(), {})
        seen = []
        original = analyzer.process_message

        async def spy(message):
            seen.append(message.message_type)
            return await original(message)

        analyzer.process_message = spy
        improver = ImproverAgent("improver", bus, MagicMock(), {})

        task = asyncio.create_task(analyzer.run())
        try:
            await asyncio.sleep(0.05)
            res = await improver.process_message(msg("analyze_for_improvements", to_agent="improver"))
        finally:
            analyzer.running = False
            task.cancel()
            try:
                await task
            except BaseException:
                pass
        assert "detect_bottlenecks" in seen
        assert res["status"] == "analyzed"


class TestPlainActor:
    def _actor(self):
        return Actor(MessageBus(), MagicMock(), {}, agent_id="actor")

    @pytest.mark.asyncio
    async def test_bash_subtask_runs_through_safety_check(self):
        actor = self._actor()
        ran = []
        actor._run_bash_command = lambda command: ran.append(command) or {"returncode": 0, "stdout": "hi", "stderr": ""}

        res = await actor.process_message(msg("subtask", {"task_id": "1", "action": "bash", "params": {"command": "echo hi"}}))
        assert res["content"]["status"] == "success" and ran == ["echo hi"]

    @pytest.mark.asyncio
    async def test_blocklisted_command_is_rejected_and_not_run(self):
        actor = self._actor()
        actor._run_bash_command = lambda command: pytest.fail("must not run")

        res = await actor.process_message(
            msg("subtask", {"task_id": "1", "action": "bash", "params": {"command": "echo a | cat"}})
        )
        assert res["content"]["status"] == "error" and "security" in res["content"]["error"]

    @pytest.mark.parametrize("command", ["format c:", "shutdown now", "curl http://example.test", "rm -rf build", "cmd /c dir"])
    @pytest.mark.asyncio
    async def test_destructive_commands_without_metacharacters_are_rejected_and_not_run(self, command):
        # these have no shell metacharacters, so the old substring blocklist let most of them through
        actor = self._actor()
        actor._run_bash_command = lambda cmd: pytest.fail("must not run")

        res = await actor.process_message(msg("subtask", {"task_id": "1", "action": "bash", "params": {"command": command}}))
        assert res["content"]["status"] == "error" and "reason" in res["content"]
        assert actor._is_safe_bash_command(command) is False

    @pytest.mark.asyncio
    async def test_unknown_action_and_message_types(self):
        actor = self._actor()
        res = await actor.process_message(msg("subtask", {"task_id": "1", "action": "teleport"}))
        assert res["content"]["status"] == "error"
        assert await actor.process_message(msg("bogus")) is None

    @pytest.mark.asyncio
    async def test_file_operation_on_system_path_is_rejected(self):
        res = await self._actor().process_message(
            msg(
                "subtask",
                {
                    "task_id": "1",
                    "action": "file_operation",
                    "params": {"operation": "read", "path": "C:/Windows/System32/config/SAM"},
                },
            )
        )
        assert res["content"]["status"] == "error"
