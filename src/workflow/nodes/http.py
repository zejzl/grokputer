"""
HTTP Node for GG Workflow Framework

Performs HTTP requests (GET, POST, PUT, DELETE, PATCH) to external APIs.
Supports headers, query params, body, authentication, and retries.

Author: Grokputer Team
Date: 2025-11-16
"""
from __future__ import annotations

import asyncio
import json
from enum import Enum
from typing import Any, Dict, Optional, Union

import aiohttp

from .base import BaseNode, NodeContext


class HTTPMethod(Enum):
    """Supported HTTP methods."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"


class HTTPNode(BaseNode):
    """
    Node for making HTTP requests to external APIs.

    Configuration:
        url: Target URL (can use {{variables}} from context)
        method: HTTP method (GET, POST, PUT, DELETE, PATCH)
        headers: Request headers dict
        query_params: Query parameters dict
        body: Request body (dict or string)
        auth: Authentication config (bearer_token or basic)
        timeout: Request timeout in seconds (default: 30)
        retries: Number of retry attempts (default: 3)
        retry_delay: Delay between retries in seconds (default: 1)
        verify_ssl: Whether to verify SSL certificates (default: True)

    Example:
        node = HTTPNode(
            "fetch_user",
            config={
                "url": "https://api.example.com/users/{{user_id}}",
                "method": "GET",
                "headers": {"Accept": "application/json"},
                "auth": {"bearer_token": "{{api_key}}"}
            }
        )
    """

    def __init__(self, node_id: str, name: Optional[str] = None, config: Optional[Dict] = None):
        super().__init__(node_id, name, config)

        # Validate required config
        if not self.config.get("url"):
            raise ValueError(f"HTTPNode {node_id} requires 'url' in config")

        # Set defaults
        self.config.setdefault("method", "GET")
        self.config.setdefault("timeout", 30)
        self.config.setdefault("retries", 3)
        self.config.setdefault("retry_delay", 1)
        self.config.setdefault("verify_ssl", True)

    async def execute(self, context: NodeContext) -> NodeContext:
        """
        Execute HTTP request.

        Args:
            context: Input context with data

        Returns:
            Output context with response data
        """
        # Interpolate variables in config
        url = self._interpolate(self.config["url"], context)
        method = HTTPMethod[self.config["method"].upper()]
        headers = self._interpolate_dict(self.config.get("headers", {}), context)
        query_params = self._interpolate_dict(self.config.get("query_params", {}), context)
        body = self._interpolate(self.config.get("body"), context)
        timeout = self.config["timeout"]
        retries = self.config["retries"]
        retry_delay = self.config["retry_delay"]
        verify_ssl = self.config["verify_ssl"]

        # Add authentication
        auth_config = self.config.get("auth", {})
        if auth_config:
            headers = self._add_auth(headers, auth_config, context)

        # Make request with retries
        response_data = None
        last_error = None

        for attempt in range(retries + 1):
            try:
                response_data = await self._make_request(
                    method=method.value,
                    url=url,
                    headers=headers,
                    params=query_params,
                    body=body,
                    timeout=timeout,
                    verify_ssl=verify_ssl,
                )
                break  # Success

            except Exception as e:
                last_error = e
                if attempt < retries:
                    await asyncio.sleep(retry_delay)
                    continue
                else:
                    # All retries exhausted
                    raise Exception(
                        f"HTTP request failed after {retries + 1} attempts: {str(e)}"
                    ) from e

        # Store response in context
        output_context = NodeContext(
            data={
                "status_code": response_data["status"],
                "headers": response_data["headers"],
                "body": response_data["body"],
                "url": url,
                "method": method.value,
            },
            metadata=context.metadata,
            state=context.state,
        )

        # Also preserve previous data
        output_context.set_state(f"{self.node_id}_response", response_data)

        return output_context

    async def _make_request(
        self,
        method: str,
        url: str,
        headers: Dict,
        params: Dict,
        body: Optional[Union[str, Dict]],
        timeout: int,
        verify_ssl: bool,
    ) -> Dict:
        """Make the actual HTTP request."""
        async with aiohttp.ClientSession() as session:
            # Prepare body
            json_body = None
            data_body = None

            if body:
                if isinstance(body, dict):
                    json_body = body
                    headers.setdefault("Content-Type", "application/json")
                else:
                    data_body = body

            # Make request
            async with session.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=json_body,
                data=data_body,
                timeout=aiohttp.ClientTimeout(total=timeout),
                ssl=verify_ssl,
            ) as response:
                # Parse response body
                content_type = response.headers.get("Content-Type", "")

                if "application/json" in content_type:
                    body_data = await response.json()
                else:
                    body_data = await response.text()

                return {
                    "status": response.status,
                    "headers": dict(response.headers),
                    "body": body_data,
                }

    def _interpolate(self, value: Any, context: NodeContext) -> Any:
        """Replace {{variable}} placeholders with values from context."""
        if not isinstance(value, str):
            return value

        # Simple template replacement
        result = value
        for key, val in context.data.items():
            placeholder = f"{{{{{key}}}}}"
            if placeholder in result:
                result = result.replace(placeholder, str(val))

        # Also check state
        for key, val in context.state.items():
            placeholder = f"{{{{{key}}}}}"
            if placeholder in result:
                result = result.replace(placeholder, str(val))

        return result

    def _interpolate_dict(self, d: Dict, context: NodeContext) -> Dict:
        """Interpolate all values in a dictionary."""
        return {key: self._interpolate(val, context) for key, val in d.items()}

    def _add_auth(self, headers: Dict, auth_config: Dict, context: NodeContext) -> Dict:
        """Add authentication to headers."""
        headers = headers.copy()

        # Bearer token
        if "bearer_token" in auth_config:
            token = self._interpolate(auth_config["bearer_token"], context)
            headers["Authorization"] = f"Bearer {token}"

        # Basic auth
        elif "basic" in auth_config:
            basic = auth_config["basic"]
            username = self._interpolate(basic.get("username", ""), context)
            password = self._interpolate(basic.get("password", ""), context)

            import base64

            credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
            headers["Authorization"] = f"Basic {credentials}"

        # API key in header
        elif "api_key" in auth_config:
            key_name = auth_config.get("api_key_name", "X-API-Key")
            key_value = self._interpolate(auth_config["api_key"], context)
            headers[key_name] = key_value

        return headers
