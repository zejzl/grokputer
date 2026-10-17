# GG Workflow Framework

Python-native workflow orchestration system that combines n8n-style visual logic with Grokputer's AI-powered Pantheon agents.

## Features

- **Core Nodes**: HTTP, Transform, Conditional, AI
- **Integrations**: Notion, Asana, Slack (+ more to come)
- **AI-Powered**: Invoke Grok, Claude, or any Pantheon agent
- **Multi-Provider**: Use MAF for consensus across multiple AI providers
- **Async Execution**: Built on MessageBus (18K msg/sec)
- **Self-Healing**: Learner and Improver agents optimize workflows over time

## Quick Start

```python
import asyncio
from src.workflow import Workflow, WorkflowEngine
from src.workflow.nodes import HTTPNode, AINode, SlackNode

async def main():
    # Create workflow
    workflow = Workflow("weather_alert")

    # 1. Fetch weather
    fetch = HTTPNode("fetch", config={
        "url": "https://api.weatherapi.com/v1/current.json",
        "method": "GET",
        "query_params": {"key": "YOUR_KEY", "q": "San Francisco"}
    })
    workflow.add_node(fetch)

    # 2. AI analysis
    analyze = AINode("analyze", config={
        "provider": "grok",
        "prompt": "Suggest an activity based on: {{body.current.condition.text}}"
    })
    workflow.add_node(analyze)
    workflow.add_edge(fetch, analyze)

    # 3. Notify
    notify = SlackNode("notify", config={
        "bot_token": "YOUR_TOKEN",
        "operation": "send_message",
        "channel": "#weather",
        "text": "Weather update: {{ai_response}}"
    })
    workflow.add_node(notify)
    workflow.add_edge(analyze, notify)

    # Execute
    engine = WorkflowEngine()
    result = await engine.execute(workflow)
    print(f"Status: {result['status']}")

asyncio.run(main())
```

## Running a workflow from a file

Define the workflow in YAML (or JSON) and run it with `main.py`:

```yaml
name: hello
timeout: 30                 # optional, seconds
input: {user: {name: Grokputer}}   # optional initial data
nodes:
  - id: pick_name
    type: transform         # http | conditional | transform | ai | notion | asana | slack | noop
    config: {operation: jq, expression: ".user.name"}
  - id: done
    type: noop
edges:
  - [pick_name, done]       # or {from: a, to: b, condition: "true"}
```

```bash
python main.py --workflow workflows/hello.yaml
python main.py --workflow workflows/hello.yaml --workflow-input '{"user": {"name": "Zej"}}'
```

- String values in node configs can use `${ENV_VAR}` (a missing variable is an error), so tokens need not live in the file. `{{variables}}` are left for the engine.
- Callables (`transform_func`, `custom_evaluator`) cannot be written in a file; transform nodes use `operation: jq`.
- An edge `condition` routes: the target runs only if the source took that branch (see Conditional Branching below). Try `workflows/branch.yaml`.
- Exit codes: 0 success, 1 a node failed or timed out, 2 invalid definition or input. Loader: `src/workflow/loader.py`; example: `workflows/hello.yaml`.

## Available Nodes

### Core Nodes

#### HTTPNode
Make HTTP requests (GET, POST, PUT, DELETE, PATCH).

```python
HTTPNode("api_call", config={
    "url": "https://api.example.com/data",
    "method": "POST",
    "headers": {"Authorization": "Bearer {{token}}"},
    "body": {"key": "value"},
    "retries": 3
})
```

#### ConditionalNode
Branch based on conditions.

```python
ConditionalNode("check", config={
    "conditions": [
        {"field": "status", "operator": "==", "value": "active"}
    ]
})
```

#### TransformNode
Transform data with custom functions or JQ expressions.

```python
TransformNode("extract", config={
    "operation": "jq",
    "expression": ".user.email"
})
```

#### AINode
Ask one AI provider a question. It runs on the same `GrokClient` as the rest of Grokputer, so the provider's API key must be in the environment (`XAI_API_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`), or `claude` CLI logged in for `claude-cli`.

```python
AINode("classify", config={
    "provider": "claude",            # grok (default), claude, claude-cli, gemini, openai
    "model": "claude-haiku-5-5",     # optional; omitted = the provider's default (GROK_MODEL, CLAUDE_MODEL, ...)
    "system_prompt": "Reply with one word.",
    "prompt": "Classify urgency of: {{text}}",
    "temperature": 0.2,              # default 0.7; ignored by claude-cli
    "max_tokens": 50,                # default 2000; ignored by claude-cli
})
```

The node outputs `ai_response`, `raw_response`, `provider` and the `model` that answered, and records token usage under the tag `workflow:<node_id>`. A failing call (bad key, billing error, ...) fails the node with the provider's message; use `max_retries` in the node config to retry.

Not supported by `AINode`, and rejected when the node is created: `provider: "maf"` (MAF returns consensus metadata, not a reply; use `main.py --providers`) and `pantheon_agent` (use `PantheonNode`).

### Integration Nodes

#### NotionNode
Read/write Notion pages and databases.

```python
NotionNode("get_tasks", config={
    "api_key": "{{NOTION_API_KEY}}",
    "operation": "query_database",
    "database_id": "abc123",
    "filter": {"property": "Status", "select": {"equals": "To Do"}}
})
```

#### AsanaNode
Manage Asana tasks and projects.

```python
AsanaNode("create_task", config={
    "api_key": "{{ASANA_API_KEY}}",
    "operation": "create_task",
    "workspace_gid": "12345",
    "name": "{{task_name}}",
    "assignee": "user@example.com"
})
```

#### SlackNode
Send messages and notifications.

```python
SlackNode("alert", config={
    "bot_token": "{{SLACK_BOT_TOKEN}}",
    "operation": "send_message",
    "channel": "#alerts",
    "text": "Task completed: {{task_name}}"
})
```

## Variable Interpolation

Use `{{variable}}` syntax to reference context data:

```python
HTTPNode("fetch", config={
    "url": "https://api.example.com/users/{{user_id}}",
    "headers": {"Authorization": "Bearer {{api_token}}"}
})
```

Variables are resolved from:
1. `context.data` - Data passed between nodes
2. `context.state` - Workflow state
3. Environment variables (when using `os.getenv()`)

## Conditional Branching

Connect different nodes based on conditions:

```python
# Add conditional
workflow.add_node(check_status)

# Branch on condition result
workflow.add_edge(check_status, success_node, condition="true")
workflow.add_edge(check_status, failure_node, condition="false")
```

How routing works:

- A `ConditionalNode` reports the branch it took (`"true"` or `"false"`). An edge with a `condition` is *active* only when its source took that branch; an edge without one is active whenever the source ran.
- A node runs if it has no inputs or at least one active incoming edge (an OR-join). Otherwise it is marked `SKIPPED`, and that propagates: everything downstream of a skipped node that has no other active input is skipped too. A diamond (`check -> A | B -> join`) therefore runs `join` after whichever side was taken.
- Any node can route, not only conditionals: set the state key `"<node_id>_branch"` to a label (`context.set_state(f"{self.node_id}_branch", "gold")`) and use that label as the edge `condition`. This allows multi-way switches.
- Labels are compared as lowercase strings, so `condition=True` equals `"true"`. An edge condition on a node that reports no branch is never taken (a warning is logged).
- Each `run()` starts from clean statuses and branch labels, so the same workflow can take a different branch on its next run. `execute()` returns `nodes_skipped` next to `nodes_executed`.

## Pantheon Integration

Delegating to a Pantheon agent is done with `PantheonNode` (`src/workflow/pantheon_integration.py`), configured with `agent` and `task`. `AINode` does not accept `pantheon_agent`. `PantheonNode` has no tests yet and has not been run against live agents, so treat it as unverified.

```python
from src.workflow.pantheon_integration import PantheonNode

PantheonNode("analyze_screen", config={
    "agent": "observer",
    "task": "Find all text elements on screen",
})
```

## Testing

```bash
# Run all workflow tests
pytest tests/workflow/ -v

# Run with coverage
pytest tests/workflow/ --cov=src.workflow --cov-report=html
```

## Examples

See `examples/` directory:
- `workflow_quickstart.py` - Basic workflow concepts
- `notion_asana_sync.py` - Notion → Asana sync with AI classification

## Architecture

```
src/workflow/
├── __init__.py         # Main exports
├── engine.py           # WorkflowEngine (execution)
├── flow.py             # Workflow (definition)
├── nodes/
│   ├── base.py         # BaseNode, NodeContext
│   ├── http.py         # HTTP requests
│   ├── conditional.py  # If/else logic
│   ├── transform.py    # Data transformations
│   ├── ai_node.py      # AI/Pantheon integration
│   ├── notion.py       # Notion API
│   ├── asana.py        # Asana API
│   └── slack.py        # Slack API
└── README.md          # This file
```

## Roadmap

- [ ] More integration nodes (GitHub, Linear, Discord)
- [ ] Visual workflow builder UI (Streamlit)
- [ ] Workflow templates library
- [ ] Trigger system (webhooks, schedules, events)
- [ ] State persistence (Redis backend)
- [ ] Self-learning optimization (via Learner agent)
- [ ] Distributed execution (Docker Swarm)

## Contributing

Workflow nodes are easy to create! Extend `BaseNode`:

```python
from src.workflow.nodes.base import BaseNode, NodeContext

class CustomNode(BaseNode):
    async def execute(self, context: NodeContext) -> NodeContext:
        # Your logic here
        result = do_something(context.data)
        context.set("result", result)
        return context
```

## ZA GROKA. ZA GG. ZA INFINITE EVOLUTION.
