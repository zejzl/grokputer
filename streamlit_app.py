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
from typing import Dict, Any

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

def run_swarm(task: str, session_id: str = None, backend: str = "qwen", agent_roles: str = "coordinator,observer,actor"):
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
st.markdown("Monitor, queue, and visualize multi-agent swarms. Eternal memory via Redis. Backend: Qwen (local) or Grok (API).")

# Sidebar: Controls
with st.sidebar:
    st.header("Task Queue")
    task = st.text_input("Enter task:", placeholder="e.g., List files in vault and create summary.md")
    backend = st.selectbox("Backend:", ["qwen (local GGUF)", "grok (API)"])
    agent_roles = st.text_input("Agent Roles:", value="coordinator,observer,actor", help="Comma-separated: coordinator,observer,actor")
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
        # Embed viz from view_sessions
        with st.spinner("Loading visualization..."):
            # Simulate calling view_sessions (output to temp file or capture)
            viz_output = subprocess.run(["python", "view_sessions.py", selected_session], capture_output=True, text=True)
            st.text(viz_output.stdout)
        
        # Metrics expander
        with st.expander("Detailed Metrics"):
            if "activities" in st.session_state:  # Assume from logs
                st.metric("Actions Executed", 5)
                st.metric("Success Rate", "100%")
                st.metric("Duration", "12s")

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