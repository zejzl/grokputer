"""
Deadlock detection and recovery for agent swarm.

Monitors agent activity to detect and handle deadlock situations where
agents are waiting on each other indefinitely.
"""

import asyncio
import logging
import time
from typing import Dict, Optional, Callable
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class DeadlockError(Exception):
    """Raised when a deadlock is detected."""
    pass


@dataclass
class AgentActivity:
    """Track agent activity for deadlock detection."""
    agent_id: str
    last_activity: float = field(default_factory=time.time)
    message_count: int = 0
    state: str = "idle"


class DeadlockDetector:
    """
    Watchdog for detecting deadlocks in agent swarm.

    Monitors agent activity and detects when agents are stuck waiting
    on each other. Provides recovery strategies.

    Usage:
        detector = DeadlockDetector(timeout_seconds=30.0)

        # In agent code
        detector.update_activity("observer")

        # Start monitoring
        await detector.monitor()
    """

    def __init__(
        self,
        timeout_seconds: float = 30.0,
        check_interval: float = 5.0,
        on_deadlock: Optional[Callable] = None
    ):
        """
        Initialize deadlock detector.

        Args:
            timeout_seconds: Max idle time before deadlock suspected
            check_interval: How often to check for deadlocks (seconds)
            on_deadlock: Optional callback when deadlock detected
        """
        self.timeout = timeout_seconds
        self.check_interval = check_interval
        self.on_deadlock = on_deadlock

        self.agent_states: Dict[str, AgentActivity] = {}
        self.running = False
        self.monitor_task: Optional[asyncio.Task] = None

        # Stats
        self.deadlocks_detected = 0
        self.deadlocks_recovered = 0

    def register_agent(self, agent_id: str):
        """Register an agent for monitoring."""
        self.agent_states[agent_id] = AgentActivity(agent_id=agent_id)
        logger.debug(f"[DeadlockDetector] Registered agent: {agent_id}")

    def unregister_agent(self, agent_id: str):
        """Unregister an agent (on shutdown)."""
        if agent_id in self.agent_states:
            del self.agent_states[agent_id]
            logger.debug(f"[DeadlockDetector] Unregistered agent: {agent_id}")

    def update_activity(self, agent_id: str, state: Optional[str] = None):
        """
        Agent reports activity.

        Args:
            agent_id: ID of active agent
            state: Optional state update (idle, processing, etc.)
        """
        if agent_id not in self.agent_states:
            self.register_agent(agent_id)

        activity = self.agent_states[agent_id]
        activity.last_activity = time.time()
        activity.message_count += 1

        if state:
            activity.state = state

        logger.debug(
            f"[DeadlockDetector] Activity: {agent_id} "
            f"(state={activity.state}, messages={activity.message_count})"
        )

    async def monitor(self):
        """
        Background task checking for deadlocks.

        Runs continuously until stopped. Checks agent activity at
        regular intervals and triggers recovery on deadlock.
        """
        # Note: running flag is set by start() method
        logger.info(
            f"[DeadlockDetector] Starting monitor "
            f"(timeout={self.timeout}s, interval={self.check_interval}s)"
        )

        try:
            while self.running:
                await asyncio.sleep(self.check_interval)
                await self._check_for_deadlocks()
        except asyncio.CancelledError:
            logger.info("[DeadlockDetector] Monitor cancelled")
            raise
        finally:
            self.running = False

    async def _check_for_deadlocks(self):
        """Check all agents for deadlock conditions."""
        now = time.time()
        stuck_agents = []

        for agent_id, activity in self.agent_states.items():
            idle_time = now - activity.last_activity

            if idle_time > self.timeout:
                stuck_agents.append((agent_id, idle_time))

        if stuck_agents:
            await self._handle_deadlock(stuck_agents)

    async def _handle_deadlock(self, stuck_agents):
        """
        Handle detected deadlock.

        Recovery strategies:
        1. Log warning
        2. Call callback if provided
        3. Raise error for coordinator to handle

        Args:
            stuck_agents: List of (agent_id, idle_time) tuples
        """
        self.deadlocks_detected += 1

        # Build error message
        agents_str = ", ".join(
            f"{agent_id} (idle {idle_time:.1f}s)"
            for agent_id, idle_time in stuck_agents
        )

        error_msg = (
            f"Deadlock detected! Stuck agents: {agents_str}. "
            f"Total deadlocks: {self.deadlocks_detected}"
        )

        logger.error(f"[DeadlockDetector] {error_msg}")

        # Call custom handler if provided
        if self.on_deadlock:
            try:
                await self.on_deadlock(stuck_agents)
                self.deadlocks_recovered += 1
                logger.info("[DeadlockDetector] Recovery handler succeeded")
            except Exception as e:
                logger.error(f"[DeadlockDetector] Recovery failed: {e}")

        # Raise error for coordinator
        raise DeadlockError(error_msg)

    async def start(self):
        """Start monitoring in background task."""
        if not self.monitor_task or self.monitor_task.done():
            self.running = True  # Set flag before creating task
            self.monitor_task = asyncio.create_task(self.monitor())
            logger.info("[DeadlockDetector] Started background monitoring")

    async def stop(self):
        """Stop monitoring gracefully."""
        self.running = False

        if self.monitor_task and not self.monitor_task.done():
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass

        logger.info("[DeadlockDetector] Stopped")

    def get_stats(self) -> Dict:
        """Get deadlock detection statistics."""
        return {
            "deadlocks_detected": self.deadlocks_detected,
            "deadlocks_recovered": self.deadlocks_recovered,
            "agents_monitored": len(self.agent_states),
            "running": self.running
        }

    def get_agent_status(self) -> Dict[str, Dict]:
        """Get status of all monitored agents."""
        now = time.time()
        return {
            agent_id: {
                "idle_time": now - activity.last_activity,
                "message_count": activity.message_count,
                "state": activity.state,
                "healthy": (now - activity.last_activity) < self.timeout
            }
            for agent_id, activity in self.agent_states.items()
        }
