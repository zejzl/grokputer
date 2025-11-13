#!/usr/bin/env python3
"""
Test script for CharacterAnalysisAgent and StoryGenerationAgent
"""

import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agents.character_analysis_agent import CharacterAnalysisAgent
from src.agents.story_generation_agent import StoryGenerationAgent
from src.core.message_bus import MessageBus, Message, MessagePriority
from src.observability.session_logger import SessionLogger


class MockSessionLogger:
    def log_agent_start(self, agent_id):
        pass

    def log_agent_activity(self, agent_id, activity):
        pass

    def log_session_end(self):
        pass


async def test_character_analysis():
    """Test character analysis functionality."""
    print("Testing CharacterAnalysisAgent...")

    # Create mock dependencies
    message_bus = MessageBus()
    session_logger = MockSessionLogger()
    config = {"debug": True}

    # Create agent
    agent = CharacterAnalysisAgent(
        agent_id="test_character_analyzer", message_bus=message_bus, session_logger=session_logger, config=config
    )

    # Test character analysis
    character_data = {
        "name": "Raven",
        "description": "A powerful witch with unlimited magical abilities who seeks domination and control over everything",
    }

    analysis = await agent.analyze_character(character_data)
    print(f"Analysis result: {analysis}")

    # Test story validation
    story_prompt = "A powerful witch gains unlimited power and destroys the world"
    validation = await agent.validate_story_generation(story_prompt)
    print(f"Validation result: {validation}")

    print("CharacterAnalysisAgent test completed.\n")


async def test_story_generation():
    """Test story generation functionality."""
    print("Testing StoryGenerationAgent...")

    # Create mock dependencies
    message_bus = MessageBus()
    session_logger = MockSessionLogger()
    config = {"debug": True}

    # Create agent
    agent = StoryGenerationAgent(
        agent_id="test_story_generator", message_bus=message_bus, session_logger=session_logger, config=config
    )

    # Test story generation
    story = await agent.generate_story(
        theme="power", character_inspiration="raven", length="short", safety_level="balanced"
    )

    print(f"Generated story title: {story['story_title']}")
    print(f"Story length: {len(story['story_text'])} characters")
    print(f"Safety check: {story['safety_check']}")

    print("StoryGenerationAgent test completed.\n")


async def main():
    """Run all tests."""
    print("Starting agent tests...\n")

    await test_character_analysis()
    await test_story_generation()

    print("All tests completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
