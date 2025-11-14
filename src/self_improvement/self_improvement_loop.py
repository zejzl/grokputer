"""
Self-Improvement Training Loop
============================

Continuous DPO training loop for agent evolution.
Collects preferences from successful runs and optimizes agent parameters.
"""

import asyncio
import logging
import time
from pathlib import Path
import json

from src.self_improvement.dpo_optimizer import AgentDPO
from src.self_improvement.preference_collector import PreferenceCollector
from src.grok_client import GrokClient

logger = logging.getLogger(__name__)

class SelfImprovementLoop:
    """
    Continuous self-improvement loop using DPO training.
    """

    def __init__(self, config_path: str = "config/self_improvement_config.json"):
        self.config_path = Path(config_path)
        self.config = self._load_config()

        # Initialize DPO
        self.dpo = AgentDPO(
            param_space=self.config["param_space"],
            learning_rate=self.config.get("learning_rate", 1e-3),
            beta=self.config.get("beta", 0.1)
        )

        # Initialize preference collector
        grok_client = GrokClient() if self.config.get("use_grok", False) else None
        self.collector = PreferenceCollector(self.dpo, grok_client)

        # Training stats
        self.training_stats = {
            "loops_completed": 0,
            "pairs_collected": 0,
            "avg_training_loss": 0.0,
            "last_optimization": None
        }

        logger.info("Self-improvement loop initialized")

    def _load_config(self) -> dict:
        """Load configuration from file."""
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                return json.load(f)
        else:
            # Default config
            return {
                "param_space": {
                    "temperature": [0.1, 1.0],
                    "max_tokens": [50, 500],
                    "timeout": [5, 30]
                },
                "learning_rate": 1e-3,
                "beta": 0.1,
                "use_grok": False,
                "training_interval": 3600,  # 1 hour
                "collection_batch_size": 10,
                "save_interval": 100  # Save model every 100 loops
            }

    def _save_config(self):
        """Save current config."""
        self.config_path.parent.mkdir(exist_ok=True)
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=2)

    def _save_model(self):
        """Save DPO model."""
        model_path = Path("models/dpo_model.pth")
        model_path.parent.mkdir(exist_ok=True)
        self.dpo.save_model(str(model_path))
        logger.info(f"Saved DPO model to {model_path}")

    def _load_model(self):
        """Load DPO model if exists."""
        model_path = Path("models/dpo_model.pth")
        if model_path.exists():
            self.dpo.load_model(str(model_path))
            logger.info(f"Loaded DPO model from {model_path}")

    async def run_training_loop(self, max_loops: int = 100):
        """
        Run the continuous training loop.

        Args:
            max_loops: Maximum number of training loops to run
        """
        logger.info("Starting self-improvement training loop")

        # Load existing model if available
        self._load_model()

        for loop_num in range(max_loops):
            logger.info(f"Starting training loop {loop_num + 1}/{max_loops}")

            try:
                # Collect preference data
                collected = await self.collector.collect_preferences_batch(
                    num_pairs=self.config["collection_batch_size"]
                )

                self.training_stats["pairs_collected"] += collected

                # Train DPO model
                if len(self.dpo.preference_pairs) >= 5:
                    loss = self.dpo.train_step(batch_size=min(32, len(self.dpo.preference_pairs)))
                    self.training_stats["avg_training_loss"] = (
                        (self.training_stats["avg_training_loss"] * self.training_stats["loops_completed"] + loss) /
                        (self.training_stats["loops_completed"] + 1)
                    )

                    logger.info(f"Loop {loop_num + 1}: collected {collected} pairs, training loss {loss:.4f}")

                # Optimize parameters for next collection
                if loop_num % 10 == 0:  # Every 10 loops
                    optimal_params = await self.collector.optimize_collection_strategy()
                    self.training_stats["last_optimization"] = optimal_params
                    logger.info(f"Optimized collection parameters: {optimal_params}")

                # Save model periodically
                if (loop_num + 1) % self.config["save_interval"] == 0:
                    self._save_model()

                self.training_stats["loops_completed"] += 1

                # Save stats
                self._save_stats()

                # Wait before next loop
                await asyncio.sleep(self.config["training_interval"])

            except Exception as e:
                logger.error(f"Error in training loop {loop_num + 1}: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error

        logger.info("Training loop completed")

    def _save_stats(self):
        """Save training statistics."""
        stats_path = Path("logs/self_improvement_stats.json")
        stats_path.parent.mkdir(exist_ok=True)
        with open(stats_path, 'w') as f:
            json.dump(self.training_stats, f, indent=2, default=str)

    def get_current_optimal_params(self, task_description: str) -> dict:
        """
        Get currently optimal parameters for a task.

        Args:
            task_description: Description of the task

        Returns:
            Optimal parameter settings
        """
        return self.dpo.optimize_parameters(task_description, {"quality": 0.8, "speed": 0.7})

    def add_human_feedback(self, task_description: str, params_used: dict, rating: float):
        """
        Add human feedback for DPO training.

        Args:
            task_description: Task that was performed
            params_used: Parameters used
            rating: Human rating (0.0 to 1.0)
        """
        success = self.collector.collect_human_feedback(task_description, params_used, rating)
        if success:
            logger.info(f"Added human feedback: rating {rating:.2f} for {task_description[:50]}...")
        else:
            logger.error("Failed to add human feedback")

async def main():
    """Main function for running self-improvement loop."""
    import argparse

    parser = argparse.ArgumentParser(description="Self-Improvement Training Loop")
    parser.add_argument("--loops", type=int, default=10, help="Number of training loops")
    parser.add_argument("--config", type=str, default="config/self_improvement_config.json", help="Config file path")
    parser.add_argument("--daemon", action="store_true", help="Run as daemon")

    args = parser.parse_args()

    loop = SelfImprovementLoop(args.config)

    if args.daemon:
        logger.info("Running as daemon - press Ctrl+C to stop")
        try:
            await loop.run_training_loop(max_loops=1000)  # Run indefinitely
        except KeyboardInterrupt:
            logger.info("Daemon stopped by user")
    else:
        await loop.run_training_loop(max_loops=args.loops)

    # Show final stats
    stats = loop.collector.get_collection_stats()
    print(f"Final training stats: {loop.training_stats}")
    print(f"Collection stats: {stats}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())