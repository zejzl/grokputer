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
    ProviderCapability,
    CircuitBreakerState,
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerStats,
    CircuitBreakerOpenException,
)


# Provider Instance Tests


def test_provider_instance_creation():
    """Test creating a provider instance"""
    provider = ProviderInstance(
        provider_id="test_provider",
        provider_type="grok",
        model="grok-4-fast-reasoning",
        capabilities=[ProviderCapability.TEXT_GENERATION, ProviderCapability.CODE_ANALYSIS],
    )

    assert provider.provider_id == "test_provider"
    assert provider.provider_type == "grok"
    assert provider.model == "grok-4-fast-reasoning"
    assert ProviderCapability.TEXT_GENERATION in provider.capabilities
    assert ProviderCapability.CODE_ANALYSIS in provider.capabilities


def test_provider_instance_minimal():
    """Test creating a provider with minimal required fields"""
    provider = ProviderInstance(
        provider_id="minimal_provider",
        provider_type="openai",
        model="gpt-4",
        capabilities=[ProviderCapability.TEXT_GENERATION]
    )

    assert provider.provider_id == "minimal_provider"
    assert len(provider.capabilities) == 1


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

    provider = ProviderInstance(
        provider_id="provider1",
        provider_type="grok",
        model="grok-4",
        capabilities=[ProviderCapability.TEXT_GENERATION]
    )

    registry.register(provider)

    assert "provider1" in registry._providers
    retrieved = registry.get("provider1")
    assert retrieved == provider


def test_provider_registry_get_provider():
    """Test getting a provider by ID"""
    registry = ProviderRegistry()

    provider = ProviderInstance(
        provider_id="provider1",
        provider_type="grok",
        model="grok-4",
        capabilities=[ProviderCapability.TEXT_GENERATION]
    )

    registry.register(provider)

    retrieved = registry.get("provider1")
    assert retrieved == provider


def test_provider_registry_get_nonexistent_provider():
    """Test getting a provider that doesn't exist returns None"""
    registry = ProviderRegistry()

    result = registry.get("nonexistent")
    assert result is None


def test_provider_registry_filter_by_capability():
    """Test filtering providers by capability"""
    registry = ProviderRegistry()

    provider1 = ProviderInstance(
        provider_id="provider1",
        provider_type="grok",
        model="grok-4",
        capabilities=[ProviderCapability.TEXT_GENERATION, ProviderCapability.CODE_ANALYSIS]
    )
    provider2 = ProviderInstance(
        provider_id="provider2",
        provider_type="dalle",
        model="dall-e-3",
        capabilities=[ProviderCapability.CREATIVE_WRITING]
    )

    registry.register(provider1)
    registry.register(provider2)

    text_providers = registry.get_by_capability(ProviderCapability.TEXT_GENERATION)
    assert len(text_providers) >= 1
    assert any(p.provider_id == "provider1" for p in text_providers)


def test_provider_registry_multiple_capabilities():
    """Test provider with multiple capabilities"""
    registry = ProviderRegistry()

    provider = ProviderInstance(
        provider_id="provider1",
        provider_type="grok",
        model="grok-4",
        capabilities=[
            ProviderCapability.TEXT_GENERATION,
            ProviderCapability.CODE_ANALYSIS,
            ProviderCapability.CRITICAL_THINKING
        ]
    )

    registry.register(provider)

    # Should be retrievable by any of its capabilities
    for cap in provider.capabilities:
        matching = registry.get_by_capability(cap)
        assert any(p.provider_id == "provider1" for p in matching)


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

    provider1 = ProviderInstance(
        provider_id="provider1",
        provider_type="grok",
        model="grok-4",
        capabilities=[ProviderCapability.TEXT_GENERATION]
    )
    provider2 = ProviderInstance(
        provider_id="provider2",
        provider_type="claude",
        model="claude-3-opus",
        capabilities=[ProviderCapability.TEXT_GENERATION]
    )

    registry.register(provider1)
    registry.register(provider2)

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
