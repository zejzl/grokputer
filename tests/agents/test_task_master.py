"""TaskMaster (task board) and BaseAgent's task client, end to end over a MessageBus. No LLM, no network."""
import asyncio
import time
from typing import Any, Dict, Optional
from unittest.mock import MagicMock

import pytest

from src.agents.task_master import TaskMaster, TaskPriority, TaskRegistry, TaskStatus
from src.core.base_agent import BaseAgent
from src.core.message_bus import Message, MessageBus
from src.observability.session_logger import SessionLogger


class Worker(BaseAgent):
    async def process_message(self, message: Message) -> Optional[Dict[str, Any]]:
        return None


def msg(message_type, content=None, from_agent="w1"):
    return Message(from_agent=from_agent, to_agent="taskmaster", message_type=message_type, content=content or {})


def make_master(bus=None, **config):
    return TaskMaster(bus or MessageBus(), MagicMock(), {"auto_delegate": False, **config})


async def run_in_background(agent):
    task = asyncio.create_task(agent.run())
    await asyncio.sleep(0.05)
    return task


async def stop(agent, task):
    agent.running = False
    task.cancel()
    try:
        await task
    except BaseException:
        pass


class TestRegistry:
    def test_dependencies_gate_availability(self):
        reg = TaskRegistry()
        first = reg.create_task("first", "")
        second = reg.create_task("second", "", dependencies=[first.task_id])

        assert [t.task_id for t in reg.get_available_tasks("w1", 5)] == [first.task_id]
        reg.assign_task(first.task_id, "w1")
        reg.update_task_status(first.task_id, TaskStatus.COMPLETED, "w1")
        assert second.task_id in [t.task_id for t in reg.get_available_tasks("w1", 5)]

    def test_priority_order_and_stats(self):
        reg = TaskRegistry()
        low = reg.create_task("low", "", priority=TaskPriority.LOW)
        high = reg.create_task("high", "", priority=TaskPriority.CRITICAL)
        assert reg.get_available_tasks("w1", 1)[0].task_id == high.task_id
        assert reg.get_system_stats()["total_tasks"] == 2
        assert reg.get_task(low.task_id).title == "low"


class TestHandlers:
    @pytest.mark.asyncio
    async def test_create_request_and_complete(self):
        bus = MessageBus()
        master = make_master(bus)
        bus.register_agent("w1")

        created = await master.process_message(msg("create_task", {"title": "T", "priority": "high"}))
        assert created["status"] == "created"

        assigned = await master.process_message(msg("task_request"))
        assert assigned["status"] == "assigned" and assigned["task"]["task_id"] == created["task"]["task_id"]
        # the reply carries the task, so it is not pushed a second time
        with pytest.raises(asyncio.TimeoutError):
            await bus.receive("w1", timeout=0.05)

        done = await master.process_message(
            msg("task_status_update", {"task_id": assigned["task_id"], "status": "completed", "notes": "ok"})
        )
        assert done == {"status": "updated", "task_id": assigned["task_id"], "new_status": "completed"}
        master.session_logger.log_task_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_tasks_busy_and_validation(self):
        bus = MessageBus()
        master = make_master(bus, max_agent_tasks=1)
        bus.register_agent("w1")

        assert (await master.process_message(msg("task_request")))["status"] == "no_tasks"
        await master.process_message(msg("create_task", {"title": "A"}))
        await master.process_message(msg("create_task", {"title": "B"}))
        assert (await master.process_message(msg("task_request")))["status"] == "assigned"
        assert (await master.process_message(msg("task_request")))["status"] == "busy"

        assert (await master.process_message(msg("task_status_update", {})))["status"] == "error"
        bad = await master.process_message(msg("task_status_update", {"task_id": "x", "status": "nonsense"}))
        assert bad["status"] == "error" and "Invalid status" in bad["message"]
        assert (await master.process_message(msg("bogus")))["status"] == "unknown_message_type"

    @pytest.mark.asyncio
    async def test_heartbeat_capabilities_and_stats(self):
        master = make_master()
        assert (await master.process_message(msg("agent_capabilities", {"capabilities": ["a"]})))["status"] == "capabilities_updated"
        assert master.agent_capabilities["w1"] == ["a"]
        assert (await master.process_message(msg("agent_heartbeat")))["status"] == "heartbeat_ack"
        assert (await master.process_message(msg("get_system_stats")))["status"] == "stats"
        assert master.get_system_status()["registered_agents"] == ["w1"]

    @pytest.mark.asyncio
    async def test_auto_delegation_on_create_picks_least_loaded_active_agent(self):
        bus = MessageBus()
        master = make_master(bus, auto_delegate=True)
        bus.register_agent("w1")
        bus.register_agent("w2")
        for agent_id in ("w1", "w2"):
            await master.process_message(msg("agent_capabilities", {"capabilities": ["x"]}, from_agent=agent_id))
            await master.process_message(msg("agent_heartbeat", from_agent=agent_id))
        await master.process_message(msg("create_task", {"title": "first"}))  # goes to w1 or w2
        await master.process_message(msg("create_task", {"title": "second"}))  # must go to the other one

        owners = {t.assigned_agent for t in master.task_registry.get_all_tasks()}
        assert owners == {"w1", "w2"}

    @pytest.mark.asyncio
    async def test_stale_agent_tasks_are_returned_to_pending(self):
        bus = MessageBus()
        bus.register_agent("w1")
        master = make_master(bus, heartbeat_timeout=1)
        await master.process_message(msg("create_task", {"title": "T"}))
        bus_msg = await master.process_message(msg("task_request"))
        assert bus_msg["status"] == "assigned"

        master.last_heartbeat["w1"] = time.time() - 60
        await master._check_stale_agents()
        task = master.task_registry.get_all_tasks()[0]
        assert task.status == TaskStatus.PENDING and task.assigned_agent is None


class TestTaskClientRoundTrip:
    """BaseAgent's task client talking to a running TaskMaster over the bus."""

    @pytest.mark.asyncio
    async def test_register_create_request_update(self):
        bus = MessageBus()
        master = make_master(bus)
        worker = Worker("w1", bus, MagicMock(), {})
        worker.enable_task_client(["writing"])
        master_task = await run_in_background(master)
        try:
            await worker.register_capabilities()
            assert master.agent_capabilities["w1"] == ["writing"]

            task_id = await worker.create_task("Write a haiku", "five seven five", priority="high", tags=["writing"])
            assert task_id and master.task_registry.get_task(task_id).title == "Write a haiku"

            task = await worker.request_task()
            assert task["task_id"] == task_id and worker.current_tasks[task_id] is task
            assert master.task_registry.get_task(task_id).assigned_agent == "w1"

            await worker.update_task_status(task_id, "completed", "done")
            assert master.task_registry.get_task(task_id).status == TaskStatus.COMPLETED
            assert task_id not in worker.current_tasks

            assert await worker.get_available_tasks() == []
        finally:
            await stop(master, master_task)

    @pytest.mark.asyncio
    async def test_client_methods_return_none_without_a_taskmaster(self):
        worker = Worker("w1", MessageBus(), MagicMock(), {})
        worker.enable_task_client(["x"])
        assert await worker.create_task("t", "d") is None
        assert await worker.request_task() is None
        assert await worker.get_available_tasks() == []

    @pytest.mark.asyncio
    async def test_client_times_out_instead_of_hanging_when_taskmaster_is_not_running(self):
        bus = MessageBus()
        make_master(bus)  # registered, but its run loop never starts
        worker = Worker("w1", bus, MagicMock(), {"task_request_timeout": 0.2})
        worker.enable_task_client(["x"])
        started = time.monotonic()
        assert await worker.request_task() is None
        assert time.monotonic() - started < 2

    @pytest.mark.asyncio
    async def test_assigned_task_is_processed_by_the_agent(self):
        bus = MessageBus()
        master = make_master(bus)
        worker = Worker("w1", bus, MagicMock(), {})
        worker.enable_task_client(["x"])
        master_task = await run_in_background(master)
        try:
            task_id = await worker.create_task("t", "d")
            task = await worker.request_task()
            seen = []
            original = worker.process_message

            async def spy(message):
                seen.append(message.message_type)
                return {"status": "success"}

            worker.process_message = spy
            await worker._process_assigned_task(task)
            assert seen == ["task_execution"]
            assert master.task_registry.get_task(task_id).status == TaskStatus.COMPLETED
        finally:
            await stop(master, master_task)


def test_session_logger_has_log_task_update():
    assert callable(SessionLogger.log_task_update)


@pytest.mark.asyncio
async def test_auto_delegation_waits_for_dependencies():
    bus = MessageBus()
    master = make_master(bus, auto_delegate=True)
    bus.register_agent("w1")
    await master.process_message(msg("agent_capabilities", {"capabilities": ["x"]}))
    await master.process_message(msg("agent_heartbeat"))

    blocker = (await master.process_message(msg("create_task", {"title": "blocker"})))["task"]["task_id"]
    # `blocker` was auto-delegated to w1; the dependent task must stay pending until it completes
    dependent = (await master.process_message(msg("create_task", {"title": "dependent", "dependencies": [blocker]})))["task"]
    assert master.task_registry.get_task(dependent["task_id"]).status == TaskStatus.PENDING


class TestStandaloneTaskClient:
    """src/core/task_client.TaskClient: used by agents that are not BaseAgents (see demo_task_management.py)."""

    @pytest.mark.asyncio
    async def test_pull_flow_request_update_stats(self):
        from src.core.task_client import TaskClient

        bus = MessageBus()
        master = make_master(bus)
        master_task = await run_in_background(master)
        try:
            client = TaskClient("alpha", bus)
            assert (await client.register_capabilities(["coding"]))["status"] == "capabilities_updated"
            created = await client.create_task("Fix bug", "details", priority="high")
            assert created["status"] == "created"

            task = await client.request_task()
            assert task["task_id"] == created["task"]["task_id"] and client.get_current_tasks() == [task]

            assert (await client.update_task_status(task["task_id"], "completed"))["status"] == "updated"
            assert client.get_current_tasks() == []
            assert (await client.get_system_stats())["status_counts"]["completed"] == 1
            assert await client.get_available_tasks() == []
        finally:
            await stop(master, master_task)

    @pytest.mark.asyncio
    async def test_auto_delegated_tasks_are_pushed_to_the_clients_inbox(self):
        from src.core.task_client import TaskClient

        bus = MessageBus()
        master = make_master(bus, auto_delegate=True)
        master_task = await run_in_background(master)
        try:
            client = TaskClient("alpha", bus)
            await client.register_capabilities(["coding"])
            await client.send_heartbeat()  # auto-delegation only considers agents with a recent heartbeat

            await client.create_task("Pushed", "d")
            assert await client.poll_assignments() == 1
            (task,) = client.get_current_tasks()
            assert task["title"] == "Pushed" and task["assigned_agent"] == "alpha"
        finally:
            await stop(master, master_task)

    @pytest.mark.asyncio
    async def test_returns_none_style_results_when_taskmaster_is_absent(self):
        from src.core.task_client import TaskClient

        client = TaskClient("alpha", MessageBus())
        assert await client.request_task() is None
        assert await client.get_available_tasks() == []
        assert await client.get_system_stats() is None


@pytest.mark.asyncio
async def test_assignment_to_an_agent_without_an_inbox_is_not_an_error():
    bus = MessageBus()  # "ghost" is never registered
    master = make_master(bus, auto_delegate=True)
    await master.process_message(msg("agent_capabilities", {"capabilities": ["x"]}, from_agent="ghost"))
    await master.process_message(msg("agent_heartbeat", from_agent="ghost"))

    created = await master.process_message(msg("create_task", {"title": "T"}, from_agent="demo"))
    assert created["status"] == "created"
    assert master.task_registry.get_task(created["task"]["task_id"]).assigned_agent == "ghost"


@pytest.mark.asyncio
async def test_a_task_is_delivered_to_the_client_exactly_once():
    from src.core.task_client import TaskClient

    bus = MessageBus()
    master = make_master(bus, auto_delegate=True)
    master_task = await run_in_background(master)
    try:
        client = TaskClient("alpha", bus)
        await client.register_capabilities(["x"])
        await client.send_heartbeat()
        await client.create_task("Only once", "d")  # auto-delegated: pushed
        assert await client.poll_assignments() == 1
        (task,) = client.get_current_tasks()

        await client.update_task_status(task["task_id"], "completed")
        # a stale duplicate push for the finished task must not bring it back
        await bus.send(
            Message(
                from_agent="taskmaster", to_agent="alpha", message_type="task_assigned", content={"task": task}
            )
        )
        assert await client.poll_assignments() == 0 and client.get_current_tasks() == []
    finally:
        await stop(master, master_task)


class TestBaseAgentTaskLoop:
    def test_check_interval_is_configurable(self):
        assert Worker("w1", MessageBus(), MagicMock(), {}).task_check_interval == 30.0
        assert Worker("w2", MessageBus(), MagicMock(), {"task_check_interval": 2}).task_check_interval == 2.0

    @pytest.mark.asyncio
    async def test_reply_message_counts_as_a_completed_task(self):
        bus = MessageBus()
        master = make_master(bus)
        worker = Worker("w1", bus, MagicMock(), {})
        worker.enable_task_client(["x"])

        async def answer(message):
            return Message(from_agent="w1", to_agent="taskmaster", message_type="answer", content={})

        worker.process_message = answer
        master_task = await run_in_background(master)
        try:
            task_id = await worker.create_task("t", "d")
            task = await worker.request_task()
            await worker._process_assigned_task(task)
            assert master.task_registry.get_task(task_id).status == TaskStatus.COMPLETED
        finally:
            await stop(master, master_task)


class TestCapabilityMatching:
    """required_capabilities is a hard filter; tag/capability overlap (affinity) is only a tie-breaker."""

    def test_can_take_rules(self):
        reg = TaskRegistry()
        anyone = reg.create_task("anyone", "")
        needs_both = reg.create_task("needs both", "", required_capabilities=["Writing", "editing"])

        assert reg.can_take(anyone, None) and reg.can_take(anyone, []) and reg.can_take(anyone, ["x"])
        assert not reg.can_take(needs_both, None)
        assert not reg.can_take(needs_both, ["writing"])  # all required capabilities, not any
        assert reg.can_take(needs_both, [" WRITING ", "Editing", "extra"])  # case/whitespace-insensitive

    def test_available_tasks_are_filtered_by_capability(self):
        reg = TaskRegistry()
        open_task = reg.create_task("open", "")
        story = reg.create_task("story", "", required_capabilities=["story"])
        reg.create_task("code", "", required_capabilities=["code"])

        ids = lambda caps: {t.task_id for t in reg.get_available_tasks("a", 10, caps)}  # noqa: E731
        assert ids(None) == {open_task.task_id}
        assert ids(["story"]) == {open_task.task_id, story.task_id}
        assert len(ids(["story", "code"])) == 3

    def test_affinity_breaks_ties_but_priority_still_wins(self):
        reg = TaskRegistry()
        plain = reg.create_task("plain", "", priority=TaskPriority.MEDIUM, tags=["other"])
        match = reg.create_task("match", "", priority=TaskPriority.MEDIUM, tags=["story"])
        urgent = reg.create_task("urgent", "", priority=TaskPriority.CRITICAL, tags=["other"])

        order = [t.task_id for t in reg.get_available_tasks("a", 3, ["story"])]
        assert order == [urgent.task_id, match.task_id, plain.task_id]

    def test_task_roundtrips_required_capabilities(self):
        from src.agents.task_master import Task

        task = TaskRegistry().create_task("t", "d", required_capabilities=["a", "b"])
        assert Task.from_dict(task.to_dict()).required_capabilities == ["a", "b"]

    @pytest.mark.asyncio
    async def test_task_request_only_offers_tasks_the_agent_can_take(self):
        bus = MessageBus()
        master = make_master(bus)
        await master.process_message(msg("create_task", {"title": "Story", "required_capabilities": ["story"]}))
        await master.process_message(msg("agent_capabilities", {"capabilities": ["code"]}, from_agent="coder"))
        await master.process_message(msg("agent_capabilities", {"capabilities": ["story"]}, from_agent="writer"))

        assert (await master.process_message(msg("task_request", from_agent="coder")))["status"] == "no_tasks"
        assert (await master.process_message(msg("task_request", from_agent="stranger")))["status"] == "no_tasks"
        listing = await master.process_message(msg("get_available_tasks", from_agent="coder"))
        assert listing["tasks"] == []
        assert (await master.process_message(msg("task_request", from_agent="writer")))["status"] == "assigned"

    @pytest.mark.asyncio
    async def test_auto_delegation_goes_to_the_capable_agent_even_if_another_is_idler(self):
        bus = MessageBus()
        master = make_master(bus, auto_delegate=True)
        for agent_id, caps in (("coder", ["code"]), ("writer", ["story"])):
            await master.process_message(msg("agent_capabilities", {"capabilities": caps}, from_agent=agent_id))
            await master.process_message(msg("agent_heartbeat", from_agent=agent_id))
        # give the writer work so the coder is the less loaded agent
        await master.process_message(msg("create_task", {"title": "busy", "required_capabilities": ["story"]}))

        created = await master.process_message(msg("create_task", {"title": "S2", "required_capabilities": ["story"]}))
        assert master.task_registry.get_task(created["task"]["task_id"]).assigned_agent == "writer"

    @pytest.mark.asyncio
    async def test_auto_delegation_prefers_the_better_tag_match_at_equal_load(self):
        master = make_master(auto_delegate=True)
        for agent_id, caps in (("a", ["code"]), ("b", ["story"])):
            await master.process_message(msg("agent_capabilities", {"capabilities": caps}, from_agent=agent_id))
            await master.process_message(msg("agent_heartbeat", from_agent=agent_id))

        created = await master.process_message(msg("create_task", {"title": "S", "tags": ["story"]}))
        assert master.task_registry.get_task(created["task"]["task_id"]).assigned_agent == "b"

    @pytest.mark.asyncio
    async def test_task_nobody_can_take_waits_and_is_reported(self):
        bus = MessageBus()
        master = make_master(bus, auto_delegate=True)
        await master.process_message(msg("agent_capabilities", {"capabilities": ["code"]}, from_agent="coder"))
        await master.process_message(msg("agent_heartbeat", from_agent="coder"))

        created = await master.process_message(msg("create_task", {"title": "Poem", "required_capabilities": ["poetry"]}))
        task_id = created["task"]["task_id"]
        assert master.task_registry.get_task(task_id).status == TaskStatus.PENDING
        assert [t.task_id for t in master.unassignable_tasks()] == [task_id]
        assert (await master.process_message(msg("get_system_stats")))["data"]["unassignable"] == 1
        assert master.get_system_status()["unassignable_tasks"] == [task_id]

        # a poet shows up and pulls the waiting task
        bus.register_agent("poet")
        await master.process_message(msg("agent_capabilities", {"capabilities": ["poetry"]}, from_agent="poet"))
        assert master.unassignable_tasks() == []
        assert (await master.process_message(msg("task_request", from_agent="poet")))["task_id"] == task_id

    @pytest.mark.asyncio
    async def test_clients_can_create_tasks_with_required_capabilities(self):
        from src.core.task_client import TaskClient

        bus = MessageBus()
        master = make_master(bus)
        worker = Worker("w1", bus, MagicMock(), {})
        worker.enable_task_client(["writing"])
        master_task = await run_in_background(master)
        try:
            via_agent = await worker.create_task("A", "d", required_capabilities=["writing"])
            via_client = (await TaskClient("admin", bus).create_task("B", "d", required_capabilities=["x"]))["task"]
            assert master.task_registry.get_task(via_agent).required_capabilities == ["writing"]
            assert via_client["required_capabilities"] == ["x"]
        finally:
            await stop(master, master_task)
