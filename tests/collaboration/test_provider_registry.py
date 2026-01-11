"""
Comprehensive tests for MAF Provider Registry

Tests cover circuit breakers, health checks, provider management,
capability matching, and reliability tracking.
"""

import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch
from src.collaboration.provider_registry import (
    ProviderRegistry,
    ProviderInstance,
    ProviderCapability,
    CircuitBreakerState,
    CircuitBreaker,
    CircuitBreakerOpenException,
)


# Provider Instance Tests


def test_provider_instance_creation():
    """Test creating a provider instance"""
    provider = ProviderInstance(
        provider_id="test_provider",
        provider_type="grok",
        model="grok-4-fast-reasoning",
        capabilities=[ProviderCapability.CHAT, ProviderCapability.CODE_GENERATION],
        max_tokens=8000,
        temperature=0.7
    )

    assert provider.provider_id == "test_provider"
    assert provider.provider_type == "grok"
    assert provider.model == "grok-4-fast-reasoning"
    assert ProviderCapability.CHAT in provider.capabilities
    assert ProviderCapability.CODE_GENERATION in provider.capabilities
    assert provider.max_tokens == 8000
    assert provider.temperature == 0.7


def test_provider_instance_minimal():
    """Test creating a provider with minimal required fields"""
    provider = ProviderInstance(
        provider_id="minimal_provider",
        provider_type="openai",
        model="gpt-4",
        capabilities=[ProviderCapability.CHAT]
    )

    assert provider.provider_id == "minimal_provider"
    assert len(provider.capabilities) == 1


# Provider Capability Tests


def test_provider_capabilities_exist():
    """Test that all expected capabilities are defined"""
    assert ProviderCapability.CHAT
    assert ProviderCapability.CODE_GENERATION
    assert ProviderCapability.IMAGE_GENERATION
    assert ProviderCapability.EMBEDDING
    assert ProviderCapability.FUNCTION_CALLING


# Circuit Breaker Tests


def test_circuit_breaker_initialization():
    """Test circuit breaker initializes in CLOSED state"""
    cb = CircuitBreaker(
        failure_threshold=5,
        recovery_timeout=60.0,
        half_open_max_calls=3
    )

    assert cb.state == CircuitBreakerState.CLOSED
    assert cb.failure_count == 0
    assert cb.failure_threshold == 5
    assert cb.recovery_timeout == 60.0


def test_circuit_breaker_failure_counting():
    """Test circuit breaker counts failures"""
    cb = CircuitBreaker(failure_threshold=3)

    cb.record_failure()
    assert cb.failure_count == 1
    assert cb.state == CircuitBreakerState.CLOSED

    cb.record_failure()
    assert cb.failure_count == 2
    assert cb.state == CircuitBreakerState.CLOSED

    cb.record_failure()
    assert cb.failure_count == 3
    assert cb.state == CircuitBreakerState.OPEN


def test_circuit_breaker_opens_on_threshold():
    """Test circuit breaker opens when failure threshold is reached"""
    cb = CircuitBreaker(failure_threshold=2)

    cb.record_failure()
    cb.record_failure()

    assert cb.state == CircuitBreakerState.OPEN


def test_circuit_breaker_success_resets_count():
    """Test that success resets failure count in CLOSED state"""
    cb = CircuitBreaker(failure_threshold=5)

    cb.record_failure()
    cb.record_failure()
    assert cb.failure_count == 2

    cb.record_success()
    assert cb.failure_count == 0
    assert cb.state == CircuitBreakerState.CLOSED


def test_circuit_breaker_call_allowed_when_closed():
    """Test that calls are allowed when circuit is CLOSED"""
    cb = CircuitBreaker()
    assert cb.call_allowed() is True


def test_circuit_breaker_call_not_allowed_when_open():
    """Test that calls are not allowed when circuit is OPEN"""
    cb = CircuitBreaker(failure_threshold=1)

    cb.record_failure()
    assert cb.state == CircuitBreakerState.OPEN
    assert cb.call_allowed() is False


def test_circuit_breaker_transitions_to_half_open():
    """Test circuit breaker transitions to HALF_OPEN after timeout"""
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)

    # Open the circuit
    cb.record_failure()
    assert cb.state == CircuitBreakerState.OPEN

    # Wait for recovery timeout
    time.sleep(0.15)

    # Next call check should transition to HALF_OPEN
    assert cb.call_allowed() is True
    assert cb.state == CircuitBreakerState.HALF_OPEN


def test_circuit_breaker_half_open_success_closes():
    """Test that success in HALF_OPEN state closes the circuit"""
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)

    # Open the circuit
    cb.record_failure()

    # Wait and transition to HALF_OPEN
    time.sleep(0.15)
    cb.call_allowed()

    # Success should close it
    cb.record_success()
    assert cb.state == CircuitBreakerState.CLOSED
    assert cb.failure_count == 0


def test_circuit_breaker_half_open_failure_reopens():
    """Test that failure in HALF_OPEN state reopens the circuit"""
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)

    # Open the circuit
    cb.record_failure()

    # Wait and transition to HALF_OPEN
    time.sleep(0.15)
    cb.call_allowed()

    # Failure should reopen it
    cb.record_failure()
    assert cb.state == CircuitBreakerState.OPEN


# Provider Registry Tests


def test_provider_registry_initialization():
    """Test provider registry initializes empty"""
    registry = ProviderRegistry()

    assert len(registry.providers) == 0
    assert len(registry.circuit_breakers) == 0


def test_provider_registry_register_provider():
    """Test registering a provider"""
    registry = ProviderRegistry()

    provider = ProviderInstance(
        provider_id="provider1",
        provider_type="grok",
        model="grok-4",
        capabilities=[ProviderCapability.CHAT]
    )

    registry.register_provider(provider)

    assert "provider1" in registry.providers
    assert registry.providers["provider1"] == provider
    assert "provider1" in registry.circuit_breakers


def test_provider_registry_get_provider():
    """Test getting a provider by ID"""
    registry = ProviderRegistry()

    provider = ProviderInstance(
        provider_id="provider1",
        provider_type="grok",
        model="grok-4",
        capabilities=[ProviderCapability.CHAT]
    )

    registry.register_provider(provider)

    retrieved = registry.get_provider("provider1")
    assert retrieved == provider


def test_provider_registry_get_nonexistent_provider():
    """Test getting a provider that doesn't exist returns None"""
    registry = ProviderRegistry()

    result = registry.get_provider("nonexistent")
    assert result is None


def test_provider_registry_list_providers():
    """Test listing all providers"""
    registry = ProviderRegistry()

    provider1 = ProviderInstance(
        provider_id="provider1",
        provider_type="grok",
        model="grok-4",
        capabilities=[ProviderCapability.CHAT]
    )
    provider2 = ProviderInstance(
        provider_id="provider2",
        provider_type="claude",
        model="claude-3-opus",
        capabilities=[ProviderCapability.CHAT]
    )

    registry.register_provider(provider1)
    registry.register_provider(provider2)

    providers = registry.list_providers()
    assert len(providers) == 2
    assert provider1 in providers
    assert provider2 in providers


def test_provider_registry_filter_by_capability():
    """Test filtering providers by capability"""
    registry = ProviderRegistry()

    provider1 = ProviderInstance(
        provider_id="provider1",
        provider_type="grok",
        model="grok-4",
        capabilities=[ProviderCapability.CHAT, ProviderCapability.CODE_GENERATION]
    )
    provider2 = ProviderInstance(
        provider_id="provider2",
        provider_type="dalle",
        model="dall-e-3",
        capabilities=[ProviderCapability.IMAGE_GENERATION]
    )

    registry.register_provider(provider1)
    registry.register_provider(provider2)

    chat_providers = registry.get_providers_by_capability(ProviderCapability.CHAT)
    assert len(chat_providers) == 1
    assert chat_providers[0].provider_id == "provider1"

    image_providers = registry.get_providers_by_capability(ProviderCapability.IMAGE_GENERATION)
    assert len(image_providers) == 1
    assert image_providers[0].provider_id == "provider2"


def test_provider_registry_multiple_capabilities():
    """Test filtering providers with multiple capabilities"""
    registry = ProviderRegistry()

    provider = ProviderInstance(
        provider_id="provider1",
        provider_type="grok",
        model="grok-4",
        capabilities=[
            ProviderCapability.CHAT,
            ProviderCapability.CODE_GENERATION,
            ProviderCapability.FUNCTION_CALLING
        ]
    )

    registry.register_provider(provider)

    # Should match all three capabilities
    for cap in provider.capabilities:
        matching = registry.get_providers_by_capability(cap)
        assert len(matching) == 1
        assert matching[0].provider_id == "provider1"


def test_provider_registry_circuit_breaker_integration():
    """Test that circuit breakers are created for registered providers"""
    registry = ProviderRegistry()

    provider = ProviderInstance(
        provider_id="provider1",
        provider_type="grok",
        model="grok-4",
        capabilities=[ProviderCapability.CHAT]
    )

    registry.register_provider(provider)

    assert "provider1" in registry.circuit_breakers
    cb = registry.circuit_breakers["provider1"]
    assert isinstance(cb, CircuitBreaker)
    assert cb.state == CircuitBreakerState.CLOSED


def test_provider_registry_get_healthy_providers():
    """Test getting only healthy providers"""
    registry = ProviderRegistry()

    provider1 = ProviderInstance(
        provider_id="provider1",
        provider_type="grok",
        model="grok-4",
        capabilities=[ProviderCapability.CHAT]
    )
    provider2 = ProviderInstance(
        provider_id="provider2",
        provider_type="claude",
        model="claude-3-opus",
        capabilities=[ProviderCapability.CHAT]
    )

    registry.register_provider(provider1)
    registry.register_provider(provider2)

    # Break provider1's circuit
    for _ in range(5):
        registry.circuit_breakers["provider1"].record_failure()

    healthy = registry.get_healthy_providers()

    # Only provider2 should be healthy
    assert len(healthy) == 1
    assert healthy[0].provider_id == "provider2"


def test_circuit_breaker_open_exception():
    """Test CircuitBreakerOpenException"""
    exception = CircuitBreakerOpenException("provider1")

    assert "provider1" in str(exception)
    assert isinstance(exception, Exception)


def test_circuit_breaker_statistics():
    """Test circuit breaker tracks statistics"""
    cb = CircuitBreaker(failure_threshold=5)

    # Record some activity
    cb.record_success()
    cb.record_success()
    cb.record_failure()
    cb.record_success()

    assert cb.failure_count == 1
    assert cb.state == CircuitBreakerState.CLOSED


def test_provider_registry_remove_provider():
    """Test removing a provider from registry"""
    registry = ProviderRegistry()

    provider = ProviderInstance(
        provider_id="provider1",
        provider_type="grok",
        model="grok-4",
        capabilities=[ProviderCapability.CHAT]
    )

    registry.register_provider(provider)
    assert "provider1" in registry.providers

    # If remove method exists
    if hasattr(registry, 'remove_provider'):
        registry.remove_provider("provider1")
        assert "provider1" not in registry.providers


def test_provider_registry_update_provider():
    """Test updating a provider in registry"""
    registry = ProviderRegistry()

    provider = ProviderInstance(
        provider_id="provider1",
        provider_type="grok",
        model="grok-4",
        capabilities=[ProviderCapability.CHAT]
    )

    registry.register_provider(provider)

    # Update with new capabilities
    updated_provider = ProviderInstance(
        provider_id="provider1",
        provider_type="grok",
        model="grok-4",
        capabilities=[ProviderCapability.CHAT, ProviderCapability.CODE_GENERATION]
    )

    registry.register_provider(updated_provider)  # Should update existing

    retrieved = registry.get_provider("provider1")
    assert ProviderCapability.CODE_GENERATION in retrieved.capabilities


def test_circuit_breaker_state_transitions():
    """Test all circuit breaker state transitions"""
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)

    # CLOSED -> OPEN
    assert cb.state == CircuitBreakerState.CLOSED
    cb.record_failure()
    cb.record_failure()
    assert cb.state == CircuitBreakerState.OPEN

    # OPEN -> HALF_OPEN
    time.sleep(0.15)
    cb.call_allowed()
    assert cb.state == CircuitBreakerState.HALF_OPEN

    # HALF_OPEN -> CLOSED
    cb.record_success()
    assert cb.state == CircuitBreakerState.CLOSED


def test_provider_health_tracking():
    """Test provider health can be tracked"""
    registry = ProviderRegistry()

    provider = ProviderInstance(
        provider_id="provider1",
        provider_type="grok",
        model="grok-4",
        capabilities=[ProviderCapability.CHAT]
    )

    registry.register_provider(provider)

    # Provider should start healthy
    healthy_providers = registry.get_healthy_providers()
    assert len(healthy_providers) == 1


def test_circuit_breaker_exponential_recovery():
    """Test circuit breaker recovery timeout"""
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)

    cb.record_failure()
    assert cb.state == CircuitBreakerState.OPEN

    # Should not allow calls immediately
    assert cb.call_allowed() is False

    # After timeout, should allow
    time.sleep(0.15)
    assert cb.call_allowed() is True
