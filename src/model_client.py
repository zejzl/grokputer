"""
Unified Model Client for Grokputer - Multi-Provider AI Support

Supports multiple AI providers:
- xAI (Grok)
- OpenAI (GPT models)
- Anthropic (Claude)
- Local models (Ollama, etc.)

Enables seamless switching between models for maximum flexibility.
"""
from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ModelClient(ABC):
    """Abstract base class for AI model clients."""

    def __init__(self, api_key: str, model: str, **kwargs):
        self.api_key = api_key
        self.model = model
        self.client = None
        self._initialize_client(**kwargs)

    @abstractmethod
    def _initialize_client(self, **kwargs):
        """Initialize the specific client."""
        pass

    @abstractmethod
    async def create_message(
        self, task: str, conversation_history: Optional[List[Dict]] = None, **kwargs
    ) -> Dict[str, Any]:
        """Create a message with the AI model."""
        pass

    @abstractmethod
    async def get_available_models(self) -> List[str]:
        """Get list of available models for this provider."""
        pass


class GrokClient(ModelClient):
    """xAI Grok client."""

    def _initialize_client(self, base_url: str = "https://api.x.ai/v1", **kwargs):
        try:
            from openai import AsyncOpenAI

            self.client = AsyncOpenAI(api_key=self.api_key, base_url=base_url)
        except ImportError:
            logger.error("OpenAI package required for Grok client")
            raise

    async def create_message(
        self, task: str, conversation_history: Optional[List[Dict]] = None, **kwargs
    ) -> Dict[str, Any]:
        try:
            messages = []
            if conversation_history:
                messages.extend(conversation_history)
            messages.append({"role": "user", "content": task})

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=kwargs.get("temperature", 0.7),
                max_tokens=kwargs.get("max_tokens", 4096),
            )

            return {
                "status": "success",
                "content": response.choices[0].message.content,
                "usage": response.usage.model_dump() if response.usage else None,
            }
        except Exception as e:
            logger.error(f"Grok API error: {e}")
            return {"status": "error", "error": str(e)}

    async def get_available_models(self) -> List[str]:
        # xAI models are limited, return known ones
        return ["grok-beta", "grok-vision-beta"]

    async def test_connection(self) -> bool:
        """Test connection to Grok API."""
        if not self.api_key:
            return False
        try:
            # Make a simple test call
            response = await self.client.chat.completions.create(
                model=self.model, messages=[{"role": "user", "content": "Hello"}], max_tokens=10
            )
            return True
        except Exception as e:
            logger.error(f"Grok API test failed: {e}")
            return False


class OpenAIClient(ModelClient):
    """OpenAI GPT client."""

    def _initialize_client(self, **kwargs):
        try:
            from openai import AsyncOpenAI

            self.client = AsyncOpenAI(api_key=self.api_key)
        except ImportError:
            logger.error("OpenAI package required")
            raise

    async def create_message(
        self, task: str, conversation_history: Optional[List[Dict]] = None, **kwargs
    ) -> Dict[str, Any]:
        try:
            messages = []
            if conversation_history:
                messages.extend(conversation_history)
            messages.append({"role": "user", "content": task})

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=kwargs.get("temperature", 0.7),
                max_tokens=kwargs.get("max_tokens", 4096),
            )

            return {
                "status": "success",
                "content": response.choices[0].message.content,
                "usage": response.usage.model_dump() if response.usage else None,
            }
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return {"status": "error", "error": str(e)}

    async def get_available_models(self) -> List[str]:
        try:
            models = await self.client.models.list()
            return [m.id for m in models.data if m.id.startswith("gpt")]
        except Exception as e:
            logger.error(f"Failed to get OpenAI models: {e}")
            return ["gpt-4", "gpt-3.5-turbo", "gpt-4-turbo"]


class ClaudeClient(ModelClient):
    """Anthropic Claude client."""

    def _initialize_client(self, **kwargs):
        try:
            import anthropic

            self.client = anthropic.AsyncAnthropic(api_key=self.api_key)
        except ImportError:
            logger.error("Anthropic package required for Claude client")
            raise

    async def create_message(
        self, task: str, conversation_history: Optional[List[Dict]] = None, **kwargs
    ) -> Dict[str, Any]:
        try:
            messages = []
            if conversation_history:
                # Convert to Claude format if needed
                for msg in conversation_history:
                    if msg["role"] == "assistant":
                        messages.append({"role": "assistant", "content": msg["content"]})
                    elif msg["role"] == "user":
                        messages.append({"role": "user", "content": msg["content"]})
            messages.append({"role": "user", "content": task})

            response = await self.client.messages.create(
                model=self.model,
                max_tokens=kwargs.get("max_tokens", 4096),
                temperature=kwargs.get("temperature", 0.7),
                messages=messages,
            )

            return {
                "status": "success",
                "content": response.content[0].text,
                "usage": {"input_tokens": response.usage.input_tokens, "output_tokens": response.usage.output_tokens},
            }
        except Exception as e:
            logger.error(f"Claude API error: {e}")
            return {"status": "error", "error": str(e)}

    async def get_available_models(self) -> List[str]:
        # Claude models are known, return current ones
        return [
            "claude-sonnet-4-5-20250929",  # Claude Sonnet 4.5 (newest)
            "claude-3-5-sonnet-20241022",  # Claude 3.5 Sonnet v2
            "claude-3-5-sonnet-20240620",  # Claude 3.5 Sonnet v1
            "claude-3-opus-20240229",  # Claude 3 Opus
            "claude-3-sonnet-20240229",  # Claude 3 Sonnet
            "claude-3-haiku-20240307",  # Claude 3 Haiku
        ]

    async def test_connection(self) -> bool:
        """Test connection to Claude API."""
        return bool(self.api_key)


class OllamaClient(ModelClient):
    """Local Ollama client for running models locally."""

    def _initialize_client(self, base_url: str = "http://localhost:11434", **kwargs):
        try:
            from ollama import AsyncClient

            self.client = AsyncClient(host=base_url)
        except ImportError:
            logger.error("Ollama package required for local models")
            raise

    async def create_message(
        self, task: str, conversation_history: Optional[List[Dict]] = None, **kwargs
    ) -> Dict[str, Any]:
        try:
            messages = []
            if conversation_history:
                messages.extend(conversation_history)
            messages.append({"role": "user", "content": task})

            response = await self.client.chat(
                model=self.model,
                messages=messages,
                options={"temperature": kwargs.get("temperature", 0.7), "num_predict": kwargs.get("max_tokens", 4096)},
            )

            return {
                "status": "success",
                "content": response["message"]["content"],
                "usage": None,  # Ollama doesn't provide usage stats
            }
        except Exception as e:
            logger.error(f"Ollama error: {e}")
            return {"status": "error", "error": str(e)}

    async def get_available_models(self) -> List[str]:
        try:
            response = await self.client.list()
            return [m["name"] for m in response["models"]]
        except Exception as e:
            logger.error(f"Failed to get Ollama models: {e}")
            return []

    async def test_connection(self) -> bool:
        """Test connection to Ollama API."""
        try:
            # Try to list models as a connection test
            await self.client.list()
            return True
        except Exception:
            return False


class GeminiClient(ModelClient):
    """Google Gemini client."""

    def _initialize_client(self, **kwargs):
        try:
            import google.generativeai as genai

            genai.configure(api_key=self.api_key)
            self.client = genai.GenerativeModel(self.model)
        except ImportError:
            logger.error("google-generativeai package required for Gemini client")
            raise

    async def create_message(
        self, task: str, conversation_history: Optional[List[Dict]] = None, **kwargs
    ) -> Dict[str, Any]:
        try:
            # Gemini uses a different message format
            messages = []
            if conversation_history:
                for msg in conversation_history:
                    if msg["role"] == "user":
                        messages.append({"role": "user", "parts": [msg["content"]]})
                    elif msg["role"] == "assistant":
                        messages.append({"role": "model", "parts": [msg["content"]]})
            messages.append({"role": "user", "parts": [task]})

            # Start chat with history
            chat = self.client.start_chat(history=messages[:-1])  # Exclude the last message as it's the new input

            response = await chat.send_message_async(
                task,
                generation_config={
                    "temperature": kwargs.get("temperature", 0.7),
                    "max_output_tokens": kwargs.get("max_tokens", 4096),
                },
            )

            return {
                "status": "success",
                "content": response.text,
                "usage": None,  # Gemini doesn't provide detailed usage stats in the same way
            }
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return {"status": "error", "error": str(e)}

    async def get_available_models(self) -> List[str]:
        try:
            import google.generativeai as genai

            models = genai.list_models()
            return [m.name for m in models if "generateContent" in m.supported_generation_methods]
        except Exception as e:
            logger.error(f"Failed to get Gemini models: {e}")
            return ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro"]

    async def test_connection(self) -> bool:
        """Test connection to Gemini API."""
        return bool(self.api_key)


class ModelClientFactory:
    """Factory for creating model clients."""

    @staticmethod
    def create_client(provider: str, api_key: str, model: str, **kwargs) -> ModelClient:
        """Create a model client for the specified provider."""
        provider = provider.lower()

        if provider in ["grok", "xai"]:
            return GrokClient(api_key, model, **kwargs)
        elif provider in ["openai", "gpt"]:
            return OpenAIClient(api_key, model, **kwargs)
        elif provider in ["claude", "anthropic"]:
            return ClaudeClient(api_key, model, **kwargs)
        elif provider in ["ollama", "local"]:
            return OllamaClient(api_key, model, **kwargs)
        elif provider in ["gemini", "google"]:
            return GeminiClient(api_key, model, **kwargs)
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    @staticmethod
    def get_supported_providers() -> List[str]:
        """Get list of supported providers."""
        return ["grok", "openai", "claude", "ollama", "gemini"]

    @staticmethod
    async def get_available_models(provider: str, api_key: str = "", **kwargs) -> List[str]:
        """Get available models for a provider."""
        try:
            # Create a dummy client to get models
            dummy_model = "dummy"
            client = ModelClientFactory.create_client(provider, api_key, dummy_model, **kwargs)
            return await client.get_available_models()
        except Exception as e:
            logger.error(f"Failed to get models for {provider}: {e}")
            return []


# Backward compatibility - keep the old GrokClient class
class LegacyGrokClient(GrokClient):
    """Legacy GrokClient for backward compatibility."""

    pass
