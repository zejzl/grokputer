import asyncio
import hashlib  # For perceptual hashing (doc integrity)
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

# Grokputer imports (adapt to your src structure)
try:
    from src.core.base_agent import (
        BaseAgent,  # Pantheon base (fallback to dict if not available)
    )
    from src.core.config import Config  # For API keys, etc.
    from src.grok_client import GrokClient  # Async Grok API wrapper

    # from src.core.message_bus import MessageBus  # For future inter-agent comms
except ImportError:
    # Fallback stubs for early dev
    class GrokClient:
        async def chat(self, system_prompt, user_prompt, temperature=0.2, max_tokens=1024):
            role = system_prompt.split("You are ")[1].split(" in")[0] if "You are " in system_prompt else "reasoner"
            return f"Mock Grok response for {role}: {user_prompt[:50]}... (Detailed Markdown specs/stories would go here. Embed context, code, tests.)"

    class BaseAgent:
        def __init__(self, role):
            self.role = role

    class Config:
        def __init__(self):
            self.xai_api_key = os.getenv("XAI_API_KEY", "mock_key")


# Redis setup (eternal vault)
import redis

r = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)

# Config
config = Config()
grok_client = GrokClient(api_key=config.xai_api_key)


class AnalystAgent(BaseAgent):
    """Phase 1: Analyst - Requirements breakdown."""

    def __init__(self):
        super().__init__("analyst")


class PMAgent(BaseAgent):
    """Phase 1: PM - Prioritization and PRD."""

    def __init__(self):
        super().__init__("pm")


class ArchitectAgent(BaseAgent):
    """Phase 1: Architect - Scalable designs."""

    def __init__(self):
        super().__init__("architect")


class ScrumMasterAgent(BaseAgent):
    """Phase 2: Scrum Master - Story generation."""

    def __init__(self):
        super().__init__("scrum_master")


async def query_grok(prompt: str, role: str = "reasoner") -> str:
    """Async Grok query (low temp for consistency)."""
    system_prompt = (
        f"You are {role} in Grokputer's AI Dev Workflow. Be detailed, consistent, structured. Output in Markdown."
    )
    try:
        response = await grok_client.chat(
            system_prompt=system_prompt, user_prompt=prompt, temperature=0.2, max_tokens=1024
        )
        return response.strip()
    except Exception as e:
        print(f"API Error: {e}. Falling back to offline mode.")
        return f"Offline fallback for {role}: Use cached template - detailed specs/stories pending API availability."


class AIDevWorkflow:
    def __init__(self, user_input: str):
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.project_dir = Path("outputs/ai_dev_sessions") / self.session_id
        self.project_dir.mkdir(parents=True, exist_ok=True)
        self.memory_key = f"ai_dev:{self.session_id}"
        self.user_input = user_input
        self.refinements = 0  # Track human interventions
        # Init Redis session
        r.set(self.memory_key, json.dumps({"input": user_input, "session_id": self.session_id}))

    def _save_doc(self, name: str, content: str):
        """Save Markdown to project dir + Redis with hash for integrity."""
        file_path = self.project_dir / name
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        # Perceptual hash (simple MD5 for now; integrate imagehash for Validator)
        content_hash = hashlib.md5(content.encode()).hexdigest()
        r.hset(self.memory_key, name, json.dumps({"content": content, "hash": content_hash}))

    async def phase_1_agentic_planning(self) -> Dict[str, str]:
        """Phase 1: Spawn Analyst/PM/Architect in parallel for PRD/Arch docs."""
        agents = {
            AnalystAgent(): "Analyze requirements: Break down user input into detailed specs.",
            PMAgent(): "Prioritize features: Create PRD with timelines, risks, and human-in-loop notes.",
            ArchitectAgent(): "Design architecture: Embed guidance for scalability (e.g., Redis MCP integration).",
        }

        docs = {}

        async def run_agent(agent, prompt_base):
            prompt = f"{prompt_base}\nUser Input: {self.user_input}\nOutput as Markdown."
            response = await query_grok(prompt, agent.role)

            # Human-in-loop: Refine?
            print(f"\n--- {agent.role.upper()} OUTPUT ---\n{response}\nRefine this output? (y/n): ")
            refine_choice = input().strip().lower()
            if refine_choice == "y":
                self.refinements += 1
                refine_notes = input("Enter refinement notes: ").strip()
                refine_prompt = f"Previous: {response}\nRefine based on: {refine_notes}\nOutput updated Markdown."
                response = await query_grok(refine_prompt, agent.role)

            doc_name = (
                "prd.md"
                if agent.role == "pm"
                else "arch.md" if agent.role == "architect" else f"{agent.role}_analysis.md"
            )
            docs[doc_name] = response
            self._save_doc(doc_name, response)
            return doc_name, response

        # Parallel execution (future: via MessageBus)
        tasks = [run_agent(agent, base) for agent, base in agents.items()]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle exceptions in results
        for result in results:
            if isinstance(result, Exception):
                print(f"Agent task failed: {result}")

        # Archive to Redis
        phase1_data = {**json.loads(r.get(self.memory_key) or "{}"), "phase1_docs": docs}
        r.set(self.memory_key, json.dumps(phase1_data))
        print("\nPhase 1 Complete: Docs generated and archived.")
        return docs

    async def phase_2_context_engineered_dev(self, phase1_docs: Dict[str, str]) -> List[str]:
        """Phase 2: Scrum Master transforms plans into hyper-detailed stories."""
        scrum_agent = ScrumMasterAgent()
        scrum_prompt = f"""
Transform these docs into 3-5 development stories with full context, impl details, arch guidance.
User Input: {self.user_input}
PRD: {phase1_docs.get('prd.md', '')}
Arch: {phase1_docs.get('arch.md', '')}
Analysis: {phase1_docs.get('analyst_analysis.md', '')}

Output as Markdown with H3 headers like '### Story 1: [Title]'.
Each story: 
- User story format ("As a [user], I want [feature] so that [benefit]").
- Acceptance criteria (bulleted list).
- Implementation steps (numbered, with code snippets in ```python blocks).
- Test outlines (e.g., unit/integration tests).
- Architectural ties (reference PRD/Arch).

Aim for 3-5 stories covering the full scope. Be hyper-detailed to eliminate context loss.
"""
        stories_raw = await query_grok(scrum_prompt, scrum_agent.role)

        # Parse stories: Split on '### Story \d+:'
        story_pattern = r"###\s*Story\s*\d+[:\s]*(.*?(?=###\s*Story\s*\d+|$(?<!\w)))"
        stories = re.findall(story_pattern, stories_raw, re.DOTALL | re.IGNORECASE)

        # Fallback if regex fails: Simple split
        if not stories:
            stories = [s.strip() for s in re.split(r"###\s*Story\s*\d+[:\s]*", stories_raw)[1:] if s.strip()]

        story_files = []
        for i, story in enumerate(stories[:5], 1):  # Limit to 5
            story_md = f"### Story {i}: {self.user_input.split()[0]} Feature\n{story.strip()}\n\n---\nGenerated in Session: {self.session_id}"
            file_name = f"dev_story_{i}.md"
            self._save_doc(file_name, story_md)
            story_files.append(str(self.project_dir / file_name))

        # Export metrics to Redis (for Analyzer/Streamlit)
        metrics = {
            "stories_generated": len(story_files),
            "refinements": self.refinements,
            "timestamp": self.session_id,
            "user_input": self.user_input,
        }
        r.hset("ai_dev_metrics", self.session_id, json.dumps(metrics))

        # Archive Phase 2 to Redis
        phase2_data = {**json.loads(r.get(self.memory_key) or "{}"), "phase2_stories": story_files, "metrics": metrics}
        r.set(self.memory_key, json.dumps(phase2_data))

        print(f"Phase 2 Complete: {len(story_files)} stories generated.")
        return story_files


async def run_ai_dev_workflow(user_input: str):
    """Top-level async runner for the workflow."""
    print(f"Starting AI Dev Workflow for: {user_input}")
    workflow = AIDevWorkflow(user_input)
    phase1 = await workflow.phase_1_agentic_planning()
    stories = await workflow.phase_2_context_engineered_dev(phase1)
    print(f"Workflow complete! Outputs in {workflow.project_dir}")
    print(f"Stories: {stories}")
    print(f"View metrics in Redis key: ai_dev_metrics:{workflow.session_id}")
    return stories


# Example usage (for testing)
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        asyncio.run(run_ai_dev_workflow(" ".join(sys.argv[1:])))
    else:
        print("Usage: python ai_dev_workflow.py 'Your task description'")
