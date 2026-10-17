"""Regression tests: no shell=True, and the formerly bare excepts behave."""
import ast
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import improve_swarm



ROOT = Path(__file__).resolve().parents[1]
SCANNED = [ROOT / "main.py", ROOT / "improve_swarm.py", ROOT / "autonomous.py", *sorted((ROOT / "src").rglob("*.py"))]


def _calls_with_shell_true(tree):
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            for kw in node.keywords:
                if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                    yield node.lineno


def _bare_excepts(tree):
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler) and node.type is None:
            yield node.lineno


class TestSourceGuards:
    def _scan(self, finder):
        hits = []
        for path in SCANNED:
            if not path.exists():
                continue
            tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
            hits += [f"{path.relative_to(ROOT)}:{line}" for line in finder(tree)]
        return hits

    def test_no_subprocess_shell_true(self):
        assert self._scan(_calls_with_shell_true) == []

    def test_no_bare_except(self):
        assert self._scan(_bare_excepts) == []


class TestImproveSwarm:
    def _fix(self, path, old, new):
        return {"file": str(path), "old_str": old, "new_str": new, "reason": "test"}

    @pytest.fixture(autouse=True)
    def _quiet_log(self, monkeypatch, tmp_path):
        monkeypatch.setattr(improve_swarm, "IMPROVE_LOG", tmp_path / "improve.log")

    def test_apply_edit_is_literal_and_never_uses_subprocess(self, tmp_path):
        f = tmp_path / "mod.py"
        f.write_text("a = x / y  # (1+1) [z]\n", encoding="utf-8")
        with patch("improve_swarm.subprocess.run") as run:
            ok = improve_swarm.apply_edit(self._fix(f, "x / y  # (1+1) [z]", "x // y"))
        assert ok is True and f.read_text(encoding="utf-8") == "a = x // y\n"
        run.assert_not_called()

    def test_apply_edit_missing_old_str_reverts_and_fails(self, tmp_path):
        f = tmp_path / "mod.py"
        f.write_text("keep me\n", encoding="utf-8")
        assert improve_swarm.apply_edit(self._fix(f, "not there", "x")) is False
        assert f.read_text(encoding="utf-8") == "keep me\n"

    def test_dry_run_changes_nothing(self, tmp_path):
        f = tmp_path / "mod.py"
        f.write_text("same\n", encoding="utf-8")
        assert improve_swarm.apply_edit(self._fix(f, "same", "diff"), dry_run=True) is True
        assert f.read_text(encoding="utf-8") == "same\n"

    def test_test_fix_uses_argv_list_without_shell(self):
        with patch("improve_swarm.subprocess.run") as run, patch("improve_swarm.read_logs", return_value=[]):
            run.return_value = MagicMock(returncode=0, stdout="")
            improve_swarm.test_fix({"agent_action": "actor.bash", "error": "e"})
        args, kwargs = run.call_args
        assert isinstance(args[0], list) and kwargs["shell"] is False
        assert "--max-iterations" in args[0]


class TestImproveSwarmRevert:
    @pytest.fixture(autouse=True)
    def _quiet_log(self, monkeypatch, tmp_path):
        monkeypatch.setattr(improve_swarm, "IMPROVE_LOG", tmp_path / "improve.log")

    def _run_main(self, tmp_path, test_passes):
        f = tmp_path / "mod.py"
        f.write_text("value = 1" + chr(10), encoding="utf-8")
        fix = {"file": str(f), "old_str": "value = 1", "new_str": "value = 2", "reason": "test"}
        issue = {"agent_action": "actor.bash", "error": "e", "count": 3, "examples": [], "file": str(f)}
        with patch.object(improve_swarm, "read_logs", return_value=[{"x": 1}]), patch.object(
            improve_swarm, "detect_issues", return_value=[issue]
        ), patch.object(improve_swarm, "get_grok_fix", return_value=fix), patch.object(
            improve_swarm, "test_fix", return_value=test_passes
        ):
            improve_swarm.main()
        return f

    def test_failed_test_reverts_the_edit(self, tmp_path):
        f = self._run_main(tmp_path, test_passes=False)
        assert f.read_text(encoding="utf-8") == "value = 1" + chr(10)

    def test_passing_test_keeps_the_edit(self, tmp_path):
        f = self._run_main(tmp_path, test_passes=True)
        assert f.read_text(encoding="utf-8") == "value = 2" + chr(10)

    def test_revert_without_backup_is_a_noop(self):
        assert improve_swarm.revert_edit({"file": "nope.py"}) is False


class TestFormerBareExcepts:
    def test_taskmaster_fallback_does_not_raise(self):
        import asyncio

        from src.agents.taskmaster import Taskmaster

        class _Tm(Taskmaster):
            async def process_message(self, message):
                return None

        tm = _Tm.__new__(_Tm)
        tm.client = MagicMock()

        async def chat(messages):
            return "not json"

        async def analyze():
            return {}

        tm.client.chat = chat
        tm.analyze_metrics = analyze
        tasks = asyncio.run(tm.suggest_tasks({}))
        assert len(tasks) >= 3 and all(hasattr(t, "impact_score") for t in tasks)

    def test_connect_to_process_closes_socket_and_returns_false(self):
        from src.core.distributed_communication import ProcessCommunicator

        comm = ProcessCommunicator.__new__(ProcessCommunicator)
        comm.process_id = "p"
        comm.client_sockets = {}
        fake = MagicMock()
        fake.connect.side_effect = ConnectionRefusedError
        with patch("src.core.distributed_communication.socket.socket", return_value=fake):
            assert comm.connect_to_process("other") is False
        assert fake.close.call_count == 100

    def test_taskmaster_parses_valid_json(self):
        import asyncio
        import json

        from src.agents.taskmaster import Taskmaster

        class _Tm(Taskmaster):
            async def process_message(self, message):
                return None

        tm = _Tm.__new__(_Tm)
        tm.client = MagicMock()
        payload = [
            {"description": "a", "priority": "high", "impact": 9, "effort": "low", "category": "feature"},
            {"description": "b", "priority": "low", "impact": 3, "effort": "high", "category": "opt"},
        ]

        async def chat(messages):
            return json.dumps(payload)

        async def analyze():
            return {}

        tm.client.chat = chat
        tm.analyze_metrics = analyze
        tasks = asyncio.run(tm.suggest_tasks({}))
        assert [t.description for t in tasks] == ["a", "b"]
