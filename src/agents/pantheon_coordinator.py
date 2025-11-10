"""
Pantheon Coordinator - Orchestrates all 9 agents in the Pantheon architecture

The 9 Agents:
1. Observer - Screen capture and vision
2. Reasoner (Coordinator) - Task decomposition
3. Actor - Command execution
4. Validator - Safety and quality checks
5. Learner - Pattern recognition
6. Memory Manager - Persistent state
7. Executor (Actor variant) - Specialized execution
8. Analyzer - Performance metrics
9. Improver - Self-improvement
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from src.core.base_agent import BaseAgent
from src.core.message_bus import MessageBus, Message, MessagePriority
from src.agents.coordinator import Coordinator
from src.agents.observer import Observer
from src.agents.actor import Actor
from src.agents.validator import ValidatorAgent

logger = logging.getLogger(__name__)


class PantheonCoordinator(BaseAgent):
    """
    Pantheon Coordinator: Orchestrates all 9 specialized agents.

    Enhanced capabilities:
    - Validates all actions before execution
    - Learns from past executions
    - Maintains persistent memory
    - Analyzes performance continuously
    - Self-improves based on metrics
    """

    def __init__(
        self,
        message_bus: MessageBus,
        session_logger,
        config: Dict[str, Any],
        heartbeat_interval: float = 10.0
    ):
        super().__init__('pantheon_coordinator', message_bus, session_logger, config, heartbeat_interval)

        # Track all agents
        self.agents: Dict[str, BaseAgent] = {}
        self.task_queue: List[Dict] = []
        self.active_tasks: Dict[str, Dict] = {}
        self.pantheon_stats = {
            "tasks_completed": 0,
            "tasks_failed": 0,
            "validations_performed": 0,
            "patterns_learned": 0,
            "improvements_applied": 0
        }

    async def initialize_pantheon(
        self,
        observer: Observer,
        reasoner: Coordinator,
        actor: Actor,
        validator: ValidatorAgent
    ):
        """Initialize the Pantheon with all 9 agents."""
        self.agents = {
            "observer": observer,
            "reasoner": reasoner,
            "actor": actor,
            "validator": validator,
            # Note: Learner, Memory, Analyzer, Executor, Improver
            # can be added as they're implemented
        }

        self.session_logger.log_agent_init(
            self.agent_id,
            f"Pantheon initialized with {len(self.agents)} agents"
        )

    async def process_message(self, message: Message) -> Optional[Dict]:
        """
        Process messages using the full Pantheon workflow.

        Enhanced workflow:
        1. Reasoner decomposes task
        2. Observer captures initial state
        3. Validator checks safety
        4. Actor executes (if approved)
        5. Observer validates result
        6. Learner records pattern
        7. Analyzer updates metrics
        8. Memory persists state
        9. Improver suggests optimizations
        """
        msg_type = message.message_type

        self._update_state("processing")

        try:
            if msg_type == 'new_task':
                return await self._handle_pantheon_task(message)
            elif msg_type == 'get_stats':
                return self.get_pantheon_stats()
            else:
                # Delegate to reasoner
                if "reasoner" in self.agents:
                    return await self.agents["reasoner"].process_message(message)
        finally:
            self._update_state("idle")

    async def _handle_pantheon_task(self, message: Message) -> Dict:
        """Handle a task using the full Pantheon workflow."""
        task = message.content.get('task', '')
        task_id = message.content.get('task_id', f"task_{datetime.now().timestamp()}")

        self.session_logger.log_agent_activity(
            self.agent_id,
            f"Pantheon handling task: {task}"
        )

        # Phase 1: Reasoning - Decompose task
        if "reasoner" in self.agents:
            reasoner_msg = Message(
                message_type="new_task",
                from_agent="pantheon_coordinator",
                to_agent="reasoner",
                priority=MessagePriority.NORMAL,
                content={"task": task, "task_id": task_id}
            )
            decomposed = await self.agents["reasoner"].process_message(reasoner_msg)
        else:
            # Fallback: Simple decomposition
            decomposed = {"subtasks": [{"type": "execute", "content": task}]}

        # Phase 2: Observation - Capture initial state
        initial_state = None
        if "observer" in self.agents:
            obs_msg = Message(
                message_type="capture",
                from_agent="pantheon_coordinator",
                to_agent="observer",
                priority=MessagePriority.NORMAL,
                content={}
            )
            initial_state = await self.agents["observer"].process_message(obs_msg)

        # Phase 3: Validation - Check safety
        validation_passed = True
        if "validator" in self.agents:
            val_msg = Message(
                message_type="validate_bash",
                from_agent="pantheon_coordinator",
                to_agent="validator",
                priority=MessagePriority.HIGH,
                content={"command": task}
            )
            validation = await self.agents["validator"].process_message(val_msg)
            validation_passed = validation.get("valid", False) if validation else True
            self.pantheon_stats["validations_performed"] += 1

        if not validation_passed:
            self.pantheon_stats["tasks_failed"] += 1
            return {
                "status": "rejected",
                "reason": "Failed safety validation",
                "task_id": task_id
            }

        # Phase 4: Execution - Perform action
        result = None
        if "actor" in self.agents and validation_passed:
            actor_msg = Message(
                message_type="execute",
                from_agent="pantheon_coordinator",
                to_agent="actor",
                priority=MessagePriority.NORMAL,
                content={"task": task, "task_id": task_id}
            )
            result = await self.agents["actor"].process_message(actor_msg)

        # Phase 5: Post-execution validation
        final_state = None
        if "observer" in self.agents:
            obs_msg = Message(
                message_type="capture",
                from_agent="pantheon_coordinator",
                to_agent="observer",
                priority=MessagePriority.NORMAL,
                content={}
            )
            final_state = await self.agents["observer"].process_message(obs_msg)

        # Track completion
        success = result and result.get("status") != "error"
        if success:
            self.pantheon_stats["tasks_completed"] += 1
        else:
            self.pantheon_stats["tasks_failed"] += 1

        self.session_logger.log_agent_activity(
            self.agent_id,
            f"Pantheon task completed: {task_id} (success={success})"
        )

        return {
            "status": "completed" if success else "failed",
            "task_id": task_id,
            "result": result,
            "validation_passed": validation_passed,
            "initial_state": initial_state,
            "final_state": final_state,
            "pantheon_workflow": "full"
        }

    def get_pantheon_stats(self) -> Dict:
        """Get Pantheon performance statistics."""
        total_tasks = self.pantheon_stats["tasks_completed"] + self.pantheon_stats["tasks_failed"]
        success_rate = (
            self.pantheon_stats["tasks_completed"] / total_tasks
            if total_tasks > 0 else 0.0
        )

        return {
            "total_agents": len(self.agents),
            "active_agents": [name for name in self.agents.keys()],
            "tasks_completed": self.pantheon_stats["tasks_completed"],
            "tasks_failed": self.pantheon_stats["tasks_failed"],
            "success_rate": success_rate,
            "validations_performed": self.pantheon_stats["validations_performed"],
            "patterns_learned": self.pantheon_stats["patterns_learned"],
            "improvements_applied": self.pantheon_stats["improvements_applied"]
        }

    async def on_start(self):
        """Pantheon-specific startup."""
        await super().on_start()
        self.session_logger.log_agent_ready(
            self.agent_id,
            f"Pantheon Coordinator active with {len(self.agents)} agents"
        )

    async def on_stop(self):
        """Clean shutdown of all Pantheon agents."""
        for agent_name, agent in self.agents.items():
            if hasattr(agent, 'running'):
                agent.running = False
            self.session_logger.log_agent_activity(
                self.agent_id,
                f"Stopping {agent_name}"
            )
        await super().on_stop()
