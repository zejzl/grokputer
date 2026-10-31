"""Rate a finished Grokputer session, which is how training data gets made.

    python -m src.training.rate list
    python -m src.training.rate last --rating 2 --issue wrong-action --comment "clicked the wrong icon"
    python -m src.training.rate session_20261031_101500 --rating 1 --issue ocr --issue "popup blocked the button"

A rating of 3 or lower marks a session as a failure; the trainer needs at least one issue per failure. The shorthands
below map to the phrases the trainer's correction heuristics look for; any other text is kept as a free-form issue.
"""

import argparse
import json
import sys
from pathlib import Path

from .feedback import FEEDBACK_FILE, record_feedback

ISSUE_SHORTHAND = {
    "ocr": "OCR confidence low",
    "wrong-action": "Wrong action selected",
    "timeout": "Timeout",
    "coordination": "Coordination issue",
}
DEFAULT_LOGS = Path("logs")


def session_dirs(logs: Path):
    """Session directories, newest first."""
    found = [d for d in logs.iterdir() if d.is_dir() and d.name.startswith("session_") and (d / "session.json").exists()]
    return sorted(found, key=lambda d: (d / "session.json").stat().st_mtime, reverse=True)


def resolve(logs: Path, name: str) -> Path:
    if not logs.is_dir():
        raise SystemExit(f"[ERROR] no logs directory at {logs}")
    if name == "last":
        found = session_dirs(logs)
        if not found:
            raise SystemExit(f"[ERROR] no sessions in {logs}")
        return found[0]
    candidate = logs / name
    if candidate.parent.resolve() != logs.resolve() or not (candidate / "session.json").exists():
        raise SystemExit(f"[ERROR] {name} is not a session in {logs} (try: list)")
    return candidate


def describe(directory: Path) -> str:
    try:
        task = json.loads((directory / "session.json").read_text(encoding="utf-8")).get("task", "")
    except (OSError, json.JSONDecodeError):
        task = "(unreadable)"
    rated = ""
    feedback = directory / FEEDBACK_FILE
    if feedback.exists():
        try:
            rated = f"  rated {json.loads(feedback.read_text(encoding='utf-8')).get('user_rating')}"
        except (OSError, json.JSONDecodeError):
            rated = "  rated (unreadable)"
    return f"{directory.name}{rated}  {str(task)[:70]}"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m src.training.rate", description=__doc__.splitlines()[0])
    parser.add_argument("session", help="session directory name, 'last', or 'list' to show recent sessions")
    parser.add_argument("--rating", type=int, help="1 (bad) to 5 (good)")
    parser.add_argument("--issue", action="append", default=[],
                        help=f"what went wrong; shorthands: {', '.join(ISSUE_SHORTHAND)}; repeatable")
    parser.add_argument("--comment", default="")
    parser.add_argument("--logs", type=Path, default=DEFAULT_LOGS, help="logs directory (default: logs)")
    args = parser.parse_args(argv)

    if args.session == "list":
        if not args.logs.is_dir():
            print(f"[ERROR] no logs directory at {args.logs}", file=sys.stderr)
            return 1
        for directory in session_dirs(args.logs)[:15]:
            print(describe(directory))
        return 0

    if args.rating is None:
        parser.error("--rating is required")
    directory = resolve(args.logs, args.session)
    issues = [ISSUE_SHORTHAND.get(i, i) for i in args.issue]
    try:
        path = record_feedback(directory, args.rating, issues, args.comment)
    except ValueError as error:
        print(f"[ERROR] {error}", file=sys.stderr)
        return 1
    print(f"[OK] saved {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
