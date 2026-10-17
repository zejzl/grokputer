"""
Pantheon Coordinator - Orchestrates all 9 agents in the Pantheon architecture

Default behavior is planning only (decompose + safety review). Execution is opt-in (--execute) and
requires per-command confirmation; see _handle_pantheon_task.

The 9 Agents (ALL IMPLEMENTED):
1. Observer - Screen capture and vision [OK]
2. Reasoner (Coordinator) - Task decomposition [OK]
3. Actor - Command execution [OK]
4. Validator - Safety and quality checks [OK]
5. Learner - Pattern recognition [OK]
6. Memory Manager - Persistent state [OK]
7. Executor - Multi-step workflow execution [OK]
8. Analyzer - Performance metrics and health monitoring [OK]
9. Improver - Self-optimization and continuous improvement [OK]
"""
from __future__ import annotations

import asyncio
import inspect
import logging
import platform
import re
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from src.agents.character_analysis_agent import CharacterAnalysisAgent
from src.agents.coordinator import Coordinator
from src.agents.executor_agent import ExecutorAgent
from src.agents.learner import LearnerAgent
from src.agents.story_generation_agent import StoryGenerationAgent
from src.agents.validator import ValidatorAgent
from src.core.base_agent import BaseAgent
from src.core.message_bus import Message, MessageBus, MessagePriority
from src.memory.backends.redis_store import RedisMemoryBackend
from src.memory.hierarchical_memory import HierarchicalMemoryManager
from src.memory.interfaces import MemoryConfig

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

        # Plan/execute workflow: planning only unless execute mode is on AND a confirm_callback approves each command
        self.execute_mode: bool = bool((config or {}).get("pantheon_execute", False))
        self.confirm_callback: Optional[Callable[[Dict[str, Any], str], Any]] = None  # (subtask, command) -> bool
        self.last_report: Optional[Dict[str, Any]] = None

    async def initialize_pantheon(
        self,
        observer: Any,  # ObserverAgent (observer_agent.py) in main.py; Observer (observer.py) also fits
        reasoner: Coordinator,
        actor: Any,  # ActorAgent (actor_agent.py) in main.py; Actor (actor.py) also fits
        validator: ValidatorAgent,
        learner: Optional[LearnerAgent] = None,
        memory_config: Optional[MemoryConfig] = None,
        executor: Optional[ExecutorAgent] = None,
        analyzer: Optional[Any] = None,  # analyzer_agent.AnalyzerAgent or analyzer.AnalyzerAgent
        improver: Optional[Any] = None,  # improver_agent.ImproverAgent or improver.ImproverAgent
        character_analyzer: Optional[CharacterAnalysisAgent] = None,
        story_generator: Optional[StoryGenerationAgent] = None,
        visionary: Optional["VisionaryAgent"] = None,
        love_agent: Optional["LoveAgent"] = None,
        documentation_agent: Optional["DocumentationAgent"] = None,
        maf_coordinator: Optional["MAFCoordinator"] = None,
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
            "maf_coordinator": maf_coordinator,
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

    # ------------------------------------------------------------------
    # Plan / execute workflow
    #
    # Default (plan mode): learn -> decompose -> safety-review each subtask -> report. Nothing is run.
    # Execute mode (config "pantheon_execute", CLI --execute): additionally, for each "actor" subtask,
    # propose ONE command, validate it, ask the confirm_callback, and only then run it.
    # With no confirm_callback nothing is ever executed.
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_subtasks(raw: Any) -> List[Dict[str, Any]]:
        """Coerce decomposition output into [{index, id, description, agent, priority, dependencies}]."""
        if isinstance(raw, dict):
            raw = raw.get("subtasks", [])
        subtasks = []
        for i, item in enumerate(raw or []):
            if isinstance(item, str):
                item = {"description": item}
            if not isinstance(item, dict):
                continue
            subtasks.append(
                {
                    "index": i,
                    "id": item.get("id", f"sub{i + 1}"),
                    "description": str(item.get("description") or item.get("content") or "").strip(),
                    "agent": item.get("agent") or item.get("target_agent") or "unknown",
                    "priority": item.get("priority", "medium"),
                    "dependencies": list(item.get("dependencies") or []),
                }
            )
        return subtasks

    async def _handle_pantheon_task(self, message: Message) -> Dict:
        """Plan a task with the Pantheon (and, in execute mode, run confirmed actor subtasks)."""
        task = message.content.get("task", "")
        task_id = message.content.get("task_id", f"task_{datetime.now().timestamp()}")
        start_time = datetime.now().timestamp()
        mode = "execute" if self.execute_mode else "plan"

        self.session_logger.log_agent_activity(self.agent_id, f"Pantheon handling task ({mode} mode): {task}")

        try:
            report = await self._plan_and_maybe_execute(task, task_id, mode, start_time)
        except Exception as e:
            logger.error(f"[PANTHEON] Task failed: {e}", exc_info=True)
            report = {"status": "failed", "task_id": task_id, "mode": mode, "error": str(e), "subtasks": []}
            self.pantheon_stats["tasks_failed"] += 1

        report["execution_time"] = datetime.now().timestamp() - start_time
        self.last_report = report
        self.session_logger.log_agent_activity(
            self.agent_id, f"Pantheon task finished: {task_id} (status={report['status']}, mode={mode})"
        )

        # Always signal, so the caller never waits out its timeout after an error
        self.task_completion_event.set()
        return report

    async def _plan_and_maybe_execute(self, task: str, task_id: str, mode: str, start_time: float) -> Dict[str, Any]:
        # Phase 0: learned optimizations
        optimization = None
        if self.agents.get("learner"):
            optimization = await self.agents["learner"].process_message(
                Message(
                    message_type="suggest_optimization",
                    from_agent=self.agent_id,
                    to_agent="learner",
                    priority=MessagePriority.NORMAL,
                    content={"task_type": task},
                )
            )

        # Phase 1: decompose
        if self.agents.get("coordinator"):
            decomposed = await self.agents["coordinator"].process_message(
                Message(
                    message_type="decompose_task",
                    from_agent=self.agent_id,
                    to_agent="coordinator",
                    priority=MessagePriority.NORMAL,
                    content={"task": task, "task_id": task_id},
                )
            )
        else:
            decomposed = {"subtasks": [{"description": task, "agent": "actor"}]}
        subtasks = self._normalize_subtasks(decomposed)

        if not subtasks:
            self.pantheon_stats["tasks_failed"] += 1
            return {"status": "failed", "task_id": task_id, "mode": mode, "error": "No subtasks produced", "subtasks": []}

        # Phase 2: safety review of every subtask description
        flagged = await self._review_plan(subtasks)

        # Phase 3 (execute mode only): confirmed, validated, one command at a time
        execution: List[Dict[str, Any]] = []
        if mode == "execute":
            execution = await self._execute_plan(subtasks, flagged)

        executed = [e for e in execution if e["status"] == "executed"]
        failed = [e for e in execution if e["status"] == "failed"]
        if mode == "plan":
            status = "planned"
        elif failed:
            status = "partially_executed" if executed else "failed"
        else:
            status = "executed" if executed else "no_actions_run"

        success = status in ("planned", "executed", "no_actions_run")
        self.pantheon_stats["tasks_completed" if success else "tasks_failed"] += 1

        # Phase 4: learning (best effort; never aborts the report)
        if self.agents.get("learner"):
            try:
                await self.agents["learner"].process_message(
                    Message(
                        message_type="record_execution",
                        from_agent=self.agent_id,
                        to_agent="learner",
                        priority=MessagePriority.LOW,
                        content={
                            "task_id": task_id,
                            "task_type": task,
                            "actions": [s["description"] for s in subtasks],
                            "success": success,
                            "execution_time": datetime.now().timestamp() - start_time,
                            "metadata": {"mode": mode, "flagged": sorted(flagged)},
                        },
                    )
                )
                if success:
                    self.pantheon_stats["patterns_learned"] += 1
            except Exception as e:
                logger.warning(f"[PANTHEON] Learner could not record this run: {e}")

        return {
            "status": status,
            "task_id": task_id,
            "mode": mode,
            "subtasks": subtasks,
            "safety_flags": {i: flagged[i] for i in sorted(flagged)},
            "execution": execution,
            "optimization_used": optimization is not None,
        }

    async def _review_plan(self, subtasks: List[Dict[str, Any]]) -> Dict[int, List[str]]:
        """Run the validator's safety check on every subtask; returns {index: issues} for flagged ones."""
        flagged: Dict[int, List[str]] = {}
        validator = self.agents.get("validator")
        if not validator:
            return flagged
        for st in subtasks:
            reply = await validator.process_message(
                Message(
                    message_type="check_safety",
                    from_agent=self.agent_id,
                    to_agent="validator",
                    priority=MessagePriority.HIGH,
                    content={"content": st["description"]},
                )
            )
            self.pantheon_stats["validations_performed"] += 1
            verdict = (reply or {}).get("content", {})
            if not verdict.get("safe", True):
                flagged[st["index"]] = list(verdict.get("issues", []))
        return flagged

    async def _propose_command(self, description: str) -> Optional[str]:
        """Ask the LLM for a single simple command for a subtask (None if it cannot)."""
        client = getattr(self.agents.get("coordinator"), "grok_client", None)
        if client is None:
            return None
        prompt = (
            "Give exactly ONE command that accomplishes this step on "
            f"{platform.system()}:\n\n{description}\n\n"
            "The command is run directly WITHOUT a shell, so it must be a real executable (not a shell builtin or a "
            "PowerShell cmdlet; to use PowerShell write: powershell -NoProfile -Command \"...\"). It must not contain "
            "any of these characters: ; & | < > $ ` \\ % ( ). Use forward slashes in paths.\n"
            "Reply with only the command on a single line. If it cannot be done with one simple, safe command, "
            "reply with the single word NONE."
        )
        reply = await client.create_message(task=prompt, agent="pantheon_exec")
        if reply.get("status") != "success":
            return None
        text = (reply.get("content") or "").strip()
        fenced = re.search(r"```(?:\w+)?\s*(.*?)```", text, re.DOTALL)
        if fenced:
            text = fenced.group(1).strip()
        line = text.splitlines()[0].strip() if text else ""
        return None if not line or line.upper() == "NONE" else line

    async def _confirm(self, subtask: Dict[str, Any], command: str) -> bool:
        """Ask the user; no callback or any error means no."""
        if self.confirm_callback is None:
            return False
        try:
            answer = self.confirm_callback(subtask, command)
            if inspect.isawaitable(answer):
                answer = await answer
            return bool(answer)
        except Exception as e:
            logger.warning(f"[PANTHEON] Confirmation failed, treating as declined: {e}")
            return False

    async def _execute_plan(self, subtasks: List[Dict[str, Any]], flagged: Dict[int, List[str]]) -> List[Dict[str, Any]]:
        """Run actor subtasks one at a time: propose command -> validate -> confirm -> execute."""
        results: List[Dict[str, Any]] = []
        blocked: set = set()  # indices and ids of subtasks that failed, were declined, or were blocked
        executor = getattr(self.agents.get("actor"), "action_executor", None)
        validator = self.agents.get("validator")

        for st in subtasks:
            entry = {"index": st["index"], "description": st["description"], "agent": st["agent"], "status": "skipped"}
            results.append(entry)

            def finish(status: str, reason: str = "", _entry=entry, _st=st) -> None:
                _entry["status"] = status
                if reason:
                    _entry["reason"] = reason
                if status in ("failed", "declined", "blocked"):
                    blocked.update({_st["index"], _st["id"]})

            if any(dep in blocked for dep in st["dependencies"]):
                finish("blocked", "a dependency did not complete")
            elif st["index"] in flagged:
                finish("blocked", f"flagged by safety review: {', '.join(flagged[st['index']])}")
            elif st["agent"] != "actor":
                finish("skipped", f"only 'actor' subtasks can be executed (agent: {st['agent']})")
            elif executor is None:
                finish("skipped", "no action executor available")
            else:
                command = await self._propose_command(st["description"])
                if command is None:
                    finish("skipped", "no single simple command could be derived")
                    continue
                entry["command"] = command

                if validator:
                    verdict = await validator.process_message(
                        Message(
                            message_type="validate_bash",
                            from_agent=self.agent_id,
                            to_agent="validator",
                            priority=MessagePriority.HIGH,
                            content={"command": command},
                        )
                    )
                    self.pantheon_stats["validations_performed"] += 1
                    if not (verdict or {}).get("valid", False):
                        finish("blocked", f"validator rejected the command: {(verdict or {}).get('issues')}")
                        continue

                if not await self._confirm(st, command):
                    finish("declined", "not confirmed by the user")
                    continue

                outcome = await executor.execute_bash(command)
                entry["output"] = (outcome.get("stdout") or outcome.get("error") or "")[:500]
                entry["returncode"] = outcome.get("returncode")
                if outcome.get("status") == "success" and outcome.get("returncode", 0) == 0:
                    finish("executed")
                else:
                    finish("failed", str(outcome.get("error") or outcome.get("stderr") or "non-zero exit")[:200])

        return results

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
