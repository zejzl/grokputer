# src/agents/executor_agent.py
"""
Executor Agent: Orchestrates complex multi-step workflows.
Phase 2: Handles sequences (e.g., observe-analyze-validate-act loops), stateful execution.
Integrates Coordinator for delegation, Memory for workflow state.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Dict, Any, List, Optional
from enum import Enum
from datetime import datetime

from src.core.base_agent import BaseAgent
from src.core.message_bus import MessageBus, Message, MessagePriority

logger = logging.getLogger(__name__)


class WorkflowState(Enum):
    """Workflow states."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class ExecutorAgent(BaseAgent):
    def __init__(self, agent_id: str, message_bus, session_logger, config: Dict[str, Any], action_executor=None):
        super().__init__(agent_id, message_bus, session_logger, config)
        self.action_executor = action_executor
        self.config = config or {
            "debug": False,
            "max_steps": 20,
            "timeout_per_step": 30,  # Seconds
            "recovery_retries": 3,
            "parallel_threshold": 0.5,  # Fraction of steps that can parallel
        }

        # Initialize workflow storage
        self.active_workflows: Dict[str, Dict[str, Any]] = {}
        self.workflow_history: List[Dict[str, Any]] = []
        self.step_tasks: Dict[str, List[asyncio.Task]] = {}  # workflow_id -> tasks for parallel

        logger.info(f"[{self.agent_id}] Executor agent initialized")

    async def process_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process workflow execution requests.

        Message types:
        - execute_workflow: Start a new workflow execution
        - get_workflow_status: Get status of a running workflow
        - cancel_workflow: Cancel a running workflow
        """
        msg_type = message.get("type")

        if msg_type == "execute_workflow":
            return await self._handle_execute_workflow(message)
        elif msg_type == "get_workflow_status":
            return await self._handle_get_status(message)
        elif msg_type == "cancel_workflow":
            return await self._handle_cancel_workflow(message)
        else:
            logger.warning(f"[{self.agent_id}] Unknown message type: {msg_type}")
            return {"status": "error", "reason": f"Unknown message type: {msg_type}"}

    async def _handle_execute_workflow(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle workflow execution request."""
        workflow_id = message.get("workflow_id") or f"workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        steps = message.get("steps", [])
        context = message.get("context", {})

        if not steps:
            return {"status": "error", "reason": "No steps provided"}

        # Initialize workflow
        self.active_workflows[workflow_id] = {
            "id": workflow_id,
            "steps": steps,
            "context": context,
            "state": WorkflowState.IN_PROGRESS,
            "current_step": 0,
            "results": {},
            "start_time": datetime.now(),
            "errors": [],
        }

        logger.info(f"[{self.agent_id}] Started workflow {workflow_id} with {len(steps)} steps")

        # Start execution (in background)
        asyncio.create_task(self._execute_workflow(workflow_id))

        return {"status": "started", "workflow_id": workflow_id}

    async def _handle_get_status(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle workflow status request."""
        workflow_id = message.get("workflow_id")
        if not workflow_id or workflow_id not in self.active_workflows:
            return {"status": "error", "reason": "Workflow not found"}

        workflow = self.active_workflows[workflow_id]
        return {
            "status": "ok",
            "workflow_id": workflow_id,
            "state": workflow["state"].value,
            "current_step": workflow["current_step"],
            "total_steps": len(workflow["steps"]),
            "results": workflow["results"],
            "errors": workflow["errors"],
        }

    async def _handle_cancel_workflow(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle workflow cancellation request."""
        workflow_id = message.get("workflow_id")
        if not workflow_id or workflow_id not in self.active_workflows:
            return {"status": "error", "reason": "Workflow not found"}

        self.active_workflows[workflow_id]["state"] = WorkflowState.PAUSED
        logger.info(f"[{self.agent_id}] Cancelled workflow {workflow_id}")
        return {"status": "cancelled", "workflow_id": workflow_id}

    async def _execute_workflow(self, workflow_id: str):
        """Execute a workflow asynchronously."""
        workflow = self.active_workflows.get(workflow_id)
        if not workflow:
            return

        try:
            # Execute steps
            result = await self._execute_steps(workflow_id)

            # Update workflow state
            workflow["state"] = WorkflowState.COMPLETED
            workflow["end_time"] = datetime.now()
            workflow["final_result"] = result

            # Move to history
            self.workflow_history.append(workflow)
            del self.active_workflows[workflow_id]

            logger.info(f"[{self.agent_id}] Completed workflow {workflow_id}")

        except Exception as e:
            workflow["state"] = WorkflowState.FAILED
            workflow["errors"].append(str(e))
            logger.error(f"[{self.agent_id}] Workflow {workflow_id} failed: {e}")

    async def _execute_steps(self, workflow_id: str) -> Dict[str, Any]:
        """Execute workflow steps with parallel processing where possible."""
        workflow = self.active_workflows[workflow_id]
        steps = workflow["steps"]
        context = workflow["context"]

        results = {}

        # Group steps for parallel execution
        step_groups = self._group_parallel_steps(steps)

        for group in step_groups:
            if workflow["state"] != WorkflowState.IN_PROGRESS:
                break  # Cancelled

            # Execute steps in this group in parallel
            tasks = []
            for step in group:
                step_id = step.get("id", f"step_{len(results)}")
                task = asyncio.create_task(self._execute_single_step(workflow_id, step, context))
                tasks.append((step_id, task))

            # Wait for all steps in group to complete
            for step_id, task in tasks:
                try:
                    result = await asyncio.wait_for(task, timeout=self.config["timeout_per_step"])
                    results[step_id] = result
                    workflow["results"][step_id] = result
                except asyncio.TimeoutError:
                    results[step_id] = {"status": "timeout", "error": "Step timed out"}
                    workflow["errors"].append(f"Step {step_id} timed out")
                except Exception as e:
                    results[step_id] = {"status": "error", "error": str(e)}
                    workflow["errors"].append(f"Step {step_id} failed: {e}")

            workflow["current_step"] += len(group)

        return {"status": "completed", "results": results}

    async def _execute_single_step(
        self, workflow_id: str, step: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a single workflow step."""
        step_type = step.get("type")
        step_params = step.get("params", {})

        if step_type == "delegate":
            # Delegate to another agent
            target_agent = step_params.get("agent")
            message = step_params.get("message", {})

            if target_agent:
                # Send message and wait for response
                response = await self._send_and_wait(target_agent, message)
                return response

        elif step_type == "condition":
            # Evaluate condition
            condition = step_params.get("condition", "")
            result = await self._check_condition(condition, context, workflow_id)
            return {"status": "completed", "result": result}

        elif step_type == "delay":
            # Simple delay
            delay = step_params.get("seconds", 1)
            await asyncio.sleep(delay)
            return {"status": "completed"}

        else:
            return {"status": "error", "reason": f"Unknown step type: {step_type}"}

    async def _send_and_wait(self, target_agent: str, message: Dict[str, Any]) -> Dict[str, Any]:
        """Send message to agent and wait for response."""
        # Send message via MessageBus
        correlation_id = f"{self.agent_id}_{datetime.now().timestamp()}"
        message_with_id = {**message, "correlation_id": correlation_id}

        await self.message_bus.send(target_agent, message_with_id)

        # Wait for response (simplified - in full implementation would use correlation IDs)
        logger.info(f"[{self.agent_id}] Delegating to {target_agent}: {message}")
        # Placeholder response - in real implementation, would wait for response message
        return {"status": "completed", "response": f"Delegated to {target_agent}"}

    def _group_parallel_steps(self, steps: List[Dict]) -> List[List[Dict]]:
        """Group steps that can be executed in parallel based on dependencies."""
        groups = []
        current_group = []

        for step in steps:
            dependencies = step.get("depends_on", [])
            if dependencies:
                # If has dependencies, check if they are satisfied by current group
                dep_satisfied = all(dep in [s.get("id") for s in current_group] for dep in dependencies)
                if not dep_satisfied:
                    # Start new group
                    if current_group:
                        groups.append(current_group)
                        current_group = []
            current_group.append(step)

        if current_group:
            groups.append(current_group)

        return groups

    async def _check_condition(self, condition: str, context: Dict, workflow_id: str) -> bool:
        """Evaluate a simple condition."""
        # Basic condition evaluation
        if "==" in condition:
            left, right = condition.split("==", 1)
            left = left.strip()
            right = right.strip().strip('"').strip("'")
            return str(context.get(left, "")) == right

        # Context key existence check
        if condition.startswith("exists:"):
            key = condition[7:].strip()
            return key in context

        # Default to true for simple conditions
        return True
