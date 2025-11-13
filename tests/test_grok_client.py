import pytest
from unittest.mock import AsyncMock, patch
from src.grok_client import GrokClient


class TestGrokClient:
    @pytest.mark.asyncio
    async def test_create_message(self):
        """Test message creation."""
        client = GrokClient()

        with patch("openai.AsyncOpenAI") as mock_openai:
            mock_client = AsyncMock()
            mock_openai.return_value = mock_client

            mock_response = AsyncMock()
            mock_response.choices = [AsyncMock()]
            mock_response.choices[0].message.content = "Test response"
            mock_client.chat.completions.create.return_value = mock_response

            message = await client.create_message("test prompt")

            assert "content" in message
            assert "role" in message
            assert message["role"] == "user"

    @pytest.mark.asyncio
    async def test_continue_conversation(self):
        """Test conversation continuation with mock API."""
        client = GrokClient()

        messages = [{"role": "user", "content": "Hello"}]
        conversation_history = []

        with patch("openai.AsyncOpenAI") as mock_openai:
            mock_client = AsyncMock()
            mock_openai.return_value = mock_client

            mock_response = AsyncMock()
            mock_response.choices = [AsyncMock()]
            mock_response.choices[0].message.content = "Hi there!"
            mock_client.chat.completions.create.return_value = mock_response

            response = await client.continue_conversation(messages, conversation_history)

            assert response == "Hi there!"
            mock_client.chat.completions.create.assert_called_once()

    def test_initialization(self):
        """Test client initialization."""
        client = GrokClient()

        assert client.model == "grok-4-fast-reasoning"
        assert "api.x.ai" in client.base_url
