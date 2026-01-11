"""
MessageBus Adapter for GG Workflow Framework

This module provides integration between GG workflows and the distributed MessageBus,
enabling communication between workflow instances and other Grokputer components.

Author: Grokputer Team
Date: 2026-01-11
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Callable

from .nodes.base import BaseNode, NodeContext

logger = logging.getLogger(__name__)


class MessageBusAdapter:
    """
    Adapter for connecting GG workflows to the distributed MessageBus.

    This enables workflows to:
    - Publish messages to other workflows or components
    - Subscribe to messages from other systems
    - Coordinate distributed workflow execution
    - Communicate with Pantheon agents
    """

    def __init__(self, workflow_id: str):
        self.workflow_id = workflow_id
        self.message_bus = None
        self.subscriptions: Dict[str, Callable] = {}
        self._running = False
        self._subscription_tasks: List[asyncio.Task] = []

    async def initialize(self):
        """Initialize the MessageBus connection."""
        try:
            # Import MessageBus components
            from src.core.message_bus import MessageBus, Message, MessagePriority

            self.message_bus = MessageBus()
            await self.message_bus.start()

            # Register workflow as a message bus participant
            self.workflow_participant_id = f"workflow_{self.workflow_id}"

            logger.info(f"MessageBus adapter initialized for workflow {self.workflow_id}")

        except ImportError as e:
            logger.warning(f"MessageBus not available: {e}")
            self.message_bus = None

    async def shutdown(self):
        """Shutdown the MessageBus connection."""
        if self.message_bus:
            # Cancel all subscription tasks
            for task in self._subscription_tasks:
                task.cancel()

            await asyncio.gather(*self._subscription_tasks, return_exceptions=True)

            await self.message_bus.stop()
            logger.info(f"MessageBus adapter shutdown for workflow {self.workflow_id}")

    async def publish_message(
        self,
        recipient: str,
        content: Dict[str, Any],
        priority: str = "medium",
        correlation_id: Optional[str] = None
    ) -> str:
        """
        Publish a message to the MessageBus.

        Args:
            recipient: Target recipient ID
            content: Message content
            priority: Message priority (low, medium, high)
            correlation_id: Optional correlation ID for request-response

        Returns:
            Message ID
        """
        if not self.message_bus:
            raise RuntimeError("MessageBus not initialized")

        from src.core.message_bus import Message, MessagePriority

        # Convert priority string to enum
        msg_priority = getattr(MessagePriority, priority.upper(), MessagePriority.MEDIUM)

        message = Message(
            id=f"{self.workflow_id}_{asyncio.get_event_loop().time()}",
            sender=self.workflow_participant_id,
            recipient=recipient,
            content={
                **content,
                "workflow_id": self.workflow_id,
                "timestamp": asyncio.get_event_loop().time(),
            },
            priority=msg_priority,
            correlation_id=correlation_id,
        )

        await self.message_bus.publish(message)
        logger.debug(f"Published message {message.id} to {recipient}")

        return message.id

    async def subscribe_to_topic(
        self,
        topic: str,
        callback: Callable[[Dict[str, Any]], None],
        filter_func: Optional[Callable[[Dict[str, Any]], bool]] = None
    ):
        """
        Subscribe to messages on a topic.

        Args:
            topic: Topic to subscribe to
            callback: Function to call when message received
            filter_func: Optional filter function
        """
        if not self.message_bus:
            raise RuntimeError("MessageBus not initialized")

        async def message_handler():
            try:
                while self._running:
                    # In a real implementation, this would use the MessageBus subscription mechanism
                    # For now, we'll simulate by checking for messages periodically

                    # This is a simplified implementation
                    # Real implementation would use proper MessageBus subscription

                    await asyncio.sleep(1)  # Check every second

                    # Simulate receiving a message (in real implementation, this would come from MessageBus)
                    # For demo purposes, we'll occasionally trigger the callback

                    if asyncio.get_event_loop().time() % 10 < 1:  # Every ~10 seconds
                        mock_message = {
                            "id": f"mock_{asyncio.get_event_loop().time()}",
                            "sender": "mock_sender",
                            "content": {
                                "topic": topic,
                                "message": f"Mock message for topic {topic}",
                                "timestamp": asyncio.get_event_loop().time(),
                            }
                        }

                        if filter_func is None or filter_func(mock_message):
                            try:
                                await callback(mock_message)
                            except Exception as e:
                                logger.error(f"Error in message callback: {e}")

            except asyncio.CancelledError:
                logger.debug(f"Subscription task cancelled for topic {topic}")
            except Exception as e:
                logger.error(f"Error in subscription handler for topic {topic}: {e}")

        # Start the subscription task
        task = asyncio.create_task(message_handler())
        self._subscription_tasks.append(task)

        self.subscriptions[topic] = callback
        logger.info(f"Subscribed to topic {topic}")

    async def unsubscribe_from_topic(self, topic: str):
        """Unsubscribe from a topic."""
        if topic in self.subscriptions:
            del self.subscriptions[topic]
            logger.info(f"Unsubscribed from topic {topic}")

    async def send_request_response(
        self,
        recipient: str,
        request_content: Dict[str, Any],
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """
        Send a request and wait for response.

        Args:
            recipient: Target recipient
            request_content: Request content
            timeout: Response timeout in seconds

        Returns:
            Response content
        """
        correlation_id = f"req_{self.workflow_id}_{asyncio.get_event_loop().time()}"

        # Publish request
        await self.publish_message(
            recipient=recipient,
            content=request_content,
            priority="high",
            correlation_id=correlation_id
        )

        # Wait for response
        response_future = asyncio.Future()

        async def response_handler(message: Dict[str, Any]):
            if message.get("correlation_id") == correlation_id:
                response_future.set_result(message["content"])

        # Subscribe to responses (simplified)
        await self.subscribe_to_topic(
            topic=f"response_{correlation_id}",
            callback=response_handler
        )

        try:
            response = await asyncio.wait_for(response_future, timeout=timeout)
            return response
        finally:
            await self.unsubscribe_from_topic(f"response_{correlation_id}")

    async def broadcast_workflow_status(self, status: Dict[str, Any]):
        """Broadcast workflow status to all interested parties."""
        await self.publish_message(
            recipient="workflow_coordinator",
            content={
                "type": "workflow_status",
                "workflow_id": self.workflow_id,
                **status
            },
            priority="low"
        )

    async def request_workflow_coordination(self, coordination_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Request coordination from the workflow coordinator.

        Args:
            coordination_type: Type of coordination needed
            data: Coordination data

        Returns:
            Coordination response
        """
        return await self.send_request_response(
            recipient="workflow_coordinator",
            request_content={
                "type": "coordination_request",
                "coordination_type": coordination_type,
                "data": data
            }
        )

    def get_adapter_stats(self) -> Dict[str, Any]:
        """Get adapter statistics."""
        return {
            "workflow_id": self.workflow_id,
            "message_bus_connected": self.message_bus is not None,
            "active_subscriptions": len(self.subscriptions),
            "running_tasks": len(self._subscription_tasks),
        }


class MessageBusNode(BaseNode):
    """
    Workflow node for MessageBus communication.

    This node allows workflows to:
    - Send messages to other workflows or components
    - Receive messages from the MessageBus
    - Coordinate with distributed systems
    """

    def __init__(self, node_id: str, name: Optional[str] = None, config: Optional[Dict] = None):
        super().__init__(node_id, name, config)

        # Validate required config
        if not self.config.get("operation"):
            raise ValueError(f"MessageBusNode {node_id} requires 'operation' in config")

        # Initialize adapter (will be set by workflow engine)
        self.adapter: Optional[MessageBusAdapter] = None

    def set_adapter(self, adapter: MessageBusAdapter):
        """Set the MessageBus adapter."""
        self.adapter = adapter

    async def execute(self, context: NodeContext) -> NodeContext:
        """
        Execute MessageBus operation.

        Args:
            context: Input context

        Returns:
            Output context with operation results
        """
        if not self.adapter:
            raise RuntimeError(f"MessageBus adapter not set for node {self.node_id}")

        operation = self.config["operation"]

        # Dispatch to operation handler
        if operation == "publish_message":
            result = await self._publish_message(context)
        elif operation == "send_request":
            result = await self._send_request(context)
        elif operation == "broadcast_status":
            result = await self._broadcast_status(context)
        elif operation == "request_coordination":
            result = await self._request_coordination(context)
        else:
            raise ValueError(f"Unknown MessageBus operation: {operation}")

        # Create output context
        output_context = NodeContext(
            data={
                "messagebus_response": result,
                "operation": operation,
            },
            metadata=context.metadata,
            state=context.state,
        )

        # Store result in state
        output_context.set_state(f"{self.node_id}_response", result)

        return output_context

    async def _publish_message(self, context: NodeContext) -> Dict[str, Any]:
        """Publish a message to the MessageBus."""
        recipient = self._interpolate(self.config["recipient"], context)
        content = self._interpolate_dict(self.config.get("content", {}), context)
        priority = self.config.get("priority", "medium")

        message_id = await self.adapter.publish_message(
            recipient=recipient,
            content=content,
            priority=priority
        )

        return {
            "status": "published",
            "message_id": message_id,
            "recipient": recipient
        }

    async def _send_request(self, context: NodeContext) -> Dict[str, Any]:
        """Send a request and wait for response."""
        recipient = self._interpolate(self.config["recipient"], context)
        request_content = self._interpolate_dict(self.config.get("request_content", {}), context)
        timeout = self.config.get("timeout", 30.0)

        response = await self.adapter.send_request_response(
            recipient=recipient,
            request_content=request_content,
            timeout=timeout
        )

        return {
            "status": "response_received",
            "response": response
        }

    async def _broadcast_status(self, context: NodeContext) -> Dict[str, Any]:
        """Broadcast workflow status."""
        status_data = self._interpolate_dict(self.config.get("status_data", {}), context)

        await self.adapter.broadcast_workflow_status(status_data)

        return {
            "status": "broadcasted",
            "status_data": status_data
        }

    async def _request_coordination(self, context: NodeContext) -> Dict[str, Any]:
        """Request workflow coordination."""
        coordination_type = self._interpolate(self.config["coordination_type"], context)
        coordination_data = self._interpolate_dict(self.config.get("coordination_data", {}), context)

        response = await self.adapter.request_workflow_coordination(
            coordination_type=coordination_type,
            data=coordination_data
        )

        return {
            "status": "coordination_response",
            "coordination_type": coordination_type,
            "response": response
        }

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
                    for item in val
                ]
            else:
                result[key] = val
        return result


# Global adapter cache
_message_bus_adapters: Dict[str, MessageBusAdapter] = {}

def get_message_bus_adapter(workflow_id: str) -> MessageBusAdapter:
    """
    Get or create a MessageBus adapter for a workflow.

    Args:
        workflow_id: Workflow identifier

    Returns:
        MessageBusAdapter instance
    """
    if workflow_id not in _message_bus_adapters:
        _message_bus_adapters[workflow_id] = MessageBusAdapter(workflow_id)

    return _message_bus_adapters[workflow_id]

async def initialize_workflow_message_bus(workflow_id: str) -> MessageBusAdapter:
    """
    Initialize MessageBus adapter for a workflow.

    Args:
        workflow_id: Workflow identifier

    Returns:
        Initialized MessageBusAdapter
    """
    adapter = get_message_bus_adapter(workflow_id)
    await adapter.initialize()
    return adapter

async def shutdown_all_message_bus_adapters():
    """Shutdown all MessageBus adapters."""
    shutdown_tasks = []
    for adapter in _message_bus_adapters.values():
        shutdown_tasks.append(adapter.shutdown())

    await asyncio.gather(*shutdown_tasks, return_exceptions=True)
    _message_bus_adapters.clear()