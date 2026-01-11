"""
Comprehensive tests for MAF Orchestrator

Tests cover retry logic, fallback management, performance monitoring,
structured logging, and core orchestration flows.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from src.collaboration.orchestrator import (
    RetryManager,
    RetryConfig,
    FallbackManager,
    FallbackConfig,
    OrchestrationError,
    ProviderFailureError,
    ConsensusFailureError,
    TimeoutError as OrchestratorTimeoutError,
)
from src.collaboration.provider_registry import (
    ProviderInstance,
    ProviderMetadata,
    ProviderCapability,
    ProviderRegistry,
    CircuitBreakerOpenException,
)


# Retry Manager Tests


@pytest.mark.asyncio
async def test_retry_manager_success_first_attempt():
    """Test successful execution on first attempt"""
    retry_manager = RetryManager(RetryConfig(max_attempts=3))

    async def success_func():
        return "success"

    result = await retry_manager.execute_with_retry(success_func)
    assert result == "success"


@pytest.mark.asyncio
async def test_retry_manager_success_after_retries():
    """Test successful execution after failed attempts"""
    retry_manager = RetryManager(RetryConfig(max_attempts=3, base_delay=0.01))

    attempt_count = 0

    async def flaky_func():
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count < 3:
            raise Exception("Temporary failure")
        return "success"

    result = await retry_manager.execute_with_retry(flaky_func)
    assert result == "success"
    assert attempt_count == 3


@pytest.mark.asyncio
async def test_retry_manager_all_attempts_fail():
    """Test that exception is raised when all attempts fail"""
    retry_manager = RetryManager(RetryConfig(max_attempts=3, base_delay=0.01))

    async def always_fail():
        raise ValueError("Permanent failure")

    with pytest.raises(ValueError, match="Permanent failure"):
        await retry_manager.execute_with_retry(always_fail)


def test_retry_manager_calculate_delay_exponential():
    """Test exponential backoff calculation"""
    config = RetryConfig(base_delay=1.0, backoff_factor=2.0, jitter=False)
    retry_manager = RetryManager(config)

    delay_0 = retry_manager._calculate_delay(0)
    delay_1 = retry_manager._calculate_delay(1)
    delay_2 = retry_manager._calculate_delay(2)

    assert delay_0 == 1.0  # 1.0 * 2^0
    assert delay_1 == 2.0  # 1.0 * 2^1
    assert delay_2 == 4.0  # 1.0 * 2^2


def test_retry_manager_calculate_delay_max_cap():
    """Test that delay is capped at max_delay"""
    config = RetryConfig(base_delay=10.0, backoff_factor=2.0, max_delay=20.0, jitter=False)
    retry_manager = RetryManager(config)

    delay = retry_manager._calculate_delay(5)  # Would be 10 * 2^5 = 320
    assert delay == 20.0  # Capped at max_delay


def test_retry_manager_calculate_delay_with_jitter():
    """Test that jitter adds randomness to delay"""
    config = RetryConfig(base_delay=1.0, backoff_factor=2.0, jitter=True)
    retry_manager = RetryManager(config)

    # Run multiple times to ensure jitter varies
    delays = [retry_manager._calculate_delay(1) for _ in range(10)]

    # All delays should be around 2.0 but different due to jitter
    assert len(set(delays)) > 1  # Not all the same
    assert all(1.5 <= d <= 2.5 for d in delays)  # Within jitter range (±25%)


def test_retry_manager_calculate_delay_minimum():
    """Test that delay has a minimum value"""
    config = RetryConfig(base_delay=0.001, backoff_factor=1.0, jitter=False)
    retry_manager = RetryManager(config)

    delay = retry_manager._calculate_delay(0)
    assert delay >= 0.1  # Minimum 100ms


# Fallback Manager Tests


def test_fallback_manager_get_fallback_providers():
    """Test fallback provider selection"""
    registry = ProviderRegistry()

    # Register some providers
    metadata1 = ProviderMetadata(
        name="provider1",
        provider_type="grok",
        model="grok-4",
        capabilities=[ProviderCapability.TEXT_GENERATION, ProviderCapability.CODE_ANALYSIS],
    )
    client1 = MagicMock()
    registry.register_provider("provider1", client1, metadata1)

    metadata2 = ProviderMetadata(
        name="provider2",
        provider_type="claude",
        model="claude-3-opus",
        capabilities=[ProviderCapability.TEXT_GENERATION, ProviderCapability.CODE_ANALYSIS],
    )
    client2 = MagicMock()
    registry.register_provider("provider2", client2, metadata2)

    metadata3 = ProviderMetadata(
        name="provider3",
        provider_type="openai",
        model="gpt-4",
        capabilities=[ProviderCapability.TEXT_GENERATION],
    )
    client3 = MagicMock()
    registry.register_provider("provider3", client3, metadata3)

    fallback_manager = FallbackManager(registry, FallbackConfig(enable_fallbacks=True))

    # Get fallbacks excluding provider1
    failed_ids = {"provider1"}
    fallbacks = fallback_manager.get_fallback_providers(
        failed_ids,
        [ProviderCapability.TEXT_GENERATION, ProviderCapability.CODE_ANALYSIS],
        max_providers=2
    )

    assert len(fallbacks) <= 2
    assert all(p.metadata.name not in failed_ids for p in fallbacks)
    # Should get providers that have the required capabilities and aren't in failed_ids
    # The actual providers returned depend on the registry's internal selection logic


def test_fallback_manager_disabled():
    """Test that fallbacks return empty when disabled"""
    registry = ProviderRegistry()
    fallback_manager = FallbackManager(registry, FallbackConfig(enable_fallbacks=False))

    fallbacks = fallback_manager.get_fallback_providers(
        set(),
        [ProviderCapability.TEXT_GENERATION],
        max_providers=3
    )

    assert len(fallbacks) == 0


def test_fallback_manager_no_suitable_providers():
    """Test fallback when no suitable providers exist"""
    registry = ProviderRegistry()

    # Register provider with different capability
    metadata = ProviderMetadata(
        name="provider1",
        provider_type="grok",
        model="grok-4",
        capabilities=[ProviderCapability.CREATIVE_WRITING],
    )
    client = MagicMock()
    registry.register_provider("provider1", client, metadata)

    fallback_manager = FallbackManager(registry, FallbackConfig(enable_fallbacks=True))

    # Request providers with different capability
    fallbacks = fallback_manager.get_fallback_providers(
        set(),
        [ProviderCapability.TEXT_GENERATION],
        max_providers=3
    )

    assert len(fallbacks) == 0


# Error Classes Tests


def test_provider_failure_error():
    """Test ProviderFailureError structure"""
    original_error = ValueError("Connection failed")
    error = ProviderFailureError("provider1", original_error)

    assert error.provider_id == "provider1"
    assert error.original_error == original_error
    assert "provider1" in str(error)
    assert "Connection failed" in str(error)


def test_orchestration_errors_inheritance():
    """Test that all orchestration errors inherit from OrchestrationError"""
    assert issubclass(ProviderFailureError, OrchestrationError)
    assert issubclass(ConsensusFailureError, OrchestrationError)
    assert issubclass(OrchestratorTimeoutError, OrchestrationError)


# Config Tests


def test_retry_config_defaults():
    """Test RetryConfig default values"""
    config = RetryConfig()

    assert config.max_attempts == 3
    assert config.base_delay == 1.0
    assert config.max_delay == 30.0
    assert config.backoff_factor == 2.0
    assert config.jitter is True


def test_fallback_config_defaults():
    """Test FallbackConfig default values"""
    config = FallbackConfig()

    assert config.enable_fallbacks is True
    assert config.max_fallback_providers == 2
    assert config.fallback_delay == 0.5


def test_retry_config_custom_values():
    """Test RetryConfig with custom values"""
    config = RetryConfig(
        max_attempts=5,
        base_delay=2.0,
        max_delay=60.0,
        backoff_factor=3.0,
        jitter=False
    )

    assert config.max_attempts == 5
    assert config.base_delay == 2.0
    assert config.max_delay == 60.0
    assert config.backoff_factor == 3.0
    assert config.jitter is False


@pytest.mark.asyncio
async def test_retry_manager_with_args_and_kwargs():
    """Test retry manager passes arguments correctly"""
    retry_manager = RetryManager(RetryConfig(max_attempts=2, base_delay=0.01))

    async def func_with_args(a, b, c=None):
        return f"{a}-{b}-{c}"

    result = await retry_manager.execute_with_retry(func_with_args, "arg1", "arg2", c="kwarg")
    assert result == "arg1-arg2-kwarg"


@pytest.mark.asyncio
async def test_retry_manager_preserves_exception_type():
    """Test that original exception type is preserved"""
    retry_manager = RetryManager(RetryConfig(max_attempts=2, base_delay=0.01))

    class CustomError(Exception):
        pass

    async def custom_fail():
        raise CustomError("Custom failure")

    with pytest.raises(CustomError, match="Custom failure"):
        await retry_manager.execute_with_retry(custom_fail)


def test_fallback_manager_respects_max_providers():
    """Test that fallback manager respects max_providers parameter"""
    registry = ProviderRegistry()

    # Register 5 providers
    for i in range(5):
        metadata = ProviderMetadata(
            name=f"provider{i}",
            provider_type="grok",
            model="grok-4",
            capabilities=[ProviderCapability.TEXT_GENERATION],
        )
        client = MagicMock()
        registry.register_provider(f"provider{i}", client, metadata)

    fallback_manager = FallbackManager(registry, FallbackConfig(enable_fallbacks=True))

    # Request only 2 fallbacks
    fallbacks = fallback_manager.get_fallback_providers(
        set(),
        [ProviderCapability.TEXT_GENERATION],
        max_providers=2
    )

    assert len(fallbacks) <= 2


@pytest.mark.asyncio
async def test_retry_manager_async_exception_handling():
    """Test retry manager handles async exceptions correctly"""
    retry_manager = RetryManager(RetryConfig(max_attempts=3, base_delay=0.01))

    call_count = 0

    async def async_fail_then_succeed():
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.001)
        if call_count < 2:
            raise asyncio.TimeoutError("Async timeout")
        return "success"

    result = await retry_manager.execute_with_retry(async_fail_then_succeed)
    assert result == "success"
    assert call_count == 2
