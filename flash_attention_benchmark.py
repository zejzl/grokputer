#!/usr/bin/env python3
"""
Flash Attention Performance Benchmark
Compares performance with different num_heads configurations.
"""

import time
import numpy as np
from src.cognitive.flash_attention import CognitiveEnhancer

def benchmark_attention(embed_dim=128, num_heads_list=[8, 16], memory_slots=50, num_runs=10):
    """Benchmark attention performance with different configurations."""

    # Sample data
    current_input = "Analyze this complex problem and provide insights."
    context_history = [
        {"content": "Previous analysis showed interesting patterns", "timestamp": time.time()},
        {"content": "Further investigation revealed key relationships", "timestamp": time.time()},
        {"content": "The solution involves multiple interconnected factors", "timestamp": time.time()},
    ]

    results = {}

    for num_heads in num_heads_list:
        print(f"\nBenchmarking num_heads={num_heads}...")

        try:
            enhancer = CognitiveEnhancer(embed_dim=embed_dim, num_heads=num_heads, memory_slots=memory_slots)

            times = []
            for i in range(num_runs):
                start_time = time.time()
                result = enhancer.process_context(current_input, context_history)
                end_time = time.time()
                times.append(end_time - start_time)

            avg_time = np.mean(times)
            std_time = np.std(times)
            min_time = np.min(times)
            max_time = np.max(times)

            results[num_heads] = {
                'avg_time': avg_time,
                'std_time': std_time,
                'min_time': min_time,
                'max_time': max_time,
                'runs': num_runs
            }

            print(".4f")
            print(".4f")
            print(".4f")
            print(".4f")

        except Exception as e:
            print(f"Error with num_heads={num_heads}: {e}")
            results[num_heads] = {'error': str(e)}

    return results

def compare_performance(results):
    """Compare performance between configurations."""
    if len(results) < 2:
        return "Need at least 2 configurations to compare"

    configs = list(results.keys())
    baseline = configs[0]

    if 'error' in results[baseline]:
        return f"Baseline config {baseline} failed: {results[baseline]['error']}"

    baseline_time = results[baseline]['avg_time']

    comparison = f"\nPerformance Comparison (vs num_heads={baseline}):\n"
    comparison += "=" * 50 + "\n"

    for config in configs[1:]:
        if 'error' in results[config]:
            comparison += f"num_heads={config}: FAILED - {results[config]['error']}\n"
        else:
            config_time = results[config]['avg_time']
            speedup = baseline_time / config_time
            change = ((config_time - baseline_time) / baseline_time) * 100

            comparison += f"num_heads={config}: "
            if speedup > 1:
                comparison += ".2f"
            else:
                comparison += ".2f"
            comparison += ".1f"
            comparison += "\n"

    return comparison

if __name__ == "__main__":
    print("Flash Attention Performance Benchmark")
    print("=" * 50)

    # Run benchmark
    results = benchmark_attention()

    # Compare results
    comparison = compare_performance(results)
    print(comparison)

    # Summary
    print("\nSummary:")
    print("- num_heads=8: Baseline configuration")
    print("- num_heads=16: Tuned configuration for Pantheon")
    print("- Higher num_heads can provide better parallelization")
    print("- Performance may vary based on hardware and input size")