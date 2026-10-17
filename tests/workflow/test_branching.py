"""Conditional branching: edges with a condition only fire for the branch the source took."""
import pytest

from src.workflow.engine import WorkflowEngine
from src.workflow.flow import Workflow
from src.workflow.nodes import ConditionalNode
from src.workflow.nodes.base import BaseNode, NodeContext, NodeStatus


class Mark(BaseNode):
    """Records that it ran, in order, under data["ran"]."""

    async def execute(self, context: NodeContext) -> NodeContext:
        context.set("ran", context.get("ran", []) + [self.node_id])
        return context


class Switch(BaseNode):
    """Multi-way router: reports data["color"] as its branch."""

    async def execute(self, context: NodeContext) -> NodeContext:
        context.set_state(f"{self.node_id}_branch", context.get("color"))
        return context


class Boom(BaseNode):
    async def execute(self, context: NodeContext) -> NodeContext:
        raise RuntimeError("boom")


def is_big():
    return ConditionalNode("check", config={"conditions": [{"field": "n", "operator": ">", "value": 10}]})


def diamond():
    """check -> big (true) / small (false) -> join"""
    wf = Workflow("diamond")
    check, big, small, join = is_big(), Mark("big"), Mark("small"), Mark("join")
    for node in (check, big, small, join):
        wf.add_node(node)
    wf.add_edge(check, big, condition="true")
    wf.add_edge(check, small, condition="false")
    wf.add_edge(big, join)
    wf.add_edge(small, join)
    return wf


def statuses(wf):
    return {node_id: node.status for node_id, node in wf.engine.nodes.items()}


@pytest.mark.parametrize("parallel", [True, False])
@pytest.mark.asyncio
async def test_true_branch_runs_and_false_branch_is_skipped(parallel):
    wf = diamond()
    data = await wf.run({"n": 50}, parallel=parallel)
    assert data["ran"] == ["big", "join"]
    assert statuses(wf) == {
        "check": NodeStatus.SUCCESS,
        "big": NodeStatus.SUCCESS,
        "small": NodeStatus.SKIPPED,
        "join": NodeStatus.SUCCESS,
    }


@pytest.mark.parametrize("parallel", [True, False])
@pytest.mark.asyncio
async def test_false_branch_runs_and_true_branch_is_skipped(parallel):
    wf = diamond()
    data = await wf.run({"n": 1}, parallel=parallel)
    assert data["ran"] == ["small", "join"]
    assert statuses(wf)["big"] == NodeStatus.SKIPPED


@pytest.mark.asyncio
async def test_skip_propagates_down_a_skipped_branch():
    wf = Workflow("chain")
    check, a1, a2, b1 = is_big(), Mark("a1"), Mark("a2"), Mark("b1")
    for node in (check, a1, a2, b1):
        wf.add_node(node)
    wf.add_edge(check, a1, condition="true")
    wf.add_edge(a1, a2)  # unconditional, but a1 is skipped
    wf.add_edge(check, b1, condition="false")

    data = await wf.run({"n": 1})
    assert data["ran"] == ["b1"]
    assert statuses(wf)["a1"] == statuses(wf)["a2"] == NodeStatus.SKIPPED


@pytest.mark.asyncio
async def test_join_with_all_inputs_skipped_is_skipped_too():
    wf = Workflow("allskipped")
    check, a, b, join = is_big(), Mark("a"), Mark("b"), Mark("join")
    for node in (check, a, b, join):
        wf.add_node(node)
    wf.add_edge(check, a, condition="true")
    wf.add_edge(check, b, condition="true")
    wf.add_edge(a, join)
    wf.add_edge(b, join)

    data = await wf.run({"n": 1})
    assert "ran" not in data
    assert statuses(wf)["join"] == NodeStatus.SKIPPED


@pytest.mark.asyncio
async def test_workflows_without_conditions_are_unaffected():
    wf = Workflow("plain")
    a, b, c = Mark("a"), Mark("b"), Mark("c")
    for node in (a, b, c):
        wf.add_node(node)
    wf.add_edge(a, b).add_edge(a, c)
    assert (await wf.run({}))["ran"] in (["a", "b", "c"], ["a", "c", "b"])
    assert all(s == NodeStatus.SUCCESS for s in statuses(wf).values())


@pytest.mark.asyncio
async def test_rerun_with_different_input_takes_the_other_branch():
    wf = diamond()
    assert (await wf.run({"n": 50}))["ran"] == ["big", "join"]
    # no wf.reset(): run() starts from clean statuses and branch labels
    assert (await wf.run({"n": 1}))["ran"] == ["small", "join"]
    assert statuses(wf)["big"] == NodeStatus.SKIPPED


@pytest.mark.asyncio
async def test_two_conditionals_do_not_overwrite_each_others_branch():
    """data["branch"] is global, so routing uses each node's own state key."""
    wf = Workflow("two")
    first = ConditionalNode("first", config={"conditions": [{"field": "n", "operator": ">", "value": 10}]})
    second = ConditionalNode("second", config={"conditions": [{"field": "n", "operator": ">", "value": 100}]})
    on_first_true, on_second_false = Mark("first_true"), Mark("second_false")
    for node in (first, second, on_first_true, on_second_false):
        wf.add_node(node)
    wf.add_edge(first, second)
    wf.add_edge(first, on_first_true, condition="true")
    wf.add_edge(second, on_second_false, condition="false")

    data = await wf.run({"n": 50})  # first: true, second: false, and data["branch"] ends up "false"
    assert sorted(data["ran"]) == ["first_true", "second_false"]


@pytest.mark.parametrize("color, expected", [("red", ["red"]), ("blue", ["blue"]), ("green", [])])
@pytest.mark.asyncio
async def test_custom_node_can_route_multi_way(color, expected):
    wf = Workflow("switch")
    switch, red, blue = Switch("switch"), Mark("red"), Mark("blue")
    for node in (switch, red, blue):
        wf.add_node(node)
    wf.add_edge(switch, red, condition="red")
    wf.add_edge(switch, blue, condition="blue")

    data = await wf.run({"color": color})
    assert data.get("ran", []) == expected


@pytest.mark.asyncio
async def test_condition_is_case_insensitive_and_accepts_bool():
    wf = Workflow("case")
    check, yes = is_big(), Mark("yes")
    wf.add_node(check)
    wf.add_node(yes)
    wf.add_edge(check, yes, condition=True)  # str(True).lower() == "true"
    assert (await wf.run({"n": 50}))["ran"] == ["yes"]


@pytest.mark.asyncio
async def test_condition_on_a_node_that_reports_no_branch_is_never_taken():
    wf = Workflow("nobranch")
    a, b = Mark("a"), Mark("b")
    wf.add_node(a)
    wf.add_node(b)
    wf.add_edge(a, b, condition="true")
    data = await wf.run({})
    assert data["ran"] == ["a"] and statuses(wf)["b"] == NodeStatus.SKIPPED


@pytest.mark.asyncio
async def test_failure_still_aborts_and_is_not_mistaken_for_a_skip():
    wf = Workflow("fail")
    check, boom = is_big(), Boom("boom")
    wf.add_node(check)
    wf.add_node(boom)
    wf.add_edge(check, boom, condition="true")
    with pytest.raises(RuntimeError):
        await wf.run({"n": 50})
    assert statuses(wf)["boom"] == NodeStatus.FAILED


@pytest.mark.asyncio
async def test_execute_summary_counts_skipped_nodes():
    wf = diamond()
    result = await WorkflowEngine().execute(wf, {"n": 50})
    assert result["nodes_executed"] == 3 and result["nodes_skipped"] == 1
    assert (await WorkflowEngine().execute(Workflow("empty")))["nodes_skipped"] == 0


def test_disconnecting_removes_the_edge_condition():
    wf = Workflow("disc")
    check, big = is_big(), Mark("big")
    wf.add_node(check)
    wf.add_node(big)
    wf.add_edge(check, big, condition="true")
    assert big.input_conditions == {"check": "true"}
    check.disconnect_from(big)
    assert big.input_conditions == {}
