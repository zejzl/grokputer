"""
Pantheon Coordinator - Orchestrates all 9 agents in the Pantheon architecture

The 9 Agents (ALL IMPLEMENTED):
1. Observer - Screen capture and vision ✅
2. Reasoner (Coordinator) - Task decomposition ✅
3. Actor - Command execution ✅
4. Validator - Safety and quality checks ✅
5. Learner - Pattern recognition ✅
6. Memory Manager - Persistent state ✅
7. Executor - Specialized execution with circuit breakers ✅
8. Analyzer - Performance metrics and health monitoring ✅
9. Improver - Self-optimization and continuous improvement ✅
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
from src.agents.learner import LearnerAgent
from src.memory.hierarchical_memory import HierarchicalMemoryManager
from src.memory.interfaces import MemoryConfig
from src.memory.backends.redis_store import RedisMemoryBackend
from src.agents.executor_agent import ExecutorAgent
from src.agents.analyzer import AnalyzerAgent
from src.agents.improver import ImproverAgent
from src.agents.character_analysis_agent import CharacterAnalysisAgent
from src.agents.story_generation_agent import StoryGenerationAgent

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
        self, message_bus: MessageBus, session_logger, config: Dict[str, Any], heartbeat_interval: float = 10.0
    ):
        super().__init__("pantheon_coordinator", message_bus, session_logger, config, heartbeat_interval)

        # Track all agents
        self.agents: Dict[str, BaseAgent] = {}
        self.task_queue: List[Dict] = []
        self.active_tasks: Dict[str, Dict] = {}
        self.pantheon_stats = {
            "tasks_completed": 0,
            "tasks_failed": 0,
            "validations_performed": 0,
            "patterns_learned": 0,
            "improvements_applied": 0,
        }

        # Completion signaling
        self.task_completion_event = asyncio.Event()

    async def initialize_pantheon(
        self,
        observer: Observer,
        reasoner: Coordinator,
        actor: Actor,
        validator: ValidatorAgent,
        learner: Optional[LearnerAgent] = None,
        memory_config: Optional[MemoryConfig] = None,
        executor: Optional[ExecutorAgent] = None,
        analyzer: Optional[AnalyzerAgent] = None,
        improver: Optional[ImproverAgent] = None,
        character_analyzer: Optional[CharacterAnalysisAgent] = None,
        story_generator: Optional[StoryGenerationAgent] = None,
        visionary: Optional["VisionaryAgent"] = None,
        love_agent: Optional["LoveAgent"] = None,
        documentation_agent: Optional["DocumentationAgent"] = None,
        memory_manager=None,
    ):
        """Initialize the Pantheon with all 9 agents."""
        # Initialize hierarchical memory system
        if memory_manager is None:
            if memory_config is None:
                memory_config = MemoryConfig()

            # Create Redis backend for long-term storage
            redis_backend = RedisMemoryBackend(memory_config)

            # Create hierarchical memory manager with knowledge graph
            hierarchical_memory = HierarchicalMemoryManager(memory_config, redis_backend)

            # Start hierarchical memory system
            await hierarchical_memory.start()
        else:
            hierarchical_memory = memory_manager

        # Inject memory manager into agents that need it
        if learner and hasattr(learner, "memory_manager"):
            learner.memory_manager = hierarchical_memory

        self.agents = {
            "observer": observer,
            "coordinator": reasoner,
            "actor": actor,
            "validator": validator,
            "learner": learner,
            "memory": hierarchical_memory,
            "executor": executor,
            "analyzer": analyzer,
            "improver": improver,
            "character_analyzer": character_analyzer,
            "story_generator": story_generator,
            "visionary": visionary,
            "love_agent": love_agent,
            "documentation_agent": documentation_agent,
        }

        self.session_logger.log_agent_start(self.agent_id)

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
            if msg_type == "new_task":
                return await self._handle_pantheon_task(message)
            elif msg_type == "get_stats":
                return self.get_pantheon_stats()
            elif msg_type == "character_analysis_request":
                return await self._handle_character_analysis(message)
            elif msg_type == "story_generation_request":
                return await self._handle_story_generation(message)
            else:
                # Delegate to reasoner
                if "reasoner" in self.agents:
                    return await self.agents["reasoner"].process_message(message)
        finally:
            self._update_state("idle")

    async def _handle_pantheon_task(self, message: Message) -> Dict:
        """Handle a task using the full Pantheon workflow with all 9 agents."""
        task = message.content.get("task", "")
        task_id = message.content.get("task_id", f"task_{datetime.now().timestamp()}")
        start_time = datetime.now().timestamp()

        self.session_logger.log_agent_activity(self.agent_id, f"Pantheon handling task: {task}")

        # Phase 0: Check for learned optimizations
        optimization = None
        if "learner" in self.agents:
            learner_msg = Message(
                message_type="suggest_optimization",
                from_agent="pantheon_coordinator",
                to_agent="learner",
                priority=MessagePriority.NORMAL,
                content={"task_type": task},
            )
            optimization = await self.agents["learner"].process_message(learner_msg)

        # Phase 1: Reasoning - Decompose task
        if "coordinator" in self.agents:
            reasoner_msg = Message(
                message_type="decompose_task",
                from_agent="pantheon_coordinator",
                to_agent="coordinator",
                priority=MessagePriority.NORMAL,
                content={"task": task, "task_id": task_id},
            )
            decomposed = await self.agents["coordinator"].process_message(reasoner_msg)
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
                content={},
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
                content={"command": task},
            )
            validation = await self.agents["validator"].process_message(val_msg)
            validation_passed = validation.get("valid", False) if validation else True
            self.pantheon_stats["validations_performed"] += 1

        if not validation_passed:
            self.pantheon_stats["tasks_failed"] += 1
            return {"status": "rejected", "reason": "Failed safety validation", "task_id": task_id}

        # Phase 4: Execution - Perform action (use Executor if available, else Actor)
        result = None
        execution_time = 0.0

        if "executor" in self.agents and validation_passed:
            # Use advanced Executor with retry and circuit breakers
            executor_msg = Message(
                message_type="execute_with_retry",
                from_agent="pantheon_coordinator",
                to_agent="executor",
                priority=MessagePriority.NORMAL,
                content={"action": {"type": "bash", "params": {"command": task}, "id": task_id}, "max_retries": 3},
            )
            result = await self.agents["executor"].process_message(executor_msg)
        elif "actor" in self.agents and validation_passed:
            # Fallback to basic Actor
            actor_msg = Message(
                message_type="execute",
                from_agent="pantheon_coordinator",
                to_agent="actor",
                priority=MessagePriority.NORMAL,
                content={"task": task, "task_id": task_id},
            )
            result = await self.agents["actor"].process_message(actor_msg)

        execution_time = datetime.now().timestamp() - start_time

        # Phase 5: Post-execution validation
        final_state = None
        if "observer" in self.agents:
            obs_msg = Message(
                message_type="capture",
                from_agent="pantheon_coordinator",
                to_agent="observer",
                priority=MessagePriority.NORMAL,
                content={},
            )
            final_state = await self.agents["observer"].process_message(obs_msg)

        # Track completion
        success = result and result.get("status") not in ["error", "failed", "rejected"]

        # Phase 5.5: Conflict Resolution (if execution failed but validation passed)
        conflict_resolved = False
        if not success and validation_passed:
            conflict_resolution = await self._resolve_pantheon_conflict(task, task_id, result)
            if conflict_resolution["resolved"]:
                success = True
                result = conflict_resolution["result"]
                conflict_resolved = True
                self.pantheon_stats["conflicts_resolved"] = self.pantheon_stats.get("conflicts_resolved", 0) + 1

        # Phase 6: Learning - Record execution for pattern learning
        if "learner" in self.agents:
            learner_msg = Message(
                message_type="record_execution",
                from_agent="pantheon_coordinator",
                to_agent="learner",
                priority=MessagePriority.LOW,
                content={
                    "task_id": task_id,
                    "task_type": task,
                    "actions": [task],
                    "success": success,
                    "execution_time": execution_time,
                    "metadata": {"validation_passed": validation_passed, "conflict_resolved": conflict_resolved},
                },
            )
            await self.agents["learner"].process_message(learner_msg)
            if success:
                self.pantheon_stats["patterns_learned"] += 1

        # Phase 7: Analytics - Record metrics
        if "analyzer" in self.agents:
            analyzer_msg = Message(
                message_type="record_task",
                from_agent="pantheon_coordinator",
                to_agent="analyzer",
                priority=MessagePriority.LOW,
                content={
                    "task_type": task,
                    "execution_time": execution_time,
                    "success": success,
                    "agent_id": "executor" if "executor" in self.agents else "actor",
                },
            )
            await self.agents["analyzer"].process_message(analyzer_msg)

        # Phase 8: Improvement - Analyze for optimizations
        if "improver" in self.agents and self.pantheon_stats["tasks_completed"] % 10 == 0:
            # Every 10 tasks, analyze for improvements
            improver_msg = Message(
                message_type="analyze_for_improvements",
                from_agent="pantheon_coordinator",
                to_agent="improver",
                priority=MessagePriority.LOW,
                content={},
            )
            improvements = await self.agents["improver"].process_message(improver_msg)
            if improvements and improvements.get("improvements_found", 0) > 0:
                self.pantheon_stats["improvements_applied"] += improvements.get("auto_applied", 0)

        # Update stats
        if success:
            self.pantheon_stats["tasks_completed"] += 1
        else:
            self.pantheon_stats["tasks_failed"] += 1

        self.session_logger.log_agent_activity(
            self.agent_id, f"Pantheon task completed: {task_id} (success={success}, time={execution_time:.2f}s)"
        )

        # Signal task completion
        self.task_completion_event.set()

        return {
            "status": "completed" if success else "failed",
            "task_id": task_id,
            "result": result,
            "validation_passed": validation_passed,
            "initial_state": initial_state,
            "final_state": final_state,
            "execution_time": execution_time,
            "optimization_used": optimization is not None,
            "conflict_resolved": conflict_resolved,
            "pantheon_workflow": "full_9_agent",
        }

    async def _resolve_pantheon_conflict(self, task: str, task_id: str, failed_result: Dict) -> Dict[str, Any]:
        """
        Resolve conflicts in Pantheon execution using consensus voting.

        Args:
            task: Original task
            task_id: Task ID
            failed_result: Failed execution result

        Returns:
            Resolution result
        """
        self.session_logger.log_agent_activity(self.agent_id, f"Resolving conflict for task: {task}")

        # Method 1: Retry with different agent (Actor vs Executor)
        if "executor" in self.agents and failed_result.get("agent") != "executor":
            # Try with Executor
            executor_msg = Message(
                message_type="execute_with_retry",
                from_agent="pantheon_coordinator",
                to_agent="executor",
                priority=MessagePriority.HIGH,
                content={"action": {"type": "bash", "params": {"command": task}, "id": task_id}, "max_retries": 2},
            )
            retry_result = await self.agents["executor"].process_message(executor_msg)
            if retry_result and retry_result.get("status") == "success":
                return {"resolved": True, "result": retry_result, "method": "agent_switch"}

        # Method 2: Consensus voting with multiple agents
        votes = []
        if "validator" in self.agents:
            # Validator vote
            val_msg = Message(
                message_type="validate_bash",
                from_agent="pantheon_coordinator",
                to_agent="validator",
                priority=MessagePriority.HIGH,
                content={"command": task, "expected_success": True},
            )
            val_vote = await self.agents["validator"].process_message(val_msg)
            votes.append(val_vote.get("valid", False) if val_vote else False)

        if "analyzer" in self.agents:
            # Analyzer assessment
            analyzer_msg = Message(
                message_type="assess_execution",
                from_agent="pantheon_coordinator",
                to_agent="analyzer",
                priority=MessagePriority.NORMAL,
                content={"task": task, "result": failed_result},
            )
            analyzer_vote = await self.agents["analyzer"].process_message(analyzer_msg)
            votes.append(analyzer_vote.get("should_retry", False) if analyzer_vote else False)

        # Majority vote
        positive_votes = sum(votes)
        if positive_votes > len(votes) / 2:
            # Retry one more time with fallback agent
            if "actor" in self.agents:
                actor_msg = Message(
                    message_type="execute",
                    from_agent="pantheon_coordinator",
                    to_agent="actor",
                    priority=MessagePriority.HIGH,
                    content={"task": task, "task_id": task_id},
                )
                final_result = await self.agents["actor"].process_message(actor_msg)
                if final_result and final_result.get("status") == "success":
                    return {"resolved": True, "result": final_result, "method": "consensus_retry"}

        return {"resolved": False, "result": failed_result, "method": "unresolvable"}

    async def _handle_character_analysis(self, message: Message) -> Dict:
        """Handle character analysis requests using the CharacterAnalysisAgent."""
        if "character_analyzer" not in self.agents or not self.agents["character_analyzer"]:
            return {"error": "CharacterAnalysisAgent not available"}

        # Forward to character analyzer
        response = await self.agents["character_analyzer"].process_message(message)
        return response.content if response else {"error": "No response from character analyzer"}

    async def _handle_story_generation(self, message: Message) -> Dict:
        """Handle story generation requests using the StoryGenerationAgent."""
        if "story_generator" not in self.agents or not self.agents["story_generator"]:
            return {"error": "StoryGenerationAgent not available"}

        # Forward to story generator
        response = await self.agents["story_generator"].process_message(message)
        return response.content if response else {"error": "No response from story generator"}

    def get_pantheon_stats(self) -> Dict:
        """Get Pantheon performance statistics."""
        total_tasks = self.pantheon_stats["tasks_completed"] + self.pantheon_stats["tasks_failed"]
        success_rate = self.pantheon_stats["tasks_completed"] / total_tasks if total_tasks > 0 else 0.0

        return {
            "total_agents": len(self.agents),
            "active_agents": [name for name in self.agents.keys()],
            "tasks_completed": self.pantheon_stats["tasks_completed"],
            "tasks_failed": self.pantheon_stats["tasks_failed"],
            "success_rate": success_rate,
            "validations_performed": self.pantheon_stats["validations_performed"],
            "patterns_learned": self.pantheon_stats["patterns_learned"],
            "improvements_applied": self.pantheon_stats["improvements_applied"],
        }

    async def on_start(self):
        """Pantheon-specific startup."""
        await super().on_start()
        self.session_logger.log_agent_start(self.agent_id)

    async def on_stop(self):
        """Clean shutdown of all Pantheon agents."""
        for agent_name, agent in self.agents.items():
            if hasattr(agent, "running"):
                agent.running = False
            self.session_logger.log_agent_activity(self.agent_id, f"Stopping {agent_name}")

        # Stop hierarchical memory system
        if "memory" in self.agents and hasattr(self.agents["memory"], "stop"):
            await self.agents["memory"].stop()

        await super().on_stop()

    async def _handle_todo_sync(self, message: Message):
        """Handle todo sync messages from dynamic todo manager."""
        logger.info(f"[PANTHEON] Todo update received: {message.content}")

        # Forward to reasoner (Council proxy)
        if "reasoner" in self.agents:
            todo_msg = Message(
                message_type="todo_update", from_agent="todo_manager", to_agent="reasoner", content=message.content
            )
            await self.agents["reasoner"].process_message(todo_msg)

        # Forward to learner (Taskmaster proxy)
        if "learner" in self.agents:
            todo_msg = Message(
                message_type="todo_update", from_agent="todo_manager", to_agent="learner", content=message.content
            )
            await self.agents["learner"].process_message(todo_msg)

        # Agents can publish edits back via message_bus
