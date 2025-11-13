#!/usr/bin/env python3
"""
Task Management System Demo

Demonstrates the new efficient task delegation system for Grokputer Pantheon.
Shows how agents can request tasks, update status, and coordinate through TaskMaster.
"""

import asyncio
import logging
from pathlib import Path
from src.core.message_bus import MessageBus, Message, MessagePriority
from src.observability.session_logger import SessionLogger
from src.agents.taskmaster import TaskMaster
from src.core.task_client import TaskClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DemoAgent:
    """Demo agent that uses TaskClient to interact with TaskMaster."""

    def __init__(self, agent_id: str, message_bus: MessageBus, capabilities: list):
        self.agent_id = agent_id
        self.task_client = TaskClient(agent_id, message_bus)
        self.capabilities = capabilities
        self.current_task = None

    async def initialize(self):
        """Initialize agent and register with TaskMaster."""
        await self.task_client.register_capabilities(self.capabilities)
        logger.info(f"[{self.agent_id}] Initialized with capabilities: {self.capabilities}")

    async def run(self):
        """Main agent loop."""
        # Start heartbeat and idle task loops
        heartbeat_task = asyncio.create_task(self.task_client.start_heartbeat_loop(interval=10))
        idle_task = asyncio.create_task(self.task_client.start_idle_task_loop(check_interval=5))

        try:
            while True:
                # Check for assigned tasks
                current_tasks = self.task_client.get_current_tasks()
                if current_tasks:
                    for task in current_tasks:
                        if task["status"] == "assigned":
                            await self.process_task(task)
                await asyncio.sleep(2)

        except KeyboardInterrupt:
            logger.info(f"[{self.agent_id}] Shutting down")
        finally:
            heartbeat_task.cancel()
            idle_task.cancel()

    async def process_task(self, task: dict):
        """Process an assigned task."""
        task_id = task["task_id"]
        title = task["title"]

        logger.info(f"[{self.agent_id}] Processing task: {title}")

        # Update status to in_progress
        await self.task_client.update_task_status(task_id, "in_progress", "Starting work")

        # Simulate work
        await asyncio.sleep(3)

        # Complete task
        await self.task_client.update_task_status(task_id, "completed", f"Task {title} completed successfully")
        logger.info(f"[{self.agent_id}] Completed task: {title}")


async def demo_task_management():
    """Demonstrate the task management system."""
    logger.info("🚀 Starting Task Management System Demo")

    # Initialize core systems
    message_bus = MessageBus()

    session_logger = SessionLogger(
        session_id="task_demo", task="Task Management System Demo", log_dir=Path("./logs"), swarm_mode=True
    )

    # Create TaskMaster
    taskmaster_config = {"auto_delegate": True, "max_agent_tasks": 2, "heartbeat_timeout": 30}
    taskmaster = TaskMaster(message_bus, session_logger, taskmaster_config)

    # Start TaskMaster
    taskmaster_task = asyncio.create_task(taskmaster.run())

    # Wait for TaskMaster to initialize
    await asyncio.sleep(1)

    # Create demo agents
    agents = []
    agent_configs = [
        ("agent_alpha", ["coding", "testing", "debugging"]),
        ("agent_beta", ["analysis", "research", "documentation"]),
        ("agent_gamma", ["deployment", "monitoring", "optimization"]),
    ]

    for agent_id, capabilities in agent_configs:
        agent = DemoAgent(agent_id, message_bus, capabilities)
        await agent.initialize()
        agents.append(agent)

    # Start agents
    agent_tasks = [asyncio.create_task(agent.run()) for agent in agents]

    # Create some demo tasks
    logger.info("📋 Creating demo tasks...")

    # Create tasks via TaskMaster (normally this would be done by a coordinator or user)
    task_message = Message(
        from_agent="demo",
        to_agent="taskmaster",
        message_type="create_task",
        content={
            "title": "Fix critical security vulnerability",
            "description": "Address CVE-2024-12345 in authentication module",
            "priority": "critical",
            "tags": ["security", "urgent"],
        },
        priority=MessagePriority.HIGH,
    )
    await message_bus.send(task_message)

    task2 = Message(
        from_agent="demo",
        to_agent="taskmaster",
        message_type="create_task",
        content={
            "title": "Implement user dashboard",
            "description": "Create responsive dashboard with real-time metrics",
            "priority": "high",
            "tags": ["frontend", "ui"],
        },
        priority=MessagePriority.NORMAL,
    )
    await message_bus.send(task2)

    task3 = Message(
        from_agent="demo",
        to_agent="taskmaster",
        message_type="create_task",
        content={
            "title": "Write API documentation",
            "description": "Document all REST endpoints with examples",
            "priority": "medium",
            "tags": ["documentation", "api"],
        },
        priority=MessagePriority.NORMAL,
    )
    await message_bus.send(task3)

    task4 = Message(
        from_agent="demo",
        to_agent="taskmaster",
        message_type="create_task",
        content={
            "title": "Optimize database queries",
            "description": "Improve slow queries in user analytics",
            "priority": "medium",
            "tags": ["database", "performance"],
        },
        priority=MessagePriority.NORMAL,
    )
    await message_bus.send(task4)

    task5 = Message(
        from_agent="demo",
        to_agent="taskmaster",
        message_type="create_task",
        content={
            "title": "Update dependencies",
            "description": "Upgrade to latest secure versions",
            "priority": "low",
            "tags": ["maintenance", "security"],
        },
        priority=MessagePriority.NORMAL,
    )
    await message_bus.send(task5)

    # Let the system run for a while to demonstrate task delegation
    logger.info("⏳ Running task delegation demo for 30 seconds...")
    await asyncio.sleep(30)

    # Get system stats
    logger.info("📊 Getting system statistics...")
    stats_message = Message(
        from_agent="demo",
        to_agent="taskmaster",
        message_type="get_system_stats",
        content={},
        priority=MessagePriority.NORMAL,
    )
    await message_bus.send(stats_message)
    # Note: In a real implementation, we'd wait for a response, but for demo we just send

    # Shutdown
    logger.info("🛑 Shutting down demo...")

    # Cancel all tasks
    taskmaster_task.cancel()
    for task in agent_tasks:
        task.cancel()

    try:
        await taskmaster_task
        await asyncio.gather(*agent_tasks, return_exceptions=True)
    except asyncio.CancelledError:
        pass

    logger.info("✅ Task Management System Demo completed!")


if __name__ == "__main__":
    asyncio.run(demo_task_management())
