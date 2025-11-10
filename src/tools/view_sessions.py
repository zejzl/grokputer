#!/usr/bin/env python3
"""
Session viewer utility for Grokputer.

View and analyze past execution sessions.
"""

import sys
import json
import click
from pathlib import Path
from datetime import datetime
from typing import Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src import config
from src.session_logger import SessionIndex


def format_timestamp(iso_string: str) -> str:
    """Format ISO timestamp for display."""
    try:
        dt = datetime.fromisoformat(iso_string)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return iso_string


def print_session_summary(session_dir: Path):
    """Print a summary of a session."""
    summary_path = session_dir / "summary.txt"

    if summary_path.exists():
        with open(summary_path, 'r') as f:
            print(f.read())
    else:
        print(f"No summary found for session: {session_dir.name}")


def print_session_json(session_dir: Path, pretty: bool = True):
    """Print the JSON log of a session."""
    json_path = session_dir / "session.json"

    if json_path.exists():
        with open(json_path, 'r') as f:
            data = json.load(f)

        if pretty:
            print(json.dumps(data, indent=2))
        else:
            print(json.dumps(data))
    else:
        print(f"No JSON log found for session: {session_dir.name}")


def print_session_metrics(session_dir: Path):
    """Print metrics for a session."""
    metrics_path = session_dir / "metrics.json"

    if metrics_path.exists():
        with open(metrics_path, 'r') as f:
            metrics = json.load(f)

        print("\n" + "=" * 70)
        print(f"METRICS: {session_dir.name}")
        print("=" * 70)
        print(f"Total Iterations: {metrics['total_iterations']}")
        print(f"Total Tool Calls: {metrics['total_tool_calls']}")
        print(f"Total Errors: {metrics['total_errors']}")
        print(f"API Success Rate: {metrics['api_success_rate']:.1%}")
        print(f"Avg API Duration: {metrics['avg_api_duration']:.2f}s")
        print(f"Total Screenshot Size: {metrics['total_screenshot_size_mb']:.2f} MB")
        print("=" * 70 + "\n")
    else:
        print(f"No metrics found for session: {session_dir.name}")


@click.group()
def cli():
    """View and analyze Grokputer execution sessions."""
    pass


@cli.command()
@click.option('--limit', '-n', default=10, help='Number of sessions to show')
def list(limit: int):
    """List recent sessions."""
    index = SessionIndex(config.LOGS_DIR)
    sessions = index.get_recent_sessions(limit)

    if not sessions:
        print("No sessions found.")
        return

    print("\n" + "=" * 70)
    print("RECENT SESSIONS")
    print("=" * 70 + "\n")

    for i, session in enumerate(sessions, 1):
        print(f"{i}. {session['session_id']}")
        print(f"   Task: {session['task']}")
        print(f"   Model: {session['model']}")
        print(f"   Time: {format_timestamp(session['start_time'])}")
        print()


@cli.command()
@click.argument('session_id')
@click.option('--format', '-f', type=click.Choice(['summary', 'json', 'metrics', 'all']), default='summary')
@click.option('--pretty/--no-pretty', default=True, help='Pretty print JSON')
def show(session_id: str, format: str, pretty: bool):
    """Show details of a specific session."""
    # Find session directory
    session_dir = config.LOGS_DIR / session_id

    if not session_dir.exists():
        # Try to find by partial match
        matches = [d for d in config.LOGS_DIR.iterdir() if d.is_dir() and session_id in d.name]

        if not matches:
            print(f"Session not found: {session_id}")
            return
        elif len(matches) > 1:
            print(f"Multiple sessions match '{session_id}':")
            for match in matches:
                print(f"  - {match.name}")
            return
        else:
            session_dir = matches[0]

    # Display requested format
    if format == 'summary' or format == 'all':
        print_session_summary(session_dir)

    if format == 'json' or format == 'all':
        if format == 'all':
            print("\n" + "=" * 70)
            print("JSON LOG")
            print("=" * 70 + "\n")
        print_session_json(session_dir, pretty)

    if format == 'metrics' or format == 'all':
        print_session_metrics(session_dir)


@cli.command()
@click.argument('query')
def search(query: str):
    """Search sessions by task description."""
    index = SessionIndex(config.LOGS_DIR)
    sessions = index.search_sessions(query)

    if not sessions:
        print(f"No sessions found matching: {query}")
        return

    print("\n" + "=" * 70)
    print(f"SEARCH RESULTS: '{query}'")
    print("=" * 70 + "\n")

    for i, session in enumerate(sessions, 1):
        print(f"{i}. {session['session_id']}")
        print(f"   Task: {session['task']}")
        print(f"   Model: {session['model']}")
        print(f"   Time: {format_timestamp(session['start_time'])}")
        print()


@cli.command()
def compare():
    """Compare metrics across recent sessions."""
    index = SessionIndex(config.LOGS_DIR)
    sessions = index.get_recent_sessions(5)

    if len(sessions) < 2:
        print("Need at least 2 sessions to compare.")
        return

    print("\n" + "=" * 70)
    print("SESSION COMPARISON (Last 5 sessions)")
    print("=" * 70 + "\n")

    # Header
    print(f"{'Session ID':<25} {'Iters':<8} {'Tools':<8} {'Errors':<8} {'API Success':<12}")
    print("-" * 70)

    # Load and display metrics for each session
    for session in sessions:
        session_dir = config.LOGS_DIR / session['session_id']
        metrics_path = session_dir / "metrics.json"

        if metrics_path.exists():
            with open(metrics_path, 'r') as f:
                metrics = json.load(f)

            session_id_short = session['session_id'][:24]
            print(f"{session_id_short:<25} "
                  f"{metrics['total_iterations']:<8} "
                  f"{metrics['total_tool_calls']:<8} "
                  f"{metrics['total_errors']:<8} "
                  f"{metrics['api_success_rate']:.0%}")

    print()


@cli.command()
@click.argument('session_id')
def tail(session_id: str):
    """Show the last few lines of a session log."""
    # Find session directory
    session_dir = config.LOGS_DIR / session_id

    if not session_dir.exists():
        matches = [d for d in config.LOGS_DIR.iterdir() if d.is_dir() and session_id in d.name]
        if not matches:
            print(f"Session not found: {session_id}")
            return
        session_dir = matches[0]

    log_path = session_dir / "session.log"

    if not log_path.exists():
        print(f"Log file not found: {session_dir.name}")
        return

    # Read last 20 lines
    with open(log_path, 'r') as f:
        lines = f.readlines()

    print("\n" + "=" * 70)
    print(f"LAST 20 LINES: {session_dir.name}")
    print("=" * 70 + "\n")

    for line in lines[-20:]:
        print(line.rstrip())


if __name__ == '__main__':
    cli()
