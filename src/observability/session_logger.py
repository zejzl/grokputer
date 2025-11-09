"""
Session logging with swarm metrics support.

Tracks execution details, agent interactions, performance metrics,
and swarm-specific data for multi-agent tasks.
"""

import json
import logging
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class SwarmMetrics:
    """Metrics specific to multi-agent swarm execution."""

    # Agent performance
    agent_states: Dict[str, str] = field(default_factory=dict)  # agent_id -> state
    agent_message_counts: Dict[str, int] = field(default_factory=dict)
    agent_errors: Dict[str, List[str]] = field(default_factory=lambda: {})

    # Communication metrics
    total_handoffs: int = 0
    handoff_latencies: List[float] = field(default_factory=list)  # milliseconds
    message_count: int = 0
    avg_handoff_latency: float = 0.0
    max_handoff_latency: float = 0.0

    # Coordination metrics
    coordinator_decisions: int = 0
    task_decompositions: int = 0
    confirmations_requested: int = 0
    confirmations_approved: int = 0

    # Health metrics
    heartbeats_received: int = 0
    deadlocks_detected: int = 0
    agent_restarts: int = 0

    def add_handoff(self, latency_ms: float):
        """Record a handoff between agents."""
        self.total_handoffs += 1
        self.handoff_latencies.append(latency_ms)
        self.avg_handoff_latency = sum(self.handoff_latencies) / len(self.handoff_latencies)
        self.max_handoff_latency = max(self.handoff_latencies)

    def increment_agent_messages(self, agent_id: str):
        """Increment message count for agent."""
        self.agent_message_counts[agent_id] = self.agent_message_counts.get(agent_id, 0) + 1
        self.message_count += 1

    def add_agent_error(self, agent_id: str, error: str):
        """Record agent error."""
        if agent_id not in self.agent_errors:
            self.agent_errors[agent_id] = []
        self.agent_errors[agent_id].append(error)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


class SessionLogger:
    """
    Enhanced session logger with swarm metrics support.

    Tracks:
    - Session metadata (task, model, timestamps)
    - Iteration details (screenshots, API calls, tool executions)
    - Swarm metrics (handoffs, agent states, communication)
    - Performance data (latency, throughput, errors)
    - Structured logs (JSON + human-readable)
    """

    def __init__(
        self,
        session_id: str,
        task: str,
        log_dir: Path,
        swarm_mode: bool = False
    ):
        """
        Initialize session logger.

        Args:
            session_id: Unique session identifier
            task: Task description
            log_dir: Directory to store logs
            swarm_mode: Enable swarm metrics tracking
        """
        self.session_id = session_id
        self.task = task
        self.swarm_mode = swarm_mode

        # Create session directory
        self.session_dir = log_dir / session_id
        self.session_dir.mkdir(parents=True, exist_ok=True)

        # Log files
        self.log_file = self.session_dir / "session.log"
        self.json_file = self.session_dir / "session.json"
        self.metrics_file = self.session_dir / "metrics.json"

        # Session data
        self.start_time = time.time()
        self.iterations = 0
        self.tool_executions = []
        self.api_calls = []
        self.errors = []

        # Swarm metrics
        self.swarm_metrics = SwarmMetrics() if swarm_mode else None

        # Initialize log files
        self._init_logs()

        logger.info(f"[SessionLogger] Started session: {session_id}")

    def _init_logs(self):
        """Initialize log files with headers."""
        with open(self.log_file, "w") as f:
            f.write(f"Session: {self.session_id}\n")
            f.write(f"Task: {self.task}\n")
            f.write(f"Started: {datetime.now().isoformat()}\n")
            f.write(f"Swarm Mode: {self.swarm_mode}\n")
            f.write("-" * 80 + "\n\n")

    def log_agent_start(self, agent_id: str):
        """Log agent startup."""
        msg = f"[AGENT START] {agent_id}"
        self._log(msg)

        if self.swarm_metrics:
            self.swarm_metrics.agent_states[agent_id] = "started"

    def log_agent_stop(self, agent_id: str):
        """Log agent shutdown."""
        msg = f"[AGENT STOP] {agent_id}"
        self._log(msg)

        if self.swarm_metrics:
            self.swarm_metrics.agent_states[agent_id] = "stopped"

    def log_agent_error(self, agent_id: str, error: str):
        """Log agent error."""
        msg = f"[AGENT ERROR] {agent_id}: {error}"
        self._log(msg)
        self.errors.append({"agent": agent_id, "error": error, "timestamp": time.time()})

        if self.swarm_metrics:
            self.swarm_metrics.add_agent_error(agent_id, error)

    def log_agent_activity(self, agent_id: str, state: str):
        """Log agent activity/state change."""
        msg = f"[AGENT ACTIVITY] {agent_id} -> {state}"
        self._log(msg)

        if self.swarm_metrics:
            self.swarm_metrics.agent_states[agent_id] = state

    def log_agent_wait(self, agent_id: str):
        """Log agent waiting."""
        msg = f"[AGENT WAIT] {agent_id}"
        self._log(msg)

    def log_heartbeat(self, agent_id: str):
        """Log agent heartbeat."""
        if self.swarm_metrics:
            self.swarm_metrics.heartbeats_received += 1

    def log_handoff(self, from_agent: str, to_agent: str, latency_ms: float):
        """Log message handoff between agents."""
        msg = f"[HANDOFF] {from_agent} -> {to_agent} ({latency_ms:.2f}ms)"
        self._log(msg)

        if self.swarm_metrics:
            self.swarm_metrics.add_handoff(latency_ms)

    def log_message(self, from_agent: str, to_agent: str, message_type: str):
        """Log message sent between agents."""
        msg = f"[MESSAGE] {from_agent} -> {to_agent}: {message_type}"
        self._log(msg)

        if self.swarm_metrics:
            self.swarm_metrics.increment_agent_messages(from_agent)

    def log_iteration(self, iteration: int, data: Dict[str, Any]):
        """Log iteration details."""
        self.iterations = iteration
        msg = f"\n[ITERATION {iteration}]\n{json.dumps(data, indent=2)}"
        self._log(msg)

    def log_tool_execution(self, tool_name: str, params: Dict, result: Any, status: str):
        """Log tool execution."""
        execution = {
            "tool": tool_name,
            "params": params,
            "result": str(result)[:200],  # Truncate long results
            "status": status,
            "timestamp": time.time()
        }
        self.tool_executions.append(execution)

        msg = f"[TOOL] {tool_name} -> {status}"
        self._log(msg)

    def log_api_call(self, duration: float, model: str, success: bool):
        """Log API call."""
        call = {
            "duration": duration,
            "model": model,
            "success": success,
            "timestamp": time.time()
        }
        self.api_calls.append(call)

        msg = f"[API] {model} ({duration:.2f}s) -> {'OK' if success else 'FAIL'}"
        self._log(msg)

    def log_confirmation(self, agent_id: str, action: str, score: int, approved: bool):
        """Log safety confirmation."""
        msg = f"[CONFIRM] {agent_id}: {action} (score={score}) -> {'APPROVED' if approved else 'DENIED'}"
        self._log(msg)

        if self.swarm_metrics:
            self.swarm_metrics.confirmations_requested += 1
            if approved:
                self.swarm_metrics.confirmations_approved += 1

    def _log(self, message: str):
        """Write message to log file."""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        with open(self.log_file, "a") as f:
            f.write(f"[{timestamp}] {message}\n")

    def save_metrics(self):
        """Save final metrics to JSON."""
        duration = time.time() - self.start_time

        metrics = {
            "session_id": self.session_id,
            "task": self.task,
            "duration_seconds": duration,
            "iterations": self.iterations,
            "tool_executions": len(self.tool_executions),
            "api_calls": len(self.api_calls),
            "errors": len(self.errors),
            "swarm_mode": self.swarm_mode
        }

        if self.swarm_metrics:
            metrics["swarm"] = self.swarm_metrics.to_dict()

        with open(self.metrics_file, "w") as f:
            json.dump(metrics, f, indent=2)

        # Also save full session data
        session_data = {
            **metrics,
            "tool_executions": self.tool_executions,
            "api_calls": self.api_calls,
            "errors": self.errors
        }

        with open(self.json_file, "w") as f:
            json.dump(session_data, f, indent=2)

        logger.info(f"[SessionLogger] Saved metrics to {self.metrics_file}")

    def finalize(self):
        """Finalize session and save all data."""
        duration = time.time() - self.start_time

        summary = [
            "\n" + "=" * 80,
            f"Session Summary: {self.session_id}",
            "=" * 80,
            f"Task: {self.task}",
            f"Duration: {duration:.2f}s",
            f"Iterations: {self.iterations}",
            f"Tool Executions: {len(self.tool_executions)}",
            f"API Calls: {len(self.api_calls)}",
            f"Errors: {len(self.errors)}",
        ]

        if self.swarm_metrics:
            summary.extend([
                "",
                "Swarm Metrics:",
                f"  Handoffs: {self.swarm_metrics.total_handoffs}",
                f"  Avg Latency: {self.swarm_metrics.avg_handoff_latency:.2f}ms",
                f"  Messages: {self.swarm_metrics.message_count}",
                f"  Heartbeats: {self.swarm_metrics.heartbeats_received}",
                f"  Agents: {len(self.swarm_metrics.agent_states)}",
            ])

        summary.append("=" * 80)

        summary_text = "\n".join(summary)
        self._log(summary_text)
        self.save_metrics()

        logger.info(f"[SessionLogger] Finalized session: {self.session_id}")
