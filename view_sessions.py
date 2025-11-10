#!/usr/bin/env python3
"""
Swarm Visualization: CLI tool to view session metrics, timelines, graphs from logs.
Run: python view_sessions.py [session_id] [--graph]
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path
from collections import defaultdict
import argparse
import re

# Try matplotlib for graphs; fallback to text
try:
    import matplotlib.pyplot as plt
    import networkx as nx
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    print("[WARN] No matplotlib/networkx; using text viz only.")

from src import config

LOG_DIR = Path(config.LOG_DIR)

def get_sessions() -> list:
    """Get available session dirs."""
    sessions = [d for d in LOG_DIR.glob("swarm_*") if d.is_dir()]
    return sorted(sessions, key=lambda d: d.stat().st_mtime, reverse=True)

def load_session_logs(session_id: str) -> dict:
    """Load logs for session."""
    session_dir = LOG_DIR / session_id
    if not session_dir.exists():
        print(f"[ERROR] Session {session_id} not found. Available: {get_sessions()[:3]}")
        sys.exit(1)
    
    logs = {}
    for file in session_dir.glob("*.log"):
        with open(file, "r") as f:
            content = f.read()
            # Parse simple key-value or timestamped lines
            # Assume format: [TIMESTAMP] [AGENT] EVENT: details
            events = re.findall(r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] \[(\w+)\] (\w+): (.*)', content)
            logs[file.stem] = events
    
    # Also load jsonl if exists
    jsonl_file = session_dir / "activities.jsonl"
    if jsonl_file.exists():
        activities = []
        with open(jsonl_file, "r") as f:
            for line in f:
                try:
                    activities.append(json.loads(line.strip()))
                except:
                    pass
        logs["activities"] = activities
    
    print(f"[OK] Loaded session {session_id}: {len(logs)} log files.")
    return logs

def print_timeline(logs: dict, session_id: str):
    """Print ASCII timeline of agent activities."""
    # Group events by agent and time
    agent_events = defaultdict(list)
    start_time = datetime.now()
    
    for log_type, events in logs.items():
        for timestamp_str, agent, event, details in events:
            try:
                ts = datetime.fromisoformat(timestamp_str)
                duration = (ts - start_time).total_seconds() if hasattr(start_time, 'replace') else 0
                agent_events[agent].append({"time": duration, "event": event, "details": details})
            except:
                continue
    
    total_duration = max([max([e["time"] for e in ev]) for ev in agent_events.values()] or [0]) + 1
    
    print(f"\nTIMELINE for {session_id} (0-{int(total_duration)}s):")
    for agent, evs in sorted(agent_events.items()):
        evs.sort(key=lambda e: e["time"])
        print(f"{agent}: ", end="")
        for e in evs[:5]:  # Top 5 events
            bar_len = min(int(e["time"]), 20)
            bar = "=" * bar_len
            print(f"[{bar} {int(e['time'])}s] {e['event']}: {e['details'][:50]}", end=" | ")
        if len(evs) > 5:
            print("... (+more)")
        else:
            print()

def print_metrics(logs: dict):
    """Print key metrics."""
    print("\nMETRICS:")
    # Parse from activities if available
    if "activities" in logs:
        acts = logs["activities"]
        agent_stats = defaultdict(lambda: {"actions": 0, "success": 0, "errors": 0})
        for act in acts:
            agent = act.get("agent", "unknown")
            if act.get("outcome") == "success":
                agent_stats[agent]["success"] += 1
            else:
                agent_stats[agent]["errors"] += 1
            agent_stats[agent]["actions"] += 1
        
        for agent, stats in agent_stats.items():
            success_rate = (stats["success"] / stats["actions"] * 100) if stats["actions"] > 0 else 0
            print(f"- {agent}: Actions:{stats['actions']}, Success:{success_rate:.1f}%, Errors:{stats['errors']}")
    else:
        print("[INFO] No activities.jsonl; basic metrics unavailable.")

def plot_graph(logs: dict, session_id: str):
    """Plot message graph if matplotlib available."""
    if not HAS_MATPLOTLIB:
        print("[SKIP] Matplotlib not available; no graph.")
        return
    
    G = nx.DiGraph()
    edges = []
    
    # Parse messages from logs (assume pattern)
    for log_type, events in logs.items():
        for _, from_agent, event, details in events:
            if "→" in details or "to" in details.lower():
                match = re.search(r'(\w+) → (\w+)', details)
                if match:
                    G.add_edge(match.group(1), match.group(2), label=event)
    
    if G.number_of_nodes() > 0:
        pos = nx.spring_layout(G)
        nx.draw(G, pos, with_labels=True, node_color="lightblue", node_size=2000, font_size=10, arrows=True)
        plt.title(f"Swarm Graph: {session_id}")
        plt.show()
    else:
        print("[INFO] No messages parsed for graph.")

def main(session_id: str = None, graph: bool = False):
    if session_id is None:
        sessions = get_sessions()
        if not sessions:
            print("[ERROR] No sessions found.")
            return
        session_id = sessions[0].name
        print(f"[INFO] Using latest session: {session_id}")
    
    logs = load_session_logs(session_id)
    print(f"\nSWARM SESSION: {session_id} (Task: inferred from logs)")
    print_timeline(logs, session_id)
    print_metrics(logs)
    if graph:
        plot_graph(logs, session_id)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="View swarm sessions.")
    parser.add_argument("session_id", nargs="?", help="Session ID (default: latest)")
    parser.add_argument("--graph", action="store_true", help="Show graph (requires matplotlib)")
    args = parser.parse_args()
    main(args.session_id, args.graph)