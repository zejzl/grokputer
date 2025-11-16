"""
AI Node for GG Workflow Framework

Integrates AI reasoning into workflows using Grok, Claude, or other providers.
Can make decisions, generate content, analyze data, or invoke Pantheon agents.

Author: Grokputer Team
Date: 2025-11-16
"""

import json
from typing import Any, Dict, List, Optional

from .base import BaseNode, NodeContext


class AINode(BaseNode):
    """
    Node for AI-powered operations.

    This node can:
    - Make decisions based on context data
    - Generate content (text, code, etc.)
    - Analyze and extract insights
    - Invoke specific Pantheon agents
    - Use multi-provider consensus (MAF)

    Configuration:
        provider: AI provider ("grok", "claude", "openai", "maf")
        model: Model to use (e.g., "grok-4-fast-reasoning")
        prompt: Prompt template (can use {{variables}})
        system_prompt: Optional system prompt
        temperature: Sampling temperature (0.0 - 1.0)
        max_tokens: Maximum tokens to generate
        output_format: Expected output format ("text", "json", "decision")
        pantheon_agent: Optional agent name to delegate to
        maf_config: Configuration for multi-provider mode

    Example:
        # Simple decision node
        node = AINode(
            "classify_urgency",
            config={
                "provider": "grok",
                "model": "grok-4-fast-reasoning",
                "prompt": "Classify urgency of: {{message}}. Reply with: low, medium, or high",
                "output_format": "text"
            }
        )

        # Pantheon agent delegation
        node = AINode(
            "analyze_screen",
            config={
                "pantheon_agent": "observer",
                "prompt": "Analyze current screen and extract key information"
            }
        )

        # Multi-provider consensus
        node = AINode(
            "critical_decision",
            config={
                "provider": "maf",
                "maf_config": {
                    "providers": ["grok", "claude", "openai"],
                    "consensus_threshold": 0.6
                },
                "prompt": "Should we proceed with: {{action}}?"
            }
        )
    """

    def __init__(self, node_id: str, name: Optional[str] = None, config: Optional[Dict] = None):
        super().__init__(node_id, name, config)

        # Validate config
        if not self.config.get("prompt") and not self.config.get("pantheon_agent"):
            raise ValueError(f"AINode {node_id} requires 'prompt' or 'pantheon_agent' in config")

        # Set defaults
        self.config.setdefault("provider", "grok")
        self.config.setdefault("model", "grok-4-fast-reasoning")
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
        # Check if using Pantheon agent
        if "pantheon_agent" in self.config:
            result = await self._invoke_pantheon_agent(context)
        elif self.config["provider"] == "maf":
            result = await self._invoke_maf(context)
        else:
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
                "model": self.config.get("model"),
            },
            metadata=context.metadata,
            state=context.state,
        )

        # Store in state for reference
        output_context.set_state(f"{self.node_id}_response", parsed_result)

        return output_context

    async def _invoke_provider(self, context: NodeContext) -> str:
        """Invoke a single AI provider."""
        from src.model_client import ModelClient

        # Prepare prompt
        prompt = self._interpolate(self.config["prompt"], context)
        system_prompt = self._interpolate(self.config.get("system_prompt", ""), context)

        # Initialize client
        client = ModelClient(
            provider=self.config["provider"],
            model=self.config["model"],
        )

        # Make API call
        response = await client.create_message_async(
            prompt=prompt,
            system=system_prompt if system_prompt else None,
            temperature=self.config["temperature"],
            max_tokens=self.config["max_tokens"],
        )

        return response

    async def _invoke_maf(self, context: NodeContext) -> str:
        """Invoke Multi-Agent Framework for consensus."""
        from src.collaboration.orchestrator import MultiProviderOrchestrator

        maf_config = self.config["maf_config"]
        prompt = self._interpolate(self.config["prompt"], context)

        # Initialize orchestrator
        orchestrator = MultiProviderOrchestrator(
            providers=maf_config["providers"],
            consensus_threshold=maf_config.get("consensus_threshold", 0.6),
        )

        # Get consensus
        result = await orchestrator.get_consensus(
            task=prompt,
            temperature=self.config["temperature"],
        )

        return result["consensus_response"]

    async def _invoke_pantheon_agent(self, context: NodeContext) -> str:
        """Delegate to a specific Pantheon agent."""
        from src.core.message_bus import MessageBus, Message, MessagePriority

        agent_name = self.config["pantheon_agent"]
        prompt = self._interpolate(self.config["prompt"], context)

        # Get MessageBus instance
        message_bus = MessageBus()

        # Create message for agent
        message = Message(
            id=f"{self.node_id}_request",
            sender="ai_node",
            recipient=agent_name,
            content={
                "task": prompt,
                "context": context.data,
            },
            priority=MessagePriority.MEDIUM,
        )

        # Send and wait for response
        await message_bus.publish(message)

        # Wait for response (with timeout)
        import asyncio

        timeout = self.config.get("agent_timeout", 30)

        try:
            response_message = await asyncio.wait_for(
                message_bus.subscribe(f"{agent_name}_response"), timeout=timeout
            )
            return response_message.content.get("result", "")
        except asyncio.TimeoutError:
            raise Exception(f"Pantheon agent '{agent_name}' timeout after {timeout}s")

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
