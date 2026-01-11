"""
Comprehensive tests for MAF Provider Registry - API-Aligned Version

Tests cover circuit breakers, health checks, provider management,
capability matching, and reliability tracking.
"""

import pytest
import time
from unittest.mock import MagicMock, Mock, patch, AsyncMock
from src.collaboration.provider_registry import (
    ProviderRegistry,
    ProviderInstance,
    ProviderMetadata,
    ProviderCapability,
    CircuitBreakerState,
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerStats,
    CircuitBreakerOpenException,
)


# Helper Functions

def create_test_metadata(
    name="test_provider",
    provider_type="grok",
    model="grok-4",
    capabilities=None
) -> ProviderMetadata:
    """Create test ProviderMetadata."""
    if capabilities is None:
        capabilities = [ProviderCapability.TEXT_GENERATION]

    return ProviderMetadata(
        name=name,
        provider_type=provider_type,
        model=model,
        capabilities=capabilities
    )


# Provider Metadata Tests

def test_provider_metadata_creation():
    """Test creating provider metadata"""
    metadata = create_test_metadata(
        name="test_provider",
        provider_type="grok",
        model="grok-4-fast-reasoning",
        capabilities=[ProviderCapability.TEXT_GENERATION, ProviderCapability.CODE_ANALYSIS]
    )

    assert metadata.name == "test_provider"
    assert metadata.provider_type == "grok"
    assert metadata.model == "grok-4-fast-reasoning"
    assert ProviderCapability.TEXT_GENERATION in metadata.capabilities
    assert ProviderCapability.CODE_ANALYSIS in metadata.capabilities


def test_provider_metadata_minimal():
    """Test creating metadata with minimal required fields"""
    metadata = ProviderMetadata(
        name="minimal_provider",
        provider_type="openai",
        model="gpt-4"
    )

    assert metadata.name == "minimal_provider"
    assert metadata.capabilities == []  # Default empty list


# Provider Instance Tests

def test_provider_instance_creation():
    """Test creating a provider instance"""
    metadata = create_test_metadata()
    client = MagicMock()

    provider = ProviderInstance(
        metadata=metadata,
        client=client
    )

    assert provider.metadata == metadata
    assert provider.client == client
    assert provider.weight == 1.0  # Default weight
    assert provider.is_active is True


def test_provider_instance_with_weight():
    """Test creating provider with custom weight"""
    metadata = create_test_metadata()
    client = MagicMock()

    provider = ProviderInstance(
        metadata=metadata,
        client=client,
        weight=0.8
    )

    assert provider.weight == 0.8


# Provider Capability Tests

def test_provider_capabilities_exist():
    """Test that all expected capabilities are defined"""
    assert ProviderCapability.TEXT_GENERATION
    assert ProviderCapability.CODE_ANALYSIS
    assert ProviderCapability.CRITICAL_THINKING
    assert ProviderCapability.CREATIVE_WRITING
    assert ProviderCapability.RESEARCH
    assert ProviderCapability.VALIDATION
    assert ProviderCapability.SYNTHESIS


# Circuit Breaker Config Tests

def test_circuit_breaker_config_defaults():
    """Test CircuitBreakerConfig default values"""
    config = CircuitBreakerConfig()

    assert config.failure_threshold == 5
    assert config.recovery_timeout == 60.0
    assert config.success_threshold == 3


def test_circuit_breaker_config_custom():
    """Test CircuitBreakerConfig with custom values"""
    config = CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=30.0,
        success_threshold=2
    )

    assert config.failure_threshold == 3
    assert config.recovery_timeout == 30.0
    assert config.success_threshold == 2


# Circuit Breaker Tests

def test_circuit_breaker_initialization():
    """Test circuit breaker initializes in CLOSED state"""
    config = CircuitBreakerConfig(failure_threshold=5, recovery_timeout=60.0)
    cb = CircuitBreaker(config)

    assert cb.state == CircuitBreakerState.CLOSED
    assert cb.stats.consecutive_failures == 0
    assert cb.config.failure_threshold == 5


def test_circuit_breaker_default_config():
    """Test circuit breaker with default config"""
    cb = CircuitBreaker()

    assert cb.state == CircuitBreakerState.CLOSED
    assert cb.config.failure_threshold == 5


def test_circuit_breaker_stats_tracking():
    """Test circuit breaker tracks statistics"""
    cb = CircuitBreaker()

    assert cb.stats.total_requests == 0
    assert cb.stats.successful_requests == 0
    assert cb.stats.failed_requests == 0


# Circuit Breaker State Tests

def test_circuit_breaker_states_exist():
    """Test that all circuit breaker states are defined"""
    assert CircuitBreakerState.CLOSED
    assert CircuitBreakerState.OPEN
    assert CircuitBreakerState.HALF_OPEN


def test_circuit_breaker_state_values():
    """Test circuit breaker state values"""
    assert CircuitBreakerState.CLOSED.value == "closed"
    assert CircuitBreakerState.OPEN.value == "open"
    assert CircuitBreakerState.HALF_OPEN.value == "half_open"


# Provider Registry Tests

def test_provider_registry_initialization():
    """Test provider registry initializes empty"""
    registry = ProviderRegistry()

    assert len(registry._providers) == 0


def test_provider_registry_register_provider():
    """Test registering a provider"""
    registry = ProviderRegistry()

    metadata = create_test_metadata(
        name="provider1",
        capabilities=[ProviderCapability.TEXT_GENERATION]
    )
    client = MagicMock()

    result = registry.register_provider("provider1", client, metadata)

    assert result is True
    assert "provider1" in registry._providers
    retrieved = registry.get_provider("provider1")
    assert retrieved is not None
    assert retrieved.metadata.name == "provider1"


def test_provider_registry_get_provider():
    """Test getting a provider by ID"""
    registry = ProviderRegistry()

    metadata = create_test_metadata(name="provider1")
    client = MagicMock()
    registry.register_provider("provider1", client, metadata)

    retrieved = registry.get_provider("provider1")
    assert retrieved is not None
    assert retrieved.metadata.name == "provider1"


def test_provider_registry_get_nonexistent_provider():
    """Test getting a provider that doesn't exist returns None"""
    registry = ProviderRegistry()

    result = registry.get_provider("nonexistent")
    assert result is None


def test_provider_registry_filter_by_capability():
    """Test filtering providers by capability"""
    registry = ProviderRegistry()

    metadata1 = create_test_metadata(
        name="provider1",
        capabilities=[ProviderCapability.TEXT_GENERATION, ProviderCapability.CODE_ANALYSIS]
    )
    client1 = MagicMock()
    registry.register_provider("provider1", client1, metadata1)

    metadata2 = create_test_metadata(
        name="provider2",
        capabilities=[ProviderCapability.CREATIVE_WRITING]
    )
    client2 = MagicMock()
    registry.register_provider("provider2", client2, metadata2)

    text_providers = registry.get_providers_by_capability(ProviderCapability.TEXT_GENERATION, only_healthy=False)
    assert len(text_providers) >= 1
    assert any(p.metadata.name == "provider1" for p in text_providers)


def test_provider_registry_multiple_capabilities():
    """Test provider with multiple capabilities"""
    registry = ProviderRegistry()

    metadata = create_test_metadata(
        name="provider1",
        capabilities=[
            ProviderCapability.TEXT_GENERATION,
            ProviderCapability.CODE_ANALYSIS,
            ProviderCapability.CRITICAL_THINKING
        ]
    )
    client = MagicMock()
    registry.register_provider("provider1", client, metadata)

    # Should be retrievable by any of its capabilities
    for cap in metadata.capabilities:
        matching = registry.get_providers_by_capability(cap, only_healthy=False)
        assert any(p.metadata.name == "provider1" for p in matching)


def test_circuit_breaker_open_exception():
    """Test CircuitBreakerOpenException"""
    exception = CircuitBreakerOpenException("Circuit breaker is open")

    assert "open" in str(exception).lower()
    assert isinstance(exception, Exception)


def test_provider_registry_circuit_breakers_enabled():
    """Test that circuit breakers can be enabled"""
    registry = ProviderRegistry(enable_circuit_breakers=True)
    assert registry._enable_circuit_breakers is True


def test_provider_registry_circuit_breakers_disabled():
    """Test that circuit breakers can be disabled"""
    registry = ProviderRegistry(enable_circuit_breakers=False)
    assert registry._enable_circuit_breakers is False


def test_circuit_breaker_stats_initialization():
    """Test CircuitBreakerStats initialization"""
    stats = CircuitBreakerStats()

    assert stats.total_requests == 0
    assert stats.successful_requests == 0
    assert stats.failed_requests == 0
    assert stats.consecutive_failures == 0
    assert stats.consecutive_successes == 0
    assert stats.last_failure_time is None
    assert stats.last_success_time is None


def test_provider_registry_list_all():
    """Test listing all registered providers"""
    registry = ProviderRegistry()

    metadata1 = create_test_metadata(name="provider1")
    client1 = MagicMock()
    registry.register_provider("provider1", client1, metadata1)

    metadata2 = create_test_metadata(
        name="provider2",
        provider_type="claude",
        model="claude-3-opus"
    )
    client2 = MagicMock()
    registry.register_provider("provider2", client2, metadata2)

    all_providers = list(registry._providers.values())
    assert len(all_providers) == 2


def test_provider_capability_enum_values():
    """Test provider capability enum values"""
    assert ProviderCapability.TEXT_GENERATION.value == "text_generation"
    assert ProviderCapability.CODE_ANALYSIS.value == "code_analysis"
    assert ProviderCapability.CRITICAL_THINKING.value == "critical_thinking"
    assert ProviderCapability.CREATIVE_WRITING.value == "creative_writing"
    assert ProviderCapability.RESEARCH.value == "research"
    assert ProviderCapability.VALIDATION.value == "validation"
    assert ProviderCapability.SYNTHESIS.value == "synthesis"
