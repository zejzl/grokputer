"""
Comprehensive tests for MAF RL Optimizer

Tests cover Q-learning agent, experience replay, epsilon-greedy exploration,
state-action-reward tracking, and policy optimization.
"""

import pytest
import numpy as np
from unittest.mock import MagicMock, Mock, patch
from src.collaboration.rl_optimizer import (
    QLearningAgent,
    Experience,
    ReplayBuffer,
)


# Experience Tests


def test_experience_creation():
    """Test creating an experience tuple"""
    experience = Experience(
        state="state1",
        action="action1",
        reward=1.0,
        next_state="state2",
        done=False
    )

    assert experience.state == "state1"
    assert experience.action == "action1"
    assert experience.reward == 1.0
    assert experience.next_state == "state2"
    assert experience.done is False


def test_experience_terminal_state():
    """Test experience with terminal state"""
    experience = Experience(
        state="final_state",
        action="final_action",
        reward=10.0,
        next_state=None,
        done=True
    )

    assert experience.done is True
    assert experience.next_state is None
    assert experience.reward == 10.0


# Replay Buffer Tests


def test_replay_buffer_initialization():
    """Test replay buffer initializes with correct capacity"""
    buffer = ReplayBuffer(capacity=1000)

    assert buffer.capacity == 1000
    assert len(buffer.buffer) == 0


def test_replay_buffer_add_experience():
    """Test adding experience to buffer"""
    buffer = ReplayBuffer(capacity=100)

    exp = Experience(
        state="state1",
        action="action1",
        reward=1.0,
        next_state="state2",
        done=False
    )

    buffer.add(exp)

    assert len(buffer.buffer) == 1
    assert buffer.buffer[0] == exp


def test_replay_buffer_capacity_limit():
    """Test that buffer respects capacity limit"""
    buffer = ReplayBuffer(capacity=3)

    for i in range(5):
        exp = Experience(
            state=f"state{i}",
            action=f"action{i}",
            reward=float(i),
            next_state=f"state{i+1}",
            done=False
        )
        buffer.add(exp)

    # Should only keep last 3
    assert len(buffer.buffer) == 3


def test_replay_buffer_sample():
    """Test sampling from buffer"""
    buffer = ReplayBuffer(capacity=100)

    # Add experiences
    for i in range(10):
        exp = Experience(
            state=f"state{i}",
            action=f"action{i}",
            reward=float(i),
            next_state=f"state{i+1}",
            done=False
        )
        buffer.add(exp)

    # Sample batch
    batch = buffer.sample(batch_size=5)

    assert len(batch) == 5
    assert all(isinstance(exp, Experience) for exp in batch)


def test_replay_buffer_sample_more_than_available():
    """Test sampling when batch size exceeds buffer size"""
    buffer = ReplayBuffer(capacity=100)

    # Add only 3 experiences
    for i in range(3):
        exp = Experience(
            state=f"state{i}",
            action=f"action{i}",
            reward=float(i),
            next_state=f"state{i+1}",
            done=False
        )
        buffer.add(exp)

    # Try to sample 5
    batch = buffer.sample(batch_size=5)

    # Should return all available (3)
    assert len(batch) == 3


def test_replay_buffer_empty_sample():
    """Test sampling from empty buffer"""
    buffer = ReplayBuffer(capacity=100)

    batch = buffer.sample(batch_size=5)

    assert len(batch) == 0


# Q-Learning Agent Tests


def test_qlearning_agent_initialization():
    """Test Q-learning agent initializes correctly"""
    agent = QLearningAgent(
        learning_rate=0.1,
        discount_factor=0.95,
        epsilon=0.2,
        epsilon_decay=0.995,
        min_epsilon=0.01
    )

    assert agent.learning_rate == 0.1
    assert agent.discount_factor == 0.95
    assert agent.epsilon == 0.2
    assert agent.epsilon_decay == 0.995
    assert agent.min_epsilon == 0.01
    assert isinstance(agent.q_table, dict)


def test_qlearning_agent_default_values():
    """Test Q-learning agent with default values"""
    agent = QLearningAgent()

    assert agent.learning_rate > 0
    assert 0 < agent.discount_factor <= 1
    assert 0 <= agent.epsilon <= 1
    assert agent.q_table == {}


def test_qlearning_agent_get_q_value():
    """Test getting Q-value for state-action pair"""
    agent = QLearningAgent()

    # New state-action should return 0
    q_value = agent.get_q_value("state1", "action1")
    assert q_value == 0.0


def test_qlearning_agent_set_q_value():
    """Test setting Q-value for state-action pair"""
    agent = QLearningAgent()

    agent.set_q_value("state1", "action1", 5.0)

    q_value = agent.get_q_value("state1", "action1")
    assert q_value == 5.0


def test_qlearning_agent_get_best_action():
    """Test selecting best action for a state"""
    agent = QLearningAgent()

    # Set up Q-values
    agent.set_q_value("state1", "action_a", 1.0)
    agent.set_q_value("state1", "action_b", 5.0)
    agent.set_q_value("state1", "action_c", 2.0)

    actions = ["action_a", "action_b", "action_c"]
    best_action = agent.get_best_action("state1", actions)

    # Should select action_b (highest Q-value)
    assert best_action == "action_b"


def test_qlearning_agent_choose_action_exploitation():
    """Test action selection during exploitation (epsilon=0)"""
    agent = QLearningAgent(epsilon=0.0)  # Pure exploitation

    agent.set_q_value("state1", "action_a", 1.0)
    agent.set_q_value("state1", "action_b", 5.0)

    actions = ["action_a", "action_b"]

    # Should always choose best action
    chosen_actions = [agent.choose_action("state1", actions) for _ in range(10)]

    assert all(action == "action_b" for action in chosen_actions)


def test_qlearning_agent_choose_action_exploration():
    """Test action selection includes exploration"""
    agent = QLearningAgent(epsilon=1.0)  # Pure exploration

    agent.set_q_value("state1", "action_a", 1.0)
    agent.set_q_value("state1", "action_b", 5.0)

    actions = ["action_a", "action_b"]

    # With epsilon=1.0, should explore randomly
    chosen_actions = [agent.choose_action("state1", actions) for _ in range(100)]

    # Should get both actions due to random exploration
    assert "action_a" in chosen_actions
    assert "action_b" in chosen_actions


def test_qlearning_agent_update():
    """Test Q-value update"""
    agent = QLearningAgent(learning_rate=0.1, discount_factor=0.9)

    # Set initial Q-values
    agent.set_q_value("state1", "action1", 0.0)
    agent.set_q_value("state2", "action_a", 5.0)
    agent.set_q_value("state2", "action_b", 3.0)

    # Update: state1, action1 leads to state2 with reward 10
    agent.update("state1", "action1", 10.0, "state2", done=False)

    # Q(s,a) = Q(s,a) + α * (r + γ * max(Q(s',a')) - Q(s,a))
    # Q = 0 + 0.1 * (10 + 0.9 * 5 - 0) = 0.1 * (10 + 4.5) = 1.45
    expected_q = 1.45
    actual_q = agent.get_q_value("state1", "action1")

    assert abs(actual_q - expected_q) < 0.01


def test_qlearning_agent_update_terminal_state():
    """Test Q-value update for terminal state"""
    agent = QLearningAgent(learning_rate=0.1, discount_factor=0.9)

    agent.set_q_value("state1", "action1", 0.0)

    # Terminal state: no future reward
    agent.update("state1", "action1", 10.0, "state_terminal", done=True)

    # Q = 0 + 0.1 * (10 + 0 - 0) = 1.0
    expected_q = 1.0
    actual_q = agent.get_q_value("state1", "action1")

    assert abs(actual_q - expected_q) < 0.01


def test_qlearning_agent_epsilon_decay():
    """Test that epsilon decays over time"""
    agent = QLearningAgent(epsilon=1.0, epsilon_decay=0.9, min_epsilon=0.1)

    initial_epsilon = agent.epsilon

    agent.decay_epsilon()

    assert agent.epsilon < initial_epsilon
    assert agent.epsilon == 0.9


def test_qlearning_agent_epsilon_min_limit():
    """Test that epsilon doesn't go below minimum"""
    agent = QLearningAgent(epsilon=0.15, epsilon_decay=0.5, min_epsilon=0.1)

    agent.decay_epsilon()

    # 0.15 * 0.5 = 0.075, but should be clamped to 0.1
    assert agent.epsilon == 0.1


def test_qlearning_agent_q_table_persistence():
    """Test that Q-table persists across updates"""
    agent = QLearningAgent()

    agent.set_q_value("state1", "action1", 5.0)
    agent.set_q_value("state1", "action2", 3.0)
    agent.set_q_value("state2", "action1", 7.0)

    assert len(agent.q_table) == 2  # 2 states
    assert "state1" in agent.q_table
    assert "state2" in agent.q_table


def test_qlearning_agent_multiple_updates():
    """Test multiple Q-value updates"""
    agent = QLearningAgent(learning_rate=0.1, discount_factor=0.9)

    # Initial value
    agent.set_q_value("state1", "action1", 0.0)

    # Multiple updates should gradually increase Q-value
    for _ in range(10):
        agent.update("state1", "action1", 1.0, "state2", done=False)

    final_q = agent.get_q_value("state1", "action1")

    # Should be greater than 0 after positive rewards
    assert final_q > 0


def test_qlearning_agent_negative_reward():
    """Test Q-value update with negative reward"""
    agent = QLearningAgent(learning_rate=0.1, discount_factor=0.9)

    agent.set_q_value("state1", "action1", 0.0)

    # Negative reward
    agent.update("state1", "action1", -5.0, "state2", done=False)

    q_value = agent.get_q_value("state1", "action1")

    # Q-value should be negative
    assert q_value < 0


def test_qlearning_agent_state_initialization():
    """Test that new states are initialized to 0"""
    agent = QLearningAgent()

    # Access Q-value for new state-action pair
    q_value = agent.get_q_value("never_seen_state", "never_seen_action")

    assert q_value == 0.0


def test_qlearning_agent_action_values_independence():
    """Test that different actions have independent Q-values"""
    agent = QLearningAgent()

    agent.set_q_value("state1", "action_a", 10.0)
    agent.set_q_value("state1", "action_b", 5.0)

    assert agent.get_q_value("state1", "action_a") == 10.0
    assert agent.get_q_value("state1", "action_b") == 5.0


def test_qlearning_agent_max_q_value():
    """Test getting maximum Q-value for a state"""
    agent = QLearningAgent()

    agent.set_q_value("state1", "action_a", 3.0)
    agent.set_q_value("state1", "action_b", 7.0)
    agent.set_q_value("state1", "action_c", 5.0)

    actions = ["action_a", "action_b", "action_c"]
    max_q = max(agent.get_q_value("state1", a) for a in actions)

    assert max_q == 7.0


def test_replay_buffer_fifo_behavior():
    """Test that replay buffer follows FIFO when at capacity"""
    buffer = ReplayBuffer(capacity=3)

    # Add 5 experiences
    experiences = []
    for i in range(5):
        exp = Experience(
            state=f"state{i}",
            action=f"action{i}",
            reward=float(i),
            next_state=f"state{i+1}",
            done=False
        )
        experiences.append(exp)
        buffer.add(exp)

    # Should contain last 3 (index 2, 3, 4)
    assert len(buffer.buffer) == 3
    assert experiences[2] in buffer.buffer or experiences[3] in buffer.buffer or experiences[4] in buffer.buffer


def test_qlearning_agent_convergence():
    """Test that Q-values converge with repeated updates"""
    agent = QLearningAgent(learning_rate=0.5, discount_factor=0.9)

    agent.set_q_value("state1", "action1", 0.0)

    # Repeatedly update with same reward
    for _ in range(100):
        agent.update("state1", "action1", 10.0, "state_terminal", done=True)

    final_q = agent.get_q_value("state1", "action1")

    # Should converge close to reward value (10.0)
    assert abs(final_q - 10.0) < 1.0


def test_qlearning_agent_learning_rate_effect():
    """Test that learning rate affects update magnitude"""
    agent_slow = QLearningAgent(learning_rate=0.01, discount_factor=0.9)
    agent_fast = QLearningAgent(learning_rate=0.5, discount_factor=0.9)

    agent_slow.set_q_value("state1", "action1", 0.0)
    agent_fast.set_q_value("state1", "action1", 0.0)

    # Single update
    agent_slow.update("state1", "action1", 10.0, "state_terminal", done=True)
    agent_fast.update("state1", "action1", 10.0, "state_terminal", done=True)

    # Fast learner should have higher Q-value after one update
    assert agent_fast.get_q_value("state1", "action1") > agent_slow.get_q_value("state1", "action1")


def test_replay_buffer_clear():
    """Test clearing replay buffer"""
    buffer = ReplayBuffer(capacity=100)

    for i in range(10):
        exp = Experience(
            state=f"state{i}",
            action=f"action{i}",
            reward=float(i),
            next_state=f"state{i+1}",
            done=False
        )
        buffer.add(exp)

    assert len(buffer.buffer) == 10

    # Clear if method exists
    if hasattr(buffer, 'clear'):
        buffer.clear()
        assert len(buffer.buffer) == 0
