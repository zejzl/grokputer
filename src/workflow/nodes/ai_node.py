"""
AI Node for GG Workflow Framework

Integrates AI reasoning into workflows using Grok, Claude, or other providers.
Can make decisions, generate content, analyze data, or invoke Pantheon agents.

Author: Grokputer Team
Date: 2025-11-16
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from .base import BaseNode, NodeContext


class AINode(BaseNode):
    """
    Node for AI-powered operations, backed by the real `src.grok_client.GrokClient`.

    This node can make decisions based on context data, generate content (text, code, ...) and
    analyze or extract insights. Each call goes to one provider and records its token usage under
    the agent tag "workflow:<node_id>".

    Configuration:
        provider: "grok" (default), "claude", "claude-cli", "gemini" or "openai". The provider's API
            key must be in the environment (claude-cli needs the `claude` CLI logged in).
        model: Optional model name. Omitted means the provider's default (GROK_MODEL, CLAUDE_MODEL, ...).
        prompt: Prompt template (can use {{variables}})
        system_prompt: Optional system prompt
        temperature: Sampling temperature (default 0.7; ignored by claude-cli)
        max_tokens: Maximum tokens to generate (default 2000; ignored by claude-cli)
        output_format: Expected output format ("text", "json", "decision")

    Not supported here (rejected when the node is created):
        provider "maf": MAF returns consensus metadata rather than a reply; use `main.py --providers`.
        pantheon_agent: use PantheonNode (src/workflow/pantheon_integration.py) to delegate to an agent.

    Example:
        node = AINode(
            "classify_urgency",
            config={
                "provider": "claude",
                "model": "claude-haiku-5-5",
                "prompt": "Classify urgency of: {{message}}. Reply with: low, medium, or high",
                "output_format": "text"
            }
        )
    """

    def __init__(self, node_id: str, name: Optional[str] = None, config: Optional[Dict] = None):
        super().__init__(node_id, name, config)

        # Validate config
        if "pantheon_agent" in self.config:
            raise ValueError(f"AINode {node_id}: 'pantheon_agent' is not supported by AINode; use PantheonNode")
        if self.config.get("provider") == "maf":
            raise ValueError(
                f"AINode {node_id}: provider 'maf' is not supported by AINode (MAF returns consensus metadata, "
                "not a reply); run MAF with `main.py --providers` or pick a single provider"
            )
        if not self.config.get("prompt"):
            raise ValueError(f"AINode {node_id} requires 'prompt' in config")

        self._used_model: Optional[str] = None  # model that answered the last call

        # Set defaults (no default model: None means the provider's own default)
        self.config.setdefault("provider", "grok")
        self.config.setdefault("temperature", 0.7)
        self.config.setdefault("max_tokens", 2000)
        self.config.setdefault("output_format", "text")

    async def execute(self, context: NodeContext) -> NodeContext:
        """
        Execute AI operation.

        Args:
            context: Input context

        Returns:
            Output context with AI response
        """
        result = await self._invoke_provider(context)

        # Parse output based on format
        output_format = self.config["output_format"]
        parsed_result = self._parse_output(result, output_format)

        # Create output context
        output_context = NodeContext(
            data={
                "ai_response": parsed_result,
                "raw_response": result,
                "provider": self.config["provider"],
                "model": self._used_model or self.config.get("model"),
            },
            metadata=context.metadata,
            state=context.state,
        )

        # Store in state for reference
        output_context.set_state(f"{self.node_id}_response", parsed_result)

        return output_context

    async def _invoke_provider(self, context: NodeContext) -> str:
        """Send the prompt to the configured provider through GrokClient and return the reply text."""
        from src.grok_client import GrokClient

        prompt = self._interpolate(self.config["prompt"], context)
        system_prompt = self._interpolate(self.config.get("system_prompt", ""), context)

        # Raises ValueError for an unknown provider or a missing API key
        client = GrokClient(provider=self.config["provider"])
        try:
            provider = client.providers[0]
            if self.config.get("model"):
                provider.model = self.config["model"]
            provider.temperature = self.config["temperature"]
            provider.max_tokens = self.config["max_tokens"]

            history = [{"role": "system", "content": system_prompt}] if system_prompt else None
            response = await client.create_message(
                prompt, conversation_history=history, agent=f"workflow:{self.node_id}"
            )
        finally:
            await client.close()

        if response.get("status") != "success":
            raise RuntimeError(
                f"AINode {self.node_id}: {self.config['provider']} call failed: "
                f"{response.get('error') or 'no content returned'}"
            )
        self._used_model = response.get("model")
        return response["content"]

    def _parse_output(self, result: str, output_format: str) -> Any:
        """Parse AI output based on expected format."""
        if output_format == "text":
            return result.strip()

        elif output_format == "json":
            # Try to extract JSON from response
            import re

            json_match = re.search(r"\{.*\}", result, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                raise ValueError(f"Could not extract JSON from response: {result[:100]}...")

        elif output_format == "decision":
            # Extract boolean decision
            result_lower = result.lower().strip()
            if "yes" in result_lower or "true" in result_lower or "proceed" in result_lower:
                return True
            elif "no" in result_lower or "false" in result_lower or "stop" in result_lower:
                return False
            else:
                raise ValueError(f"Could not parse decision from response: {result[:100]}...")

        else:
            return result

    def _interpolate(self, value: str, context: NodeContext) -> str:
        """Replace {{variable}} placeholders with values from context."""
        if not value:
            return value

        result = value
        for key, val in context.data.items():
            placeholder = f"{{{{{key}}}}}"
            if placeholder in result:
                # Convert to JSON if complex type
                if isinstance(val, (dict, list)):
                    val_str = json.dumps(val, indent=2)
                else:
                    val_str = str(val)
                result = result.replace(placeholder, val_str)

        # Also check state
        for key, val in context.state.items():
            placeholder = f"{{{{{key}}}}}"
            if placeholder in result:
                if isinstance(val, (dict, list)):
                    val_str = json.dumps(val, indent=2)
                else:
                    val_str = str(val)
                result = result.replace(placeholder, val_str)

        return result
