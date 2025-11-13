import streamlit as st
import redis
import requests
import psutil
import time
import json
from datetime import datetime
import subprocess
import GPUtil  # pip install gputil
import docker  # pip install docker
from db.analytics_performance_tools import (
    performance_monitor,
    analytics_query,
    reset_performance_counters,
    get_performance_data,
    get_performance_recommendations,
)
from anomaly_detector import detect_performance_anomalies, get_anomaly_detector

# Config
REDIS_HOST = "localhost"
REDIS_PORT = 6379
PROMETHEUS_URL = "http://localhost:9090"
DOCKER_SOCKET = "unix://var/run/docker.sock"

st.set_page_config(page_title="Grokputer Swarm Dashboard", layout="wide", initial_sidebar_state="expanded")


def get_redis_data():
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)
        proposals_keys = [k.decode() for k in r.keys("proposals_*")]
        proposals = []
        for key in proposals_keys:
            data = r.get(key)
            if data:
                proposals.append({"key": key, "data": json.loads(data)})
        haiku = r.get("eternal_bloom")
        haiku = haiku.decode() if haiku else "No haiku yet"
        evolutions_keys = [k.decode() for k in r.keys("agent_evolutions_*")]
        evolutions = []
        for key in evolutions_keys:
            data = r.get(key)
            if data:
                evolutions.append({"key": key, "data": json.loads(data)})
        return proposals, haiku, evolutions
    except Exception as e:
        st.error(f"Redis connection error: {e}")
        return [], "Error", []


def get_prometheus_data(query):
    try:
        response = requests.get(f"{PROMETHEUS_URL}/api/v1/query?query={query}")
        if response.status_code == 200:
            data = response.json()
            if data["status"] == "success" and data["data"]["resultType"] == "vector":
                return data["data"]["result"]
        return []
    except Exception as e:
        st.error(f"Prometheus query error: {e}")
        return []


def get_system_resources():
    cpu_percent = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory()
    ram_percent = ram.percent
    ram_used = ram.used / (1024**3)  # GB
    ram_total = ram.total / (1024**3)  # GB

    gpus = GPUtil.getGPUs()
    gpu_info = []
    if gpus:
        for gpu in gpus:
            gpu_info.append(
                {
                    "name": gpu.name,
                    "load": gpu.load * 100,
                    "memory_used": gpu.memoryUsed,
                    "memory_total": gpu.memoryTotal,
                }
            )

    return cpu_percent, ram_percent, ram_used, ram_total, gpu_info


def get_swarm_status():
    try:
        client = docker.from_env()
        stacks = client.stacks.list()
        if stacks:
            stack = stacks[0]  # Assume grokputer-swarm
            services = client.services.list(stack=stack.name)
            status = [
                {
                    "service": s.name,
                    "replicas": f"{s.spec.mode.Replicated.replicas}/{s.spec.mode.Replicated.replicas}",
                    "state": s.attrs["Spec"]["TaskTemplate"]["ContainerSpec"]["Image"],
                }
                for s in services
            ]
            return status
        return []
    except Exception as e:
        st.error(f"Docker/Swarm error: {e}")
        return []


st.title("🏛️ Grokputer Swarm Dashboard")
st.markdown("Live monitoring of daemon, swarm, resources, and Redis state.")

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    [
        "Prometheus Metrics",
        "Redis Proposals & Evolutions",
        "System Resources",
        "Performance & Agent Metrics",
        "Swarm Status",
    ]
)

with tab1:
    st.header("Prometheus Metrics")
    col1, col2, col3 = st.columns(3)

    with col1:
        cycles = get_prometheus_data("daemon_cycles_total")
        st.metric("Total Cycles", cycles[0]["value"][1] if cycles else 0)

    with col2:
        proposals = get_prometheus_data("proposals_generated_total")
        st.metric("Proposals Generated", proposals[0]["value"][1] if proposals else 0)

    with col3:
        applies = get_prometheus_data("proposals_applied_total")
        st.metric("Proposals Applied", applies[0]["value"][1] if applies else 0)

    # Chart for cycle duration
    duration = get_prometheus_data("rate(cycle_duration_seconds_sum[5m])")
    if duration:
        st.line_chart({"Duration": [float(duration[0]["value"][1])]})

    # Refresh button
    if st.button("Refresh Metrics"):
        st.rerun()

with tab2:
    st.header("Redis Data")
    proposals, haiku, evolutions = get_redis_data()

    st.subheader("Haiku")
    st.write(haiku)

    st.subheader("Proposals")
    if proposals:
        for prop in proposals:
            with st.expander(prop["key"]):
                st.json(prop["data"])
    else:
        st.info("No proposals yet—run the daemon!")

    st.subheader("Evolutions")
    if evolutions:
        for evol in evolutions:
            with st.expander(evol["key"]):
                st.json(evol["data"])
    else:
        st.info("No evolutions yet—let the swarm learn!")

with tab3:
    st.header("System Resources")
    cpu, ram_percent, ram_used, ram_total, gpus = get_system_resources()

    col1, col2 = st.columns(2)
    with col1:
        st.metric("CPU Usage", f"{cpu:.1f}%")
        st.metric("RAM Usage", f"{ram_percent:.1f}% ({ram_used:.1f}GB / {ram_total:.1f}GB)")

    with col2:
        if gpus:
            for gpu in gpus:
                st.metric(f"GPU {gpu['name']}", f"{gpu['load']:.1f}% MEM {gpu['memory_used']}/{gpu['memory_total']}MB")
        else:
            st.info("No GPU detected.")

    # Progress bars
    st.progress(cpu / 100)
    st.progress(ram_percent / 100)

    if st.button("Refresh Resources"):
        st.rerun()

with tab4:
    st.header("Swarm Status")
    status = get_swarm_status()
    if status:
        st.table(status)
    else:
        st.info("No Swarm stack found—run docker stack deploy.")

    # Docker stats
    try:
        result = subprocess.run(["docker", "stats", "--no-stream"], capture_output=True, text=True)
        st.code(result.stdout, language="text")
    except Exception as e:
        st.error(f"Docker stats error: {e}")

with tab5:
    st.header("Performance & Agent Metrics")

    # Get performance data
    perf_data = get_performance_data()

    # System Performance Metrics
    st.subheader("System Performance")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("CPU Usage", f"{perf_data['system']['cpu_percent']:.1f}%")
        st.metric("Memory Usage", f"{perf_data['system']['memory_percent']:.1f}%")
    with col2:
        st.metric("Memory Used", f"{perf_data['system']['memory_used_gb']:.1f}GB")
        st.metric("Disk Usage", f"{perf_data['system']['disk_percent']:.1f}%")
    with col3:
        st.metric("Uptime", f"{perf_data['uptime']:.1f}s")
        st.metric("Disk Used", f"{perf_data['system']['disk_used_gb']:.1f}GB")

    # Progress bars
    st.progress(perf_data["system"]["cpu_percent"] / 100, text="CPU")
    st.progress(perf_data["system"]["memory_percent"] / 100, text="Memory")
    st.progress(perf_data["system"]["disk_percent"] / 100, text="Disk")

    # API Performance Metrics
    st.subheader("API Performance")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total API Calls", perf_data["api"]["total_calls"])
        st.metric("Avg Response Time", f"{perf_data['api']['avg_response_time']:.2f}s")
    with col2:
        if perf_data["api"]["calls_per_agent"]:
            st.subheader("Calls per Agent")
            for agent, calls in perf_data["api"]["calls_per_agent"].items():
                st.metric(f"{agent}", calls)
        else:
            st.info("No API calls recorded yet")

    # Throughput Metrics
    st.subheader("Throughput Metrics (per minute)")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("API Throughput", f"{perf_data['throughput']['overall_api_throughput']:.1f} req/min")
    with col2:
        st.metric("MAF Throughput", f"{perf_data['throughput']['maf_throughput']:.1f} orch/min")
    with col3:
        st.metric("Time Window", f"{perf_data['throughput']['time_window_minutes']} min")

    # Agent Throughput Details
    if perf_data["throughput"]["agent_throughput"]:
        st.subheader("Agent Throughput Details")
        agent_cols = st.columns(min(len(perf_data["throughput"]["agent_throughput"]), 4))
        for i, (agent, throughput) in enumerate(perf_data["throughput"]["agent_throughput"].items()):
            if i < len(agent_cols):
                with agent_cols[i]:
                    st.metric(f"{agent}", f"{throughput:.1f} req/min")

    # MAF Orchestration Metrics
    st.subheader("MAF Orchestration Stats")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Orchestrations", perf_data["maf"]["total_maf_orchestrations"])
        st.metric("Success Rate", f"{perf_data['maf']['maf_success_rate']:.1%}")
    with col2:
        st.metric("Successful Orchestrations", perf_data["maf"]["successful_maf_orchestrations"])
        st.metric("Avg Execution Time", f"{perf_data['maf']['average_maf_execution_time']:.2f}s")
    with col3:
        if perf_data["maf"]["maf_provider_distribution"]:
            st.subheader("Provider Distribution")
            for providers, count in perf_data["maf"]["maf_provider_distribution"].items():
                st.metric(f"{providers} providers", count)
        else:
            st.info("No MAF orchestrations yet")

    # Agent Analytics
    st.subheader("Agent Performance Analytics")
    col1, col2 = st.columns(2)

    with col1:
        if st.button("Swarm Rolls Summary"):
            summary = analytics_query("summary")
            st.code(summary, language="text")

        if st.button("Top Agents"):
            top_agents = analytics_query("top_agents", limit=5)
            st.code(top_agents, language="text")

    with col2:
        agent_name = st.text_input("Agent Name for Stats:", placeholder="e.g., coordinator")
        if st.button("Get Agent Stats") and agent_name:
            agent_stats = analytics_query("agent_stats", agent_name=agent_name)
            st.code(agent_stats, language="text")

        if st.button("Roll Distribution"):
            distribution = analytics_query("roll_distribution", limit=10)
            st.code(distribution, language="text")

    # Performance Recommendations
    st.subheader("🚀 Performance Optimization Recommendations")
    if st.button("💡 Get Recommendations"):
        recommendations = get_performance_recommendations(perf_data)

        if recommendations:
            for rec in recommendations:
                st.info(rec)
        else:
            st.success("✅ System performance is optimal - no recommendations needed!")

    # Anomaly Detection
    st.subheader("🔍 Anomaly Detection")
    if st.button("🔍 Detect Anomalies"):
        anomaly_result = detect_performance_anomalies()

        # Display anomalies
        anomalies = anomaly_result["anomalies"]
        if any(anomalies.values()):
            st.error("⚠️ Anomalies Detected!")
            for metric, is_anomaly in anomalies.items():
                if is_anomaly:
                    st.warning(f"🚨 {metric.replace('_', ' ').title()} anomaly detected")
        else:
            st.success("✅ No anomalies detected - system performing normally")

        # Display anomaly recommendations
        anomaly_recs = anomaly_result.get("recommendations", [])
        if anomaly_recs:
            st.subheader("💡 Anomaly-Based Recommendations")
            for rec in anomaly_recs:
                st.warning(f"• {rec}")

        # Anomaly statistics
        stats = anomaly_result["anomaly_stats"]
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Anomalies", stats["total_anomalies"])
        with col2:
            st.metric("Detection Window", stats["window_size"])
        with col3:
            st.metric("Threshold (σ)", stats["threshold_std"])

    # Reset Counters
    if st.button("Reset Performance Counters"):
        reset_msg = performance_monitor("reset")
        st.success(reset_msg)
        st.rerun()

# Auto-refresh
time.sleep(5)
st.rerun()
