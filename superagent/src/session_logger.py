"""
Enhanced session logging for Grokputer.

Tracks execution sessions with structured data, metrics, and searchable logs.
Useful for both Claude and Grok to review what happened during task execution.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import time


@dataclass
class SessionMetadata:
    """Metadata for a Grokputer execution session."""
    session_id: str
    start_time: str
    task: str
    model: str
    max_iterations: int
    debug_mode: bool
    require_confirmation: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class IterationMetrics:
    """Metrics for a single iteration of the observe-reason-act loop."""
    iteration_number: int
    start_time: float
    screenshot_captured: bool
    screenshot_size_bytes: Optional[int]
    api_call_duration: Optional[float]
    api_call_success: bool
    tool_calls_count: int
    tool_results: List[Dict[str, Any]]
    grok_response: Optional[str]
    errors: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SessionLogger:
    """
    Enhanced logger that tracks sessions, iterations, and metrics.

    Creates both human-readable logs and structured JSON for analysis.
    """

    def __init__(self, logs_dir: Path, session_id: Optional[str] = None):
        """
        Initialize session logger.

        Args:
            logs_dir: Directory to store log files
            session_id: Optional session ID (auto-generated if not provided)
        """
        self.logs_dir = Path(logs_dir)
        self.logs_dir.mkdir(exist_ok=True)

        # Generate session ID if not provided
        self.session_id = session_id or self._generate_session_id()

        # Session data
        self.metadata: Optional[SessionMetadata] = None
        self.iterations: List[IterationMetrics] = []
        self.start_time = time.time()

        # Create session-specific log files
        self.session_dir = self.logs_dir / self.session_id
        self.session_dir.mkdir(exist_ok=True)

        self.text_log_path = self.session_dir / "session.log"
        self.json_log_path = self.session_dir / "session.json"
        self.metrics_path = self.session_dir / "metrics.json"

        # Setup Python logger
        self.logger = self._setup_logger()

        self.logger.info(f"Session logger initialized: {self.session_id}")

    def _generate_session_id(self) -> str:
        """Generate a unique session ID."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"session_{timestamp}"

    def _setup_logger(self) -> logging.Logger:
        """Setup Python logger for this session."""
        logger = logging.getLogger(f"grokputer.{self.session_id}")
        logger.setLevel(logging.DEBUG)

        # File handler for session log
        file_handler = logging.FileHandler(self.text_log_path)
        file_handler.setLevel(logging.DEBUG)

        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)

        logger.addHandler(file_handler)

        return logger

    def start_session(self, metadata: SessionMetadata):
        """
        Start a new session.

        Args:
            metadata: Session metadata
        """
        self.metadata = metadata
        self.start_time = time.time()

        self.logger.info("=" * 70)
        self.logger.info(f"SESSION STARTED: {self.session_id}")
        self.logger.info(f"Task: {metadata.task}")
        self.logger.info(f"Model: {metadata.model}")
        self.logger.info(f"Max Iterations: {metadata.max_iterations}")
        self.logger.info("=" * 70)

        # Write initial metadata to JSON
        self._save_json_log()

    def log_iteration_start(self, iteration_number: int):
        """
        Log the start of an iteration.

        Args:
            iteration_number: Current iteration number
        """
        self.logger.info("")
        self.logger.info("-" * 70)
        self.logger.info(f"ITERATION {iteration_number} START")
        self.logger.info("-" * 70)

    def log_observation(self, success: bool, screenshot_size: Optional[int] = None, error: Optional[str] = None):
        """
        Log screenshot observation.

        Args:
            success: Whether screenshot was captured successfully
            screenshot_size: Size of screenshot in bytes
            error: Error message if failed
        """
        if success:
            size_kb = screenshot_size / 1024 if screenshot_size else 0
            self.logger.info(f"[OBSERVE] Screenshot captured: {size_kb:.1f} KB")
        else:
            self.logger.error(f"[OBSERVE] Screenshot failed: {error}")

    def log_api_call(self, duration: float, success: bool, response: Optional[str] = None, error: Optional[str] = None):
        """
        Log Grok API call.

        Args:
            duration: Duration of API call in seconds
            success: Whether API call succeeded
            response: Grok's response text
            error: Error message if failed
        """
        if success:
            self.logger.info(f"[REASON] Grok API call successful ({duration:.2f}s)")
            if response:
                # Truncate long responses for readability
                display_response = response[:200] + "..." if len(response) > 200 else response
                self.logger.info(f"[REASON] Response: {display_response}")
        else:
            self.logger.error(f"[REASON] API call failed ({duration:.2f}s): {error}")

    def log_tool_execution(self, tool_name: str, result: Dict[str, Any]):
        """
        Log tool execution result.

        Args:
            tool_name: Name of the tool
            result: Tool execution result
        """
        status = result.get("status", "unknown")
        self.logger.info(f"[ACT] Tool: {tool_name} -> {status}")

        # Log details for debugging
        if status == "error":
            error = result.get("error", "Unknown error")
            self.logger.error(f"[ACT] Error details: {error}")

    def log_iteration_complete(self, metrics: IterationMetrics):
        """
        Log completion of an iteration and save metrics.

        Args:
            metrics: Iteration metrics
        """
        duration = time.time() - metrics.start_time
        self.iterations.append(metrics)

        self.logger.info(f"Iteration {metrics.iteration_number} complete ({duration:.2f}s)")
        self.logger.info(f"  - API calls: {'OK' if metrics.api_call_success else 'FAIL'}")
        self.logger.info(f"  - Tools executed: {metrics.tool_calls_count}")
        self.logger.info(f"  - Errors: {len(metrics.errors)}")

        # Save updated metrics
        self._save_metrics()
        self._save_json_log()

    def end_session(self, reason: str = "completed"):
        """
        End the session and write final logs.

        Args:
            reason: Reason for session end (completed, error, interrupted)
        """
        total_duration = time.time() - self.start_time

        self.logger.info("")
        self.logger.info("=" * 70)
        self.logger.info(f"SESSION ENDED: {reason}")
        self.logger.info(f"Total duration: {total_duration:.2f}s")
        self.logger.info(f"Iterations completed: {len(self.iterations)}")
        self.logger.info("=" * 70)

        # Write final JSON
        self._save_json_log()
        self._save_metrics()

        # Write summary
        self._write_summary()

    def _save_json_log(self):
        """Save session data to JSON file."""
        session_data = {
            "session_id": self.session_id,
            "metadata": self.metadata.to_dict() if self.metadata else None,
            "start_time": datetime.fromtimestamp(self.start_time).isoformat(),
            "iterations": [it.to_dict() for it in self.iterations],
            "total_iterations": len(self.iterations)
        }

        with open(self.json_log_path, 'w') as f:
            json.dump(session_data, f, indent=2)

    def _save_metrics(self):
        """Save metrics summary to separate file."""
        if not self.iterations:
            return

        metrics = {
            "session_id": self.session_id,
            "total_iterations": len(self.iterations),
            "total_tool_calls": sum(it.tool_calls_count for it in self.iterations),
            "total_errors": sum(len(it.errors) for it in self.iterations),
            "api_success_rate": sum(1 for it in self.iterations if it.api_call_success) / len(self.iterations),
            "avg_api_duration": sum(it.api_call_duration or 0 for it in self.iterations) / len(self.iterations),
            "total_screenshot_size_mb": sum(it.screenshot_size_bytes or 0 for it in self.iterations) / (1024 * 1024)
        }

        with open(self.metrics_path, 'w') as f:
            json.dump(metrics, f, indent=2)

    def _write_summary(self):
        """Write a human-readable summary."""
        summary_path = self.session_dir / "summary.txt"

        with open(summary_path, 'w') as f:
            f.write("=" * 70 + "\n")
            f.write(f"GROKPUTER SESSION SUMMARY: {self.session_id}\n")
            f.write("=" * 70 + "\n\n")

            if self.metadata:
                f.write(f"Task: {self.metadata.task}\n")
                f.write(f"Model: {self.metadata.model}\n")
                f.write(f"Start Time: {self.metadata.start_time}\n")
                f.write(f"Max Iterations: {self.metadata.max_iterations}\n\n")

            f.write(f"Iterations Completed: {len(self.iterations)}\n")
            f.write(f"Total Duration: {time.time() - self.start_time:.2f}s\n\n")

            if self.iterations:
                f.write("ITERATION BREAKDOWN:\n")
                f.write("-" * 70 + "\n")

                for it in self.iterations:
                    f.write(f"\nIteration {it.iteration_number}:\n")
                    f.write(f"  Screenshot: {'OK' if it.screenshot_captured else 'FAIL'}")
                    if it.screenshot_size_bytes:
                        f.write(f" ({it.screenshot_size_bytes / 1024:.1f} KB)")
                    f.write("\n")
                    f.write(f"  API Call: {'OK' if it.api_call_success else 'FAIL'}")
                    if it.api_call_duration:
                        f.write(f" ({it.api_call_duration:.2f}s)")
                    f.write("\n")
                    f.write(f"  Tools Executed: {it.tool_calls_count}\n")

                    if it.errors:
                        f.write(f"  Errors:\n")
                        for error in it.errors:
                            f.write(f"    - {error}\n")

                    if it.tool_results:
                        f.write(f"  Tool Results:\n")
                        for result in it.tool_results:
                            f.write(f"    - {result.get('function_name')}: {result.get('result', {}).get('status')}\n")

            f.write("\n" + "=" * 70 + "\n")
            f.write("Full logs available in:\n")
            f.write(f"  - {self.text_log_path.name}\n")
            f.write(f"  - {self.json_log_path.name}\n")
            f.write(f"  - {self.metrics_path.name}\n")

    def get_session_dir(self) -> Path:
        """Get the session directory path."""
        return self.session_dir


class SessionIndex:
    """
    Index of all sessions for easy searching and comparison.
    """

    def __init__(self, logs_dir: Path):
        """
        Initialize session index.

        Args:
            logs_dir: Directory containing session logs
        """
        self.logs_dir = Path(logs_dir)
        self.index_path = self.logs_dir / "session_index.json"

    def add_session(self, session_id: str, metadata: SessionMetadata):
        """
        Add a session to the index.

        Args:
            session_id: Session ID
            metadata: Session metadata
        """
        index = self._load_index()

        index[session_id] = {
            "task": metadata.task,
            "model": metadata.model,
            "start_time": metadata.start_time,
            "debug_mode": metadata.debug_mode
        }

        self._save_index(index)

    def get_recent_sessions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent sessions.

        Args:
            limit: Maximum number of sessions to return

        Returns:
            List of session info dictionaries
        """
        index = self._load_index()
        sessions = sorted(
            index.items(),
            key=lambda x: x[1]["start_time"],
            reverse=True
        )

        return [{"session_id": sid, **info} for sid, info in sessions[:limit]]

    def search_sessions(self, query: str) -> List[Dict[str, Any]]:
        """
        Search sessions by task description.

        Args:
            query: Search query

        Returns:
            List of matching session info
        """
        index = self._load_index()
        matches = []

        query_lower = query.lower()
        for sid, info in index.items():
            if query_lower in info["task"].lower():
                matches.append({"session_id": sid, **info})

        return matches

    def _load_index(self) -> Dict[str, Any]:
        """Load the session index."""
        if self.index_path.exists():
            with open(self.index_path, 'r') as f:
                return json.load(f)
        return {}

    def _save_index(self, index: Dict[str, Any]):
        """Save the session index."""
        with open(self.index_path, 'w') as f:
            json.dump(index, f, indent=2)
