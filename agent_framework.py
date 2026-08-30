from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, List
import logging

logger = logging.getLogger(__name__)

class BaseAgent(ABC):
    def __init__(self, name: str, config: Dict[str, Any] = None):
        self.name = name
        self.config = config or {}
        self.message_queue = asyncio.Queue()
        self.running = False

    @abstractmethod
    async def run(self):
        pass

    async def send_message(self, msg: Any):
        await self.message_queue.put(msg)

    async def receive_message(self) -> Any:
        return await self.message_queue.get()

class AgentManager:
    def __init__(self):
        self.agents: List[BaseAgent] = []
        self.message_bus = asyncio.Queue()

    def add_agent(self, agent: BaseAgent):
        self.agents.append(agent)

    async def start_all(self):
        tasks = [agent.run() for agent in self.agents]
        self.running = True
        await asyncio.gather(*tasks)

    async def stop_all(self):
        self.running = False
        for agent in self.agents:
            agent.running = False

# Example usage
async def main():
    manager = AgentManager()
    # Add agents here
    await manager.start_all()

if __name__ == "__main__":
    asyncio.run(main())