"""
Abstract base class for LLM agents in collaboration mode.
"""

from abc import ABC, abstractmethod
from typing import List
import logging

from src.collaboration.message_models import CollaborationMessage, AgentRole, MessageType

logger = logging.getLogger(__name__)


class BaseLLMAgent(ABC):
    """Abstract base class for LLM agents in collaboration mode."""

    def __init__(
        self,
        role: AgentRole,
        model: str,
        api_key: str,
        max_retries: int = 3,
        timeout: float = 30.0
    ):
        """
        Initialize base agent.

        Args:
            role: Agent role (CLAUDE or GROK)
            model: Model identifier
            api_key: API key for the service
            max_retries: Maximum retry attempts
            timeout: API timeout in seconds
        """
        self.role = role
        self.model = model
        self.api_key = api_key
        self.max_retries = max_retries
        self.timeout = timeout

        # Message history for context
        self.message_history: List[CollaborationMessage] = []

        logger.info(f"Initialized {role.value} agent with model {model}")

    @abstractmethod
    async def generate_response(
        self,
        prompt: str,
        context: List[CollaborationMessage],
        round_number: int
    ) -> str:
        """
        Generate a response given the current context.

        Args:
            prompt: Original user task/prompt
            context: Previous messages in this collaboration
            round_number: Current conversation round (1-indexed)

        Returns:
            Generated response text (markdown format)
        """
        pass

    @abstractmethod
    async def call_api(
        self,
        messages: List[dict],
        **kwargs
    ) -> dict:
        """
        Call the underlying LLM API.

        Args:
            messages: List of message dicts (OpenAI/Anthropic format)
            **kwargs: Additional API parameters

        Returns:
            API response dict with keys: content, model, usage
        """
        pass

    def add_to_history(self, message: CollaborationMessage) -> None:
        """Add message to context history."""
        self.message_history.append(message)
        logger.debug(f"{self.role.value}: Added message {message.message_id} to history")

    def get_context_window(self, max_messages: int = 10) -> List[CollaborationMessage]:
        """
        Get recent context for next API call.

        Args:
            max_messages: Maximum number of recent messages to return

        Returns:
            List of recent CollaborationMessages
        """
        return self.message_history[-max_messages:]

    async def process_message(
        self,
        message: CollaborationMessage,
        original_prompt: str
    ) -> CollaborationMessage:
        """
        Process incoming message and generate response.

        This is the main entry point for agent participation.

        Args:
            message: Incoming message (trigger or feedback)
            original_prompt: Original user task

        Returns:
            Response message
        """
        logger.info(
            f"{self.role.value}: Processing message {message.message_id} "
            f"(round {message.round_number})"
        )

        # Add received message to history
        self.add_to_history(message)

        # Generate response with full context
        context = self.get_context_window()

        try:
            response_text = await self.generate_response(
                prompt=original_prompt,
                context=context,
                round_number=message.round_number
            )
        except Exception as e:
            logger.error(f"{self.role.value}: Failed to generate response: {e}")
            raise

        # Create response message
        response_msg = CollaborationMessage(
            message_id=f"msg_{message.round_number:03d}_{self.role.value}",
            correlation_id=message.correlation_id,
            message_type=MessageType.FEEDBACK if message.round_number > 1 else MessageType.PROPOSAL,
            sender=self.role,
            recipient=None,  # Broadcast
            round_number=message.round_number,
            content=response_text,
            in_reply_to=message.message_id if message.round_number > 1 else None
        )

        logger.info(f"{self.role.value}: Generated response {response_msg.message_id}")

        return response_msg
