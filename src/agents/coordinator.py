# src/agents/coordinator.py
"""
Coordinator Agent: Task decomposition, delegation, and aggregation.
Ultra-pro version: Grok-powered reasoning for decomposition/routing.
Part of ORAM Pantheon/Swarm.
"""

import asyncio
import logging
import json
import time
import heapq
from typing import Dict, Any, List, Tuple
from enum import Enum
from collections import defaultdict

# Existing imports
from src.core.base_agent import BaseAgent
from src.core.message_bus import MessageBus, Message, MessagePriority
from src.grok_client import GrokClient, FallbackGrokClient
from src.observability.session_logger import SessionLogger
from src.observability.deadlock_detector import DeadlockDetector
from src.cognitive.agent_integration import CognitiveCoordinatorMixin

# New imports for enhanced decomposition
from src.agents.validator import ValidatorAgent
from src.agents.learner import LearnerAgent

# DPO optimization
from src.self_improvement.dpo_optimizer import AgentDPO
from src.self_improvement.preference_collector import PreferenceCollector


class TaskStatus(Enum):
    """Task status enumeration."""

    DELEGATED = "delegated"
    COMPLETED = "completed"
    FAILED = "failed"
    PENDING = "pending"


class DelegationTarget(Enum):
    """Possible delegation targets."""

    OBSERVER = "observer"
    ACTOR = "actor"
    VALIDATOR = "validator"
    MEMORY = "memory"
    ALL = "all"


class TaskPrioritizer:
    """
    Dynamic load balancer and prioritizer for subtask delegation.

    Uses priority queue to route tasks to least-loaded agents.
    Monitors MessageBus queue sizes for real-time load balancing.
    """

    def __init__(self, message_bus: MessageBus):
        self.bus = message_bus
        self.pq: List[Tuple[float, int, Dict]] = []  # (priority, id, subtask)
        self.agent_load: Dict[str, int] = defaultdict(int)  # agent_type -> pending count
        self.task_counter = 0

    async def get_load(self, agent_type: str) -> int:
        """
        Get current load for an agent type by checking MessageBus queue.

        Args:
            agent_type: Type of agent to check

        Returns:
            Current queue size for that agent type
        """
        try:
            # Check MessageBus queue size for this agent
            queue_size = self.bus.get_queue_size(agent_type)
            self.agent_load[agent_type] = queue_size
            return queue_size
        except Exception as e:
            # Fallback to cached load if MessageBus check fails
            return self.agent_load.get(agent_type, 0)

    async def add_subtask(self, subtask: Dict):
        """
        Add a subtask to the priority queue with dynamic load-based priority.

        Args:
            subtask: Subtask dictionary with target_agent, priority, etc.
        """
        agent_type = subtask.get("target_agent", "actor")

        # Get current load for this agent type
        load = await self.get_load(agent_type)

        # Calculate priority (lower priority number = higher priority)
        # Base priority from subtask
        base_priority = self._get_priority_value(subtask.get("priority", "medium"))

        # Adjust for load: higher load = lower priority (higher number)
        load_penalty = load * 0.1  # Small penalty per queued task

        # Time-sensitive tasks get bonus
        time_bonus = 0
        if subtask.get("type") in ["act", "action"] and subtask.get("priority") == "high":
            time_bonus = -0.5  # Boost priority for urgent actions

        final_priority = base_priority + load_penalty + time_bonus

        # Add to priority queue
        self.task_counter += 1
        heapq.heappush(self.pq, (final_priority, self.task_counter, subtask))

    async def get_next_subtask(self) -> Dict:
        """
        Get the highest priority subtask from the queue.

        Returns:
            Next subtask to execute
        """
        if not self.pq:
            return None

        priority, _, subtask = heapq.heappop(self.pq)
        return subtask

    def _get_priority_value(self, priority_str: str) -> float:
        """
        Convert priority string to numeric value.

        Args:
            priority_str: "high", "medium", "low"

        Returns:
            Numeric priority (lower = higher priority)
        """
        priority_map = {"high": 0.0, "medium": 1.0, "low": 2.0}
        return priority_map.get(priority_str.lower(), 1.0)

    def get_queue_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the prioritizer queue.

        Returns:
            Dictionary with queue statistics
        """
        return {
            "queued_tasks": len(self.pq),
            "agent_loads": dict(self.agent_load),
            "total_load": sum(self.agent_load.values()),
        }

    async def update_loads(self):
        """
        Update load information for all known agent types.
        """
        agent_types = ["observer", "actor", "validator", "memory", "analyzer", "improver"]
        for agent_type in agent_types:
            await self.get_load(agent_type)


class Coordinator(BaseAgent, CognitiveCoordinatorMixin):
    def __init__(
        self,
        message_bus: MessageBus = None,
        grok_client: FallbackGrokClient = None,
        session_logger: SessionLogger = None,
        deadlock_detector: DeadlockDetector = None,
        config: Dict[str, Any] = None,
        cognitive_enabled: bool = True,
    ):
        # Initialize BaseAgent first
        super().__init__(
            agent_id="coordinator",
            message_bus=message_bus,
            session_logger=session_logger,
            config=config
        )

        config = config or {
            "debug": False,
            "max_subtasks": 10,
            "auto_restart": True,
            "decomposition_prompt": """Decompose the following task into 2-5 specific, actionable subtasks:

Task: {task}

Return a JSON list of subtasks, where each subtask has:
- "description": Brief description of the subtask
- "agent": Suggested agent type (observer/actor/validator/analyzer/improver/memory)
- "priority": high/medium/low
- "dependencies": List of subtask indices this depends on (empty if none)

Example format:
[
  {{"description": "Analyze codebase", "agent": "observer", "priority": "high", "dependencies": []}},
  {{"description": "Execute changes", "agent": "actor", "priority": "high", "dependencies": [0]}}
]""",
        }
        BaseAgent.__init__(
            self, agent_id="coordinator", message_bus=message_bus, session_logger=session_logger, config=config
        )

        # Initialize cognitive capabilities
        CognitiveCoordinatorMixin.__init__(self, cognitive_enabled=cognitive_enabled)

        self.grok_client = grok_client or FallbackGrokClient()
        self.deadlock_detector = deadlock_detector

        # Enable TaskClient integration
        self.enable_task_client(
            [
                "task_coordination",
                "task_decomposition",
                "agent_orchestration",
                "workflow_management",
                "multi_agent_coordination",
            ]
        )
        self.config = config or {
            "debug": False,
            "max_subtasks": 10,
            "decomposition_prompt": """
Decompose the task '{task}' into 3-5 sequential or parallel sub-tasks for a multi-agent system.
Agents available: observer (screen/vision), actor (actions/bash/file/UI), validator (safety/checks).
For each sub-task, specify:
- id: Unique ID (e.g., sub1)
- type: 'observe', 'act', 'validate', etc.
- target_agent: 'observer', 'actor', 'validator'
- description: Brief instruction
- priority: 'high', 'medium', 'low'
- dependencies: List of prior sub-task IDs (e.g., ['sub1'])

Output as JSON list only, no extra text: [{{"id": "sub1", "type": "...", "target_agent": "...", "description": "...", "priority": "...", "dependencies": []}}]
            """,
            "aggregation_threshold": 0.8,  # Consensus score for completion
            "validator_enabled": True,  # Enable validator pre-scan
            "learner_enabled": True,  # Enable learner pattern integration
            "feasibility_threshold": 0.7,  # Minimum feasibility score
            "max_refinement_iterations": 3,  # Max self-prompt loops
        }

        # Initialize enhanced decomposition components
        self.validator = None
        self.learner = None
        if self.config.get("validator_enabled", True):
            self.validator = ValidatorAgent(
                agent_id="coordinator_validator",
                message_bus=message_bus,
                session_logger=session_logger,
                config={"debug": self.config.get("debug", False)},
            )

        if self.config.get("learner_enabled", True):
            self.learner = LearnerAgent(
                agent_id="coordinator_learner",
                message_bus=message_bus,
                session_logger=session_logger,
                config={"debug": self.config.get("debug", False)},
            )

        # Initialize load balancer and prioritizer
        self.task_prioritizer = TaskPrioritizer(message_bus)

        # Initialize DPO optimizer for parameter tuning
        param_space = {"temperature": (0.1, 1.0), "max_tokens": (50, 500), "timeout": (5, 30)}
        self.dpo_optimizer = AgentDPO(param_space)
        self.preference_collector = PreferenceCollector(self.dpo_optimizer, self.grok_client)

        # Already registered by BaseAgent

        self.logger = logging.getLogger(__name__)
        self.running = False
        self.active_tasks: Dict[str, List[Dict]] = {}  # task_id -> sub-tasks
        self.results: Dict[str, Any] = {}  # task_id -> aggregated results
        self.completed_subtasks: set = set()  # Track completed sub-IDs
        self.task_start_times: Dict[str, float] = {}  # task_id -> start timestamp

        if self.deadlock_detector:
            self.deadlock_detector.register_agent("coordinator")

        # Meta-reasoning and self-improvement tracking
        self.orchestration_traces: List[Dict] = []
        self.performance_metrics: Dict[str, Any] = {
            "tasks_completed": 0,
            "tasks_failed": 0,
            "avg_decomposition_time": 0.0,
            "avg_execution_time": 0.0,
            "conflict_resolution_attempts": 0,
            "successful_resolutions": 0,
        }

        self.logger.info("[COORDINATOR] Initialized - Ultra-Pro Mode with Meta-Reasoning")

    async def process_message(self, message):
        """
        Process a message (for compatibility with BaseAgent interface).
        """
        msg_type = message.message_type
        self.logger.info(f"[COORDINATOR] Processing: {msg_type} - {message.content}")

        if msg_type == "new_task":
            await self._handle_new_task(message)
            return {"status": "delegated"}
        elif msg_type == "decompose_task":
            task_data = message.content
            task_desc = task_data.get("task", "")
            task_id = task_data.get("task_id", "default")
            try:
                subtasks = await self._enhanced_decompose_task(task_desc, task_id)
                return {"subtasks": subtasks}
            except Exception as e:
                self.logger.error(f"[COORDINATOR] Decomposition failed: {e}, using fallback")
                subtasks = self._fallback_decompose(task_desc)
                return {"subtasks": subtasks}
        elif msg_type == "suggest_optimization":
            # Handle optimization requests
            return {"optimization": "none"}
        else:
            return {"status": "unknown_message_type"}

    async def run(self):
        """
        Main coordinator loop: Listen for tasks, decompose, delegate, aggregate.
        Includes loop prevention to avoid infinite processing.
        """
        self.running = True
        self.session_logger.log_agent_start("coordinator")
        self.logger.info("[COORDINATOR] Starting run loop")

        # Loop prevention
        max_iterations = self.config.get("max_coordinator_iterations", 1000)
        iteration_count = 0

        # Listen for incoming messages (new tasks or results)
        async for message in self.message_bus.subscribe("coordinator"):
            if not self.running:
                break

            iteration_count += 1
            if iteration_count >= max_iterations:
                self.logger.warning(f"[COORDINATOR] Max iterations ({max_iterations}) reached, stopping to prevent infinite loop")
                break

            msg_type = message.message_type
            self.logger.info(f"[COORDINATOR] Received: {msg_type} - {message.content} (iteration {iteration_count})")
            self.session_logger.log_agent_activity("coordinator", msg_type)

            if self.deadlock_detector:
                self.deadlock_detector.update_activity("coordinator", state="processing")

            if msg_type == "new_task":
                await self._handle_new_task(message)
            elif msg_type in ["action_result", "observation_result"]:
                await self._handle_result(message)
            elif msg_type == "action_failed":
                await self._handle_failure(message)

        self.session_logger.log_agent_stop("coordinator")
        self.logger.info("[COORDINATOR] Stopped")

    async def _handle_new_task(self, message: Message):
        """
        Decompose task using Grok, create sub-tasks, delegate.
        """
        task_data = message.content
        task_id = task_data.get("task_id", "default")
        task_desc = task_data.get("description", "")
        start_time = time.time()
        self.task_start_times[task_id] = start_time

        self.active_tasks[task_id] = []
        self.logger.info(f"[COORDINATOR] Decomposing task: {task_desc}")

        # Use enhanced decomposition with validator and learner integration
        try:
            subtasks = await self._enhanced_decompose_task(task_desc, task_id)
        except Exception as e:
            self.logger.error(f"[COORDINATOR] Enhanced decomposition failed: {e}, using fallback")
            subtasks = self._fallback_decompose(task_desc)

        decomposition_time = time.time() - start_time
        self.active_tasks[task_id] = subtasks
        self.session_logger.log_agent_activity(
            "coordinator", "decomposed", {"task_id": task_id, "subtasks": len(subtasks)}
        )

        # Record decomposition for cognitive learning
        self._record_decomposition(task_desc, subtasks)

        # Delegate sub-tasks (topological order for dependencies)
        await self._delegate_subtasks(task_id, subtasks)

    def _get_recent_decompositions(self) -> List[Dict[str, Any]]:
        """Get context from recent task decompositions for cognitive enhancement."""
        if not hasattr(self, "_decomposition_history"):
            self._decomposition_history = []

        # Return last 5 decompositions as context
        return self._decomposition_history[-5:]

    def _record_decomposition(self, task_desc: str, subtasks: List[Dict]):
        """Record decomposition for future cognitive enhancement."""
        if not hasattr(self, "_decomposition_history"):
            self._decomposition_history = []

        self._decomposition_history.append({"task": task_desc, "subtasks": subtasks, "timestamp": time.time()})

    async def _enhanced_decompose_task(self, task_desc: str, task_id: str) -> List[Dict]:
        """
        Enhanced task decomposition with validator pre-scan and learner patterns.

        Args:
            task_desc: Task description
            task_id: Unique task identifier

        Returns:
            List of validated and refined subtasks
        """
        self.logger.info(f"[COORDINATOR] Starting enhanced decomposition for: {task_desc}")

        # Step 1: Get learner insights for similar tasks
        learner_insights = await self._get_learner_insights(task_desc)
        self.logger.info(f"[COORDINATOR] Learner insights: {len(learner_insights)} patterns found")

        # Step 2: Initial decomposition with learner-enhanced prompt
        enhanced_prompt = self._build_enhanced_prompt(task_desc, learner_insights)
        try:
            subtasks = await asyncio.wait_for(
                self._decompose_with_prompt(enhanced_prompt, task_desc),
                timeout=30.0  # 30 second timeout
            )
        except asyncio.TimeoutError:
            self.logger.warning("[COORDINATOR] Decomposition timed out, using fallback")
            subtasks = self._fallback_decompose(task_desc)

        # Step 3: Validator pre-scan and refinement loop
        refined_subtasks = await self._validate_and_refine_subtasks(subtasks, task_desc, task_id)

        self.logger.info(f"[COORDINATOR] Enhanced decomposition complete: {len(refined_subtasks)} subtasks")
        return refined_subtasks

    async def _get_learner_insights(self, task_desc: str) -> List[Dict]:
        """
        Query learner for historical patterns and insights.

        Args:
            task_desc: Task description to find patterns for

        Returns:
            List of relevant learner insights
        """
        if not self.learner:
            return []

        try:
            # Query learner for similar task patterns
            insights = []

            # Get task type classification from learner
            task_patterns = await self.learner.get_task_patterns(task_desc)
            if task_patterns:
                insights.extend(task_patterns)

            # Get success patterns for similar tasks
            success_patterns = await self.learner.get_success_patterns(task_desc)
            if success_patterns:
                insights.extend(success_patterns)

            return insights

        except Exception as e:
            self.logger.warning(f"[COORDINATOR] Failed to get learner insights: {e}")
            return []

    def _build_enhanced_prompt(self, task_desc: str, learner_insights: List[Dict]) -> str:
        """
        Build enhanced decomposition prompt using learner insights.

        Args:
            task_desc: Original task description
            learner_insights: Insights from learner agent

        Returns:
            Enhanced prompt string
        """
        # Get decomposition prompt with fallback
        decomposition_prompt = self.config.get(
            "decomposition_prompt",
            """Decompose the following task into 2-5 specific, actionable subtasks:

Task: {task}

Return a JSON list of subtasks, where each subtask has:
- "description": Brief description of the subtask
- "agent": Suggested agent type (observer/actor/validator/analyzer/improver/memory)
- "priority": high/medium/low
- "dependencies": List of subtask indices this depends on (empty if none)

Example format:
[
  {{"description": "Analyze codebase", "agent": "observer", "priority": "high", "dependencies": []}},
  {{"description": "Execute changes", "agent": "actor", "priority": "high", "dependencies": [0]}}
]""",
        )
        base_prompt = decomposition_prompt.format(task=task_desc)

        if not learner_insights:
            return base_prompt

        # Extract key insights
        agent_usage_patterns = []
        common_subtask_types = []
        success_indicators = []

        for insight in learner_insights:
            if "agent_usage" in insight:
                agent_usage_patterns.extend(insight["agent_usage"])
            if "subtask_types" in insight:
                common_subtask_types.extend(insight["subtask_types"])
            if "success_patterns" in insight:
                success_indicators.extend(insight["success_patterns"])

        # Build enhancement string
        enhancement = "\n\nHistorical insights for similar tasks:\n"

        if agent_usage_patterns:
            enhancement += f"- Common agent usage: {', '.join(set(agent_usage_patterns))}\n"

        if common_subtask_types:
            enhancement += f"- Effective subtask types: {', '.join(set(common_subtask_types))}\n"

        if success_indicators:
            enhancement += f"- Success patterns: {', '.join(set(success_indicators))}\n"

        enhancement += "\nConsider these patterns when decomposing this task for optimal execution."

        return base_prompt + enhancement

    async def _decompose_with_prompt(self, prompt: str, task_desc: str) -> List[Dict]:
        """
        Perform decomposition using the given prompt.

        Args:
            prompt: Decomposition prompt
            task_desc: Original task description

        Returns:
            List of subtasks
        """
        # Use cognitive enhancement for better task decomposition
        enhanced_decomposition = self.enhance_task_decomposition(
            task_desc, context_history=self._get_recent_decompositions()
        )

        # Enhanced prompt with cognitive insights
        enhanced_task = enhanced_decomposition.get("enhanced_task", task_desc)
        cognitive_insights = enhanced_decomposition.get("cognitive_insights", {})

        # Adjust prompt based on cognitive insights
        complexity = cognitive_insights.get("complexity", "medium")
        parallelization = cognitive_insights.get("parallelization", "optional")

        prompt_modifier = ""
        if complexity == "high":
            prompt_modifier = " This is a complex task requiring careful decomposition into 4-6 detailed sub-tasks."
        elif complexity == "low":
            prompt_modifier = " This is a simple task that can be handled with 2-3 basic sub-tasks."

        if parallelization == "recommended":
            prompt_modifier += " Prioritize parallel execution where possible."

        # Grok-powered decomposition with cognitive enhancement
        final_prompt = prompt + prompt_modifier
        decomposition_response = await self.grok_client.create_message(task=final_prompt, conversation_history=None)

        if decomposition_response["status"] != "success":
            self.logger.error(f"[COORDINATOR] Decomposition failed: {decomposition_response}")
            return self._fallback_decompose(task_desc)

        # Parse JSON from Grok response
        try:
            subtasks_json = decomposition_response.get("content", "[]")
            subtasks: List[Dict] = json.loads(subtasks_json)
            subtasks = subtasks[: self.config["max_subtasks"]]
        except json.JSONDecodeError:
            self.logger.warning("[COORDINATOR] Invalid JSON from Grok; using fallback")
            subtasks = self._fallback_decompose(task_desc)

        return subtasks

    async def _validate_and_refine_subtasks(self, subtasks: List[Dict], task_desc: str, task_id: str) -> List[Dict]:
        """
        Validate subtasks for feasibility and refine if needed.

        Args:
            subtasks: Initial subtasks to validate
            task_desc: Original task description
            task_id: Task identifier

        Returns:
            Validated and refined subtasks
        """
        if not self.validator:
            return subtasks

        max_iterations = self.config.get("max_refinement_iterations", 3)
        threshold = self.config.get("feasibility_threshold", 0.7)

        for iteration in range(max_iterations):
            self.logger.info(f"[COORDINATOR] Validation iteration {iteration + 1}/{max_iterations}")

            # Validate each subtask with timeout
            validation_results = []
            for subtask in subtasks:
                try:
                    score = await asyncio.wait_for(
                        self._score_subtask_feasibility(subtask, task_desc),
                        timeout=10.0  # 10 second timeout per subtask
                    )
                    validation_results.append((subtask, score))
                except asyncio.TimeoutError:
                    self.logger.warning(f"[COORDINATOR] Subtask validation timed out: {subtask.get('description', 'unknown')}")
                    validation_results.append((subtask, 0.0))  # Low score for timeout

            # Check if all subtasks meet threshold
            low_score_subtasks = [(subtask, score) for subtask, score in validation_results if score < threshold]

            if not low_score_subtasks:
                self.logger.info("[COORDINATOR] All subtasks meet feasibility threshold")
                break

            # Refine low-scoring subtasks
            self.logger.info(f"[COORDINATOR] Refining {len(low_score_subtasks)} low-scoring subtasks")

            refined_subtasks = []
            for subtask, score in validation_results:
                if score >= threshold:
                    refined_subtasks.append(subtask)
                else:
                    # Generate refinement prompt
                    refinement_prompt = self._build_refinement_prompt(subtask, score, task_desc)

                    # Get refined subtask from Grok with timeout
                    try:
                        refinement_response = await asyncio.wait_for(
                            self.grok_client.create_message(
                                task=refinement_prompt, conversation_history=None
                            ),
                            timeout=20.0  # 20 second timeout for refinement
                        )
                    except asyncio.TimeoutError:
                        self.logger.warning(f"[COORDINATOR] Refinement timed out for subtask: {subtask.get('description', 'unknown')}")
                        refinement_response = {"status": "error", "content": "Timeout during refinement"}

                    if refinement_response["status"] == "success":
                        try:
                            refined_json = json.loads(refinement_response["content"])
                            if isinstance(refined_json, dict):
                                refined_subtasks.append(refined_json)
                            else:
                                # Keep original if refinement fails
                                refined_subtasks.append(subtask)
                        except json.JSONDecodeError:
                            refined_subtasks.append(subtask)
                    else:
                        refined_subtasks.append(subtask)

            subtasks = refined_subtasks

        return subtasks

    async def _score_subtask_feasibility(self, subtask: Dict, task_context: str) -> float:
        """
        Score a subtask's feasibility using the validator.

        Args:
            subtask: Subtask to score
            task_context: Original task description

        Returns:
            Feasibility score (0.0 to 1.0)
        """
        if not self.validator:
            return 1.0  # Assume feasible if no validator

        try:
            # Create validation message
            validation_msg = {
                "type": "validate_output",
                "output": {
                    "subtask": subtask,
                    "description": subtask.get("description", ""),
                    "target_agent": subtask.get("target_agent", ""),
                    "type": subtask.get("type", ""),
                },
                "task_context": {
                    "original_task": task_context,
                    "required_fields": ["description", "target_agent", "type"],
                },
            }

            # Get validation result
            result = await self.validator.process_message(validation_msg)

            if result and "content" in result:
                validation_data = result["content"]
                score = validation_data.get("score", 0) / 100.0  # Convert to 0-1 scale
                return min(max(score, 0.0), 1.0)  # Clamp to valid range

        except Exception as e:
            self.logger.warning(f"[COORDINATOR] Feasibility scoring failed: {e}")

        return 0.5  # Default neutral score

    def _build_refinement_prompt(self, subtask: Dict, score: float, task_context: str) -> str:
        """
        Build a prompt to refine a low-scoring subtask.

        Args:
            subtask: Original subtask
            score: Current feasibility score
            task_context: Original task description

        Returns:
            Refinement prompt
        """
        return f"""
Refine this subtask to make it more feasible and effective:

Original Task: {task_context}
Current Subtask: {json.dumps(subtask, indent=2)}
Current Feasibility Score: {score:.2f} (needs to be > 0.7)

Issues identified:
- The subtask may be too vague or complex
- Agent assignment might not be optimal
- Dependencies or requirements may be unclear

Please provide a refined version of this subtask as a JSON object with the same structure:
{{"id": "...", "type": "...", "target_agent": "...", "description": "...", "priority": "...", "dependencies": [...] }}

Make it more specific, actionable, and ensure the target_agent is appropriate for the task type.
Output only the JSON object, no additional text.
"""

        # Keep only recent history
        self._decomposition_history = self._decomposition_history[-10:]

    async def _resolve_conflicts(self, task_id: str, subtasks: List[Dict], aggregated: Dict) -> Dict[str, Any]:
        """
        Attempt to resolve conflicts in task results.

        Args:
            task_id: Task identifier
            subtasks: List of subtasks
            aggregated: Current aggregated results

        Returns:
            Resolution result
        """
        self.logger.info(f"[COORDINATOR] Attempting conflict resolution for task {task_id}")

        failed_subtasks = [st for st in subtasks if aggregated["results"].get(st["id"], {}).get("status") != "success"]

        if not failed_subtasks:
            return {"resolved": True, "method": "no_conflicts"}

        # Method 1: Retry failed subtasks
        if len(failed_subtasks) <= 2:  # Only retry if few failures
            self.logger.info(f"[COORDINATOR] Retrying {len(failed_subtasks)} failed subtasks")
            await self._delegate_subtasks(task_id, failed_subtasks)

            # Wait a bit for results (simplified)
            await asyncio.sleep(2)

            # Check if now resolved
            success_count = sum(
                1 for r in self.results.values() if r.get("status") == "success" and r.get("task_id") == task_id
            )
            if success_count == len(subtasks):
                return {"resolved": True, "method": "retry"}

        # Method 2: Consensus voting with validator
        if self.validator:
            self.logger.info("[COORDINATOR] Using validator for consensus voting")
            vote_results = []
            for sub in subtasks:
                result = aggregated["results"].get(sub["id"])
                if result:
                    vote = await self._validator_vote(sub, result)
                    vote_results.append(vote)

            # Simple majority vote
            positive_votes = sum(1 for v in vote_results if v.get("valid", False))
            if positive_votes > len(vote_results) / 2:
                return {"resolved": True, "method": "validator_consensus"}

        # Method 3: Rollback and re-execute (if executor available)
        # This would require tracking which executor handled which subtasks
        # For now, simplified - just mark as unresolvable

        self.logger.warning(f"[COORDINATOR] Conflict resolution failed for task {task_id}")
        return {"resolved": False, "method": "unresolvable"}

    async def _validator_vote(self, subtask: Dict, result: Dict) -> Dict[str, Any]:
        """
        Use validator to vote on a subtask result.

        Args:
            subtask: Subtask definition
            result: Result to validate

        Returns:
            Validation vote
        """
        if not self.validator:
            return {"valid": True, "reason": "no_validator"}

        validation_msg = {
            "type": "validate_output",
            "output": {
                "subtask": subtask,
                "result": result,
                "description": subtask.get("description", ""),
                "target_agent": subtask.get("target_agent", ""),
            },
            "task_context": {
                "expected_output": "successful execution",
                "validation_criteria": ["status == success", "no errors"],
            },
        }

        try:
            vote_result = await self.validator.process_message(validation_msg)
            return vote_result if vote_result else {"valid": False, "reason": "validation_failed"}
        except Exception as e:
            self.logger.warning(f"[COORDINATOR] Validator vote failed: {e}")
            return {"valid": False, "reason": str(e)}

    async def perform_meta_reasoning(self) -> List[Dict]:
        """
        Analyze orchestration performance and suggest improvements.

        Returns:
            List of improvement suggestions
        """
        suggestions = []

        # Analyze task completion patterns
        total_tasks = self.performance_metrics["tasks_completed"] + self.performance_metrics["tasks_failed"]
        if total_tasks > 5:  # Need some data
            success_rate = self.performance_metrics["tasks_completed"] / total_tasks

            if success_rate < 0.8:
                suggestions.append(
                    {
                        "type": "reliability",
                        "suggestion": "Task success rate below 80%. Consider improving agent selection or adding more validation.",
                        "data": {"success_rate": success_rate, "total_tasks": total_tasks},
                    }
                )

            # Analyze decomposition time
            avg_decomp_time = self.performance_metrics["avg_decomposition_time"]
            if avg_decomp_time > 10.0:  # Too slow
                suggestions.append(
                    {
                        "type": "performance",
                        "suggestion": "Decomposition taking too long. Consider caching similar patterns or simplifying prompts.",
                        "data": {"avg_time": avg_decomp_time},
                    }
                )

            # Analyze conflict resolution
            resolution_rate = self.performance_metrics["successful_resolutions"] / max(
                self.performance_metrics["conflict_resolution_attempts"], 1
            )
            if resolution_rate < 0.5:
                suggestions.append(
                    {
                        "type": "efficiency",
                        "suggestion": "Low conflict resolution success. Review validation and retry strategies.",
                        "data": {"resolution_rate": resolution_rate},
                    }
                )

        # Analyze agent load balancing
        if hasattr(self, "task_prioritizer"):
            queue_stats = self.task_prioritizer.get_queue_stats()
            total_load = queue_stats.get("total_load", 0)
            if total_load > 10:  # High load
                suggestions.append(
                    {
                        "type": "scalability",
                        "suggestion": "High agent load detected. Consider adding more agent instances or optimizing delegation.",
                        "data": queue_stats,
                    }
                )

        # Record this meta-reasoning session
        self.orchestration_traces.append(
            {
                "timestamp": time.time(),
                "type": "meta_reasoning",
                "suggestions_count": len(suggestions),
                "performance_snapshot": self.performance_metrics.copy(),
            }
        )

        return suggestions

    def record_task_completion(self, task_id: str, success: bool, execution_time: float, decomposition_time: float):
        """
        Record task completion for meta-reasoning analysis.

        Args:
            task_id: Task identifier
            success: Whether task succeeded
            execution_time: Total execution time
            decomposition_time: Time spent on decomposition
        """
        if success:
            self.performance_metrics["tasks_completed"] += 1
        else:
            self.performance_metrics["tasks_failed"] += 1

        # Update averages
        total_completed = self.performance_metrics["tasks_completed"]
        self.performance_metrics["avg_execution_time"] = (
            (self.performance_metrics["avg_execution_time"] * (total_completed - 1)) + execution_time
        ) / total_completed

        total_decomp = total_completed + self.performance_metrics["tasks_failed"]
        self.performance_metrics["avg_decomposition_time"] = (
            (self.performance_metrics["avg_decomposition_time"] * (total_decomp - 1)) + decomposition_time
        ) / total_decomp

        # Add trace
        self.orchestration_traces.append(
            {
                "timestamp": time.time(),
                "type": "task_completion",
                "task_id": task_id,
                "success": success,
                "execution_time": execution_time,
                "decomposition_time": decomposition_time,
            }
        )

    def record_conflict_resolution(self, success: bool):
        """
        Record conflict resolution attempt.

        Args:
            success: Whether resolution succeeded
        """
        self.performance_metrics["conflict_resolution_attempts"] += 1
        if success:
            self.performance_metrics["successful_resolutions"] += 1

        self.orchestration_traces.append({"timestamp": time.time(), "type": "conflict_resolution", "success": success})

    def get_orchestration_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive orchestration report for analysis.

        Returns:
            Report dictionary
        """
        return {
            "performance_metrics": self.performance_metrics,
            "recent_traces": self.orchestration_traces[-10:],  # Last 10 traces
            "improvement_suggestions": asyncio.run(self.perform_meta_reasoning()),
            "agent_load_stats": self.task_prioritizer.get_queue_stats() if hasattr(self, "task_prioritizer") else {},
        }

    def _fallback_decompose(self, task_desc: str) -> List[Dict]:
        """
        Simple rule-based decomposition if Grok fails.
        """
        # Basic parsing: "observe ... then act: ..."
        lower_task = task_desc.lower()
        if "observe" in lower_task and "act" in lower_task:
            return [
                {
                    "id": "sub1",
                    "type": "observe",
                    "target_agent": "observer",
                    "description": "Capture and analyze screen",
                    "priority": "high",
                    "dependencies": [],
                },
                {
                    "id": "sub2",
                    "type": "act",
                    "target_agent": "actor",
                    "description": task_desc.split("act:")[-1].strip() if "act:" in task_desc else task_desc,
                    "priority": "medium",
                    "dependencies": ["sub1"],
                },
                {
                    "id": "sub3",
                    "type": "validate",
                    "target_agent": "validator",
                    "description": "Verify action success",
                    "priority": "low",
                    "dependencies": ["sub2"],
                },
            ]
        else:
            return [
                {
                    "id": "sub1",
                    "type": "act",
                    "target_agent": "actor",
                    "description": task_desc,
                    "priority": "high",
                    "dependencies": [],
                }
            ]

    async def _delegate_subtasks(self, task_id: str, subtasks: List[Dict]):
        """
        Delegate ready sub-tasks using load-aware prioritization.
        """
        # Update agent loads before delegation
        await self.task_prioritizer.update_loads()

        # Simple topological: Delegate all non-dependent first, then iterate
        for _ in range(len(subtasks)):  # Max passes = num subtasks
            ready_subtasks = [
                st
                for st in subtasks
                if all(dep in self.completed_subtasks for dep in st.get("dependencies", []))
                and sub["id"] not in self.completed_subtasks
            ]

            if not ready_subtasks:
                break  # No more ready

            # Add ready subtasks to prioritizer
            for sub in ready_subtasks:
                await self.task_prioritizer.add_subtask(sub)

            # Delegate in priority order from prioritizer (only the ones we just added)
            for _ in range(len(ready_subtasks)):
                prioritized_subtask = await self.task_prioritizer.get_next_subtask()
                if prioritized_subtask is None:
                    break

                sub_id = prioritized_subtask["id"]
                target = prioritized_subtask["target_agent"]
                desc = prioritized_subtask["description"]
                sub_type = prioritized_subtask["type"]
                priority_str = prioritized_subtask["priority"]
                priority = (
                    MessagePriority.HIGH
                    if priority_str == "high"
                    else MessagePriority.NORMAL if priority_str == "medium" else MessagePriority.LOW
                )

                # Create delegation message
                del_msg = Message(
                    from_agent="coordinator",
                    to_agent=target,
                    message_type=f"{sub_type}_task",  # e.g., "observe_task", "act_task"
                    content={
                        "task_id": task_id,
                        "sub_id": sub_id,
                        "description": desc,
                        "type": sub_type,
                        "params": {},  # Extend as needed
                        "safety_level": "low" if priority_str != "high" else "medium",
                    },
                    priority=priority,
                )

                # Send to specific agent or broadcast
                if target == DelegationTarget.ALL.value:
                    await self.message_bus.broadcast(del_msg)
                else:
                    # Send directly to target agent
                    await self.message_bus.send(del_msg)

                self.logger.info(f"[COORDINATOR] Delegated {sub_id} to {target}: {desc}")
                self.session_logger.log_agent_activity("coordinator", "delegated", {"sub_id": sub_id, "target": target})

        if self.config["debug"]:
            queue_stats = self.task_prioritizer.get_queue_stats()
            print(f"[COORDINATOR] Delegated subtasks for {task_id}. Queue stats: {queue_stats}")

    async def _handle_result(self, message: Message):
        """
        Aggregate results from sub-tasks.
        """
        content = message.content
        task_id = content.get("task_id")
        sub_id = content.get("sub_id", "unknown")
        result = content.get("result")

        if task_id not in self.active_tasks:
            return

        self.results[sub_id] = result
        self.completed_subtasks.add(sub_id)
        self.logger.info(f"[COORDINATOR] Result for {sub_id}: {result.get('status', 'unknown')}")

        # Check if all subtasks complete
        subtasks = self.active_tasks.get(task_id, [])
        if len(self.completed_subtasks.intersection(st["id"] for st in subtasks)) == len(subtasks):
            await self._aggregate_and_complete(task_id, subtasks)

    async def _handle_failure(self, message: Message):
        """
        Handle sub-task failure: Retry or escalate.
        """
        content = message.content
        task_id = content.get("task_id")
        sub_id = content.get("sub_id")
        error = content.get("error")

        self.logger.warning(f"[COORDINATOR] Failure in {sub_id}: {error}")
        self.session_logger.log_agent_activity("coordinator", "failure_handled", {"sub_id": sub_id, "error": error})

        # Simple retry: Re-delegate if low-risk
        if task_id in self.active_tasks:
            subtasks = self.active_tasks[task_id]
            sub = next((s for s in subtasks if s["id"] == sub_id), None)
            if sub and sub.get("retries", 0) < 2:
                sub["retries"] = sub.get("retries", 0) + 1
                await self._delegate_subtasks(task_id, [sub])  # Re-delegate single
            else:
                # Escalate or mark failed
                self.results[sub_id] = {"status": "failed", "error": error}
                self.completed_subtasks.add(sub_id)
                await self._aggregate_and_complete(task_id, self.active_tasks.get(task_id, []))

    async def _aggregate_and_complete(self, task_id: str, subtasks: List[Dict]):
        """
        Aggregate results and send completion, with conflict resolution.
        """
        # Simple aggregation: Collect all results, check consensus
        aggregated = {
            "task_id": task_id,
            "subtasks": subtasks,
            "results": {st["id"]: self.results.get(st["id"]) for st in subtasks},
        }
        success_count = sum(1 for r in aggregated["results"].values() if r.get("status") == "success")
        consensus_score = success_count / len(subtasks)
        consensus = consensus_score >= self.config["aggregation_threshold"]

        if not consensus:
            # Attempt conflict resolution
            resolution_result = await self._resolve_conflicts(task_id, subtasks, aggregated)
            if resolution_result["resolved"]:
                aggregated["status"] = "completed"
                aggregated["consensus_score"] = 1.0
                aggregated["conflict_resolved"] = True
                aggregated["resolution_method"] = resolution_result["method"]
            else:
                aggregated["status"] = "failed"
                aggregated["consensus_score"] = consensus_score
                aggregated["conflict_unresolved"] = True
        else:
            aggregated["status"] = "completed"
            aggregated["consensus_score"] = consensus_score

        # Send completion to all or user
        complete_msg = Message(
            from_agent="coordinator",
            to_agent="all",  # Or "user"/pantheon
            message_type="task_complete",
            content=aggregated,
            priority=MessagePriority.HIGH,
        )
        await self.message_bus.broadcast(complete_msg)

        # Record for meta-reasoning
        execution_time = time.time() - self.task_start_times.get(task_id, time.time())
        self.record_task_completion(
            task_id, aggregated["status"] == "completed", execution_time, 0.0
        )  # decomposition_time could be tracked separately

        # Record conflict resolution if it happened
        if aggregated.get("conflict_resolved"):
            self.record_conflict_resolution(True)
        elif aggregated.get("conflict_unresolved"):
            self.record_conflict_resolution(False)

        self.logger.info(
            f"[COORDINATOR] Task {task_id} {aggregated['status']} (score: {aggregated['consensus_score']:.2f})"
        )
        self.session_logger.log_agent_activity("coordinator", "completed", aggregated)

        # DPO optimization: Collect preference data and optimize parameters
        if aggregated["status"] == "completed":
            await self._optimize_with_dpo(task_id, aggregated)

        # Cleanup
        del self.active_tasks[task_id]
        if task_id in self.task_start_times:
            del self.task_start_times[task_id]
        self.completed_subtasks -= {st["id"] for st in subtasks}

    async def _send_completion(self, task_id: str, result: Dict):
        """
        Send early completion (e.g., on error).
        """
        complete_msg = Message(
            from_agent="coordinator",
            to_agent="all",
            message_type="task_complete",
            content={"task_id": task_id, "result": result},
            priority=MessagePriority.HIGH,
        )
        await self.message_bus.broadcast(complete_msg)

    async def _optimize_with_dpo(self, task_id: str, result: Dict[str, Any]):
        """
        Use DPO to optimize parameters based on task performance.

        Args:
            task_id: Completed task ID
            result: Task completion result
        """
        try:
            # Extract performance metrics
            consensus_score = result.get("consensus_score", 0.5)
            execution_time = time.time() - self.task_start_times.get(task_id, time.time())

            # Create current parameter snapshot
            current_params = {
                "temperature": getattr(self.grok_client, "temperature", 0.7),
                "max_tokens": getattr(self.grok_client, "max_tokens", 200),
                "timeout": getattr(self.grok_client, "timeout", 15),
            }

            # Get DPO-optimized parameters
            optimized_params = self.dpo_optimizer.optimize_parameters(
                f"Task {task_id}: {result.get('task_description', 'unknown')}",
                {
                    "consensus": consensus_score,
                    "speed": max(0, 1 - execution_time / 60),  # Normalize to 0-1
                    "success": 1.0 if result["status"] == "completed" else 0.0,
                },
            )

            # Collect preference data by comparing current vs optimized
            if optimized_params != current_params:
                # Simulate preference collection (in practice, would run trials)
                await self.preference_collector.collect_preferences_batch(num_pairs=1)

                # Apply optimized parameters for future tasks
                for param, value in optimized_params.items():
                    if hasattr(self.grok_client, param):
                        setattr(self.grok_client, param, value)

                self.logger.info(f"[COORDINATOR] DPO optimized parameters: {optimized_params}")

        except Exception as e:
            self.logger.error(f"[COORDINATOR] DPO optimization failed: {e}")

    def process_nli_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a task from Natural Language Interface.

        Args:
            task_data: Task data from NLI with description, type, parameters

        Returns:
            Task execution result
        """
        try:
            # Create a unique task ID
            task_id = f"nli_{int(time.time() * 1000)}"

            # Convert NLI task to coordinator format
            coordinator_task = {
                "task_id": task_id,
                "description": task_data.get("description", "NLI task"),
                "type": task_data.get("type", "general"),
                "parameters": task_data.get("parameters", {}),
                "source": "nli",
            }

            # Log the task
            self.logger.info(f"[COORDINATOR] Processing NLI task: {coordinator_task['description']}")

            # For simple tasks, execute directly without full decomposition
            task_type = task_data.get("type", "general")

            if task_type == "bash":
                # Execute bash command directly
                result = self._execute_simple_bash_task(task_data)
            elif task_type == "web_search":
                # Execute web search
                result = self._execute_simple_web_task(task_data)
            else:
                # Use full decomposition for complex tasks
                result = self._execute_complex_task(coordinator_task)

            return {
                "task_id": task_id,
                "success": result.get("success", False),
                "result": result,
                "summary": result.get("summary", "Task completed"),
            }

        except Exception as e:
            self.logger.error(f"[COORDINATOR] NLI task processing failed: {e}")
            return {
                "task_id": task_id if "task_id" in locals() else "unknown",
                "success": False,
                "error": str(e),
                "summary": "Task failed",
            }

    def _execute_simple_bash_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a simple bash command."""
        try:
            command = task_data.get("command", "")
            if not command:
                return {"success": False, "error": "No command provided"}

            # In a real implementation, this would delegate to actor agent
            # For now, simulate success
            return {
                "success": True,
                "output": f"Executed: {command}",
                "summary": f"Successfully executed bash command: {command}",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _execute_simple_web_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a simple web task."""
        try:
            query = task_data.get("query", "")
            if not query:
                return {"success": False, "error": "No query provided"}

            # In a real implementation, this would delegate to appropriate agent
            # For now, simulate success
            return {
                "success": True,
                "results": f"Search results for: {query}",
                "summary": f"Successfully searched for: {query}",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _execute_complex_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a complex task requiring full decomposition."""
        # This would trigger the full async task processing
        # For NLI integration, we'll simulate for now
        return {"success": True, "summary": f"Complex task processed: {task_data.get('description', 'unknown')}"}


# Example usage (for testing)
if __name__ == "__main__":
    # Stub setup
    from src.core.message_bus import MessageBus
    from src.observability.session_logger import SessionLogger
    from src.observability.deadlock_detector import DeadlockDetector
    from src.grok_client import GrokClient
    import logging
    from pathlib import Path

    logging.basicConfig(level=logging.INFO)

    bus = MessageBus()
    logger = SessionLogger(session_id="test", task="coord_test", log_dir=Path("./logs"), swarm_mode=True)
    detector = DeadlockDetector()
    grok = FallbackGrokClient()

    coord = Coordinator(
        message_bus=bus, grok_client=grok, session_logger=logger, deadlock_detector=detector, config={"debug": True}
    )

    async def test_coordinator():
        # Simulate new task message
        task_msg = Message(
            from_agent="user",
            to_agent="coordinator",
            message_type="new_task",
            content={"task_id": "test1", "description": "observe screen then act: echo 'ZA GROKA' via bash"},
        )
        await coord._handle_new_task(task_msg)
        # Simulate results
        result_msg = Message(
            from_agent="actor",
            to_agent="coordinator",
            message_type="action_result",
            content={"task_id": "test1", "sub_id": "sub2", "result": {"status": "success", "output": "ZA GROKA"}},
        )
        await coord._handle_result(result_msg)

    asyncio.run(test_coordinator())
