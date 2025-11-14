"""
Distributed Message Bus with Redis Clustering and Load Balancing
================================================================

Scalable message bus supporting distributed agents across multiple nodes.
Features Redis clustering for high availability and load balancing for optimal performance.
"""

import asyncio
import logging
import time
import json
import hashlib
import threading
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass, field
import argparse
import signal
import sys

# Import existing MessageBus
from .message_bus import MessageBus, Message, MessagePriority

logger = logging.getLogger(__name__)

# Optional Redis import
try:
    import redis
    from redis.cluster import RedisCluster
    REDIS_AVAILABLE = True
except ImportError:
    redis = None
    RedisCluster = None
    REDIS_AVAILABLE = False

class DistributedMessageBus(MessageBus):
    """
    Distributed message bus with Redis clustering and load balancing.

    Features:
    - Redis Cluster support for distributed messaging
    - Load balancing across multiple nodes
    - Auto-scaling and failover
    - Daemon mode for background operation
    - High availability with node discovery
    """

    def __init__(
        self,
        redis_hosts: List[Dict[str, Any]] = None,
        node_id: str = None,
        load_balancing_enabled: bool = True,
        auto_discovery: bool = True,
        **kwargs
    ):
        """
        Initialize distributed message bus.

        Args:
            redis_hosts: List of Redis cluster nodes [{'host': 'localhost', 'port': 6379}, ...]
            node_id: Unique identifier for this node
            load_balancing_enabled: Enable load balancing
            auto_discovery: Auto-discover cluster nodes
            **kwargs: Passed to parent MessageBus
        """
        super().__init__(**kwargs)

        self.node_id = node_id or f"node_{hashlib.md5(str(time.time()).encode()).hexdigest()[:8]}"
        self.load_balancing_enabled = load_balancing_enabled
        self.auto_discovery = auto_discovery

        # Redis cluster setup
        self.redis_hosts = redis_hosts or [{'host': 'localhost', 'port': 6379}]
        self.redis_cluster = None
        self.redis_available = False

        # Distributed features
        self.cluster_nodes: Set[str] = set()
        self.node_loads: Dict[str, float] = {}
        self.message_routing: Dict[str, str] = {}  # agent_id -> node_id

        # Load balancing
        self.load_balancer = LoadBalancer(self.node_id) if load_balancing_enabled else None

        # Daemon mode
        self.daemon_mode = False
        self.daemon_thread = None
        self.shutdown_event = threading.Event()

        # Initialize Redis connection
        self._init_redis_cluster()

        logger.info(f"DistributedMessageBus initialized: node_id={self.node_id}, redis_available={self.redis_available}")

    def _init_redis_cluster(self):
        """Initialize Redis cluster connection."""
        if not REDIS_AVAILABLE:
            logger.warning("Redis not available. Running in local-only mode.")
            return

        try:
            # Try to connect to Redis cluster
            startup_nodes = [redis.ClusterNode(**host) for host in self.redis_hosts]
            self.redis_cluster = RedisCluster(
                startup_nodes=startup_nodes,
                decode_responses=True,
                skip_full_coverage_check=True,
                max_connections=20
            )

            # Test connection
            self.redis_cluster.ping()
            self.redis_available = True

            # Register this node
            self._register_node()

            # Start cluster monitoring
            self._start_cluster_monitoring()

            logger.info(f"Connected to Redis cluster with {len(self.redis_hosts)} nodes")

        except Exception as e:
            logger.error(f"Failed to connect to Redis cluster: {e}")
            self.redis_available = False

    def _register_node(self):
        """Register this node in the cluster."""
        if not self.redis_available:
            return

        node_info = {
            'node_id': self.node_id,
            'registered_agents': list(self.queues.keys()),
            'load_factor': 0.0,
            'last_seen': time.time(),
            'status': 'active'
        }

        try:
            self.redis_cluster.setex(
                f"node:{self.node_id}",
                300,  # 5 minute TTL
                json.dumps(node_info)
            )

            # Add to cluster nodes set
            self.redis_cluster.sadd("cluster_nodes", self.node_id)

        except Exception as e:
            logger.error(f"Failed to register node: {e}")

    def _start_cluster_monitoring(self):
        """Start background cluster monitoring."""
        if not self.redis_available:
            return

        async def monitor_cluster():
            while not self.shutdown_event.is_set():
                try:
                    await asyncio.sleep(30)  # Check every 30 seconds

                    # Update node registration
                    self._register_node()

                    # Discover other nodes
                    self._discover_cluster_nodes()

                    # Update load balancing info
                    if self.load_balancer:
                        await self.load_balancer.update_cluster_loads(self.cluster_nodes, self.redis_cluster)

                except Exception as e:
                    logger.error(f"Cluster monitoring error: {e}")
                    await asyncio.sleep(60)  # Wait longer on error

        asyncio.create_task(monitor_cluster())

    def _discover_cluster_nodes(self):
        """Discover other nodes in the cluster."""
        if not self.redis_available:
            return

        try:
            nodes = self.redis_cluster.smembers("cluster_nodes")
            self.cluster_nodes = set(nodes)

            # Remove this node
            self.cluster_nodes.discard(self.node_id)

            logger.debug(f"Discovered {len(self.cluster_nodes)} cluster nodes")

        except Exception as e:
            logger.error(f"Failed to discover cluster nodes: {e}")

    async def send(self, message: Message):
        """Send message with distributed routing."""
        # Check if recipient is on another node
        target_node = self.message_routing.get(message.to_agent)

        if target_node and target_node != self.node_id and self.redis_available:
            # Route to remote node
            await self._send_remote(message, target_node)
        else:
            # Local delivery
            await super().send(message)

    async def _send_remote(self, message: Message, target_node: str):
        """Send message to remote node via Redis."""
        if not self.redis_available:
            await super().send(message)
            return

        try:
            message_data = {
                'message': message.to_dict(),
                'target_node': target_node,
                'source_node': self.node_id,
                'timestamp': time.time()
            }

            # Publish to Redis channel for target node
            channel = f"node_messages:{target_node}"
            self.redis_cluster.publish(channel, json.dumps(message_data))

            logger.debug(f"Sent remote message: {message.from_agent} -> {message.to_agent} via {target_node}")

        except Exception as e:
            logger.error(f"Failed to send remote message: {e}")
            # Fallback to local if remote fails
            await super().send(message)

    def register_agent(self, agent_id: str, queue_size: int = 0):
        """Register agent with distributed routing."""
        super().register_agent(agent_id, queue_size)

        # Update routing table
        self.message_routing[agent_id] = self.node_id

        # Register with cluster
        if self.redis_available:
            self._register_node()

    async def broadcast(self, message: Message, exclude: Optional[str] = None):
        """Broadcast with distributed routing."""
        # Local broadcast
        await super().broadcast(message, exclude)

        # Distributed broadcast
        if self.redis_available and self.cluster_nodes:
            for node_id in self.cluster_nodes:
                if exclude and node_id == exclude:
                    continue

                broadcast_msg = Message(
                    from_agent=message.from_agent,
                    to_agent=f"node:{node_id}",  # Special routing
                    message_type="broadcast",
                    content={
                        'original_message': message.to_dict(),
                        'exclude': exclude
                    },
                    priority=message.priority
                )

                await self._send_remote(broadcast_msg, node_id)

    def get_cluster_stats(self) -> Dict[str, Any]:
        """Get cluster-wide statistics."""
        stats = self.get_stats()

        if not self.redis_available:
            stats['cluster'] = {'status': 'unavailable'}
            return stats

        try:
            # Get all node info
            nodes_info = {}
            for node_id in self.cluster_nodes:
                node_key = f"node:{node_id}"
                node_data = self.redis_cluster.get(node_key)
                if node_data:
                    nodes_info[node_id] = json.loads(node_data)

            stats['cluster'] = {
                'status': 'active',
                'total_nodes': len(self.cluster_nodes) + 1,  # +1 for this node
                'nodes': nodes_info,
                'load_balancing': self.load_balancing_enabled,
                'auto_discovery': self.auto_discovery
            }

        except Exception as e:
            stats['cluster'] = {'status': 'error', 'error': str(e)}

        return stats

    # Daemon Mode Support

    def start_daemon(self, auto_mode: bool = True):
        """Start message bus in daemon mode."""
        self.daemon_mode = True

        def daemon_main():
            """Main daemon function."""
            logger.info("Starting DistributedMessageBus daemon...")

            # Setup signal handlers
            signal.signal(signal.SIGTERM, self._signal_handler)
            signal.signal(signal.SIGINT, self._signal_handler)

            try:
                # Start event loop
                asyncio.run(self._run_daemon(auto_mode))
            except Exception as e:
                logger.error(f"Daemon error: {e}")
            finally:
                logger.info("DistributedMessageBus daemon stopped")

        self.daemon_thread = threading.Thread(target=daemon_main, daemon=True)
        self.daemon_thread.start()

        logger.info(f"DistributedMessageBus daemon started (node: {self.node_id})")

    def stop_daemon(self):
        """Stop daemon mode."""
        if self.daemon_mode:
            logger.info("Stopping DistributedMessageBus daemon...")
            self.shutdown_event.set()

            if self.daemon_thread and self.daemon_thread.is_alive():
                self.daemon_thread.join(timeout=10)

            self.daemon_mode = False

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.stop_daemon()

    async def _run_daemon(self, auto_mode: bool):
        """Run daemon event loop."""
        logger.info("DistributedMessageBus daemon running...")

        # Subscribe to node messages
        if self.redis_available:
            asyncio.create_task(self._listen_for_remote_messages())

        # Auto mode: continuous optimization
        if auto_mode:
            asyncio.create_task(self._auto_optimization_loop())

        # Keep daemon alive
        while not self.shutdown_event.is_set():
            await asyncio.sleep(1)

            # Periodic health checks
            if int(time.time()) % 60 == 0:  # Every minute
                stats = self.get_cluster_stats()
                logger.info(f"Daemon health: {stats['total_messages']} messages, "
                          f"{stats['cluster'].get('total_nodes', 1)} nodes")

    async def _listen_for_remote_messages(self):
        """Listen for messages from other nodes."""
        if not self.redis_available:
            return

        try:
            pubsub = self.redis_cluster.pubsub()
            channel = f"node_messages:{self.node_id}"
            pubsub.subscribe(channel)

            logger.info(f"Listening for remote messages on channel: {channel}")

            while not self.shutdown_event.is_set():
                message = pubsub.get_message(timeout=1.0)
                if message and message['type'] == 'message':
                    try:
                        data = json.loads(message['data'])
                        remote_msg_data = data['message']

                        # Reconstruct message
                        remote_msg = Message(
                            from_agent=remote_msg_data['from'],
                            to_agent=remote_msg_data['to'],
                            message_type=remote_msg_data['type'],
                            content=remote_msg_data['content'],
                            priority=MessagePriority[remote_msg_data['priority']],
                            correlation_id=remote_msg_data.get('correlation_id'),
                            timestamp=remote_msg_data['timestamp']
                        )

                        # Route locally
                        await self.send(remote_msg)

                    except Exception as e:
                        logger.error(f"Error processing remote message: {e}")

        except Exception as e:
            logger.error(f"Remote message listener error: {e}")

    async def _auto_optimization_loop(self):
        """Continuous auto-optimization in daemon mode."""
        while not self.shutdown_event.is_set():
            await asyncio.sleep(300)  # Every 5 minutes

            try:
                # Run performance optimization
                optimizations = self.optimize_performance()

                # Log significant optimizations
                if optimizations['optimizations_performed']:
                    logger.info(f"Auto-optimization performed: {len(optimizations['optimizations_performed'])} actions")

                # Update cluster loads
                if self.load_balancer:
                    await self.load_balancer.balance_load(self, self.redis_cluster)

            except Exception as e:
                logger.error(f"Auto-optimization error: {e}")

class LoadBalancer:
    """
    Load balancer for distributed message routing.
    """

    def __init__(self, node_id: str):
        self.node_id = node_id
        self.node_loads: Dict[str, float] = {}

    async def update_cluster_loads(self, cluster_nodes: Set[str], redis_cluster):
        """Update load information for all cluster nodes."""
        self.node_loads = {}

        for node_id in cluster_nodes:
            try:
                node_key = f"node:{node_id}"
                node_data = redis_cluster.get(node_key)
                if node_data:
                    node_info = json.loads(node_data)
                    self.node_loads[node_id] = node_info.get('load_factor', 0.0)
            except Exception as e:
                logger.error(f"Failed to get load for node {node_id}: {e}")

    async def balance_load(self, message_bus: DistributedMessageBus, redis_cluster):
        """Perform load balancing operations."""
        if not self.node_loads:
            return

        # Find overloaded and underloaded nodes
        avg_load = sum(self.node_loads.values()) / len(self.node_loads)

        overloaded = [node for node, load in self.node_loads.items() if load > avg_load * 1.2]
        underloaded = [node for node, load in self.node_loads.items() if load < avg_load * 0.8]

        if overloaded and underloaded:
            logger.info(f"Load balancing: {len(overloaded)} overloaded, {len(underloaded)} underloaded")

            # Simple balancing: suggest agent migrations
            # In production, this would trigger actual migrations
            for over_node in overloaded:
                for under_node in underloaded:
                    logger.info(f"Suggest migrating agents from {over_node} to {under_node}")

def main():
    """Main function for running distributed message bus."""
    parser = argparse.ArgumentParser(description="Distributed Message Bus")
    parser.add_argument("--daemon", action="store_true", help="Run in daemon mode")
    parser.add_argument("--auto", action="store_true", help="Enable auto-optimization in daemon mode")
    parser.add_argument("--node-id", help="Unique node identifier")
    parser.add_argument("--redis-host", default="localhost", help="Redis host")
    parser.add_argument("--redis-port", type=int, default=6379, help="Redis port")
    parser.add_argument("--no-load-balancing", action="store_true", help="Disable load balancing")

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(level=logging.INFO)

    # Create distributed bus
    redis_hosts = [{'host': args.redis_host, 'port': args.redis_port}]
    bus = DistributedMessageBus(
        redis_hosts=redis_hosts,
        node_id=args.node_id,
        load_balancing_enabled=not args.no_load_balancing
    )

    if args.daemon:
        # Start daemon
        bus.start_daemon(auto_mode=args.auto)

        # Keep main thread alive
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            bus.stop_daemon()

    else:
        # Interactive mode
        logger.info("Distributed Message Bus started in interactive mode")
        logger.info(f"Node ID: {bus.node_id}")
        logger.info(f"Redis available: {bus.redis_available}")

        # Keep running for testing
        try:
            asyncio.run(asyncio.sleep(3600))  # Run for 1 hour
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
            asyncio.run(bus.shutdown())

if __name__ == "__main__":
    main()