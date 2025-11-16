"""
Asana Node for GG Workflow Framework

Integrates with Asana API for task and project management.
Supports operations like create task, update task, get task, add to project.

Author: Grokputer Team
Date: 2025-11-16
"""

from typing import Any, Dict, List, Optional

import aiohttp

from .base import BaseNode, NodeContext


class AsanaNode(BaseNode):
    """
    Node for Asana API operations.

    Configuration:
        api_key: Asana personal access token (or use {{ASANA_API_KEY}})
        operation: Operation type (create_task, update_task, get_task, add_to_project, etc.)
        task_gid: Task GID (for get/update operations)
        project_gid: Project GID (for create_task, add_to_project)
        workspace_gid: Workspace GID (for create operations)
        name: Task name (for create operations)
        notes: Task description (optional)
        assignee: Assignee email or GID (optional)
        due_date: Due date in YYYY-MM-DD format (optional)
        completed: Mark as completed (for update operations)

    Example:
        # Create task
        node = AsanaNode(
            "create_asana_task",
            config={
                "api_key": "{{ASANA_API_KEY}}",
                "operation": "create_task",
                "workspace_gid": "12345",
                "project_gid": "67890",
                "name": "{{task_name}}",
                "notes": "{{task_description}}",
                "assignee": "user@example.com"
            }
        )

        # Update task
        node = AsanaNode(
            "complete_task",
            config={
                "api_key": "{{ASANA_API_KEY}}",
                "operation": "update_task",
                "task_gid": "{{task_id}}",
                "completed": True
            }
        )

        # Get task
        node = AsanaNode(
            "get_task",
            config={
                "api_key": "{{ASANA_API_KEY}}",
                "operation": "get_task",
                "task_gid": "{{task_id}}"
            }
        )
    """

    BASE_URL = "https://app.asana.com/api/1.0"

    def __init__(self, node_id: str, name: Optional[str] = None, config: Optional[Dict] = None):
        super().__init__(node_id, name, config)

        # Validate required config
        if not self.config.get("api_key"):
            raise ValueError(f"AsanaNode {node_id} requires 'api_key' in config")
        if not self.config.get("operation"):
            raise ValueError(f"AsanaNode {node_id} requires 'operation' in config")

    async def execute(self, context: NodeContext) -> NodeContext:
        """
        Execute Asana operation.

        Args:
            context: Input context

        Returns:
            Output context with Asana response
        """
        operation = self.config["operation"]

        # Dispatch to operation handler
        if operation == "create_task":
            result = await self._create_task(context)
        elif operation == "update_task":
            result = await self._update_task(context)
        elif operation == "get_task":
            result = await self._get_task(context)
        elif operation == "delete_task":
            result = await self._delete_task(context)
        elif operation == "add_to_project":
            result = await self._add_to_project(context)
        elif operation == "create_subtask":
            result = await self._create_subtask(context)
        elif operation == "add_comment":
            result = await self._add_comment(context)
        else:
            raise ValueError(f"Unknown Asana operation: {operation}")

        # Create output context
        output_context = NodeContext(
            data={
                "asana_response": result,
                "operation": operation,
            },
            metadata=context.metadata,
            state=context.state,
        )

        # Store in state
        output_context.set_state(f"{self.node_id}_response", result)

        return output_context

    async def _create_task(self, context: NodeContext) -> Dict:
        """Create a new task."""
        url = f"{self.BASE_URL}/tasks"

        # Build task data
        task_data = {
            "name": self._interpolate(self.config["name"], context),
        }

        # Add workspace
        if "workspace_gid" in self.config:
            task_data["workspace"] = self._interpolate(self.config["workspace_gid"], context)

        # Add optional fields
        if "notes" in self.config:
            task_data["notes"] = self._interpolate(self.config["notes"], context)

        if "assignee" in self.config:
            assignee = self._interpolate(self.config["assignee"], context)
            # If email, need to look up GID first (simplified - use as-is)
            task_data["assignee"] = assignee

        if "due_date" in self.config:
            task_data["due_on"] = self._interpolate(self.config["due_date"], context)

        if "completed" in self.config:
            task_data["completed"] = self.config["completed"]

        # Add to project if specified
        if "project_gid" in self.config:
            task_data["projects"] = [self._interpolate(self.config["project_gid"], context)]

        body = {"data": task_data}
        return await self._make_request("POST", url, context, json=body)

    async def _update_task(self, context: NodeContext) -> Dict:
        """Update an existing task."""
        task_gid = self._interpolate(self.config["task_gid"], context)
        url = f"{self.BASE_URL}/tasks/{task_gid}"

        # Build update data
        task_data = {}

        if "name" in self.config:
            task_data["name"] = self._interpolate(self.config["name"], context)
        if "notes" in self.config:
            task_data["notes"] = self._interpolate(self.config["notes"], context)
        if "completed" in self.config:
            task_data["completed"] = self.config["completed"]
        if "due_date" in self.config:
            task_data["due_on"] = self._interpolate(self.config["due_date"], context)
        if "assignee" in self.config:
            task_data["assignee"] = self._interpolate(self.config["assignee"], context)

        body = {"data": task_data}
        return await self._make_request("PUT", url, context, json=body)

    async def _get_task(self, context: NodeContext) -> Dict:
        """Get task details."""
        task_gid = self._interpolate(self.config["task_gid"], context)
        url = f"{self.BASE_URL}/tasks/{task_gid}"

        return await self._make_request("GET", url, context)

    async def _delete_task(self, context: NodeContext) -> Dict:
        """Delete a task."""
        task_gid = self._interpolate(self.config["task_gid"], context)
        url = f"{self.BASE_URL}/tasks/{task_gid}"

        return await self._make_request("DELETE", url, context)

    async def _add_to_project(self, context: NodeContext) -> Dict:
        """Add task to a project."""
        task_gid = self._interpolate(self.config["task_gid"], context)
        project_gid = self._interpolate(self.config["project_gid"], context)
        url = f"{self.BASE_URL}/tasks/{task_gid}/addProject"

        body = {"data": {"project": project_gid}}
        return await self._make_request("POST", url, context, json=body)

    async def _create_subtask(self, context: NodeContext) -> Dict:
        """Create a subtask under a parent task."""
        parent_gid = self._interpolate(self.config["task_gid"], context)
        url = f"{self.BASE_URL}/tasks/{parent_gid}/subtasks"

        subtask_data = {
            "name": self._interpolate(self.config["name"], context),
        }

        if "notes" in self.config:
            subtask_data["notes"] = self._interpolate(self.config["notes"], context)

        body = {"data": subtask_data}
        return await self._make_request("POST", url, context, json=body)

    async def _add_comment(self, context: NodeContext) -> Dict:
        """Add a comment (story) to a task."""
        task_gid = self._interpolate(self.config["task_gid"], context)
        url = f"{self.BASE_URL}/tasks/{task_gid}/stories"

        body = {"data": {"text": self._interpolate(self.config["comment"], context)}}
        return await self._make_request("POST", url, context, json=body)

    async def _make_request(
        self, method: str, url: str, context: NodeContext, json: Optional[Dict] = None
    ) -> Dict:
        """Make authenticated request to Asana API."""
        api_key = self._interpolate(self.config["api_key"], context)

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        async with aiohttp.ClientSession() as session:
            async with session.request(
                method=method, url=url, headers=headers, json=json, timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status >= 400:
                    error_body = await response.text()
                    raise Exception(f"Asana API error {response.status}: {error_body}")

                return await response.json()

    def _interpolate(self, value: Any, context: NodeContext) -> Any:
        """Replace {{variable}} placeholders."""
        if not isinstance(value, str):
            return value

        result = value
        for key, val in {**context.data, **context.state}.items():
            placeholder = f"{{{{{key}}}}}"
            if placeholder in result:
                result = result.replace(placeholder, str(val))

        return result
