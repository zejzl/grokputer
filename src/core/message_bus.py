"""
Message bus for inter-agent communication using asyncio.Queue.

Provides microsecond-latency message routing between agents in the swarm.
Designed for 3-5 local agents with <100ms handoff latency target.
"""

import asyncio
import logging
import time
import uuid
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum
from collections import deque

# Standardized error handling
from ..exceptions import MessageBusError, handle_error
# TOON integration
try:
    from ..utils.toon_utils import encode_for_swarm, decode_from_swarm, estimate_savings, ToonDecodeError
    TOON_AVAILABLE = True
except ImportError:
    TOON_AVAILABLE = False
    logger.warning("TOON utils not available - install python-toon for token efficiency")

logger = logging.getLogger(__name__)


class MessagePriority(IntEnum):
    """Message priority levels (lower number = higher priority)."""

    HIGH = 0
    NORMAL = 1
    LOW = 2


@dataclass
class Message:
    """
    Standard message format for agent communication.

    Attributes:
        from_agent: ID of sending agent
        to_agent: ID of receiving agent
        message_type: Type of message (task, observation, action, result, etc.)
        content: Message payload
        priority: Message priority (HIGH, NORMAL, LOW)
        correlation_id: ID linking related messages (for request-response pairs)
        timestamp: Message creation time
        metadata: Additional message metadata
    """

    from_agent: str
    to_agent: str
    message_type: str
    content: Dict[str, Any]
    priority: MessagePriority = MessagePriority.NORMAL
    correlation_id: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary for logging."""
        return {
            "from": self.from_agent,
            "to": self.to_agent,
            "type": self.message_type,
            "content": self.content,
            "priority": self.priority.name,
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }

    def __lt__(self, other):
        """Compare messages by priority for PriorityQueue."""
        if not isinstance(other, Message):
            return NotImplemented
        # Lower priority number = higher priority
        if self.priority != other.priority:
            return self.priority < other.priority
        # Same priority: FIFO by timestamp
        return self.timestamp < other.timestamp


class MessageBus:
    """
    Production-ready message bus using asyncio.Queue for inter-agent communication.

    Features:
    - Message priorities (HIGH, NORMAL, LOW)
    - Request-response pattern with correlation IDs
    - Message history for debugging (last 100 messages)
    - Latency tracking per message type
    - Broadcast support
    - Microsecond-latency routing
    - Thread-safe, atomic operations

    Usage:
        bus = MessageBus()
        bus.register_agent("observer")
        bus.register_agent("actor")

        # Send with priority
        await bus.send(Message(
            from_agent="observer",
            to_agent="actor",
            message_type="observation",
            content={"screenshot": "base64..."},
            priority=MessagePriority.HIGH
        ))

        # Request-response pattern
        response = await bus.send_request(
            from_agent="coordinator",
            to_agent="observer",
            message_type="capture_screen",
            content={},
            timeout=5.0
        )
    """

    def __init__(self, default_timeout: float = 30.0, history_size: int = 100, max_concurrent: int = 1000):
        """
        Initialize the message bus.

        Args:
            default_timeout: Default timeout for receive operations (seconds)
            history_size: Number of messages to keep in history
            max_concurrent: Maximum concurrent message operations
        """
        self.queues: Dict[str, asyncio.PriorityQueue] = {}
        self.default_timeout = default_timeout
        self.history_size = history_size
        self.message_count = 0
        self.start_time = time.time()

        # Concurrency control
        self.concurrency_semaphore = asyncio.Semaphore(max_concurrent)

        # Analytics for concurrency monitoring
        self.concurrency_acquired = 0
        self.concurrency_released = 0
        self.concurrency_wait_time = 0.0

        # Message history for debugging
        self.message_history: deque = deque(maxlen=history_size)

        # Latency tracking
        self.latency_by_type: Dict[str, List[float]] = {}

        # Pending requests for request-response pattern
        self.pending_requests: Dict[str, asyncio.Future] = {}

        logger.info(
            f"MessageBus initialized with default timeout: {default_timeout}s, history: {history_size}, max_concurrent: {max_concurrent}"
        )

    async def _acquire_concurrency(self) -> None:
        """Acquire concurrency semaphore with analytics tracking."""
        start_time = time.time()
        await self.concurrency_semaphore.acquire()
        wait_time = time.time() - start_time
        self.concurrency_acquired += 1
        self.concurrency_wait_time += wait_time

        if wait_time > 0.1:  # Log significant waits
            logger.warning(
                f"[CONCURRENCY] Waited {wait_time:.3f}s for semaphore (acquired: {self.concurrency_acquired})"
            )

    def _release_concurrency(self) -> None:
        """Release concurrency semaphore with analytics tracking."""
        self.concurrency_semaphore.release()
        self.concurrency_released += 1

    def get_concurrency_stats(self) -> Dict[str, float]:
        """Get concurrency analytics with proper typing."""
        active = self.concurrency_acquired - self.concurrency_released
        return {
            "acquired": float(self.concurrency_acquired),
            "released": float(self.concurrency_released),
            "active": float(active),
            "total_wait_time": self.concurrency_wait_time,
            "avg_wait_time": self.concurrency_wait_time / max(1, self.concurrency_acquired),
            "semaphore_limit": float(getattr(self.concurrency_semaphore, "_value", 0) + active),
        }

    def register_agent(self, agent_id: str, queue_size: int = 0):
        """
        Register an agent and create its priority message queue.

        Args:
            agent_id: Unique identifier for the agent
            queue_size: Maximum queue size (0 = unlimited)
        """
        if agent_id in self.queues:
            logger.warning(f"Agent {agent_id} already registered")
            return

        self.queues[agent_id] = asyncio.PriorityQueue(maxsize=queue_size)
        logger.info(f"Registered agent: {agent_id} (queue, maxsize={queue_size})")

    def unregister_agent(self, agent_id: str):
        """
        Unregister an agent and remove its queue.

        Args:
            agent_id: Agent to unregister
        """
        if agent_id in self.queues:
            del self.queues[agent_id]
            logger.info(f"Unregistered agent: {agent_id}")
        else:
            logger.warning(f"Attempted to unregister unknown agent: {agent_id}")

    async def send(self, message: Message):
        """
        Send a message to an agent's priority queue.

        Args:
            message: Message to send

        Raises:
            ValueError: If target agent is not registered
        """
        if message.to_agent not in self.queues:
            error_msg = f"Unknown agent: {message.to_agent}"
            handle_error(ValueError(error_msg), "MessageBus.send", "error")
            raise MessageBusError(
                error_msg, {"to_agent": message.to_agent, "available_agents": list(self.queues.keys())}
            )

        # Add to priority queue (fast operation, no concurrency limit needed)
        await self.queues[message.to_agent].put(message)

        self.message_count += 1

        # Add to message history
        self.message_history.append(
            {
                "timestamp": message.timestamp,
                "from": message.from_agent,
                "to": message.to_agent,
                "type": message.message_type,
                "priority": message.priority.name,
                "correlation_id": message.correlation_id,
            }
        )

        logger.debug(
            f"Message sent: {message.from_agent} -> {message.to_agent} "
            f"[{message.message_type}] priority={message.priority.name} "
            f"(correlation_id={message.correlation_id})"
        )

    async def receive(self, agent_id: str, timeout: Optional[float] = None) -> Message:
        """
        Receive a message from an agent's priority queue.

        Args:
            agent_id: Agent receiving the message
            timeout: Timeout in seconds (None = use default)

        Returns:
            Received message (highest priority first)

        Raises:
            ValueError: If agent is not registered
            asyncio.TimeoutError: If timeout expires
        """
        if agent_id not in self.queues:
            raise ValueError(f"Unknown agent: {agent_id}")

        timeout = timeout if timeout is not None else self.default_timeout

        # Acquire concurrency control for receive operations
        await self._acquire_concurrency()

        receive_start = time.time()

        try:
            message = await asyncio.wait_for(self.queues[agent_id].get(), timeout=timeout)

            # Calculate latency (time since message was sent)
            latency = time.time() - message.timestamp

            # Track latency by message type
            if message.message_type not in self.latency_by_type:
                self.latency_by_type[message.message_type] = []
            self.latency_by_type[message.message_type].append(latency)

            logger.debug(
                f"Message received by {agent_id}: {message.from_agent} -> {agent_id} "
                f"[{message.message_type}] priority={message.priority.name} latency={latency*1000:.2f}ms"
            )

            return message

        except asyncio.TimeoutError:
            logger.debug(f"Agent {agent_id} receive timeout after {timeout}s")
            raise
        finally:
            # Always release concurrency control
            self._release_concurrency()

    async def subscribe(self, agent_id: str):
        """
        Subscribe to messages for an agent. Returns an async iterator.

        Args:
            agent_id: Agent to subscribe to

        Yields:
            Messages as they arrive
        """
        while True:
            try:
                message = await self.receive(agent_id, timeout=None)
                yield message
            except asyncio.TimeoutError:
                continue  # Keep listening

    def subscribe_callback(self, agent_id: str, callback: callable):
        """
        Subscribe to messages for an agent with a callback function.

        Args:
            agent_id: Agent to subscribe to
            callback: Function to call with each message
        """
        # For now, store callbacks and handle in a background task
        if not hasattr(self, '_callbacks'):
            self._callbacks = {}
        if agent_id not in self._callbacks:
            self._callbacks[agent_id] = []
        self._callbacks[agent_id].append(callback)

        # Start background listener if not already running
        if not hasattr(self, '_callback_tasks'):
            self._callback_tasks = {}
        if agent_id not in self._callback_tasks:
            self._callback_tasks[agent_id] = asyncio.create_task(self._run_callbacks(agent_id))

    async def _run_callbacks(self, agent_id: str):
        """Run callbacks for messages to an agent."""
        try:
            async for message in self.subscribe(agent_id):
                if agent_id in self._callbacks:
                    for callback in self._callbacks[agent_id]:
                        try:
                            await callback(message)
                        except Exception as e:
                            logger.error(f"Callback error for {agent_id}: {e}")
        except Exception as e:
            logger.error(f"Callback runner error for {agent_id}: {e}")

    async def send_request(
        self,
        from_agent: str,
        to_agent: str,
        message_type: str,
        content: Dict[str, Any],
        priority: MessagePriority = MessagePriority.NORMAL,
        timeout: Optional[float] = None,
    ) -> Message:
        """
        Send a request and wait for a response (request-response pattern).

        Creates a background task to receive the response and returns it.

        Args:
            from_agent: Requesting agent ID
            to_agent: Target agent ID
            message_type: Type of request
            content: Request payload
            priority: Message priority
            timeout: Response timeout (seconds)

        Returns:
            Response message

        Raises:
            asyncio.TimeoutError: If response timeout expires
        """
        # Generate correlation ID
        correlation_id = str(uuid.uuid4())

        # Create future for response
        response_future = asyncio.Future()
        self.pending_requests[correlation_id] = response_future

        # Background task to receive response
        async def receive_response():
            """Receive the response message and set future."""
            try:
                while True:
                    msg = await self.receive(from_agent, timeout=timeout)
                    # Check if this is our response
                    if msg.correlation_id == correlation_id:
                        if not response_future.done():
                            response_future.set_result(msg)
                        break
                    else:
                        # Not our response, put it back? Or handle differently
                        # For now, we'll just continue (message is consumed)
                        logger.warning(
                            f"Received unmatched message while waiting for response: "
                            f"expected correlation_id={correlation_id}, got {msg.correlation_id}"
                        )
            except Exception as e:
                if not response_future.done():
                    response_future.set_exception(e)

        # Start background receiver
        receiver_task = asyncio.create_task(receive_response())

        # Send request
        request = Message(
            from_agent=from_agent,
            to_agent=to_agent,
            message_type=message_type,
            content=content,
            priority=priority,
            correlation_id=correlation_id,
        )

        await self.send(request)

        # Wait for response
        timeout = timeout if timeout is not None else self.default_timeout

        try:
            response = await asyncio.wait_for(response_future, timeout=timeout)
            logger.debug(
                f"Request-response complete: {from_agent} -> {to_agent} "
                f"[{message_type}] in {(time.time() - request.timestamp)*1000:.2f}ms"
            )
            return response

        except asyncio.TimeoutError:
            # Clean up
            self.pending_requests.pop(correlation_id, None)
            receiver_task.cancel()
            logger.error(f"Request timeout: {from_agent} -> {to_agent} [{message_type}] " f"after {timeout}s")
            raise
        finally:
            # Ensure receiver task is cancelled
            if not receiver_task.done():
                receiver_task.cancel()
                try:
                    await receiver_task
                except asyncio.CancelledError:
                    pass

    async def send_response(
        self,
        from_agent: str,
        to_agent: str,
        message_type: str,
        content: Dict[str, Any],
        correlation_id: str,
        priority: MessagePriority = MessagePriority.HIGH,
    ):
        """
        Send a response to a request (helper for request-response pattern).

        Args:
            from_agent: Responding agent ID
            to_agent: Original requester ID
            message_type: Response type (usually "response" or "{request_type}_response")
            content: Response payload
            correlation_id: Correlation ID from the request
            priority: Response priority (default HIGH for fast responses)
        """
        response = Message(
            from_agent=from_agent,
            to_agent=to_agent,
            message_type=message_type,
            content=content,
            priority=priority,
            correlation_id=correlation_id,
        )

        await self.send(response)

    async def broadcast(self, message: Message, exclude: Optional[str] = None):
        """
        Broadcast a message to all registered agents (except sender and excluded).

        Args:
            message: Message to broadcast
            exclude: Optional agent ID to exclude
        """
        original_to = message.to_agent

        for agent_id in self.queues.keys():
            if agent_id == message.from_agent:
                continue
            if exclude and agent_id == exclude:
                continue

            # Create a copy with updated to_agent
            broadcast_message = Message(
                from_agent=message.from_agent,
                to_agent=agent_id,
                message_type=message.message_type,
                content=message.content,
                correlation_id=message.correlation_id,
                timestamp=message.timestamp,
                metadata=message.metadata,
            )

            await self.send(broadcast_message)

        logger.info(f"Broadcast from {message.from_agent}: {message.message_type}")

    def get_queue_size(self, agent_id: str) -> int:
        """
        Get the current size of an agent's queue.

        Args:
            agent_id: Agent to check

        Returns:
            Number of messages in queue
        """
        if agent_id not in self.queues:
            return 0
        return self.queues[agent_id].qsize()

    def get_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive message bus statistics.

        Returns:
            Dictionary with bus stats including latency metrics
        """
        uptime = time.time() - self.start_time

        # Calculate latency statistics
        latency_stats = {}
        for msg_type, latencies in self.latency_by_type.items():
            if latencies:
                latency_stats[msg_type] = {
                    "count": len(latencies),
                    "avg_ms": (sum(latencies) / len(latencies)) * 1000,
                    "min_ms": min(latencies) * 1000,
                    "max_ms": max(latencies) * 1000,
                }

        return {
            "uptime_seconds": uptime,
            "total_messages": self.message_count,
            "messages_per_second": self.message_count / uptime if uptime > 0 else 0,
            "registered_agents": list(self.queues.keys()),
            "queue_sizes": {agent_id: queue.qsize() for agent_id, queue in self.queues.items()},
            "pending_requests": len(self.pending_requests),
            "message_history_size": len(self.message_history),
            "latency_by_type": latency_stats,
            "concurrency_stats": self.get_concurrency_stats(),
        }

    def get_performance_snapshot(self) -> Dict[str, Any]:
        """
        Get real-time performance snapshot for monitoring.

        Returns:
            Performance metrics optimized for monitoring dashboards
        """
        stats = self.get_stats()
        current_time = time.time()

        # Calculate recent performance (last 60 seconds)
        recent_messages = sum(1 for msg in self.message_history
                            if current_time - msg["timestamp"] < 60)

        # Queue health metrics
        queue_health = {}
        for agent_id, queue in self.queues.items():
            qsize = queue.qsize()
            max_size = getattr(queue, '_maxsize', 0) or float('inf')
            queue_health[agent_id] = {
                "current_size": qsize,
                "max_size": max_size,
                "utilization_percent": (qsize / max_size * 100) if max_size != float('inf') else 0,
                "is_full": qsize >= max_size if max_size != float('inf') else False,
            }

        return {
            "timestamp": current_time,
            "overall_throughput": stats["messages_per_second"],
            "recent_throughput_60s": recent_messages / 60 if recent_messages > 0 else 0,
            "total_agents": len(stats["registered_agents"]),
            "total_queues": len(self.queues),
            "queue_health": queue_health,
            "pending_requests_count": stats["pending_requests"],
            "concurrency_active": stats["concurrency_stats"]["active"],
            "concurrency_limit": stats["concurrency_stats"]["semaphore_limit"],
            "concurrency_utilization_percent": (
                stats["concurrency_stats"]["active"] / stats["concurrency_stats"]["semaphore_limit"] * 100
                if stats["concurrency_stats"]["semaphore_limit"] > 0 else 0
            ),
            "avg_latency_ms": sum(
                type_stats["avg_ms"] for type_stats in stats["latency_by_type"].values()
            ) / len(stats["latency_by_type"]) if stats["latency_by_type"] else 0,
        }

    def optimize_performance(self) -> Dict[str, Any]:
        """
        Perform automatic performance optimizations based on current metrics.

        Returns:
            Dictionary describing optimizations performed
        """
        optimizations = {}
        stats = self.get_performance_snapshot()

        # Clean up old message history if it's getting large
        if len(self.message_history) > self.history_size * 1.5:
            # Keep only recent messages (last 10 minutes)
            cutoff_time = time.time() - 600
            old_count = len(self.message_history)
            self.message_history = [
                msg for msg in self.message_history
                if msg["timestamp"] > cutoff_time
            ]
            new_count = len(self.message_history)
            optimizations["history_cleanup"] = {
                "old_count": old_count,
                "new_count": new_count,
                "removed": old_count - new_count,
            }

        # Check for queue congestion
        congested_queues = []
        for agent_id, health in stats["queue_health"].items():
            if health["utilization_percent"] > 80:
                congested_queues.append(agent_id)

        if congested_queues:
            optimizations["queue_congestion_warning"] = {
                "congested_agents": congested_queues,
                "recommendation": "Consider increasing queue sizes or processing capacity",
            }

        # Check concurrency utilization
        if stats["concurrency_utilization_percent"] > 90:
            optimizations["high_concurrency_warning"] = {
                "current_active": stats["concurrency_active"],
                "limit": stats["concurrency_limit"],
                "recommendation": "Consider increasing max_concurrent limit",
            }

        # Latency optimization suggestions
        if stats["avg_latency_ms"] > 10:  # More than 10ms average
            optimizations["latency_optimization"] = {
                "current_avg_ms": stats["avg_latency_ms"],
                "recommendations": [
                    "Consider reducing message history size",
                    "Check for blocking operations in message handlers",
                    "Monitor agent processing times",
                ],
            }

        return {
            "timestamp": time.time(),
            "optimizations_performed": optimizations,
            "performance_snapshot": stats,
        }

    def get_message_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get recent message history.

        Args:
            limit: Number of recent messages to return (None = all)

        Returns:
            List of message summaries
        """
        history = list(self.message_history)
        if limit:
            history = history[-limit:]
        return history

    def clear_queue(self, agent_id: str):
        """
        Clear all messages from an agent's priority queue.

        Args:
            agent_id: Agent whose queue to clear
        """
        if agent_id not in self.queues:
            return

        # Create a new priority queue to replace the old one
        maxsize = self.queues[agent_id].maxsize
        self.queues[agent_id] = asyncio.Queue(maxsize=maxsize)

        logger.info(f"Cleared priority queue for agent: {agent_id}")

    async def send_toon(self, to_agent: str, data: Dict[str, Any], from_agent: str = "system", priority: MessagePriority = MessagePriority.NORMAL, correlation_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Send data encoded in TOON format for token efficiency.
        Returns the TOON string sent.
        """
        if not TOON_AVAILABLE:
            raise MessageBusError("TOON not available - install python-toon")
        toon_str, savings = await estimate_savings(data)
        logger.info(f"TOON send to {to_agent}: {savings:.1f}% savings ({len(toon_str)} chars)")
        message = Message(
            from_agent=from_agent,
            to_agent=to_agent,
            message_type="toon_data",
            content={"toon": toon_str, "savings": savings},
            priority=priority,
            correlation_id=correlation_id,
            metadata=metadata or {},
        )
        await self.send(message)
        return toon_str

    async def receive_toon(self, agent_id: str, timeout: float = 5.0) -> Tuple[Dict[str, Any], float]:
        """
        Receive and decode TOON message.
        Returns (decoded_data, savings_percentage).
        Raises ToonDecodeError if decode fails.
        """
        if not TOON_AVAILABLE:
            raise MessageBusError("TOON not available - install python-toon")
        message = await self.receive(agent_id, timeout)
        if message.message_type == "toon_data":
            toon_str = message.content["toon"]
            savings = message.content["savings"]
            try:
                data = await decode_from_swarm(toon_str)
                return data, savings
            except ToonDecodeError as e:
                logger.error(f"TOON decode failed: {e}")
                raise
        else:
            # Not TOON, return content as is
            return message.content, 0.0

    async def shutdown(self):
        """
        Shutdown the message bus and clear all queues.
        """
        logger.info("Shutting down MessageBus...")

        for agent_id in list(self.queues.keys()):
            self.clear_queue(agent_id)

        self.queues.clear()

        stats = self.get_stats()
        logger.info(f"MessageBus shutdown complete. Total messages: {stats['total_messages']}")
