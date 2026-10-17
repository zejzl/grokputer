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
        notice = await bus.receive("w1", timeout=1)
        assert notice.message_type == "task_assigned"

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
