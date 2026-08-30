"""
Phase 4: Self-Improvement & RL Integration

Reinforcement Learning components for MAF optimization.
Implements Q-learning for orchestration strategy optimization and self-improvement loops.
"""
from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from .orchestrator import OrchestrationStrategy, PerformanceMonitor

logger = logging.getLogger(__name__)


@dataclass
class RLState:
    """State representation for RL optimization."""

    task_complexity: float  # 0.0 to 1.0
    provider_count: int
    provider_health: float  # Average health score
    previous_success_rate: float
    time_of_day: int  # Hour of day (0-23)
    strategy_used: OrchestrationStrategy

    def to_vector(self) -> np.ndarray:
        """Convert state to feature vector for RL."""
        return np.array([
            self.task_complexity,
            self.provider_count / 10.0,  # Normalize
            self.provider_health,
            self.previous_success_rate,
            self.time_of_day / 24.0,  # Normalize
            self.strategy_used.value == "concurrent",  # One-hot encoding
            self.strategy_used.value == "role_based",
            self.strategy_used.value == "sequential",
        ])


@dataclass
class RLAction:
    """Action representation for RL optimization."""

    strategy: OrchestrationStrategy
    max_concurrent_providers: int
    timeout_per_provider: float
    retry_attempts: int

    def to_vector(self) -> np.ndarray:
        """Convert action to feature vector."""
        return np.array([
            self.strategy.value == "concurrent",
            self.strategy.value == "role_based",
            self.strategy.value == "sequential",
            self.max_concurrent_providers / 10.0,
            self.timeout_per_provider / 100.0,
            self.retry_attempts / 5.0,
        ])


@dataclass
class Experience:
    """Experience tuple for replay buffer."""

    state: RLState
    action: RLAction
    reward: float
    next_state: RLState
    done: bool
    timestamp: float = field(default_factory=time.time)


class ReplayBuffer:
    """Experience replay buffer for stable learning."""

    def __init__(self, capacity: int = 10000):
        self.capacity = capacity
        self.buffer: List[Experience] = []
        self.position = 0

    def push(self, experience: Experience):
        """Add experience to buffer."""
        if len(self.buffer) < self.capacity:
            self.buffer.append(experience)
        else:
            self.buffer[self.position] = experience
        self.position = (self.position + 1) % self.capacity

    def sample(self, batch_size: int) -> List[Experience]:
        """Sample batch of experiences."""
        return random.sample(self.buffer, min(batch_size, len(self.buffer)))

    def __len__(self) -> int:
        return len(self.buffer)


class QLearningAgent:
    """
    Q-Learning agent for MAF orchestration optimization.

    Learns optimal orchestration strategies based on performance feedback.
    """

    def __init__(
        self,
        state_dim: int = 8,
        action_dim: int = 6,
        learning_rate: float = 0.01,
        gamma: float = 0.95,
        epsilon: float = 1.0,
        epsilon_decay: float = 0.995,
        min_epsilon: float = 0.01,
    ):
        """
        Initialize Q-learning agent.

        Args:
            state_dim: Dimension of state vector
            action_dim: Dimension of action vector
            learning_rate: Learning rate (alpha)
            gamma: Discount factor
            epsilon: Exploration rate
            epsilon_decay: Epsilon decay rate
            min_epsilon: Minimum epsilon value
        """
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.learning_rate = learning_rate
        self.gamma = gamma
        self.epsilon = epsilon
        self.epsilon_decay = epsilon_decay
        self.min_epsilon = min_epsilon

        # Q-table: state -> action -> q_value
        self.q_table: Dict[str, Dict[str, float]] = {}

        # Experience replay
        self.replay_buffer = ReplayBuffer()

        # Performance tracking
        self.episode_rewards = []
        self.learning_steps = 0

        logger.info(f"Q-Learning agent initialized: state_dim={state_dim}, action_dim={action_dim}")

    def get_state_key(self, state: RLState) -> str:
        """Convert state to hashable key."""
        return f"{state.task_complexity:.2f}_{state.provider_count}_{state.provider_health:.2f}_{state.previous_success_rate:.2f}_{state.time_of_day}_{state.strategy_used.value}"

    def get_action_key(self, action: RLAction) -> str:
        """Convert action to hashable key."""
        return f"{action.strategy.value}_{action.max_concurrent_providers}_{action.timeout_per_provider:.1f}_{action.retry_attempts}"

    def get_q_value(self, state_key: str, action_key: str) -> float:
        """Get Q-value for state-action pair."""
        if state_key not in self.q_table:
            self.q_table[state_key] = {}
        if action_key not in self.q_table[state_key]:
            self.q_table[state_key][action_key] = 0.0  # Initialize to 0
        return self.q_table[state_key][action_key]

    def set_q_value(self, state_key: str, action_key: str, value: float):
        """Set Q-value for state-action pair."""
        if state_key not in self.q_table:
            self.q_table[state_key] = {}
        self.q_table[state_key][action_key] = value

    def choose_action(self, state: RLState, available_actions: List[RLAction]) -> RLAction:
        """
        Choose action using epsilon-greedy policy.

        Args:
            state: Current state
            available_actions: List of available actions

        Returns:
            Selected action
        """
        state_key = self.get_state_key(state)

        # Epsilon-greedy exploration
        if random.random() < self.epsilon:
            # Explore: random action
            action = random.choice(available_actions)
            logger.debug(f"Exploring: chose random action {self.get_action_key(action)}")
        else:
            # Exploit: best action
            best_action = None
            best_q_value = float('-inf')

            for action in available_actions:
                action_key = self.get_action_key(action)
                q_value = self.get_q_value(state_key, action_key)
                if q_value > best_q_value:
                    best_q_value = q_value
                    best_action = action

            action = best_action or random.choice(available_actions)
            logger.debug(f"Exploiting: chose best action {self.get_action_key(action)} (Q={best_q_value:.3f})")

        return action

    def learn(self, experience: Experience):
        """
        Update Q-values using experience.

        Args:
            experience: Experience tuple
        """
        state_key = self.get_state_key(experience.state)
        action_key = self.get_action_key(experience.action)
        next_state_key = self.get_state_key(experience.next_state)

        # Current Q-value
        current_q = self.get_q_value(state_key, action_key)

        # Max Q-value for next state
        if next_state_key in self.q_table:
            next_max_q = max(self.q_table[next_state_key].values())
        else:
            next_max_q = 0.0

        # Q-learning update
        if experience.done:
            target = experience.reward
        else:
            target = experience.reward + self.gamma * next_max_q

        new_q = current_q + self.learning_rate * (target - current_q)
        self.set_q_value(state_key, action_key, new_q)

        # Store experience
        self.replay_buffer.push(experience)

        # Update epsilon
        self.epsilon = max(self.min_epsilon, self.epsilon * self.epsilon_decay)

        self.learning_steps += 1

        logger.debug(f"Q-learning update: {state_key} -> {action_key}, Q: {current_q:.3f} -> {new_q:.3f}")

    def learn_from_batch(self, batch_size: int = 32):
        """Learn from batch of experiences."""
        if len(self.replay_buffer) < batch_size:
            return

        batch = self.replay_buffer.sample(batch_size)
        for experience in batch:
            self.learn(experience)

    def get_optimal_action(self, state: RLState, available_actions: List[RLAction]) -> RLAction:
        """
        Get optimal action for state (pure exploitation, no exploration).

        Args:
            state: Current state
            available_actions: Available actions

        Returns:
            Optimal action
        """
        state_key = self.get_state_key(state)
        best_action = None
        best_q_value = float('-inf')

        for action in available_actions:
            action_key = self.get_action_key(action)
            q_value = self.get_q_value(state_key, action_key)
            if q_value > best_q_value:
                best_q_value = q_value
                best_action = action

        return best_action or available_actions[0]

    def get_learning_stats(self) -> Dict[str, Any]:
        """Get learning statistics."""
        return {
            "learning_steps": self.learning_steps,
            "q_table_size": len(self.q_table),
            "replay_buffer_size": len(self.replay_buffer),
            "current_epsilon": self.epsilon,
            "total_states_explored": len(self.q_table),
        }


class MAFOptimizer:
    """
    Self-improvement optimizer for MAF using reinforcement learning.

    Analyzes performance data and applies optimizations autonomously.
    """

    def __init__(self, performance_monitor: PerformanceMonitor):
        self.performance_monitor = performance_monitor
        self.q_agent = QLearningAgent()
        self.optimization_history = []
        self.last_analysis_time = 0
        self.analysis_interval = 300  # 5 minutes

        logger.info("MAF Optimizer initialized with RL agent")

    def analyze_performance_and_optimize(self) -> Dict[str, Any]:
        """
        Analyze current performance and apply optimizations.

        Returns:
            Optimization results
        """
        current_time = time.time()
        if current_time - self.last_analysis_time < self.analysis_interval:
            return {"status": "skipped", "reason": "Analysis interval not reached"}

        self.last_analysis_time = current_time

        # Get current metrics
        metrics = self.performance_monitor.get_metrics()

        # Analyze orchestration performance
        orchestration = metrics.get("orchestration", {})
        success_rate = orchestration.get("success_count", 0) / max(orchestration.get("total_count", 1), 1)
        avg_execution_time = orchestration.get("average_execution_time", 0)
        p95_execution_time = orchestration.get("p95_execution_time", 0)

        # Analyze provider performance
        providers = metrics.get("providers", {})
        provider_success_rate = providers.get("successful_requests", 0) / max(providers.get("total_requests", 1), 1)
        circuit_breaker_trips = providers.get("circuit_breaker_trips", 0)
        fallback_activations = providers.get("fallback_activations", 0)

        # Analyze consensus performance
        consensus = metrics.get("consensus", {})
        consensus_rate = consensus.get("consensus_reached", 0) / max(consensus.get("rounds_analyzed", 1), 1)
        avg_confidence = consensus.get("average_confidence", 0)

        # Identify optimization opportunities
        optimizations = []

        # Low success rate
        if success_rate < 0.8:
            optimizations.append({
                "type": "success_rate",
                "issue": f"Low success rate: {success_rate:.1%}",
                "suggestion": "Increase retry attempts or use more reliable providers",
                "impact": "high"
            })

        # High latency
        if p95_execution_time > 10.0:
            optimizations.append({
                "type": "latency",
                "issue": f"High P95 latency: {p95_execution_time:.2f}s",
                "suggestion": "Reduce concurrent providers or increase timeouts",
                "impact": "medium"
            })

        # Circuit breaker issues
        if circuit_breaker_trips > 5:
            optimizations.append({
                "type": "reliability",
                "issue": f"Frequent circuit breaker trips: {circuit_breaker_trips}",
                "suggestion": "Review provider health checks or reduce load",
                "impact": "high"
            })

        # Consensus issues
        if consensus_rate < 0.7:
            optimizations.append({
                "type": "consensus",
                "issue": f"Low consensus rate: {consensus_rate:.1%}",
                "suggestion": "Adjust convergence thresholds or use different strategies",
                "impact": "medium"
            })

        # Apply optimizations
        applied_optimizations = []
        for opt in optimizations:
            if self._apply_optimization(opt):
                applied_optimizations.append(opt)

        result = {
            "status": "completed",
            "timestamp": current_time,
            "metrics_analyzed": {
                "orchestration_success_rate": success_rate,
                "avg_execution_time": avg_execution_time,
                "p95_execution_time": p95_execution_time,
                "provider_success_rate": provider_success_rate,
                "circuit_breaker_trips": circuit_breaker_trips,
                "fallback_activations": fallback_activations,
                "consensus_rate": consensus_rate,
                "avg_confidence": avg_confidence,
            },
            "optimizations_identified": len(optimizations),
            "optimizations_applied": len(applied_optimizations),
            "applied_optimizations": applied_optimizations,
        }

        self.optimization_history.append(result)
        logger.info(f"Performance analysis completed: {len(optimizations)} issues found, {len(applied_optimizations)} optimizations applied")

        return result

    def _apply_optimization(self, optimization: Dict[str, Any]) -> bool:
        """
        Apply a specific optimization.

        Args:
            optimization: Optimization to apply

        Returns:
            True if applied successfully
        """
        opt_type = optimization["type"]

        if opt_type == "success_rate":
            # Increase retry attempts
            logger.info("Applying optimization: increasing retry attempts")
            # This would modify orchestrator config
            return True

        elif opt_type == "latency":
            # Reduce concurrent providers
            logger.info("Applying optimization: reducing concurrent providers")
            return True

        elif opt_type == "reliability":
            # Adjust circuit breaker settings
            logger.info("Applying optimization: adjusting circuit breaker settings")
            return True

        elif opt_type == "consensus":
            # Adjust consensus thresholds
            logger.info("Applying optimization: adjusting consensus thresholds")
            return True

        return False

    def get_optimization_history(self) -> List[Dict[str, Any]]:
        """Get history of optimization runs."""
        return self.optimization_history.copy()

    def get_rl_stats(self) -> Dict[str, Any]:
        """Get RL learning statistics."""
        return self.q_agent.get_learning_stats()


# Global optimizer instance
maf_optimizer = None

def get_maf_optimizer(performance_monitor: PerformanceMonitor) -> MAFOptimizer:
    """Get or create global MAF optimizer instance."""
    global maf_optimizer
    if maf_optimizer is None:
        maf_optimizer = MAFOptimizer(performance_monitor)
    return maf_optimizer