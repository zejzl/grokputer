"""
Distributed Cognitive Processing for Grokputer.

Enables scaling of cognitive workloads across multiple agents through
intelligent orchestration, load balancing, and collaborative reasoning.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from ..cognitive.flash_attention import CognitiveEnhancer
from ..core.message_bus import Message, MessageBus, MessagePriority
from ..memory.hierarchical_memory import HierarchicalMemoryManager
from ..memory.interfaces import MemoryConfig

logger = logging.getLogger(__name__)


class CognitiveTaskType(Enum):
    """Types of cognitive tasks that can be distributed."""

    REASONING = "reasoning"
    ANALYSIS = "analysis"
    SYNTHESIS = "synthesis"
    VALIDATION = "validation"
    OPTIMIZATION = "optimization"
    LEARNING = "learning"
    MEMORY_RETRIEVAL = "memory_retrieval"
    CONTEXT_PROCESSING = "context_processing"


class AgentCapability(Enum):
    """Cognitive capabilities that agents can possess."""

    HIGH_LEVEL_REASONING = "high_level_reasoning"
    DETAILED_ANALYSIS = "detailed_analysis"
    PATTERN_RECOGNITION = "pattern_recognition"
    MEMORY_INTEGRATION = "memory_integration"
    VALIDATION_CHECKING = "validation_checking"
    OPTIMIZATION_PLANNING = "optimization_planning"
    LEARNING_ADAPTATION = "learning_adaptation"


@dataclass
class CognitiveTask:
    """Represents a cognitive processing task."""

    task_id: str
    task_type: CognitiveTaskType
    content: Dict[str, Any]
    priority: MessagePriority = MessagePriority.NORMAL
    dependencies: List[str] = field(default_factory=list)  # Task IDs this depends on
    estimated_complexity: float = 1.0  # 0.1 to 10.0
    required_capabilities: Set[AgentCapability] = field(default_factory=set)
    timeout_seconds: float = 30.0
    created_at: float = field(default_factory=time.time)
    assigned_agent: Optional[str] = None
    status: str = "pending"  # pending, processing, completed, failed


@dataclass
class AgentProfile:
    """Profile of an agent's cognitive capabilities and current load."""

    agent_id: str
    capabilities: Set[AgentCapability]
    current_load: float = 0.0  # 0.0 to 1.0
    max_load: float = 1.0
    specialization_score: Dict[CognitiveTaskType, float] = field(default_factory=dict)
    performance_history: List[Dict[str, Any]] = field(default_factory=list)
    last_active: float = field(default_factory=time.time)

    def can_handle_task(self, task: CognitiveTask) -> float:
        """Return capability score (0.0-1.0) for handling a task."""
        if not task.required_capabilities.issubset(self.capabilities):
            return 0.0

        # Calculate specialization score
        task_specialization = self.specialization_score.get(task.task_type, 0.5)

        # Consider current load (prefer less loaded agents)
        load_factor = 1.0 - self.current_load

        # Consider capability match
        if task.required_capabilities:
            capability_match = len(task.required_capabilities.intersection(self.capabilities)) / len(
                task.required_capabilities
            )
        else:
            # If no specific capabilities required, assume full match
            capability_match = 1.0

        return task_specialization * 0.4 + load_factor * 0.4 + capability_match * 0.2

    def estimate_processing_time(self, task: CognitiveTask) -> float:
        """Estimate time to process a task."""
        base_time = task.estimated_complexity * 2.0  # Base 2 seconds per complexity unit
        specialization_factor = 1.0 / max(self.specialization_score.get(task.task_type, 0.5), 0.1)
        load_penalty = 1.0 + self.current_load

        return base_time * specialization_factor * load_penalty


class DistributedCognitiveOrchestrator:
    """
    Orchestrates cognitive processing across multiple agents.

    Distributes complex cognitive tasks, manages load balancing,
    and coordinates collaborative reasoning processes.
    """

    def __init__(
        self,
        message_bus: MessageBus,
        cognitive_enhancer: Optional[CognitiveEnhancer] = None,
        memory_config: Optional[MemoryConfig] = None,
    ):
        self.message_bus = message_bus
        self.cognitive_enhancer = cognitive_enhancer or CognitiveEnhancer()
        self.agent_id = "cognitive_orchestrator"

        # Initialize hierarchical memory
        self.memory_config = memory_config or MemoryConfig(backend="hierarchical")
        from ..memory.managers.memory_factory import create_memory_backend

        self.memory_backend = create_memory_backend(self.memory_config)

        # Agent registry
        self.agent_profiles: Dict[str, AgentProfile] = {}
        self.active_tasks: Dict[str, CognitiveTask] = {}
        self.task_dependencies: Dict[str, Set[str]] = {}  # task_id -> dependent task_ids
        self.consensus_tasks: Dict[str, Dict[str, Any]] = {}  # consensus_id -> metadata

        # Performance tracking
        self.task_history: List[Dict[str, Any]] = []
        self.orchestration_stats = {
            "total_tasks_processed": 0,
            "average_completion_time": 0.0,
            "load_balancing_efficiency": 0.0,
            "agent_utilization": {},
        }

        # Register orchestrator as an agent
        self.message_bus.register_agent(self.agent_id)

        # Start message processing
        self._processing_task = None

    async def start_processing(self):
        """Start processing messages from the message bus."""
        if self._processing_task is not None:
            return

        self._processing_task = asyncio.create_task(self._process_messages())
        logger.info("Started cognitive orchestrator message processing")

    async def stop_processing(self):
        """Stop processing messages."""
        if self._processing_task is not None:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass
            self._processing_task = None
            logger.info("Stopped cognitive orchestrator message processing")

    async def _process_messages(self):
        """Process messages from the message bus."""
        try:
            while True:
                message = await self.message_bus.receive(self.agent_id, timeout=1.0)
                if message:
                    await self._handle_message(message)
        except asyncio.CancelledError:
            logger.info("Message processing cancelled")
            raise
        except Exception as e:
            logger.error(f"Error processing messages: {e}")

    async def _handle_message(self, message: Message):
        """Handle incoming messages."""
        if message.message_type == "cognitive_task_result":
            await self._handle_task_result(message)
        elif message.message_type == "agent_status_update":
            await self._handle_agent_status(message)
        elif message.message_type == "consensus_response":
            # Handle consensus responses
            consensus_id = message.content.get("consensus_id")
            if consensus_id:
                await self._handle_consensus_response(consensus_id, message.from_agent, message.content.get("response"))
        else:
            logger.debug(f"Ignored message type: {message.message_type}")

    async def register_agent(
        self,
        agent_id: str,
        capabilities: Set[AgentCapability],
        specialization_scores: Optional[Dict[CognitiveTaskType, float]] = None,
    ) -> None:
        """Register an agent with the cognitive orchestrator."""
        profile = AgentProfile(
            agent_id=agent_id, capabilities=capabilities, specialization_score=specialization_scores or {}
        )

        self.agent_profiles[agent_id] = profile
        logger.info(f"Registered cognitive agent: {agent_id} with capabilities: {capabilities}")

    async def submit_cognitive_task(
        self,
        task_type: CognitiveTaskType,
        content: Dict[str, Any],
        priority: MessagePriority = MessagePriority.NORMAL,
        dependencies: Optional[List[str]] = None,
        required_capabilities: Optional[Set[AgentCapability]] = None,
        estimated_complexity: float = 1.0,
        timeout_seconds: float = 30.0,
    ) -> str:
        """
        Submit a cognitive task for distributed processing.

        Returns task ID for tracking.
        """
        task_id = f"cognitive_{int(time.time() * 1000)}_{len(self.active_tasks)}"

        task = CognitiveTask(
            task_id=task_id,
            task_type=task_type,
            content=content,
            priority=priority,
            dependencies=dependencies or [],
            estimated_complexity=estimated_complexity,
            required_capabilities=required_capabilities or set(),
            timeout_seconds=timeout_seconds,
        )

        self.active_tasks[task_id] = task

        # Track dependencies
        for dep_id in task.dependencies:
            if dep_id not in self.task_dependencies:
                self.task_dependencies[dep_id] = set()
            self.task_dependencies[dep_id].add(task_id)

        # Try to assign immediately (only if no dependencies or dependencies are satisfied)
        if not task.dependencies or await self._check_dependencies_satisfied(task):
            await self._assign_task(task)

        logger.info(f"Submitted cognitive task: {task_id} ({task_type.value})")
        return task_id

    async def _assign_task(self, task: CognitiveTask) -> bool:
        """Assign a task to the best available agent."""
        if task.status == "completed" or task.status == "failed":
            return False

        # Check if dependencies are satisfied
        if not await self._check_dependencies_satisfied(task):
            return False

        # Find best agent
        best_agent, score = self._find_best_agent(task)

        if best_agent is None:
            logger.warning(f"No suitable agent found for task {task.task_id}")
            return False

        # Assign task
        task.assigned_agent = best_agent
        task.status = "processing"

        # Update agent load
        agent_profile = self.agent_profiles[best_agent]
        agent_profile.current_load = min(1.0, agent_profile.current_load + task.estimated_complexity * 0.1)

        # Retrieve relevant context from memory
        context = self.retrieve_task_context(best_agent, task.task_type, query=str(task.content), top_k=3)

        # Send task to agent with context
        message = Message(
            from_agent=self.agent_id,
            to_agent=best_agent,
            message_type="cognitive_task",
            content={
                "task_id": task.task_id,
                "task_type": task.task_type.value,
                "content": task.content,
                "estimated_complexity": task.estimated_complexity,
                "timeout_seconds": task.timeout_seconds,
                "memory_context": context,  # Include relevant past experiences
            },
            priority=task.priority,
        )

        await self.message_bus.send(message)
        logger.debug(f"Assigned task {task.task_id} to agent {best_agent} (score: {score:.3f})")

        return True

    def _find_best_agent(self, task: CognitiveTask) -> Tuple[Optional[str], float]:
        """Find the best agent for a task based on capabilities and load."""
        best_agent = None
        best_score = 0.0

        for agent_id, profile in self.agent_profiles.items():
            if profile.current_load >= profile.max_load:
                continue  # Agent is at capacity

            capability_score = profile.can_handle_task(task)
            if capability_score > best_score:
                best_score = capability_score
                best_agent = agent_id

        return best_agent, best_score

    async def _check_dependencies_satisfied(self, task: CognitiveTask) -> bool:
        """Check if all task dependencies are completed."""
        for dep_id in task.dependencies:
            if dep_id in self.active_tasks:
                dep_task = self.active_tasks[dep_id]
                if dep_task.status != "completed":
                    return False
        return True

    async def _handle_task_result(self, message: Message) -> None:
        """Handle completion of a cognitive task."""
        content = message.content
        task_id = content.get("task_id")
        result = content.get("result")
        success = content.get("success", True)

        if task_id not in self.active_tasks:
            logger.warning(f"Received result for unknown task: {task_id}")
            return

        task = self.active_tasks[task_id]
        agent_id = message.from_agent

        # Update task status
        task.status = "completed" if success else "failed"

        # Update agent load and performance
        if agent_id in self.agent_profiles:
            profile = self.agent_profiles[agent_id]
            profile.current_load = max(0.0, profile.current_load - task.estimated_complexity * 0.1)

            # Track performance
            completion_time = time.time() - task.created_at
            performance_record = {
                "task_id": task_id,
                "task_type": task.task_type.value,
                "completion_time": completion_time,
                "success": success,
                "estimated_time": profile.estimate_processing_time(task),
            }
            profile.performance_history.append(performance_record)

            # Update specialization based on performance
            performance_score = 1.0 if success else 0.0
            # Adjust score based on completion time vs estimated time
            time_ratio = completion_time / (performance_record["estimated_time"] + 0.1)  # Avoid division by zero
            if time_ratio < 1.2:  # Completed faster than estimated
                performance_score = min(1.0, performance_score + 0.1)
            elif time_ratio > 2.0:  # Took much longer
                performance_score = max(0.0, performance_score - 0.2)

            self.update_agent_specialization(agent_id, task.task_type, performance_score)

        # Check if this is part of a consensus task
        task_content = task.content
        if "consensus_id" in task_content and success:
            consensus_id = task_content["consensus_id"]
            await self._handle_consensus_response(consensus_id, agent_id, result)

        # Store result in hierarchical memory for learning
        self.store_task_result(task, result, success)

        # Update orchestration stats
        self.orchestration_stats["total_tasks_processed"] += 1

        # Trigger dependent tasks
        if task_id in self.task_dependencies:
            for dependent_id in self.task_dependencies[task_id]:
                if dependent_id in self.active_tasks:
                    await self._assign_task(self.active_tasks[dependent_id])

        # Clean up completed task
        del self.active_tasks[task_id]

        logger.info(f"Task {task_id} completed by {agent_id} (success: {success})")

    async def _handle_agent_status(self, message: Message) -> None:
        """Handle agent status updates."""
        content = message.content
        agent_id = message.from_agent

        if agent_id in self.agent_profiles:
            profile = self.agent_profiles[agent_id]
            profile.last_active = time.time()

            # Update load if provided
            if "current_load" in content:
                profile.current_load = content["current_load"]

    async def get_orchestration_status(self) -> Dict[str, Any]:
        """Get current orchestration status and statistics."""
        active_tasks_count = len([t for t in self.active_tasks.values() if t.status == "processing"])
        pending_tasks_count = len([t for t in self.active_tasks.values() if t.status == "pending"])

        # Calculate load balancing efficiency
        total_capacity = sum(p.max_load for p in self.agent_profiles.values())
        total_load = sum(p.current_load for p in self.agent_profiles.values())
        load_efficiency = total_load / total_capacity if total_capacity > 0 else 0.0

        return {
            "active_agents": len(self.agent_profiles),
            "active_tasks": active_tasks_count,
            "pending_tasks": pending_tasks_count,
            "total_tasks_processed": self.orchestration_stats["total_tasks_processed"],
            "load_efficiency": load_efficiency,
            "agent_status": {
                agent_id: {"load": profile.current_load, "capabilities": [cap.value for cap in profile.capabilities]}
                for agent_id, profile in self.agent_profiles.items()
            },
        }

    def get_memory_stats(self) -> Dict[str, Any]:
        """Get hierarchical memory statistics."""
        try:
            if hasattr(self.memory_backend, "get_hierarchical_stats"):
                return self.memory_backend.get_hierarchical_stats()
            else:
                return self.memory_backend.consolidate("cognitive_orchestrator")
        except Exception as e:
            logger.error(f"Failed to get memory stats: {e}")
            return {"error": str(e)}

    async def create_cognitive_pipeline(self, pipeline_name: str, task_sequence: List[Dict[str, Any]]) -> str:
        """
        Create a cognitive processing pipeline.

        Args:
            pipeline_name: Name for the pipeline
            task_sequence: List of task definitions with dependencies

        Returns:
            Pipeline ID
        """
        pipeline_id = f"pipeline_{int(time.time() * 1000)}"
        submitted_tasks = []

        # First pass: submit all tasks without dependencies to get task IDs
        for i, task_def in enumerate(task_sequence):
            task_id = await self.submit_cognitive_task(
                task_type=task_def["type"],
                content=task_def["content"],
                dependencies=[],  # No dependencies initially
                required_capabilities=task_def.get("capabilities", set()),
                estimated_complexity=task_def.get("complexity", 1.0),
            )
            submitted_tasks.append(task_id)

        # Second pass: update tasks with proper dependencies
        for i, (task_def, task_id) in enumerate(zip(task_sequence, submitted_tasks)):
            dep_indices = task_def.get("dependencies", [])
            if dep_indices:
                # Convert dependency indices to task IDs
                actual_deps = [submitted_tasks[int(idx)] for idx in dep_indices if int(idx) < len(submitted_tasks)]
                if actual_deps:
                    # Update the task's dependencies
                    if task_id in self.active_tasks:
                        task = self.active_tasks[task_id]
                        task.dependencies = actual_deps
                        # If dependencies are not satisfied, set status back to pending
                        if not await self._check_dependencies_satisfied(task):
                            task.status = "pending"
                            # Remove from agent load since it's no longer processing
                            if task.assigned_agent and task.assigned_agent in self.agent_profiles:
                                profile = self.agent_profiles[task.assigned_agent]
                                profile.current_load = max(0.0, profile.current_load - task.estimated_complexity * 0.1)
                            task.assigned_agent = None

        logger.info(f"Created cognitive pipeline: {pipeline_name} with {len(task_sequence)} tasks")
        return pipeline_id

    async def create_consensus_task(
        self,
        task_type: CognitiveTaskType,
        content: Dict[str, Any],
        num_agents: int = 3,
        consensus_threshold: float = 0.7,
        priority: MessagePriority = MessagePriority.NORMAL,
    ) -> str:
        """
        Create a consensus-based cognitive task where multiple agents work together.

        Args:
            task_type: Type of cognitive task
            content: Task content
            num_agents: Number of agents to involve (3-5 recommended)
            consensus_threshold: Agreement threshold (0.0-1.0)
            priority: Task priority

        Returns:
            Consensus task ID
        """
        consensus_id = f"consensus_{int(time.time() * 1000)}"

        # Create individual agent tasks
        agent_tasks = []
        for i in range(num_agents):
            task_id = await self.submit_cognitive_task(
                task_type=task_type,
                content={**content, "consensus_id": consensus_id, "agent_index": i, "total_agents": num_agents},
                priority=priority,
                estimated_complexity=1.0,
            )
            agent_tasks.append(task_id)

        # Store consensus metadata
        self.consensus_tasks[consensus_id] = {
            "agent_tasks": agent_tasks,
            "responses": {},
            "threshold": consensus_threshold,
            "status": "waiting",
            "created_at": time.time(),
        }

        logger.info(f"Created consensus task {consensus_id} with {num_agents} agents")
        return consensus_id

    async def _handle_consensus_response(self, consensus_id: str, agent_id: str, response: Any) -> None:
        """Handle a response from an agent in a consensus task."""
        if consensus_id not in self.consensus_tasks:
            return

        consensus_data = self.consensus_tasks[consensus_id]
        consensus_data["responses"][agent_id] = response

        # Check if all agents have responded
        if len(consensus_data["responses"]) >= len(consensus_data["agent_tasks"]):
            await self._resolve_consensus(consensus_id)

    async def _resolve_consensus(self, consensus_id: str) -> None:
        """Resolve consensus from agent responses."""
        consensus_data = self.consensus_tasks[consensus_id]
        responses = consensus_data["responses"]
        threshold = consensus_data["threshold"]

        if not responses:
            logger.warning(f"No responses for consensus {consensus_id}")
            return

        # Simple majority voting for now (can be enhanced)
        response_counts = {}
        for response in responses.values():
            # Convert response to comparable format
            response_key = (
                str(response)
                if not isinstance(response, (dict, list))
                else str(sorted(response.items()) if isinstance(response, dict) else response)
            )
            response_counts[response_key] = response_counts.get(response_key, 0) + 1

        total_responses = len(responses)
        consensus_reached = False
        consensus_result = None

        for response_key, count in response_counts.items():
            agreement_ratio = count / total_responses
            if agreement_ratio >= threshold:
                consensus_reached = True
                # Convert back to original format (simplified)
                consensus_result = list(responses.values())[list(response_counts.keys()).index(response_key)]
                break

        # Update consensus status
        consensus_data["status"] = "completed" if consensus_reached else "failed"
        consensus_data["result"] = consensus_result
        consensus_data["agreement_ratio"] = max(response_counts.values()) / total_responses if response_counts else 0.0

        # Notify interested parties
        await self.message_bus.send(
            Message(
                msg_type="consensus_result",
                content={
                    "consensus_id": consensus_id,
                    "consensus_reached": consensus_reached,
                    "result": consensus_result,
                    "agreement_ratio": consensus_data["agreement_ratio"],
                    "total_responses": total_responses,
                },
                priority=MessagePriority.NORMAL,
            )
        )

        logger.info(
            f"Consensus {consensus_id} resolved: reached={consensus_reached}, ratio={consensus_data['agreement_ratio']:.2f}"
        )

    def store_task_result(self, task: CognitiveTask, result: Any, success: bool) -> None:
        """Store task result in hierarchical memory for learning and extract knowledge."""
        episode_data = {
            "task_id": task.task_id,
            "task_type": task.task_type.value,
            "content": task.content,
            "result": result,
            "success": success,
            "completion_time": time.time() - task.created_at,
            "agent_id": task.assigned_agent,
            "complexity": task.estimated_complexity,
            "importance": 1.0 if success else 0.5,  # Successful tasks are more important
            "type": "cognitive_task_result",
            "timestamp": time.time(),
        }

        try:
            self.memory_backend.store_episode(task.assigned_agent or "cognitive_orchestrator", episode_data)

            # Extract and store knowledge from successful task results
            if success and result:
                self._extract_knowledge_from_task_result(task, result)

        except Exception as e:
            logger.error(f"Failed to store task result in memory: {e}")

    def _extract_knowledge_from_task_result(self, task: CognitiveTask, result: Any) -> None:
        """Extract entities and relationships from task results for knowledge graph."""
        try:
            # Convert result to text for relationship extraction
            result_text = self._result_to_text(result)

            if result_text:
                # Extract relationships from result
                relationships = self.memory_backend.extract_and_store_relationships(
                    result_text, source=f"task_result_{task.task_id}"
                )

                # Store key entities from task content and result
                task_entities = self._extract_entities_from_task(task, result)
                for entity_data in task_entities:
                    try:
                        entity = Entity(**entity_data)
                        self.memory_backend.store_entity(entity)
                    except Exception as e:
                        logger.debug(f"Failed to store entity {entity_data.get('label')}: {e}")

        except Exception as e:
            logger.error(f"Failed to extract knowledge from task result: {e}")

    def _result_to_text(self, result: Any) -> str:
        """Convert task result to searchable text."""
        if isinstance(result, str):
            return result
        elif isinstance(result, dict):
            # Extract meaningful text from dict results
            text_parts = []
            for key, value in result.items():
                if isinstance(value, str) and len(value) > 3:
                    text_parts.append(f"{key}: {value}")
                elif isinstance(value, (int, float)):
                    text_parts.append(f"{key}: {value}")
            return " ".join(text_parts)
        elif isinstance(result, list):
            return " ".join(str(item) for item in result if item)
        else:
            return str(result)

    def _extract_entities_from_task(self, task: CognitiveTask, result: Any) -> List[Dict[str, Any]]:
        """Extract key entities from task content and result."""
        entities = []

        # Extract from task type and content
        task_type_entity = {
            "id": f"task_type_{task.task_type.value}",
            "label": task.task_type.value.replace("_", " ").title(),
            "entity_type": "task_type",
            "properties": {
                "description": f"Cognitive task type for {task.task_type.value}",
                "complexity_range": "1.0-10.0",
            },
            "source": "task_extraction",
        }
        entities.append(task_type_entity)

        # Extract from result if it's structured
        if isinstance(result, dict):
            for key, value in result.items():
                if isinstance(value, str) and len(value) > 5 and len(value.split()) <= 10:
                    # Potential entity
                    entity_id = f"result_entity_{hash(key + str(value)) % 10000}"
                    entities.append(
                        {
                            "id": entity_id,
                            "label": value,
                            "entity_type": "result_entity",
                            "properties": {"context": key, "task_type": task.task_type.value},
                            "source": f"task_result_{task.task_id}",
                        }
                    )

        return entities

    def retrieve_task_context(
        self, agent_id: str, task_type: CognitiveTaskType, query: str = None, top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """Retrieve relevant task context from memory using semantic search."""
        try:
            # Use semantic search if query provided, otherwise use regular context retrieval
            if query and hasattr(self.memory_backend, "semantic_search"):
                context = self.memory_backend.semantic_search(query, top_k * 2)
            else:
                context = self.memory_backend.retrieve_context(agent_id, query, top_k * 2)

            # Filter for similar task types and enhance with knowledge graph traversal
            relevant_context = []
            for item in context:
                if item.get("task_type") == task_type.value or not item.get("task_type"):
                    relevant_context.append(item)

                    # If this is an entity, traverse related knowledge
                    if item.get("type") == "entity" and item.get("entity_id"):
                        try:
                            traversal = self.memory_backend.traverse_knowledge(
                                item["entity_id"], relationship_types=["related_to", "part_of", "causes"], max_depth=2
                            )
                            if traversal.get("paths"):
                                item["knowledge_paths"] = traversal["paths"][:3]  # Add top 3 paths
                        except Exception as e:
                            logger.debug(f"Failed to traverse knowledge for {item.get('entity_id')}: {e}")

            return relevant_context[:top_k]
        except Exception as e:
            logger.error(f"Failed to retrieve task context: {e}")
            return []

    def update_agent_specialization(
        self, agent_id: str, task_type: CognitiveTaskType, performance_score: float
    ) -> None:
        """Update an agent's specialization score based on task performance."""
        if agent_id not in self.agent_profiles:
            return

        profile = self.agent_profiles[agent_id]

        # Update specialization score using exponential moving average
        current_score = profile.specialization_score.get(task_type, 0.5)
        alpha = 0.1  # Learning rate
        new_score = current_score * (1 - alpha) + performance_score * alpha

        profile.specialization_score[task_type] = max(0.0, min(1.0, new_score))

        logger.debug(f"Updated {agent_id} specialization for {task_type.value}: {new_score:.3f}")

    async def get_agent_performance_report(self, agent_id: str) -> Dict[str, Any]:
        """Get detailed performance report for an agent."""
        if agent_id not in self.agent_profiles:
            return {}

        profile = self.agent_profiles[agent_id]

        # Calculate performance metrics
        recent_history = profile.performance_history[-20:]  # Last 20 tasks

        if not recent_history:
            return {
                "agent_id": agent_id,
                "total_tasks": 0,
                "success_rate": 0.0,
                "average_completion_time": 0.0,
                "specialization_scores": dict(profile.specialization_score),
            }

        success_rate = sum(1 for h in recent_history if h["success"]) / len(recent_history)
        avg_completion_time = sum(h["completion_time"] for h in recent_history) / len(recent_history)

        return {
            "agent_id": agent_id,
            "total_tasks": len(profile.performance_history),
            "success_rate": success_rate,
            "average_completion_time": avg_completion_time,
            "specialization_scores": dict(profile.specialization_score),
            "current_load": profile.current_load,
        }
