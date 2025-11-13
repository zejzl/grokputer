#!/usr/bin/env python3
"""
Grokputer Swarm Dashboard - Streamlit UI
Live monitoring, task queuing, session visualization, and controls.
Run: streamlit run streamlit_app.py
Requires: pip install streamlit redis (for eternal memory view)
"""

import streamlit as st
import subprocess
import time
import json
import os
from pathlib import Path
from datetime import datetime
import redis  # For eternal memory peek
from typing import Dict, Any, List
import re

# Local imports (adjust paths as needed)
from src import config
from src.db_config import redis_client, get_sessions  # Assume updated with get_sessions
from view_sessions import main as view_session_main  # Call viz function

# Config
LOG_DIR = Path(config.LOG_DIR)
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

# Redis client for memory view
try:
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, password=REDIS_PASSWORD, decode_responses=True)
    r.ping()  # Test connection
    REDIS_AVAILABLE = True
except:
    REDIS_AVAILABLE = False
    st.warning("Redis not available; eternal memory view disabled.")


def generate_swarm_mermaid(session_id: str) -> str:
    """
    Generate Mermaid diagram for swarm/agent interactions from logs.

    Args:
        session_id: Session ID to visualize

    Returns:
        Mermaid diagram string
    """
    log_file = LOG_DIR / session_id / "activity.log"
    if not log_file.exists():
        return "graph TD\n    A[No logs found]"

    # Parse logs for agent interactions
    interactions = []
    agents = set()

    with open(log_file, "r") as f:
        for line in f:
            # Parse log lines for agent activities
            # Example log format: [TIMESTAMP] [AGENT] Message
            match = re.search(r"\[(\w+)\]\s*(.*)", line)
            if match:
                agent, message = match.groups()
                agents.add(agent)

                # Extract interactions
                if "Delegated" in message:
                    sub_match = re.search(r"Delegated (\w+) to (\w+)", message)
                    if sub_match:
                        sub_id, target = sub_match.groups()
                        interactions.append((agent, target, f"delegate_{sub_id}"))
                elif "Result for" in message:
                    sub_match = re.search(r"Result for (\w+)", message)
                    if sub_match:
                        sub_id = sub_match.group(1)
                        interactions.append((agent, "coordinator", f"result_{sub_id}"))

    # Generate Mermaid flowchart
    mermaid = "graph TD\n"

    # Add agents as nodes
    for agent in sorted(agents):
        mermaid += f"    {agent}[{agent.upper()}]\n"

    # Add interactions as edges
    for i, (from_agent, to_agent, label) in enumerate(interactions):
        mermaid += f"    {from_agent} -->|{label}| {to_agent}\n"

    # Add task flow if coordinator present
    if "coordinator" in agents:
        mermaid += "    User -->|new_task| coordinator\n"
        mermaid += "    coordinator -->|task_complete| User\n"

    return mermaid


def get_swarm_metrics(session_id: str) -> Dict[str, Any]:
    """
    Extract metrics from session logs.

    Args:
        session_id: Session ID

    Returns:
        Metrics dictionary
    """
    log_file = LOG_DIR / session_id / "activity.log"
    if not log_file.exists():
        return {}

    metrics = {
        "total_actions": 0,
        "successful_actions": 0,
        "failed_actions": 0,
        "agents_active": set(),
        "duration": "Unknown",
    }

    with open(log_file, "r") as f:
        lines = f.readlines()
        if lines:
            # Estimate duration from first/last timestamp
            first_line = lines[0]
            last_line = lines[-1]
            # Assuming timestamp format, but simplified

        for line in lines:
            metrics["agents_active"].add(line.split()[0].strip("[]") if "[" in line else "unknown")

            if "Delegated" in line:
                metrics["total_actions"] += 1
            elif "success" in line.lower():
                metrics["successful_actions"] += 1
            elif "fail" in line.lower():
                metrics["failed_actions"] += 1

    metrics["agents_active"] = len(metrics["agents_active"])
    metrics["success_rate"] = f"{(metrics['successful_actions'] / max(metrics['total_actions'], 1)) * 100:.1f}%"

    return metrics


def run_swarm(
    task: str, session_id: str = None, backend: str = "qwen", agent_roles: str = "coordinator,observer,actor"
):
    """Run swarm via subprocess."""
    cmd = ["python", "main.py", "--swarm", f"--task '{task}'"]
    if session_id:
        cmd += ["--session-id", session_id]
    if backend == "grok":
        cmd += ["--backend", "grok"]
    cmd += ["--agent-roles", agent_roles]
    with st.spinner(f"Running swarm: {task}..."):
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=".")
        stdout, stderr = process.communicate(timeout=120)  # 2min timeout
        if process.returncode == 0:
            st.success(f"Swarm completed: {task}")
            return stdout
        else:
            st.error(f"Swarm failed: {stderr}")
            return stderr


def get_live_logs(session_id: str, lines: int = 50):
    """Tail logs for session."""
    log_file = LOG_DIR / session_id / "activity.log"  # Assume log file
    if log_file.exists():
        with open(log_file, "r") as f:
            lines_list = f.readlines()[-lines:]
        return "".join(lines_list)
    return "No logs found."


def view_redis_memory(session_id: str):
    """Peek Redis keys for session."""
    if not REDIS_AVAILABLE:
        return "Redis unavailable."
    keys = [k for k in r.keys(f"swarm:{session_id}:*")]
    if not keys:
        return "No eternal state for this session."
    state = {}
    for key in keys:
        value = r.get(key)
        if value:
            try:
                state[key] = json.loads(value)
            except:
                state[key] = value
    return state


# Streamlit UI
st.set_page_config(page_title="Grokputer Swarm Dashboard", layout="wide", initial_sidebar_state="expanded")

st.title("🦅 Grokputer Swarm Dashboard")
st.markdown(
    "Monitor, queue, and visualize multi-agent swarms. Eternal memory via Redis. Backend: Qwen (local) or Grok (API)."
)

# Sidebar: Controls
with st.sidebar:
    st.header("Task Queue")
    task = st.text_input("Enter task:", placeholder="e.g., List files in vault and create summary.md")
    backend = st.selectbox("Backend:", ["qwen (local GGUF)", "grok (API)"])
    agent_roles = st.text_input(
        "Agent Roles:", value="coordinator,observer,actor", help="Comma-separated: coordinator,observer,actor"
    )
    session_id = st.text_input("Session ID:", placeholder="Auto-generate or resume (e.g., resume_test)")
    if st.button("🚀 Run Swarm", type="primary"):
        if task:
            output = run_swarm(task, session_id or f"session_{int(time.time())}", backend.lower(), agent_roles)
            st.session_state.last_output = output
            st.rerun()
        else:
            st.warning("Enter a task.")

    st.header("Sessions")
    sessions = get_sessions()  # From view_sessions.py or db_config
    selected_session = st.selectbox("Select Session:", [s.name for s in sessions] if sessions else ["No sessions"])

# Main Content
col1, col2 = st.columns(2)

with col1:
    st.header("📊 Live Metrics & Viz")
    if selected_session:
        # Swarm Architecture Diagram
        st.subheader("Swarm Architecture")
        mermaid_diagram = generate_swarm_mermaid(selected_session)
        st.code(mermaid_diagram, language="mermaid")

        # Note: To render Mermaid, you can copy this code to https://mermaid.live/
        st.info("💡 Copy the above code to [Mermaid Live Editor](https://mermaid.live/) to visualize the swarm flow.")

        # Metrics from logs
        metrics = get_swarm_metrics(selected_session)
        if metrics:
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                st.metric("Total Actions", metrics.get("total_actions", 0))
            with col_b:
                st.metric("Success Rate", metrics.get("success_rate", "N/A"))
            with col_c:
                st.metric("Active Agents", metrics.get("agents_active", 0))

        # Embed viz from view_sessions
        with st.spinner("Loading visualization..."):
            # Simulate calling view_sessions (output to temp file or capture)
            viz_output = subprocess.run(
                ["python", "view_sessions.py", selected_session], capture_output=True, text=True
            )
            st.text(viz_output.stdout)

with col2:
    st.header("📝 Live Logs")
    if selected_session:
        logs = get_live_logs(selected_session)
        st.text_area("Recent Logs:", logs, height=300, key=f"logs_{selected_session}")
        if st.button("🔄 Refresh Logs"):
            st.rerun()

    st.header("∞ Eternal Memory (Redis)")
    if selected_session and REDIS_AVAILABLE:
        memory = view_redis_memory(selected_session)
        st.json(memory)
    else:
        st.info("Select session and ensure Redis running.")

# Footer
st.header("Recent Runs")
if "last_output" in st.session_state:
    st.text_area("Last Swarm Output:", st.session_state.last_output, height=200)

# Auto-refresh for live
time.sleep(5)  # Placeholder; use st.rerun() in loop if needed
st.rerun()
