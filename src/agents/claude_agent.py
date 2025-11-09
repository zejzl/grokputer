"""
Claude API wrapper for collaboration mode.
"""

import asyncio
from typing import List
from anthropic import AsyncAnthropic
from tenacity import retry, stop_after_attempt, wait_exponential
import logging

from src.agents.base_llm_agent import BaseLLMAgent
from src.collaboration.message_models import CollaborationMessage, AgentRole

logger = logging.getLogger(__name__)


class ClaudeAgent(BaseLLMAgent):
    """Claude API wrapper for collaboration mode."""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-5-20250929",
        max_retries: int = 3,
        timeout: float = 30.0
    ):
        """
        Initialize Claude agent.

        Args:
            api_key: Anthropic API key
            model: Claude model identifier
            max_retries: Maximum retry attempts
            timeout: API timeout in seconds
        """
        super().__init__(
            role=AgentRole.CLAUDE,
            model=model,
            api_key=api_key,
            max_retries=max_retries,
            timeout=timeout
        )

        self.client = AsyncAnthropic(api_key=api_key)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    async def call_api(
        self,
        messages: List[dict],
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs
    ) -> dict:
        """
        Call Claude API with retry logic.

        Args:
            messages: List of message dicts in Anthropic format
            max_tokens: Maximum response tokens
            temperature: Sampling temperature
            **kwargs: Additional API parameters

        Returns:
            API response dict with keys: content, model, usage, stop_reason
        """
        try:
            response = await asyncio.wait_for(
                self.client.messages.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    **kwargs
                ),
                timeout=self.timeout
            )

            return {
                "content": response.content[0].text,
                "model": response.model,
                "usage": {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens
                },
                "stop_reason": response.stop_reason
            }

        except asyncio.TimeoutError:
            logger.error(f"Claude API timeout after {self.timeout}s")
            raise
        except Exception as e:
            logger.error(f"Claude API error: {e}")
            raise

    async def generate_response(
        self,
        prompt: str,
        context: List[CollaborationMessage],
        round_number: int
    ) -> str:
        """
        Generate Claude's response in collaboration.

        Constructs a system prompt that encourages:
        - Respectful collaboration with Grok
        - Structured, markdown-formatted responses
        - Explicit consensus/disagreement signals

        Args:
            prompt: Original user task/prompt
            context: Previous messages in this collaboration
            round_number: Current conversation round (1-indexed)

        Returns:
            Generated response text (markdown format)
        """
        # Build system prompt
        system_prompt = self._build_collaboration_system_prompt(prompt, round_number)

        # Build message history
        messages = self._build_message_history(context)

        # Call API
        response = await self.call_api(
            messages=messages,
            max_tokens=2048,
            temperature=0.7,
            system=system_prompt
        )

        return response["content"]

    def _build_collaboration_system_prompt(self, original_prompt: str, round_number: int) -> str:
        """Build system prompt for collaboration context."""

        base_prompt = f"""You are Claude, collaborating with Grok (xAI's LLM) to solve the following task:

**Task**: {original_prompt}

**Your Role**:
- Provide thoughtful, structured analysis and implementation plans
- Engage respectfully with Grok's ideas
- Highlight areas of agreement and disagreement explicitly
- Use markdown formatting for clarity
- Signal consensus clearly when reached (use phrases like "I agree with Grok's approach")

**Current Round**: {round_number}/5

**Guidelines**:
1. If this is Round 1, propose your initial ideas
2. If this is Round 2+, respond to Grok's previous messages
3. Be concise but thorough (aim for 200-400 words)
4. Structure your response with clear headings
5. End with explicit next steps or consensus statement

Remember: The goal is to create a unified implementation plan that leverages both your perspectives."""

        return base_prompt

    def _build_message_history(self, context: List[CollaborationMessage]) -> List[dict]:
        """Convert CollaborationMessage history to Anthropic message format."""

        messages = []

        for msg in context:
            role = "assistant" if msg.sender == self.role else "user"

            # Format message with attribution
            content = f"**{msg.sender.value.upper()}** (Round {msg.round_number}):\n\n{msg.content}"

            messages.append({
                "role": role,
                "content": content
            })

        return messages
