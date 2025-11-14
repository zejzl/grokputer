import asyncio
import time
from pathlib import Path
from src.core.message_bus import MessageBus, Message, MessagePriority
from src.observability.session_logger import SessionLogger

async def throughput_test():
    # Setup
    bus = MessageBus()
    logger = SessionLogger(session_id="throughput_test", task="throughput", log_dir=Path("logs"))

    # Register multiple agents
    num_agents = 10
    for i in range(num_agents):
        bus.register_agent(f"agent_{i}")

    # Create simple agents that just echo messages
    async def echo_agent(agent_id: str):
        while True:
            try:
                msg = await bus.receive(agent_id, timeout=1.0)
                if msg:
                    # Echo back to sender
                    response = Message(
                        from_agent=agent_id,
                        to_agent=msg.from_agent,
                        message_type="echo_response",
                        content={"echo": msg.content, "timestamp": time.time()},
                        priority=MessagePriority.NORMAL
                    )
                    await bus.send(response)
            except asyncio.TimeoutError:
                continue

    # Start echo agents
    agent_tasks = []
    for i in range(num_agents):
        task = asyncio.create_task(echo_agent(f"agent_{i}"))
        agent_tasks.append(task)

    # Test throughput
    test_sender = "test_sender"
    bus.register_agent(test_sender)

    num_messages = 1000
    start_time = time.time()

    # Send messages in parallel
    send_tasks = []
    for i in range(num_messages):
        target_agent = f"agent_{i % num_agents}"
        msg = Message(
            from_agent=test_sender,
            to_agent=target_agent,
            message_type="test_message",
            content={"msg_id": i, "data": "test"},
            priority=MessagePriority.NORMAL
        )
        send_tasks.append(bus.send(msg))

    await asyncio.gather(*send_tasks)

    # Wait for responses
    responses_received = 0
    timeout_start = time.time()
    while responses_received < num_messages and (time.time() - timeout_start) < 10.0:
        try:
            msg = await bus.receive(test_sender, timeout=0.1)
            if msg and msg.message_type == "echo_response":
                responses_received += 1
        except asyncio.TimeoutError:
            continue

    end_time = time.time()
    total_time = end_time - start_time

    messages_per_second = num_messages / total_time if total_time > 0 else 0

    print(f"MessageBus Throughput Test Results:")
    print(f"Messages sent: {num_messages}")
    print(f"Responses received: {responses_received}")
    print(f"Total time: {total_time:.2f} seconds")
    print(f"Messages per second: {messages_per_second:.2f}")

    # Cleanup
    for task in agent_tasks:
        task.cancel()
    try:
        await asyncio.gather(*agent_tasks, return_exceptions=True)
    except asyncio.CancelledError:
        pass

if __name__ == "__main__":
    asyncio.run(throughput_test())