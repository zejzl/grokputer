"""
Task Management System for Grokputer Pantheon

Provides centralized task delegation, status tracking, and agent coordination.
Integrates with MessageBus for real-time task communication and delegation.
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from src.core.base_agent import BaseAgent
from src.core.message_bus import MessageBus, Message, MessagePriority
from src.observability.session_logger import SessionLogger

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Task execution status."""

    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    """Task priority levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Task:
    """Represents a task in the system."""

    task_id: str
    title: str
    description: str
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.PENDING
    assigned_agent: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    deadline: Optional[float] = None
    dependencies: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary for serialization."""
        return {
            "task_id": self.task_id,
            "title": self.title,
            "description": self.description,
            "priority": self.priority.value,
            "status": self.status.value,
            "assigned_agent": self.assigned_agent,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "deadline": self.deadline,
            "dependencies": self.dependencies,
            "tags": self.tags,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Task":
        """Create task from dictionary."""
        return cls(
            task_id=data["task_id"],
            title=data["title"],
            description=data["description"],
            priority=TaskPriority(data["priority"]),
            status=TaskStatus(data["status"]),
            assigned_agent=data.get("assigned_agent"),
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            deadline=data.get("deadline"),
            dependencies=data.get("dependencies", []),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
        )


class TaskRegistry:
    """Central registry for managing tasks across the system."""

    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self.agent_workloads: Dict[str, Set[str]] = {}  # agent_id -> set of task_ids
        self.task_counter = 0

    def create_task(
        self,
        title: str,
        description: str,
        priority: TaskPriority = TaskPriority.MEDIUM,
        deadline: Optional[float] = None,
        dependencies: List[str] = None,
        tags: List[str] = None,
        metadata: Dict[str, Any] = None,
    ) -> Task:
        """Create a new task."""
        self.task_counter += 1
        task_id = f"task_{self.task_counter:04d}"

        task = Task(
            task_id=task_id,
            title=title,
            description=description,
            priority=priority,
            deadline=deadline,
            dependencies=dependencies or [],
            tags=tags or [],
            metadata=metadata or {},
        )

        self.tasks[task_id] = task
        logger.info(f"Created task: {task_id} - {title}")
        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID."""
        return self.tasks.get(task_id)

    def get_all_tasks(self, status_filter: Optional[TaskStatus] = None) -> List[Task]:
        """Get all tasks, optionally filtered by status."""
        tasks = list(self.tasks.values())
        if status_filter:
            tasks = [t for t in tasks if t.status == status_filter]
        return sorted(tasks, key=lambda t: (t.priority.value, t.created_at), reverse=True)

    def get_pending_tasks(self) -> List[Task]:
        """Get all pending tasks."""
        return self.get_all_tasks(TaskStatus.PENDING)

    def assign_task(self, task_id: str, agent_id: str) -> bool:
        """Assign a task to an agent."""
        task = self.tasks.get(task_id)
        if not task or task.status != TaskStatus.PENDING:
            return False

        task.assigned_agent = agent_id
        task.status = TaskStatus.ASSIGNED
        task.updated_at = time.time()

        # Track agent workload
        if agent_id not in self.agent_workloads:
            self.agent_workloads[agent_id] = set()
        self.agent_workloads[agent_id].add(task_id)

        logger.info(f"Assigned task {task_id} to agent {agent_id}")
        return True

    def update_task_status(self, task_id: str, status: TaskStatus, agent_id: Optional[str] = None) -> bool:
        """Update task status."""
        task = self.tasks.get(task_id)
        if not task:
            return False

        old_status = task.status
        task.status = status
        task.updated_at = time.time()

        if agent_id:
            task.assigned_agent = agent_id

        # Handle completion/cleanup
        if status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            if task.assigned_agent and task_id in self.agent_workloads.get(task.assigned_agent, set()):
                self.agent_workloads[task.assigned_agent].remove(task_id)

        logger.info(f"Updated task {task_id} status: {old_status.value} -> {status.value}")
        return True

    def get_agent_workload(self, agent_id: str) -> List[Task]:
        """Get all tasks assigned to an agent."""
        task_ids = self.agent_workloads.get(agent_id, set())
        return [self.tasks[task_id] for task_id in task_ids if task_id in self.tasks]

    def get_available_tasks(self, agent_id: str, max_tasks: int = 3) -> List[Task]:
        """Get tasks that could be assigned to an agent."""
        # Get pending tasks not assigned to this agent
        available_tasks = [
            task
            for task in self.tasks.values()
            if task.status == TaskStatus.PENDING and task.assigned_agent != agent_id
        ]

        # Sort by priority and deadline
        def sort_key(task):
            priority_weight = {"critical": 4, "high": 3, "medium": 2, "low": 1}[task.priority.value]
            deadline_weight = 0
            if task.deadline:
                time_until_deadline = task.deadline - time.time()
                deadline_weight = max(0, 1000 - time_until_deadline)  # Closer deadlines get higher weight
            return (priority_weight, deadline_weight, -task.created_at)  # Newer tasks first

        available_tasks.sort(key=sort_key, reverse=True)
        return available_tasks[:max_tasks]

    def get_system_stats(self) -> Dict[str, Any]:
        """Get system-wide task statistics."""
        total_tasks = len(self.tasks)
        status_counts = {}
        for status in TaskStatus:
            status_counts[status.value] = sum(1 for t in self.tasks.values() if t.status == status)

        priority_counts = {}
        for priority in TaskPriority:
            priority_counts[priority.value] = sum(1 for t in self.tasks.values() if t.priority == priority)

        agent_workloads = {agent_id: len(tasks) for agent_id, tasks in self.agent_workloads.items()}

        return {
            "total_tasks": total_tasks,
            "status_counts": status_counts,
            "priority_counts": priority_counts,
            "agent_workloads": agent_workloads,
            "active_agents": len([aid for aid, tasks in agent_workloads.items() if tasks > 0]),
        }


class TaskMaster(BaseAgent):
    """
    Central task coordination agent.

    Manages task delegation, monitors agent workloads, and ensures
    tasks are completed efficiently across the Pantheon.
    """

    def __init__(self, message_bus: MessageBus, session_logger: SessionLogger, config: Dict[str, Any]):
        super().__init__(agent_id="taskmaster", message_bus=message_bus, session_logger=session_logger, config=config)

        self.task_registry = TaskRegistry()
        self.agent_capabilities: Dict[str, List[str]] = {}  # agent_id -> list of capabilities
        self.last_heartbeat: Dict[str, float] = {}  # agent_id -> last heartbeat time

        # Auto-delegation settings
        self.auto_delegate = config.get("auto_delegate", True)
        self.max_agent_tasks = config.get("max_agent_tasks", 3)
        self.heartbeat_timeout = config.get("heartbeat_timeout", 300)  # 5 minutes

        logger.info(
            "[TaskMaster] Initialized with auto_delegate=%s, max_agent_tasks=%s",
            self.auto_delegate,
            self.max_agent_tasks,
        )

    async def process_message(self, message: Message) -> Optional[Dict[str, Any]]:
        """Process incoming messages."""
        msg_type = message.message_type

        if msg_type == "task_request":
            return await self._handle_task_request(message)
        elif msg_type == "task_status_update":
            return await self._handle_task_status_update(message)
        elif msg_type == "agent_heartbeat":
            return await self._handle_agent_heartbeat(message)
        elif msg_type == "agent_capabilities":
            return await self._handle_agent_capabilities(message)
        elif msg_type == "get_system_stats":
            return await self._handle_get_system_stats(message)
        elif msg_type == "create_task":
            return await self._handle_create_task(message)
        elif msg_type == "get_available_tasks":
            return await self._handle_get_available_tasks(message)

        return {"status": "unknown_message_type", "type": msg_type}

    async def _handle_task_request(self, message: Message) -> Dict[str, Any]:
        """Handle agent requesting a task."""
        agent_id = message.from_agent
        requested_priority = message.content.get("priority")

        # Check agent workload
        current_tasks = self.task_registry.get_agent_workload(agent_id)
        active_tasks = [t for t in current_tasks if t.status in [TaskStatus.ASSIGNED, TaskStatus.IN_PROGRESS]]

        if len(active_tasks) >= self.max_agent_tasks:
            return {
                "status": "busy",
                "message": f"Agent {agent_id} already has {len(active_tasks)} active tasks",
                "active_tasks": len(active_tasks),
            }

        # Find suitable task
        available_tasks = self.task_registry.get_available_tasks(agent_id, 1)
        if not available_tasks:
            return {"status": "no_tasks", "message": "No available tasks"}

        task = available_tasks[0]

        # Assign task
        if self.task_registry.assign_task(task.task_id, agent_id):
            # Update task status
            self.task_registry.update_task_status(task.task_id, TaskStatus.ASSIGNED, agent_id)

            # Notify agent
            assign_message = Message(
                from_agent=self.agent_id,
                to_agent=agent_id,
                message_type="task_assigned",
                content={"task": task.to_dict(), "assigned_by": "taskmaster"},
                priority=MessagePriority.HIGH,
            )
            await self.message_bus.send(assign_message)

            return {"status": "assigned", "task_id": task.task_id, "task_title": task.title}
        else:
            return {"status": "assignment_failed", "task_id": task.task_id}

    async def _handle_task_status_update(self, message: Message) -> Dict[str, Any]:
        """Handle task status update from agent."""
        agent_id = message.from_agent
        task_id = message.content.get("task_id")
        new_status = message.content.get("status")
        notes = message.content.get("notes", "")

        if not task_id or not new_status:
            return {"status": "error", "message": "Missing task_id or status"}

        try:
            status = TaskStatus(new_status)
            success = self.task_registry.update_task_status(task_id, status, agent_id)

            if success:
                # Log the update
                self.session_logger.log_task_update(agent_id, task_id, status.value, notes)

                # Check for auto-delegation
                if self.auto_delegate and status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                    await self._check_auto_delegate(agent_id)

                return {"status": "updated", "task_id": task_id, "new_status": status.value}
            else:
                return {"status": "error", "message": f"Task {task_id} not found"}

        except ValueError:
            return {"status": "error", "message": f"Invalid status: {new_status}"}

    async def _handle_agent_heartbeat(self, message: Message) -> Dict[str, Any]:
        """Handle agent heartbeat."""
        agent_id = message.from_agent
        self.last_heartbeat[agent_id] = time.time()

        # Check for stale agents and reassign their tasks
        await self._check_stale_agents()

        return {"status": "heartbeat_ack", "timestamp": time.time()}

    async def _handle_agent_capabilities(self, message: Message) -> Dict[str, Any]:
        """Handle agent capabilities update."""
        agent_id = message.from_agent
        capabilities = message.content.get("capabilities", [])

        self.agent_capabilities[agent_id] = capabilities
        logger.info(f"[TaskMaster] Updated capabilities for {agent_id}: {capabilities}")

        return {"status": "capabilities_updated"}

    async def _handle_get_system_stats(self, message: Message) -> Dict[str, Any]:
        """Handle request for system statistics."""
        stats = self.task_registry.get_system_stats()
        return {"status": "stats", "data": stats}

    async def _handle_create_task(self, message: Message) -> Dict[str, Any]:
        """Handle task creation request."""
        content = message.content

        task = self.task_registry.create_task(
            title=content.get("title", "Untitled Task"),
            description=content.get("description", ""),
            priority=TaskPriority(content.get("priority", "medium")),
            deadline=content.get("deadline"),
            dependencies=content.get("dependencies", []),
            tags=content.get("tags", []),
            metadata=content.get("metadata", {}),
        )

        # Auto-delegate if enabled
        if self.auto_delegate:
            await self._try_auto_delegate_task(task)

        return {"status": "created", "task": task.to_dict()}

    async def _handle_get_available_tasks(self, message: Message) -> Dict[str, Any]:
        """Handle request for available tasks."""
        agent_id = message.from_agent
        limit = message.content.get("limit", 5)

        available_tasks = self.task_registry.get_available_tasks(agent_id, limit)
        return {"status": "available_tasks", "tasks": [task.to_dict() for task in available_tasks]}

    async def _check_auto_delegate(self, agent_id: str):
        """Check if we should auto-delegate tasks to an agent."""
        if not self.auto_delegate:
            return

        # Get agent's current workload
        current_tasks = self.task_registry.get_agent_workload(agent_id)
        active_count = sum(1 for t in current_tasks if t.status in [TaskStatus.ASSIGNED, TaskStatus.IN_PROGRESS])

        # If agent has capacity, try to assign a task
        if active_count < self.max_agent_tasks:
            available_tasks = self.task_registry.get_available_tasks(agent_id, 1)
            if available_tasks:
                task = available_tasks[0]
                if self.task_registry.assign_task(task.task_id, agent_id):
                    self.task_registry.update_task_status(task.task_id, TaskStatus.ASSIGNED, agent_id)

                    assign_message = Message(
                        from_agent=self.agent_id,
                        to_agent=agent_id,
                        message_type="task_assigned",
                        content={"task": task.to_dict(), "assigned_by": "taskmaster", "reason": "auto_delegation"},
                        priority=MessagePriority.NORMAL,
                    )
                    await self.message_bus.send(assign_message)

    async def _try_auto_delegate_task(self, task: Task):
        """Try to auto-delegate a newly created task."""
        if not self.auto_delegate:
            return

        # Find best agent for this task
        best_agent = None
        min_workload = float("inf")

        for agent_id in self.agent_capabilities.keys():
            # Check if agent is active (recent heartbeat)
            last_heartbeat = self.last_heartbeat.get(agent_id, 0)
            if time.time() - last_heartbeat > self.heartbeat_timeout:
                continue  # Skip inactive agents

            # Check workload
            current_tasks = self.task_registry.get_agent_workload(agent_id)
            active_count = sum(1 for t in current_tasks if t.status in [TaskStatus.ASSIGNED, TaskStatus.IN_PROGRESS])

            if active_count < self.max_agent_tasks and active_count < min_workload:
                best_agent = agent_id
                min_workload = active_count

        if best_agent:
            if self.task_registry.assign_task(task.task_id, best_agent):
                self.task_registry.update_task_status(task.task_id, TaskStatus.ASSIGNED, best_agent)

                assign_message = Message(
                    from_agent=self.agent_id,
                    to_agent=best_agent,
                    message_type="task_assigned",
                    content={"task": task.to_dict(), "assigned_by": "taskmaster", "reason": "auto_delegation"},
                    priority=MessagePriority.NORMAL,
                )
                await self.message_bus.send(assign_message)

    async def _check_stale_agents(self):
        """Check for stale agents and reassign their tasks."""
        current_time = time.time()
        stale_agents = []

        for agent_id, last_heartbeat in self.last_heartbeat.items():
            if current_time - last_heartbeat > self.heartbeat_timeout:
                stale_agents.append(agent_id)

        for agent_id in stale_agents:
            # Reassign tasks from stale agent
            tasks = self.task_registry.get_agent_workload(agent_id)
            for task in tasks:
                if task.status in [TaskStatus.ASSIGNED, TaskStatus.IN_PROGRESS]:
                    # Mark as pending and remove assignment
                    task.status = TaskStatus.PENDING
                    task.assigned_agent = None
                    task.updated_at = current_time

                    logger.warning(f"[TaskMaster] Reassigned task {task.task_id} from stale agent {agent_id}")

                    # Try to auto-delegation to another agent
                    if self.auto_delegate:
                        await self._try_auto_delegate_task(task)

    async def on_start(self):
        """Initialize taskmaster."""
        logger.info("[TaskMaster] Starting task coordination system")

        # Register with message bus (coordinator notification removed for demo)
        # ready_message = Message(
        #     from_agent=self.agent_id,
        #     to_agent="coordinator",
        #     message_type="agent_ready",
        #     content={
        #         "agent_id": self.agent_id,
        #         "capabilities": ["task_management", "delegation", "coordination"]
        #     },
        #     priority=MessagePriority.NORMAL
        # )
        # await self.message_bus.send(ready_message)

    async def on_stop(self):
        """Cleanup on shutdown."""
        logger.info("[TaskMaster] Shutting down task coordination system")

    def get_system_status(self) -> Dict[str, Any]:
        """Get current system status."""
        return {
            "taskmaster_status": "active",
            "registered_agents": list(self.agent_capabilities.keys()),
            "active_agents": len(
                [
                    aid
                    for aid in self.last_heartbeat.keys()
                    if time.time() - self.last_heartbeat[aid] <= self.heartbeat_timeout
                ]
            ),
            "task_stats": self.task_registry.get_system_stats(),
            "auto_delegate": self.auto_delegate,
            "max_agent_tasks": self.max_agent_tasks,
        }
