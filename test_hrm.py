import asyncio
from pathlib import Path
from src.core.message_bus import MessageBus, Message, MessagePriority
from src.agents.hrm_reasoner import HRMReasonerAgent
from src.observability.session_logger import SessionLogger

async def test_hrm_reasoner():
    # Setup
    bus = MessageBus()
    logger = SessionLogger(session_id="test", task="test_hrm", log_dir=Path("logs"))

    # Create HRM agent
    hrm_agent = HRMReasonerAgent(
        agent_id="hrm_reasoner",
        message_bus=bus,
        session_logger=logger,
        config={"debug": True}
    )

    # Register agents
    bus.register_agent("hrm_reasoner")
    bus.register_agent("test_user")

    # Start agent in background
    agent_task = asyncio.create_task(hrm_agent.run())

    # Send a reasoning task
    task_message = Message(
        from_agent="test_user",
        to_agent="hrm_reasoner",
        message_type="reasoning_task",
        content={"task": "Solve: 2 + 2", "task_id": "test_001"},
        priority=MessagePriority.NORMAL
    )

    await bus.send(task_message)

    # Wait for response
    response = await bus.receive("test_user", timeout=5.0)

    print(f"HRM Response: {response.content}")

    # Stop agent
    agent_task.cancel()
    try:
        await agent_task
    except asyncio.CancelledError:
        pass

asyncio.run(test_hrm_reasoner())