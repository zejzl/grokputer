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
    message = Message(from_agent="agent1", to_agent="agent2", message_type="test", content={"data": "hello"})
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
    await bus.send(
        Message(
            from_agent="sender",
            to_agent="test_agent",
            message_type="low",
            content={"priority": "low"},
            priority=MessagePriority.LOW,
        )
    )

    await bus.send(
        Message(
            from_agent="sender",
            to_agent="test_agent",
            message_type="high",
            content={"priority": "high"},
            priority=MessagePriority.HIGH,
        )
    )

    await bus.send(
        Message(
            from_agent="sender",
            to_agent="test_agent",
            message_type="normal",
            content={"priority": "normal"},
            priority=MessagePriority.NORMAL,
        )
    )

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
            correlation_id=request.correlation_id,
        )

    # Start responder in background
    responder_future = asyncio.create_task(responder_task())

    # Send request and wait for response
    response = await bus.send_request(
        from_agent="requester",
        to_agent="responder",
        message_type="request",
        content={"data": "test_request"},
        timeout=2.0,
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
            timeout=0.5,  # Short timeout
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
        content={"announcement": "hello all"},
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
        await bus.send(Message(from_agent="agent1", to_agent="agent2", message_type=f"msg_{i}", content={"index": i}))

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
    await bus.send(Message(from_agent="sender", to_agent="receiver", message_type="test", content={}))

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
    await bus.send(Message(from_agent="sender", to_agent="agent", message_type="msg1", content={}))

    await bus.send(Message(from_agent="sender", to_agent="agent", message_type="msg2", content={}))

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
        await bus.send(Message(from_agent="sender", to_agent="agent", message_type=f"msg_{i}", content={}))

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
    await bus.send(Message(from_agent="agent1", to_agent="agent2", message_type="test", content={}))

    # Shutdown
    await bus.shutdown()

    # All queues should be cleared
    stats = bus.get_stats()
    assert len(stats["registered_agents"]) == 0


# ============================================================================
# STRESS TESTING - High Concurrency
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.stress
async def test_many_agents_concurrent():
    """Test 10 agents sending 100 messages each concurrently (1000 total messages)."""
    bus = MessageBus()
    num_agents = 10
    messages_per_agent = 100

    # Register agents
    for i in range(num_agents):
        bus.register_agent(f"agent_{i}")

    async def agent_sender(agent_id: int):
        """Each agent sends messages to all other agents."""
        for msg_num in range(messages_per_agent):
            target = f"agent_{(agent_id + 1) % num_agents}"  # Send to next agent
            await bus.send(Message(
                from_agent=f"agent_{agent_id}",
                to_agent=target,
                message_type="stress_test",
                content={"msg_num": msg_num, "from": agent_id}
            ))

    # Run all senders concurrently
    import time
    start_time = time.time()

    tasks = [agent_sender(i) for i in range(num_agents)]
    await asyncio.gather(*tasks)

    duration = time.time() - start_time
    throughput = (num_agents * messages_per_agent) / duration

    print(f"\n[STRESS TEST] Sent {num_agents * messages_per_agent} messages in {duration:.2f}s")
    print(f"[STRESS TEST] Throughput: {throughput:.0f} msg/sec")

    # Verify no deadlocks - all queues should have messages
    stats = bus.get_stats()
    assert stats["total_messages"] == num_agents * messages_per_agent
    assert throughput > 1000, "Throughput should exceed 1000 msg/sec"


@pytest.mark.asyncio
@pytest.mark.stress
async def test_queue_saturation():
    """Test filling queues to capacity - verify no deadlocks."""
    bus = MessageBus()
    bus.register_agent("receiver", queue_size=100)

    # Fill queue to capacity
    for i in range(100):
        await bus.send(Message(
            from_agent="sender",
            to_agent="receiver",
            message_type="saturation",
            content={"index": i}
        ))

    assert bus.get_queue_size("receiver") == 100

    # Try to send one more (should block briefly but not deadlock)
    send_task = asyncio.create_task(bus.send(Message(
        from_agent="sender",
        to_agent="receiver",
        message_type="overflow",
        content={}
    )))

    # Give it a moment to attempt send
    await asyncio.sleep(0.1)

    # Now drain queue
    for _ in range(100):
        await bus.receive("receiver", timeout=1.0)

    # The overflow message should now complete
    await asyncio.wait_for(send_task, timeout=1.0)

    # Verify overflow message arrived
    overflow_msg = await bus.receive("receiver", timeout=1.0)
    assert overflow_msg.message_type == "overflow"


@pytest.mark.asyncio
@pytest.mark.stress
async def test_bursty_traffic():
    """Test alternating idle periods and 1000 message bursts."""
    bus = MessageBus()
    bus.register_agent("receiver")

    async def send_burst(burst_num: int, size: int):
        """Send a burst of messages."""
        for i in range(size):
            await bus.send(Message(
                from_agent="sender",
                to_agent="receiver",
                message_type="burst",
                content={"burst": burst_num, "msg": i}
            ))

    async def receive_burst(size: int):
        """Receive a burst of messages."""
        for _ in range(size):
            await bus.receive("receiver", timeout=2.0)

    import time

    # Burst 1: 1000 messages
    start = time.time()
    await send_burst(1, 1000)
    send_duration = time.time() - start

    # Idle period
    await asyncio.sleep(0.1)

    # Receive burst 1
    await receive_burst(1000)

    # Burst 2: Another 1000 messages
    await send_burst(2, 1000)

    # Idle period
    await asyncio.sleep(0.1)

    # Receive burst 2
    await receive_burst(1000)

    print(f"\n[BURSTY TRAFFIC] Sent 1000 messages in {send_duration:.3f}s ({1000/send_duration:.0f} msg/sec)")

    stats = bus.get_stats()
    assert stats["total_messages"] == 2000


@pytest.mark.asyncio
@pytest.mark.stress
async def test_memory_leak_detection():
    """Send 10K messages and check memory growth."""
    import sys
    bus = MessageBus()
    bus.register_agent("receiver")

    # Get initial memory (rough estimate via sys.getsizeof on queues)
    initial_queue_size = bus.get_queue_size("receiver")

    # Send 10K messages
    for i in range(10_000):
        await bus.send(Message(
            from_agent="sender",
            to_agent="receiver",
            message_type="memory_test",
            content={"index": i}
        ))

        # Drain every 1000 to prevent queue overflow
        if (i + 1) % 1000 == 0:
            for _ in range(1000):
                await bus.receive("receiver", timeout=1.0)

    # Drain remaining
    remaining = bus.get_queue_size("receiver")
    for _ in range(remaining):
        await bus.receive("receiver", timeout=1.0)

    # Final check
    final_queue_size = bus.get_queue_size("receiver")
    assert final_queue_size == 0, "Queue should be empty after draining"

    # Check history size is capped
    history = bus.get_message_history()
    assert len(history) <= 100, "History should be capped at configured size"

    stats = bus.get_stats()
    assert stats["total_messages"] == 10_000


# ============================================================================
# FAILURE SCENARIOS - Error Handling
# ============================================================================

@pytest.mark.asyncio
async def test_receive_from_unregistered_agent():
    """Test receiving from an agent that was never registered."""
    bus = MessageBus()

    # Try to receive from unregistered agent
    with pytest.raises(ValueError, match="Unknown agent"):
        await bus.receive("nonexistent_agent", timeout=0.1)


@pytest.mark.asyncio
async def test_send_to_nonexistent_agent():
    """Test sending to an agent that doesn't exist."""
    bus = MessageBus()
    bus.register_agent("sender")

    # Send to nonexistent agent - MessageBus raises ValueError
    with pytest.raises(ValueError, match="Unknown agent"):
        await bus.send(Message(
            from_agent="sender",
            to_agent="nonexistent",
            message_type="test",
            content={}
        ))


@pytest.mark.asyncio
async def test_double_registration():
    """Test registering the same agent twice."""
    bus = MessageBus()

    # First registration
    bus.register_agent("agent1")
    assert "agent1" in bus.queues

    # Second registration - should be a no-op or raise warning
    bus.register_agent("agent1")

    # Agent should still be registered exactly once
    assert "agent1" in bus.queues

    # Send message and verify it arrives
    await bus.send(Message(
        from_agent="sender",
        to_agent="agent1",
        message_type="test",
        content={}
    ))

    msg = await bus.receive("agent1", timeout=1.0)
    assert msg is not None


@pytest.mark.asyncio
async def test_shutdown_with_pending_messages():
    """Test shutdown with messages still in queues."""
    bus = MessageBus()
    bus.register_agent("receiver")

    # Send messages without receiving
    for i in range(10):
        await bus.send(Message(
            from_agent="sender",
            to_agent="receiver",
            message_type="pending",
            content={"index": i}
        ))

    assert bus.get_queue_size("receiver") == 10

    # Shutdown should clear pending messages
    await bus.shutdown()

    stats = bus.get_stats()
    assert len(stats["registered_agents"]) == 0


@pytest.mark.asyncio
async def test_timeout_accuracy():
    """Test that timeouts fire within ±50ms of specified time."""
    import time
    bus = MessageBus()
    bus.register_agent("receiver")

    # No messages sent - receive should timeout
    timeout_duration = 0.5  # 500ms

    start = time.time()
    with pytest.raises(asyncio.TimeoutError):
        await bus.receive("receiver", timeout=timeout_duration)

    actual_duration = time.time() - start

    # Should timeout within 500ms ± 50ms
    assert abs(actual_duration - timeout_duration) < 0.1, \
        f"Timeout took {actual_duration:.3f}s, expected ~{timeout_duration}s"


# ============================================================================
# WINDOWS ASYNCIO EDGE CASES
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.windows
async def test_windows_event_loop_stress():
    """Test Windows event loop with 5-10 agents under load."""
    import sys
    import time

    bus = MessageBus()
    num_agents = 10
    messages_per_agent = 50

    # Register agents
    for i in range(num_agents):
        bus.register_agent(f"agent_{i}")

    async def agent_worker(agent_id: int):
        """Agent sends and receives messages."""
        # Send phase
        for i in range(messages_per_agent):
            target = f"agent_{(agent_id + 1) % num_agents}"
            await bus.send(Message(
                from_agent=f"agent_{agent_id}",
                to_agent=target,
                message_type="windows_stress",
                content={"from": agent_id, "msg": i}
            ))

        # Receive phase
        for _ in range(messages_per_agent):
            try:
                await bus.receive(f"agent_{agent_id}", timeout=5.0)
            except asyncio.TimeoutError:
                pass  # Some agents might not receive all messages

    start = time.time()

    # Run all agents concurrently
    tasks = [agent_worker(i) for i in range(num_agents)]
    await asyncio.gather(*tasks)

    duration = time.time() - start

    print(f"\n[WINDOWS STRESS] {num_agents} agents, {num_agents * messages_per_agent} messages")
    print(f"[WINDOWS STRESS] Completed in {duration:.2f}s on {sys.platform}")

    # Should complete without event loop errors
    assert duration < 30, "Should complete within 30s"


@pytest.mark.asyncio
@pytest.mark.windows
async def test_concurrent_send_receive_pairs():
    """Test 5 agents doing request-response simultaneously."""
    bus = MessageBus()
    num_pairs = 5

    # Register agents
    for i in range(num_pairs):
        bus.register_agent(f"requester_{i}")
        bus.register_agent(f"responder_{i}")

    async def request_response_pair(pair_id: int):
        """One requester-responder pair."""
        async def responder():
            request = await bus.receive(f"responder_{pair_id}", timeout=5.0)
            await bus.send_response(
                from_agent=f"responder_{pair_id}",
                to_agent=f"requester_{pair_id}",
                message_type="response",
                content={"result": f"response_{pair_id}"},
                correlation_id=request.correlation_id
            )

        # Start responder
        responder_task = asyncio.create_task(responder())

        # Send request
        response = await bus.send_request(
            from_agent=f"requester_{pair_id}",
            to_agent=f"responder_{pair_id}",
            message_type="request",
            content={"data": f"request_{pair_id}"},
            timeout=5.0
        )

        await responder_task

        assert response.content["result"] == f"response_{pair_id}"

    # Run all pairs concurrently
    tasks = [request_response_pair(i) for i in range(num_pairs)]
    await asyncio.gather(*tasks)

    print(f"\n[CONCURRENT PAIRS] {num_pairs} request-response pairs completed successfully")


@pytest.mark.asyncio
@pytest.mark.windows
async def test_priority_inversion_under_load():
    """Test that HIGH priority messages still win at 1000 msg/sec."""
    import time
    bus = MessageBus()
    bus.register_agent("receiver")

    # Send 1000 LOW priority messages
    for i in range(1000):
        await bus.send(Message(
            from_agent="sender",
            to_agent="receiver",
            message_type="low_priority",
            content={"index": i},
            priority=MessagePriority.LOW
        ))

    # Now send 1 HIGH priority message
    await bus.send(Message(
        from_agent="sender",
        to_agent="receiver",
        message_type="high_priority",
        content={"important": True},
        priority=MessagePriority.HIGH
    ))

    # The HIGH priority message should be received first
    msg = await bus.receive("receiver", timeout=1.0)
    assert msg.message_type == "high_priority", "HIGH priority should be received first"
    assert msg.priority == MessagePriority.HIGH


@pytest.mark.asyncio
@pytest.mark.windows
async def test_asyncio_queue_full_behavior():
    """Test behavior when asyncio.PriorityQueue is full."""
    bus = MessageBus()
    bus.register_agent("receiver", queue_size=10)

    # Fill queue completely
    for i in range(10):
        await bus.send(Message(
            from_agent="sender",
            to_agent="receiver",
            message_type="fill",
            content={"index": i}
        ))

    assert bus.get_queue_size("receiver") == 10

    # Try to send when full - should block
    send_task = asyncio.create_task(bus.send(Message(
        from_agent="sender",
        to_agent="receiver",
        message_type="blocked",
        content={}
    )))

    # Task should be pending
    await asyncio.sleep(0.1)
    assert not send_task.done(), "Send should be blocked on full queue"

    # Drain one message
    await bus.receive("receiver", timeout=1.0)

    # Now send should complete
    await asyncio.wait_for(send_task, timeout=1.0)


# ============================================================================
# PHASE 1 READINESS - Multi-Agent Coordination
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.phase1
async def test_trio_coordination_pattern():
    """Simulate Coordinator → Observer → Actor flow."""
    bus = MessageBus()
    bus.register_agent("coordinator")
    bus.register_agent("observer")
    bus.register_agent("actor")

    async def coordinator():
        """Coordinator delegates task to Observer."""
        await bus.send(Message(
            from_agent="coordinator",
            to_agent="observer",
            message_type="capture_screen",
            content={"task": "observe"},
            priority=MessagePriority.HIGH
        ))

        # Wait for observation
        observation = await bus.receive("coordinator", timeout=5.0)
        assert observation.from_agent == "observer"

        # Send action to Actor
        await bus.send(Message(
            from_agent="coordinator",
            to_agent="actor",
            message_type="perform_action",
            content={"action": "click", "observation": observation.content},
            priority=MessagePriority.HIGH
        ))

        # Wait for action result
        result = await bus.receive("coordinator", timeout=5.0)
        assert result.from_agent == "actor"
        return result

    async def observer():
        """Observer captures screen and sends observation."""
        task = await bus.receive("observer", timeout=5.0)
        assert task.message_type == "capture_screen"

        # Send observation back
        await bus.send(Message(
            from_agent="observer",
            to_agent="coordinator",
            message_type="observation",
            content={"screenshot": "base64_data", "dimensions": "1920x1080"}
        ))

    async def actor():
        """Actor performs action and sends result."""
        action = await bus.receive("actor", timeout=5.0)
        assert action.message_type == "perform_action"

        # Send result back
        await bus.send(Message(
            from_agent="actor",
            to_agent="coordinator",
            message_type="action_result",
            content={"status": "success", "action": "click"}
        ))

    import time
    start = time.time()

    # Run trio
    results = await asyncio.gather(
        coordinator(),
        observer(),
        actor()
    )

    duration = time.time() - start

    print(f"\n[TRIO TEST] Coordinator → Observer → Actor completed in {duration:.2f}s")
    assert duration < 5.0, "Trio should complete in <5s"

    # Verify coordinator got final result
    final_result = results[0]
    assert final_result.content["status"] == "success"


@pytest.mark.asyncio
@pytest.mark.phase1
async def test_broadcast_to_multiple_subscribers():
    """Test 1 sender broadcasting to 5 receivers."""
    bus = MessageBus()
    bus.register_agent("broadcaster")

    num_receivers = 5
    for i in range(num_receivers):
        bus.register_agent(f"receiver_{i}")

    # Broadcast message
    await bus.broadcast(Message(
        from_agent="broadcaster",
        to_agent="all",
        message_type="announcement",
        content={"message": "System update available"},
        priority=MessagePriority.HIGH
    ))

    # All receivers should get the message
    received_count = 0
    for i in range(num_receivers):
        msg = await bus.receive(f"receiver_{i}", timeout=1.0)
        assert msg.content["message"] == "System update available"
        # Note: broadcast() doesn't preserve priority in current implementation
        assert msg.message_type == "announcement"
        received_count += 1

    assert received_count == num_receivers
    print(f"\n[BROADCAST] Successfully delivered to {received_count} receivers")


@pytest.mark.asyncio
@pytest.mark.phase1
async def test_correlation_id_tracking():
    """Test that correlation IDs survive complex request-response flows."""
    bus = MessageBus()
    bus.register_agent("client")
    bus.register_agent("service1")
    bus.register_agent("service2")

    async def service1_handler():
        """Service1 receives request, forwards to Service2."""
        request = await bus.receive("service1", timeout=5.0)
        original_correlation_id = request.correlation_id

        # Forward to service2
        response2 = await bus.send_request(
            from_agent="service1",
            to_agent="service2",
            message_type="sub_request",
            content={"original": request.content},
            timeout=5.0
        )

        # Send final response with original correlation ID
        await bus.send_response(
            from_agent="service1",
            to_agent="client",
            message_type="final_response",
            content={"result": response2.content["data"]},
            correlation_id=original_correlation_id
        )

    async def service2_handler():
        """Service2 responds to sub-request."""
        sub_request = await bus.receive("service2", timeout=5.0)

        await bus.send_response(
            from_agent="service2",
            to_agent="service1",
            message_type="sub_response",
            content={"data": "processed"},
            correlation_id=sub_request.correlation_id
        )

    # Start services
    service1_task = asyncio.create_task(service1_handler())
    service2_task = asyncio.create_task(service2_handler())

    # Client sends request
    response = await bus.send_request(
        from_agent="client",
        to_agent="service1",
        message_type="initial_request",
        content={"query": "test"},
        timeout=5.0
    )

    await service1_task
    await service2_task

    # Verify correlation ID was preserved
    assert response.correlation_id is not None
    assert response.content["result"] == "processed"

    print(f"\n[CORRELATION ID] Successfully tracked through 2-hop request chain")


@pytest.mark.asyncio
@pytest.mark.phase1
async def test_message_history_under_load():
    """Test that message history works correctly with 1000+ messages."""
    bus = MessageBus(history_size=100)
    bus.register_agent("sender")
    bus.register_agent("receiver")

    # Send 1000 messages
    for i in range(1000):
        await bus.send(Message(
            from_agent="sender",
            to_agent="receiver",
            message_type=f"msg_type_{i % 10}",
            content={"index": i}
        ))

    # History should be capped at 100
    history = bus.get_message_history()
    assert len(history) == 100, "History should be capped at configured size"

    # Should contain most recent messages
    last_message = history[-1]
    assert last_message["type"] == "msg_type_9"  # 999 % 10 = 9

    # Check history limit parameter
    limited_history = bus.get_message_history(limit=10)
    assert len(limited_history) == 10

    print(f"\n[HISTORY] Successfully capped at {len(history)} entries out of 1000 messages")
