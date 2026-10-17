"""MessageBus.send_and_wait: request/response by correlation_id, without touching the caller's queue."""
import asyncio
from typing import Any, Dict, Optional
from unittest.mock import MagicMock

import pytest

from src.core.base_agent import BaseAgent
from src.core.message_bus import Message, MessageBus
from src.exceptions import MessageBusError


class EchoAgent(BaseAgent):
    async def process_message(self, message: Message) -> Optional[Dict[str, Any]]:
        if message.message_type == "silent":
            return None
        return {"echo": message.content.get("n")}


async def _started(agent):
    task = asyncio.create_task(agent.run())
    await asyncio.sleep(0.05)
    return task


async def _stopped(agent, task):
    agent.running = False
    task.cancel()
    try:
        await task
    except BaseException:
        pass


def _request(n=1, message_type="ask"):
    return Message(from_agent="caller", to_agent="ignored", message_type=message_type, content={"n": n})


@pytest.mark.asyncio
async def test_returns_the_replys_content():
    bus = MessageBus()
    bus.register_agent("caller")
    agent = EchoAgent("echo", bus, MagicMock(), {})
    task = await _started(agent)
    try:
        assert await bus.send_and_wait("echo", _request(7), timeout=3) == {"echo": 7}
    finally:
        await _stopped(agent, task)
    assert bus._awaiting_reply == {}


@pytest.mark.asyncio
async def test_concurrent_requests_get_their_own_replies():
    bus = MessageBus()
    bus.register_agent("caller")
    agent = EchoAgent("echo", bus, MagicMock(), {})
    task = await _started(agent)
    try:
        results = await asyncio.gather(*(bus.send_and_wait("echo", _request(n), timeout=3) for n in range(5)))
    finally:
        await _stopped(agent, task)
    assert [r["echo"] for r in results] == [0, 1, 2, 3, 4]


@pytest.mark.asyncio
async def test_timeout_raises_and_cleans_up():
    bus = MessageBus()
    bus.register_agent("caller")
    agent = EchoAgent("echo", bus, MagicMock(), {})  # registered but not running: nobody answers
    with pytest.raises(asyncio.TimeoutError):
        await bus.send_and_wait("echo", _request(), timeout=0.1)
    assert bus._awaiting_reply == {}


@pytest.mark.asyncio
async def test_unknown_target_raises_bus_error():
    bus = MessageBus()
    with pytest.raises(MessageBusError):
        await bus.send_and_wait("nobody", _request(), timeout=0.1)
    assert bus._awaiting_reply == {}


@pytest.mark.asyncio
async def test_reply_from_a_different_agent_does_not_resolve_the_request():
    bus = MessageBus()
    bus.register_agent("caller")
    bus.register_agent("echo")
    bus.register_agent("other")

    async def impostor():
        await asyncio.sleep(0.05)
        # same correlation id but not from the agent that was asked
        (corr,) = bus._awaiting_reply.keys()
        await bus.send(Message("other", "caller", "reply", {"echo": "wrong"}, correlation_id=corr))

    asyncio.create_task(impostor())
    with pytest.raises(asyncio.TimeoutError):
        await bus.send_and_wait("echo", _request(), timeout=0.3)


@pytest.mark.asyncio
async def test_reply_to_an_unregistered_sender_does_not_put_the_agent_in_error():
    """A fire-and-forget message from an agent with no inbox used to end in MessageBusError -> error state."""
    bus = MessageBus()
    agent = EchoAgent("echo", bus, MagicMock(), {})
    task = await _started(agent)
    try:
        # default reply address is "coordinator", which is not registered here
        await bus.send(Message(from_agent="ghost", to_agent="echo", message_type="ask", content={"n": 1}))
        await asyncio.sleep(0.2)
        assert agent.state.status != "error" and agent.state.error is None

        # still serving requests afterwards
        bus.register_agent("caller")
        assert await bus.send_and_wait("echo", _request(5), timeout=3) == {"echo": 5}
    finally:
        await _stopped(agent, task)
