import pytest

import main


def test_interactive_menu_exits_cleanly_on_eof(monkeypatch):
    def raise_eof(prompt=""):
        raise EOFError

    monkeypatch.setattr("builtins.input", raise_eof)
    with pytest.raises(SystemExit) as exc:
        main._run_interactive_mode(False, 1, 1, True)
    assert exc.value.code == 0
