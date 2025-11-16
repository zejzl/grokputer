"""
Direct Preference Optimization (DPO) for Agent Parameter Tuning

Adapts DPO to optimize agent parameters based on performance preferences.
Uses preference pairs of parameter settings to directly optimize without reward models.
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim

logger = logging.getLogger(__name__)


@dataclass
class PreferencePair:
    """Represents a preference pair for DPO training."""

    task_description: str
    chosen_params: Dict[str, Any]  # Preferred parameter settings
    rejected_params: Dict[str, Any]  # Less preferred parameter settings
    task_metrics: Dict[str, float]  # Performance metrics for the task


class AgentDPO:
    """
    DPO optimizer for agent parameter tuning.

    Learns to prefer parameter settings that lead to better performance
    using preference pairs without explicit reward modeling.
    """

    def __init__(
        self,
        param_space: Dict[str, Tuple[float, float]],
        learning_rate: float = 1e-3,
        beta: float = 0.1,
        device: str = "cpu",
    ):
        """
        Initialize DPO optimizer.

        Args:
            param_space: Dict of parameter names to (min, max) ranges
            learning_rate: Learning rate for optimization
            beta: DPO regularization parameter
            device: PyTorch device
        """
        self.param_space = param_space
        self.beta = beta
        self.device = device

        # Create parameter embeddings (simple linear layers for each param)
        self.param_embeddings = nn.ModuleDict()
        for param_name, (min_val, max_val) in param_space.items():
            # Normalize to [-1, 1] range
            self.param_embeddings[param_name] = nn.Linear(1, 32)

        # Policy network (maps parameter sets to preference scores)
        self.policy_net = nn.Sequential(
            nn.Linear(len(param_space) * 32, 128),
            nn.ReLU(),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, 1),  # Single preference score
        ).to(device)

        self.optimizer = optim.Adam(
            list(self.param_embeddings.parameters()) + list(self.policy_net.parameters()), lr=learning_rate
        )

        self.preference_pairs: List[PreferencePair] = []

        logger.info(f"DPO initialized for {len(param_space)} parameters")

    def params_to_tensor(self, params: Dict[str, Any]) -> torch.Tensor:
        """Convert parameter dict to tensor embedding."""
        embeddings = []
        for param_name, param_value in params.items():
            if param_name in self.param_embeddings:
                # Normalize value to [-1, 1]
                min_val, max_val = self.param_space[param_name]
                normalized = 2 * (param_value - min_val) / (max_val - min_val) - 1
                tensor_val = torch.tensor([[normalized]], dtype=torch.float32, device=self.device)
                embedding = self.param_embeddings[param_name](tensor_val)
                embeddings.append(embedding.squeeze())

        if embeddings:
            return torch.cat(embeddings)
        else:
            return torch.zeros(len(self.param_space) * 32, device=self.device)

    def get_preference_score(self, params: Dict[str, Any]) -> float:
        """Get preference score for parameter set."""
        with torch.no_grad():
            embedding = self.params_to_tensor(params)
            score = self.policy_net(embedding.unsqueeze(0))
            return score.item()

    def dpo_loss(self, chosen_params: Dict[str, Any], rejected_params: Dict[str, Any]) -> torch.Tensor:
        """Compute DPO loss for a preference pair."""
        chosen_embedding = self.params_to_tensor(chosen_params)
        rejected_embedding = self.params_to_tensor(rejected_params)

        chosen_score = self.policy_net(chosen_embedding.unsqueeze(0))
        rejected_score = self.policy_net(rejected_embedding.unsqueeze(0))

        # DPO loss: -log(σ(β * (chosen_score - rejected_score)))
        logits = self.beta * (chosen_score - rejected_score)
        loss = -torch.log(torch.sigmoid(logits)).mean()

        return loss

    def add_preference_pair(self, pair: PreferencePair):
        """Add a preference pair to the training data."""
        self.preference_pairs.append(pair)
        logger.debug(f"Added preference pair for task: {pair.task_description[:50]}...")

    def train_step(self, batch_size: int = 32) -> float:
        """Perform one training step on random batch of preference pairs."""
        if len(self.preference_pairs) < batch_size:
            return 0.0

        # Sample batch
        batch_indices = np.random.choice(len(self.preference_pairs), batch_size, replace=True)
        batch_pairs = [self.preference_pairs[i] for i in batch_indices]

        total_loss = 0.0

        for pair in batch_pairs:
            loss = self.dpo_loss(pair.chosen_params, pair.rejected_params)
            total_loss += loss.item()

            # Backward pass
            self.optimizer.zero_grad()
            loss.backward()
            self.optimizer.step()

        avg_loss = total_loss / len(batch_pairs)
        logger.debug(f"DPO training step: loss={avg_loss:.4f}")

        return avg_loss

    def optimize_parameters(self, task_description: str, current_metrics: Dict[str, float]) -> Dict[str, Any]:
        """
        Suggest optimal parameters for a task based on learned preferences.

        Args:
            task_description: Description of the current task
            current_metrics: Current performance metrics

        Returns:
            Suggested parameter adjustments
        """
        # For now, sample from parameter space and pick best scoring
        # In production, could use more sophisticated optimization

        best_params = {}
        best_score = float("-inf")

        # Sample some parameter combinations
        for _ in range(50):  # Sample 50 combinations
            params = {}
            for param_name, (min_val, max_val) in self.param_space.items():
                params[param_name] = np.random.uniform(min_val, max_val)

            score = self.get_preference_score(params)
            if score > best_score:
                best_score = score
                best_params = params

        logger.info(f"DPO suggested params with score {best_score:.3f}: {best_params}")
        return best_params

    def save_model(self, filepath: str):
        """Save DPO model."""
        torch.save(
            {
                "param_embeddings": self.param_embeddings.state_dict(),
                "policy_net": self.policy_net.state_dict(),
                "param_space": self.param_space,
                "beta": self.beta,
            },
            filepath,
        )
        logger.info(f"DPO model saved to {filepath}")

    def load_model(self, filepath: str):
        """Load DPO model."""
        checkpoint = torch.load(filepath)
        self.param_embeddings.load_state_dict(checkpoint["param_embeddings"])
        self.policy_net.load_state_dict(checkpoint["policy_net"])
        logger.info(f"DPO model loaded from {filepath}")


# Example usage
if __name__ == "__main__":
    # Define parameter space for agent optimization
    param_space = {"temperature": (0.1, 1.0), "max_tokens": (50, 500), "timeout": (5, 30)}

    dpo = AgentDPO(param_space)

    # Add some example preference pairs
    pair1 = PreferencePair(
        task_description="Simple task",
        chosen_params={"temperature": 0.7, "max_tokens": 200, "timeout": 10},
        rejected_params={"temperature": 0.3, "max_tokens": 100, "timeout": 5},
        task_metrics={"accuracy": 0.9, "speed": 0.8},
    )

    dpo.add_preference_pair(pair1)

    # Train for a few steps
    for _ in range(10):
        loss = dpo.train_step(batch_size=1)
        print(f"Loss: {loss:.4f}")

    # Get optimal parameters
    optimal = dpo.optimize_parameters("Test task", {"accuracy": 0.8})
    print(f"Optimal params: {optimal}")
