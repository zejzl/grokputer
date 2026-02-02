"""
Notion Node for GG Workflow Framework

Integrates with Notion API for reading/writing pages, databases, blocks.
Supports common operations like get page, create page, update properties, query database.

Author: Grokputer Team
Date: 2025-11-16
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import aiohttp

from .base import BaseNode, NodeContext


class NotionNode(BaseNode):
    """
    Node for Notion API operations.

    Configuration:
        api_key: Notion integration token (or use {{NOTION_API_KEY}})
        operation: Operation type (get_page, create_page, update_page, query_database, etc.)
        page_id: Page ID (for get/update operations)
        database_id: Database ID (for query/create operations)
        properties: Properties dict (for create/update operations)
        filter: Query filter (for query_database)
        sorts: Sort configuration (for query_database)

    Example:
        # Get page
        node = NotionNode(
            "get_task",
            config={
                "api_key": "{{NOTION_API_KEY}}",
                "operation": "get_page",
                "page_id": "abc123"
            }
        )

        # Create page in database
        node = NotionNode(
            "create_task",
            config={
                "api_key": "{{NOTION_API_KEY}}",
                "operation": "create_page",
                "database_id": "db123",
                "properties": {
                    "Name": {"title": [{"text": {"content": "{{task_name}}"}}]},
                    "Status": {"select": {"name": "To Do"}}
                }
            }
        )

        # Query database
        node = NotionNode(
            "query_tasks",
            config={
                "api_key": "{{NOTION_API_KEY}}",
                "operation": "query_database",
                "database_id": "db123",
                "filter": {
                    "property": "Status",
                    "select": {"equals": "In Progress"}
                }
            }
        )
    """

    NOTION_VERSION = "2022-06-28"
    BASE_URL = "https://api.notion.com/v1"

    def __init__(self, node_id: str, name: Optional[str] = None, config: Optional[Dict] = None):
        super().__init__(node_id, name, config)

        # Validate required config
        if not self.config.get("api_key"):
            raise ValueError(f"NotionNode {node_id} requires 'api_key' in config")
        if not self.config.get("operation"):
            raise ValueError(f"NotionNode {node_id} requires 'operation' in config")

    async def execute(self, context: NodeContext) -> NodeContext:
        """
        Execute Notion operation.

        Args:
            context: Input context

        Returns:
            Output context with Notion response
        """
        operation = self.config["operation"]

        # Dispatch to operation handler
        if operation == "get_page":
            result = await self._get_page(context)
        elif operation == "create_page":
            result = await self._create_page(context)
        elif operation == "update_page":
            result = await self._update_page(context)
        elif operation == "query_database":
            result = await self._query_database(context)
        elif operation == "get_database":
            result = await self._get_database(context)
        elif operation == "get_block_children":
            result = await self._get_block_children(context)
        else:
            raise ValueError(f"Unknown Notion operation: {operation}")

        # Create output context
        output_context = NodeContext(
            data={
                "notion_response": result,
                "operation": operation,
            },
            metadata=context.metadata,
            state=context.state,
        )

        # Store in state
        output_context.set_state(f"{self.node_id}_response", result)

        return output_context

    async def _get_page(self, context: NodeContext) -> Dict:
        """Get a Notion page by ID."""
        page_id = self._interpolate(self.config["page_id"], context)
        url = f"{self.BASE_URL}/pages/{page_id}"

        return await self._make_request("GET", url, context)

    async def _create_page(self, context: NodeContext) -> Dict:
        """Create a new page in a database."""
        database_id = self._interpolate(self.config["database_id"], context)
        properties = self._interpolate_dict(self.config["properties"], context)

        url = f"{self.BASE_URL}/pages"
        body = {"parent": {"database_id": database_id}, "properties": properties}

        # Add content if specified
        if "children" in self.config:
            body["children"] = self.config["children"]

        return await self._make_request("POST", url, context, json=body)

    async def _update_page(self, context: NodeContext) -> Dict:
        """Update page properties."""
        page_id = self._interpolate(self.config["page_id"], context)
        properties = self._interpolate_dict(self.config["properties"], context)

        url = f"{self.BASE_URL}/pages/{page_id}"
        body = {"properties": properties}

        return await self._make_request("PATCH", url, context, json=body)

    async def _query_database(self, context: NodeContext) -> Dict:
        """Query a database with filters and sorts."""
        database_id = self._interpolate(self.config["database_id"], context)
        url = f"{self.BASE_URL}/databases/{database_id}/query"

        body = {}
        if "filter" in self.config:
            body["filter"] = self.config["filter"]
        if "sorts" in self.config:
            body["sorts"] = self.config["sorts"]
        if "page_size" in self.config:
            body["page_size"] = self.config["page_size"]

        return await self._make_request("POST", url, context, json=body)

    async def _get_database(self, context: NodeContext) -> Dict:
        """Get database metadata."""
        database_id = self._interpolate(self.config["database_id"], context)
        url = f"{self.BASE_URL}/databases/{database_id}"

        return await self._make_request("GET", url, context)

    async def _get_block_children(self, context: NodeContext) -> Dict:
        """Get children blocks of a block/page."""
        block_id = self._interpolate(self.config["block_id"], context)
        url = f"{self.BASE_URL}/blocks/{block_id}/children"

        return await self._make_request("GET", url, context)

    async def _make_request(
        self, method: str, url: str, context: NodeContext, json: Optional[Dict] = None
    ) -> Dict:
        """Make authenticated request to Notion API."""
        api_key = self._interpolate(self.config["api_key"], context)

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Notion-Version": self.NOTION_VERSION,
            "Content-Type": "application/json",
        }

        async with aiohttp.ClientSession() as session:
            async with session.request(
                method=method, url=url, headers=headers, json=json, timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status >= 400:
                    error_body = await response.text()
                    raise Exception(f"Notion API error {response.status}: {error_body}")

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

    def _interpolate_dict(self, d: Dict, context: NodeContext) -> Dict:
        """Recursively interpolate dict values."""
        result = {}
        for key, val in d.items():
            if isinstance(val, str):
                result[key] = self._interpolate(val, context)
            elif isinstance(val, dict):
                result[key] = self._interpolate_dict(val, context)
            elif isinstance(val, list):
                result[key] = [
                    self._interpolate_dict(item, context) if isinstance(item, dict) else item
                    for item in val
                ]
            else:
                result[key] = val
        return result
