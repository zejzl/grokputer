"""
Integration tests for MAF Provider Pool

Tests cover connection pooling, load balancing strategies, circuit breaker integration,
health monitoring, and background cleanup tasks.
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from src.collaboration.provider_pool import (
    ProviderPool,
    PoolConfig,
    PoolStrategy,
    CircuitBreaker,
    ConnectionInfo,
    ProviderPoolStats,
)
from src.collaboration.provider_registry import (
    ProviderRegistry,
    ProviderInstance,
    ProviderMetadata,
    ProviderCapability,
)


# Helper Functions

def create_test_provider_metadata(name="test_provider", capabilities=None) -> ProviderMetadata:
    """Create test ProviderMetadata."""
    if capabilities is None:
        capabilities = [ProviderCapability.TEXT_GENERATION]

    return ProviderMetadata(
        name=name,
        provider_type="grok",
        model="grok-4",
        capabilities=capabilities
    )


def create_test_provider_instance(name="test_provider", weight=1.0) -> ProviderInstance:
    """Create test ProviderInstance."""
    metadata = create_test_provider_metadata(name=name)
    client = MagicMock()

    return ProviderInstance(
        metadata=metadata,
        client=client,
        weight=weight
    )


# Provider Pool Initialization Tests

def test_provider_pool_initialization():
    """Test ProviderPool initializes with default config."""
    registry = ProviderRegistry()
    pool = ProviderPool(registry=registry)

    assert pool.config is not None
    assert pool.registry == registry
    assert pool._connections == {}
    assert pool._circuit_breakers == {}
    assert pool._round_robin_index == {}
    assert pool._cleanup_task is None
    assert pool._health_monitor_task is None


def test_provider_pool_custom_config():
    """Test ProviderPool with custom configuration."""
    config = PoolConfig(
        max_connections_per_provider=10,
        connection_timeout=60.0,
        load_balancing_strategy=PoolStrategy.LEAST_LOADED
    )
    registry = ProviderRegistry()
    pool = ProviderPool(config=config, registry=registry)

    assert pool.config == config
    assert pool.config.max_connections_per_provider == 10
    assert pool.config.connection_timeout == 60.0
    assert pool.config.load_balancing_strategy == PoolStrategy.LEAST_LOADED


# Connection Management Tests

@pytest.mark.asyncio
async def test_acquire_connection_success():
    """Test acquiring a connection successfully."""
    registry = ProviderRegistry()
    pool = ProviderPool(registry=registry)

    provider_id = "test_provider"
    connection = await pool.acquire_connection(provider_id)

    assert connection is not None
    assert connection.provider_id == provider_id
    assert connection.active_requests == 1
    assert connection.total_requests == 1
    assert connection.is_healthy is True
    assert provider_id in pool._connections
    assert len(pool._connections[provider_id]) == 1


@pytest.mark.asyncio
async def test_acquire_connection_circuit_breaker_open():
    """Test acquiring connection when circuit breaker is open."""
    registry = ProviderRegistry()
    pool = ProviderPool(registry=registry)

    provider_id = "test_provider"

    # Simulate circuit breaker open
    circuit_breaker = pool._circuit_breakers[provider_id] = CircuitBreaker()
    circuit_breaker.state = "open"

    connection = await pool.acquire_connection(provider_id)
    assert connection is None


@pytest.mark.asyncio
async def test_acquire_connection_max_limit():
    """Test acquiring connections up to the maximum limit."""
    config = PoolConfig(max_connections_per_provider=2)
    registry = ProviderRegistry()
    pool = ProviderPool(config=config, registry=registry)

    provider_id = "test_provider"

    # Acquire first connection
    conn1 = await pool.acquire_connection(provider_id)
    assert conn1 is not None

    # Acquire second connection
    conn2 = await pool.acquire_connection(provider_id)
    assert conn2 is not None

    # Third connection should be None (at limit)
    conn3 = await pool.acquire_connection(provider_id)
    assert conn3 is None

    # Release one connection
    await pool.release_connection(conn1)

    # Now should be able to acquire again
    conn4 = await pool.acquire_connection(provider_id)
    assert conn4 is not None


@pytest.mark.asyncio
async def test_release_connection():
    """Test releasing a connection."""
    registry = ProviderRegistry()
    pool = ProviderPool(registry=registry)

    provider_id = "test_provider"
    connection = await pool.acquire_connection(provider_id)
    assert connection.active_requests == 1

    await pool.release_connection(connection)
    assert connection.active_requests == 0


# Load Balancing Strategy Tests

def test_select_provider_round_robin():
    """Test round-robin provider selection."""
    registry = ProviderRegistry()

    # Register multiple providers
    provider1 = create_test_provider_instance("provider1")
    provider2 = create_test_provider_instance("provider2")
    provider3 = create_test_provider_instance("provider3")

    registry._providers["provider1"] = provider1
    registry._providers["provider2"] = provider2
    registry._providers["provider3"] = provider3

    pool = ProviderPool(registry=registry)

    # Test round-robin selection
    selected = []
    for _ in range(6):  # More than number of providers to test cycling
        provider_id = pool.select_provider(strategy=PoolStrategy.ROUND_ROBIN)
        selected.append(provider_id)

    assert selected == ["provider1", "provider2", "provider3", "provider1", "provider2", "provider3"]


def test_select_provider_weighted_random():
    """Test weighted random provider selection."""
    registry = ProviderRegistry()

    # Register providers with different weights
    provider1 = create_test_provider_instance("provider1", weight=0.5)
    provider2 = create_test_provider_instance("provider2", weight=1.0)

    registry._providers["provider1"] = provider1
    registry._providers["provider2"] = provider2

    pool = ProviderPool(registry=registry)

    # Test weighted random selection (multiple samples for statistical significance)
    selections = []
    for _ in range(100):
        provider_id = pool.select_provider(strategy=PoolStrategy.WEIGHTED_RANDOM)
        selections.append(provider_id)

    # Provider2 should be selected more often due to higher weight
    provider2_count = selections.count("provider2")
    provider1_count = selections.count("provider1")

    assert provider2_count > provider1_count  # Statistical expectation


def test_select_provider_least_loaded():
    """Test least loaded provider selection."""
    registry = ProviderRegistry()

    provider1 = create_test_provider_instance("provider1")
    provider2 = create_test_provider_instance("provider2")

    registry._providers["provider1"] = provider1
    registry._providers["provider2"] = provider2

    pool = ProviderPool(registry=registry)

    # Simulate different load levels
    pool._connections["provider1"] = [
        ConnectionInfo("provider1", "conn1", active_requests=2),
        ConnectionInfo("provider1", "conn2", active_requests=1),
    ]
    pool._connections["provider2"] = [
        ConnectionInfo("provider2", "conn3", active_requests=0),
    ]

    # Provider2 should be selected (lower load)
    selected = pool.select_provider(strategy=PoolStrategy.LEAST_LOADED)
    assert selected == "provider2"


def test_select_provider_health_priority():
    """Test health priority provider selection."""
    registry = ProviderRegistry()

    # Create providers with different health scores
    metadata1 = create_test_provider_metadata("provider1")
    metadata1.reliability_score = 0.8
    provider1 = ProviderInstance(metadata=metadata1, client=MagicMock(), weight=1.0)

    metadata2 = create_test_provider_metadata("provider2")
    metadata2.reliability_score = 0.9
    provider2 = ProviderInstance(metadata=metadata2, client=MagicMock(), weight=1.0)

    registry._providers["provider1"] = provider1
    registry._providers["provider2"] = provider2

    pool = ProviderPool(registry=registry)

    # Provider2 should be selected (higher health score)
    selected = pool.select_provider(strategy=PoolStrategy.HEALTH_PRIORITY)
    assert selected == "provider2"


def test_select_provider_with_capabilities():
    """Test provider selection with required capabilities."""
    registry = ProviderRegistry()

    # Register providers with different capabilities
    provider1 = create_test_provider_instance("provider1")
    provider1.metadata.capabilities = [ProviderCapability.TEXT_GENERATION]

    provider2 = create_test_provider_instance("provider2")
    provider2.metadata.capabilities = [ProviderCapability.CODE_ANALYSIS, ProviderCapability.CRITICAL_THINKING]

    registry._providers["provider1"] = provider1
    registry._providers["provider2"] = provider2

    pool = ProviderPool(registry=registry)

    # Select provider with TEXT_GENERATION capability
    selected = pool.select_provider(required_capabilities=[ProviderCapability.TEXT_GENERATION])
    assert selected == "provider1"

    # Select provider with CODE_ANALYSIS capability
    selected = pool.select_provider(required_capabilities=[ProviderCapability.CODE_ANALYSIS])
    assert selected == "provider2"


# Execute with Provider Tests

@pytest.mark.asyncio
async def test_execute_with_provider_success():
    """Test successful execution with provider."""
    registry = ProviderRegistry()
    pool = ProviderPool(registry=registry)

    provider_id = "test_provider"

    async def mock_operation(x, y):
        return x + y

    result = await pool.execute_with_provider(provider_id, mock_operation, 2, 3)
    assert result == 5

    # Check that connection was acquired and released
    assert provider_id in pool._connections
    connection = pool._connections[provider_id][0]
    assert connection.total_requests == 1
    assert connection.active_requests == 0  # Should be released


@pytest.mark.asyncio
async def test_execute_with_provider_failure():
    """Test execution with provider that fails."""
    registry = ProviderRegistry()
    pool = ProviderPool(registry=registry)

    provider_id = "test_provider"

    async def mock_operation():
        raise ValueError("Operation failed")

    with pytest.raises(ValueError, match="Operation failed"):
        await pool.execute_with_provider(provider_id, mock_operation)

    # Check that failure was recorded
    connection = pool._connections[provider_id][0]
    assert connection.failed_requests == 1
    assert connection.is_healthy is False

    # Check circuit breaker
    circuit_breaker = pool._circuit_breakers[provider_id]
    assert circuit_breaker.failure_count == 1


# Background Task Tests

@pytest.mark.asyncio
async def test_pool_start_stop():
    """Test starting and stopping the provider pool."""
    registry = ProviderRegistry()
    pool = ProviderPool(registry=registry)

    # Mock registry methods
    registry.start_health_monitoring = AsyncMock()
    registry.stop_health_monitoring = AsyncMock()

    await pool.start()

    assert pool._cleanup_task is not None
    assert pool._health_monitor_task is not None
    assert registry.start_health_monitoring.called

    await pool.stop()

    assert pool._cleanup_task.done()
    assert pool._health_monitor_task.done()
    assert registry.stop_health_monitoring.called


@pytest.mark.asyncio
async def test_connection_cleanup():
    """Test background connection cleanup."""
    registry = ProviderRegistry()
    config = PoolConfig(connection_timeout=1)  # Short timeout for testing
    pool = ProviderPool(config=config, registry=registry)

    provider_id = "test_provider"

    # Create a connection and simulate it being idle
    conn = ConnectionInfo(provider_id, "test_conn")
    conn.last_used = time.time() - 10  # Make it old
    pool._connections[provider_id] = [conn]

    await pool._cleanup_idle_connections()

    # Connection should be removed
    assert len(pool._connections[provider_id]) == 0


@pytest.mark.asyncio
async def test_health_monitoring():
    """Test background health monitoring."""
    registry = ProviderRegistry()
    pool = ProviderPool(registry=registry)

    provider_id = "test_provider"

    # Create connections with different health states
    healthy_conn = ConnectionInfo(provider_id, "healthy", is_healthy=True, last_used=time.time())
    unhealthy_conn = ConnectionInfo(provider_id, "unhealthy", is_healthy=True, last_used=time.time() - 100, total_requests=10, failed_requests=2)

    pool._connections[provider_id] = [healthy_conn, unhealthy_conn]

    await pool._check_connection_health()

    # Healthy connection should remain healthy
    assert healthy_conn.is_healthy is True

    # Unhealthy connection should be marked unhealthy
    assert unhealthy_conn.is_healthy is False

    # Stats should be updated
    assert pool._stats.healthy_connections == 1
    assert pool._stats.total_connections == 2


# Statistics Tests

def test_pool_stats():
    """Test pool statistics tracking."""
    registry = ProviderRegistry()
    pool = ProviderPool(registry=registry)

    stats = pool.get_pool_stats()

    assert isinstance(stats, ProviderPoolStats)
    assert stats.total_connections == 0
    assert stats.active_connections == 0
    assert stats.healthy_connections == 0
    assert stats.total_requests == 0
    assert stats.failed_requests == 0
    assert stats.average_response_time == 0.0
    assert stats.pool_hit_rate == 0.0


def test_provider_stats():
    """Test provider-specific statistics."""
    registry = ProviderRegistry()
    pool = ProviderPool(registry=registry)

    provider_id = "test_provider"

    # Create some connections with activity
    conn1 = ConnectionInfo(provider_id, "conn1", active_requests=1, total_requests=5, failed_requests=1)
    conn2 = ConnectionInfo(provider_id, "conn2", active_requests=0, total_requests=3, failed_requests=0)

    pool._connections[provider_id] = [conn1, conn2]

    # Add circuit breaker
    circuit_breaker = CircuitBreaker()
    circuit_breaker.state = "closed"
    pool._circuit_breakers[provider_id] = circuit_breaker

    stats = pool.get_provider_stats(provider_id)

    assert stats["provider_id"] == provider_id
    assert stats["total_connections"] == 2
    assert stats["active_connections"] == 1
    assert stats["healthy_connections"] == 2  # Both are healthy by default
    assert stats["total_requests"] == 8
    assert stats["failed_requests"] == 1
    assert stats["circuit_breaker_state"] == "closed"


# Error Handling Tests

@pytest.mark.asyncio
async def test_execute_with_provider_no_connection():
    """Test execution when no connection can be acquired."""
    registry = ProviderRegistry()
    config = PoolConfig(max_connections_per_provider=0)  # No connections allowed
    pool = ProviderPool(config=config, registry=registry)

    provider_id = "test_provider"

    async def mock_operation():
        return "success"

    with pytest.raises(Exception, match=f"No available connection for provider {provider_id}"):
        await pool.execute_with_provider(provider_id, mock_operation)


def test_select_provider_no_candidates():
    """Test provider selection when no candidates available."""
    registry = ProviderRegistry()
    pool = ProviderPool(registry=registry)

    # No providers registered
    selected = pool.select_provider()
    assert selected is None


def test_select_provider_unavailable_capability():
    """Test provider selection with unavailable capability."""
    registry = ProviderRegistry()

    # Register provider without the required capability
    provider = create_test_provider_instance("provider1")
    provider.metadata.capabilities = [ProviderCapability.TEXT_GENERATION]
    registry._providers["provider1"] = provider

    pool = ProviderPool(registry=registry)

    # Request unavailable capability
    selected = pool.select_provider(required_capabilities=[ProviderCapability.CREATIVE_WRITING])
    assert selected is None</content>
<parameter name="filePath">tests/collaboration/test_provider_pool.py