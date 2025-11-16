#!/usr/bin/env python3
"""
Limbo Autobet Daemon

Runs the LimboAutobetAgent in background for autonomous betting.

Usage:
    python limbo_daemon.py --start
    python limbo_daemon.py --stop
    python limbo_daemon.py --status
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.core.message_bus import MessageBus, Message, MessagePriority
from src.observability.session_logger import SessionLogger
from src.agents.limbo_autobet_agent import LimboAutobetAgent
from src.agents.observer import Observer
from src.agents.actor_agent import ActorAgent
from src.core.action_executor import ActionExecutor
from src.observability.deadlock_detector import DeadlockDetector

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LimboDaemon:
    """Daemon to run Limbo autobet agent with required dependencies."""

    def __init__(self):
        self.message_bus = None
        self.session_logger = None
        self.limbo_agent = None
        self.observer = None
        self.actor = None
        self.running = False

    async def initialize(self):
        """Initialize all components."""
        logger.info("[LimboDaemon] Initializing components...")

        # Initialize message bus
        self.message_bus = MessageBus()
        await self.message_bus.initialize()

        # Initialize session logger
        self.session_logger = SessionLogger(
            session_id="limbo_autobet",
            task="autonomous_betting",
            log_dir=Path("./logs"),
            swarm_mode=False
        )

        # Initialize deadlock detector
        deadlock_detector = DeadlockDetector()

        # Initialize action executor
        action_executor = ActionExecutor()

        # Initialize Observer agent
        observer_config = {
            "screenshot_quality": 85,
            "max_screenshot_width": 1920,
            "max_screenshot_height": 1080,
            "screenshot_cache_size": 10,
        }
        self.observer = Observer(
            message_bus=self.message_bus,
            session_logger=self.session_logger,
            config=observer_config,
        )

        # Initialize Actor agent
        self.actor = ActorAgent(
            message_bus=self.message_bus,
            action_executor=action_executor,
            session_logger=self.session_logger,
            deadlock_detector=deadlock_detector,
            config={"debug": False, "max_retries": 3, "safety_threshold": 0.8},
        )

        # Initialize Limbo agent
        limbo_config = {
            "base_bet": 0.01,
            "profit_target": 1.38,
            "loss_increase": 0.25,
            "max_bet": 1.0,
            "min_balance": 0.1,
            "stop_loss": 0.5,
            "target_multiplier": 1.38,
            "bet_input_pos": (400, 300),
            "multiplier_input_pos": (500, 300),
            "bet_button_pos": (600, 300),
        }
        self.limbo_agent = LimboAutobetAgent(
            message_bus=self.message_bus,
            session_logger=self.session_logger,
            config=limbo_config,
        )

        logger.info("[LimboDaemon] All components initialized")

    async def start(self):
        """Start the daemon."""
        await self.initialize()

        self.running = True
        logger.info("[LimboDaemon] Starting daemon...")

        # Start all agents
        tasks = [
            asyncio.create_task(self.observer.run()),
            asyncio.create_task(self.actor.run()),
            asyncio.create_task(self.limbo_agent.run()),
        ]

        # Start betting
        await asyncio.sleep(2)  # Wait for agents to start
        start_msg = Message(
            from_agent="daemon",
            to_agent="limbo_autobet",
            message_type="start_betting",
            content={"starting_balance": 1.0},  # Assume starting balance
            priority=MessagePriority.NORMAL,
        )
        await self.message_bus.send(start_msg)

        # Wait for tasks
        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            logger.info("[LimboDaemon] Received interrupt, shutting down...")
        finally:
            await self.stop()

    async def stop(self):
        """Stop the daemon."""
        logger.info("[LimboDaemon] Stopping daemon...")
        self.running = False

        if self.limbo_agent:
            await self.limbo_agent.stop()
        if self.observer:
            await self.observer.stop()
        if self.actor:
            await self.actor.stop()
        if self.message_bus:
            await self.message_bus.close()

        logger.info("[LimboDaemon] Daemon stopped")

    async def get_status(self):
        """Get status of the betting."""
        if not self.limbo_agent:
            return {"status": "not_initialized"}

        # Send status message
        status_msg = Message(
            from_agent="daemon",
            to_agent="limbo_autobet",
            message_type="status",
            content={},
            priority=MessagePriority.NORMAL,
        )
        await self.message_bus.send(status_msg)
        # In real implementation, wait for response
        return {"status": "running"}


async def main():
    daemon = LimboDaemon()

    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "--start":
            await daemon.start()
        elif command == "--stop":
            await daemon.stop()
        elif command == "--status":
            status = await daemon.get_status()
            print(status)
        else:
            print("Usage: python limbo_daemon.py --start|--stop|--status")
    else:
        print("Usage: python limbo_daemon.py --start|--stop|--status")


if __name__ == "__main__":
    asyncio.run(main())