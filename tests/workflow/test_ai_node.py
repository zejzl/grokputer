"""AINode on the real GrokClient. Only the HTTP layer (GrokClient._call_provider) is patched."""
from unittest.mock import patch

import pytest

from src.grok_client import GrokClient
from src.workflow import WorkflowDefinitionError, build_workflow
from src.workflow.nodes import AINode
from src.workflow.nodes.base import NodeContext, NodeStatus


def make_fake(reply="high", fail_with=None):
    """Stand-in for GrokClient._call_provider that records what the node asked for.

    Must be a plain async function: AsyncMock only awaits side effects that are coroutine functions.
    """
    calls = []

    async def fake_call(client, provider, messages, session_id=None, agent="unknown", image_b64=None, meta=None):
        calls.append(
            {
                "name": provider.name,
                "model": provider.model,
                "temperature": provider.temperature,
                "max_tokens": provider.max_tokens,
                "messages": list(messages),
                "agent": agent,
            }
        )
        if fail_with:
            meta["error"] = fail_with
            return None
        meta.update({"model": provider.model, "provider": provider.name, "usage": {"total_tokens": 3}})
        return reply

    fake_call.calls = calls
    return fake_call


@pytest.fixture
def fake():
    fake_call = make_fake()
    with patch.object(GrokClient, "_call_provider", autospec=True, side_effect=fake_call):
        yield fake_call


async def run(node, **data):
    return await node.run(NodeContext(data=data))


class TestConfig:
    def test_defaults(self):
        node = AINode("n", config={"prompt": "hi"})
        assert node.config["provider"] == "grok"
        assert node.config["temperature"] == 0.7 and node.config["max_tokens"] == 2000
        assert "model" not in node.config  # None means the provider's own default

    @pytest.mark.parametrize(
        "config, message",
        [
            ({"prompt": "x", "pantheon_agent": "observer"}, "PantheonNode"),
            ({"pantheon_agent": "observer"}, "PantheonNode"),
            ({"prompt": "x", "provider": "maf"}, "main.py --providers"),
            ({}, "requires 'prompt'"),
        ],
    )
    def test_unsupported_or_incomplete_config_is_rejected_when_created(self, config, message):
        with pytest.raises(ValueError, match=message):
            AINode("n", config=config)

    def test_loader_reports_it_as_a_definition_error(self):
        definition = {"nodes": [{"id": "a", "type": "ai", "config": {"provider": "maf", "prompt": "x"}}]}
        with pytest.raises(WorkflowDefinitionError, match="not supported by AINode"):
            build_workflow(definition)


class TestProviderCall:
    @pytest.mark.asyncio
    async def test_reply_and_output_shape(self, fake):
        node = AINode("classify", config={"prompt": "Classify urgency of: {{message}}"})
        out = await run(node, message="server on fire")

        assert out.data["ai_response"] == "high" and out.data["raw_response"] == "high"
        assert out.data["provider"] == "grok"
        assert out.get_state("classify_response") == "high"
        assert fake.calls[0]["messages"] == [{"role": "user", "content": "Classify urgency of: server on fire"}]
        assert fake.calls[0]["agent"] == "workflow:classify"

    @pytest.mark.asyncio
    async def test_system_prompt_is_sent_as_a_system_message(self, fake):
        node = AINode("n", config={"prompt": "{{q}}", "system_prompt": "You answer in one word."})
        await run(node, q="status?")
        assert fake.calls[0]["messages"] == [
            {"role": "system", "content": "You answer in one word."},
            {"role": "user", "content": "status?"},
        ]

    @pytest.mark.asyncio
    async def test_model_temperature_and_max_tokens_reach_the_provider(self, fake):
        node = AINode("n", config={"prompt": "p", "model": "grok-custom", "temperature": 0.1, "max_tokens": 321})
        out = await run(node)
        call = fake.calls[0]
        assert (call["model"], call["temperature"], call["max_tokens"]) == ("grok-custom", 0.1, 321)
        assert out.data["model"] == "grok-custom"

    @pytest.mark.asyncio
    async def test_without_a_model_the_providers_default_is_used(self, fake, monkeypatch):
        monkeypatch.setenv("GROK_MODEL", "env-default-model")
        out = await run(AINode("n", config={"prompt": "p"}))
        assert fake.calls[0]["model"] == "env-default-model" and out.data["model"] == "env-default-model"

    @pytest.mark.asyncio
    async def test_provider_is_selected_by_the_node_not_the_environment(self, fake, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        monkeypatch.setenv("PRIORITY_PROVIDER", "grok")
        await run(AINode("n", config={"prompt": "p", "provider": "claude"}))
        assert fake.calls[0]["name"] == "claude"

    @pytest.mark.asyncio
    async def test_client_is_closed_even_when_the_call_fails(self):
        closed = []

        async def close(self):
            closed.append(True)

        failing = make_fake(fail_with="credit balance too low")
        with patch.object(GrokClient, "_call_provider", autospec=True, side_effect=failing), patch.object(
            GrokClient, "close", close
        ):
            with pytest.raises(RuntimeError):
                await run(AINode("n", config={"prompt": "p"}))
        assert closed == [True]


class TestFailures:
    @pytest.mark.asyncio
    async def test_provider_error_message_surfaces_and_fails_the_node(self):
        node = AINode("n", config={"prompt": "p"})
        failing = make_fake(fail_with="grok API error 402: credit balance too low")
        with patch.object(GrokClient, "_call_provider", autospec=True, side_effect=failing):
            with pytest.raises(RuntimeError, match="credit balance too low"):
                await run(node)
        assert node.status == NodeStatus.FAILED

    @pytest.mark.asyncio
    async def test_unknown_provider_and_missing_key_are_clear_errors(self, monkeypatch):
        with pytest.raises(ValueError, match="unknown or its API key is not set"):
            await run(AINode("n", config={"prompt": "p", "provider": "nonsense"}))

        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with pytest.raises(ValueError, match="claude"):
            await run(AINode("n", config={"prompt": "p", "provider": "claude"}))


class TestInAWorkflow:
    @pytest.mark.asyncio
    async def test_yaml_style_definition_runs_and_feeds_the_next_node(self, fake):
        from src.workflow import WorkflowEngine

        definition = {
            "name": "classify",
            "nodes": [
                {"id": "ask", "type": "ai", "config": {"prompt": "Urgency of {{message}}?"}},
                {
                    "id": "is_high",
                    "type": "conditional",
                    "config": {"conditions": [{"field": "ai_response", "operator": "==", "value": "high"}]},
                },
                {"id": "page", "type": "noop"},
                {"id": "ignore", "type": "noop"},
            ],
            "edges": [
                ["ask", "is_high"],
                {"from": "is_high", "to": "page", "condition": "true"},
                {"from": "is_high", "to": "ignore", "condition": "false"},
            ],
        }
        workflow = build_workflow(definition)
        result = await WorkflowEngine().execute(workflow, {"message": "disk full"})

        assert result["status"] == "success" and result["nodes_skipped"] == 1
        assert workflow.engine.nodes["page"].status == NodeStatus.SUCCESS
        assert workflow.engine.nodes["ignore"].status == NodeStatus.SKIPPED
