#!/usr/bin/env python3
"""
Quick test of Pantheon literary agents
"""

import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agents.character_analysis_agent import CharacterAnalysisAgent
from src.agents.story_generation_agent import StoryGenerationAgent
from src.core.message_bus import MessageBus
from src.observability.session_logger import SessionLogger


class MockSessionLogger:
    def log_agent_start(self, agent_id):
        pass

    def log_agent_activity(self, agent_id, activity):
        pass

    def log_session_end(self):
        pass


async def quick_test():
    """Quick test of literary agents."""
    print("Testing Literary Agents...")

    # Setup
    message_bus = MessageBus()
    session_logger = MockSessionLogger()
    config = {"debug": True}

    # Test Character Analysis
    print("\nTesting CharacterAnalysisAgent...")
    char_agent = CharacterAnalysisAgent("char_test", message_bus, session_logger, config)

    character = {
        "name": "Test Witch",
        "description": "A young witch who discovers her powers and learns to control them responsibly",
    }
    analysis = await char_agent.analyze_character(character)

    print(f"Character analysis complete: {analysis['overall_safety_score']}/100 safety score")

    # Test Story Generation
    print("\nTesting StoryGenerationAgent...")
    story_agent = StoryGenerationAgent("story_test", message_bus, session_logger, config)

    story = await story_agent.generate_story("power", "raven", "short", "safe")
    print(f"Story generated: '{story['story_title']}' ({len(story['story_text'])} chars)")

    print("\nAll literary agents working perfectly!")


if __name__ == "__main__":
    asyncio.run(quick_test())
