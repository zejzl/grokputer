"""
Coordinator Agent for Grokputer Swarm

This agent serves as the central orchestrator for multi-agent tasks.
Responsibilities:
- Task decomposition (heuristic-based for Phase 1)
- Delegation to Observer/Actor via MessageBus
- Confirmation handling with safety scoring
- Result aggregation and validation
- Basic error recovery and timeouts

Extends BaseAgent for lifecycle management.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from enum import Enum

from src.core.base_agent import BaseAgent
from src.core.message_bus import MessageBus, Message, MessagePriority
from src.observability.session_logger import SessionLogger
from src import config

logger = logging.getLogger(__name__)

class TaskStatus(Enum):
    """Enum for task states."""
    PENDING = "pending"
    DECOMPOSED = "decomposed"
    DELEGATED = "delegated"
    AGGREGATING = "aggregating"
    COMPLETED = "completed"
    FAILED = "failed"

class Coordinator(BaseAgent):
    """
    Coordinator Agent: Orchestrates swarm tasks.

    - Decomposes high-level tasks into subtasks
    - Delegates to specialized agents (Observer, Actor)
    - Handles user confirmations for high-risk actions
    - Aggregates results and validates completion
    - Tracks SwarmMetrics for performance

    Phase 1: Simple heuristic decomposition (string matching).
    Phase 2: AI-based decomposition via Grok API.
    """

    def __init__(
        self,
        message_bus: MessageBus,
        session_logger: SessionLogger,
        config: Dict[str, Any],
        heartbeat_interval: float = 10.0
    ):
        super().__init__('coordinator', message_bus, session_logger, config, heartbeat_interval)
        self.active_tasks: Dict[str, Dict[str, Any]] = {}  # task_id -> task_info
        self.pending_responses: Dict[str, List[str]] = {}  # task_id -> expected_agent_ids

    async def process_message(self, message: Message) -> Optional[Dict]:
        """
        Process incoming messages and orchestrate swarm.

        Handles:
        - New task from user (type: 'new_task')
        - Responses from agents (type: 'response')
        - Errors/timeouts (type: 'error')

        Returns response or None (handled by BaseAgent loop).
        """
        msg_type = message.message_type
        task_id = message.content.get('task_id', 'default')

        if msg_type == 'new_task':
            return await self._handle_new_task(message, task_id)
        elif msg_type == 'response':
            return await self._handle_response(message, task_id)
        elif msg_type == 'error':
            return await self._handle_error(message, task_id)
        else:
            logger.warning(f"Unknown message type: {msg_type}")
            self.session_logger.log_agent_error(self.agent_id, f"Unknown type: {msg_type}")
            return None

    async def _handle_new_task(self, message: Message, task_id: str) -> Dict:
        """Decompose and delegate new task."""
        task_description = message.content.get('description', '')
        logger.info(f"New task received: {task_description}")

        # Update task state
        self.active_tasks[task_id] = {
            'status': TaskStatus.PENDING,
            'description': task_description,
            'subtasks': [],
            'results': {}
        }

        # Decompose (Phase 1: simple heuristics)
        subtasks = self._decompose_task(task_description)
        self.active_tasks[task_id]['subtasks'] = subtasks
        self.active_tasks[task_id]['status'] = TaskStatus.DECOMPOSED

        # Delegate subtasks
        responses = []
        for subtask in subtasks:
            delegated = await self._delegate_subtask(task_id, subtask)
            if delegated:
                responses.append(delegated)
            else:
                logger.error(f"Failed to delegate subtask: {subtask}")

        self.active_tasks[task_id]['status'] = TaskStatus.DELEGATED

        # Track metrics
        if self.session_logger.swarm_metrics:
            self.session_logger.swarm_metrics.coordinator_decisions += 1
            self.session_logger.swarm_metrics.task_decompositions += 1

        # Log decomposition
        logger.info(f"[Coordinator] Decomposed task {task_id} into {len(subtasks)} subtasks")

        return {
            'to': message.from_agent,
            'type': 'task_delegated',
            'content': {'task_id': task_id, 'subtasks': len(subtasks), 'status': 'delegated'},
            'priority': MessagePriority.NORMAL
        }

    def _decompose_task(self, task_description: str) -> List[Dict[str, Any]]:
        """
        Decompose task into subtasks (Phase 1: heuristic rules).

        Rules:
        - If 'screen' or 'observe' → Observer (capture)
        - If 'click', 'type', 'bash' → Actor (action)
        - Default: Split into observe + act

        Returns list of subtasks: [{'agent': 'observer', 'action': 'capture_screen'}]
        """
        subtasks = []
        task_lower = task_description.lower()

        # Heuristic decomposition
        if any(word in task_lower for word in ['screen', 'observe', 'see']):
            subtasks.append({
                'agent': 'observer',
                'action': 'capture_screen',
                'params': {}  # Default full screen (no region)
            })
        if any(word in task_lower for word in ['click', 'type', 'bash', 'execute']):
            subtasks.append({
                'agent': 'actor',
                'action': 'perform_action',
                'params': {'command': task_description}  # Pass task for Actor to parse
            })
        # Default: Observe first, then act
        if not subtasks:
            subtasks = [
                {'agent': 'observer', 'action': 'capture_screen', 'params': {}},
                {'agent': 'actor', 'action': 'perform_action', 'params': {'command': task_description}}
            ]

        logger.info(f"Decomposed '{task_description}' into {len(subtasks)} subtasks")
        return subtasks

    async def _delegate_subtask(self, task_id: str, subtask: Dict[str, Any]) -> Optional[Dict]:
        """Delegate subtask to target agent via MessageBus."""
        agent_id = subtask['agent']
        action = subtask['action']
        params = subtask.get('params', {})

        # Safety check for Actor actions
        if agent_id == 'actor' and self._requires_confirmation(action, params):
            confirmed = await self._request_confirmation(task_id, action, params)
            if not confirmed:
                logger.warning(f"Subtask rejected by user: {action}")
                self.session_logger.log_confirmation(self.agent_id, action, 85, False)
                return None

        # Send message to agent
        delegate_msg = Message(
            from_agent=self.agent_id,
            to_agent=agent_id,
            message_type='subtask',
            content={
                'task_id': task_id,
                'action': action,
                'params': params
            },
            priority=MessagePriority.HIGH if agent_id == 'actor' else MessagePriority.NORMAL
        )

        try:
            await self.message_bus.send(delegate_msg)
            logger.info(f"Delegated {action} to {agent_id} for task {task_id}")

            # Track expected response
            if task_id not in self.pending_responses:
                self.pending_responses[task_id] = []
            self.pending_responses[task_id].append(agent_id)

            # Log handoff
            self.session_logger.log_handoff(self.agent_id, agent_id, 0.0)  # Latency tracked later
            self.session_logger.log_message(self.agent_id, agent_id, 'subtask')

            return {'status': 'delegated', 'agent': agent_id, 'action': action}

        except Exception as e:
            logger.error(f"Delegation failed for {agent_id}: {e}")
            self.session_logger.log_agent_error(self.agent_id, f"Delegation error: {e}")
            return None

    def _requires_confirmation(self, action: str, params: Dict) -> bool:
        """Check if action needs user confirmation (safety scoring)."""
        # Simple heuristic for Phase 1
        risky_actions = ['bash', 'click', 'type']  # Expand with safety_scores
        if action in risky_actions:
            # Simulate safety score (integrate with config.py in Phase 2)
            score = 50  # Placeholder; use calculate_safety_score(params.get('command'))
            return score > 70
        return False

    async def _request_confirmation(self, task_id: str, action: str, params: Dict) -> bool:
        """Request user confirmation for high-risk actions."""
        print(f"[CONFIRM] Coordinator: Proposed action '{action}' for task {task_id}")
        print(f"Details: {params}")
        print("Safety Score: 85/100 [HIGH RISK]")  # Placeholder

        # Async-friendly input (use asyncio.to_thread for real input)
        response = await asyncio.to_thread(input, "Approve? (y/n): ")
        approved = response.strip().lower() == 'y'

        self.session_logger.log_confirmation(task_id, action, 85, approved)  # Score placeholder
        return approved

    async def _handle_response(self, message: Message, task_id: str) -> Optional[Dict]:
        """Aggregate responses from agents."""
        if task_id not in self.active_tasks:
            logger.warning(f"Unknown task_id in response: {task_id}")
            return None

        agent_id = message.from_agent
        response_content = message.content
        self.active_tasks[task_id]['results'][agent_id] = response_content
        self.pending_responses[task_id].remove(agent_id)

        logger.info(f"Received response from {agent_id} for task {task_id}")

        # Check if all responses received
        if not self.pending_responses.get(task_id):
            final_result = await self._aggregate_and_validate(task_id)
            self.active_tasks[task_id]['status'] = TaskStatus.COMPLETED
            del self.active_tasks[task_id]
            del self.pending_responses[task_id]

            logger.info(f"[Coordinator] Task {task_id} completed: {final_result['summary']}")

            return {
                'to': 'user',  # Or original sender
                'type': 'task_complete',
                'content': {'task_id': task_id, 'result': final_result},
                'priority': MessagePriority.NORMAL
            }

        self.active_tasks[task_id]['status'] = TaskStatus.AGGREGATING
        return None

    async def _aggregate_and_validate(self, task_id: str) -> Dict[str, Any]:
        """Aggregate results and perform basic validation."""
        results = self.active_tasks[task_id]['results']
        description = self.active_tasks[task_id]['description']

        # Simple validation (Phase 1: check for errors)
        aggregated = {
            'task': description,
            'agents_involved': list(results.keys()),
            'raw_results': results,
            'success': all('error' not in res for res in results.values()),
            'summary': 'All subtasks completed successfully' if all('error' not in res for res in results.values()) else 'Partial failure detected'
        }

        if not aggregated['success']:
            logger.warning(f"Task {task_id} partial failure: {aggregated['summary']}")
            aggregated['recovery_suggestion'] = 'Retry failed subtasks'  # Phase 2: auto-retry

        logger.info(f"Aggregated results for task {task_id}: {aggregated['summary']}")
        return aggregated

    async def _handle_error(self, message: Message, task_id: str) -> Optional[Dict]:
        """Handle errors from agents (basic recovery)."""
        if task_id in self.active_tasks:
            self.active_tasks[task_id]['status'] = TaskStatus.FAILED
            error = message.content.get('error', 'Unknown error')
            self.session_logger.log_agent_error(self.agent_id, f"Task {task_id} failed: {error}")

            # Simple recovery: Log and notify (Phase 2: retry logic)
            logger.error(f"Task {task_id} failed: {error}")

            return {
                'to': 'user',
                'type': 'task_failed',
                'content': {'task_id': task_id, 'error': error},
                'priority': MessagePriority.HIGH
            }

        return None

    async def on_stop(self):
        """Graceful shutdown: Handle pending tasks."""
        for task_id in list(self.active_tasks.keys()):
            if self.active_tasks[task_id]['status'] in [TaskStatus.DELEGATED, TaskStatus.AGGREGATING]:
                logger.warning(f"Task {task_id} interrupted during shutdown")
                self.session_logger.log_agent_activity(self.agent_id, f"interrupted_{task_id}")

        logger.info("Coordinator shutdown complete")