"""
Unit tests for DeadlockDetector.
"""

import pytest
import asyncio
import time
from src.observability.deadlock_detector import DeadlockDetector, DeadlockError


@pytest.mark.asyncio
async def test_register_agent():
    """Test agent registration."""
    detector = DeadlockDetector(timeout_seconds=5.0)

    detector.register_agent("observer")
    assert "observer" in detector.agent_states
    assert detector.agent_states["observer"].agent_id == "observer"


@pytest.mark.asyncio
async def test_update_activity():
    """Test activity tracking."""
    detector = DeadlockDetector(timeout_seconds=5.0)
    detector.register_agent("observer")

    before = detector.agent_states["observer"].last_activity
    await asyncio.sleep(0.1)

    detector.update_activity("observer", state="processing")

    after = detector.agent_states["observer"].last_activity
    assert after > before
    assert detector.agent_states["observer"].state == "processing"
    assert detector.agent_states["observer"].message_count == 1


@pytest.mark.asyncio
async def test_no_deadlock_when_active():
    """Test that active agents don't trigger deadlock."""
    detector = DeadlockDetector(timeout_seconds=1.0, check_interval=0.5)
    detector.register_agent("observer")

    # Start monitoring
    monitor_task = asyncio.create_task(detector.monitor())

    try:
        # Keep agent active
        for _ in range(3):
            detector.update_activity("observer")
            await asyncio.sleep(0.3)

        # Should not raise deadlock
        assert detector.deadlocks_detected == 0

    finally:
        await detector.stop()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass


@pytest.mark.asyncio
async def test_deadlock_detection():
    """Test that inactive agents trigger deadlock."""
    detector = DeadlockDetector(timeout_seconds=0.5, check_interval=0.3)
    detector.register_agent("observer")

    # Start monitoring
    await detector.start()

    try:
        # Wait for deadlock to be detected
        with pytest.raises(DeadlockError) as exc_info:
            await detector.monitor_task

        assert "observer" in str(exc_info.value)
        assert detector.deadlocks_detected == 1

    finally:
        await detector.stop()


@pytest.mark.asyncio
async def test_deadlock_callback():
    """Test custom deadlock handler."""
    callback_called = False
    stuck_agents_list = []

    async def custom_handler(stuck_agents):
        nonlocal callback_called, stuck_agents_list
        callback_called = True
        stuck_agents_list = stuck_agents

    detector = DeadlockDetector(
        timeout_seconds=0.5,
        check_interval=0.3,
        on_deadlock=custom_handler
    )
    detector.register_agent("observer")

    await detector.start()

    try:
        with pytest.raises(DeadlockError):
            await detector.monitor_task

        assert callback_called
        assert len(stuck_agents_list) == 1
        assert stuck_agents_list[0][0] == "observer"
        assert detector.deadlocks_recovered == 1

    finally:
        await detector.stop()


@pytest.mark.asyncio
async def test_unregister_agent():
    """Test agent unregistration."""
    detector = DeadlockDetector(timeout_seconds=5.0)

    detector.register_agent("observer")
    assert "observer" in detector.agent_states

    detector.unregister_agent("observer")
    assert "observer" not in detector.agent_states


@pytest.mark.asyncio
async def test_get_stats():
    """Test statistics retrieval."""
    detector = DeadlockDetector(timeout_seconds=5.0)
    detector.register_agent("observer")
    detector.register_agent("actor")

    stats = detector.get_stats()
    assert stats["agents_monitored"] == 2
    assert stats["deadlocks_detected"] == 0
    assert stats["deadlocks_recovered"] == 0


@pytest.mark.asyncio
async def test_get_agent_status():
    """Test agent status retrieval."""
    detector = DeadlockDetector(timeout_seconds=5.0)
    detector.register_agent("observer")

    detector.update_activity("observer", state="processing")

    status = detector.get_agent_status()
    assert "observer" in status
    assert status["observer"]["state"] == "processing"
    assert status["observer"]["message_count"] == 1
    assert status["observer"]["healthy"] is True
    assert status["observer"]["idle_time"] < 1.0


@pytest.mark.asyncio
async def test_start_stop():
    """Test start/stop functionality."""
    detector = DeadlockDetector(timeout_seconds=5.0)

    assert detector.running is False

    await detector.start()
    assert detector.running is True
    assert detector.monitor_task is not None

    await detector.stop()
    assert detector.running is False
