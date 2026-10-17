"""src.tools must expose the toolkit (it used to be shadowed by the package and failed to load)."""
import pytest

import src.tools as tools


@pytest.mark.parametrize(
    "name",
    [
        "bash",
        "search",
        "generate_code",
        "execute_generated_code",
        "get_vault_stats",
        "execute_tool",
        "scan_vault",
        "analytics_query_tool",
        "performance_monitor_tool",
        "enhanced_analytics_query",
    ],
)
def test_toolkit_names_are_exposed(name):
    assert callable(getattr(tools, name))


def test_unknown_attribute_raises_attribute_error():
    with pytest.raises(AttributeError):
        tools.definitely_not_a_tool


def test_registry_resolves_every_entry():
    assert all(callable(fn) for fn in tools.TOOL_REGISTRY.values())
    assert tools.execute_tool("nope")["status"] == "error"
    assert tools.execute_tool("invoke_prayer")["status"] == "success"


def test_generate_and_execute_roundtrip(tmp_path):
    res = tools.generate_code("hello.py", "print('hi')", sandbox_dir=str(tmp_path))
    assert res["status"] == "success"
    run = tools.execute_generated_code("hello.py", sandbox_dir=str(tmp_path))
    assert run["status"] == "success" and run["output"].strip() == "hi"


def test_generate_code_rejects_bad_syntax_and_path_escape(tmp_path):
    assert tools.generate_code("bad.py", "print(", sandbox_dir=str(tmp_path))["status"] == "error"
    res = tools.generate_code("../evil.py", "print(1)", sandbox_dir=str(tmp_path))
    assert res["status"] == "error" and "sandbox" in res["message"]
    assert not (tmp_path.parent / "evil.py").exists()


@pytest.mark.parametrize("cmd", ["echo hi; id", "echo hi | cat", "echo $HOME", "ls > out.txt"])
def test_bash_rejects_shell_metacharacters(cmd):
    res = tools.bash(cmd)
    assert res["status"] == "error" and "metacharacters" in res["message"]


def test_bash_runs_a_plain_command():
    assert tools.bash("git --version")["status"] == "success"


def test_search_finds_text(tmp_path):
    (tmp_path / "a.txt").write_text("needle here", encoding="utf-8")
    res = tools.search("needle", str(tmp_path))
    assert res["status"] == "success" and len(res["results"]) == 1


def test_analytics_query_is_the_real_implementation():
    # an earlier stub (`pass`) used to shadow the real function and return None
    assert tools.analytics_query("summary") is not None
