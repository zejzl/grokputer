"""
Cline API client wrapper for Grokputer.
Uses Anthropic's Claude API for Cline (Claude-based assistant).

Async-ready for multi-agent swarm operations.
"""

import logging
from typing import List, Dict, Any, Optional
from anthropic import AsyncAnthropic
from src import config

logger = logging.getLogger(__name__)


class ClineClient:
    """
    Async wrapper for Anthropic's Claude API for Cline.

    All methods are async to enable parallel API calls in multi-agent swarms.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None
    ):
        """
        Initialize the Cline client.

        Args:
            api_key: Anthropic API key (defaults to config.CLAUDE_API_KEY)
            model: Model name (defaults to config.CLINE_MODEL)
        """
        self.api_key = api_key or config.CLAUDE_API_KEY
        self.model = model or config.CLINE_MODEL

        # Initialize AsyncAnthropic client
        self.client = AsyncAnthropic(api_key=self.api_key)

        logger.info(f"Initialized async Cline client: model={self.model}")

    async def create_message(
        self,
        task: str,
        screenshot_base64: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Send a message to Cline with optional screenshot and get a response (async).

        Args:
            task: The task description/prompt
            screenshot_base64: Base64-encoded screenshot (optional)
            conversation_history: Previous conversation messages (optional)

        Returns:
            Response from Cline API
        """
        try:
            messages = []

            # Add conversation history if provided
            if conversation_history:
                messages.extend(conversation_history)

            # Build user message
            user_content = [{"type": "text", "text": f"Task: {task}"}]

            # Add screenshot if provided (Claude supports image content)
            if screenshot_base64:
                user_content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",  # Assuming PNG screenshot
                        "data": screenshot_base64
                    }
                })

            messages.append({
                "role": "user",
                "content": user_content
            })

            logger.info(f"Sending async message to Cline: task='{task[:50]}...'")

            # Make async API call
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=config.SYSTEM_PROMPT,
                messages=messages,
                tools=config.TOOLS if config.TOOLS else []
            )

            logger.info(f"Received response from Cline: {response.id}")

            return self._parse_response(response)

        except Exception as e:
            logger.error(f"Error calling Cline API: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    def _parse_response(self, response: Any) -> Dict[str, Any]:
        """
        Parse the API response into a standardized format.

        Args:
            response: Raw API response

        Returns:
            Parsed response dictionary
        """
        try:
            message = response.content[0]

            result = {
                "status": "success",
                "response_id": response.id,
                "model": response.model,
                "finish_reason": response.stop_reason,
                "content": None,
                "tool_calls": []
            }

            # Extract content if text
            if hasattr(message, 'type') and message.type == 'text':
                result["content"] = message.text

            # Parse tool calls if present
            if hasattr(response, 'content') and len(response.content) > 1:
                for block in response.content[1:]:
                    if hasattr(block, 'type') and block.type == 'tool_use':
                        result["tool_calls"].append({
                            "id": block.id,
                            "type": "function",
                            "function": {
                                "name": block.name,
                                "arguments": str(block.input) if block.input else "{}"
                            }
                        })

            logger.info(f"Cline requested {len(result['tool_calls'])} tool calls")

            return result

        except Exception as e:
            logger.error(f"Error parsing Cline response: {e}")
            return {
                "status": "error",
                "error": f"Failed to parse response: {e}"
            }

    async def continue_conversation(
        self,
        tool_results: List[Dict[str, Any]],
        conversation_history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Continue the conversation after tool execution (async).

        Args:
            tool_results: Results from executed tools
            conversation_history: Previous conversation messages

        Returns:
            Next response from Cline
        """
        try:
            messages = conversation_history.copy()

            # Add tool results as user messages (since Claude expects tool results in user role)
            for result in tool_results:
                messages.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": result.get("tool_call_id", ""),
                        "content": str(result.get("result", ""))
                    }]
                })

            logger.info(f"Continuing conversation with {len(tool_results)} tool results")

            # Make async API call
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=config.SYSTEM_PROMPT,
                messages=messages,
                tools=config.TOOLS if config.TOOLS else []
            )

            return self._parse_response(response)

        except Exception as e:
            logger.error(f"Error continuing conversation: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    async def test_connection(self) -> bool:
        """
        Test the connection to Cline API (async).

        Returns:
            True if connection is successful, False otherwise
        """
        try:
            logger.info("Testing Cline API connection...")

            # Make async API call
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=50,
                messages=[
                    {"role": "user", "content": "Hello, Cline. This is a connection test."}
                ]
            )

            logger.info("Cline API connection successful")
            return True

        except Exception as e:
            logger.error(f"Cline API connection failed: {e}")
            return False
