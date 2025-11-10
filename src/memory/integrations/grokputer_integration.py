from ..managers.persistent_manager import PersistentMemoryManager
from ..interfaces import MemoryConfig
from typing import Dict, Any, List

class GrokputerMemoryIntegration:
    def __init__(self):
        self.config = MemoryConfig()
        self.memory = PersistentMemoryManager(self.config)

    def log_episode(self, agent_id: str, episode_data: Dict[str, Any]) -> None:
        '''Log an episode for the agent.'''
        self.memory.store_episode(agent_id, episode_data)

    def get_context(self, agent_id: str, query: str = None, top_k: int = 5) -> List[Dict[str, Any]]:
        '''Retrieve context for the agent.'''
        return self.memory.retrieve_context(agent_id, query, top_k)

    def consolidate_memory(self, agent_id: str) -> Dict[str, Any]:
        '''Consolidate memory for the agent.'''
        return self.memory.consolidate(agent_id)

    def get_memory_context(self, task: str) -> str:
        '''Get memory context for a task (used by main.py).'''
        # For now, return a simple context string
        # In future, could analyze task and retrieve relevant memories
        consolidated = self.memory.consolidate("grokputer")  # Use generic agent_id
        if consolidated.get("status") == "no_data":
            return "No previous task memory available."

        context = f"Previous tasks: {consolidated.get('total_episodes', 0)} episodes, "
        context += f"success rate: {consolidated.get('success_rate', 0):.1%}, "
        context += f"common tools: {list(consolidated.get('tool_usage', {}).keys())}"

        return context

    def update_memory_with_tool_result(self, task: str, tool_name: str, tool_args: Dict[str, Any], tool_result: Any) -> None:
        '''Update memory with tool execution result (used by main.py).'''
        episode_data = {
            "task": task,
            "tool_used": tool_name,
            "tool_args": tool_args,
            "tool_result": str(tool_result),  # Convert to string for storage
            "success": True if "error" not in str(tool_result).lower() else False,
            "timestamp": None  # Will be set by DB
        }
        self.memory.store_episode("grokputer", episode_data)