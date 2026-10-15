"""PantheonCoordinator plan/execute workflow: planning by default, execution only with confirmation."""
import asyncio
from unittest.mock import AsyncMock, Mock

import pytest

from src.agents.pantheon_coordinator import PantheonCoordinator
from src.core.message_bus import Message, MessageBus, MessagePriority

SUBTASKS = [
    {"description": "Look at the screen", "agent": "observer", "priority": "high", "dependencies": []},
    {"description": "Check free disk space", "agent": "actor", "priority": "high", "dependencies": [0]},
    {"description": "Summarize", "agent": "validator", "priority": "low", "dependencies": [1]},
]


def make_pantheon(execute=False, confirm=None, subtasks=None, command="whoami", validator_valid=True, unsafe=()):
    bus = MessageBus()
    session_logger = Mock()
    pantheon = PantheonCoordinator(bus, session_logger, {})
    pantheon.execute_mode = execute
    pantheon.confirm_callback = confirm

    coordinator = Mock()
    coordinator.process_message = AsyncMock(return_value={"subtasks": subtasks if subtasks is not None else SUBTASKS})
    coordinator.grok_client.create_message = AsyncMock(return_value={"status": "success", "content": command})

    async def validate(msg):
        if msg.message_type == "check_safety":
            bad = msg.content["content"] in unsafe
            return {"content": {"safe": not bad, "issues": ["dangerous_command_format"] if bad else []}}
        return {"valid": validator_valid, "issues": [] if validator_valid else ["nope"]}

    validator = Mock()
    validator.process_message = AsyncMock(side_effect=validate)

    action_executor = Mock()
    action_executor.execute_bash = AsyncMock(return_value={"status": "success", "returncode": 0, "stdout": "me\n"})
    actor = Mock()
    actor.action_executor = action_executor

    learner = Mock()
    learner.process_message = AsyncMock(return_value={"status": "ok"})

    pantheon.agents = {"coordinator": coordinator, "validator": validator, "actor": actor, "learner": learner}
    return pantheon, action_executor


def run(pantheon, task="check disk"):
    msg = Message(
        message_type="new_task",
        from_agent="user",
        to_agent="pantheon_coordinator",
        priority=MessagePriority.HIGH,
        content={"task": task, "task_id": "t1"},
    )
    return asyncio.run(pantheon.process_message(msg))


def test_plan_mode_never_executes():
    pantheon, executor = make_pantheon(execute=False)
    report = run(pantheon)
    assert report["status"] == "planned" and report["mode"] == "plan"
    assert [s["agent"] for s in report["subtasks"]] == ["observer", "actor", "validator"]
    assert report["execution"] == []
    executor.execute_bash.assert_not_called()
    assert pantheon.task_completion_event.is_set()
    assert pantheon.last_report is report
    assert pantheon.pantheon_stats["tasks_completed"] == 1


def test_plan_flags_unsafe_subtasks():
    pantheon, _ = make_pantheon(unsafe=("Check free disk space",))
    report = run(pantheon)
    assert report["safety_flags"] == {1: ["dangerous_command_format"]}
    assert report["status"] == "planned"


def test_execute_without_callback_runs_nothing():
    pantheon, executor = make_pantheon(execute=True, confirm=None)
    report = run(pantheon)
    executor.execute_bash.assert_not_called()
    by_index = {e["index"]: e for e in report["execution"]}
    assert by_index[1]["status"] == "declined"
    assert by_index[0]["status"] == "skipped"  # observer subtask is not executable
    assert by_index[2]["status"] == "blocked"  # depends on the declined one
    assert report["status"] == "no_actions_run"


def test_execute_runs_only_after_confirmation():
    seen = []

    def confirm(subtask, command):
        seen.append((subtask["description"], command))
        return True

    pantheon, executor = make_pantheon(execute=True, confirm=confirm)
    report = run(pantheon)
    executor.execute_bash.assert_awaited_once_with("whoami")
    assert seen == [("Check free disk space", "whoami")]
    by_index = {e["index"]: e for e in report["execution"]}
    assert by_index[1]["status"] == "executed" and by_index[1]["output"] == "me\n"
    assert report["status"] == "executed"


def test_async_confirm_callback_supported():
    async def confirm(subtask, command):
        return True

    pantheon, executor = make_pantheon(execute=True, confirm=confirm)
    assert run(pantheon)["status"] == "executed"
    executor.execute_bash.assert_awaited_once()


def test_validator_rejection_blocks_execution():
    pantheon, executor = make_pantheon(execute=True, confirm=lambda s, c: True, validator_valid=False)
    report = run(pantheon)
    executor.execute_bash.assert_not_called()
    assert {e["index"]: e["status"] for e in report["execution"]}[1] == "blocked"


def test_flagged_subtask_is_not_executed():
    pantheon, executor = make_pantheon(execute=True, confirm=lambda s, c: True, unsafe=("Check free disk space",))
    report = run(pantheon)
    executor.execute_bash.assert_not_called()
    assert {e["index"]: e["status"] for e in report["execution"]}[1] == "blocked"


def test_none_reply_means_no_command():
    pantheon, executor = make_pantheon(execute=True, confirm=lambda s, c: True, command="NONE")
    report = run(pantheon)
    executor.execute_bash.assert_not_called()
    assert {e["index"]: e["status"] for e in report["execution"]}[1] == "skipped"


def test_fenced_command_is_unwrapped():
    pantheon, executor = make_pantheon(execute=True, confirm=lambda s, c: True, command="```\ndir\n```")
    run(pantheon)
    executor.execute_bash.assert_awaited_once_with("dir")


def test_failed_command_reports_failure():
    pantheon, executor = make_pantheon(execute=True, confirm=lambda s, c: True)
    executor.execute_bash.return_value = {"status": "error", "error": "boom"}
    report = run(pantheon)
    assert report["status"] == "failed"
    assert pantheon.pantheon_stats["tasks_failed"] == 1


def test_no_subtasks_is_failure_and_still_signals():
    pantheon, _ = make_pantheon(subtasks=[])
    report = run(pantheon)
    assert report["status"] == "failed"
    assert pantheon.task_completion_event.is_set()


def test_exception_still_signals_completion():
    pantheon, _ = make_pantheon()
    pantheon.agents["coordinator"].process_message = AsyncMock(side_effect=RuntimeError("llm down"))
    report = run(pantheon)
    assert report["status"] == "failed" and "llm down" in report["error"]
    assert pantheon.task_completion_event.is_set()
