#!/usr/bin/env python3
"""
Taskmaster Agent for Grokputer
AI-powered planner using analytics data to prioritize tasks/roadmaps.
Scores suggestions by impact (success rate, duration, API usage) and effort.
Integrates with Pantheon Coordinator for dynamic next steps.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Dict, List

from analytics import generate_report  # For metrics
from src.core.base_agent import BaseAgent
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
    """Taskmaster: Analyzes analytics, suggests prioritized tasks."""

    def __init__(self, name="taskmaster", client=None):
        super().__init__(name=name)
        self.client = client or FallbackGrokClient()
        self.analytics = generate_report(30)  # Last 30 days; refresh as needed

    async def analyze_metrics(self) -> Dict[str, Any]:
        """Analyze analytics for bottlenecks/insights."""
        report = generate_report(30)
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
        except:
            # Fallback suggestions
            fallback = [
                TaskSuggestion("Implement provider fallbacks", "high", 9.5, "medium", "integration"),
                Taskmaster("Add Taskmaster integration to Pantheon", "medium", 8.0, "low", "feature"),
                TaskSuggestion("Optimize memory leaks", "low", 7.0, "high", "opt"),
            ]
            return fallback

    async def get_next_step(self, task: str) -> str:
        """Get detailed next step for a task."""
        messages = [{"role": "user", "content": f"For task '{task}', provide step-by-step implementation plan."}]
        return await self.client.chat(messages)

    async def run(self):
        """Taskmaster run loop: Suggest based on queue."""
        while True:
            if self.inbox.qsize() > 0:
                msg = await self.inbox.get()
                if msg["type"] == "suggest":
                    suggestions = await self.suggest_tasks(msg.get("state", ""))
                    await self.outbox.put({"type": "suggestions", "data": suggestions})
                    logger.info(f"Taskmaster suggested {len(suggestions)} tasks")
                await asyncio.sleep(0.1)
            else:
                await asyncio.sleep(1)


# Integration with Pantheon
async def integrate_with_pantheon():
    """Example: Add Taskmaster to message bus."""
    from src.core.message_bus import MessageBus

    bus = MessageBus()
    taskmaster = Taskmaster()
    bus.register_agent(taskmaster)
    # Start in coordinator: Send {'type': 'suggest'} to taskmaster inbox
    asyncio.create_task(taskmaster.run())
    logger.info("Taskmaster integrated with Pantheon")


if __name__ == "__main__":
    import json

    async def demo():
        tm = Taskmaster()
        suggestions = await tm.suggest_tasks("Post-opt wave; Redis restored.")
        print(json.dumps([s.__dict__ for s in suggestions], indent=2))

    asyncio.run(demo())
