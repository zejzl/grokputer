"""
Unit tests for SessionLogger.
"""

import pytest
import json
import tempfile
from pathlib import Path
from src.observability.session_logger import SessionLogger, SwarmMetrics


def test_swarm_metrics_initialization():
    """Test SwarmMetrics initialization."""
    metrics = SwarmMetrics()

    assert metrics.total_handoffs == 0
    assert metrics.message_count == 0
    assert metrics.heartbeats_received == 0
    assert len(metrics.agent_states) == 0
    assert len(metrics.handoff_latencies) == 0


def test_swarm_metrics_add_handoff():
    """Test handoff recording."""
    metrics = SwarmMetrics()

    metrics.add_handoff(10.5)
    metrics.add_handoff(15.2)
    metrics.add_handoff(8.3)

    assert metrics.total_handoffs == 3
    assert len(metrics.handoff_latencies) == 3
    assert metrics.avg_handoff_latency == pytest.approx(11.33, abs=0.1)
    assert metrics.max_handoff_latency == 15.2


def test_swarm_metrics_agent_messages():
    """Test agent message counting."""
    metrics = SwarmMetrics()

    metrics.increment_agent_messages("observer")
    metrics.increment_agent_messages("observer")
    metrics.increment_agent_messages("actor")

    assert metrics.agent_message_counts["observer"] == 2
    assert metrics.agent_message_counts["actor"] == 1
    assert metrics.message_count == 3


def test_swarm_metrics_agent_errors():
    """Test agent error tracking."""
    metrics = SwarmMetrics()

    metrics.add_agent_error("observer", "Connection timeout")
    metrics.add_agent_error("observer", "API error")
    metrics.add_agent_error("actor", "Invalid command")

    assert len(metrics.agent_errors["observer"]) == 2
    assert len(metrics.agent_errors["actor"]) == 1
    assert "Connection timeout" in metrics.agent_errors["observer"]


def test_session_logger_initialization():
    """Test SessionLogger initialization."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_dir = Path(tmpdir)

        logger = SessionLogger(
            session_id="test_session_001",
            task="Test task",
            log_dir=log_dir,
            swarm_mode=True
        )

        assert logger.session_id == "test_session_001"
        assert logger.task == "Test task"
        assert logger.swarm_mode is True
        assert logger.swarm_metrics is not None
        assert (log_dir / "test_session_001").exists()
        assert (log_dir / "test_session_001" / "session.log").exists()


def test_session_logger_agent_logging():
    """Test agent lifecycle logging."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_dir = Path(tmpdir)

        logger = SessionLogger(
            session_id="test_session_002",
            task="Test task",
            log_dir=log_dir,
            swarm_mode=True
        )

        logger.log_agent_start("observer")
        logger.log_agent_activity("observer", "processing")
        logger.log_agent_error("observer", "Test error")
        logger.log_agent_stop("observer")

        # Check swarm metrics
        assert logger.swarm_metrics.agent_states["observer"] == "stopped"
        assert len(logger.swarm_metrics.agent_errors["observer"]) == 1
        assert logger.swarm_metrics.agent_errors["observer"][0] == "Test error"

        # Check log file
        log_content = (log_dir / "test_session_002" / "session.log").read_text()
        assert "AGENT START" in log_content
        assert "AGENT ERROR" in log_content
        assert "observer" in log_content


def test_session_logger_handoff():
    """Test handoff logging."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_dir = Path(tmpdir)

        logger = SessionLogger(
            session_id="test_session_003",
            task="Test task",
            log_dir=log_dir,
            swarm_mode=True
        )

        logger.log_handoff("observer", "actor", 12.5)
        logger.log_handoff("actor", "coordinator", 8.3)

        assert logger.swarm_metrics.total_handoffs == 2
        assert logger.swarm_metrics.avg_handoff_latency == pytest.approx(10.4, abs=0.1)


def test_session_logger_messages():
    """Test message logging."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_dir = Path(tmpdir)

        logger = SessionLogger(
            session_id="test_session_004",
            task="Test task",
            log_dir=log_dir,
            swarm_mode=True
        )

        logger.log_message("observer", "coordinator", "observation")
        logger.log_message("coordinator", "actor", "action")

        assert logger.swarm_metrics.message_count == 2
        assert logger.swarm_metrics.agent_message_counts["observer"] == 1
        assert logger.swarm_metrics.agent_message_counts["coordinator"] == 1


def test_session_logger_tool_execution():
    """Test tool execution logging."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_dir = Path(tmpdir)

        logger = SessionLogger(
            session_id="test_session_005",
            task="Test task",
            log_dir=log_dir,
            swarm_mode=False
        )

        logger.log_tool_execution(
            tool_name="bash",
            params={"command": "ls -la"},
            result="file1.txt\nfile2.txt",
            status="success"
        )

        assert len(logger.tool_executions) == 1
        assert logger.tool_executions[0]["tool"] == "bash"
        assert logger.tool_executions[0]["status"] == "success"


def test_session_logger_confirmation():
    """Test confirmation logging."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_dir = Path(tmpdir)

        logger = SessionLogger(
            session_id="test_session_006",
            task="Test task",
            log_dir=log_dir,
            swarm_mode=True
        )

        logger.log_confirmation("actor", "rm file.txt", 85, True)
        logger.log_confirmation("actor", "rm -rf /", 100, False)

        assert logger.swarm_metrics.confirmations_requested == 2
        assert logger.swarm_metrics.confirmations_approved == 1


def test_session_logger_finalize():
    """Test session finalization and metrics saving."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_dir = Path(tmpdir)

        logger = SessionLogger(
            session_id="test_session_007",
            task="Test task",
            log_dir=log_dir,
            swarm_mode=True
        )

        logger.log_agent_start("observer")
        logger.log_handoff("observer", "actor", 10.0)
        logger.log_iteration(1, {"screenshot": "ok", "api": "ok"})
        logger.finalize()

        # Check metrics file exists
        metrics_file = log_dir / "test_session_007" / "metrics.json"
        assert metrics_file.exists()

        # Check JSON file exists
        json_file = log_dir / "test_session_007" / "session.json"
        assert json_file.exists()

        # Check metrics content
        with open(metrics_file) as f:
            metrics = json.load(f)

        assert metrics["session_id"] == "test_session_007"
        assert metrics["task"] == "Test task"
        assert metrics["swarm_mode"] is True
        assert "swarm" in metrics
        assert metrics["swarm"]["total_handoffs"] == 1


def test_session_logger_non_swarm_mode():
    """Test logger works without swarm mode."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_dir = Path(tmpdir)

        logger = SessionLogger(
            session_id="test_session_008",
            task="Test task",
            log_dir=log_dir,
            swarm_mode=False
        )

        assert logger.swarm_metrics is None

        # Should not crash when logging swarm-specific events
        logger.log_handoff("a", "b", 10.0)
        logger.log_heartbeat("observer")

        logger.finalize()

        # Metrics should not include swarm data
        metrics_file = log_dir / "test_session_008" / "metrics.json"
        with open(metrics_file) as f:
            metrics = json.load(f)

        assert "swarm" not in metrics
