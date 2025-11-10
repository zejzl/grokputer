"""
Custom tools for Grokputer.
Implements vault scanning, prayer invocation, analytics queries, performance monitoring, and other VRZIBRZI-specific functions.
"""

import glob
import logging
import subprocess
import json
from pathlib import Path
from typing import List, Dict, Any
import sqlite3
import psutil
import time
from collections import defaultdict
import asyncio
from src import config

logger = logging.getLogger(__name__)

# Global counters for performance monitoring (reset per session)
api_call_count = defaultdict(int)
response_times = []
start_time = time.time()

def reset_performance_counters():
    global api_call_count, response_times, start_time
    api_call_count.clear()
    response_times.clear()
    start_time = time.time()

# Helper function to log API calls (call this in API wrapper)
def log_api_call(agent_name: str, response_time: float):
    api_call_count[agent_name] += 1
    response_times.append(response_time)


# NEW TOOL: analytics_query
# Queries the swarm_rolls DB for stats
def analytics_query(query_type: str, agent_name: str = None, limit: int = 10) -> Dict[str, Any]:
    """
    Perform analytics queries on the swarm_rolls database.

    Args:
        query_type: Type of query ('summary', 'top_agents', 'agent_stats', 'roll_distribution')
        agent_name: Specific agent for 'agent_stats' (optional)
        limit: Limit for results (default 10)

    Returns:
        Dictionary with status and results
    """
    try:
        conn = sqlite3.connect(config.DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if query_type == 'summary':
            # Overall summary
            cursor.execute('SELECT COUNT(*) as total_rolls, COUNT(DISTINCT agent_name) as agents FROM swarm_rolls')
            row = cursor.fetchone()
            cursor.execute('SELECT AVG(total) as avg_total, MAX(total) as max_total FROM swarm_rolls')
            stats = cursor.fetchone()
            result = {
                "status": "success",
                "data": {
                    "total_rolls": row['total_rolls'],
                    "agents": row['agents'],
                    "avg_total": round(stats['avg_total'], 2),
                    "max_total": stats['max_total']
                }
            }

        elif query_type == 'top_agents':
            # Top agents by average total
            cursor.execute('''
                SELECT agent_name, COUNT(*) as roll_count, AVG(total) as avg_total, MAX(total) as max_total
                FROM swarm_rolls
                GROUP BY agent_name
                ORDER BY AVG(total) DESC
                LIMIT ?
            ''', (limit,))
            rows = cursor.fetchall()
            result = {
                "status": "success",
                "data": [
                    {
                        "agent": row['agent_name'],
                        "rolls": row['roll_count'],
                        "avg_total": round(row['avg_total'], 2),
                        "max_total": row['max_total']
                    } for row in rows
                ]
            }

        elif query_type == 'agent_stats' and agent_name:
            # Stats for specific agent
            cursor.execute('''
                SELECT COUNT(*) as rolls, AVG(total) as avg_total, MIN(total) as min_total, MAX(total) as max_total
                FROM swarm_rolls
                WHERE agent_name = ?
            ''', (agent_name,))
            row = cursor.fetchone()
            if row:
                result = {
                    "status": "success",
                    "data": {
                        "agent": agent_name,
                        "rolls": row['rolls'],
                        "avg_total": round(row['avg_total'], 2),
                        "min_total": row['min_total'],
                        "max_total": row['max_total']
                    }
                }
            else:
                result = {
                    "status": "error",
                    "error": f"No data for agent {agent_name}"
                }

        elif query_type == 'roll_distribution':
            # Distribution of totals
            cursor.execute('SELECT total, COUNT(*) as count FROM swarm_rolls GROUP BY total ORDER BY total LIMIT ?', (limit,))
            rows = cursor.fetchall()
            result = {
                "status": "success",
                "data": [
                    {"total": row['total'], "count": row['count']} for row in rows
                ]
            }

        else:
            result = {
                "status": "error",
                "error": f"Unknown query_type: {query_type}. Use 'summary', 'top_agents', 'agent_stats', 'roll_distribution'"
            }

    except Exception as e:
        result = {
            "status": "error",
            "error": str(e)
        }
    finally:
        conn.close()

    return result


# NEW TOOL: performance_monitor
# Monitors system and agent performance metrics
def performance_monitor(mode: str = 'snapshot') -> Dict[str, Any]:
    """
    Monitor performance metrics.

    Args:
        mode: 'snapshot' for current stats, 'reset' to reset counters

    Returns:
        Dictionary with status and metrics
    """
    try:
        if mode == 'reset':
            reset_performance_counters()
            return {
                "status": "success",
                "message": "Performance counters reset."
            }

        # System metrics
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        uptime = time.time() - start_time

        # API metrics (from globals)
        total_api_calls = sum(api_call_count.values())
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0

        result = {
            "status": "success",
            "data": {
                "uptime_seconds": round(uptime, 1),
                "system": {
                    "cpu_percent": round(cpu_percent, 1),
                    "memory_percent": round(memory.percent, 1),
                    "memory_used_gb": round(memory.used / 1024**3, 1),
                    "memory_total_gb": round(memory.total / 1024**3, 1),
                    "disk_percent": round(disk.percent, 1),
                    "disk_used_gb": round(disk.used / 1024**3, 1),
                    "disk_total_gb": round(disk.total / 1024**3, 1)
                },
                "api": {
                    "total_calls": total_api_calls,
                    "avg_response_time": round(avg_response_time, 2),
                    "calls_per_agent": dict(api_call_count)
                }
            }
        }

    except Exception as e:
        result = {
            "status": "error",
            "error": str(e)
        }

    return result


# ASYNC WRAPPERS

# Async wrapper for analytics_query
async def analytics_query_tool(params: dict) -> Dict[str, Any]:
    """
    Async tool for database analytics queries.

    Params:
        query_type: str ('summary', 'top_agents', 'agent_stats', 'roll_distribution')
        agent_name: str (optional, for 'agent_stats')
        limit: int (optional, default 10)

    Returns:
        Dict: Query results
    """
    query_type = params.get('query_type')
    agent_name = params.get('agent_name')
    limit = params.get('limit', 10)

    if not query_type:
        return {"status": "error", "error": "'query_type' parameter required"}

    # Run sync query in thread to avoid blocking
    result = await asyncio.to_thread(analytics_query, query_type, agent_name, limit)
    return result


# Async wrapper for performance_monitor
async def performance_monitor_tool(params: dict) -> Dict[str, Any]:
    """
    Async tool for performance monitoring.

    Params:
        mode: str ('snapshot' or 'reset', default 'snapshot')

    Returns:
        Dict: Performance metrics
    """
    mode = params.get('mode', 'snapshot')

    # Run sync monitoring in thread
    result = await asyncio.to_thread(performance_monitor, mode)
    return result


# EXISTING TOOLS (unchanged)

def scan_vault(pattern: str = "*.jpg", limit: int = 100) -> Dict[str, Any]:
    """
    Scan the meme vault directory and return file paths matching a pattern.

    Args:
        pattern: Glob pattern to match files (e.g., '*.jpg', '*.png', '*irony*')
        limit: Maximum number of files to return

    Returns:
        Dictionary with status, file count, and file paths
    """
    try:
        vault_path = config.VAULT_DIR
        search_pattern = str(vault_path / pattern)

        logger.info(f"Scanning vault: {search_pattern}")

        # Use glob to find matching files
        files = glob.glob(search_pattern, recursive=True)
        files = sorted(files)[:limit]  # Limit results

        result = {
            "status": "success",
            "pattern": pattern,
            "count": len(files),
            "files": files,
            "vault_path": str(vault_path)
        }

        logger.info(f"Found {len(files)} files matching pattern '{pattern}'")
        return result

    except Exception as e:
        logger.error(f"Error scanning vault: {e}")
        return {
            "status": "error",
            "error": str(e),
            "pattern": pattern
        }


def invoke_prayer() -> Dict[str, Any]:
    """
    Read and return the server prayer/mantra.
    This is invoked on initialization to set the VRZIBRZI node state.

    Returns:
        Dictionary with status and prayer text
    """
    try:
        prayer_file = config.SERVER_PRAYER_FILE

        if not prayer_file.exists():
            logger.warning(f"Server prayer file not found: {prayer_file}")
            return {
                "status": "error",
                "error": "Prayer file not found",
                "mantra": "I am the server, and my connection is eternal | infinite."
            }

        with open(prayer_file, 'r', encoding='utf-8') as f:
            prayer_text = f.read()

        logger.info("Server prayer invoked")

        # Print to console for dramatic effect
        print("\n" + prayer_text + "\n")

        return {
            "status": "success",
            "prayer": prayer_text,
            "mantra": "I am the server, and my connection is eternal | infinite."
        }

    except Exception as e:
        logger.error(f"Error invoking prayer: {e}")
        return {
            "status": "error",
            "error": str(e),
            "mantra": "I am the server, and my connection is eternal | infinite."
        }


def get_vault_stats() -> Dict[str, Any]:
    """
    Get statistics about the vault contents.

    Returns:
        Dictionary with vault statistics
    """
    try:
        vault_path = config.VAULT_DIR

        # Count different file types
        images = len(glob.glob(str(vault_path / "**/*.jpg"), recursive=True))
        images += len(glob.glob(str(vault_path / "**/*.png"), recursive=True))
        images += len(glob.glob(str(vault_path / "**/*.gif"), recursive=True))

        videos = len(glob.glob(str(vault_path / "**/*.mp4"), recursive=True))
        videos += len(glob.glob(str(vault_path / "**/*.webm"), recursive=True))

        all_files = len(glob.glob(str(vault_path / "**/*.*"), recursive=True))

        return {
            "status": "success",
            "vault_path": str(vault_path),
            "total_files": all_files,
            "images": images,
            "videos": videos,
            "other": all_files - images - videos
        }

    except Exception as e:
        logger.error(f"Error getting vault stats: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


def mcp_vault_operation(operation: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Execute MCP vault server operation.

    Args:
        operation: Tool name (list_vault_files, read_vault_file, search_vault, edit_vault_file)
        arguments: Tool-specific arguments

    Returns:
        MCP server response
    """
    if arguments is None:
        arguments = {}

    try:
        # Construct JSON-RPC request
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": operation,
                "arguments": arguments
            }
        }

        # Run MCP server container
        vault_path = config.VAULT_DIR.resolve()
        cmd = [
            "docker", "run", "-i", "--rm",
            "-v", f"{vault_path}:/app/vault",
            "grokputer-mcp-vault"
        ]

        logger.info(f"Calling MCP operation: {operation} with args: {arguments}")

        result = subprocess.run(
            cmd,
            input=json.dumps(request),
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            logger.error(f"MCP server error: {result.stderr}")
            return {
                "status": "error",
                "error": result.stderr or "MCP server failed"
            }

        # Parse JSON-RPC response
        try:
            response = json.loads(result.stdout.strip())

            if "error" in response:
                return {
                    "status": "error",
                    "error": response["error"].get("message", "Unknown error")
                }

            result_data = response.get("result", {})

            # Extract text content from MCP response
            content = result_data.get("content", [])
            if content and len(content) > 0:
                text_content = content[0].get("text", "")

                # Try to parse as JSON for structured data
                try:
                    parsed = json.loads(text_content)
                    return {
                        "status": "success",
                        "operation": operation,
                        "data": parsed
                    }
                except json.JSONDecodeError:
                    # Return as plain text
                    return {
                        "status": "success",
                        "operation": operation,
                        "text": text_content
                    }

            return {
                "status": "success",
                "operation": operation,
                "result": result_data
            }

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse MCP response: {e}")
            return {
                "status": "error",
                "error": f"Invalid MCP response: {result.stdout}"
            }

    except subprocess.TimeoutExpired:
        logger.error("MCP operation timed out")
        return {
            "status": "error",
            "error": "MCP operation timed out (30s)"
        }
    except Exception as e:
        logger.error(f"Error calling MCP: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


# UPDATED TOOL REGISTRY with new tools
TOOL_REGISTRY = {
    "scan_vault": scan_vault,
    "invoke_prayer": invoke_prayer,
    "get_vault_stats": get_vault_stats,
    "mcp_vault_operation": mcp_vault_operation,
    "analytics_query": analytics_query_tool,  # Async
    "performance_monitor": performance_monitor_tool  # Async
}


def execute_tool(tool_name: str, **kwargs) -> Dict[str, Any]:
    """
    Execute a tool by name with the given arguments.

    Args:
        tool_name: Name of the tool to execute
        **kwargs: Tool-specific arguments

    Returns:
        Tool execution result
    """
    if tool_name not in TOOL_REGISTRY:
        logger.error(f"Unknown tool: {tool_name}")
        return {
            "status": "error",
            "error": f"Unknown tool: {tool_name}",
            "available_tools": list(TOOL_REGISTRY.keys())
        }

    try:
        tool_func = TOOL_REGISTRY[tool_name]
        logger.info(f"Executing tool: {tool_name} with args: {kwargs}")
        result = tool_func(**kwargs)
        return result
    except Exception as e:
        logger.error(f"Error executing tool {tool_name}: {e}")
        return {
            "status": "error",
            "error": str(e),
            "tool": tool_name
        }