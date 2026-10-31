"""Ratings for finished sessions: the input of the QLoRA training data. No heavy imports, so the rate command starts fast."""

import json
from pathlib import Path
from typing import Any, Dict, List

FEEDBACK_FILE = "feedback.json"


def record_feedback(session_dir: Path, rating: int, what_went_wrong: List[str], comment: str = "") -> Path:
    """Attach a rating to a finished session. This is the supported way to create training data.

    SessionLogger writes session.json (task, tool_executions, errors) but never asks for a rating, so the rating
    lives in a sidecar file next to it: {"user_rating": 1-5, "what_went_wrong": [...], "feedback_comment": "..."}.
    """
    if not isinstance(rating, int) or isinstance(rating, bool) or not 1 <= rating <= 5:
        raise ValueError("rating must be an integer from 1 to 5")
    if not what_went_wrong or not all(isinstance(i, str) and i.strip() for i in what_went_wrong):
        raise ValueError("what_went_wrong must list at least one issue (non-empty strings)")
    path = Path(session_dir) / FEEDBACK_FILE
    path.write_text(json.dumps({"user_rating": rating, "what_went_wrong": list(what_went_wrong),
                                "feedback_comment": comment}, indent=2), encoding="utf-8")
    return path


def read_session(session_dir: Path) -> Dict[str, Any] | None:
    """One session as {task, rating, issues, comment, actions}, or None when it has no usable data.

    Reads what the current SessionLogger writes (session.json: top-level "task" and "tool_executions", each with
    "tool") plus the feedback.json sidecar. The older layout, with everything under session.json "metadata"
    (user_rating, what_went_wrong, feedback_comment, task) and "iterations[].tool_results[].function_name", still loads.
    """
    session_json = session_dir / "session.json"
    if not session_json.exists():
        return None
    with open(session_json, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return None

    meta = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
    feedback = {}
    feedback_json = session_dir / FEEDBACK_FILE
    if feedback_json.exists():
        with open(feedback_json, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        feedback = loaded if isinstance(loaded, dict) else {}

    def pick(key):
        return feedback.get(key, meta.get(key))

    actions = [e.get("tool", "unknown") for e in data.get("tool_executions", []) if isinstance(e, dict)]
    for iteration in data.get("iterations", []) if isinstance(data.get("iterations"), list) else []:
        for result in iteration.get("tool_results", []):
            actions.append(result.get("function_name", "unknown"))
    return {
        "task": data.get("task") or meta.get("task") or "Unknown task",
        "rating": pick("user_rating"),
        "issues": pick("what_went_wrong") or [],
        "comment": pick("feedback_comment") or "",
        "actions": actions,
    }
