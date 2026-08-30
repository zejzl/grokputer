"""
Slack Node for GG Workflow Framework

Integrates with Slack API for sending messages, notifications, and managing channels.
Supports operations like send message, upload file, create channel, add reaction.

Author: Grokputer Team
Date: 2025-11-16
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import aiohttp

from .base import BaseNode, NodeContext


class SlackNode(BaseNode):
    """
    Node for Slack API operations.

    Configuration:
        bot_token: Slack bot token (or use {{SLACK_BOT_TOKEN}})
        operation: Operation type (send_message, upload_file, create_channel, etc.)
        channel: Channel ID or name (e.g., "#general", "C1234567890")
        text: Message text (for send_message)
        blocks: Rich message blocks (optional, for advanced formatting)
        thread_ts: Thread timestamp (to reply in thread)
        file_path: Path to file (for upload_file)
        initial_comment: Comment for uploaded file

    Example:
        # Send simple message
        node = SlackNode(
            "notify_slack",
            config={
                "bot_token": "{{SLACK_BOT_TOKEN}}",
                "operation": "send_message",
                "channel": "#alerts",
                "text": "New task created: {{task_name}}"
            }
        )

        # Send rich message with blocks
        node = SlackNode(
            "send_alert",
            config={
                "bot_token": "{{SLACK_BOT_TOKEN}}",
                "operation": "send_message",
                "channel": "C1234567890",
                "text": "Alert",
                "blocks": [
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": "*Alert:* {{message}}"}
                    }
                ]
            }
        )

        # Upload file
        node = SlackNode(
            "upload_report",
            config={
                "bot_token": "{{SLACK_BOT_TOKEN}}",
                "operation": "upload_file",
                "channel": "#reports",
                "file_path": "{{report_path}}",
                "initial_comment": "Daily report: {{date}}"
            }
        )
    """

    BASE_URL = "https://slack.com/api"

    def __init__(self, node_id: str, name: Optional[str] = None, config: Optional[Dict] = None):
        super().__init__(node_id, name, config)

        # Validate required config
        if not self.config.get("bot_token"):
            raise ValueError(f"SlackNode {node_id} requires 'bot_token' in config")
        if not self.config.get("operation"):
            raise ValueError(f"SlackNode {node_id} requires 'operation' in config")

    async def execute(self, context: NodeContext) -> NodeContext:
        """
        Execute Slack operation.

        Args:
            context: Input context

        Returns:
            Output context with Slack response
        """
        operation = self.config["operation"]

        # Dispatch to operation handler
        if operation == "send_message":
            result = await self._send_message(context)
        elif operation == "upload_file":
            result = await self._upload_file(context)
        elif operation == "create_channel":
            result = await self._create_channel(context)
        elif operation == "add_reaction":
            result = await self._add_reaction(context)
        elif operation == "get_channel_info":
            result = await self._get_channel_info(context)
        elif operation == "list_channels":
            result = await self._list_channels(context)
        else:
            raise ValueError(f"Unknown Slack operation: {operation}")

        # Create output context
        output_context = NodeContext(
            data={
                "slack_response": result,
                "operation": operation,
            },
            metadata=context.metadata,
            state=context.state,
        )

        # Store in state
        output_context.set_state(f"{self.node_id}_response", result)

        return output_context

    async def _send_message(self, context: NodeContext) -> Dict:
        """Send a message to a channel."""
        url = f"{self.BASE_URL}/chat.postMessage"

        # Build message payload
        payload = {
            "channel": self._interpolate(self.config["channel"], context),
            "text": self._interpolate(self.config["text"], context),
        }

        # Add optional fields
        if "blocks" in self.config:
            payload["blocks"] = self._interpolate_dict(self.config["blocks"], context)

        if "thread_ts" in self.config:
            payload["thread_ts"] = self._interpolate(self.config["thread_ts"], context)

        if "username" in self.config:
            payload["username"] = self._interpolate(self.config["username"], context)

        if "icon_emoji" in self.config:
            payload["icon_emoji"] = self.config["icon_emoji"]

        return await self._make_request("POST", url, context, json=payload)

    async def _upload_file(self, context: NodeContext) -> Dict:
        """Upload a file to a channel."""
        url = f"{self.BASE_URL}/files.upload"

        # Get file content
        file_path = self._interpolate(self.config["file_path"], context)

        # Read file
        try:
            with open(file_path, "rb") as f:
                file_content = f.read()
        except Exception as e:
            raise Exception(f"Failed to read file {file_path}: {str(e)}")

        # Build form data
        data = aiohttp.FormData()
        data.add_field("channels", self._interpolate(self.config["channel"], context))
        data.add_field("file", file_content, filename=file_path.split("/")[-1])

        if "initial_comment" in self.config:
            data.add_field(
                "initial_comment", self._interpolate(self.config["initial_comment"], context)
            )

        if "title" in self.config:
            data.add_field("title", self._interpolate(self.config["title"], context))

        return await self._make_request("POST", url, context, data=data)

    async def _create_channel(self, context: NodeContext) -> Dict:
        """Create a new channel."""
        url = f"{self.BASE_URL}/conversations.create"

        payload = {
            "name": self._interpolate(self.config["channel_name"], context),
        }

        if "is_private" in self.config:
            payload["is_private"] = self.config["is_private"]

        return await self._make_request("POST", url, context, json=payload)

    async def _add_reaction(self, context: NodeContext) -> Dict:
        """Add emoji reaction to a message."""
        url = f"{self.BASE_URL}/reactions.add"

        payload = {
            "channel": self._interpolate(self.config["channel"], context),
            "timestamp": self._interpolate(self.config["timestamp"], context),
            "name": self.config["emoji"],  # e.g., "thumbsup", "fire"
        }

        return await self._make_request("POST", url, context, json=payload)

    async def _get_channel_info(self, context: NodeContext) -> Dict:
        """Get information about a channel."""
        url = f"{self.BASE_URL}/conversations.info"

        params = {
            "channel": self._interpolate(self.config["channel"], context),
        }

        return await self._make_request("GET", url, context, params=params)

    async def _list_channels(self, context: NodeContext) -> Dict:
        """List all channels."""
        url = f"{self.BASE_URL}/conversations.list"

        params = {
            "types": self.config.get("types", "public_channel,private_channel"),
            "limit": self.config.get("limit", 100),
        }

        return await self._make_request("GET", url, context, params=params)

    async def _make_request(
        self,
        method: str,
        url: str,
        context: NodeContext,
        json: Optional[Dict] = None,
        params: Optional[Dict] = None,
        data: Optional[aiohttp.FormData] = None,
    ) -> Dict:
        """Make authenticated request to Slack API."""
        bot_token = self._interpolate(self.config["bot_token"], context)

        headers = {
            "Authorization": f"Bearer {bot_token}",
        }

        if json is not None:
            headers["Content-Type"] = "application/json"

        async with aiohttp.ClientSession() as session:
            async with session.request(
                method=method,
                url=url,
                headers=headers,
                json=json,
                params=params,
                data=data,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                result = await response.json()

                # Check for Slack API errors
                if not result.get("ok"):
                    error = result.get("error", "Unknown error")
                    raise Exception(f"Slack API error: {error}")

                return result

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

    def _interpolate_dict(self, data: Any, context: NodeContext) -> Any:
        """Recursively interpolate dict/list values."""
        if isinstance(data, str):
            return self._interpolate(data, context)
        elif isinstance(data, dict):
            return {key: self._interpolate_dict(val, context) for key, val in data.items()}
        elif isinstance(data, list):
            return [self._interpolate_dict(item, context) for item in data]
        else:
            return data
