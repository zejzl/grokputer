#!/usr/bin/env python3
"""
Taskmaster Agent for Grokputer
AI-powered planner using analytics data to prioritize tasks/roadmaps.
Scores suggestions by impact (success rate, duration, API usage) and effort.
Integrates with Pantheon Coordinator for dynamic next steps.
"""
from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

from analytics import generate_report  # For metrics
from src.core.base_agent import BaseAgent
from src.core.message_bus import Message
from src.grok_client import FallbackGrokClient  # For reasoning

logger = logging.getLogger(__name__)


@dataclass
class TaskSuggestion:
    description: str
    priority: str  # high/medium/low
    impact_score: float  # 0-10 based on metrics
    effort_estimate: str  # low/medium/high
    category: str  # integration/feature/opt


class Taskmaster(BaseAgent):
    """
    Taskmaster: Analyzes analytics, suggests prioritized tasks.

    Not the task board: that is TaskMaster in src/agents/task_master.py (bus id "taskmaster").

    Message types handled:
    - 'suggest': content {"state": str} -> reply type 'suggestions' with a list of task dicts
    - 'next_step': content {"task": str} -> reply type 'next_step' with an implementation plan
    """

    def __init__(self, agent_id="task_planner", message_bus=None, session_logger=None, config=None, client=None):
        super().__init__(agent_id, message_bus, session_logger, config or {})
        self.client = client or FallbackGrokClient()

    async def process_message(self, message: Message) -> Optional[Dict[str, Any]]:
        """Handle suggestion requests arriving over the MessageBus."""
        content = message.content if isinstance(message.content, dict) else {}

        if message.message_type == "suggest":
            suggestions = await self.suggest_tasks(content.get("state", ""))
            logger.info(f"[{self.agent_id}] Suggested {len(suggestions)} tasks")
            return {
                "to": message.from_agent,
                "type": "suggestions",
                "content": {"suggestions": [asdict(t) for t in suggestions]},
            }

        if message.message_type == "next_step":
            task = content.get("task", "")
            if not task:
                return {"to": message.from_agent, "type": "error", "content": {"reason": "Missing task"}}
            plan = await self.get_next_step(task)
            return {"to": message.from_agent, "type": "next_step", "content": {"task": task, "plan": plan}}

        logger.warning(f"[{self.agent_id}] Unknown message type: {message.message_type}")
        return {
            "to": message.from_agent,
            "type": "error",
            "content": {"reason": f"Unknown message type: {message.message_type}"},
        }

    async def analyze_metrics(self) -> Dict[str, Any]:
        """Analyze analytics for bottlenecks/insights."""
        try:
            report = generate_report(30)  # Last 30 days
        except sqlite3.Error as e:
            logger.warning(f"[{self.agent_id}] Analytics unavailable: {e}")
            report = {"success_rate_percent": 100, "avg_duration_seconds": 0, "total_api_calls": 0, "providers": {}}
        insights = {
            "success_rate": report["success_rate_percent"],
            "avg_duration": report["avg_duration_seconds"],
            "total_api_calls": report["total_api_calls"],
            "providers": report["providers"],
            "bottlenecks": [],
        }

        if report["success_rate_percent"] < 90:
            insights["bottlenecks"].append("Low success: Improve validation/actors")
        if report["avg_duration_seconds"] > 60:
            insights["bottlenecks"].append("High latency: Optimize API/async")
        if report["total_api_calls"] > 1000:
            insights["bottlenecks"].append("High usage: Add caching/fallbacks")

        return insights

    async def suggest_tasks(self, current_state: str = "") -> List[TaskSuggestion]:
        """Suggest tasks based on metrics and state."""
        insights = await self.analyze_metrics()

        # Prompt Grok for suggestions
        messages = [
            {"role": "system", "content": "You are Taskmaster, prioritize Grokputer advancements based on metrics."},
            {
                "role": "user",
                "content": f"Metrics: {insights}. Current state: {current_state}. Suggest 3-5 tasks with priority, impact (0-10), effort (low/medium/high), category (integration/feature/opt). Format as JSON list.",
            },
        ]

        response = await self.client.chat(messages)
        try:
            suggestions = json.loads(response)
            tasks = []
            for s in suggestions:
                tasks.append(
                    TaskSuggestion(
                        description=s["description"],
                        priority=s["priority"],
                        impact_score=s["impact"],
                        effort_estimate=s["effort"],
                        category=s["category"],
                    )
                )
            return sorted(tasks, key=lambda t: t.impact_score, reverse=True)
        except (ValueError, TypeError, KeyError):
            # Fallback suggestions
            fallback = [
                TaskSuggestion("Implement provider fallbacks", "high", 9.5, "medium", "integration"),
                TaskSuggestion("Add Taskmaster integration to Pantheon", "medium", 8.0, "low", "feature"),
                TaskSuggestion("Optimize memory leaks", "low", 7.0, "high", "opt"),
            ]
            return fallback

    async def get_next_step(self, task: str) -> str:
        """Get detailed next step for a task."""
        messages = [{"role": "user", "content": f"For task '{task}', provide step-by-step implementation plan."}]
        return await self.client.chat(messages)


# Integration with Pantheon
async def integrate_with_pantheon(bus, session_logger):
    """Example: Add Taskmaster to message bus."""
    taskmaster = Taskmaster("taskmaster", bus, session_logger, {})
    # Start in coordinator: send a Message(message_type="suggest") to "taskmaster"
    asyncio.create_task(taskmaster.run())
    logger.info("Taskmaster integrated with Pantheon")


if __name__ == "__main__":
    async def demo():
        from unittest.mock import MagicMock

        from src.core.message_bus import MessageBus

        tm = Taskmaster("taskmaster", MessageBus(), MagicMock(), {})
        suggestions = await tm.suggest_tasks("Post-opt wave; Redis restored.")
        print(json.dumps([s.__dict__ for s in suggestions], indent=2))

    asyncio.run(demo())
