import pytest
from unittest.mock import AsyncMock, patch
from src.grok_client import GrokClient, ProviderConfig


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


class TestUsageAndPayloads:
    def test_normalize_usage_per_provider(self):
        assert GrokClient._normalize_usage("grok", {"usage": {"prompt_tokens": 10, "completion_tokens": 5}}) == {
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "total_tokens": 15,
        }
        assert GrokClient._normalize_usage("claude", {"usage": {"input_tokens": 7, "output_tokens": 3}})[
            "total_tokens"
        ] == 10
        assert GrokClient._normalize_usage("gemini", {"usageMetadata": {"promptTokenCount": 4, "candidatesTokenCount": 2}})[
            "total_tokens"
        ] == 6
        assert GrokClient._normalize_usage("grok", {})["total_tokens"] == 0

    def test_usage_summary_per_agent(self):
        client = GrokClient()
        client.record_usage("observer", {"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120})
        client.record_usage("coordinator", {"prompt_tokens": 50, "completion_tokens": 10, "total_tokens": 60})
        client.record_usage("coordinator", {"prompt_tokens": 50, "completion_tokens": 10, "total_tokens": 60})
        summary = client.get_usage_summary()
        assert summary["coordinator"]["calls"] == 2
        assert summary["total"]["total_tokens"] == 240

    def test_image_payloads(self):
        msgs = [{"role": "user", "content": "look"}]
        grok = ProviderConfig("grok", "k", "http://x", "m")
        claude = ProviderConfig("claude", "k", "http://x", "m")
        gemini = ProviderConfig("gemini", "k", "http://x", "m")

        body, _ = GrokClient._build_payload(grok, msgs, "AAAA")
        assert body["messages"][0]["content"][1]["image_url"]["url"] == "data:image/png;base64,AAAA"
        body, _ = GrokClient._build_payload(claude, msgs, "AAAA")
        assert body["messages"][0]["content"][0]["source"]["data"] == "AAAA"
        body, _ = GrokClient._build_payload(gemini, msgs + [{"role": "assistant", "content": "ok"}], "AAAA")
        assert body["contents"][0]["parts"][1]["inline_data"]["data"] == "AAAA"
        assert body["contents"][1]["role"] == "model"

    def test_no_image_keeps_plain_content(self):
        body, _ = GrokClient._build_payload(
            ProviderConfig("grok", "k", "http://x", "m"), [{"role": "user", "content": "hi"}]
        )
        assert body["messages"][0]["content"] == "hi"

    @pytest.mark.asyncio
    async def test_create_message_returns_usage_and_passes_image(self):
        client = GrokClient()

        async def fake_chat(messages, session_id=None, agent="unknown", image_b64=None, meta=None):
            meta.update({"model": "m1", "finish_reason": "stop", "usage": {"total_tokens": 9}})
            assert image_b64 == "IMG" and agent == "observer"
            return "seen"

        with patch.object(client, "chat", side_effect=fake_chat):
            res = await client.create_message("what?", screenshot_base64="IMG", agent="observer")
        assert res["status"] == "success" and res["content"] == "seen"
        assert res["model"] == "m1" and res["usage"]["total_tokens"] == 9

    @pytest.mark.asyncio
    async def test_create_message_none_content_is_error(self):
        client = GrokClient()
        with patch.object(client, "chat", return_value=None):
            res = await client.create_message("x")
        assert res["status"] == "error"

    @pytest.mark.asyncio
    async def test_test_connection_needs_key(self):
        client = GrokClient()
        client.providers = [ProviderConfig("grok", "", "http://x", "m")]
        client.current_provider_index = 0
        assert await client.test_connection() is False


class TestProviderFallback:
    def _client(self, names):
        client = GrokClient()
        client.providers = [ProviderConfig(n, "k", "http://x", "m") for n in names]
        client.current_provider_index = 0
        return client

    @pytest.mark.asyncio
    async def test_falls_back_when_provider_returns_none(self):
        client = self._client(["grok", "claude"])
        calls = []

        async def fake_call(provider, messages, session_id=None, agent="unknown", image_b64=None, meta=None):
            calls.append(provider.name)
            if provider.name == "grok":
                meta["error"] = "grok API error 500"
                return None
            meta["provider"] = "claude"
            return "from claude"

        meta = {}
        with patch.object(client, "_call_provider", side_effect=fake_call):
            res = await client.chat([{"role": "user", "content": "x"}], meta=meta)
        assert res == "from claude"
        assert calls == ["grok", "claude"]
        assert meta["provider"] == "claude"

    @pytest.mark.asyncio
    async def test_falls_back_when_provider_raises(self):
        client = self._client(["grok", "claude"])

        async def fake_call(provider, *args, **kwargs):
            if provider.name == "grok":
                raise RuntimeError("boom")
            return "ok"

        with patch.object(client, "_call_provider", side_effect=fake_call):
            assert await client.chat([{"role": "user", "content": "x"}]) == "ok"

    @pytest.mark.asyncio
    async def test_all_providers_return_none_keeps_last_error(self):
        client = self._client(["grok", "claude"])
        calls = []

        async def fake_call(provider, messages, session_id=None, agent="unknown", image_b64=None, meta=None):
            calls.append(provider.name)
            meta["error"] = f"{provider.name} down"
            return None

        meta = {}
        with patch.object(client, "_call_provider", side_effect=fake_call):
            assert await client.chat([{"role": "user", "content": "x"}], meta=meta) is None
        assert calls == ["grok", "claude"]
        assert meta["error"] == "claude down"

    @pytest.mark.asyncio
    async def test_all_providers_raise_gives_api_error(self):
        from src.exceptions import APIError

        client = self._client(["grok", "claude"])
        with patch.object(client, "_call_provider", side_effect=RuntimeError("boom")):
            with pytest.raises(APIError):
                await client.chat([{"role": "user", "content": "x"}])


class TestErrorMessages:
    def test_error_message_extraction(self):
        body = '{"type":"error","error":{"type":"invalid_request_error","message":"credit balance too low"}}'
        assert GrokClient._error_message(body) == "credit balance too low"
        assert GrokClient._error_message('{"code":"x","error":"Incorrect API key"}') == "Incorrect API key"
        assert GrokClient._error_message("not json") == "not json"

    @pytest.mark.asyncio
    async def test_create_message_surfaces_api_error(self):
        client = GrokClient()

        async def fake_chat(messages, session_id=None, agent="unknown", image_b64=None, meta=None):
            meta["error"] = "claude API error 400: credit balance too low"
            return None

        with patch.object(client, "chat", side_effect=fake_chat):
            res = await client.create_message("x")
        assert res["status"] == "error"
        assert "credit balance too low" in res["error"]


class TestClaudeCliProvider:
    def _cli_client(self, monkeypatch):
        monkeypatch.setenv("PRIORITY_PROVIDER", "claude-cli")
        monkeypatch.setenv("FALLBACK_PROVIDERS", "")
        return GrokClient()

    def test_provider_loaded(self, monkeypatch):
        client = self._cli_client(monkeypatch)
        assert [p.name for p in client.providers] == ["claude-cli"]

    def test_flatten_messages(self):
        system, prompt = GrokClient._flatten_messages([{"role": "user", "content": "hi"}])
        assert (system, prompt) == ("", "hi")
        system, prompt = GrokClient._flatten_messages(
            [
                {"role": "system", "content": "be brief"},
                {"role": "user", "content": "a"},
                {"role": "assistant", "content": "b"},
                {"role": "user", "content": "c"},
            ]
        )
        assert system == "be brief"
        assert prompt == "User: a\n\nAssistant: b\n\nUser: c"

    @pytest.mark.asyncio
    async def test_success_counts_cache_tokens_and_drops_api_key(self, monkeypatch):
        import json as _json

        client = self._cli_client(monkeypatch)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "secret-should-not-leak")
        captured = {}

        class FakeProc:
            returncode = 0

            async def communicate(self, data):
                captured["stdin"] = data
                out = {
                    "result": "pong",
                    "stop_reason": "end_turn",
                    "usage": {
                        "input_tokens": 2,
                        "cache_creation_input_tokens": 500,
                        "cache_read_input_tokens": 100,
                        "output_tokens": 4,
                    },
                    "modelUsage": {"claude-haiku-5-5": {}},
                }
                return _json.dumps(out).encode(), b""

        async def fake_exec(*cmd, **kwargs):
            captured["env"] = kwargs["env"]
            return FakeProc()

        monkeypatch.setattr("src.grok_client.asyncio.create_subprocess_exec", fake_exec)
        monkeypatch.setattr("src.grok_client.shutil.which", lambda name: "claude")
        client.providers[0].rate_limit = 0.0

        res = await client.create_message("ping", agent="t")
        assert res["status"] == "success" and res["content"] == "pong"
        assert res["usage"] == {"prompt_tokens": 602, "completion_tokens": 4, "total_tokens": 606}
        assert res["model"] == "claude-haiku-5-5"
        assert captured["stdin"] == b"ping"
        assert "ANTHROPIC_API_KEY" not in captured["env"]
        assert client.get_usage_summary()["t"]["calls"] == 1

    @pytest.mark.asyncio
    async def test_missing_cli_and_images_are_clear_errors(self, monkeypatch):
        client = self._cli_client(monkeypatch)
        client.providers[0].rate_limit = 0.0
        monkeypatch.setattr("src.grok_client.shutil.which", lambda name: None)

        res = await client.create_message("x")
        assert res["status"] == "error" and "not found" in res["error"]
        res = await client.create_message("x", screenshot_base64="AAAA")
        assert res["status"] == "error" and "screenshots" in res["error"]
        assert await client.test_connection() is False


class TestGenerationOverrides:
    """ProviderConfig.max_tokens / temperature (used by workflow AINode) reach each provider's request body."""

    MSGS = [{"role": "system", "content": "be brief"}, {"role": "user", "content": "hi"}]

    def test_defaults_are_unchanged(self):
        body, _ = GrokClient._build_payload(ProviderConfig("grok", "k", "http://x", "m"), self.MSGS)
        assert body["max_tokens"] == 1024 and body["temperature"] == 0.7
        body, _ = GrokClient._build_payload(ProviderConfig("claude", "k", "http://x", "m"), self.MSGS)
        assert body["max_tokens"] == 1024 and "temperature" not in body
        body, _ = GrokClient._build_payload(ProviderConfig("gemini", "k", "http://x", "m"), self.MSGS)
        assert "generationConfig" not in body

    @pytest.mark.parametrize("name", ["grok", "openai"])
    def test_openai_compatible_body(self, name):
        body, _ = GrokClient._build_payload(
            ProviderConfig(name, "k", "http://x", "m", max_tokens=333, temperature=0.0), self.MSGS
        )
        assert body["max_tokens"] == 333 and body["temperature"] == 0.0  # 0.0 must not fall back to 0.7

    def test_claude_body(self):
        body, _ = GrokClient._build_payload(
            ProviderConfig("claude", "k", "http://x", "m", max_tokens=333, temperature=0.2), self.MSGS
        )
        assert body["max_tokens"] == 333 and body["temperature"] == 0.2 and body["system"] == "be brief"

    def test_gemini_body(self):
        body, _ = GrokClient._build_payload(
            ProviderConfig("gemini", "k", "http://x", "m", max_tokens=333, temperature=0.2), self.MSGS
        )
        assert body["generationConfig"] == {"temperature": 0.2, "maxOutputTokens": 333}
