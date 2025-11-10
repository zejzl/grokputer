# Fixed version with proper content parsing

import re
from pathlib import Path
from typing import Dict, Any, List

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

    # Find the start of actual content (skip any embedded data)
    start_idx = content.find('Command Simulated')
    if start_idx == -1:
        return examples
    content = content[start_idx:]

    # Split by sections based on "Command Simulated" patterns
    sections = re.split(r'(?=Command Simulated)', content)

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
            example['success'] = True  # Default to success

        # Extract agent count
        agent_match = re.search(r'Agents?: (\d+)', section, re.IGNORECASE)
        if agent_match:
            example['agent_count'] = int(agent_match.group(1))

        # Categorize by type
        if 'png' in section.lower() or 'meme' in section.lower():
            example['type'] = 'file_analysis'
        elif 'crypto' in section.lower() or 'btc' in section.lower():
            example['type'] = 'market_analysis'
        elif 'notepad' in section.lower() or 'window' in section.lower() or 'click' in section.lower():
            example['type'] = 'ui_automation'
        else:
            example['type'] = 'general'

        if example.get('task'):  # Only add if we found a task
            examples.append(example)

    return examples

# Include the analysis functions (same as before)
def analyze_swarm_overview(examples: List[Dict[str, Any]]) -> Dict[str, Any]:
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
        }
    }

def analyze_execution_times(examples: List[Dict[str, Any]]) -> Dict[str, Any]:
    times = [ex.get('execution_time', 0) for ex in examples if 'execution_time' in ex]
    if not times:
        return {"status": "error", "error": "No execution time data available"}

    avg_time = sum(times) / len(times)
    return {
        "status": "success",
        "metric": "execution_times",
        "data": {
            "avg_time": round(avg_time, 2),
            "min_time": min(times),
            "max_time": max(times),
        }
    }

def analyze_success_rates(examples: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(examples)
    successful = sum(1 for ex in examples if ex.get('success', False))
    return {
        "status": "success",
        "metric": "success_rates",
        "data": {
            "overall_success_rate": round(successful / total, 2) if total > 0 else 0,
        }
    }

def analyze_message_counts(examples: List[Dict[str, Any]]) -> Dict[str, Any]:
    counts = [ex.get('message_count', 0) for ex in examples if 'message_count' in ex]
    if not counts:
        return {"status": "error", "error": "No message count data available"}

    avg_count = sum(counts) / len(counts)
    return {
        "status": "success",
        "metric": "message_counts",
        "data": {
            "avg_message_count": round(avg_count, 1),
        }
    }

def analyze_agent_efficiency(examples: List[Dict[str, Any]]) -> Dict[str, Any]:
    agent_counts = [ex.get('agent_count', 0) for ex in examples if 'agent_count' in ex]
    if not agent_counts:
        return {"status": "error", "error": "No agent count data available"}

    avg_agents = sum(agent_counts) / len(agent_counts)
    return {
        "status": "success",
        "metric": "agent_efficiency",
        "data": {
            "avg_agents_per_swarm": round(avg_agents, 1),
        }
    }