#!/usr/bin/env python3
"""
Enhanced Streamlit Dashboard for Grokputer
Real-time analytics, performance graphs, agent metrics, and session overview.
Integrates with analytics.py and hierarchical memory.
Run with: streamlit run streamlit_app.py
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sqlite3
import json
from datetime import datetime, timedelta
import time
import psutil  # For real-time system metrics
from analytics import generate_report, init_db  # Integrate with analytics
from src.memory.hierarchical_memory import HierarchicalMemory  # Memory integration

# Page config
st.set_page_config(
    page_title="Grokputer Dashboard",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'memory' not in st.session_state:
    st.session_state.memory = HierarchicalMemory()

# Sidebar
st.sidebar.title("Grokputer Controls")
log_level = st.sidebar.selectbox("Log Level", ['INFO', 'DEBUG', 'WARNING'])
st.sidebar.slider("Refresh Rate (s)", 1, 10, 5)

# Initialize analytics DB
init_db()

# Main dashboard
st.title("🤖 Grokputer - Real-Time Analytics & Performance Dashboard")
st.markdown("**Enhanced monitoring with analytics, graphs, and system metrics.**")

# Row 1: Key Metrics
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Sessions", generate_report()['total_sessions'])
with col2:
    st.metric("Success Rate", f"{generate_report()['success_rate_percent']}%")
with col3:
    st.metric("Avg Duration", f"{generate_report()['avg_duration_seconds']:.2f}s")
with col4:
    st.metric("Total API Calls", generate_report()['total_api_calls'])

# Row 2: Analytics Report
st.subheader("[STATS] Recent Analytics Report (Last 7 Days)")
report = generate_report(7)
st.json(report)

# Row 3: Performance Graphs
st.subheader("[IMPROVEMENT] Performance Metrics")
placeholder = st.empty()

# Real-time system metrics (CPU, Memory)
def get_system_metrics():
    return {
        'cpu': psutil.cpu_percent(interval=1),
        'memory': psutil.virtual_memory().percent,
        'disk': psutil.disk_usage('/').percent
    }

# Simulate real-time updates (use st.rerun for live)
if st.button("Update Metrics"):
    metrics = get_system_metrics()
    fig = make_subplots(rows=1, cols=3, subplot_titles=('CPU %', 'Memory %', 'Disk %'))
    fig.add_trace(go.Indicator(mode="gauge+number", value=metrics['cpu'], title='CPU'), row=1, col=1)
    fig.add_trace(go.Indicator(mode="gauge+number", value=metrics['memory'], title='Memory'), row=1, col=2)
    fig.add_trace(go.Indicator(mode="gauge+number", value=metrics['disk'], title='Disk'), row=1, col=3)
    fig.update_layout(height=300)
    st.plotly_chart(fig, use_container_width=True)

# Historical API Calls Graph
st.subheader("🌐 API Calls Over Time")
conn = sqlite3.connect('./db/metrics.db')
df = pd.read_sql_query("""
    SELECT timestamp, endpoint, response_time 
    FROM api_calls 
    ORDER BY timestamp DESC 
    LIMIT 100
""", conn)
conn.close()

if not df.empty:
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    fig = px.line(df, x='timestamp', y='response_time', color='endpoint', title='Recent API Response Times')
    st.plotly_chart(fig, use_container_width=True)

# Agent Iterations and Success Rate Chart
st.subheader("[LOOP] Agent Performance")
conn = sqlite3.connect('./db/metrics.db')
df_sessions = pd.read_sql_query("""
    SELECT start_time, iterations, success, provider 
    FROM sessions 
    ORDER BY start_time DESC 
    LIMIT 50
""", conn)
conn.close()

if not df_sessions.empty:
    df_sessions['start_time'] = pd.to_datetime(df_sessions['start_time'])
    fig_success = px.bar(df_sessions, x='start_time', y='iterations', color='success', 
                         title='Iterations by Success', color_discrete_map={True: 'green', False: 'red'})
    st.plotly_chart(fig_success, use_container_width=True)

    # Provider Breakdown Pie
    provider_counts = df_sessions['provider'].value_counts()
    fig_pie = px.pie(values=provider_counts.values, names=provider_counts.index, title='Sessions by Provider')
    st.plotly_chart(fig_pie, use_container_width=True)

# Memory Usage Visualization
st.subheader("[MEMORY] Hierarchical Memory Overview")
memory_stats = {
    'short_term': len(st.session_state.memory.layers['short_term'].data),
    'context': len(st.session_state.memory.layers['context'].data),
    'long_term': len(st.session_state.memory.layers['long_term'].data)
}
st.bar_chart(memory_stats)

# Simulate memory operations for demo
if st.button("Simulate Memory Store/Retrieve"):
    key = f"demo_{int(time.time())}"
    st.session_state.memory.store(key, {"data": "sample"}, layer='context')
    retrieved = st.session_state.memory.retrieve(key, layer='context')
    st.success(f"Stored and retrieved: {retrieved}")

# Logs Preview (Tail last 20 lines)
st.subheader("📝 Recent Logs")
with open('./logs/grokputer_structured.log', 'r') as f:
    logs = f.readlines()[-20:]
st.text("\n".join(logs))

# Auto-refresh placeholder
with placeholder.container():
    st.info("Dashboard auto-refreshes every 5 seconds for real-time updates.")
    time.sleep(5)  # Simulate; in prod use st.rerun()

# Footer
st.markdown("---")
st.markdown("*ZA GROKA. Analytics & Optimizations Active.*")