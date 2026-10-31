"""The rate command: ratings land next to session.json and feed the trainer's loader."""
import json
import time

import pytest

from src.training import rate
from src.training.feedback import FEEDBACK_FILE, read_session


def make_session(logs, name, task="open settings", age=0):
    directory = logs / name
    directory.mkdir(parents=True)
    path = directory / "session.json"
    path.write_text(json.dumps({"task": task, "tool_executions": [{"tool": "click"}]}), encoding="utf-8")
    stamp = time.time() - age
    import os
    os.utime(path, (stamp, stamp))
    return directory


def test_rate_last_picks_the_newest_session_and_writes_feedback(tmp_path, capsys):
    make_session(tmp_path, "session_old", age=500)
    new = make_session(tmp_path, "session_new", age=1)
    assert rate.main(["last", "--rating", "2", "--issue", "wrong-action", "--issue", "popup", "--logs", str(tmp_path)]) == 0
    saved = json.loads((new / FEEDBACK_FILE).read_text())
    assert saved["user_rating"] == 2
    assert saved["what_went_wrong"] == ["Wrong action selected", "popup"]
    assert not (tmp_path / "session_old" / FEEDBACK_FILE).exists()
    assert read_session(new)["rating"] == 2


def test_rating_without_issue_or_out_of_range_is_refused(tmp_path, capsys):
    make_session(tmp_path, "session_a")
    assert rate.main(["session_a", "--rating", "2", "--logs", str(tmp_path)]) == 1
    assert rate.main(["session_a", "--rating", "9", "--issue", "ocr", "--logs", str(tmp_path)]) == 1
    assert not (tmp_path / "session_a" / FEEDBACK_FILE).exists()


def test_session_name_cannot_escape_the_logs_directory(tmp_path):
    make_session(tmp_path / "logs", "session_a")
    outside = make_session(tmp_path, "session_outside")
    with pytest.raises(SystemExit):
        rate.main(["../session_outside", "--rating", "1", "--issue", "ocr", "--logs", str(tmp_path / "logs")])
    assert not (outside / FEEDBACK_FILE).exists()


def test_list_shows_rated_state(tmp_path, capsys):
    make_session(tmp_path, "session_a", task="task a")
    rate.main(["session_a", "--rating", "1", "--issue", "timeout", "--logs", str(tmp_path)])
    capsys.readouterr()
    assert rate.main(["list", "--logs", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "session_a" in out and "rated 1" in out and "task a" in out


def test_missing_logs_directory_is_an_error(tmp_path, capsys):
    assert rate.main(["list", "--logs", str(tmp_path / "none")]) == 1
    with pytest.raises(SystemExit):
        rate.main(["last", "--rating", "1", "--issue", "ocr", "--logs", str(tmp_path / "none")])


def test_rate_module_does_not_load_the_training_stack():
    import subprocess, sys
    code = "import sys, src.training.rate; sys.exit(1 if 'transformers' in sys.modules or 'trl' in sys.modules else 0)"
    assert subprocess.run([sys.executable, "-c", code]).returncode == 0
