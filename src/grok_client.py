#!/usr/bin/env python3
"""
Grok Client with Provider Fallbacks
Primary: Grok (xAI). Fallbacks: Claude (Anthropic), Gemini (Google).
Async client with error handling and rate limiting.
Integrates with analytics for fallback tracking.
"""
from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

import aiohttp

# Analytics integration disabled due to database issues
# try:
#     from analytics import log_api_call, start_session, end_session
#     ANALYTICS_ENABLED = True
# except ImportError:
#     ANALYTICS_ENABLED = False

ANALYTICS_ENABLED = False

# Standardized error handling
from .exceptions import APIError, handle_error, retry_with_backoff

logger = logging.getLogger(__name__)


@dataclass
class ProviderConfig:
    name: str
    api_key: str
    base_url: str
    model: str
    max_retries: int = 3
    rate_limit: float = 1.0  # Seconds between calls


class GrokClient:
    """Async client with fallback providers."""

    def __init__(self):
        self.providers = self._load_providers()
        self.session = None
        self.current_provider_index = 0
        self.rate_limiter = asyncio.Semaphore(1)  # Simple rate limit

    def _load_providers(self) -> list[ProviderConfig]:
        """Load providers from .env (priority: grok > fallbacks)."""
        priority_provider = os.getenv("PRIORITY_PROVIDER", "grok")
        fallback_str = os.getenv("FALLBACK_PROVIDERS", "claude,gemini")
        fallbacks = [p.strip() for p in fallback_str.split(",") if p.strip()]

        providers = []

        # Priority
        if priority_provider == "grok":
            providers.append(
                ProviderConfig(
                    name="grok",
                    api_key=os.getenv("XAI_API_KEY"),
                    base_url=os.getenv("XAI_BASE_URL", "https://api.x.ai/v1"),
                    model=os.getenv("GROK_MODEL", "grok-beta"),
                )
            )
        elif priority_provider == "claude":
            providers.append(
                ProviderConfig(
                    name="claude",
                    api_key=os.getenv("ANTHROPIC_API_KEY"),
                    base_url="https://api.anthropic.com/v1",
                    model=os.getenv("CLAUDE_MODEL", "claude-3-sonnet-20240229"),
                )
            )
        # Add Gemini similarly if priority

        # Fallbacks
        for fb in fallbacks:
            if fb == "claude" and os.getenv("ANTHROPIC_API_KEY"):
                if "claude" not in [p.name for p in providers]:
                    providers.append(
                        ProviderConfig(
                            name="claude",
                            api_key=os.getenv("ANTHROPIC_API_KEY"),
                            base_url="https://api.anthropic.com/v1",
                            model=os.getenv("CLAUDE_MODEL", "claude-3-sonnet-20240229"),
                        )
                    )
            elif fb == "gemini" and os.getenv("GEMINI_API_KEY"):
                if "gemini" not in [p.name for p in providers]:
                    providers.append(
                        ProviderConfig(
                            name="gemini",
                            api_key=os.getenv("GEMINI_API_KEY"),
                            base_url="https://generativelanguage.googleapis.com/v1beta",
                            model=os.getenv("GEMINI_MODEL", "gemini-pro"),
                        )
                    )

        logger.info(f"Loaded providers: {[p.name for p in providers]}")
        return providers

    def _get_session(self):
        if self.session is None:
            connector = aiohttp.TCPConnector(limit=10, limit_per_host=2)
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(connector=connector, timeout=timeout)
        return self.session

    async def _call_provider(
        self, provider: ProviderConfig, messages: list[Dict[str, str]], session_id: Optional[int] = None
    ) -> Optional[str]:
        """Call a single provider async."""
        async with self.rate_limiter:
            await asyncio.sleep(provider.rate_limit)

            headers = {"Content-Type": "application/json"}
            if provider.name == "grok":
                headers["Authorization"] = f"Bearer {provider.api_key}"
                url = f"{provider.base_url}/chat/completions"
            elif provider.name == "claude":
                headers["x-api-key"] = provider.api_key
                headers["anthropic-version"] = "2023-06-01"
                url = f"{provider.base_url}/messages"
            elif provider.name == "gemini":
                # Gemini uses key in URL
                url = f"{provider.base_url}/models/{provider.model}:generateContent?key={provider.api_key}"
            else:
                url = f"{provider.base_url}/chat/completions"

            payload = {"model": provider.model, "messages": messages, "max_tokens": 1024, "temperature": 0.7}

            if provider.name == "claude":
                payload = {"model": provider.model, "max_tokens": 1024, "messages": messages}
            elif provider.name == "gemini":
                payload = {"contents": [{"parts": [{"text": m["content"] for m in messages}]}]}

            session = self._get_session()
            try:
                async with session.post(url, json=payload, headers=headers) as response:
                    response_time = (
                        response.connection.transport.get_extra_info("total_time", 0)
                        if response.connection and response.connection.transport
                        else 0
                    )
                    if response.status == 200:
                        data = await response.json()
                        if provider.name == "grok" or provider.name == "claude":
                            content = data["choices"][0]["message"]["content"]
                        elif provider.name == "gemini":
                            content = data["candidates"][0]["content"]["parts"][0]["text"]

                        # Log to analytics
                        if ANALYTICS_ENABLED:
                            log_api_call(session_id, url, response_time, response.status)

                        logger.info(f"{provider.name} success: {response_time:.2f}s")
                        return content
                    else:
                        error_text = await response.text()
                        logger.warning(f"{provider.name} error {response.status}: {error_text}")
                        if ANALYTICS_ENABLED:
                            log_api_call(session_id, url, response_time, response.status)
                        return None
            except Exception as e:
                error_details = {
                    "provider": provider.name,
                    "url": url,
                    "session_id": session_id,
                    "payload_size": len(str(payload)),
                }
                handle_error(e, f"API call to {provider.name}", "error")
                if ANALYTICS_ENABLED:
                    log_api_call(session_id, f"{provider.base_url}/error", 0, 500)
                return None

    async def chat(self, messages: list[Dict[str, str]], session_id: Optional[int] = None) -> str:
        """Chat with the AI using current provider."""
        if not self.session:
            self.session = self._get_session()

        provider = self.providers[self.current_provider_index]
        try:
            response = await self._call_provider(provider, messages, session_id)
            if ANALYTICS_ENABLED:
                log_api_call(provider.name, "success", len(messages))
            return response
        except Exception as e:
            logger.error(f"Provider {provider.name} failed: {e}")
            if ANALYTICS_ENABLED:
                log_api_call(provider.name, "error", len(messages))
            # Try next provider
            self.current_provider_index = (self.current_provider_index + 1) % len(self.providers)
            if self.current_provider_index != 0:  # Don't retry the same provider
                return await self.chat(messages, session_id)
            raise APIError(f"All providers failed: {e}")

    async def create_message(self, task: str, conversation_history: Optional[list] = None, **kwargs) -> Dict[str, Any]:
        """Create a message with the AI model, returning dict format."""
        messages = []
        if conversation_history:
            messages.extend(conversation_history)
        messages.append({"role": "user", "content": task})

        try:
            content = await self.chat(messages)
            return {"status": "success", "content": content}
        except Exception as e:
            logger.error(f"create_message failed: {e}")
            return {"status": "error", "content": str(e)}

    async def close(self):
        """Close the session."""
        if self.session:
            await self.session.close()


class FallbackGrokClient(GrokClient):
    """Simple alias for GrokClient with fallback capabilities."""

    pass


# Usage
async def main():
    client = FallbackGrokClient()
    messages = [{"role": "user", "content": "Hello!"}]
    response = await client.chat(messages)
    print(response)
    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
