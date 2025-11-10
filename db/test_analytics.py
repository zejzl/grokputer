#!/usr/bin/env python3
"""
Simple test script for analytics tools.
"""

import sys
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.tools import analytics_query_tool, performance_monitor_tool

async def test_analytics():
    print("Testing Analytics Tools...\n")

    # Test summary
    print("=== SUMMARY ===")
    result = await analytics_query_tool({'query_type': 'summary'})
    if result['status'] == 'success':
        data = result['data']
        print(f"Total Rolls: {data['total_rolls']}")
        print(f"Agents: {data['agents']}")
        print(f"Avg Total: {data['avg_total']:.2f}")
        print(f"Max Total: {data['max_total']}")
    else:
        print(f"Error: {result.get('error', 'Unknown')}")

    print("\n=== TOP AGENTS ===")
    result = await analytics_query_tool({'query_type': 'top_agents', 'limit': 3})
    if result['status'] == 'success':
        for item in result['data']:
            print(f"{item['agent']}: {item['rolls']} rolls, avg {item['avg_total']:.2f}")
    else:
        print(f"Error: {result.get('error', 'Unknown')}")

    print("\n=== PERFORMANCE ===")
    result = await performance_monitor_tool({'mode': 'snapshot'})
    if result['status'] == 'success':
        data = result['data']
        print(f"Uptime: {data['uptime_seconds']:.1f}s")
        print(f"CPU: {data['system']['cpu_percent']:.1f}%")
        print(f"Memory: {data['system']['memory_percent']:.1f}% used")
        print(f"API Calls: {data['api']['total_calls']}")
    else:
        print(f"Error: {result.get('error', 'Unknown')}")

    print("\nTest complete!")

if __name__ == "__main__":
    asyncio.run(test_analytics())