"""
DPO Evaluation Script

Compare DPO vs baseline parameter optimization effectiveness.
"""

import asyncio
import time

from src.grok_client import GrokClient
from src.self_improvement.dpo_optimizer import AgentDPO, PreferencePair
from src.self_improvement.preference_collector import PreferenceCollector


async def evaluate_dpo():
    """Evaluate DPO optimization performance."""

    # Initialize components
    param_space = {"temperature": (0.1, 1.0), "max_tokens": (50, 500), "timeout": (5, 30)}

    dpo = AgentDPO(param_space)
    collector = PreferenceCollector(dpo)

    print("=== DPO Evaluation ===")

    # Generate synthetic preference data
    print("Generating synthetic preference data...")
    for i in range(20):
        # Create preference pairs with known good/bad parameters
        good_params = {"temperature": 0.7, "max_tokens": 200, "timeout": 15}
        bad_params = {"temperature": 0.9, "max_tokens": 50, "timeout": 5}

        pair = PreferencePair(
            task_description=f"Synthetic task {i}",
            chosen_params=good_params,
            rejected_params=bad_params,
            task_metrics={"quality": 0.8, "speed": 0.7, "combined": 0.75},
        )
        dpo.add_preference_pair(pair)

    print(f"Added {len(dpo.preference_pairs)} preference pairs")

    # Train DPO
    print("Training DPO model...")
    for epoch in range(50):
        loss = dpo.train_step(batch_size=10)
        if epoch % 10 == 0:
            print(f"Epoch {epoch}: Loss = {loss:.4f}")

    # Test optimization
    print("\nTesting parameter optimization...")
    test_task = "Optimize parameters for file listing task"
    optimized = dpo.optimize_parameters(test_task, {"quality": 0.8, "speed": 0.6})

    print(f"Optimized parameters: {optimized}")

    # Evaluate against baseline (random)
    print("\nComparing with random baseline...")
    baseline_scores = []
    dpo_scores = []

    for _ in range(10):
        # Random parameters
        random_params = {k: collector._generate_random_params()[k] for k in param_space}
        random_score = dpo.get_preference_score(random_params)
        baseline_scores.append(random_score)

        # DPO parameters
        dpo_params = dpo.optimize_parameters("test", {"quality": 0.7, "speed": 0.7})
        dpo_score = dpo.get_preference_score(dpo_params)
        dpo_scores.append(dpo_score)

    avg_baseline = sum(baseline_scores) / len(baseline_scores)
    avg_dpo = sum(dpo_scores) / len(dpo_scores)
    improvement = ((avg_dpo - avg_baseline) / abs(avg_baseline)) * 100

    print(".3f")
    print(".3f")
    print(".1f")

    # Collection stats
    stats = collector.get_collection_stats()
    print(f"\nPreference collection stats: {stats}")

    print("\n=== Evaluation Complete ===")


if __name__ == "__main__":
    asyncio.run(evaluate_dpo())
