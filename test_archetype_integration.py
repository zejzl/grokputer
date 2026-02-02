from __future__ import annotations

import asyncio
from typing import Dict, Any, Optional

# Stub classes to avoid import errors
class BaseAgent:
    def __init__(self, *args, **kwargs):
        pass

class Message:
    def __init__(self, content: Dict):
        self.content = content

class StubMessageBus:
    def register_agent(self, agent_id):
        pass

class StubSessionLogger:
    pass

# Import the agent (assuming path is correct)
from src.agents.visionary_agent import VisionaryAgent

async def test_visionary(mode: str, seed: str):
    agent = VisionaryAgent(
        agent_id="test_visionary",
        message_bus=StubMessageBus(),
        session_logger=StubSessionLogger(),
        config={'debug': False},
        archetype_mode=mode
    )
    message = Message({"seed": seed})
    result = await agent.process_message(message)
    print(f"\n{ mode.upper() } MODE TEST:")
    print(f"Input seed: {seed}")
    print(f"Output: {result['content'] if result else 'No result'}")

async def main():
    seed = "build eternal AI"
    await test_visionary('nobody', seed)
    await test_visionary('thoth', seed)

if __name__ == "__main__":
    asyncio.run(main())