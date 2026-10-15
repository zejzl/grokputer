"""Real (non-mock) providers for MAF: registry wiring, GrokClient provider override, system-message payloads."""
import asyncio
from unittest.mock import AsyncMock

import pytest

from src.collaboration.message_models import AgentRole
from src.collaboration.provider_registry import (
    RealProviderClient,
    initialize_real_providers,
    provider_registry,
)
from src.grok_client import GrokClient, ProviderConfig


@pytest.fixture(autouse=True)
def clean_registry():
    before = set(provider_registry._providers)
    yield
    for pid in set(provider_registry._providers) - before:
        provider_registry.unregister_provider(pid)


def test_register_two_models_of_one_provider():
    registered = asyncio.run(initialize_real_providers(["claude-cli:haiku", "claude-cli:sonnet"]))
    assert registered == ["claude-cli:haiku", "claude-cli:sonnet"]
    assert provider_registry._providers["claude-cli:sonnet"].client.model == "sonnet"
    assert provider_registry._providers["claude-cli:haiku"].metadata.provider_type == "claude-cli"


def test_unknown_provider_registers_nothing():
    with pytest.raises(ValueError, match="Unknown provider"):
        asyncio.run(initialize_real_providers(["claude-cli", "nope"]))
    assert "claude-cli" not in provider_registry._providers


def test_missing_api_key_is_a_clear_error(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ValueError, match="API key is not set"):
        asyncio.run(initialize_real_providers(["openai"]))


def test_health_check_makes_no_api_call():
    client = RealProviderClient("claude-cli", "haiku")
    client._client.chat = AsyncMock()
    assert asyncio.run(client.get_available_models()) == ["haiku"]
    client._client.chat.assert_not_called()


def test_generate_response_sends_role_and_tags_usage():
    client = RealProviderClient("claude-cli", "haiku")
    client._client.chat = AsyncMock(return_value="hello")
    assert asyncio.run(client.generate_response("do it", "critic")) == "hello"
    args, kwargs = client._client.chat.call_args
    assert args[0][0]["role"] == "system" and "critic" in args[0][0]["content"]
    assert args[0][1] == {"role": "user", "content": "do it"}
    assert kwargs["agent"] == "maf_claude-cli_critic"


def test_generate_response_raises_with_api_message():
    client = RealProviderClient("claude-cli", "haiku")

    async def failing_chat(messages, agent="x", meta=None):
        meta["error"] = "claude API error 400: credit balance too low"

    client._client.chat = failing_chat
    with pytest.raises(RuntimeError, match="credit balance too low"):
        asyncio.run(client.generate_response("x", "analyzer"))


def test_grokclient_provider_override_ignores_priority(monkeypatch):
    monkeypatch.setenv("PRIORITY_PROVIDER", "grok")
    monkeypatch.setenv("OPENAI_API_KEY", "k")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-test")
    client = GrokClient(provider="openai")
    assert [(p.name, p.model) for p in client.providers] == [("openai", "gpt-test")]


def test_system_message_payloads():
    msgs = [{"role": "system", "content": "be brief"}, {"role": "user", "content": "hi"}]
    claude = ProviderConfig("claude", "k", "http://x", "m")
    gemini = ProviderConfig("gemini", "k", "http://x", "m")
    grok = ProviderConfig("grok", "k", "http://x", "m")

    body, _ = GrokClient._build_payload(claude, msgs)
    assert body["system"] == "be brief" and [m["role"] for m in body["messages"]] == ["user"]
    body, _ = GrokClient._build_payload(gemini, msgs)
    assert body["systemInstruction"]["parts"][0]["text"] == "be brief" and len(body["contents"]) == 1
    body, _ = GrokClient._build_payload(grok, msgs)
    assert [m["role"] for m in body["messages"]] == ["system", "user"]


def test_agent_role_accepts_provider_specs():
    assert AgentRole.from_provider_id("claude-cli:sonnet") == AgentRole.CLAUDE
    assert AgentRole.from_provider_id("grok") == AgentRole.GROK
    assert AgentRole.from_provider_id("CLAUDE") == AgentRole.CLAUDE
    with pytest.raises(ValueError):
        AgentRole.from_provider_id("unknown")


def test_maf_messagebus_coordinator_initializes():
    from src.collaboration.maf_messagebus_integration import MAFMessageBusCoordinator
    from src.core.message_bus import MessageBus

    async def go():
        bus = MessageBus()
        coordinator = MAFMessageBusCoordinator(bus)
        await coordinator.initialize()
        assert "maf_orchestrator" in bus.queues
        assert coordinator.orchestrator is not None

    asyncio.run(go())


def test_adapter_publishes_valid_messagebus_messages():
    from unittest.mock import Mock

    from src.collaboration.maf_messagebus_integration import MAFMessageBusAdapter
    from src.core.message_bus import MessageBus, MessagePriority

    async def go():
        bus = MessageBus()
        bus.register_agent("maf_orchestrator")
        adapter = MAFMessageBusAdapter(bus, Mock())
        await adapter._publish("task_request", {"task_id": "t"}, MessagePriority.NORMAL)
        return await bus.receive("maf_orchestrator", timeout=1.0)

    msg = asyncio.run(go())
    assert msg.message_type == "task_request" and msg.content["task_id"] == "t"
