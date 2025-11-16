"""
CrewAI-Inspired Orchestration for Grokputer Pantheon Agents.

Implements CrewAI patterns:
- Crew: Autonomous agent teams with defined roles
- Flows: Event-driven workflows with state management
- Delegation: Agents can delegate tasks to specialized agents

This provides Crew-style orchestration while maintaining Pantheon architecture.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

from src.core.base_agent import BaseAgent
from src.core.message_bus import Message, MessageBus, MessagePriority

logger = logging.getLogger(__name__)


class CrewRole(Enum):
    """CrewAI-inspired agent roles."""

    COORDINATOR = "coordinator"
    EXECUTOR = "executor"
    ANALYZER = "analyzer"
    VALIDATOR = "validator"
    LEARNER = "learner"
    OBSERVER = "observer"
    IMPROVER = "improver"
    MEMORY_MANAGER = "memory_manager"
    SPECIALIST = "specialist"


class FlowState(Enum):
    """Flow execution states."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class CrewMember:
    """Represents a member of a Crew with their role and capabilities."""

    agent: BaseAgent
    role: CrewRole
    capabilities: Set[str] = field(default_factory=set)
    priority: int = 1  # Higher priority agents get preference
    max_concurrent_tasks: int = 3
    active_tasks: int = 0

    def can_handle(self, task_type: str) -> bool:
        """Check if this crew member can handle a task type."""
        return task_type in self.capabilities

    def is_available(self) -> bool:
        """Check if agent is available for new tasks."""
        return self.active_tasks < self.max_concurrent_tasks


@dataclass
class FlowStep:
    """A step in a Flow workflow."""

    step_id: str
    description: str
    required_role: CrewRole
    task_type: str
    dependencies: List[str] = field(default_factory=list)  # Step IDs this depends on
    timeout: Optional[float] = None
    retry_count: int = 0
    max_retries: int = 3

    def is_ready(self, completed_steps: Set[str]) -> bool:
        """Check if this step is ready to execute."""
        return all(dep in completed_steps for dep in self.dependencies)


@dataclass
class FlowExecution:
    """Execution state of a Flow."""

    flow_id: str
    steps: Dict[str, FlowStep]
    state: FlowState = FlowState.PENDING
    results: Dict[str, Any] = field(default_factory=dict)
    completed_steps: Set[str] = field(default_factory=set)
    failed_steps: Set[str] = field(default_factory=set)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    assigned_agents: Dict[str, str] = field(default_factory=dict)  # step_id -> agent_id


class CrewOrchestrator:
    """
    CrewAI-inspired orchestrator for Grokputer agents.

    Provides:
    - Crew formation with role-based agents
    - Flow execution with dependency management
    - Dynamic delegation based on capabilities
    - State persistence and recovery
    """

    def __init__(self, message_bus: MessageBus):
        self.message_bus = message_bus
        self.crews: Dict[str, Dict[str, CrewMember]] = {}  # crew_id -> {agent_id: member}
        self.active_flows: Dict[str, FlowExecution] = {}
        self.flow_results: Dict[str, Dict[str, Any]] = {}

        # Flow execution tracking
        self.flow_completion_events: Dict[str, asyncio.Event] = {}

    def create_crew(self, crew_id: str, members: List[CrewMember]) -> None:
        """
        Create a new Crew with specified members.

        Args:
            crew_id: Unique identifier for the crew
            members: List of CrewMember objects
        """
        crew = {}
        for member in members:
            crew[member.agent.agent_id] = member

        self.crews[crew_id] = crew
        logger.info(f"Created crew '{crew_id}' with {len(members)} members")

    def define_flow(self, flow_id: str, steps: List[FlowStep]) -> None:
        """
        Define a reusable Flow template.

        Args:
            flow_id: Unique identifier for the flow
            steps: List of FlowStep objects defining the workflow
        """
        flow_execution = FlowExecution(flow_id=flow_id, steps={step.step_id: step for step in steps})

        self.active_flows[flow_id] = flow_execution
        self.flow_completion_events[flow_id] = asyncio.Event()

        logger.info(f"Defined flow '{flow_id}' with {len(steps)} steps")

    async def execute_flow(self, crew_id: str, flow_id: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute a Flow using a Crew.

        Args:
            crew_id: ID of the crew to use
            flow_id: ID of the flow to execute
            context: Additional context for execution

        Returns:
            Flow execution results
        """
        if crew_id not in self.crews:
            raise ValueError(f"Crew '{crew_id}' not found")

        if flow_id not in self.active_flows:
            raise ValueError(f"Flow '{flow_id}' not found")

        crew = self.crews[crew_id]
        flow = self.active_flows[flow_id]

        # Reset flow state
        flow.state = FlowState.RUNNING
        flow.start_time = datetime.now()
        flow.results = context or {}
        flow.completed_steps = set()
        flow.failed_steps = set()
        flow.assigned_agents = {}

        logger.info(f"Starting flow '{flow_id}' execution with crew '{crew_id}'")

        try:
            # Execute flow steps
            await self._execute_flow_steps(crew, flow)

            flow.state = FlowState.COMPLETED
            flow.end_time = datetime.now()

            # Store results
            self.flow_results[flow_id] = flow.results

            # Signal completion
            if flow_id in self.flow_completion_events:
                self.flow_completion_events[flow_id].set()

            logger.info(f"Flow '{flow_id}' completed successfully")
            return flow.results

        except Exception as e:
            flow.state = FlowState.FAILED
            flow.end_time = datetime.now()
            logger.error(f"Flow '{flow_id}' failed: {e}")

            # Signal completion with failure
            if flow_id in self.flow_completion_events:
                self.flow_completion_events[flow_id].set()

            raise

    async def _execute_flow_steps(self, crew: Dict[str, CrewMember], flow: FlowExecution) -> None:
        """Execute flow steps respecting dependencies."""
        pending_steps = set(flow.steps.keys())
        executing_steps: Dict[str, asyncio.Task] = {}

        while pending_steps or executing_steps:
            # Find ready steps
            ready_steps = [step_id for step_id in pending_steps if flow.steps[step_id].is_ready(flow.completed_steps)]

            # Start ready steps
            for step_id in ready_steps:
                step = flow.steps[step_id]
                task = asyncio.create_task(self._execute_step(crew, flow, step))
                executing_steps[step_id] = task
                pending_steps.remove(step_id)

            if not executing_steps:
                # No steps ready and none executing - possible deadlock
                remaining = list(pending_steps)
                logger.warning(f"Flow deadlock detected. Remaining steps: {remaining}")
                break

            # Wait for at least one step to complete
            done, pending = await asyncio.wait(executing_steps.values(), return_when=asyncio.FIRST_COMPLETED)

            # Collect completed step_ids and their tasks
            completed_steps = []
            for task in done:
                for step_id, exec_task in list(executing_steps.items()):
                    if exec_task == task:
                        completed_steps.append((step_id, task))
                        del executing_steps[step_id]
                        break

            # Process completed steps
            for step_id, task in completed_steps:
                try:
                    result = await task
                    flow.results[step_id] = result
                    flow.completed_steps.add(step_id)
                    logger.debug(f"Step '{step_id}' completed")
                except Exception as e:
                    flow.failed_steps.add(step_id)
                    logger.error(f"Step '{step_id}' failed: {e}")

                    # Handle retries
                    step = flow.steps[step_id]
                    if step.retry_count < step.max_retries:
                        step.retry_count += 1
                        pending_steps.add(step_id)
                        logger.info(f"Retrying step '{step_id}' (attempt {step.retry_count})")
                    else:
                        raise  # Max retries exceeded

    async def _execute_step(self, crew: Dict[str, CrewMember], flow: FlowExecution, step: FlowStep) -> Any:
        """Execute a single flow step."""
        # Find suitable agent
        agent_id = self._select_agent_for_step(crew, step)
        if not agent_id:
            raise RuntimeError(f"No suitable agent found for step '{step.step_id}' requiring {step.required_role}")

        agent = crew[agent_id].agent
        crew[agent_id].active_tasks += 1
        flow.assigned_agents[step.step_id] = agent_id

        try:
            # Create task message
            task_data = {
                "flow_id": flow.flow_id,
                "step_id": step.step_id,
                "task_type": step.task_type,
                "description": step.description,
                "context": flow.results,
                "timeout": step.timeout,
            }

            message = Message(
                from_agent="crew_orchestrator",
                to_agent=agent.agent_id,
                message_type="crew_task",
                content=task_data,
                priority=MessagePriority.HIGH,
            )

            # Send task to agent
            response = await self.message_bus.send_request(
                from_agent=message.from_agent,
                to_agent=message.to_agent,
                message_type=message.message_type,
                content=message.content,
                priority=message.priority,
                timeout=step.timeout,
            )

            if response and response.content.get("status") == "success":
                return response.content.get("result")
            else:
                raise RuntimeError(f"Agent {agent_id} failed step {step.step_id}: {response}")

        finally:
            crew[agent_id].active_tasks -= 1

    def _select_agent_for_step(self, crew: Dict[str, CrewMember], step: FlowStep) -> Optional[str]:
        """Select the best available agent for a step."""
        candidates = []

        for agent_id, member in crew.items():
            if member.role == step.required_role and member.can_handle(step.task_type) and member.is_available():
                candidates.append((agent_id, member.priority))

        if not candidates:
            return None

        # Select highest priority available agent
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]

    async def delegate_task(
        self,
        crew_id: str,
        task_type: str,
        task_data: Dict[str, Any],
        priority: MessagePriority = MessagePriority.NORMAL,
    ) -> Any:
        """
        Delegate a task to the most suitable agent in a crew.

        Args:
            crew_id: ID of the crew to use
            task_type: Type of task to delegate
            task_data: Task-specific data
            priority: Message priority

        Returns:
            Task result
        """
        if crew_id not in self.crews:
            raise ValueError(f"Crew '{crew_id}' not found")

        crew = self.crews[crew_id]

        # Find best agent for task
        best_agent = None
        best_priority = -1

        for member in crew.values():
            if member.can_handle(task_type) and member.is_available():
                if member.priority > best_priority:
                    best_agent = member
                    best_priority = member.priority

        if not best_agent:
            raise RuntimeError(f"No available agent in crew '{crew_id}' can handle task type '{task_type}'")

        # Execute task
        best_agent.active_tasks += 1

        try:
            message = Message(
                from_agent="crew_orchestrator",
                to_agent=best_agent.agent.agent_id,
                message_type="delegated_task",
                content={"task_type": task_type, "task_data": task_data},
                priority=priority,
            )

            response = await self.message_bus.send_request(
                from_agent=message.from_agent,
                to_agent=message.to_agent,
                message_type=message.message_type,
                content=message.content,
                priority=message.priority,
                timeout=300,
            )

            if response and response.content.get("status") == "success":
                return response.content.get("result")
            else:
                raise RuntimeError(f"Delegated task failed: {response}")

        finally:
            best_agent.active_tasks -= 1

    def get_crew_status(self, crew_id: str) -> Dict[str, Any]:
        """Get status of a crew."""
        if crew_id not in self.crews:
            return {"status": "not_found"}

        crew = self.crews[crew_id]
        return {
            "crew_id": crew_id,
            "member_count": len(crew),
            "members": [
                {
                    "agent_id": agent_id,
                    "role": member.role.value,
                    "capabilities": list(member.capabilities),
                    "active_tasks": member.active_tasks,
                    "available": member.is_available(),
                }
                for agent_id, member in crew.items()
            ],
        }

    def get_flow_status(self, flow_id: str) -> Dict[str, Any]:
        """Get status of a flow execution."""
        if flow_id not in self.active_flows:
            return {"status": "not_found"}

        flow = self.active_flows[flow_id]
        return {
            "flow_id": flow_id,
            "state": flow.state.value,
            "completed_steps": len(flow.completed_steps),
            "total_steps": len(flow.steps),
            "failed_steps": len(flow.failed_steps),
            "assigned_agents": flow.assigned_agents,
            "start_time": flow.start_time.isoformat() if flow.start_time else None,
            "end_time": flow.end_time.isoformat() if flow.end_time else None,
        }
