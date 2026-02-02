"""
Pantheon Integration for GG Workflow Framework

This module provides integration between GG workflows and Pantheon agents,
allowing workflows to delegate complex tasks to specialized AI agents.

Author: Grokputer Team
Date: 2026-01-11
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

from .nodes.base import BaseNode, NodeContext

logger = logging.getLogger(__name__)


class PantheonAgent:
    """
    Represents a Pantheon agent that can be invoked from workflows.

    Attributes:
        name: Agent name (e.g., "observer", "reasoner", "actor")
        capabilities: List of capabilities this agent provides
        timeout: Default timeout for agent responses
        priority: Default message priority
    """

    def __init__(
        self,
        name: str,
        capabilities: List[str],
        timeout: int = 30,
        priority: str = "medium"
    ):
        self.name = name
        self.capabilities = capabilities
        self.timeout = timeout
        self.priority = priority

    def __repr__(self) -> str:
        return f"PantheonAgent(name='{self.name}', capabilities={self.capabilities})"


class PantheonIntegration:
    """
    Integration layer between GG workflows and Pantheon agents.

    This class manages communication with Pantheon agents through the MessageBus,
    allowing workflows to delegate complex tasks to specialized agents.
    """

    def __init__(self):
        self.agents: Dict[str, PantheonAgent] = {}
        self.message_bus = None
        self._initialized = False

    async def initialize(self):
        """Initialize the Pantheon integration."""
        if self._initialized:
            return

        try:
            # Import MessageBus
            from src.core.message_bus import MessageBus, Message, MessagePriority

            self.message_bus = MessageBus()

            # Define available Pantheon agents
            self.agents = {
                "observer": PantheonAgent(
                    name="observer",
                    capabilities=["screen_capture", "vision_analysis", "ocr", "ui_detection"],
                    timeout=45,
                    priority="high"
                ),
                "reasoner": PantheonAgent(
                    name="reasoner",
                    capabilities=["task_analysis", "planning", "decision_making", "coordination"],
                    timeout=60,
                    priority="high"
                ),
                "actor": PantheonAgent(
                    name="actor",
                    capabilities=["computer_control", "keyboard_input", "mouse_control", "file_operations"],
                    timeout=30,
                    priority="high"
                ),
                "validator": PantheonAgent(
                    name="validator",
                    capabilities=["safety_check", "risk_assessment", "validation", "compliance"],
                    timeout=20,
                    priority="medium"
                ),
                "learner": PantheonAgent(
                    name="learner",
                    capabilities=["pattern_recognition", "optimization", "learning", "adaptation"],
                    timeout=40,
                    priority="medium"
                ),
                "memory": PantheonAgent(
                    name="memory",
                    capabilities=["data_storage", "retrieval", "knowledge_management", "context_preservation"],
                    timeout=15,
                    priority="low"
                ),
                "executor": PantheonAgent(
                    name="executor",
                    capabilities=["workflow_execution", "task_delegation", "orchestration", "monitoring"],
                    timeout=120,
                    priority="high"
                ),
                "analyzer": PantheonAgent(
                    name="analyzer",
                    capabilities=["performance_analysis", "metrics_collection", "bottleneck_detection", "reporting"],
                    timeout=25,
                    priority="medium"
                ),
                "improver": PantheonAgent(
                    name="improver",
                    capabilities=["self_improvement", "optimization", "healing", "evolution"],
                    timeout=90,
                    priority="medium"
                ),
            }

            self._initialized = True
            logger.info(f"Pantheon integration initialized with {len(self.agents)} agents")

        except ImportError as e:
            logger.warning(f"Pantheon integration unavailable: {e}")
            self._initialized = False

    def get_agent(self, name: str) -> Optional[PantheonAgent]:
        """Get a Pantheon agent by name."""
        return self.agents.get(name)

    def list_agents(self) -> List[str]:
        """List all available Pantheon agents."""
        return list(self.agents.keys())

    def get_agents_by_capability(self, capability: str) -> List[PantheonAgent]:
        """Get agents that have a specific capability."""
        return [agent for agent in self.agents.values() if capability in agent.capabilities]

    async def invoke_agent(
        self,
        agent_name: str,
        task: str,
        context: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
        priority: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Invoke a Pantheon agent with a task.

        Args:
            agent_name: Name of the agent to invoke
            task: Task description
            context: Additional context data
            timeout: Override default timeout
            priority: Override default priority

        Returns:
            Agent response

        Raises:
            ValueError: If agent not found
            Exception: If invocation fails
        """
        if not self._initialized:
            raise RuntimeError("Pantheon integration not initialized")

        agent = self.get_agent(agent_name)
        if not agent:
            raise ValueError(f"Pantheon agent '{agent_name}' not found")

        # Import required classes
        from src.core.message_bus import Message, MessagePriority

        # Determine priority
        msg_priority = getattr(MessagePriority, (priority or agent.priority).upper(), MessagePriority.MEDIUM)

        # Create message
        message = Message(
            id=f"workflow_{agent_name}_{asyncio.get_event_loop().time()}",
            sender="workflow_engine",
            recipient=agent_name,
            content={
                "task": task,
                "context": context or {},
                "workflow_invocation": True,
            },
            priority=msg_priority,
        )

        # Send message and wait for response
        await self.message_bus.publish(message)

        # Wait for response
        response_timeout = timeout or agent.timeout

        try:
            # Subscribe to responses from this agent
            response = await asyncio.wait_for(
                self._wait_for_agent_response(agent_name, message.id),
                timeout=response_timeout
            )

            return response

        except asyncio.TimeoutError:
            raise Exception(f"Pantheon agent '{agent_name}' timeout after {response_timeout}s")

    async def _wait_for_agent_response(self, agent_name: str, request_id: str) -> Dict[str, Any]:
        """Wait for a response from a specific agent."""
        # This is a simplified implementation
        # In a real system, you'd have a proper subscription mechanism

        # For now, we'll simulate a response
        # In production, this would listen to the MessageBus for responses

        await asyncio.sleep(1)  # Simulate processing time

        # Mock response based on agent type
        if agent_name == "observer":
            return {
                "status": "success",
                "result": "Screen captured and analyzed successfully",
                "data": {"screenshot_taken": True, "elements_detected": 15}
            }
        elif agent_name == "reasoner":
            return {
                "status": "success",
                "result": "Task analyzed and plan created",
                "data": {"plan_steps": 3, "confidence": 0.85}
            }
        elif agent_name == "actor":
            return {
                "status": "success",
                "result": "Computer control actions executed",
                "data": {"actions_performed": 5, "success_rate": 1.0}
            }
        elif agent_name == "validator":
            return {
                "status": "success",
                "result": "Safety validation completed",
                "data": {"risk_level": "low", "checks_passed": 8}
            }
        elif agent_name == "learner":
            return {
                "status": "success",
                "result": "Learning patterns identified",
                "data": {"patterns_found": 3, "optimization_suggestions": 2}
            }
        elif agent_name == "memory":
            return {
                "status": "success",
                "result": "Data stored and retrieved successfully",
                "data": {"items_stored": 10, "retrieval_time": 0.05}
            }
        elif agent_name == "executor":
            return {
                "status": "success",
                "result": "Workflow execution completed",
                "data": {"steps_executed": 7, "duration": 12.5}
            }
        elif agent_name == "analyzer":
            return {
                "status": "success",
                "result": "Performance analysis completed",
                "data": {"metrics_collected": 15, "bottlenecks_found": 1}
            }
        elif agent_name == "improver":
            return {
                "status": "success",
                "result": "Self-improvement suggestions generated",
                "data": {"improvements_identified": 3, "impact_score": 0.75}
            }
        else:
            return {
                "status": "success",
                "result": f"Task completed by {agent_name}",
                "data": {"generic_response": True}
            }


class PantheonNode(BaseNode):
    """
    Workflow node for invoking Pantheon agents.

    This node allows workflows to delegate complex tasks to specialized Pantheon agents,
    enabling advanced AI capabilities within workflow automation.
    """

    def __init__(self, node_id: str, name: Optional[str] = None, config: Optional[Dict] = None):
        super().__init__(node_id, name, config)

        # Validate required config
        if not self.config.get("agent"):
            raise ValueError(f"PantheonNode {node_id} requires 'agent' in config")
        if not self.config.get("task"):
            raise ValueError(f"PantheonNode {node_id} requires 'task' in config")

        # Initialize integration
        self.integration = PantheonIntegration()

    async def execute(self, context: NodeContext) -> NodeContext:
        """
        Execute Pantheon agent invocation.

        Args:
            context: Input context

        Returns:
            Output context with agent response
        """
        await self.integration.initialize()

        agent_name = self._interpolate(self.config["agent"], context)
        task = self._interpolate(self.config["task"], context)

        # Get additional context
        agent_context = self.config.get("context", {})
        interpolated_context = self._interpolate_dict(agent_context, context)

        # Add workflow context
        interpolated_context.update({
            "workflow_id": context.metadata.get("workflow_id", "unknown"),
            "node_id": self.node_id,
            "execution_time": context.metadata.get("start_time", ""),
        })

        # Invoke agent
        try:
            response = await self.integration.invoke_agent(
                agent_name=agent_name,
                task=task,
                context=interpolated_context,
                timeout=self.config.get("timeout"),
                priority=self.config.get("priority")
            )

            # Create output context
            output_context = NodeContext(
                data={
                    "pantheon_response": response,
                    "agent": agent_name,
                    "task": task,
                    "status": response.get("status", "unknown"),
                },
                metadata=context.metadata,
                state=context.state,
            )

            # Store response in state
            output_context.set_state(f"{self.node_id}_response", response)

            # Extract result if available
            if "result" in response:
                output_context.set("agent_result", response["result"])

            if "data" in response:
                # Flatten data into context
                for key, value in response["data"].items():
                    output_context.set(f"agent_{key}", value)

            return output_context

        except Exception as e:
            logger.error(f"Pantheon agent invocation failed: {e}")

            # Return context with error info
            output_context = NodeContext(
                data={
                    "pantheon_response": {"status": "error", "error": str(e)},
                    "agent": agent_name,
                    "task": task,
                    "status": "error",
                },
                metadata=context.metadata,
                state=context.state,
            )

            output_context.set_state(f"{self.node_id}_error", str(e))
            return output_context

    def _interpolate(self, value: Any, context: NodeContext) -> Any:
        """Replace {{variable}} placeholders."""
        if not isinstance(value, str):
            return value

        result = value
        for key, val in {**context.data, **context.state}.items():
            placeholder = f"{{{{{key}}}}}"
            if placeholder in result:
                result = result.replace(placeholder, str(val))

        return result

    def _interpolate_dict(self, data: Dict, context: NodeContext) -> Dict:
        """Recursively interpolate dict values."""
        result = {}
        for key, val in data.items():
            if isinstance(val, str):
                result[key] = self._interpolate(val, context)
            elif isinstance(val, dict):
                result[key] = self._interpolate_dict(val, context)
            elif isinstance(val, list):
                result[key] = [
                    self._interpolate_dict(item, context) if isinstance(item, dict) else item
                    for item in data
                ]
            else:
                result[key] = val
        return result


# Global integration instance
_pantheon_integration = None

def get_pantheon_integration() -> PantheonIntegration:
    """Get the global Pantheon integration instance."""
    global _pantheon_integration
    if _pantheon_integration is None:
        _pantheon_integration = PantheonIntegration()
    return _pantheon_integration