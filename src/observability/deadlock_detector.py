from __future__ import annotations

import asyncio
import time
from typing import Dict, Any
from src.core.message_bus import MessageBus


class DeadlockDetector:
    """Enhanced watchdog for detecting and recovering from deadlocks with auto-restart."""

    def __init__(self, timeout_seconds: float = 60.0, check_interval: float = 10.0, max_restarts: int = 3):
        self.timeout = timeout_seconds
        self.check_interval = check_interval
        self.max_restarts = max_restarts
        self.agent_states: Dict[str, Dict[str, Any]] = {}  # agent_id -> {'last_activity': time, 'restarts': 0, 'status': 'running'}
        self.running = False
        self.message_bus: MessageBus = None
        self.lifecycle_manager: AgentLifecycleManager = None
        self.restart_count = 0

    async def start(self, message_bus: MessageBus, lifecycle_manager: AgentLifecycleManager):
        """Start monitoring."""
        self.message_bus = message_bus
        self.lifecycle_manager = lifecycle_manager
        self.running = True
        asyncio.create_task(self._monitor_loop())

    async def _monitor_loop(self):
        """Background monitoring loop."""
        while self.running:
            await asyncio.sleep(self.check_interval)
            await self._check_for_deadlocks()

    async def update_activity(self, agent_id: str, status: str = 'running'):
        """Update agent activity."""
        if agent_id not in self.agent_states:
            self.agent_states[agent_id] = {'last_activity': time.time(), 'restarts': 0, 'status': status}
        else:
            self.agent_states[agent_id]['last_activity'] = time.time()
            self.agent_states[agent_id]['status'] = status

    async def _check_for_deadlocks(self):
        """Check and recover from deadlocks."""
        now = time.time()
        for agent_id, state in list(self.agent_states.items()):
            idle_time = now - state['last_activity']
            if idle_time > self.timeout and state['status'] == 'running':
                print(f"[DEADLOCK] Agent {agent_id} idle for {idle_time:.1f}s - attempting restart")
                await self._restart_agent(agent_id, state)

    async def _restart_agent(self, agent_id: str, state: Dict[str, Any]):
        from src.core.agent_lifecycle_manager import AgentLifecycleManager

        """Auto-restart stuck agent."""
        if state['restarts'] >= self.max_restarts:
            print(f"[DEADLOCK] Max restarts reached for {agent_id} - escalating to full swarm restart")
            await self._full_restart()
            return

        try:
            # Stop and restart agent
            await self.lifecycle_manager.stop_agent(agent_id)
            await asyncio.sleep(2)  # Cooldown
            await self.lifecycle_manager.start_agent(agent_id)
            
            state['restarts'] += 1
            state['last_activity'] = time.time()
            print(f"[RECOVERY] Agent {agent_id} restarted (attempt {state['restarts']}/{self.max_restarts})")
            
            # Notify via message bus
            recovery_msg = {"type": "agent_recovery", "agent": agent_id, "reason": "deadlock", "attempt": state['restarts']}
            await self.message_bus.broadcast("recovery", recovery_msg)
            
        except Exception as e:
            print(f"[ERROR] Failed to restart {agent_id}: {e}")
            state['status'] = 'failed'

    async def _full_restart(self):
        """Restart entire swarm/Pantheon."""
        self.restart_count += 1
        print(f"[EMERGENCY] Full swarm restart (attempt {self.restart_count})")
        await self.lifecycle_manager.stop_all_agents()
        await asyncio.sleep(5)
        await self.lifecycle_manager.start_all_agents()

    async def stop(self):
        """Stop monitoring."""
        self.running = False
        for agent_id in self.agent_states:
            self.agent_states[agent_id]['status'] = 'stopped'

    def get_stats(self) -> Dict[str, Any]:
        """Get recovery stats."""
        now = time.time()
        stats = {
            'active_agents': len([s for s in self.agent_states.values() if s['status'] == 'running']),
            'total_restarts': sum(s['restarts'] for s in self.agent_states.values()),
            'current_idle_times': {aid: now - s['last_activity'] for aid, s in self.agent_states.items() if s['status'] == 'running'}
        }
        return stats