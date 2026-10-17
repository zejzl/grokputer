"""Workflow file loader and the `main.py --workflow` option."""
import json

import pytest
from click.testing import CliRunner

import main  # imported at module level: the autouse conftest fixture mocks src.tools per test
from src.workflow import WorkflowDefinitionError, WorkflowEngine, build_workflow, load_workflow

HELLO = {
    "name": "hello",
    "input": {"user": {"name": "Grokputer"}},
    "nodes": [
        {"id": "pick", "type": "transform", "config": {"operation": "jq", "expression": ".user.name"}},
        {"id": "done", "type": "noop"},
    ],
    "edges": [["pick", "done"]],
}


class TestBuildWorkflow:
    @pytest.mark.asyncio
    async def test_builds_and_runs(self):
        wf = build_workflow(HELLO)
        res = await WorkflowEngine().execute(wf, HELLO["input"])
        assert res["status"] == "success" and res["nodes_executed"] == 2
        assert res["data"]["result"] == "Grokputer"

    def test_edge_dict_form_with_condition(self):
        definition = {**HELLO, "edges": [{"from": "pick", "to": "done", "condition": "true"}]}
        wf = build_workflow(definition)
        assert wf.engine.nodes["pick"].conditions["true"] is wf.engine.nodes["done"]

    @pytest.mark.parametrize(
        "mutate, message",
        [
            (lambda d: d.update(nodes=[]), "non-empty"),
            (lambda d: d["nodes"].append({"id": "pick", "type": "noop"}), "Duplicate"),
            (lambda d: d["nodes"].append({"id": "x", "type": "evil.module.Class"}), "Unknown node type"),
            (lambda d: d["nodes"].append({"id": "h", "type": "http"}), "requires 'url'"),
            (lambda d: d["edges"].append(["pick", "ghost"]), "unknown node"),
            (lambda d: d["edges"].append("pick->done"), "must be"),
            (lambda d: d["edges"].append(["done", "pick"]), "ycle"),
        ],
    )
    def test_rejects_bad_definitions(self, mutate, message):
        definition = json.loads(json.dumps(HELLO))
        mutate(definition)
        with pytest.raises(ValueError, match=message):
            build_workflow(definition)

    def test_env_vars_expand_and_missing_is_an_error(self, monkeypatch):
        monkeypatch.setenv("WF_TEST_URL", "https://example.test/api")
        definition = {"nodes": [{"id": "h", "type": "http", "config": {"url": "${WF_TEST_URL}/x"}}]}
        assert build_workflow(definition).engine.nodes["h"].config["url"] == "https://example.test/api/x"

        monkeypatch.delenv("WF_TEST_URL")
        with pytest.raises(WorkflowDefinitionError, match="WF_TEST_URL"):
            build_workflow(definition)

    def test_template_variables_are_left_alone(self):
        definition = {"nodes": [{"id": "h", "type": "http", "config": {"url": "https://x.test/{{id}}"}}]}
        assert build_workflow(definition).engine.nodes["h"].config["url"].endswith("/{{id}}")


class TestLoadWorkflow:
    def test_yaml_and_json_files(self, tmp_path):
        y = tmp_path / "w.yaml"
        y.write_text(
            "name: w\ntimeout: 5\ninput: {a: 1}\nnodes:\n  - {id: n, type: noop}\n", encoding="utf-8"
        )
        wf, options = load_workflow(y)
        assert wf.name == "w" and options == {"timeout": 5.0, "input": {"a": 1}}

        j = tmp_path / "w.json"
        j.write_text(json.dumps({"nodes": [{"id": "n", "type": "noop"}]}), encoding="utf-8")
        assert load_workflow(j)[1] == {}

    def test_missing_and_malformed_files(self, tmp_path):
        with pytest.raises(WorkflowDefinitionError, match="not found"):
            load_workflow(tmp_path / "nope.yaml")
        bad = tmp_path / "bad.yaml"
        bad.write_text("- just\n- a list\n", encoding="utf-8")
        with pytest.raises(WorkflowDefinitionError, match="mapping"):
            load_workflow(bad)

    def test_bundled_example_loads(self):
        wf, _ = load_workflow("workflows/hello.yaml")
        assert set(wf.engine.nodes) == {"pick_name", "done"}


class TestCli:
    @staticmethod
    def _invoke(*args):
        return CliRunner().invoke(main.main, ["--skip-boot", *args])

    def test_runs_example_and_merges_input(self):
        res = self._invoke("--workflow", "workflows/hello.yaml", "--workflow-input", '{"user": {"name": "Zej"}}')
        assert res.exit_code == 0, res.output
        assert "success: 2 nodes" in res.output and '"result": "Zej"' in res.output

    def test_invalid_workflow_exits_2(self, tmp_path):
        bad = tmp_path / "bad.yaml"
        bad.write_text("nodes:\n  - {id: a, type: nope}\n", encoding="utf-8")
        res = self._invoke("--workflow", str(bad))
        assert res.exit_code == 2 and "Unknown node type" in res.output

    def test_non_object_input_exits_2(self):
        res = self._invoke("--workflow", "workflows/hello.yaml", "--workflow-input", "[1]")
        assert res.exit_code == 2

    def test_failing_node_exits_1(self, tmp_path):
        wf = tmp_path / "fail.yaml"
        wf.write_text(
            "nodes:\n  - {id: t, type: transform, config: {operation: jq, expression: 'not a path'}}\n",
            encoding="utf-8",
        )
        res = self._invoke("--workflow", str(wf))
        assert res.exit_code == 1 and "Failed" in res.output
