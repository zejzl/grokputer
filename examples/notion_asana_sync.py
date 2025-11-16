"""
Notion to Asana Sync Workflow

Example workflow that:
1. Queries Notion database for new tasks
2. Checks if task is marked as "Internal Project"
3. If yes, creates corresponding Asana task
4. If no, sends Slack notification
5. Uses AI to classify task priority

Author: Grokputer Team
Date: 2025-11-16
"""

import asyncio
import os

from src.workflow.engine import WorkflowEngine
from src.workflow.flow import Workflow
from src.workflow.nodes.ai_node import AINode
from src.workflow.nodes.asana import AsanaNode
from src.workflow.nodes.conditional import ConditionalNode
from src.workflow.nodes.notion import NotionNode
from src.workflow.nodes.slack import SlackNode
from src.workflow.nodes.transform import TransformNode


async def create_notion_asana_workflow():
    """
    Create the Notion -> Asana sync workflow.

    Flow:
    1. Query Notion database
    2. For each task:
       a. Check if "Internal Project" == True
       b. If yes: Create Asana task
       c. If no: Send Slack notification
    3. Use AI to determine priority
    """
    # Create workflow
    workflow = Workflow("notion_asana_sync", description="Sync Notion tasks to Asana")

    # 1. Query Notion database for tasks
    notion_query = NotionNode(
        "query_notion",
        config={
            "api_key": os.getenv("NOTION_API_KEY", "{{NOTION_API_KEY}}"),
            "operation": "query_database",
            "database_id": os.getenv("NOTION_DB_ID", "{{NOTION_DB_ID}}"),
            "filter": {
                "property": "Status",
                "select": {"equals": "To Do"},
            },
        },
    )
    workflow.add_node(notion_query)

    # 2. Extract first task from results
    extract_task = TransformNode(
        "extract_task",
        config={
            "operation": "jq",
            "expression": ".notion_response.results[0]",
        },
    )
    workflow.add_node(extract_task)
    workflow.add_edge(notion_query, extract_task)

    # 3. Use AI to classify priority
    ai_classify = AINode(
        "classify_priority",
        config={
            "provider": "grok",
            "model": "grok-4-fast-reasoning",
            "prompt": """Based on this task information, classify the priority as: low, medium, or high.

Task: {{task_name}}
Description: {{task_description}}

Reply with only: low, medium, or high""",
            "output_format": "text",
        },
    )
    workflow.add_node(ai_classify)
    workflow.add_edge(extract_task, ai_classify)

    # 4. Check if Internal Project
    check_internal = ConditionalNode(
        "check_internal",
        config={
            "conditions": [
                {
                    "field": "properties.Internal Project.checkbox",
                    "operator": "==",
                    "value": True,
                }
            ],
        },
    )
    workflow.add_node(check_internal)
    workflow.add_edge(ai_classify, check_internal)

    # 5a. If internal: Create Asana task
    create_asana = AsanaNode(
        "create_asana_task",
        config={
            "api_key": os.getenv("ASANA_API_KEY", "{{ASANA_API_KEY}}"),
            "operation": "create_task",
            "workspace_gid": os.getenv("ASANA_WORKSPACE", "{{ASANA_WORKSPACE}}"),
            "project_gid": os.getenv("ASANA_PROJECT", "{{ASANA_PROJECT}}"),
            "name": "{{task_name}}",
            "notes": "{{task_description}}\n\nPriority: {{ai_response}}",
        },
    )
    workflow.add_node(create_asana)
    workflow.add_edge(check_internal, create_asana, condition="true")

    # 5b. If not internal: Send Slack notification
    notify_slack = SlackNode(
        "notify_external",
        config={
            "bot_token": os.getenv("SLACK_BOT_TOKEN", "{{SLACK_BOT_TOKEN}}"),
            "operation": "send_message",
            "channel": "#external-projects",
            "text": "New external project task: {{task_name}}",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*New External Task*\n{{task_name}}\n_Priority: {{ai_response}}_",
                    },
                }
            ],
        },
    )
    workflow.add_node(notify_slack)
    workflow.add_edge(check_internal, notify_slack, condition="false")

    # 6. Final notification (both paths)
    final_notify = SlackNode(
        "final_notification",
        config={
            "bot_token": os.getenv("SLACK_BOT_TOKEN", "{{SLACK_BOT_TOKEN}}"),
            "operation": "send_message",
            "channel": "#workflow-logs",
            "text": "Notion-Asana sync completed for task: {{task_name}}",
        },
    )
    workflow.add_node(final_notify)
    workflow.add_edge(create_asana, final_notify)
    workflow.add_edge(notify_slack, final_notify)

    return workflow


async def main():
    """Run the workflow."""
    print("Creating Notion-Asana sync workflow...")

    # Create workflow
    workflow = await create_notion_asana_workflow()

    # Initialize engine
    engine = WorkflowEngine()

    # Execute workflow
    print("\nExecuting workflow...")
    try:
        result = await engine.execute(workflow)

        print("\nWorkflow completed successfully!")
        print(f"Status: {result['status']}")
        print(f"Duration: {result['duration']:.2f}s")
        print(f"\nResults: {result['data']}")

    except Exception as e:
        print(f"\nWorkflow failed: {str(e)}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
