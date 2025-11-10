from src.memory.interfaces import MemoryConfig
from src.memory.managers.persistent_manager import PersistentMemoryManager
from datetime import datetime

# Load config (assuming .env loaded)
config = MemoryConfig()

# Initialize manager
manager = PersistentMemoryManager(config)

# Test store episode
data = {
    "action": "test_action",
    "outcome": "success",
    "latency": 0.5,
    "timestamp": datetime.now().isoformat()
}
manager.store_episode("test_agent", data)
print("Episode stored successfully.")

# Test retrieve context (no query, recent)
context = manager.retrieve_context("test_agent", top_k=1)
print(f"Retrieved context: {context}")

# Test semantic query (if Pinecone set up)
similar = manager.retrieve_context("test_agent", query="test_action", top_k=1)
print(f"Similar context: {similar}")

# Test consolidate
consolidated = manager.consolidate("test_agent")
print(f"Consolidated: {consolidated}")