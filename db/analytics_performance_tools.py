# Draft code for analytics_query and performance_monitor tools
# Add these to src/tools.py and update src/config.py TOOLS list

import sqlite3
import psutil
import time
from collections import defaultdict, deque
import asyncio
from db.config import DB_PATH  # Database path configuration

# Global counters for performance monitoring (reset per session)
api_call_count = defaultdict(int)
response_times = []
start_time = time.time()

# Throughput tracking
throughput_history = deque(maxlen=100)  # Store last 100 throughput measurements
agent_throughput = defaultdict(lambda: deque(maxlen=50))  # Per-agent throughput
maf_throughput = deque(maxlen=50)  # MAF orchestration throughput


def reset_performance_counters():
    global api_call_count, response_times, start_time
    api_call_count.clear()
    response_times.clear()
    start_time = time.time()


# Tool: analytics_query
# Queries the swarm_rolls DB for stats
def analytics_query(query_type: str, agent_name: str = None, limit: int = 10) -> str:
    """
    Perform analytics queries on the swarm_rolls database.

    Args:
        query_type: Type of query ('summary', 'top_agents', 'agent_stats', 'roll_distribution')
        agent_name: Specific agent for 'agent_stats' (optional)
        limit: Limit for results (default 10)

    Returns:
        Formatted string with results
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        if query_type == "summary":
            # Overall summary
            cursor.execute("SELECT COUNT(*) as total_rolls, COUNT(DISTINCT agent_name) as agents FROM swarm_rolls")
            row = cursor.fetchone()
            cursor.execute("SELECT AVG(total) as avg_total, MAX(total) as max_total FROM swarm_rolls")
            stats = cursor.fetchone()
            result = f"""
Swarm Rolls Summary:
- Total Rolls: {row['total_rolls']}
- Unique Agents: {row['agents']}
- Average Total: {stats['avg_total']:.2f}
- Max Total: {stats['max_total']}
"""

        elif query_type == "top_agents":
            # Top agents by total rolls
            cursor.execute(
                """
                SELECT agent_name, COUNT(*) as roll_count, AVG(total) as avg_total, MAX(total) as max_total
                FROM swarm_rolls
                GROUP BY agent_name
                ORDER BY AVG(total) DESC
                LIMIT ?
            """,
                (limit,),
            )
            rows = cursor.fetchall()
            result = "Top Agents by Average Total:\n"
            for row in rows:
                result += f"- {row['agent_name']}: Rolls={row['roll_count']}, Avg={row['avg_total']:.2f}, Max={row['max_total']}\n"

        elif query_type == "agent_stats" and agent_name:
            # Stats for specific agent
            cursor.execute(
                """
                SELECT COUNT(*) as rolls, AVG(total) as avg_total, MIN(total) as min_total, MAX(total) as max_total
                FROM swarm_rolls
                WHERE agent_name = ?
            """,
                (agent_name,),
            )
            row = cursor.fetchone()
            if row:
                result = f"""
Stats for {agent_name}:
- Rolls: {row['rolls']}
- Avg Total: {row['avg_total']:.2f}
- Min Total: {row['min_total']}
- Max Total: {row['max_total']}
"""
            else:
                result = f"No data for agent {agent_name}"

        elif query_type == "roll_distribution":
            # Distribution of totals
            cursor.execute(
                "SELECT total, COUNT(*) as count FROM swarm_rolls GROUP BY total ORDER BY total LIMIT ?", (limit,)
            )
            rows = cursor.fetchall()
            result = "Roll Total Distribution (Top):\n"
            for row in rows:
                result += f"- {row['total']}: {row['count']} rolls\n"

        else:
            result = (
                f"Unknown query_type: {query_type}. Use 'summary', 'top_agents', 'agent_stats', 'roll_distribution'"
            )

    except Exception as e:
        result = f"Error in analytics_query: {str(e)}"
    finally:
        conn.close()

    return result


# Tool: performance_monitor
# Monitors system and agent performance metrics
def performance_monitor(mode: str = "snapshot") -> str:
    """
    Monitor performance metrics.

    Args:
        mode: 'snapshot' for current stats, 'reset' to reset counters

    Returns:
        Formatted string with metrics
    """
    if mode == "reset":
        reset_performance_counters()
        return "Performance counters reset."

    # System metrics
    cpu_percent = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    uptime = time.time() - start_time

    # API metrics (from globals)
    total_api_calls = sum(api_call_count.values())
    avg_response_time = sum(response_times) / len(response_times) if response_times else 0

    # MAF metrics
    maf_stats = get_maf_performance_stats()

    result = f"""
Performance Snapshot (Uptime: {uptime:.1f}s):

System Metrics:
- CPU Usage: {cpu_percent:.1f}%
- Memory: {memory.percent:.1f}% used ({memory.used / 1024**3:.1f}GB / {memory.total / 1024**3:.1f}GB)
- Disk: {disk.percent:.1f}% used ({disk.used / 1024**3:.1f}GB / {disk.total / 1024**3:.1f}GB)

API Metrics:
- Total Calls: {total_api_calls}
- Avg Response Time: {avg_response_time:.2f}s
- Calls per Agent: {dict(api_call_count)}

MAF Metrics:
- Total Orchestrations: {maf_stats['total_maf_orchestrations']}
- Success Rate: {maf_stats['maf_success_rate']:.1%}
- Avg Execution Time: {maf_stats['average_maf_execution_time']:.2f}s
- Provider Distribution: {maf_stats['maf_provider_distribution']}
"""

    return result


# Helper function to log API calls (call this in API wrapper)
def log_api_call(agent_name: str, response_time: float):
    api_call_count[agent_name] += 1
    response_times.append(response_time)


# MAF-specific performance tracking
maf_orchestration_count = 0
maf_successful_orchestrations = 0
maf_execution_times = []
maf_provider_usage = defaultdict(int)


def log_maf_orchestration(success: bool, execution_time: float, providers_used: int):
    """Log MAF orchestration performance."""
    global maf_orchestration_count, maf_successful_orchestrations
    maf_orchestration_count += 1
    maf_execution_times.append(execution_time)
    maf_provider_usage[providers_used] += 1

    if success:
        maf_successful_orchestrations += 1

    # Track MAF throughput (orchestrations per minute)
    current_time = time.time()
    maf_throughput.append((current_time, 1))  # (timestamp, count)


def log_agent_activity(agent_name: str, activity_type: str = "request"):
    """Log agent activity for throughput tracking."""
    current_time = time.time()
    agent_throughput[agent_name].append((current_time, 1))  # (timestamp, count)


def calculate_throughput(data_points: deque, time_window: int = 60) -> float:
    """Calculate throughput (events per minute) over a time window."""
    if not data_points:
        return 0.0

    current_time = time.time()
    # Filter points within the time window
    recent_points = [(t, c) for t, c in data_points if current_time - t <= time_window]

    if not recent_points:
        return 0.0

    # Sum counts in the time window
    total_count = sum(c for _, c in recent_points)
    # Calculate rate per minute
    time_span = min(time_window, current_time - recent_points[0][0])
    if time_span > 0:
        return (total_count / time_span) * 60  # per minute
    return 0.0


def get_throughput_metrics() -> Dict[str, Any]:
    """Get current throughput metrics."""
    return {
        "overall_api_throughput": calculate_throughput(throughput_history),
        "agent_throughput": {agent: calculate_throughput(data) for agent, data in agent_throughput.items()},
        "maf_throughput": calculate_throughput(maf_throughput),
        "time_window_minutes": 1,  # 1 minute window
    }


def get_performance_recommendations(perf_data: Dict[str, Any]) -> List[str]:
    """Generate performance optimization recommendations based on current metrics."""
    recommendations = []

    # System resource recommendations
    system = perf_data["system"]
    if system["cpu_percent"] > 80:
        recommendations.append(
            "[FAST] High CPU usage detected - consider optimizing compute-intensive operations or scaling resources"
        )
    elif system["cpu_percent"] < 10:
        recommendations.append(
            "💤 CPU utilization is low - consider consolidating workloads or rightsizing infrastructure"
        )

    if system["memory_percent"] > 85:
        recommendations.append(
            "[MEMORY] High memory usage - check for memory leaks, optimize caching, or increase memory allocation"
        )
    elif system["memory_percent"] < 20:
        recommendations.append("[MEMORY] Memory utilization is low - consider reducing memory allocation to optimize costs")

    if system["disk_percent"] > 90:
        recommendations.append("💾 Disk space running low - clean up old logs, backups, and temporary files")

    # API performance recommendations
    api = perf_data["api"]
    if api["avg_response_time"] > 5.0:
        recommendations.append(
            "🐌 Slow API response times - investigate network latency, optimize database queries, or implement caching"
        )
    elif api["avg_response_time"] < 0.1:
        recommendations.append("[ZEJZL] API responses are very fast - excellent performance!")

    if api["total_calls"] > 1000 and api["avg_response_time"] > 2.0:
        recommendations.append("[IMPROVEMENT] High API load with slow responses - consider load balancing or horizontal scaling")

    # MAF recommendations
    maf = perf_data["maf"]
    if maf["maf_success_rate"] < 0.8 and maf["total_maf_orchestrations"] > 10:
        recommendations.append("[GG] Low MAF success rate - review orchestration logic and error handling")

    if maf["average_maf_execution_time"] > 60:
        recommendations.append("⏱️ Slow MAF execution - optimize provider selection and parallel processing")

    # Throughput recommendations
    throughput = perf_data["throughput"]
    if throughput["overall_api_throughput"] > 100:
        recommendations.append("[STATS] High API throughput - ensure adequate rate limiting and resource allocation")

    if throughput["maf_throughput"] > 10:
        recommendations.append("[LOOP] High MAF orchestration rate - monitor for resource contention")

    # Agent-specific recommendations
    agent_calls = api["calls_per_agent"]
    if agent_calls:
        max_agent = max(agent_calls.keys(), key=lambda k: agent_calls[k])
        if agent_calls[max_agent] > sum(agent_calls.values()) * 0.7:
            recommendations.append(
                f"👤 Agent '{max_agent}' is handling most requests - consider load balancing across agents"
            )

    return recommendations


def get_maf_performance_stats() -> Dict[str, Any]:
    """Get MAF-specific performance statistics."""
    avg_execution_time = sum(maf_execution_times) / len(maf_execution_times) if maf_execution_times else 0.0
    most_common_providers = (
        max(maf_provider_usage.keys(), key=lambda k: maf_provider_usage[k]) if maf_provider_usage else 0
    )

    return {
        "total_maf_orchestrations": maf_orchestration_count,
        "successful_maf_orchestrations": maf_successful_orchestrations,
        "maf_success_rate": maf_successful_orchestrations / max(maf_orchestration_count, 1),
        "average_maf_execution_time": avg_execution_time,
        "maf_provider_distribution": dict(maf_provider_usage),
        "most_common_provider_count": most_common_providers,
    }


def get_performance_data() -> Dict[str, Any]:
    """
    Get structured performance data for dashboard integration.

    Returns:
        Dictionary with system, API, and MAF metrics
    """
    # System metrics
    cpu_percent = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    uptime = time.time() - start_time

    # API metrics
    total_api_calls = sum(api_call_count.values())
    avg_response_time = sum(response_times) / len(response_times) if response_times else 0

    # MAF metrics
    maf_stats = get_maf_performance_stats()

    # Throughput metrics
    throughput = get_throughput_metrics()

    return {
        "uptime": uptime,
        "system": {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_used_gb": memory.used / 1024**3,
            "memory_total_gb": memory.total / 1024**3,
            "disk_percent": disk.percent,
            "disk_used_gb": disk.used / 1024**3,
            "disk_total_gb": disk.total / 1024**3,
        },
        "api": {
            "total_calls": total_api_calls,
            "avg_response_time": avg_response_time,
            "calls_per_agent": dict(api_call_count),
        },
        "maf": maf_stats,
        "throughput": throughput,
    }


# Example usage in tools.py:
# async def analytics_query_tool(params):
#     result = analytics_query(params.get('query_type'), params.get('agent_name'), params.get('limit', 10))
#     return result
#
# async def performance_monitor_tool(params):
#     result = performance_monitor(params.get('mode', 'snapshot'))
#     return result
#
# Then add to TOOLS dict in config.py
