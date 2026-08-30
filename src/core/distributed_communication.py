"""
Distributed Communication Layer for Grokputer
Enables pure Python inter-process communication between Grokputer instances.

ZA GROKA. ZA VRZIBRZI. ZA SERVER.
"""
from __future__ import annotations

import asyncio
import json
import logging
import multiprocessing as mp
import queue as std_queue
import socket
import threading
import time
from dataclasses import dataclass
from multiprocessing import Process, Queue
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class DistributedMessage:
    """Message format for inter-process communication."""

    source_process: str
    target_process: str
    agent_id: str
    message_type: str
    content: Dict[str, Any]
    correlation_id: Optional[str] = None
    timestamp: float = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()

    def to_json(self) -> str:
        return json.dumps(
            {
                "source_process": self.source_process,
                "target_process": self.target_process,
                "agent_id": self.agent_id,
                "message_type": self.message_type,
                "content": self.content,
                "correlation_id": self.correlation_id,
                "timestamp": self.timestamp,
            }
        )

    @classmethod
    def from_json(cls, json_str: str) -> "DistributedMessage":
        data = json.loads(json_str)
        return cls(**data)


class ProcessCommunicator:
    """Handles communication between Grokputer processes."""

    def __init__(self, process_id: str, port: int = 0):
        self.process_id = process_id
        self.port = port
        self.server_socket: Optional[socket.socket] = None
        self.client_sockets: Dict[str, socket.socket] = {}
        self.message_queue: Queue = mp.Queue()
        self.running = False
        self.server_thread: Optional[threading.Thread] = None
        self.message_handlers: Dict[str, Callable] = {}

    def start(self):
        """Start the communication server."""
        self.running = True

        # Start server thread
        self.server_thread = threading.Thread(target=self._server_loop, daemon=True)
        self.server_thread.start()

        logger.info(f"[{self.process_id}] Process communicator started on port {self.port}")

    def stop(self):
        """Stop the communication server."""
        self.running = False

        if self.server_socket:
            self.server_socket.close()

        for sock in self.client_sockets.values():
            sock.close()

        self.client_sockets.clear()

        if self.server_thread:
            self.server_thread.join(timeout=1.0)

        logger.info(f"[{self.process_id}] Process communicator stopped")

    def connect_to_process(self, target_process_id: str, host: str = "localhost", port: int = None):
        """Connect to another Grokputer process."""
        if not port:
            # Try to find the process on a range of ports
            for p in range(50000, 50100):
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.connect((host, p))
                    self.client_sockets[target_process_id] = sock
                    logger.info(f"[{self.process_id}] Connected to {target_process_id} on {host}:{p}")
                    return True
                except:
                    sock.close()
                    continue
            return False
        else:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((host, port))
                self.client_sockets[target_process_id] = sock
                logger.info(f"[{self.process_id}] Connected to {target_process_id} on {host}:{port}")
                return True
            except Exception as e:
                logger.error(f"[{self.process_id}] Failed to connect to {target_process_id}: {e}")
                return False

    def send_message(self, message: DistributedMessage):
        """Send a message to another process."""
        if message.target_process in self.client_sockets:
            try:
                sock = self.client_sockets[message.target_process]
                data = message.to_json().encode("utf-8")
                # Send message length first, then data
                sock.send(len(data).to_bytes(4, byteorder="big"))
                sock.send(data)
                return True
            except Exception as e:
                logger.error(f"[{self.process_id}] Failed to send message: {e}")
                return False
        else:
            logger.warning(f"[{self.process_id}] No connection to {message.target_process}")
            return False

    def receive_message(self, timeout: float = 0.1) -> Optional[DistributedMessage]:
        """Receive a message from the queue."""
        try:
            return self.message_queue.get(timeout=timeout)
        except std_queue.Empty:
            return None

    def register_handler(self, message_type: str, handler: Callable):
        """Register a message handler."""
        self.message_handlers[message_type] = handler

    def _server_loop(self):
        """Server loop to accept connections and receive messages."""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            self.server_socket.bind(("localhost", self.port))
            self.server_socket.listen(5)
            self.port = self.server_socket.getsockname()[1]  # Get actual port if 0 was used
            logger.info(f"[{self.process_id}] Listening on port {self.port}")

            while self.running:
                try:
                    client_sock, addr = self.server_socket.accept()
                    logger.info(f"[{self.process_id}] Accepted connection from {addr}")

                    # Start a thread to handle this client
                    client_thread = threading.Thread(target=self._handle_client, args=(client_sock,), daemon=True)
                    client_thread.start()

                except OSError:
                    break  # Socket was closed
                except Exception as e:
                    logger.error(f"[{self.process_id}] Server error: {e}")

        except Exception as e:
            logger.error(f"[{self.process_id}] Failed to start server: {e}")
        finally:
            if self.server_socket:
                self.server_socket.close()

    def _handle_client(self, client_sock: socket.socket):
        """Handle messages from a connected client."""
        try:
            while self.running:
                # Read message length
                length_bytes = client_sock.recv(4)
                if not length_bytes:
                    break

                message_length = int.from_bytes(length_bytes, byteorder="big")

                # Read message data
                data = b""
                while len(data) < message_length:
                    chunk = client_sock.recv(min(4096, message_length - len(data)))
                    if not chunk:
                        break
                    data += chunk

                if len(data) == message_length:
                    try:
                        message = DistributedMessage.from_json(data.decode("utf-8"))
                        self.message_queue.put(message)

                        # Handle message if we have a handler
                        if message.message_type in self.message_handlers:
                            handler = self.message_handlers[message.message_type]
                            # Run handler in a thread to avoid blocking
                            handler_thread = threading.Thread(target=handler, args=(message,), daemon=True)
                            handler_thread.start()

                    except Exception as e:
                        logger.error(f"[{self.process_id}] Failed to parse message: {e}")

        except Exception as e:
            logger.error(f"[{self.process_id}] Client handler error: {e}")
        finally:
            client_sock.close()


class DistributedMessageBus:
    """Distributed MessageBus that spans multiple processes."""

    def __init__(self, process_id: str):
        self.process_id = process_id
        self.communicator = ProcessCommunicator(process_id)
        self.local_queues: Dict[str, asyncio.Queue] = {}
        self.running = False

        # Register message handlers
        self.communicator.register_handler("message", self._handle_distributed_message)

    async def start(self):
        """Start the distributed message bus."""
        self.running = True
        self.communicator.start()

        # Start message processing loop
        asyncio.create_task(self._process_messages())

        logger.info(f"[{self.process_id}] Distributed MessageBus started")

    async def stop(self):
        """Stop the distributed message bus."""
        self.running = False
        self.communicator.stop()
        logger.info(f"[{self.process_id}] Distributed MessageBus stopped")

    def connect_to_process(self, target_process_id: str, host: str = "localhost", port: int = None) -> bool:
        """Connect to another Grokputer process."""
        return self.communicator.connect_to_process(target_process_id, host, port)

    async def send(
        self,
        from_agent: str,
        to_agent: str,
        message_type: str,
        content: Dict[str, Any],
        correlation_id: Optional[str] = None,
    ):
        """Send a message, potentially to another process."""
        # Determine target process
        target_process = self._get_process_for_agent(to_agent)

        if target_process == self.process_id:
            # Local message
            await self._send_local(from_agent, to_agent, message_type, content, correlation_id)
        else:
            # Distributed message
            message = DistributedMessage(
                source_process=self.process_id,
                target_process=target_process,
                agent_id=to_agent,
                message_type=message_type,
                content=content,
                correlation_id=correlation_id,
            )
            self.communicator.send_message(message)

    async def receive(self, agent_id: str, timeout: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """Receive a message for an agent."""
        if agent_id not in self.local_queues:
            self.local_queues[agent_id] = asyncio.Queue()

        try:
            return await asyncio.wait_for(self.local_queues[agent_id].get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None

    def register_agent(self, agent_id: str):
        """Register an agent with the message bus."""
        if agent_id not in self.local_queues:
            self.local_queues[agent_id] = asyncio.Queue()
        logger.info(f"[{self.process_id}] Registered agent: {agent_id}")

    async def _send_local(
        self, from_agent: str, to_agent: str, message_type: str, content: Dict[str, Any], correlation_id: Optional[str]
    ):
        """Send a message locally."""
        if to_agent in self.local_queues:
            message = {
                "from_agent": from_agent,
                "to_agent": to_agent,
                "message_type": message_type,
                "content": content,
                "correlation_id": correlation_id,
                "timestamp": time.time(),
            }
            await self.local_queues[to_agent].put(message)

    async def _process_messages(self):
        """Process incoming distributed messages."""
        while self.running:
            message = self.communicator.receive_message(timeout=0.1)
            if message:
                # Convert to local message format and deliver
                local_message = {
                    "from_agent": message.agent_id,
                    "to_agent": message.agent_id,  # This should be the local agent
                    "message_type": message.message_type,
                    "content": message.content,
                    "correlation_id": message.correlation_id,
                    "timestamp": message.timestamp,
                }

                # Find the target agent in this process
                target_agent = self._get_local_agent_for_message(message)
                if target_agent and target_agent in self.local_queues:
                    await self.local_queues[target_agent].put(local_message)

            await asyncio.sleep(0.01)  # Small delay to prevent busy waiting

    def _handle_distributed_message(self, message: DistributedMessage):
        """Handle incoming distributed messages."""
        # This is called from the communicator thread
        # The message will be processed in the async loop
        pass

    def _get_process_for_agent(self, agent_id: str) -> str:
        """Determine which process an agent belongs to."""
        # For now, assume all agents are local
        # This could be extended with a registry
        return self.process_id

    def _get_local_agent_for_message(self, message: DistributedMessage) -> Optional[str]:
        """Find the local agent that should receive this message."""
        # For now, assume the message is for an agent with the same ID
        return message.agent_id

    def get_connection_info(self) -> Dict[str, Any]:
        """Get connection information for this process."""
        return {
            "process_id": self.process_id,
            "port": self.communicator.port,
            "connected_processes": list(self.communicator.client_sockets.keys()),
        }


# Global registry of distributed message buses
_distributed_buses: Dict[str, DistributedMessageBus] = {}


def get_distributed_bus(process_id: str) -> DistributedMessageBus:
    """Get or create a distributed message bus for a process."""
    if process_id not in _distributed_buses:
        _distributed_buses[process_id] = DistributedMessageBus(process_id)
    return _distributed_buses[process_id]


def connect_processes(process_a: str, process_b: str):
    """Connect two Grokputer processes."""
    bus_a = get_distributed_bus(process_a)
    bus_b = get_distributed_bus(process_b)

    # Get connection info
    info_a = bus_a.get_connection_info()
    info_b = bus_b.get_connection_info()

    # Connect them
    bus_a.connect_to_process(process_b, port=info_b["port"])
    bus_b.connect_to_process(process_a, port=info_a["port"])

    logger.info(f"Connected processes {process_a} and {process_b}")


# Example usage function
async def demo_distributed_communication():
    """Demonstrate distributed communication between processes."""

    # Process A
    bus_a = get_distributed_bus("process_a")
    await bus_a.start()
    bus_a.register_agent("agent_a1")

    # Process B
    bus_b = get_distributed_bus("process_b")
    await bus_b.start()
    bus_b.register_agent("agent_b1")

    # Connect them
    connect_processes("process_a", "process_b")

    # Send a message from A to B
    await bus_a.send("agent_a1", "agent_b1", "hello", {"message": "Hello from process A!"})

    # Receive in B
    message = await bus_b.receive("agent_b1", timeout=5.0)
    if message:
        print(f"Process B received: {message}")

    # Cleanup
    await bus_a.stop()
    await bus_b.stop()


if __name__ == "__main__":
    # Run demo
    asyncio.run(demo_distributed_communication())
