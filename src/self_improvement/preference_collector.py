"""
Preference Data Collector for DPO Training

Collects preference pairs by comparing agent performance with different parameter settings.
Automatically generates training data for DPO optimization.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import random
import time
from concurrent.futures import ThreadPoolExecutor

from src.self_improvement.dpo_optimizer import PreferencePair, AgentDPO
from src.grok_client import GrokClient

logger = logging.getLogger(__name__)


@dataclass
class ParameterTrial:
    """Result of running an agent with specific parameters."""

    params: Dict[str, Any]
    metrics: Dict[str, float]
    execution_time: float
    success: bool
    error_message: Optional[str] = None


class PreferenceCollector:
    """
    Collects preference data by running agents with different parameter settings
    and comparing their performance on sample tasks.
    """

    def __init__(self, dpo_optimizer: AgentDPO, grok_client: Optional[GrokClient] = None):
        """
        Initialize preference collector.

        Args:
            dpo_optimizer: DPO optimizer to train
            grok_client: Grok client for running tasks (optional)
        """
        self.dpo = dpo_optimizer
        self.grok_client = grok_client or GrokClient()
        self.collected_pairs: List[PreferencePair] = []

        # Sample tasks for preference collection
        self.sample_tasks = [
            "Count the number of files in the current directory",
            "List all Python files in the project",
            "Check if a file named 'README.md' exists",
            "Get the current working directory path",
            "List all directories in the current path",
        ]

        logger.info("Preference collector initialized")

    async def run_parameter_trial(self, task: str, params: Dict[str, Any]) -> ParameterTrial:
        """
        Run a single task with specific parameters and measure performance.

        Args:
            task: Task description
            params: Parameter settings to test

        Returns:
            Trial results
        """
        start_time = time.time()

        try:
            # Apply parameters to grok client
            original_params = {}
            for param_name, param_value in params.items():
                if hasattr(self.grok_client, param_name):
                    original_params[param_name] = getattr(self.grok_client, param_name)
                    setattr(self.grok_client, param_name, param_value)

            # Run the task
            response = await self.grok_client.create_message(task)

            # Calculate metrics
            execution_time = time.time() - start_time

            # Simple success metric based on response length and time
            success = len(response.get("content", "")) > 10 and execution_time < 30
            quality_score = min(len(response.get("content", "")) / 1000, 1.0)  # Normalize
            speed_score = max(0, 1 - execution_time / 30)  # Faster is better

            metrics = {"quality": quality_score, "speed": speed_score, "combined": (quality_score + speed_score) / 2}

            # Restore original parameters
            for param_name, original_value in original_params.items():
                setattr(self.grok_client, param_name, original_value)

            return ParameterTrial(params=params, metrics=metrics, execution_time=execution_time, success=success)

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Trial failed: {e}")

            return ParameterTrial(
                params=params,
                metrics={"quality": 0.0, "speed": 0.0, "combined": 0.0},
                execution_time=execution_time,
                success=False,
                error_message=str(e),
            )

    async def compare_parameter_sets(
        self, task: str, params_a: Dict[str, Any], params_b: Dict[str, Any]
    ) -> Optional[PreferencePair]:
        """
        Compare two parameter sets on a task and create preference pair if clear winner.

        Args:
            task: Task to test
            params_a: First parameter set
            params_b: Second parameter set

        Returns:
            Preference pair if one clearly outperforms the other
        """
        trial_a = await self.run_parameter_trial(task, params_a)
        trial_b = await self.run_parameter_trial(task, params_b)

        # Determine winner based on combined metric
        score_a = trial_a.metrics["combined"]
        score_b = trial_b.metrics["combined"]

        # Only create preference if significant difference (>10% relative)
        margin = abs(score_a - score_b) / max(score_a, score_b, 0.01)

        if margin > 0.1:  # 10% difference threshold
            if score_a > score_b:
                chosen, rejected = params_a, params_b
                winner_metrics = trial_a.metrics
            else:
                chosen, rejected = params_b, params_a
                winner_metrics = trial_b.metrics

            pair = PreferencePair(
                task_description=task, chosen_params=chosen, rejected_params=rejected, task_metrics=winner_metrics
            )

            logger.info(f"Created preference pair: {task[:30]}... Winner score: {max(score_a, score_b):.3f}")
            return pair

        return None

    async def collect_preferences_batch(self, num_pairs: int = 10) -> int:
        """
        Collect a batch of preference pairs by testing parameter combinations.

        Args:
            num_pairs: Number of pairs to collect

        Returns:
            Number of pairs successfully collected
        """
        collected = 0

        for _ in range(num_pairs):
            # Select random task
            task = random.choice(self.sample_tasks)

            # Generate two random parameter sets
            params_a = self._generate_random_params()
            params_b = self._generate_random_params()

            # Ensure they're different
            while params_a == params_b:
                params_b = self._generate_random_params()

            # Compare them
            pair = await self.compare_parameter_sets(task, params_a, params_b)

            if pair:
                self.dpo.add_preference_pair(pair)
                self.collected_pairs.append(pair)
                collected += 1

                # Train on new data
                if len(self.dpo.preference_pairs) >= 5:
                    loss = self.dpo.train_step(batch_size=min(5, len(self.dpo.preference_pairs)))
                    logger.info(f"Training loss after new pair: {loss:.4f}")

        logger.info(f"Collected {collected} preference pairs in batch")
        return collected

    def _generate_random_params(self) -> Dict[str, Any]:
        """Generate random parameter settings within defined ranges."""
        params = {}
        for param_name, (min_val, max_val) in self.dpo.param_space.items():
            if isinstance(min_val, int) and isinstance(max_val, int):
                params[param_name] = random.randint(min_val, max_val)
            else:
                params[param_name] = random.uniform(min_val, max_val)
        return params

    async def optimize_collection_strategy(self) -> Dict[str, Any]:
        """
        Use current DPO model to suggest best parameters for data collection.

        Returns:
            Suggested parameters for efficient preference collection
        """
        # Use DPO to find parameters that typically perform well
        return self.dpo.optimize_parameters("Preference data collection optimization", {"quality": 0.8, "speed": 0.7})

    def collect_human_feedback(
        self,
        task_description: str,
        params_used: Dict[str, Any],
        human_rating: float,
        task_context: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Collect human feedback on agent performance for DPO training.

        Args:
            task_description: Description of the task performed
            params_used: Parameters used during task execution
            human_rating: Human rating (0.0 to 1.0, where 1.0 is best)
            task_context: Additional context about the task execution

        Returns:
            True if feedback was collected successfully
        """
        try:
            # Create a synthetic "rejected" parameter set for preference learning
            # This represents what the agent might have done worse
            rejected_params = self._generate_similar_params(params_used, human_rating)

            # Create preference pair where current params are chosen if rating is good
            if human_rating >= 0.7:  # Good performance
                chosen_params = params_used
                rejected_params = rejected_params
            else:  # Poor performance
                # If rating is poor, the rejected params become the "chosen" ones
                chosen_params = rejected_params
                rejected_params = params_used

            # Create preference pair
            pair = PreferencePair(
                task_description=task_description,
                chosen_params=chosen_params,
                rejected_params=rejected_params,
                task_metrics={
                    "human_rating": human_rating,
                    "quality": human_rating,
                    "speed": 0.5,  # Unknown speed for human feedback
                    "combined": human_rating,
                },
            )

            # Add to DPO training data
            self.dpo.add_preference_pair(pair)
            self.collected_pairs.append(pair)

            # Train on new data if we have enough
            if len(self.dpo.preference_pairs) >= 3:
                loss = self.dpo.train_step(batch_size=min(3, len(self.dpo.preference_pairs)))
                logger.info(f"DPO training loss after human feedback: {loss:.4f}")

            logger.info(f"Collected human feedback: rating={human_rating:.2f} for task: {task_description[:50]}...")
            return True

        except Exception as e:
            logger.error(f"Failed to collect human feedback: {e}")
            return False

    def _generate_similar_params(self, base_params: Dict[str, Any], performance_rating: float) -> Dict[str, Any]:
        """
        Generate similar parameter set that would likely perform differently.

        Args:
            base_params: Base parameter set
            performance_rating: How well the base params performed (0-1)

        Returns:
            Alternative parameter set
        """
        similar_params = {}

        for param_name, base_value in base_params.items():
            param_range = self.dpo.param_space.get(param_name, (base_value * 0.5, base_value * 1.5))

            if performance_rating > 0.7:
                # If performance was good, try more extreme values
                if random.choice([True, False]):
                    # Try higher value
                    similar_params[param_name] = min(param_range[1], base_value * 1.2)
                else:
                    # Try lower value
                    similar_params[param_name] = max(param_range[0], base_value * 0.8)
            else:
                # If performance was poor, try moderate adjustments
                adjustment = random.uniform(0.9, 1.1)
                similar_params[param_name] = max(param_range[0], min(param_range[1], base_value * adjustment))

        return similar_params

    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about collected preference data."""
        if not self.collected_pairs:
            return {"total_pairs": 0}

        avg_metrics = {}
        human_feedback_count = 0

        for pair in self.collected_pairs:
            for key, value in pair.task_metrics.items():
                if key not in avg_metrics:
                    avg_metrics[key] = []
                avg_metrics[key].append(value)

            if "human_rating" in pair.task_metrics:
                human_feedback_count += 1

        stats = {
            "total_pairs": len(self.collected_pairs),
            "human_feedback_pairs": human_feedback_count,
            "avg_metrics": {k: sum(v) / len(v) for k, v in avg_metrics.items()},
            "task_distribution": {},
        }

        # Task distribution
        for pair in self.collected_pairs:
            task_type = pair.task_description.split()[0].lower()
            stats["task_distribution"][task_type] = stats["task_distribution"].get(task_type, 0) + 1

        return stats


# Example usage
async def main():
    # Define parameter space
    param_space = {"temperature": (0.1, 1.0), "max_tokens": (50, 500), "timeout": (5, 30)}

    dpo = AgentDPO(param_space)
    collector = PreferenceCollector(dpo)

    # Collect some preference data
    print("Collecting preference data...")
    collected = await collector.collect_preferences_batch(num_pairs=5)
    print(f"Collected {collected} pairs")

    # Show stats
    stats = collector.get_collection_stats()
    print(f"Collection stats: {stats}")

    # Get optimized parameters
    optimal = collector.optimize_collection_strategy()
    print(f"Suggested optimal params: {optimal}")


if __name__ == "__main__":
    asyncio.run(main())
