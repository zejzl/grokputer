#!/usr/bin/env python3
"""
Grok Client with Provider Fallbacks
Primary: Grok (xAI). Fallbacks: Claude (Anthropic), Gemini (Google).
Async client with error handling and rate limiting.
Integrates with analytics for fallback tracking.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import tempfile
import time
import weakref
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

CLI_TIMEOUT = 120.0  # seconds allowed for one `claude -p` call


@dataclass
class ProviderConfig:
    name: str
    api_key: str
    base_url: str
    model: str
    max_retries: int = 3
    rate_limit: float = 1.0  # Seconds between calls
    # Per-call generation overrides; None keeps the built-in defaults (1024 tokens, grok/openai temperature 0.7,
    # claude/gemini provider default). Ignored by claude-cli, which has no such options.
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None


class GrokClient:
    """Async client with fallback providers."""

    _instances: "weakref.WeakSet[GrokClient]" = weakref.WeakSet()

    @classmethod
    def global_usage_summary(cls) -> Dict[str, Dict[str, int]]:
        """Token usage per agent tag, summed over every live client, plus a "total" entry."""
        merged: Dict[str, Dict[str, int]] = {}
        for client in list(cls._instances):
            for agent, t in client.usage_by_agent.items():
                m = merged.setdefault(agent, {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0})
                for key in m:
                    m[key] += t[key]
        grand = {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        for t in merged.values():
            for key in grand:
                grand[key] += t[key]
        merged["total"] = grand
        return merged

    def __init__(self, provider: Optional[str] = None):
        """
        Args:
            provider: Use only this provider (grok, claude, claude-cli, gemini or openai), ignoring
                PRIORITY_PROVIDER / FALLBACK_PROVIDERS. Raises ValueError if its credentials are missing.
        """
        GrokClient._instances.add(self)
        self.providers = self._load_providers(only=provider)
        self.session = None
        self.current_provider_index = 0
        self.rate_limiter = asyncio.Semaphore(1)  # Simple rate limit
        # Token usage per agent tag: {agent: {calls, prompt_tokens, completion_tokens, total_tokens}}
        self.usage_by_agent: Dict[str, Dict[str, int]] = {}

    @staticmethod
    def _provider_config(name: str) -> Optional[ProviderConfig]:
        """Build the config for one named provider from the environment; None if its credentials are missing."""
        if name == "grok":
            key = os.getenv("XAI_API_KEY")
            return key and ProviderConfig(
                "grok", key, os.getenv("XAI_BASE_URL", "https://api.x.ai/v1"), os.getenv("GROK_MODEL", "grok-beta")
            )
        if name == "claude":
            key = os.getenv("ANTHROPIC_API_KEY")
            return key and ProviderConfig(
                "claude", key, "https://api.anthropic.com/v1", os.getenv("CLAUDE_MODEL", "claude-haiku-5-5")
            )
        if name == "claude-cli":
            return GrokClient._claude_cli_config()
        if name == "gemini":
            key = os.getenv("GEMINI_API_KEY")
            return key and ProviderConfig(
                "gemini", key, "https://generativelanguage.googleapis.com/v1beta", os.getenv("GEMINI_MODEL", "gemini-pro")
            )
        if name == "openai":
            key = os.getenv("OPENAI_API_KEY")
            return key and ProviderConfig(
                "openai", key, os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"), os.getenv("OPENAI_MODEL", "gpt-4o")
            )
        return None

    def _load_providers(self, only: Optional[str] = None) -> list[ProviderConfig]:
        """Load providers from .env (priority: grok > fallbacks), or just `only` if given."""
        if only:
            config = self._provider_config(only)
            if not config:
                raise ValueError(f"Provider '{only}' is unknown or its API key is not set")
            return [config]

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
        elif priority_provider == "claude-cli":
            providers.append(self._claude_cli_config())
        elif priority_provider == "claude":
            providers.append(
                ProviderConfig(
                    name="claude",
                    api_key=os.getenv("ANTHROPIC_API_KEY"),
                    base_url="https://api.anthropic.com/v1",
                    model=os.getenv("CLAUDE_MODEL", "claude-haiku-5-5"),
                )
            )
        # Add Gemini similarly if priority

        # Fallbacks
        for fb in fallbacks:
            if fb == "claude-cli":
                if "claude-cli" not in [p.name for p in providers]:
                    providers.append(self._claude_cli_config())
            elif fb == "claude" and os.getenv("ANTHROPIC_API_KEY"):
                if "claude" not in [p.name for p in providers]:
                    providers.append(
                        ProviderConfig(
                            name="claude",
                            api_key=os.getenv("ANTHROPIC_API_KEY"),
                            base_url="https://api.anthropic.com/v1",
                            model=os.getenv("CLAUDE_MODEL", "claude-haiku-5-5"),
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

    @staticmethod
    def _claude_cli_config() -> ProviderConfig:
        """Provider that shells out to the `claude` CLI (subscription login, no API key; for testing)."""
        return ProviderConfig(
            name="claude-cli",
            api_key="",
            base_url="cli",
            model=os.getenv("CLAUDE_CLI_MODEL", "haiku"),
            rate_limit=0.0,
        )

    def _get_session(self):
        if self.session is None:
            connector = aiohttp.TCPConnector(limit=10, limit_per_host=2)
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(connector=connector, timeout=timeout)
        return self.session

    @staticmethod
    def _normalize_usage(provider_name: str, data: Dict[str, Any]) -> Dict[str, int]:
        """Map each provider's usage field to prompt/completion/total token counts."""
        if provider_name == "claude":
            raw = data.get("usage") or {}
            prompt, completion = raw.get("input_tokens", 0), raw.get("output_tokens", 0)
        elif provider_name == "gemini":
            raw = data.get("usageMetadata") or {}
            prompt, completion = raw.get("promptTokenCount", 0), raw.get("candidatesTokenCount", 0)
        else:
            raw = data.get("usage") or {}
            prompt, completion = raw.get("prompt_tokens", 0), raw.get("completion_tokens", 0)
        return {
            "prompt_tokens": int(prompt or 0),
            "completion_tokens": int(completion or 0),
            "total_tokens": int(prompt or 0) + int(completion or 0),
        }

    def record_usage(self, agent: str, usage: Dict[str, int]) -> None:
        """Add one call's token usage to the per-agent totals."""
        totals = self.usage_by_agent.setdefault(
            agent, {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        )
        totals["calls"] += 1
        for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
            totals[key] += usage.get(key, 0)

    def get_usage_summary(self) -> Dict[str, Dict[str, int]]:
        """Token usage per agent tag, plus a "total" entry."""
        summary = {agent: dict(totals) for agent, totals in self.usage_by_agent.items()}
        grand = {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        for totals in self.usage_by_agent.values():
            for key in grand:
                grand[key] += totals[key]
        summary["total"] = grand
        return summary

    def log_usage_summary(self) -> None:
        """Log token usage per agent (one line each)."""
        for agent, t in self.get_usage_summary().items():
            logger.info(
                f"[tokens] {agent}: {t['calls']} calls, {t['prompt_tokens']} in, "
                f"{t['completion_tokens']} out, {t['total_tokens']} total"
            )

    @staticmethod
    def _error_message(body: str) -> str:
        """Pull the human-readable message out of a provider error body (falls back to the raw text)."""
        try:
            err = json.loads(body).get("error", body)
        except (ValueError, AttributeError):
            return body[:300]
        if isinstance(err, dict):
            err = err.get("message", body)
        return str(err)[:300]

    @staticmethod
    def _split_system(messages: list[Dict[str, str]]) -> tuple[str, list[Dict[str, str]]]:
        """Separate system messages (which Claude and Gemini take as a top-level field) from the conversation."""
        system = "\n\n".join(m["content"] for m in messages if m.get("role") == "system")
        return system, [m for m in messages if m.get("role") != "system"]

    @staticmethod
    def _build_payload(
        provider: ProviderConfig, messages: list[Dict[str, str]], image_b64: Optional[str] = None
    ) -> tuple[Dict[str, Any], str]:
        """Build the request body for a provider; the image (PNG, base64) goes on the last user message."""
        model = provider.model
        last_user = max((i for i, m in enumerate(messages) if m.get("role") == "user"), default=None)

        if provider.name == "claude":
            system, messages = GrokClient._split_system(messages)
            last_user = max((i for i, m in enumerate(messages) if m.get("role") == "user"), default=None)
            out = []
            for i, m in enumerate(messages):
                if image_b64 and i == last_user:
                    content = [
                        {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": image_b64}},
                        {"type": "text", "text": m["content"]},
                    ]
                else:
                    content = m["content"]
                out.append({"role": m["role"], "content": content})
            body = {"model": model, "max_tokens": provider.max_tokens or 1024, "messages": out}
            if provider.temperature is not None:
                body["temperature"] = provider.temperature
            if system:
                body["system"] = system
            return body, model

        if provider.name == "gemini":
            system, messages = GrokClient._split_system(messages)
            last_user = max((i for i, m in enumerate(messages) if m.get("role") == "user"), default=None)
            contents = []
            for i, m in enumerate(messages):
                parts = [{"text": m["content"]}]
                if image_b64 and i == last_user:
                    parts.append({"inline_data": {"mime_type": "image/png", "data": image_b64}})
                contents.append({"role": "model" if m["role"] == "assistant" else "user", "parts": parts})
            body = {"contents": contents}
            generation = {}
            if provider.temperature is not None:
                generation["temperature"] = provider.temperature
            if provider.max_tokens:
                generation["maxOutputTokens"] = provider.max_tokens
            if generation:
                body["generationConfig"] = generation
            if system:
                body["systemInstruction"] = {"parts": [{"text": system}]}
            return body, model

        # OpenAI-compatible (grok, openai)
        out = []
        for i, m in enumerate(messages):
            if image_b64 and i == last_user:
                content = [
                    {"type": "text", "text": m["content"]},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}},
                ]
            else:
                content = m["content"]
            out.append({"role": m["role"], "content": content})
        if image_b64 and provider.name == "grok":
            model = os.getenv("GROK_VISION_MODEL", model)
        temperature = 0.7 if provider.temperature is None else provider.temperature
        return {
            "model": model,
            "messages": out,
            "max_tokens": provider.max_tokens or 1024,
            "temperature": temperature,
        }, model

    @staticmethod
    def _flatten_messages(messages: list[Dict[str, str]]) -> tuple[str, str]:
        """Split chat messages into (system prompt, single prompt text) for CLI use."""
        system = "\n\n".join(m["content"] for m in messages if m.get("role") == "system")
        turns = [m for m in messages if m.get("role") != "system"]
        if len(turns) == 1:
            return system, turns[0]["content"]
        prompt = "\n\n".join(f"{'Assistant' if m['role'] == 'assistant' else 'User'}: {m['content']}" for m in turns)
        return system, prompt

    async def _call_claude_cli(
        self,
        provider: ProviderConfig,
        messages: list[Dict[str, str]],
        agent: str,
        image_b64: Optional[str],
        meta: Optional[Dict[str, Any]],
    ) -> Optional[str]:
        """
        Run one prompt through the `claude` CLI (`claude -p`), which uses the user's Claude
        subscription login instead of an API key. Intended for testing; text only.
        """

        def fail(message: str) -> None:
            logger.warning(f"claude-cli: {message}")
            if meta is not None:
                meta["error"] = f"claude-cli: {message}"

        if image_b64:
            fail("screenshots are not supported by the claude-cli provider")
            return None

        exe = shutil.which("claude")
        if not exe:
            fail("`claude` CLI not found on PATH")
            return None

        system, prompt = self._flatten_messages(messages)
        cmd = [
            exe, "-p", "--output-format", "json", "--model", provider.model,
            "--system-prompt", system or "You are a helpful assistant.",
            "--tools", "", "--disable-slash-commands", "--no-session-persistence",
            "--setting-sources", "", "--strict-mcp-config",
        ]  # fmt: skip

        # An API key in the environment would make the CLI bill the API instead of using the subscription login
        env = {k: v for k, v in os.environ.items() if k not in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")}

        try:
            started = time.monotonic()
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=tempfile.gettempdir(),  # keep project CLAUDE.md files out of the prompt
                env=env,
            )
            try:
                out, err = await asyncio.wait_for(proc.communicate(prompt.encode("utf-8")), timeout=CLI_TIMEOUT)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                fail(f"timed out after {CLI_TIMEOUT:.0f}s")
                return None
            elapsed = time.monotonic() - started

            try:
                data = json.loads(out.decode("utf-8", errors="replace"))
            except ValueError:
                fail(f"exit {proc.returncode}, unparseable output: {(err or out).decode('utf-8', 'replace')[:300]}")
                return None
            if data.get("is_error") or proc.returncode != 0:
                fail(str(data.get("result") or data.get("api_error_status") or f"exit {proc.returncode}")[:300])
                return None

            raw = data.get("usage") or {}
            prompt_tokens = sum(
                int(raw.get(k, 0) or 0) for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")
            )
            completion_tokens = int(raw.get("output_tokens", 0) or 0)
            usage = {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            }
            self.record_usage(agent, usage)
            if meta is not None:
                meta.update(
                    {
                        "model": next(iter(data.get("modelUsage") or {}), provider.model),
                        "provider": provider.name,
                        "finish_reason": data.get("stop_reason") or "unknown",
                        "usage": usage,
                    }
                )
            logger.info(
                f"claude-cli success: {elapsed:.2f}s "
                f"[{agent}: {usage['prompt_tokens']} in / {usage['completion_tokens']} out tokens]"
            )
            return data.get("result", "")
        except Exception as e:
            handle_error(e, "claude-cli call", "error")
            fail(f"request failed: {e}")
            return None

    async def _call_provider(
        self,
        provider: ProviderConfig,
        messages: list[Dict[str, str]],
        session_id: Optional[int] = None,
        agent: str = "unknown",
        image_b64: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        Call a single provider async and return the reply text (None on failure).

        Token usage is recorded under `agent`. If `meta` is given it is filled with
        model, finish_reason and usage for the caller.
        """
        async with self.rate_limiter:
            await asyncio.sleep(provider.rate_limit)

            if provider.name == "claude-cli":
                return await self._call_claude_cli(provider, messages, agent, image_b64, meta)

            headers = {"Content-Type": "application/json"}
            if provider.name in ("grok", "openai"):
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

            payload, model = self._build_payload(provider, messages, image_b64)

            session = self._get_session()
            try:
                started = time.monotonic()
                async with session.post(url, json=payload, headers=headers) as response:
                    response_time = time.monotonic() - started
                    if response.status == 200:
                        data = await response.json()
                        finish_reason = "unknown"
                        if provider.name == "claude":
                            content = "".join(b.get("text", "") for b in data["content"] if b.get("type") == "text")
                            finish_reason = data.get("stop_reason") or finish_reason
                        elif provider.name == "gemini":
                            candidate = data["candidates"][0]
                            content = candidate["content"]["parts"][0]["text"]
                            finish_reason = candidate.get("finishReason") or finish_reason
                        else:
                            choice = data["choices"][0]
                            content = choice["message"]["content"]
                            finish_reason = choice.get("finish_reason") or finish_reason

                        usage = self._normalize_usage(provider.name, data)
                        self.record_usage(agent, usage)
                        if meta is not None:
                            meta.update(
                                {
                                    "model": data.get("model", model),
                                    "provider": provider.name,
                                    "finish_reason": finish_reason,
                                    "usage": usage,
                                }
                            )

                        # Log to analytics
                        if ANALYTICS_ENABLED:
                            log_api_call(session_id, url, response_time, response.status)

                        logger.info(
                            f"{provider.name} success: {response_time:.2f}s "
                            f"[{agent}: {usage['prompt_tokens']} in / {usage['completion_tokens']} out tokens]"
                        )
                        return content
                    else:
                        error_text = await response.text()
                        logger.warning(f"{provider.name} error {response.status}: {error_text}")
                        if meta is not None:
                            meta["error"] = f"{provider.name} API error {response.status}: {self._error_message(error_text)}"
                        if ANALYTICS_ENABLED:
                            log_api_call(session_id, url, response_time, response.status)
                        return None
            except Exception as e:
                handle_error(e, f"API call to {provider.name}", "error")
                if meta is not None:
                    meta["error"] = f"{provider.name} request failed: {e}"
                if ANALYTICS_ENABLED:
                    log_api_call(session_id, f"{provider.base_url}/error", 0, 500)
                return None

    async def chat(
        self,
        messages: list[Dict[str, str]],
        session_id: Optional[int] = None,
        agent: str = "unknown",
        image_b64: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Chat with the AI, starting at the current provider and falling back to the
        next ones when a provider raises or returns no content.

        Each provider is tried at most once. Returns None if every provider returned
        no content (`meta["error"]` holds the last error); raises APIError if the
        last failure was an exception.
        """
        if not self.session:
            self.session = self._get_session()

        count = len(self.providers)
        last_exc: Optional[Exception] = None
        for offset in range(count):
            provider = self.providers[(self.current_provider_index + offset) % count]
            attempt_meta: Dict[str, Any] = {}
            try:
                response = await self._call_provider(provider, messages, session_id, agent, image_b64, attempt_meta)
                last_exc = None
            except Exception as e:
                logger.error(f"Provider {provider.name} failed: {e}")
                last_exc = e
                response = None
                attempt_meta.setdefault("error", f"{provider.name} request failed: {e}")

            if response is not None:
                if ANALYTICS_ENABLED:
                    log_api_call(provider.name, "success", len(messages))
                if meta is not None:
                    meta.update(attempt_meta)
                return response

            if ANALYTICS_ENABLED:
                log_api_call(provider.name, "error", len(messages))
            if meta is not None:
                meta.update(attempt_meta)
            if offset + 1 < count:
                logger.warning(f"Provider {provider.name} gave no response, falling back to next provider")

        if last_exc is not None:
            raise APIError(f"All providers failed: {last_exc}")
        return None

    async def test_connection(self) -> bool:
        """Cheap readiness check (no network call, no tokens): API key set, or `claude` CLI on PATH for claude-cli."""
        if not self.providers:
            return False
        provider = self.providers[self.current_provider_index]
        if provider.name == "claude-cli":
            return shutil.which("claude") is not None
        return bool(provider.api_key)

    async def create_message(
        self,
        task: str,
        conversation_history: Optional[list] = None,
        screenshot_base64: Optional[str] = None,
        agent: str = "unknown",
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Create a message with the AI model, returning dict format.

        Args:
            task: The user prompt
            conversation_history: Prior messages
            screenshot_base64: Optional PNG screenshot (base64) attached to the prompt
            agent: Tag under which token usage is recorded (e.g. "observer", "coordinator")
        """
        messages = []
        if conversation_history:
            messages.extend(conversation_history)
        messages.append({"role": "user", "content": task})

        meta: Dict[str, Any] = {}
        try:
            content = await self.chat(messages, agent=agent, image_b64=screenshot_base64, meta=meta)
            if content is None:
                error = meta.get("error", "Provider returned no content")
                return {"status": "error", "error": error, "content": error}
            return {
                "status": "success",
                "content": content,
                "model": meta.get("model", "unknown"),
                "finish_reason": meta.get("finish_reason", "unknown"),
                "usage": meta.get("usage", {}),
            }
        except Exception as e:
            logger.error(f"create_message failed: {e}")
            return {"status": "error", "error": str(e), "content": str(e)}

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
