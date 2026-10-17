"""
Workflow loader: build a Workflow from a YAML or JSON definition.

Example (YAML):

    name: greet
    timeout: 30                 # optional, seconds
    input: {name: Grokputer}    # optional initial data
    nodes:
      - id: pick
        type: transform
        config: {operation: jq, expression: ".name"}
      - id: shout
        type: noop
    edges:
      - [pick, shout]
      - {from: pick, to: shout, condition: "true"}   # same as above, with an edge condition

Node types: http, conditional, transform, ai, notion, asana, slack, noop.
String values in node configs may reference environment variables as ${VAR}, so tokens
need not be stored in the file. The engine's own {{variable}} templates are left untouched.

Limits: callables (transform_func, custom_evaluator) cannot be written in a file, so
transform nodes must use `operation: jq`. An edge `condition` is stored on the source node
as in Workflow.add_edge, but the engine does not skip nodes based on a conditional's branch.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Tuple, Union

import yaml

from .flow import Workflow
from .nodes import (
    AINode,
    AsanaNode,
    ConditionalNode,
    HTTPNode,
    NoOpNode,
    NotionNode,
    SlackNode,
    TransformNode,
)

NODE_TYPES = {
    "http": HTTPNode,
    "conditional": ConditionalNode,
    "transform": TransformNode,
    "ai": AINode,
    "notion": NotionNode,
    "asana": AsanaNode,
    "slack": SlackNode,
    "noop": NoOpNode,
}

_ENV_REF = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


class WorkflowDefinitionError(ValueError):
    """The workflow definition is malformed."""


def _expand_env(value: Any) -> Any:
    """Replace ${VAR} in strings (recursively); a missing variable is an error."""
    if isinstance(value, str):

        def repl(match: "re.Match[str]") -> str:
            name = match.group(1)
            if name not in os.environ:
                raise WorkflowDefinitionError(f"Environment variable {name} is not set")
            return os.environ[name]

        return _ENV_REF.sub(repl, value)
    if isinstance(value, dict):
        return {k: _expand_env(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand_env(v) for v in value]
    return value


def read_definition(path: Union[str, Path]) -> Dict[str, Any]:
    """Read a .yaml/.yml/.json workflow file into a dict."""
    path = Path(path)
    if not path.is_file():
        raise WorkflowDefinitionError(f"Workflow file not found: {path}")
    text = path.read_text(encoding="utf-8")
    try:
        data = json.loads(text) if path.suffix.lower() == ".json" else yaml.safe_load(text)
    except (json.JSONDecodeError, yaml.YAMLError) as e:
        raise WorkflowDefinitionError(f"Could not parse {path}: {e}") from e
    if not isinstance(data, dict):
        raise WorkflowDefinitionError(f"{path}: top level must be a mapping")
    return data


def _edge_parts(edge: Any, index: int) -> Tuple[str, str, Any]:
    if isinstance(edge, (list, tuple)) and len(edge) == 2:
        return str(edge[0]), str(edge[1]), None
    if isinstance(edge, dict) and "from" in edge and "to" in edge:
        return str(edge["from"]), str(edge["to"]), edge.get("condition")
    raise WorkflowDefinitionError(f"edges[{index}] must be [from, to] or {{from, to, condition?}}")


def build_workflow(definition: Dict[str, Any]) -> Workflow:
    """Build and validate a Workflow from a definition dict."""
    nodes_def = definition.get("nodes")
    if not isinstance(nodes_def, list) or not nodes_def:
        raise WorkflowDefinitionError("'nodes' must be a non-empty list")

    workflow = Workflow(str(definition.get("name", "workflow")), definition.get("config"))
    nodes: Dict[str, Any] = {}

    for i, spec in enumerate(nodes_def):
        if not isinstance(spec, dict) or "id" not in spec or "type" not in spec:
            raise WorkflowDefinitionError(f"nodes[{i}] needs 'id' and 'type'")
        node_id, node_type = str(spec["id"]), str(spec["type"]).lower()
        if node_id in nodes:
            raise WorkflowDefinitionError(f"Duplicate node id: {node_id}")
        if node_type not in NODE_TYPES:
            raise WorkflowDefinitionError(
                f"Unknown node type {node_type!r} for node {node_id}; choose from {', '.join(sorted(NODE_TYPES))}"
            )
        config = _expand_env(spec.get("config") or {})
        if not isinstance(config, dict):
            raise WorkflowDefinitionError(f"nodes[{i}].config must be a mapping")
        try:
            node = NODE_TYPES[node_type](node_id, name=spec.get("name"), config=config)
        except (ValueError, KeyError, TypeError) as e:
            raise WorkflowDefinitionError(f"Node {node_id} ({node_type}): {e}") from e
        nodes[node_id] = node
        workflow.add_node(node)

    for i, edge in enumerate(definition.get("edges") or []):
        src, dst, condition = _edge_parts(edge, i)
        for end in (src, dst):
            if end not in nodes:
                raise WorkflowDefinitionError(f"edges[{i}] references unknown node: {end}")
        workflow.add_edge(nodes[src], nodes[dst], condition=condition)

    workflow.validate()  # raises ValueError on a cycle
    return workflow


def load_workflow(path: Union[str, Path]) -> Tuple[Workflow, Dict[str, Any]]:
    """
    Load a workflow file.

    Returns:
        (workflow, options) where options has the optional 'timeout' (seconds) and 'input'
        (initial data) keys from the file.
    """
    definition = read_definition(path)
    workflow = build_workflow(definition)
    options: Dict[str, Any] = {}
    if definition.get("timeout") is not None:
        try:
            options["timeout"] = float(definition["timeout"])
        except (TypeError, ValueError) as e:
            raise WorkflowDefinitionError(f"'timeout' must be a number of seconds: {e}") from e
    if definition.get("input") is not None:
        if not isinstance(definition["input"], dict):
            raise WorkflowDefinitionError("'input' must be a mapping")
        options["input"] = definition["input"]
    return workflow, options
