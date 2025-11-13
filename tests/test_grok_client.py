import pytest
from unittest.mock import AsyncMock, patch
from src.grok_client import GrokClient


class TestGrokClient:
    @pytest.mark.asyncio
    async def test_chat(self):
        """Test basic chat functionality with mock API."""
        client = GrokClient()

        with patch.object(client, "_call_provider", return_value="Test response") as mock_call:
            messages = [{"role": "user", "content": "test prompt"}]
            response = await client.chat(messages)

            assert response == "Test response"
            mock_call.assert_called_once()

    @pytest.mark.asyncio
    async def test_continue_conversation(self):
        """Test conversation continuation with mock API."""
        client = GrokClient()

        messages = [{"role": "user", "content": "Hello"}]

        with patch.object(client, "_call_provider", return_value="Hi there!") as mock_call:
            response = await client.chat(messages)

            assert response == "Hi there!"
            mock_call.assert_called_once()

    def test_initialization(self):
        """Test client initialization."""
        client = GrokClient()

        assert hasattr(client, "providers")
        assert isinstance(client.providers, list)
        assert len(client.providers) > 0
