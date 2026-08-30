#!/usr/bin/env python3
"""
Custom tools for Grokputer.
Implements vault scanning, prayer invocation, analytics queries, performance monitoring, and other VRZIBRZI-specific functions.
"""
from __future__ import annotations

import asyncio
import glob
import json
import logging
import sqlite3
import subprocess
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List

import psutil

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

        if query_type == "summary":
            # Overall summary
            cursor.execute("SELECT COUNT(*) as total_rolls, COUNT(DISTINCT agent_name) as agents FROM swarm_rolls")
            row = cursor.fetchone()
            cursor.execute("SELECT AVG(total) as avg_total, MAX(total) as max_total FROM swarm_rolls")
            stats = cursor.fetchone()
            result = {
                "status": "success",
                "data": {
                    "total_rolls": row["total_rolls"],
                    "agents": row["agents"],
                    "avg_total": round(stats["avg_total"], 2),
                    "max_total": stats["max_total"],
                },
            }

        elif query_type == "top_agents":
            # Top agents by average total
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
            result = {
                "status": "success",
                "data": [
                    {
                        "agent": row["agent_name"],
                        "rolls": row["roll_count"],
                        "avg_total": round(row["avg_total"], 2),
                        "max_total": row["max_total"],
                    }
                    for row in rows
                ],
            }

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
                result = {
                    "status": "success",
                    "data": {
                        "agent": agent_name,
                        "rolls": row["rolls"],
                        "avg_total": round(row["avg_total"], 2),
                        "min_total": row["min_total"],
                        "max_total": row["max_total"],
                    },
                }
            else:
                result = {"status": "error", "error": f"No data for agent {agent_name}"}

        elif query_type == "roll_distribution":
            # Distribution of totals
            cursor.execute(
                "SELECT total, COUNT(*) as count FROM swarm_rolls GROUP BY total ORDER BY total LIMIT ?", (limit,)
            )
            rows = cursor.fetchall()
            result = {"status": "success", "data": [{"total": row["total"], "count": row["count"]} for row in rows]}

        else:
            result = {
                "status": "error",
                "error": f"Unknown query_type: {query_type}. Use 'summary', 'top_agents', 'agent_stats', 'roll_distribution'",
            }

    except Exception as e:
        result = {"status": "error", "error": str(e)}
    finally:
        conn.close()

    return result


# NEW TOOL: performance_monitor
# Monitors system and agent performance metrics
def performance_monitor(mode: str = "snapshot") -> Dict[str, Any]:
    """
    Monitor performance metrics.

    Args:
        mode: 'snapshot' for current stats, 'reset' to reset counters

    Returns:
        Dictionary with status and metrics
    """
    try:
        if mode == "reset":
            reset_performance_counters()
            return {"status": "success", "message": "Performance counters reset."}

        # System metrics
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
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
                    "disk_total_gb": round(disk.total / 1024**3, 1),
                },
                "api": {
                    "total_calls": total_api_calls,
                    "avg_response_time": round(avg_response_time, 2),
                    "calls_per_agent": dict(api_call_count),
                },
            },
        }

    except Exception as e:
        result = {"status": "error", "error": str(e)}

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
    query_type = params.get("query_type")
    agent_name = params.get("agent_name")
    limit = params.get("limit", 10)

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
    mode = params.get("mode", "snapshot")

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
            "vault_path": str(vault_path),
        }

        logger.info(f"Found {len(files)} files matching pattern '{pattern}'")
        return result

    except Exception as e:
        logger.error(f"Error scanning vault: {e}")
        return {"status": "error", "error": str(e), "pattern": pattern}


def invoke_prayer() -> Dict[str, Any]:
    """
    Invoke the server prayer.
    """
    return {"status": "success", "message": "ETERNAL | INFINITE"}


def generate_code(filename: str, code_content: str, sandbox_dir: str = "outputs") -> Dict[str, Any]:
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
            "other": all_files - images - videos,
        }

    except Exception as e:
        logger.error(f"Error getting vault stats: {e}")
        return {"status": "error", "error": str(e)}


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
            "params": {"name": operation, "arguments": arguments},
        }

        # Run MCP server container
        vault_path = config.VAULT_DIR.resolve()
        cmd = ["docker", "run", "-i", "--rm", "-v", f"{vault_path}:/app/vault", "grokputer-mcp-vault"]

        logger.info(f"Calling MCP operation: {operation} with args: {arguments}")

        result = subprocess.run(cmd, input=json.dumps(request), capture_output=True, text=True, timeout=30)

        if result.returncode != 0:
            logger.error(f"MCP server error: {result.stderr}")
            return {"status": "error", "error": result.stderr or "MCP server failed"}

        # Parse JSON-RPC response
        try:
            response = json.loads(result.stdout.strip())

            if "error" in response:
                return {"status": "error", "error": response["error"].get("message", "Unknown error")}

            result_data = response.get("result", {})

            # Extract text content from MCP response
            content = result_data.get("content", [])
            if content and len(content) > 0:
                text_content = content[0].get("text", "")

                # Try to parse as JSON for structured data
                try:
                    parsed = json.loads(text_content)
                    return {"status": "success", "operation": operation, "data": parsed}
                except json.JSONDecodeError:
                    # Return as plain text
                    return {"status": "success", "operation": operation, "text": text_content}

            return {"status": "success", "operation": operation, "result": result_data}

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse MCP response: {e}")
            return {"status": "error", "error": f"Invalid MCP response: {result.stdout}"}

    except subprocess.TimeoutExpired:
        logger.error("MCP operation timed out")
        return {"status": "error", "error": "MCP operation timed out (30s)"}
    except Exception as e:
        logger.error(f"Error calling MCP: {e}")
        return {"status": "error", "error": str(e)}


# UPDATED TOOL REGISTRY with new tools
TOOL_REGISTRY = {
    "scan_vault": scan_vault,
    "invoke_prayer": invoke_prayer,
    "get_vault_stats": get_vault_stats,
    "mcp_vault_operation": mcp_vault_operation,
    "analytics_query": analytics_query_tool,  # Async
    "performance_monitor": performance_monitor_tool,  # Async
}


def execute_tool(tool_name: str, **kwargs) -> Dict[str, Any]:
    """
    Execute a tool by name with the given arguments.

    Args:
        filename: Name of the file to create (e.g., 'season_haiku.py').
        code_content: The full Python code as string.
        sandbox_dir: Directory to write the file (default 'outputs').

    Returns:
        Dict with status, path, and any errors.
    """
    try:
        # Validate syntax before writing
        ast.parse(code_content)

        # Create sandbox dir if needed
        sandbox_path = Path(sandbox_dir)
        sandbox_path.mkdir(exist_ok=True)

        # Full path
        file_path = sandbox_path / filename

        # Write file
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(code_content)

        return {"status": "success", "path": str(file_path), "message": f"Generated script at {file_path}"}
    except SyntaxError as e:
        return {"status": "error", "message": f"Syntax error in generated code: {e}"}
    except Exception as e:
        return {"status": "error", "message": f"Failed to generate script: {e}"}


def execute_generated_code(filename: str, sandbox_dir: str = "outputs") -> Dict[str, Any]:
    """
    Execute the generated Python script and capture output.

    Args:
        filename: Name of the script to run (e.g., 'season_haiku.py').
        sandbox_dir: Directory where the script is located.

    Returns:
        Dict with status, output, and any errors.
    """
    try:
        file_path = Path(sandbox_dir) / filename

        if not file_path.exists():
            return {"status": "error", "message": f"Script {file_path} not found"}

        # Run the script, capture stdout/stderr
        result = subprocess.run(
            [sys.executable, str(file_path)], capture_output=True, text=True, timeout=30  # 30s timeout for safety
        )

        output = result.stdout if result.stdout else "No output."
        error = result.stderr if result.stderr else None

        if result.returncode == 0:
            return {"status": "success", "output": output, "message": f"Executed {filename} successfully"}
        else:
            return {
                "status": "error",
                "output": output,
                "error": error,
                "message": f"Script failed with code {result.returncode}",
            }
    except subprocess.TimeoutExpired:
        return {"status": "error", "message": "Script execution timed out (30s limit)"}
    except Exception as e:
        return {"status": "error", "message": f"Failed to execute script: {e}"}


def bash(command: str) -> Dict[str, Any]:
    """
    Execute a bash/shell command.

    Args:
        command: The command to execute.

    Returns:
        Dict with status, output, and any errors.
    """
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=30  # 30s timeout for safety
        )

        output = result.stdout if result.stdout else "No output."
        error = result.stderr if result.stderr else None

        if result.returncode == 0:
            return {"status": "success", "output": output, "message": f"Command executed successfully"}
        else:
            return {
                "status": "error",
                "output": output,
                "error": error,
                "message": f"Command failed with code {result.returncode}",
            }
    except subprocess.TimeoutExpired:
        return {"status": "error", "message": "Command execution timed out (30s limit)"}
    except Exception as e:
        return {"status": "error", "message": f"Failed to execute command: {e}"}


def search(query: str, path: str = ".") -> Dict[str, Any]:
    """
    Search for text in files.

    Args:
        query: Text to search for.
        path: Directory to search in.

    Returns:
        Dict with status and search results.
    """
    try:
        import os

        results = []
        for root, dirs, files in os.walk(path):
            for file in files:
                if file.endswith((".py", ".md", ".txt", ".json")):
                    try:
                        with open(os.path.join(root, file), "r", encoding="utf-8") as f:
                            content = f.read()
                            if query in content:
                                results.append(f"{os.path.join(root, file)}: {content.count(query)} matches")
                    except:
                        pass  # Skip files that can't be read

        return {"status": "success", "results": results, "message": f"Found {len(results)} files containing '{query}'"}
    except Exception as e:
        return {"status": "error", "message": f"Search failed: {e}"}
        logger.error(f"Error executing tool {tool_name}: {e}")
        return {
            "status": "error",
            "error": str(e),
            "tool": tool_name,
        }  # Enhancement to analytics tools based on grokputer_swarm_examples.md


# Adds swarm performance analytics: execution times, success rates, message counts, agent efficiency

import re
import sqlite3
from pathlib import Path
from typing import Any, Dict, List

from src import config


# Existing analytics_query from analytics_performance_tools.py
def analytics_query(query_type: str, agent_name: str = None, limit: int = 10) -> Dict[str, Any]:
    # ... (existing code for summary, top_agents, agent_stats, roll_distribution)
    pass  # Copy from previous


# NEW: Swarm performance analytics based on examples
def swarm_performance_analytics(metric: str = "overview", example_filter: str = None) -> Dict[str, Any]:
    """
    Analyze swarm performance from grokputer_swarm_examples.md

    Args:
        metric: Type of analysis ('overview', 'execution_times', 'success_rates', 'message_counts', 'agent_efficiency')
        example_filter: Filter by example type (e.g., 'notepad', 'crypto', 'png')

    Returns:
        Dict with analysis results
    """
    examples_file = Path("../docs/grokputer_swarm_examples.md")
    if not examples_file.exists():
        return {"status": "error", "error": "Swarm examples file not found"}

    with open(examples_file, "r", encoding="utf-8") as f:
        content = f.read()

    # Parse examples from the file
    examples = parse_swarm_examples(content)

    # Filter if requested
    if example_filter:
        examples = [ex for ex in examples if example_filter.lower() in ex.get("task", "").lower()]

    if not examples:
        return {"status": "error", "error": f"No examples found matching filter: {example_filter}"}

    try:
        if metric == "overview":
            return analyze_swarm_overview(examples)
        elif metric == "execution_times":
            return analyze_execution_times(examples)
        elif metric == "success_rates":
            return analyze_success_rates(examples)
        elif metric == "message_counts":
            return analyze_message_counts(examples)
        elif metric == "agent_efficiency":
            return analyze_agent_efficiency(examples)
        else:
            return {"status": "error", "error": f"Unknown metric: {metric}"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def parse_swarm_examples(content: str) -> List[Dict[str, Any]]:
    """Parse swarm examples from the markdown content."""
    examples = []

    # Split by major sections (using > as separators for different examples)
    sections = re.split(r"\n\s*> ", content)

    for section in sections:
        if not section.strip():
            continue

        example = {}

        # Extract task description
        task_match = re.search(r"Command Simulated: (.+?)\n", section, re.IGNORECASE)
        if task_match:
            example["task"] = task_match.group(1).strip()

        # Extract execution time
        time_match = re.search(r"Completed in (\d+\.?\d*)s", section)
        if time_match:
            example["execution_time"] = float(time_match.group(1))

        # Extract message count
        msg_match = re.search(r"Messages sent: (\d+)", section)
        if msg_match:
            example["message_count"] = int(msg_match.group(1))

        # Extract success status
        if "Success: True" in section:
            example["success"] = True
        elif "Success: False" in section or "error" in section.lower():
            example["success"] = False
        else:
            example["success"] = True  # Default to success if not specified

        # Extract agent count
        agent_match = re.search(r"Agents?: (\d+)", section, re.IGNORECASE)
        if agent_match:
            example["agent_count"] = int(agent_match.group(1))

        # Extract swarm type/context
        if "png" in section.lower() or "meme" in section.lower():
            example["type"] = "file_analysis"
        elif "crypto" in section.lower() or "btc" in section.lower():
            example["type"] = "market_analysis"
        elif "notepad" in section.lower() or "window" in section.lower():
            example["type"] = "ui_automation"
        else:
            example["type"] = "general"

        if any(key in example for key in ["execution_time", "message_count", "success"]):
            examples.append(example)

    return examples


def analyze_swarm_overview(examples: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Provide overview of all swarm examples."""
    total_examples = len(examples)
    successful = sum(1 for ex in examples if ex.get("success", False))
    avg_time = sum(ex.get("execution_time", 0) for ex in examples) / total_examples if total_examples > 0 else 0
    avg_messages = sum(ex.get("message_count", 0) for ex in examples) / total_examples if total_examples > 0 else 0

    type_counts = {}
    for ex in examples:
        typ = ex.get("type", "unknown")
        type_counts[typ] = type_counts.get(typ, 0) + 1

    return {
        "status": "success",
        "metric": "overview",
        "data": {
            "total_examples": total_examples,
            "success_rate": successful / total_examples if total_examples > 0 else 0,
            "avg_execution_time": round(avg_time, 2),
            "avg_message_count": round(avg_messages, 2),
            "examples_by_type": type_counts,
            "fastest_example": min(examples, key=lambda x: x.get("execution_time", float("inf"))),
            "slowest_example": max(examples, key=lambda x: x.get("execution_time", float("inf"))),
        },
    }


def analyze_execution_times(examples: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze execution time patterns."""
    times = [ex.get("execution_time", 0) for ex in examples if "execution_time" in ex]
    if not times:
        return {"status": "error", "error": "No execution time data available"}

    avg_time = sum(times) / len(times)
    min_time = min(times)
    max_time = max(times)

    # Group by type
    type_times = {}
    for ex in examples:
        if "execution_time" in ex:
            typ = ex.get("type", "unknown")
            if typ not in type_times:
                type_times[typ] = []
            type_times[typ].append(ex["execution_time"])

    type_avgs = {typ: round(sum(times) / len(times), 2) for typ, times in type_times.items()}

    return {
        "status": "success",
        "metric": "execution_times",
        "data": {
            "avg_time": round(avg_time, 2),
            "min_time": min_time,
            "max_time": max_time,
            "time_distribution": {
                "< 5s": len([t for t in times if t < 5]),
                "5-10s": len([t for t in times if 5 <= t < 10]),
                "10-20s": len([t for t in times if 10 <= t < 20]),
                "> 20s": len([t for t in times if t >= 20]),
            },
            "avg_by_type": type_avgs,
        },
    }


def analyze_success_rates(examples: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze success rates by type and overall."""
    total = len(examples)
    successful = sum(1 for ex in examples if ex.get("success", False))

    # By type
    type_success = {}
    for ex in examples:
        typ = ex.get("type", "unknown")
        if typ not in type_success:
            type_success[typ] = {"total": 0, "success": 0}
        type_success[typ]["total"] += 1
        if ex.get("success", False):
            type_success[typ]["success"] += 1

    type_rates = {
        typ: round(stats["success"] / stats["total"], 2) if stats["total"] > 0 else 0
        for typ, stats in type_success.items()
    }

    return {
        "status": "success",
        "metric": "success_rates",
        "data": {
            "overall_success_rate": round(successful / total, 2) if total > 0 else 0,
            "success_by_type": type_rates,
            "failed_examples": [ex for ex in examples if not ex.get("success", True)],
        },
    }


def analyze_message_counts(examples: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze message passing efficiency."""
    counts = [ex.get("message_count", 0) for ex in examples if "message_count" in ex]
    if not counts:
        return {"status": "error", "error": "No message count data available"}

    avg_count = sum(counts) / len(counts)
    min_count = min(counts)
    max_count = max(counts)

    # Correlation with execution time
    time_msg_pairs = [
        (ex.get("execution_time", 0), ex.get("message_count", 0))
        for ex in examples
        if "execution_time" in ex and "message_count" in ex
    ]

    return {
        "status": "success",
        "metric": "message_counts",
        "data": {
            "avg_message_count": round(avg_count, 1),
            "min_messages": min_count,
            "max_messages": max_count,
            "message_distribution": {
                "1-5": len([c for c in counts if c <= 5]),
                "6-10": len([c for c in counts if 6 <= c <= 10]),
                "11-20": len([c for c in counts if 11 <= c <= 20]),
                ">20": len([c for c in counts if c > 20]),
            },
            "efficiency_ratio": round(avg_count / avg_time, 2) if avg_time > 0 else 0,
        },
    }


def analyze_agent_efficiency(examples: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze agent efficiency metrics."""
    agent_counts = [ex.get("agent_count", 0) for ex in examples if "agent_count" in ex]
    if not agent_counts:
        return {"status": "error", "error": "No agent count data available"}

    avg_agents = sum(agent_counts) / len(agent_counts)

    # Efficiency: time per agent
    efficiency_data = []
    for ex in examples:
        if "execution_time" in ex and "agent_count" in ex:
            time_per_agent = ex["execution_time"] / ex["agent_count"]
            efficiency_data.append(
                {
                    "task": ex.get("task", "unknown"),
                    "agents": ex["agent_count"],
                    "total_time": ex["execution_time"],
                    "time_per_agent": round(time_per_agent, 2),
                    "success": ex.get("success", False),
                }
            )

    return {
        "status": "success",
        "metric": "agent_efficiency",
        "data": {
            "avg_agents_per_swarm": round(avg_agents, 1),
            "efficiency_examples": efficiency_data[:10],  # Top 10
            "most_efficient": min(efficiency_data, key=lambda x: x["time_per_agent"]) if efficiency_data else None,
            "least_efficient": max(efficiency_data, key=lambda x: x["time_per_agent"]) if efficiency_data else None,
        },
    }


# Update analytics_query to include swarm metrics
def enhanced_analytics_query(query_type: str, agent_name: str = None, limit: int = 10) -> Dict[str, Any]:
    """Enhanced analytics including swarm performance."""
    if query_type.startswith("swarm_"):
        # Swarm-specific analytics
        swarm_metric = query_type.replace("swarm_", "")
        return swarm_performance_analytics(swarm_metric)
    else:
        # Original roll analytics
        return analytics_query(query_type, agent_name, limit)
