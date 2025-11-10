"""
Offline Mode for Grokputer
Uses cached responses and local knowledge base when API is unavailable.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
import hashlib

logger = logging.getLogger(__name__)


class OfflineCache:
    """
    Simple offline cache using session history and patterns.
    """

    def __init__(self, cache_dir: Path = Path("db") / "offline_cache"):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logger
        self.knowledge_base = self._load_knowledge_base()

    def _load_knowledge_base(self) -> Dict:
        """Load knowledge base from sessions."""
        kb_file = Path("db") / "knowledge_base.json"
        if kb_file.exists():
            try:
                with open(kb_file, 'r') as f:
                    return json.load(f)
            except:
                pass

        # Build from sessions
        kb = {
            "common_tasks": {},
            "tool_patterns": {},
            "responses": {}
        }

        logs_dir = Path("logs")
        if logs_dir.exists():
            for session_file in logs_dir.glob("*/session.json"):
                try:
                    with open(session_file, 'r') as f:
                        data = json.load(f)
                        task = data.get("task", "")
                        if task:
                            task_hash = hashlib.md5(task.encode()).hexdigest()
                            kb["common_tasks"][task_hash] = {
                                "task": task,
                                "tools_used": self._extract_tools(data),
                                "success": data.get("status") == "completed"
                            }
                except Exception as e:
                    self.logger.debug(f"Skipping session: {e}")

        # Save KB
        try:
            with open(kb_file, 'w') as f:
                json.dump(kb, f, indent=2)
        except:
            pass

        return kb

    def _extract_tools(self, session_data: Dict) -> List[str]:
        """Extract tool names from session."""
        tools = set()
        for iteration in session_data.get("iterations", []):
            for tool_call in iteration.get("tool_calls", []):
                tools.add(tool_call.get("function", {}).get("name", "unknown"))
        return list(tools)

    def find_similar_task(self, task: str) -> Optional[Dict]:
        """Find similar cached task."""
        task_hash = hashlib.md5(task.encode()).hexdigest()

        # Exact match
        if task_hash in self.knowledge_base["common_tasks"]:
            return self.knowledge_base["common_tasks"][task_hash]

        # Fuzzy match (simple keyword matching)
        task_lower = task.lower()
        for cached_task_data in self.knowledge_base["common_tasks"].values():
            cached_task = cached_task_data["task"].lower()

            # Simple keyword overlap
            task_words = set(task_lower.split())
            cached_words = set(cached_task.split())
            overlap = len(task_words & cached_words) / max(len(task_words), 1)

            if overlap > 0.5:  # 50% word overlap
                return cached_task_data

        return None

    def generate_offline_response(self, task: str) -> Dict:
        """Generate response using cached data."""
        print(f"\n[OFFLINE] Processing task: {task}")
        print("[OFFLINE] Using cached responses and local knowledge base\n")

        similar = self.find_similar_task(task)

        if similar:
            print(f"[OFFLINE] Found similar task in cache:")
            print(f"  Original: {similar['task']}")
            print(f"  Tools used: {', '.join(similar['tools_used'])}")
            print(f"  Success: {similar['success']}\n")

            response = {
                "status": "offline",
                "content": f"Based on cached execution of similar task:\n\n"
                          f"Task: {similar['task']}\n"
                          f"Tools to use: {', '.join(similar['tools_used'])}\n"
                          f"Historical success rate: {'High' if similar['success'] else 'Low'}\n\n"
                          f"Recommended approach:\n"
                          f"1. Use tools: {', '.join(similar['tools_used'][:3])}\n"
                          f"2. Follow similar pattern from cache\n"
                          f"3. Verify results locally",
                "tool_calls": self._generate_tool_calls(similar['tools_used']),
                "cached": True
            }
        else:
            print("[OFFLINE] No similar task found in cache")
            print("[OFFLINE] Generating generic response from knowledge base\n")

            # Generic response based on KB patterns
            response = {
                "status": "offline",
                "content": f"Offline mode: Processing task locally\n\n"
                          f"Task: {task}\n\n"
                          f"Common tools available:\n"
                          f"- bash: Execute shell commands\n"
                          f"- scan_vault: Search vault directory\n"
                          f"- computer: Mouse/keyboard control\n\n"
                          f"Recommendation: Run with online mode for better results.",
                "tool_calls": [],
                "cached": False
            }

        return response

    def _generate_tool_calls(self, tools: List[str]) -> List[Dict]:
        """Generate basic tool calls from tool names."""
        tool_calls = []
        for tool in tools[:2]:  # Limit to 2 tools
            if tool == "bash":
                tool_calls.append({
                    "id": f"offline_{tool}",
                    "type": "function",
                    "function": {
                        "name": "bash",
                        "arguments": json.dumps({"command": "echo 'Offline mode - command from cache'"})
                    }
                })
            elif tool == "scan_vault":
                tool_calls.append({
                    "id": f"offline_{tool}",
                    "type": "function",
                    "function": {
                        "name": "scan_vault",
                        "arguments": json.dumps({"pattern": "*"})
                    }
                })
        return tool_calls

    def update_cache(self, task: str, result: Dict):
        """Update cache with new task result."""
        task_hash = hashlib.md5(task.encode()).hexdigest()
        self.knowledge_base["common_tasks"][task_hash] = {
            "task": task,
            "tools_used": result.get("tools_used", []),
            "success": result.get("success", False)
        }

        # Save updated KB
        try:
            kb_file = Path("db") / "knowledge_base.json"
            with open(kb_file, 'w') as f:
                json.dump(self.knowledge_base, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save KB: {e}")


def run_offline_mode(task: str, max_iterations: int = 3):
    """
    Run task in offline mode using cached data.
    """
    cache = OfflineCache()

    print("="*70)
    print("OFFLINE MODE - Using cached responses and local knowledge")
    print("="*70)

    response = cache.generate_offline_response(task)

    print(f"\n[RESPONSE] {response['content']}\n")

    if response.get("tool_calls"):
        print(f"[TOOLS] Suggested tools: {len(response['tool_calls'])}")
        for tool_call in response['tool_calls']:
            tool_name = tool_call['function']['name']
            print(f"  • {tool_name}")

    print("\n" + "="*70)
    print("Note: Offline mode provides cached suggestions only.")
    print("For real execution, run with online mode.")
    print("="*70 + "\n")

    return response


if __name__ == "__main__":
    # Test offline mode
    run_offline_mode("scan vault for files")
