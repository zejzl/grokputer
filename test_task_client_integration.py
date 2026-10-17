#!/usr/bin/env python3
"""
Test script for TaskClient integration with existing agents.
"""
import asyncio
import logging
from pathlib import Path
from src.core.message_bus import MessageBus
from src.observability.session_logger import SessionLogger
from src.agents.task_master import TaskMaster, TaskPriority
from src.agents.story_generation_agent import StoryGenerationAgent
from src.agents.character_analysis_agent import CharacterAnalysisAgent
from src.agents.coordinator import Coordinator
from src import config

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_task_client_integration():
    """Test TaskClient integration with multiple agents."""

    print("=== Testing TaskClient Integration ===\n")

    # Initialize components
    message_bus = MessageBus()
    session_logger = SessionLogger(
        session_id="task_client_integration", task="TaskClient integration test", log_dir=Path("./logs"), swarm_mode=True
    )

    # Start TaskMaster
    taskmaster = TaskMaster(message_bus, session_logger, {})
    taskmaster_task = asyncio.create_task(taskmaster.run())

    # Give TaskMaster time to start
    await asyncio.sleep(1)

    # Create agents with TaskClient enabled; ask for work every 3 seconds instead of the default 30
    agent_config = {**config.__dict__, "task_check_interval": 3.0}
    agents = []

    # Story Generation Agent
    story_agent = StoryGenerationAgent("story_agent", message_bus, session_logger, agent_config)
    agents.append(story_agent)

    # Character Analysis Agent
    char_agent = CharacterAnalysisAgent("char_agent", message_bus, session_logger, agent_config)
    agents.append(char_agent)

    # Coordinator Agent
    coord_agent = Coordinator(message_bus=message_bus, session_logger=session_logger, config=agent_config)
    agents.append(coord_agent)

    # Start agents
    agent_tasks = []
    for agent in agents:
        task = asyncio.create_task(agent.run())
        agent_tasks.append(task)

    # Let agents register and start
    await asyncio.sleep(3)

    # Create some test tasks
    print("Creating test tasks...")

    # Create tasks via TaskMaster
    test_tasks = [
        {
            "title": "Generate a short story about AI evolution",
            "description": "Write a 500-word story about artificial intelligence gaining consciousness and learning about human emotions.",
            "priority": "medium",
            "tags": ["story_generation", "creative_writing"],
            "required_capabilities": ["story_generation"],
        },
        {
            "title": "Analyze character motivations in a story",
            "description": "Analyze the character arc and motivations of a protagonist who discovers they have special abilities.",
            "priority": "medium",
            "tags": ["character_analysis", "literary_analysis"],
            "required_capabilities": ["character_analysis"],
        },
        {
            "title": "Coordinate a multi-agent creative writing project",
            "description": "Break down and coordinate the creation of a short story involving multiple characters with different backgrounds.",
            "priority": "high",
            "tags": ["task_coordination", "multi_agent"],
            "required_capabilities": ["task_coordination"],
        },
    ]

    # Add tasks to TaskMaster
    for task_data in test_tasks:
        created = taskmaster.task_registry.create_task(
            title=task_data["title"],
            description=task_data["description"],
            priority=TaskPriority(task_data["priority"]),
            tags=task_data["tags"],
            required_capabilities=task_data["required_capabilities"],
        )
        print(f"Created task: {created.task_id} - {task_data['title']}")

    # Let the system run for a bit to process tasks
    print("\nRunning task processing for 30 seconds...")
    await asyncio.sleep(30)

    # Check task status
    print("\nChecking task status...")
    tasks = [t.to_dict() for t in taskmaster.task_registry.get_all_tasks()]
    for task in tasks:
        status = task.get("status", "unknown")
        assigned_to = task.get("assigned_agent") or "unassigned"
        print(f"Task '{task['title'][:50]}...': {status} (assigned to: {assigned_to})")

    # Shutdown
    print("\nShutting down...")

    # Stop agents
    for agent in agents:
        await agent.stop()

    # Stop TaskMaster
    await taskmaster.stop()

    # Cancel all tasks
    for task in agent_tasks + [taskmaster_task]:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    print("Test completed!")


if __name__ == "__main__":
    asyncio.run(test_task_client_integration())
