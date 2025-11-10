#!/usr/bin/env python3
"""
Phase 1 PoC: Minimal swarm test (Coordinator + Observer + Actor).
Task: "capture screen and click at (100,100)" - decomposed into observe + act.
Measures: Task decomposition, delegation, aggregation, <10s total.
Run: python tests/poc_swarm.py
"""
import asyncio
import time
import sys
from pathlib import Path
from typing import Dict, Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import production components
from src.core.message_bus import MessageBus, Message, MessagePriority
from src.session_logger import SessionLogger

# Config stub
CONFIG = {
    "auto_restart": True,
    "confirmation_timeout": 5.0
}

# Imports
from src.core.action_executor import ActionExecutor
from src.agents.observer import ObserverAgent
from src.agents.actor import ActorAgent
from src.agents.coordinator import Coordinator

async def run_poc_swarm():
    """Run swarm: Coordinator decomposes, delegates to Observer + Actor."""
    start_time = time.time()
    print("[SWARM POC] Starting 3-agent swarm PoC")

    # Initialize production components
    message_bus = MessageBus(default_timeout=10.0, history_size=100)
    session_logger = SessionLogger(Path("logs"), session_id="poc_swarm_test")
    action_executor = ActionExecutor()

    # Register coordinator manually (not an agent that runs a loop)
    message_bus.register_agent("coordinator")

    # Create agents
    observer = ObserverAgent(
        "observer",
        message_bus,
        session_logger,
        CONFIG,
        action_executor
    )
    actor = ActorAgent(
        "actor",
        message_bus,
        session_logger,
        CONFIG,
        action_executor
    )
    coordinator = Coordinator(
        message_bus,
        session_logger,
        CONFIG
    )

    # Start agent loops concurrently
    async def observer_loop():
        await observer.on_start()
        observer.running = True
        try:
            message = await message_bus.receive("observer", timeout=10.0)
            print(f"[OBSERVER] Received message: {message.message_type}")
            response = await observer.process_message(message)
            print(f"[OBSERVER] Process result: {response}")
            if response:
                print(f"[OBSERVER] Sending response to {response['to']}")
                # Send response back
                msg = Message(
                    from_agent="observer",
                    to_agent=response["to"],
                    message_type="response",
                    content=response["content"],
                    priority=MessagePriority.NORMAL
                )
                await message_bus.send(msg)
                print("[OBSERVER] Response sent")
            else:
                print("[OBSERVER] No response to send")
        except Exception as e:
            print(f"[OBSERVER] Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await observer.stop()

    async def actor_loop():
        await actor.on_start()
        actor.running = True
        try:
            message = await message_bus.receive("actor", timeout=10.0)
            print(f"[ACTOR] Received message: {message.message_type}")
            response = await actor.process_message(message)
            print(f"[ACTOR] Process result: {response}")
            if response:
                print(f"[ACTOR] Sending response to {response['to']}")
                # Send response back
                msg = Message(
                    from_agent="actor",
                    to_agent=response["to"],
                    message_type="response",
                    content=response["content"],
                    priority=MessagePriority.NORMAL
                )
                await message_bus.send(msg)
                print("[ACTOR] Response sent")
            else:
                print("[ACTOR] No response to send")
        except Exception as e:
            print(f"[ACTOR] Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await actor.stop()

    async def coordinator_loop():
        """Coordinator processes messages in a loop."""
        await coordinator.on_start()
        coordinator.running = True
        try:
            # First, send the initial task
            task_msg = Message(
                from_agent="user",
                to_agent="coordinator",
                message_type="new_task",
                content={
                    "description": "capture screen and click at (100,100)",
                    "task_id": "swarm_poc_task"
                },
                priority=MessagePriority.NORMAL
            )
            await message_bus.send(task_msg)

            # Process initial task
            response = await coordinator.process_message(task_msg)
            if response:
                print(f"[COORDINATOR] Initial response: {response}")

            # Now listen for responses
            while coordinator.running:
                try:
                    message = await message_bus.receive("coordinator", timeout=8.0)
                    print(f"[COORDINATOR] Received: {message.message_type}")
                    response = await coordinator.process_message(message)
                    if response:
                        print(f"[COORDINATOR] Processed and responded")
                        # For task_complete, we can stop
                        if message.message_type == "response" and response.get("type") == "task_complete":
                            print("[COORDINATOR] Task completed!")
                            break
                except asyncio.TimeoutError:
                    print("[COORDINATOR] Timeout waiting for messages")
                    break
        finally:
            await coordinator.stop()

    # Run all concurrently
    try:
        await asyncio.gather(
            observer_loop(),
            actor_loop(),
            coordinator_loop(),
            return_exceptions=True
        )
    except Exception as e:
        print(f"[SWARM POC] Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        action_executor.shutdown()
        await message_bus.shutdown()
        await coordinator.stop()

    duration = time.time() - start_time
    print(f"\n[SWARM POC] Completed in {duration:.2f}s")

    # Show MessageBus stats
    stats = message_bus.get_stats()
    print(f"[SWARM POC] Messages sent: {stats['total_messages']}")
    print(f"[SWARM POC] Message history: {len(message_bus.get_message_history())} messages")

    # Success check
    success = duration < 10.0  # Target: <10s
    print(f"[SWARM POC] Success: {success} (target: <10s)")

    return {"duration": duration, "success": success}

if __name__ == "__main__":
    asyncio.run(run_poc_swarm())