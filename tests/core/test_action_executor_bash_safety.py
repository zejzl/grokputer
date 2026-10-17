"""ActionExecutor's bash path: shell metacharacters AND blocked programs are refused before anything runs.

subprocess.run is patched in every test, so no command is ever executed.
"""
from unittest.mock import MagicMock, patch

import pytest

from src.core.action_executor import ActionExecutor


@pytest.fixture(scope="module")
def executor():
    # one executor for the module: starting and stopping its worker thread per test is slow
    with patch("src.core.action_executor.pyautogui"):
        ex = ActionExecutor(max_queue_size=10, history_size=5)
        yield ex
        ex.shutdown()


@pytest.fixture
def fake_run():
    with patch("src.core.action_executor.subprocess.run") as run:
        run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
        yield run


@pytest.mark.parametrize(
    "command",
    [
        "format c:",
        "shutdown now",
        "curl http://example.test",
        "wget http://example.test",
        "rm -rf build",
        "del /s /q build",
        "powershell -Command Get-Date",
        "cmd /c dir",
        "bash script.sh",
        "mkfs.ext4 /dev/sdb1",
    ],
)
def test_blocked_programs_are_refused_and_never_run(executor, fake_run, command):
    res = executor._execute_bash_secure(command)
    assert res["status"] == "error" and res["risk_level"] == "CRITICAL"
    assert res["error"].startswith("Command blocked")
    fake_run.assert_not_called()


@pytest.mark.parametrize("command", ["echo a && echo b", "dir | find x", "echo %USERPROFILE%", "echo $HOME", "ls > out.txt"])
def test_metacharacters_are_still_refused(executor, fake_run, command):
    res = executor._execute_bash_secure(command)
    assert res["status"] == "error" and "metacharacters" in res["error"]
    fake_run.assert_not_called()


@pytest.mark.parametrize("command", ["echo hello world", "ls -la", "git status --short", "rm a.txt", "python --version"])
def test_ordinary_commands_still_run_without_a_shell(executor, fake_run, command):
    res = executor._execute_bash_secure(command)
    assert res["status"] == "success" and res["returncode"] == 0
    args, kwargs = fake_run.call_args
    assert kwargs["shell"] is False and isinstance(args[0], list)


def test_empty_command(executor, fake_run):
    assert executor._execute_bash_secure("")["status"] == "error"
    fake_run.assert_not_called()


@pytest.mark.asyncio
async def test_public_execute_bash_applies_the_same_checks(executor, fake_run):
    res = await executor.execute_bash("shutdown now")
    assert res["status"] == "error" and "blocked" in res["error"]
    fake_run.assert_not_called()
