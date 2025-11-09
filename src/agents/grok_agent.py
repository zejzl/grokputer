"""
Grok API wrapper for collaboration mode (refactored from grok_client.py).
"""

import asyncio
from typing import List
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential
import logging

from src.agents.base_llm_agent import BaseLLMAgent
from src.collaboration.message_models import CollaborationMessage, AgentRole

logger = logging.getLogger(__name__)


class GrokAgent(BaseLLMAgent):
    """Grok API wrapper for collaboration mode (refactored from grok_client.py)."""

    def __init__(
        self,
        api_key: str,
        model: str = "grok-4-fast-reasoning",
        max_retries: int = 3,
        timeout: float = 30.0
    ):
        """
        Initialize Grok agent.

        Args:
            api_key: xAI API key
            model: Grok model identifier
            max_retries: Maximum retry attempts
            timeout: API timeout in seconds
        """
        super().__init__(
            role=AgentRole.GROK,
            model=model,
            api_key=api_key,
            max_retries=max_retries,
            timeout=timeout
        )

        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://api.x.ai/v1"
        )

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
        Call Grok API with retry logic.

        Args:
            messages: List of message dicts in OpenAI format
            max_tokens: Maximum response tokens
            temperature: Sampling temperature
            **kwargs: Additional API parameters

        Returns:
            API response dict with keys: content, model, usage, finish_reason
        """
        try:
            response = await asyncio.wait_for(
                self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    **kwargs
                ),
                timeout=self.timeout
            )

            return {
                "content": response.choices[0].message.content,
                "model": response.model,
                "usage": {
                    "input_tokens": response.usage.prompt_tokens,
                    "output_tokens": response.usage.completion_tokens
                },
                "finish_reason": response.choices[0].finish_reason
            }

        except asyncio.TimeoutError:
            logger.error(f"Grok API timeout after {self.timeout}s")
            raise
        except Exception as e:
            logger.error(f"Grok API error: {e}")
            raise

    async def generate_response(
        self,
        prompt: str,
        context: List[CollaborationMessage],
        round_number: int
    ) -> str:
        """
        Generate Grok's response in collaboration.

        Args:
            prompt: Original user task/prompt
            context: Previous messages in this collaboration
            round_number: Current conversation round (1-indexed)

        Returns:
            Generated response text (markdown format)
        """
        # Build message history (Grok uses OpenAI-compatible format)
        messages = self._build_message_history(prompt, context, round_number)

        # Call API
        response = await self.call_api(
            messages=messages,
            max_tokens=2048,
            temperature=0.7
        )

        return response["content"]

    def _build_message_history(
        self,
        original_prompt: str,
        context: List[CollaborationMessage],
        round_number: int
    ) -> List[dict]:
        """Build OpenAI-compatible message history."""

        messages = []

        # System message with collaboration context
        system_msg = f"""You are Grok, collaborating with Claude (Anthropic's LLM) to solve the following task:

**Task**: {original_prompt}

**Your Role**:
- Provide practical, implementation-focused analysis
- Engage constructively with Claude's ideas
- Highlight areas of agreement and disagreement explicitly
- Use markdown formatting for clarity
- Signal consensus clearly when reached (use phrases like "I align with Claude on...")

**Current Round**: {round_number}/5

**Guidelines**:
1. If this is Round 1, propose your initial ideas
2. If this is Round 2+, respond to Claude's previous messages
3. Be concise but thorough (aim for 200-400 words)
4. Structure your response with clear headings
5. End with explicit next steps or consensus statement

Goal: Create a unified implementation plan leveraging both perspectives."""

        messages.append({"role": "system", "content": system_msg})

        # Add conversation history
        for msg in context:
            role = "assistant" if msg.sender == self.role else "user"

            # Format with attribution
            content = f"**{msg.sender.value.upper()}** (Round {msg.round_number}):\n\n{msg.content}"

            messages.append({"role": role, "content": content})

        return messages
