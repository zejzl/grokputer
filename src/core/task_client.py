"""
Task Client for Agent-TaskMaster Communication

Provides a simple interface for agents to interact with the TaskMaster system.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.core.message_bus import Message, MessageBus, MessagePriority

logger = logging.getLogger(__name__)


class TaskClient:
    """
    Client interface for agents to communicate with TaskMaster.

    Provides methods for:
    - Requesting tasks when idle
    - Updating task status
    - Sending heartbeats
    - Registering capabilities
    """

    def __init__(self, agent_id: str, message_bus: MessageBus):
        self.agent_id = agent_id
        self.message_bus = message_bus
        self.current_tasks: Dict[str, Dict[str, Any]] = {}  # task_id -> task_data
        self.capabilities: List[str] = []
        self._seen_task_ids: set = set()  # every task id ever received, so a push cannot re-add a finished task
        # Inbox for task_assigned pushes (auto-delegation). Agents that already are BaseAgents have
        # their own inbox and task client, and should not also use this class.
        self.message_bus.register_agent(self.agent_id)

    async def poll_assignments(self) -> int:
        """Pick up task_assigned pushes waiting in this client's inbox. Returns how many were added.

        Anything else in the inbox is dropped, so only use this client for agents that read no
        other messages.
        """
        added = 0
        while True:
            try:
                message = await self.message_bus.receive(self.agent_id, timeout=0.01)
            except asyncio.TimeoutError:
                return added
            if message.message_type == "task_assigned" and isinstance(message.content.get("task"), dict):
                task = message.content["task"]
                if task["task_id"] in self._seen_task_ids:
                    continue
                self._seen_task_ids.add(task["task_id"])
                self.current_tasks[task["task_id"]] = task
                added += 1
                logger.info(f"[TaskClient:{self.agent_id}] Pushed task: {task['task_id']} - {task['title']}")
            else:
                logger.debug(f"[TaskClient:{self.agent_id}] Ignored {message.message_type} message")

    async def register_capabilities(self, capabilities: List[str]):
        """Register agent capabilities with TaskMaster."""
        self.capabilities = capabilities

        response = await self._send_message("agent_capabilities", {"capabilities": capabilities})

        logger.info(f"[TaskClient:{self.agent_id}] Registered capabilities: {capabilities}")
        return response

    async def send_heartbeat(self):
        """Send heartbeat to TaskMaster."""
        response = await self._send_message("agent_heartbeat", {"timestamp": datetime.now().timestamp()})
        return response

    async def request_task(self, priority: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Request a task assignment from TaskMaster."""
        content = {}
        if priority:
            content["priority"] = priority

        response = await self._send_message("task_request", content)

        if response and response.get("status") == "assigned":
            task_data = response.get("task")
            if task_data:
                self._seen_task_ids.add(task_data["task_id"])
                self.current_tasks[task_data["task_id"]] = task_data
                logger.info(
                    f"[TaskClient:{self.agent_id}] Assigned task: {task_data['task_id']} - {task_data['title']}"
                )
                return task_data

        logger.debug(f"[TaskClient:{self.agent_id}] Task request response: {response}")
        return None

    async def update_task_status(self, task_id: str, status: str, notes: str = ""):
        """Update the status of a task."""
        response = await self._send_message(
            "task_status_update", {"task_id": task_id, "status": status, "notes": notes}
        )

        if response and response.get("status") == "updated":
            if status in ["completed", "failed", "cancelled"]:
                # Remove from current tasks
                self.current_tasks.pop(task_id, None)

            logger.info(f"[TaskClient:{self.agent_id}] Updated task {task_id} to {status}")
        else:
            logger.warning(f"[TaskClient:{self.agent_id}] Failed to update task {task_id}: {response}")

        return response

    async def get_available_tasks(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get list of available tasks."""
        response = await self._send_message("get_available_tasks", {"limit": limit})

        if response and response.get("status") == "available_tasks":
            return response.get("tasks", [])
        return []

    async def get_system_stats(self) -> Optional[Dict[str, Any]]:
        """Get system-wide task statistics."""
        response = await self._send_message("get_system_stats", {})
        return response.get("data") if response else None

    async def create_task(
        self,
        title: str,
        description: str,
        priority: str = "medium",
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        required_capabilities: Optional[List[str]] = None,
    ):
        """Create a new task (admin function). Only agents with every `required_capabilities` may take it."""
        response = await self._send_message(
            "create_task",
            {
                "title": title,
                "description": description,
                "priority": priority,
                "tags": tags or [],
                "metadata": metadata or {},
                "required_capabilities": required_capabilities or [],
            },
        )

        return response

    def get_current_tasks(self) -> List[Dict[str, Any]]:
        """Get currently assigned tasks."""
        return list(self.current_tasks.values())

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific task by ID."""
        return self.current_tasks.get(task_id)

    async def _send_message(
        self, message_type: str, content: Dict[str, Any], timeout: float = 10.0
    ) -> Optional[Dict[str, Any]]:
        """Send a message to TaskMaster and return its reply (None if it is absent or times out)."""
        try:
            # Send message
            message = Message(
                from_agent=self.agent_id,
                to_agent="taskmaster",
                message_type=message_type,
                content=content,
                priority=MessagePriority.NORMAL,
            )

            return await self.message_bus.send_and_wait("taskmaster", message, timeout=timeout)

        except Exception as e:
            logger.error(f"[TaskClient:{self.agent_id}] Error sending message: {e}")
            return None

    async def start_heartbeat_loop(self, interval: float = 60.0):
        """Start periodic heartbeat loop."""
        while True:
            try:
                await self.send_heartbeat()
                await asyncio.sleep(interval)
            except Exception as e:
                logger.error(f"[TaskClient:{self.agent_id}] Heartbeat error: {e}")
                await asyncio.sleep(interval)

    async def start_idle_task_loop(self, check_interval: float = 30.0):
        """Start loop that requests tasks when agent is idle."""
        while True:
            try:
                await self.poll_assignments()

                # Check if we have capacity for more tasks
                current_count = len(
                    [t for t in self.current_tasks.values() if t.get("status") in ["assigned", "in_progress"]]
                )

                if current_count < 3:  # Max concurrent tasks
                    task = await self.request_task()
                    if task:
                        logger.info(f"[TaskClient:{self.agent_id}] Received new task: {task['title']}")

                await asyncio.sleep(check_interval)

            except Exception as e:
                logger.error(f"[TaskClient:{self.agent_id}] Idle task loop error: {e}")
                await asyncio.sleep(check_interval)
