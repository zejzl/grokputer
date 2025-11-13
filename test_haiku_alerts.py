#!/usr/bin/env python3
"""
Test Haiku Alerts functionality
"""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.core.message_bus import MessageBus, Message, MessagePriority
from src.tools.alerts import get_haiku_alerts


async def test_haiku_alerts():
    """Test the haiku alerts system."""
    print("Testing Haiku Alerts...")

    # Create message bus
    bus = MessageBus()
    bus.register_agent("alerts")

    # Get alerts instance
    alerts = get_haiku_alerts(bus)

    # Start listening
    await alerts.start_listening()

    # Simulate task completion messages
    test_messages = [
        {"task_name": "Screenshot Analysis", "task_type": "observation", "task_id": "test_obs_001"},
        {"task_name": "Execute Command", "task_type": "action", "task_id": "test_act_001"},
        {"task_name": "Validate Safety", "task_type": "validation", "task_id": "test_val_001"},
        {"task_name": "Generic Task", "task_type": "default", "task_id": "test_def_001"},
    ]

    print("\nSending test task completion messages...\n")

    for msg_data in test_messages:
        message = Message(
            from_agent="test_coordinator", to_agent="alerts", message_type="task_complete", content=msg_data
        )
        await alerts._generate_haiku_alert(message)
        await asyncio.sleep(0.5)  # Brief pause between alerts

    # Test manual alert
    print("\nTesting manual alert...\n")
    await alerts.trigger_manual_alert("Custom Test Task", "action", "manual_001")

    print("\nHaiku alerts test complete!")


if __name__ == "__main__":
    asyncio.run(test_haiku_alerts())
