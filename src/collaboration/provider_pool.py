"""
Provider Pool for Multi-Agent Framework (MAF)

Manages provider instances with health monitoring, load balancing, and connection pooling.
Provides high-availability provider access with automatic failover and recovery.
"""
from __future__ import annotations

import asyncio
import logging
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from .provider_registry import ProviderInstance, ProviderRegistry, provider_registry

logger = logging.getLogger(__name__)


class PoolStrategy(Enum):
    """Load balancing strategies for provider selection."""

    ROUND_ROBIN = "round_robin"
    WEIGHTED_RANDOM = "weighted_random"
    LEAST_LOADED = "least_loaded"
    HEALTH_PRIORITY = "health_priority"


@dataclass
class PoolConfig:
    """Configuration for provider pool behavior."""

    max_connections_per_provider: int = 5
    connection_timeout: float = 30.0
    health_check_interval: int = 60
    max_retry_attempts: int = 3
    retry_backoff_factor: float = 2.0
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: int = 300  # 5 minutes
    enable_connection_pooling: bool = True
    load_balancing_strategy: PoolStrategy = PoolStrategy.HEALTH_PRIORITY


@dataclass
class ConnectionInfo:
    """Information about a provider connection."""

    provider_id: str
    connection_id: str
    created_at: float = field(default_factory=time.time)
    last_used: float = field(default_factory=time.time)
    active_requests: int = 0
    total_requests: int = 0
    failed_requests: int = 0
    is_healthy: bool = True


@dataclass
class ProviderPoolStats:
    """Statistics for provider pool performance."""

    total_connections: int
    active_connections: int
    healthy_connections: int
    total_requests: int
    failed_requests: int
    average_response_time: float
    pool_hit_rate: float


class CircuitBreaker:
    """Circuit breaker pattern for provider failure handling."""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 300):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "closed"  # closed, open, half_open

    def record_success(self):
        """Record a successful operation."""
        self.failure_count = 0
        self.state = "closed"

    def record_failure(self):
        """Record a failed operation."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")

    def can_attempt(self) -> bool:
        """Check if an operation can be attempted."""
        if self.state == "closed":
            return True
        elif self.state == "open":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "half_open"
                logger.info("Circuit breaker entering half-open state")
                return True
            return False
        elif self.state == "half_open":
            return True
        return False


class ProviderPool:
    """
    Connection pool for AI providers with health monitoring and load balancing.

    Manages multiple connections per provider, handles failover, and provides
    high-availability access to AI services.
    """

    def __init__(self, config: PoolConfig = None, registry: ProviderRegistry = None):
        self.config = config or PoolConfig()
        self.registry = registry or provider_registry

        # Connection management
        self._connections: Dict[str, List[ConnectionInfo]] = {}
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._round_robin_index: Dict[str, int] = {}

        # Statistics
        self._stats = ProviderPoolStats(0, 0, 0, 0, 0, 0.0, 0.0)
        self._response_times: List[float] = []

        # Background tasks
        self._cleanup_task: Optional[asyncio.Task] = None
        self._health_monitor_task: Optional[asyncio.Task] = None

        logger.info("Provider pool initialized")

    async def start(self):
        """Start the provider pool and background tasks."""
        await self.registry.start_health_monitoring()

        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._connection_cleanup_loop())

        if self._health_monitor_task is None:
            self._health_monitor_task = asyncio.create_task(self._health_monitor_loop())

        logger.info("Provider pool started")

    async def stop(self):
        """Stop the provider pool and cleanup resources."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        if self._health_monitor_task:
            self._health_monitor_task.cancel()
            try:
                await self._health_monitor_task
            except asyncio.CancelledError:
                pass

        await self.registry.stop_health_monitoring()

        # Close all connections
        for provider_id, connections in self._connections.items():
            for conn in connections:
                # In a real implementation, this would close actual connections
                logger.debug(f"Closed connection {conn.connection_id} for provider {provider_id}")

        self._connections.clear()
        logger.info("Provider pool stopped")

    async def acquire_connection(self, provider_id: str) -> Optional[ConnectionInfo]:
        """
        Acquire a connection for the specified provider.

        Args:
            provider_id: Provider to get connection for

        Returns:
            ConnectionInfo if available, None if not
        """
        # Check circuit breaker
        if provider_id not in self._circuit_breakers:
            self._circuit_breakers[provider_id] = CircuitBreaker(
                self.config.circuit_breaker_threshold, self.config.circuit_breaker_timeout
            )

        circuit_breaker = self._circuit_breakers[provider_id]
        if not circuit_breaker.can_attempt():
            logger.warning(f"Circuit breaker open for provider {provider_id}")
            return None

        # Get or create connections for this provider
        if provider_id not in self._connections:
            self._connections[provider_id] = []

        connections = self._connections[provider_id]

        # Find available connection
        available_conn = None
        for conn in connections:
            if conn.is_healthy and conn.active_requests == 0:
                available_conn = conn
                break

        # Create new connection if needed and under limit
        if not available_conn and len(connections) < self.config.max_connections_per_provider:
            conn_id = f"{provider_id}_{len(connections)}_{int(time.time())}"
            available_conn = ConnectionInfo(provider_id=provider_id, connection_id=conn_id, is_healthy=True)
            connections.append(available_conn)
            self._stats.total_connections += 1
            logger.debug(f"Created new connection {conn_id} for provider {provider_id}")

        if available_conn:
            available_conn.active_requests += 1
            available_conn.last_used = time.time()
            available_conn.total_requests += 1
            self._stats.active_connections += 1

        return available_conn

    async def release_connection(self, connection: ConnectionInfo):
        """
        Release a connection back to the pool.

        Args:
            connection: Connection to release
        """
        if connection.active_requests > 0:
            connection.active_requests -= 1
            self._stats.active_connections = max(0, self._stats.active_connections - 1)

    async def execute_with_provider(self, provider_id: str, operation: Callable, *args, **kwargs) -> Any:
        """
        Execute an operation using a pooled connection for the provider.

        Args:
            provider_id: Provider to use
            operation: Async callable to execute
            *args, **kwargs: Arguments for the operation

        Returns:
            Result of the operation
        """
        connection = await self.acquire_connection(provider_id)
        if not connection:
            raise Exception(f"No available connection for provider {provider_id}")

        start_time = time.time()
        try:
            # Execute the operation
            result = await operation(*args, **kwargs)

            # Record success
            response_time = time.time() - start_time
            self._response_times.append(response_time)
            self._stats.total_requests += 1

            # Update circuit breaker
            self._circuit_breakers[provider_id].record_success()

            return result

        except Exception as e:
            # Record failure
            self._stats.failed_requests += 1
            connection.failed_requests += 1
            connection.is_healthy = False

            # Update circuit breaker
            self._circuit_breakers[provider_id].record_failure()

            logger.error(f"Provider operation failed for {provider_id}: {e}")
            raise e

        finally:
            await self.release_connection(connection)

    def select_provider(self, required_capabilities: List[str] = None, strategy: PoolStrategy = None) -> Optional[str]:
        """
        Select a provider using the configured load balancing strategy.

        Args:
            required_capabilities: List of required provider capabilities
            strategy: Override the default load balancing strategy

        Returns:
            Selected provider ID or None if no suitable provider found
        """
        strategy = strategy or self.config.load_balancing_strategy

        # Get candidate providers
        candidates = []
        if required_capabilities:
            # Convert string capabilities to enum if needed
            from .provider_registry import ProviderCapability

            capabilities = []
            for cap in required_capabilities:
                if isinstance(cap, str):
                    try:
                        capabilities.append(ProviderCapability[cap.upper()])
                    except KeyError:
                        logger.warning(f"Unknown capability: {cap}")
                        continue
                else:
                    capabilities.append(cap)

            candidates = self.registry.select_providers_for_task(capabilities)
        else:
            candidates = self.registry.get_all_providers(only_healthy=True)

        if not candidates:
            return None

        # Apply load balancing strategy
        if strategy == PoolStrategy.ROUND_ROBIN:
            return self._select_round_robin(candidates)
        elif strategy == PoolStrategy.WEIGHTED_RANDOM:
            return self._select_weighted_random(candidates)
        elif strategy == PoolStrategy.LEAST_LOADED:
            return self._select_least_loaded(candidates)
        elif strategy == PoolStrategy.HEALTH_PRIORITY:
            return self._select_health_priority(candidates)
        else:
            return candidates[0].metadata.name if candidates else None

    def _select_round_robin(self, candidates: List[ProviderInstance]) -> Optional[str]:
        """Round-robin selection from candidates."""
        if not candidates:
            return None

        # Simple round-robin across all candidates
        current_index = self._round_robin_index.get("global", 0)
        selected = candidates[current_index % len(candidates)]
        self._round_robin_index["global"] = (current_index + 1) % len(candidates)

        return selected.metadata.name

    def _select_weighted_random(self, candidates: List[ProviderInstance]) -> Optional[str]:
        """Weighted random selection based on provider weights."""
        if not candidates:
            return None

        total_weight = sum(p.weight for p in candidates)
        if total_weight == 0:
            return random.choice(candidates).metadata.name

        pick = random.uniform(0, total_weight)
        current_weight = 0

        for provider in candidates:
            current_weight += provider.weight
            if current_weight >= pick:
                return provider.metadata.name

        return candidates[-1].metadata.name

    def _select_least_loaded(self, candidates: List[ProviderInstance]) -> Optional[str]:
        """Select provider with least active connections."""
        if not candidates:
            return None

        # Find provider with minimum active connections
        min_load = float("inf")
        selected = None

        for provider in candidates:
            provider_id = provider.metadata.name
            connections = self._connections.get(provider_id, [])
            active_count = sum(c.active_requests for c in connections)

            if active_count < min_load:
                min_load = active_count
                selected = provider

        return selected.metadata.name if selected else None

    def _select_health_priority(self, candidates: List[ProviderInstance]) -> Optional[str]:
        """Select highest health score provider."""
        if not candidates:
            return None

        # Sort by health score (reliability * weight)
        candidates.sort(key=lambda p: (p.metadata.reliability_score * p.weight), reverse=True)
        return candidates[0].metadata.name

    async def _connection_cleanup_loop(self):
        """Background task to cleanup idle connections."""
        while True:
            try:
                await self._cleanup_idle_connections()
                await asyncio.sleep(300)  # Clean up every 5 minutes
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Connection cleanup error: {e}")
                await asyncio.sleep(300)

    async def _cleanup_idle_connections(self):
        """Remove idle connections that haven't been used recently."""
        cutoff_time = time.time() - (self.config.connection_timeout * 2)
        removed_count = 0

        for provider_id, connections in list(self._connections.items()):
            active_connections = []
            for conn in connections:
                if conn.active_requests > 0 or conn.last_used > cutoff_time:
                    active_connections.append(conn)
                else:
                    removed_count += 1
                    logger.debug(f"Removed idle connection {conn.connection_id}")

            self._connections[provider_id] = active_connections

        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} idle connections")

    async def _health_monitor_loop(self):
        """Background task for connection health monitoring."""
        while True:
            try:
                await self._check_connection_health()
                await asyncio.sleep(self.config.health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health monitor error: {e}")
                await asyncio.sleep(self.config.health_check_interval)

    async def _check_connection_health(self):
        """Check health of all connections."""
        healthy_count = 0
        total_count = 0

        for provider_id, connections in self._connections.items():
            for conn in connections:
                total_count += 1
                # Simple health check - mark as healthy if recently used and no failures
                time_since_last_use = time.time() - conn.last_used
                is_recently_used = time_since_last_use < (self.config.connection_timeout * 2)
                has_low_failure_rate = (conn.failed_requests / max(1, conn.total_requests)) < 0.1

                conn.is_healthy = is_recently_used and has_low_failure_rate
                if conn.is_healthy:
                    healthy_count += 1

        self._stats.total_connections = total_count
        self._stats.healthy_connections = healthy_count
        logger.debug(f"Connection health check: {healthy_count}/{total_count} healthy")

    def get_pool_stats(self) -> ProviderPoolStats:
        """Get current pool statistics."""
        # Update calculated stats
        if self._response_times:
            self._stats.average_response_time = sum(self._response_times[-100:]) / len(
                self._response_times[-100:]
            )  # Last 100 requests
        else:
            self._stats.average_response_time = 0.0

        total_requests = self._stats.total_requests
        if total_requests > 0:
            self._stats.pool_hit_rate = (total_requests - self._stats.failed_requests) / total_requests
        else:
            self._stats.pool_hit_rate = 0.0

        return self._stats

    def get_provider_stats(self, provider_id: str) -> Dict[str, Any]:
        """Get detailed statistics for a specific provider."""
        connections = self._connections.get(provider_id, [])
        circuit_breaker = self._circuit_breakers.get(provider_id)

        return {
            "provider_id": provider_id,
            "total_connections": len(connections),
            "active_connections": sum(c.active_requests for c in connections),
            "healthy_connections": sum(1 for c in connections if c.is_healthy),
            "total_requests": sum(c.total_requests for c in connections),
            "failed_requests": sum(c.failed_requests for c in connections),
            "circuit_breaker_state": circuit_breaker.state if circuit_breaker else "none",
        }


# Global provider pool instance - created on demand
provider_pool = None
