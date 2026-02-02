"""
Haiku Alerts for Task Completions

Provides poetic notifications when tasks complete in the swarm.
Integrates with MessageBus to listen for task completion events.
"""
from __future__ import annotations

import asyncio
import logging
import random
from typing import Any, Dict, Optional

from src.core.message_bus import Message, MessageBus

logger = logging.getLogger(__name__)

# Haiku templates for different task types
HAIKU_TEMPLATES = {
    "default": [
        "Task done, screen gleams bright,\nGrok's hand moves swift in the night,\nCode flows, errors flee.",
        "Pixels parsed, command sent,\nAgents hum in silent accord,\nProgress, unchecked, climbs.",
        "Action complete, goals met,\nSwarm intelligence prevails,\nVictory is sweet.",
        "Task accomplished well,\nAgents dance in harmony,\nSuccess resonates.",
        "Mission fulfilled now,\nDigital winds carry the win,\nTriumph in the code.",
    ],
    "observation": [
        "Screen captured, vision clear,\nGrok's eyes see all that's near,\nTruth revealed in light.",
        "Pixels dance in capture,\nObserver's gaze penetrates,\nKnowledge flows freely.",
        "Visual data streams,\nObserver agent succeeds,\nSight becomes insight.",
    ],
    "action": [
        "Commands executed swift,\nActor's hands move with purpose,\nChange ripples outward.",
        "Actions taken boldly,\nActor fulfills the command,\nWorld transforms gently.",
        "Execution complete,\nActor's will becomes reality,\nPower in motion.",
    ],
    "validation": [
        "Safety verified true,\nValidator's wisdom prevails,\nTrust in every step.",
        "Checks pass, confidence grows,\nValidator ensures safety,\nPeace in certainty.",
        "Validation complete,\nGuardian angels approve,\nPath is clear ahead.",
    ],
}


class HaikuAlerts:
    """
    Manages haiku alerts for task completions.

    Listens to MessageBus for task completion events and generates
    poetic notifications based on task type.
    """

    def __init__(self, message_bus: MessageBus):
        self.bus = message_bus
        self.active_alerts: Dict[str, asyncio.Task] = {}
        self.logger = logging.getLogger(__name__)

    async def start_listening(self):
        """Start listening for task completion events."""
        self.logger.info("Starting haiku alerts listener...")
        asyncio.create_task(self._alert_listener())

    async def _alert_listener(self):
        """Background task that listens for completion messages."""
        try:
            while True:
                # Listen for task completion messages
                message = await self.bus.receive("alerts", timeout=30.0)

                if message.message_type == "task_complete":
                    await self._generate_haiku_alert(message)

                elif message.message_type == "swarm_complete":
                    await self._generate_swarm_haiku(message)

        except asyncio.TimeoutError:
            # Timeout is expected, continue listening
            pass
        except Exception as e:
            self.logger.error(f"Error in alert listener: {e}")

    async def _generate_haiku_alert(self, message: Message):
        """Generate haiku for individual task completion."""
        content = message.content
        task_name = content.get("task_name", "Task")
        task_type = content.get("task_type", "default")
        task_id = content.get("task_id", "unknown")

        # Get appropriate templates
        templates = HAIKU_TEMPLATES.get(task_type, HAIKU_TEMPLATES["default"])
        template = random.choice(templates)

        # Customize the haiku
        haiku = template.replace("Task", task_name[:20])  # Limit length

        # Print the haiku
        print(f"\n[OK] Task Complete: {task_name}")
        print(f"📝 {haiku}")
        print(f"🔖 ID: {task_id}\n")

        # Publish haiku to bus for other agents to consume
        alert_msg = Message(
            from_agent="haiku_alerts",
            to_agent="broadcast",
            message_type="haiku_alert",
            content={
                "task_id": task_id,
                "task_name": task_name,
                "task_type": task_type,
                "poem": haiku,
                "timestamp": message.timestamp,
            },
        )
        await self.bus.broadcast(alert_msg)

    async def _generate_swarm_haiku(self, message: Message):
        """Generate haiku for entire swarm completion."""
        content = message.content
        swarm_name = content.get("swarm_name", "Swarm")
        total_tasks = content.get("total_tasks", 0)
        success_rate = content.get("success_rate", 1.0)

        # Special swarm completion haiku
        swarm_templates = [
            f"{swarm_name} complete, agents unite,\n{total_tasks} tasks in harmony,\nVictory achieved.",
            f"Swarm intelligence prevails,\n{swarm_name} conquers all challenges,\nSuccess rate: {success_rate:.1%}",
            f"Multi-agent triumph,\n{swarm_name} completes the mission,\nAgents stand as one.",
        ]

        haiku = random.choice(swarm_templates)

        print(f"\n🏆 Swarm Complete: {swarm_name}")
        print(f"[STATS] Tasks: {total_tasks} | Success: {success_rate:.1%}")
        print(f"📝 {haiku}\n")

        # Publish swarm haiku
        alert_msg = Message(
            from_agent="haiku_alerts",
            to_agent="broadcast",
            message_type="swarm_haiku",
            content={
                "swarm_name": swarm_name,
                "total_tasks": total_tasks,
                "success_rate": success_rate,
                "poem": haiku,
                "timestamp": message.timestamp,
            },
        )
        await self.bus.broadcast(alert_msg)

    async def trigger_manual_alert(self, task_name: str, task_type: str = "default", task_id: str = None):
        """Manually trigger a haiku alert (for testing or special cases)."""
        if task_id is None:
            task_id = f"manual_{random.randint(1000, 9999)}"

        message = Message(
            from_agent="manual",
            to_agent="alerts",
            message_type="task_complete",
            content={"task_name": task_name, "task_type": task_type, "task_id": task_id},
        )

        await self._generate_haiku_alert(message)

    def get_available_types(self) -> list:
        """Get list of available haiku template types."""
        return list(HAIKU_TEMPLATES.keys())


# Global instance for easy access
_alerts_instance: Optional[HaikuAlerts] = None


def get_haiku_alerts(message_bus: MessageBus) -> HaikuAlerts:
    """Get or create the global haiku alerts instance."""
    global _alerts_instance
    if _alerts_instance is None:
        _alerts_instance = HaikuAlerts(message_bus)
    return _alerts_instance


async def haiku_alert(bus: MessageBus, task_id: str):
    """
    Convenience function to wait for and alert on a specific task completion.

    Usage:
        asyncio.create_task(haiku_alert(message_bus, current_task_id))
    """
    alerts = get_haiku_alerts(bus)
    await alerts.start_listening()

    # This would be enhanced to specifically wait for the task_id
    # For now, it just starts the general listener
    pass
