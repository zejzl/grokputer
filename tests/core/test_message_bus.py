"""
Unit tests for MessageBus with priorities and request-response pattern.
"""

import asyncio
import pytest
from src.core.message_bus import MessageBus, Message, MessagePriority


@pytest.mark.asyncio
async def test_message_bus_basic_send_receive():
    """Test basic message sending and receiving."""
    bus = MessageBus()
    bus.register_agent("agent1")
    bus.register_agent("agent2")

    # Send message
    message = Message(
        from_agent="agent1",
        to_agent="agent2",
        message_type="test",
        content={"data": "hello"}
    )
    await bus.send(message)

    # Receive message
    received = await bus.receive("agent2", timeout=1.0)

    assert received.from_agent == "agent1"
    assert received.to_agent == "agent2"
    assert received.message_type == "test"
    assert received.content["data"] == "hello"


@pytest.mark.asyncio
async def test_message_priority_ordering():
    """Test that high-priority messages are received first."""
    bus = MessageBus()
    bus.register_agent("test_agent")

    # Send messages with different priorities
    await bus.send(Message(
        from_agent="sender",
        to_agent="test_agent",
        message_type="low",
        content={"priority": "low"},
        priority=MessagePriority.LOW
    ))

    await bus.send(Message(
        from_agent="sender",
        to_agent="test_agent",
        message_type="high",
        content={"priority": "high"},
        priority=MessagePriority.HIGH
    ))

    await bus.send(Message(
        from_agent="sender",
        to_agent="test_agent",
        message_type="normal",
        content={"priority": "normal"},
        priority=MessagePriority.NORMAL
    ))

    # Receive messages - should get HIGH, NORMAL, LOW
    msg1 = await bus.receive("test_agent", timeout=1.0)
    assert msg1.content["priority"] == "high"

    msg2 = await bus.receive("test_agent", timeout=1.0)
    assert msg2.content["priority"] == "normal"

    msg3 = await bus.receive("test_agent", timeout=1.0)
    assert msg3.content["priority"] == "low"


@pytest.mark.asyncio
async def test_request_response_pattern():
    """Test request-response pattern with correlation IDs."""
    bus = MessageBus()
    bus.register_agent("requester")
    bus.register_agent("responder")

    async def responder_task():
        """Simulated responder that waits for request and sends response."""
        # Wait for request
        request = await bus.receive("responder", timeout=2.0)

        # Send response with same correlation ID
        await bus.send_response(
            from_agent="responder",
            to_agent="requester",
            message_type="response",
            content={"result": "success", "request_data": request.content["data"]},
            correlation_id=request.correlation_id
        )

    # Start responder in background
    responder_future = asyncio.create_task(responder_task())

    # Send request and wait for response
    response = await bus.send_request(
        from_agent="requester",
        to_agent="responder",
        message_type="request",
        content={"data": "test_request"},
        timeout=2.0
    )

    assert response.content["result"] == "success"
    assert response.content["request_data"] == "test_request"
    assert response.correlation_id is not None

    await responder_future


@pytest.mark.asyncio
async def test_request_timeout():
    """Test that request times out if no response received."""
    bus = MessageBus()
    bus.register_agent("requester")
    bus.register_agent("responder")

    # Send request but responder never responds
    with pytest.raises(asyncio.TimeoutError):
        await bus.send_request(
            from_agent="requester",
            to_agent="responder",
            message_type="request",
            content={"data": "test"},
            timeout=0.5  # Short timeout
        )


@pytest.mark.asyncio
async def test_broadcast():
    """Test broadcasting messages to multiple agents."""
    bus = MessageBus()
    bus.register_agent("sender")
    bus.register_agent("receiver1")
    bus.register_agent("receiver2")
    bus.register_agent("receiver3")

    # Broadcast message
    message = Message(
        from_agent="sender",
        to_agent="all",  # Will be overwritten per recipient
        message_type="broadcast",
        content={"announcement": "hello all"}
    )
    await bus.broadcast(message)

    # All receivers should get the message
    msg1 = await bus.receive("receiver1", timeout=1.0)
    assert msg1.content["announcement"] == "hello all"

    msg2 = await bus.receive("receiver2", timeout=1.0)
    assert msg2.content["announcement"] == "hello all"

    msg3 = await bus.receive("receiver3", timeout=1.0)
    assert msg3.content["announcement"] == "hello all"

    # Sender should not receive its own broadcast
    with pytest.raises(asyncio.TimeoutError):
        await bus.receive("sender", timeout=0.1)


@pytest.mark.asyncio
async def test_message_history():
    """Test message history tracking."""
    bus = MessageBus(history_size=10)
    bus.register_agent("agent1")
    bus.register_agent("agent2")

    # Send multiple messages
    for i in range(5):
        await bus.send(Message(
            from_agent="agent1",
            to_agent="agent2",
            message_type=f"msg_{i}",
            content={"index": i}
        ))

    # Check history
    history = bus.get_message_history()
    assert len(history) == 5
    assert history[-1]["type"] == "msg_4"


@pytest.mark.asyncio
async def test_stats_tracking():
    """Test statistics tracking including latency."""
    bus = MessageBus()
    bus.register_agent("sender")
    bus.register_agent("receiver")

    # Send and receive message
    await bus.send(Message(
        from_agent="sender",
        to_agent="receiver",
        message_type="test",
        content={}
    ))

    await bus.receive("receiver", timeout=1.0)

    # Check stats
    stats = bus.get_stats()
    assert stats["total_messages"] == 1
    assert "test" in stats["latency_by_type"]
    assert stats["latency_by_type"]["test"]["count"] == 1
    assert stats["latency_by_type"]["test"]["avg_ms"] >= 0


@pytest.mark.asyncio
async def test_queue_size_limits():
    """Test queue size management."""
    bus = MessageBus()
    bus.register_agent("agent", queue_size=2)  # Max 2 messages

    # Send 2 messages (should succeed)
    await bus.send(Message(
        from_agent="sender",
        to_agent="agent",
        message_type="msg1",
        content={}
    ))

    await bus.send(Message(
        from_agent="sender",
        to_agent="agent",
        message_type="msg2",
        content={}
    ))

    # Queue should be full now
    assert bus.get_queue_size("agent") == 2

    # Receive one to make space
    await bus.receive("agent", timeout=1.0)
    assert bus.get_queue_size("agent") == 1


@pytest.mark.asyncio
async def test_clear_queue():
    """Test clearing agent queues."""
    bus = MessageBus()
    bus.register_agent("agent")

    # Send messages
    for i in range(3):
        await bus.send(Message(
            from_agent="sender",
            to_agent="agent",
            message_type=f"msg_{i}",
            content={}
        ))

    assert bus.get_queue_size("agent") == 3

    # Clear queue
    bus.clear_queue("agent")
    assert bus.get_queue_size("agent") == 0


@pytest.mark.asyncio
async def test_shutdown():
    """Test graceful shutdown."""
    bus = MessageBus()
    bus.register_agent("agent1")
    bus.register_agent("agent2")

    # Send some messages
    await bus.send(Message(
        from_agent="agent1",
        to_agent="agent2",
        message_type="test",
        content={}
    ))

    # Shutdown
    await bus.shutdown()

    # All queues should be cleared
    stats = bus.get_stats()
    assert len(stats["registered_agents"]) == 0
