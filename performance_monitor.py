#!/usr/bin/env python3
"""
MessageBus Performance Monitor

Monitors MessageBus performance metrics and provides optimization recommendations.
Run this script to get real-time performance insights.
"""

import asyncio
import time
from pathlib import Path
from src.core.message_bus import MessageBus

async def monitor_performance(duration_seconds: int = 60):
    """Monitor MessageBus performance for specified duration."""
    bus = MessageBus()

    print(">>> MessageBus Performance Monitor")
    print(f"Monitoring for {duration_seconds} seconds...")
    print("-" * 50)

    start_time = time.time()
    snapshots = []

    while time.time() - start_time < duration_seconds:
        snapshot = bus.get_performance_snapshot()
        snapshots.append(snapshot)

        # Print current stats
        print(f"\r[*] Throughput: {snapshot['overall_throughput']:.1f} msg/sec | "
              f"Active: {snapshot['concurrency_active']:.0f} | "
              f"Queues: {snapshot['total_queues']} | "
              f"Latency: {snapshot['avg_latency_ms']:.2f}ms", end="", flush=True)

        await asyncio.sleep(5)  # Update every 5 seconds

    print("\n" + "-" * 50)

    # Final analysis
    if snapshots:
        final = snapshots[-1]
        avg_throughput = sum(s['overall_throughput'] for s in snapshots) / len(snapshots)

        print("[+] Final Performance Report:")
        print(f"  - Average Throughput: {avg_throughput:.1f} msg/sec")
        print(f"  - Peak Throughput: {max(s['overall_throughput'] for s in snapshots):.1f} msg/sec")
        print(f"  - Current Active Connections: {final['concurrency_active']:.0f}")
        print(f"  - Queue Health: {sum(1 for q in final['queue_health'].values() if not q['is_full'])}/{len(final['queue_health'])} healthy")
        print(f"  - Average Latency: {final['avg_latency_ms']:.2f}ms")

        # Run optimization check
        print("\n[+] Optimization Analysis:")
        optimization_result = bus.optimize_performance()
        if optimization_result["optimizations_performed"]:
            for opt_name, opt_data in optimization_result["optimizations_performed"].items():
                print(f"  - {opt_name}: {opt_data}")
        else:
            print("  [+] No optimizations needed - system performing well!")

    print("\n[+] Monitoring complete!")

if __name__ == "__main__":
    # Run for 30 seconds by default
    asyncio.run(monitor_performance(30))