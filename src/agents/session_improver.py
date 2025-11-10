"""
Session Improver for Interactive Mode
Analyzes past Grokputer sessions and proposes improvements.
Simplified wrapper around ImproverAgent for manual use.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class SessionImprover:
    """
    Analyzes session logs and proposes improvements.
    Designed for interactive use (mode 4 in main.py).
    """

    def __init__(self, logs_dir: Path = Path("logs")):
        self.logs_dir = logs_dir
        self.logger = logger

    def get_latest_session(self) -> Optional[str]:
        """Get the most recent session ID."""
        sessions = list(self.logs_dir.glob("session_*/session.json"))
        if not sessions:
            return None
        latest = max(sessions, key=lambda p: p.stat().st_mtime)
        return latest.parent.name

    def get_session_data(self, session_id: str) -> Optional[Dict]:
        """Load session data from logs."""
        session_file = self.logs_dir / session_id / "session.json"
        if not session_file.exists():
            # Try swarm sessions
            session_file = self.logs_dir / f"swarm_{session_id.replace('session_', '')}" / "session.json"

        if not session_file.exists():
            self.logger.error(f"Session file not found: {session_file}")
            return None

        try:
            with open(session_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Error loading session: {e}")
            return None

    def analyze_session(self, session_id: str) -> Dict:
        """
        Analyze a session and generate improvement recommendations.

        Returns:
            Dict with analysis results and recommendations
        """
        print(f"\n[IMPROVER] Analyzing session: {session_id}")

        data = self.get_session_data(session_id)
        if not data:
            return {"error": f"Could not load session: {session_id}"}

        analysis = {
            "session_id": session_id,
            "timestamp": data.get("start_time", "unknown"),
            "task": data.get("task", "unknown"),
            "status": data.get("status", "unknown"),
            "recommendations": [],
            "metrics": {},
            "strengths": [],
            "issues": []
        }

        # Analyze iterations and performance
        iterations = data.get("iterations", [])
        if iterations:
            analysis["metrics"]["total_iterations"] = len(iterations)
            analysis["metrics"]["avg_iteration_time"] = sum(
                it.get("duration", 0) for it in iterations
            ) / len(iterations)

            # Check for failed iterations
            failed = [it for it in iterations if it.get("status") == "error"]
            if failed:
                analysis["issues"].append(f"Failed iterations: {len(failed)}/{len(iterations)}")
                analysis["recommendations"].append(
                    "Add retry logic for failed iterations"
                )
            else:
                analysis["strengths"].append("All iterations completed successfully")

        # Analyze tool calls
        tool_calls = []
        for iteration in iterations:
            tool_calls.extend(iteration.get("tool_calls", []))

        if tool_calls:
            analysis["metrics"]["total_tool_calls"] = len(tool_calls)

            # Check for repeated tools (inefficiency)
            tool_names = [tc.get("function", {}).get("name") for tc in tool_calls]
            repeated = {name: tool_names.count(name) for name in set(tool_names) if tool_names.count(name) > 2}
            if repeated:
                analysis["issues"].append(f"Repeated tool calls: {repeated}")
                analysis["recommendations"].append(
                    f"Cache results for repeated tools: {', '.join(repeated.keys())}"
                )

        # Analyze errors
        errors = data.get("errors", [])
        if errors:
            analysis["issues"].append(f"Total errors: {len(errors)}")
            error_types = {}
            for err in errors:
                err_type = err.get("type", "unknown")
                error_types[err_type] = error_types.get(err_type, 0) + 1

            analysis["metrics"]["error_types"] = error_types
            analysis["recommendations"].append(
                f"Add error handling for: {', '.join(error_types.keys())}"
            )
        else:
            analysis["strengths"].append("No errors encountered")

        # Analyze API usage
        if "api_calls" in data:
            api_calls = data["api_calls"]
            analysis["metrics"]["api_calls"] = len(api_calls)
            total_cost = sum(call.get("cost", 0) for call in api_calls)
            analysis["metrics"]["estimated_cost"] = f"${total_cost:.4f}"

            if total_cost > 1.0:
                analysis["recommendations"].append(
                    "High API cost - consider caching or reducing iterations"
                )

        # Analyze response times
        if iterations:
            slow_iterations = [it for it in iterations if it.get("duration", 0) > 30]
            if slow_iterations:
                analysis["issues"].append(f"Slow iterations: {len(slow_iterations)}")
                analysis["recommendations"].append(
                    "Optimize slow operations - consider async processing"
                )

        # Check task completion
        if data.get("status") == "completed":
            analysis["strengths"].append("Task completed successfully")
        elif data.get("status") == "partial":
            analysis["recommendations"].append(
                "Task incomplete - increase max_iterations or refine prompt"
            )

        return analysis

    def print_analysis(self, analysis: Dict):
        """Pretty-print analysis results."""
        print("\n" + "="*70)
        print(f"SESSION ANALYSIS: {analysis['session_id']}")
        print("="*70)

        print(f"\nTask: {analysis['task']}")
        print(f"Status: {analysis['status']}")
        print(f"Timestamp: {analysis['timestamp']}")

        if analysis.get("metrics"):
            print("\n📊 METRICS:")
            for key, value in analysis["metrics"].items():
                print(f"  • {key}: {value}")

        if analysis.get("strengths"):
            print("\n✅ STRENGTHS:")
            for strength in analysis["strengths"]:
                print(f"  • {strength}")

        if analysis.get("issues"):
            print("\n⚠️  ISSUES FOUND:")
            for issue in analysis["issues"]:
                print(f"  • {issue}")

        if analysis.get("recommendations"):
            print("\n💡 RECOMMENDATIONS:")
            for i, rec in enumerate(analysis["recommendations"], 1):
                print(f"  {i}. {rec}")

        print("\n" + "="*70)

    def improve_session(self, session_id: str = "latest"):
        """
        Main entry point for session improvement.
        Analyzes session and prints recommendations.
        """
        if session_id == "latest":
            session_id = self.get_latest_session()
            if not session_id:
                print("[ERROR] No sessions found")
                return
            print(f"[INFO] Using latest session: {session_id}")

        analysis = self.analyze_session(session_id)

        if "error" in analysis:
            print(f"[ERROR] {analysis['error']}")
            return

        self.print_analysis(analysis)

        # Save analysis to file
        output_file = self.logs_dir / session_id / "improvement_analysis.json"
        try:
            with open(output_file, 'w') as f:
                json.dump(analysis, f, indent=2)
            print(f"\n[SAVED] Analysis saved to: {output_file}")
        except Exception as e:
            self.logger.error(f"Could not save analysis: {e}")


if __name__ == "__main__":
    # Test the improver
    improver = SessionImprover()
    improver.improve_session("latest")
