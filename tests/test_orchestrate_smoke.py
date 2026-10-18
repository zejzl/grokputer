"""Smoke tests for orchestrate.sh using stub tool scripts (no Docker, git or network)."""
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BASH = shutil.which("bash")

pytestmark = pytest.mark.skipif(BASH is None, reason="bash not available")

TOOLS = [
    "automate.sh",
    "setup-mcp-alpine.sh",
    "deploy.sh",
    "monitor.sh",
    "git-workflow.sh",
    "code-review.sh",
    "optimize-performance.sh",
    "manage-dependencies.sh",
    "generate-docs.sh",
    "verify-mcp-setup.sh",
]


def _run(cwd, *args, timeout=60):
    result = subprocess.run(
        [BASH, "orchestrate.sh", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=timeout,
        stdin=subprocess.DEVNULL,
    )
    return result.returncode, re.sub(r"\x1b\[[0-9;]*m", "", result.stdout + result.stderr)


@pytest.fixture
def sandbox(tmp_path):
    """orchestrate.sh next to stub tools that log their calls; `quality` fails."""
    script = (ROOT / "orchestrate.sh").read_text(encoding="utf-8")
    # shorten panda mode to two cycles without waiting
    script = script.replace("sleep 300", 'sleep 0; [ "$cycle" -ge 2 ] && break')
    (tmp_path / "orchestrate.sh").write_text(script, encoding="utf-8", newline="\n")
    for tool in TOOLS:
        (tmp_path / tool).write_text(
            'echo "$0 $*" >> calls.log\n[ "$1" = "quality" ] && exit 1\nexit 0\n', encoding="utf-8", newline="\n"
        )
    return tmp_path


def test_help_and_unknown_command(sandbox):
    code, out = _run(sandbox, "help")
    assert code == 0 and "Usage:" in out
    code, _ = _run(sandbox, "no-such-command")
    assert code == 1


def test_tools_lists_stubs_as_present(sandbox):
    _, out = _run(sandbox, "tools")
    assert "✓ automate.sh" in out
    assert "✗ setup-mcp-alpine.bat" in out  # stubs only cover the .sh tools


def test_failed_step_does_not_abort_workflow(sandbox):
    _, out = _run(sandbox, "dev")
    calls = (sandbox / "calls.log").read_text()
    assert "automate.sh quality" in calls
    assert "automate.sh test" in calls  # ran after the failing step
    assert "failed: automate.sh quality" in out
    assert "finished with failures" in out


def test_panda_mode_runs_two_cycles(sandbox):
    code, out = _run(sandbox, "infinite", timeout=120)
    assert code == 0
    assert "CYCLE 1" in out and "CYCLE 2" in out
    assert out.count("Achievement Points") == 2
