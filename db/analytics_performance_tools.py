# Draft code for analytics_query and performance_monitor tools
# Add these to src/tools.py and update src/config.py TOOLS list

import sqlite3
import psutil
import time
from collections import defaultdict
import asyncio
from config import DB_PATH  # Assuming config.py has DB_PATH

# Global counters for performance monitoring (reset per session)
api_call_count = defaultdict(int)
response_times = []
start_time = time.time()

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
        if query_type == 'summary':
            # Overall summary
            cursor.execute('SELECT COUNT(*) as total_rolls, COUNT(DISTINCT agent_name) as agents FROM swarm_rolls')
            row = cursor.fetchone()
            cursor.execute('SELECT AVG(total) as avg_total, MAX(total) as max_total FROM swarm_rolls')
            stats = cursor.fetchone()
            result = f"""
Swarm Rolls Summary:
- Total Rolls: {row['total_rolls']}
- Unique Agents: {row['agents']}
- Average Total: {stats['avg_total']:.2f}
- Max Total: {stats['max_total']}
"""

        elif query_type == 'top_agents':
            # Top agents by total rolls
            cursor.execute('''
                SELECT agent_name, COUNT(*) as roll_count, AVG(total) as avg_total, MAX(total) as max_total
                FROM swarm_rolls
                GROUP BY agent_name
                ORDER BY AVG(total) DESC
                LIMIT ?
            ''', (limit,))
            rows = cursor.fetchall()
            result = "Top Agents by Average Total:\n"
            for row in rows:
                result += f"- {row['agent_name']}: Rolls={row['roll_count']}, Avg={row['avg_total']:.2f}, Max={row['max_total']}\n"

        elif query_type == 'agent_stats' and agent_name:
            # Stats for specific agent
            cursor.execute('''
                SELECT COUNT(*) as rolls, AVG(total) as avg_total, MIN(total) as min_total, MAX(total) as max_total
                FROM swarm_rolls
                WHERE agent_name = ?
            ''', (agent_name,))
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

        elif query_type == 'roll_distribution':
            # Distribution of totals
            cursor.execute('SELECT total, COUNT(*) as count FROM swarm_rolls GROUP BY total ORDER BY total LIMIT ?', (limit,))
            rows = cursor.fetchall()
            result = "Roll Total Distribution (Top):\n"
            for row in rows:
                result += f"- {row['total']}: {row['count']} rolls\n"

        else:
            result = f"Unknown query_type: {query_type}. Use 'summary', 'top_agents', 'agent_stats', 'roll_distribution'"

    except Exception as e:
        result = f"Error in analytics_query: {str(e)}"
    finally:
        conn.close()

    return result

# Tool: performance_monitor
# Monitors system and agent performance metrics
def performance_monitor(mode: str = 'snapshot') -> str:
    """
    Monitor performance metrics.

    Args:
        mode: 'snapshot' for current stats, 'reset' to reset counters

    Returns:
        Formatted string with metrics
    """
    if mode == 'reset':
        reset_performance_counters()
        return "Performance counters reset."

    # System metrics
    cpu_percent = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    uptime = time.time() - start_time

    # API metrics (from globals)
    total_api_calls = sum(api_call_count.values())
    avg_response_time = sum(response_times) / len(response_times) if response_times else 0

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
"""

    return result

# Helper function to log API calls (call this in API wrapper)
def log_api_call(agent_name: str, response_time: float):
    api_call_count[agent_name] += 1
    response_times.append(response_time)

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