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
Invoke AI models or Pantheon agents.

```python
# Single provider
AINode("classify", config={
    "provider": "grok",
    "model": "grok-4-fast-reasoning",
    "prompt": "Classify: {{text}}"
})

# Multi-provider consensus (MAF)
AINode("decide", config={
    "provider": "maf",
    "maf_config": {
        "providers": ["grok", "claude", "openai"],
        "consensus_threshold": 0.6
    },
    "prompt": "Should we proceed with: {{action}}?"
})

# Pantheon agent delegation
AINode("observe", config={
    "pantheon_agent": "observer",
    "prompt": "Analyze current screen"
})
```

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

## Pantheon Integration

Invoke specific Pantheon agents for complex operations:

```python
# Delegate to Observer agent for screen analysis
AINode("analyze_screen", config={
    "pantheon_agent": "observer",
    "prompt": "Find all text elements on screen"
})

# Delegate to Executor for multi-step tasks
AINode("execute_workflow", config={
    "pantheon_agent": "executor",
    "prompt": "Complete checkout process"
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
