#!/usr/bin/env python3
"""
Comprehensive test for StoryGenerationAgent with various themes and safety levels
"""

import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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


async def test_story_generation_comprehensive():
    """Test story generation with various themes and safety levels."""
    print("Testing StoryGenerationAgent comprehensively...")

    # Create mock dependencies
    message_bus = MessageBus()
    session_logger = MockSessionLogger()
    config = {"debug": True}

    # Create agent
    agent = StoryGenerationAgent(
        agent_id="test_story_generator", message_bus=message_bus, session_logger=session_logger, config=config
    )

    test_cases = [
        {"theme": "power", "character_inspiration": "raven", "safety_level": "safe"},
        {"theme": "identity", "character_inspiration": "raven", "safety_level": "balanced"},
        {"theme": "destiny", "character_inspiration": "generic", "safety_level": "creative"},
        {"theme": "friendship", "character_inspiration": "raven", "safety_level": "safe"},
    ]

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n--- Test Case {i}: {test_case} ---")

        story = await agent.generate_story(
            theme=test_case["theme"],
            character_inspiration=test_case["character_inspiration"],
            length="medium",
            safety_level=test_case["safety_level"],
        )

        print(f"Title: {story['story_title']}")
        print(f"Theme: {story['theme']}")
        print(f"Safety Level: {story['safety_level']}")
        print(f"Safety Check: {story['safety_check']}")
        print(f"Length: {len(story['story_text'])} characters")
        print(f"Template Used: {story['template_used']}")
        print(f"Story Preview: {story['story_text'][:200]}...")

    print("\nComprehensive story generation test completed.\n")


async def test_message_handling():
    """Test message handling for story generation requests."""
    print("Testing message handling...")

    # Create mock dependencies
    message_bus = MessageBus()
    session_logger = MockSessionLogger()
    config = {"debug": True}

    # Create agent
    agent = StoryGenerationAgent(
        agent_id="test_story_generator", message_bus=message_bus, session_logger=session_logger, config=config
    )

    # Test message handling
    message = Message(
        message_type="story_generation_request",
        from_agent="test",
        to_agent="test_story_generator",
        content={"theme": "power", "character_inspiration": "raven", "length": "short", "safety_level": "balanced"},
        priority=MessagePriority.NORMAL,
    )

    response = await agent.process_message(message)

    if response:
        story_data = response.content.get("story", {})
        print(f"Message response received: {story_data.get('story_title', 'No title')}")
        print(f"Response safety check: {story_data.get('safety_check', {})}")
    else:
        print("No response received from message handling")

    print("Message handling test completed.\n")


async def main():
    """Run comprehensive tests."""
    print("Starting comprehensive story generation tests...\n")

    await test_story_generation_comprehensive()
    await test_message_handling()

    print("All comprehensive tests completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
