# Enhancement to analytics tools based on grokputer_swarm_examples.md
# Adds swarm performance analytics: execution times, success rates, message counts, agent efficiency

import re
from pathlib import Path
from typing import Dict, Any, List
import sqlite3
from src import config

# Existing analytics_query from analytics_performance_tools.py
def analytics_query(query_type: str, agent_name: str = None, limit: int = 10) -> Dict[str, Any]:
    # ... (existing code for summary, top_agents, agent_stats, roll_distribution)
    pass  # Copy from previous

# NEW: Swarm performance analytics based on examples
def swarm_performance_analytics(metric: str = 'overview', example_filter: str = None) -> Dict[str, Any]:
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

    with open(examples_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Parse examples from the file
    examples = parse_swarm_examples(content)

    # Filter if requested
    if example_filter:
        examples = [ex for ex in examples if example_filter.lower() in ex.get('task', '').lower()]

    if not examples:
        return {"status": "error", "error": f"No examples found matching filter: {example_filter}"}

    try:
        if metric == 'overview':
            return analyze_swarm_overview(examples)
        elif metric == 'execution_times':
            return analyze_execution_times(examples)
        elif metric == 'success_rates':
            return analyze_success_rates(examples)
        elif metric == 'message_counts':
            return analyze_message_counts(examples)
        elif metric == 'agent_efficiency':
            return analyze_agent_efficiency(examples)
        else:
            return {"status": "error", "error": f"Unknown metric: {metric}"}
    except Exception as e:
        return {"status": "error", "error": str(e)}

def parse_swarm_examples(content: str) -> List[Dict[str, Any]]:
    """Parse swarm examples from the markdown content."""
    examples = []

    # Split by major sections (using > as separators for different examples)
    sections = re.split(r'\n\s*> ', content)

    for section in sections:
        if not section.strip():
            continue

        example = {}

        # Extract task description
        task_match = re.search(r'Command Simulated: (.+?)\n', section, re.IGNORECASE)
        if task_match:
            example['task'] = task_match.group(1).strip()

        # Extract execution time
        time_match = re.search(r'Completed in (\d+\.?\d*)s', section)
        if time_match:
            example['execution_time'] = float(time_match.group(1))

        # Extract message count
        msg_match = re.search(r'Messages sent: (\d+)', section)
        if msg_match:
            example['message_count'] = int(msg_match.group(1))

        # Extract success status
        if 'Success: True' in section:
            example['success'] = True
        elif 'Success: False' in section or 'error' in section.lower():
            example['success'] = False
        else:
            example['success'] = True  # Default to success if not specified

        # Extract agent count
        agent_match = re.search(r'Agents?: (\d+)', section, re.IGNORECASE)
        if agent_match:
            example['agent_count'] = int(agent_match.group(1))

        # Extract swarm type/context
        if 'png' in section.lower() or 'meme' in section.lower():
            example['type'] = 'file_analysis'
        elif 'crypto' in section.lower() or 'btc' in section.lower():
            example['type'] = 'market_analysis'
        elif 'notepad' in section.lower() or 'window' in section.lower():
            example['type'] = 'ui_automation'
        else:
            example['type'] = 'general'

        if any(key in example for key in ['execution_time', 'message_count', 'success']):
            examples.append(example)

    return examples

def analyze_swarm_overview(examples: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Provide overview of all swarm examples."""
    total_examples = len(examples)
    successful = sum(1 for ex in examples if ex.get('success', False))
    avg_time = sum(ex.get('execution_time', 0) for ex in examples) / total_examples if total_examples > 0 else 0
    avg_messages = sum(ex.get('message_count', 0) for ex in examples) / total_examples if total_examples > 0 else 0

    type_counts = {}
    for ex in examples:
        typ = ex.get('type', 'unknown')
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
            "fastest_example": min(examples, key=lambda x: x.get('execution_time', float('inf'))),
            "slowest_example": max(examples, key=lambda x: x.get('execution_time', float('inf')))
        }
    }

def analyze_execution_times(examples: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze execution time patterns."""
    times = [ex.get('execution_time', 0) for ex in examples if 'execution_time' in ex]
    if not times:
        return {"status": "error", "error": "No execution time data available"}

    avg_time = sum(times) / len(times)
    min_time = min(times)
    max_time = max(times)

    # Group by type
    type_times = {}
    for ex in examples:
        if 'execution_time' in ex:
            typ = ex.get('type', 'unknown')
            if typ not in type_times:
                type_times[typ] = []
            type_times[typ].append(ex['execution_time'])

    type_avgs = {typ: round(sum(times)/len(times), 2) for typ, times in type_times.items()}

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
                "> 20s": len([t for t in times if t >= 20])
            },
            "avg_by_type": type_avgs
        }
    }

def analyze_success_rates(examples: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze success rates by type and overall."""
    total = len(examples)
    successful = sum(1 for ex in examples if ex.get('success', False))

    # By type
    type_success = {}
    for ex in examples:
        typ = ex.get('type', 'unknown')
        if typ not in type_success:
            type_success[typ] = {'total': 0, 'success': 0}
        type_success[typ]['total'] += 1
        if ex.get('success', False):
            type_success[typ]['success'] += 1

    type_rates = {typ: round(stats['success'] / stats['total'], 2) if stats['total'] > 0 else 0
                  for typ, stats in type_success.items()}

    return {
        "status": "success",
        "metric": "success_rates",
        "data": {
            "overall_success_rate": round(successful / total, 2) if total > 0 else 0,
            "success_by_type": type_rates,
            "failed_examples": [ex for ex in examples if not ex.get('success', True)]
        }
    }

def analyze_message_counts(examples: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze message passing efficiency."""
    counts = [ex.get('message_count', 0) for ex in examples if 'message_count' in ex]
    if not counts:
        return {"status": "error", "error": "No message count data available"}

    avg_count = sum(counts) / len(counts)
    min_count = min(counts)
    max_count = max(counts)

    # Correlation with execution time
    time_msg_pairs = [(ex.get('execution_time', 0), ex.get('message_count', 0))
                      for ex in examples if 'execution_time' in ex and 'message_count' in ex]

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
                ">20": len([c for c in counts if c > 20])
            },
            "efficiency_ratio": round(avg_count / avg_time, 2) if avg_time > 0 else 0
        }
    }

def analyze_agent_efficiency(examples: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze agent efficiency metrics."""
    agent_counts = [ex.get('agent_count', 0) for ex in examples if 'agent_count' in ex]
    if not agent_counts:
        return {"status": "error", "error": "No agent count data available"}

    avg_agents = sum(agent_counts) / len(agent_counts)

    # Efficiency: time per agent
    efficiency_data = []
    for ex in examples:
        if 'execution_time' in ex and 'agent_count' in ex:
            time_per_agent = ex['execution_time'] / ex['agent_count']
            efficiency_data.append({
                'task': ex.get('task', 'unknown'),
                'agents': ex['agent_count'],
                'total_time': ex['execution_time'],
                'time_per_agent': round(time_per_agent, 2),
                'success': ex.get('success', False)
            })

    return {
        "status": "success",
        "metric": "agent_efficiency",
        "data": {
            "avg_agents_per_swarm": round(avg_agents, 1),
            "efficiency_examples": efficiency_data[:10],  # Top 10
            "most_efficient": min(efficiency_data, key=lambda x: x['time_per_agent']) if efficiency_data else None,
            "least_efficient": max(efficiency_data, key=lambda x: x['time_per_agent']) if efficiency_data else None
        }
    }

# Update analytics_query to include swarm metrics
def enhanced_analytics_query(query_type: str, agent_name: str = None, limit: int = 10) -> Dict[str, Any]:
    """Enhanced analytics including swarm performance."""
    if query_type.startswith('swarm_'):
        # Swarm-specific analytics
        swarm_metric = query_type.replace('swarm_', '')
        return swarm_performance_analytics(swarm_metric)
    else:
        # Original roll analytics
        return analytics_query(query_type, agent_name, limit)