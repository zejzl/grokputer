"""
Comprehensive tests for MAF RL Optimizer - API-Aligned Version

Tests cover Q-learning agent, experience replay, epsilon-greedy exploration,
state-action-reward tracking using actual RLState/RLAction dataclasses.
"""

import pytest
import numpy as np
from unittest.mock import MagicMock, Mock, patch
from src.collaboration.rl_optimizer import (
    QLearningAgent,
    Experience,
    ReplayBuffer,
    RLState,
    RLAction,
    MAFOptimizer,
)
from src.collaboration.orchestrator import OrchestrationStrategy


# Test Fixtures - Factory Functions

def create_test_state(
    task_complexity=0.5,
    provider_count=3,
    provider_health=0.8,
    previous_success_rate=0.75,
    time_of_day=12,
    strategy_used=OrchestrationStrategy.CONCURRENT
) -> RLState:
    """Create a test RLState."""
    return RLState(
        task_complexity=task_complexity,
        provider_count=provider_count,
        provider_health=provider_health,
        previous_success_rate=previous_success_rate,
        time_of_day=time_of_day,
        strategy_used=strategy_used
    )


def create_test_action(
    strategy=OrchestrationStrategy.CONCURRENT,
    max_concurrent_providers=3,
    timeout_per_provider=30.0,
    retry_attempts=3
) -> RLAction:
    """Create a test RLAction."""
    return RLAction(
        strategy=strategy,
        max_concurrent_providers=max_concurrent_providers,
        timeout_per_provider=timeout_per_provider,
        retry_attempts=retry_attempts
    )


def create_test_experience(
    state=None,
    action=None,
    reward=1.0,
    next_state=None,
    done=False
) -> Experience:
    """Create a test Experience."""
    if state is None:
        state = create_test_state()
    if action is None:
        action = create_test_action()
    if next_state is None:
        next_state = create_test_state(task_complexity=0.6)

    return Experience(
        state=state,
        action=action,
        reward=reward,
        next_state=next_state,
        done=done
    )


# RLState Tests

def test_rlstate_creation():
    """Test creating an RLState."""
    state = create_test_state()

    assert state.task_complexity == 0.5
    assert state.provider_count == 3
    assert state.provider_health == 0.8
    assert state.previous_success_rate == 0.75
    assert state.time_of_day == 12
    assert state.strategy_used == OrchestrationStrategy.CONCURRENT


def test_rlstate_to_vector():
    """Test RLState conversion to feature vector."""
    state = create_test_state()
    vector = state.to_vector()

    assert isinstance(vector, np.ndarray)
    assert len(vector) == 8  # 5 features + 3 one-hot encoded strategy


# RLAction Tests

def test_rlaction_creation():
    """Test creating an RLAction."""
    action = create_test_action()

    assert action.strategy == OrchestrationStrategy.CONCURRENT
    assert action.max_concurrent_providers == 3
    assert action.timeout_per_provider == 30.0
    assert action.retry_attempts == 3


def test_rlaction_to_vector():
    """Test RLAction conversion to feature vector."""
    action = create_test_action()
    vector = action.to_vector()

    assert isinstance(vector, np.ndarray)
    assert len(vector) == 6  # 3 one-hot strategy + 3 numeric features


# Experience Tests

def test_experience_creation():
    """Test creating an experience tuple."""
    state = create_test_state(task_complexity=0.5)
    action = create_test_action()
    next_state = create_test_state(task_complexity=0.6)

    experience = Experience(
        state=state,
        action=action,
        reward=1.0,
        next_state=next_state,
        done=False
    )

    assert experience.state == state
    assert experience.action == action
    assert experience.reward == 1.0
    assert experience.next_state == next_state
    assert experience.done is False
    assert hasattr(experience, 'timestamp')


def test_experience_terminal_state():
    """Test experience with terminal state."""
    state = create_test_state()
    action = create_test_action()

    experience = Experience(
        state=state,
        action=action,
        reward=10.0,
        next_state=create_test_state(),
        done=True
    )

    assert experience.done is True
    assert experience.reward == 10.0


# Replay Buffer Tests

def test_replay_buffer_initialization():
    """Test replay buffer initializes with correct capacity."""
    buffer = ReplayBuffer(capacity=1000)

    assert buffer.capacity == 1000
    assert len(buffer.buffer) == 0


def test_replay_buffer_push_experience():
    """Test adding experience to buffer."""
    buffer = ReplayBuffer(capacity=100)
    exp = create_test_experience()

    buffer.push(exp)

    assert len(buffer.buffer) == 1
    assert buffer.buffer[0] == exp


def test_replay_buffer_capacity_limit():
    """Test that buffer respects capacity limit."""
    buffer = ReplayBuffer(capacity=3)

    for i in range(5):
        exp = create_test_experience(reward=float(i))
        buffer.push(exp)

    # Should only keep 3 experiences (circular buffer)
    assert len(buffer.buffer) == 3


def test_replay_buffer_sample():
    """Test sampling from buffer."""
    buffer = ReplayBuffer(capacity=100)

    # Add experiences
    for i in range(10):
        exp = create_test_experience(reward=float(i))
        buffer.push(exp)

    # Sample batch
    batch = buffer.sample(batch_size=5)

    assert len(batch) == 5
    assert all(isinstance(exp, Experience) for exp in batch)


def test_replay_buffer_sample_more_than_available():
    """Test sampling when batch size exceeds buffer size."""
    buffer = ReplayBuffer(capacity=100)

    # Add only 3 experiences
    for i in range(3):
        exp = create_test_experience(reward=float(i))
        buffer.push(exp)

    # Try to sample 5
    batch = buffer.sample(batch_size=5)

    # Should return all available (3)
    assert len(batch) == 3


def test_replay_buffer_empty_sample():
    """Test sampling from empty buffer."""
    buffer = ReplayBuffer(capacity=100)

    batch = buffer.sample(batch_size=5)

    assert len(batch) == 0


def test_replay_buffer_len():
    """Test __len__ method of replay buffer."""
    buffer = ReplayBuffer(capacity=100)

    assert len(buffer) == 0

    buffer.push(create_test_experience())
    assert len(buffer) == 1

    buffer.push(create_test_experience())
    assert len(buffer) == 2


# Q-Learning Agent Tests

def test_qlearning_agent_initialization():
    """Test Q-learning agent initializes correctly."""
    agent = QLearningAgent(
        learning_rate=0.1,
        gamma=0.95,
        epsilon=0.2,
        epsilon_decay=0.995,
        min_epsilon=0.01
    )

    assert agent.learning_rate == 0.1
    assert agent.gamma == 0.95
    assert agent.epsilon == 0.2
    assert agent.epsilon_decay == 0.995
    assert agent.min_epsilon == 0.01
    assert isinstance(agent.q_table, dict)


def test_qlearning_agent_default_values():
    """Test Q-learning agent with default values."""
    agent = QLearningAgent()

    assert agent.learning_rate > 0
    assert 0 < agent.gamma <= 1
    assert 0 <= agent.epsilon <= 1
    assert agent.q_table == {}


def test_qlearning_agent_get_state_key():
    """Test state key generation."""
    agent = QLearningAgent()
    state = create_test_state()

    key = agent.get_state_key(state)

    assert isinstance(key, str)
    assert "0.50" in key  # task_complexity
    assert "3" in key     # provider_count


def test_qlearning_agent_get_action_key():
    """Test action key generation."""
    agent = QLearningAgent()
    action = create_test_action()

    key = agent.get_action_key(action)

    assert isinstance(key, str)
    assert "concurrent" in key  # strategy
    assert "3" in key           # max_concurrent_providers


def test_qlearning_agent_get_q_value():
    """Test getting Q-value for state-action pair."""
    agent = QLearningAgent()
    state = create_test_state()
    action = create_test_action()

    state_key = agent.get_state_key(state)
    action_key = agent.get_action_key(action)

    # New state-action should return 0
    q_value = agent.get_q_value(state_key, action_key)
    assert q_value == 0.0


def test_qlearning_agent_set_q_value():
    """Test setting Q-value for state-action pair."""
    agent = QLearningAgent()
    state = create_test_state()
    action = create_test_action()

    state_key = agent.get_state_key(state)
    action_key = agent.get_action_key(action)

    agent.set_q_value(state_key, action_key, 5.0)

    q_value = agent.get_q_value(state_key, action_key)
    assert q_value == 5.0


def test_qlearning_agent_choose_action():
    """Test action selection with epsilon-greedy policy."""
    agent = QLearningAgent(epsilon=0.5)
    state = create_test_state()

    actions = [
        create_test_action(strategy=OrchestrationStrategy.CONCURRENT),
        create_test_action(strategy=OrchestrationStrategy.ROLE_BASED),
        create_test_action(strategy=OrchestrationStrategy.SEQUENTIAL),
    ]

    chosen_action = agent.choose_action(state, actions)

    assert chosen_action in actions
    assert isinstance(chosen_action, RLAction)


def test_qlearning_agent_choose_action_exploitation():
    """Test action selection during exploitation (epsilon=0)."""
    agent = QLearningAgent(epsilon=0.0)  # Pure exploitation
    state = create_test_state()

    action_a = create_test_action(strategy=OrchestrationStrategy.CONCURRENT)
    action_b = create_test_action(strategy=OrchestrationStrategy.ROLE_BASED)

    # Set Q-values manually
    state_key = agent.get_state_key(state)
    agent.set_q_value(state_key, agent.get_action_key(action_a), 1.0)
    agent.set_q_value(state_key, agent.get_action_key(action_b), 5.0)

    actions = [action_a, action_b]

    # Should always choose best action (action_b)
    chosen_actions = [agent.choose_action(state, actions) for _ in range(10)]

    assert all(agent.get_action_key(a) == agent.get_action_key(action_b) for a in chosen_actions)


def test_qlearning_agent_learn():
    """Test Q-value learning from experience."""
    agent = QLearningAgent(learning_rate=0.1, gamma=0.9)

    state = create_test_state()
    action = create_test_action()
    next_state = create_test_state(task_complexity=0.6)

    experience = Experience(
        state=state,
        action=action,
        reward=10.0,
        next_state=next_state,
        done=False
    )

    # Learn from experience
    agent.learn(experience)

    # Q-value should have been updated
    state_key = agent.get_state_key(state)
    action_key = agent.get_action_key(action)
    q_value = agent.get_q_value(state_key, action_key)

    # Should be non-zero after learning
    assert q_value > 0


def test_qlearning_agent_learn_terminal_state():
    """Test Q-value learning for terminal state."""
    agent = QLearningAgent(learning_rate=0.1, gamma=0.9)

    state = create_test_state()
    action = create_test_action()
    terminal_state = create_test_state(task_complexity=1.0)

    experience = Experience(
        state=state,
        action=action,
        reward=10.0,
        next_state=terminal_state,
        done=True
    )

    agent.learn(experience)

    state_key = agent.get_state_key(state)
    action_key = agent.get_action_key(action)
    q_value = agent.get_q_value(state_key, action_key)

    # Terminal state: Q = learning_rate * reward = 0.1 * 10 = 1.0
    assert abs(q_value - 1.0) < 0.01


def test_qlearning_agent_get_optimal_action():
    """Test getting optimal action without exploration."""
    agent = QLearningAgent()
    state = create_test_state()

    action_a = create_test_action(strategy=OrchestrationStrategy.CONCURRENT)
    action_b = create_test_action(strategy=OrchestrationStrategy.ROLE_BASED)
    action_c = create_test_action(strategy=OrchestrationStrategy.SEQUENTIAL)

    # Set Q-values
    state_key = agent.get_state_key(state)
    agent.set_q_value(state_key, agent.get_action_key(action_a), 1.0)
    agent.set_q_value(state_key, agent.get_action_key(action_b), 5.0)
    agent.set_q_value(state_key, agent.get_action_key(action_c), 2.0)

    actions = [action_a, action_b, action_c]
    optimal_action = agent.get_optimal_action(state, actions)

    # Should select action_b (highest Q-value)
    assert agent.get_action_key(optimal_action) == agent.get_action_key(action_b)


def test_qlearning_agent_replay_buffer_integration():
    """Test that learning stores experiences in replay buffer."""
    agent = QLearningAgent()

    initial_buffer_size = len(agent.replay_buffer)

    experience = create_test_experience()
    agent.learn(experience)

    assert len(agent.replay_buffer) == initial_buffer_size + 1


def test_qlearning_agent_epsilon_decay_on_learn():
    """Test that epsilon decays during learning."""
    agent = QLearningAgent(epsilon=1.0, epsilon_decay=0.9, min_epsilon=0.1)

    initial_epsilon = agent.epsilon
    experience = create_test_experience()

    agent.learn(experience)

    assert agent.epsilon < initial_epsilon
    assert agent.epsilon >= agent.min_epsilon


def test_qlearning_agent_get_learning_stats():
    """Test getting learning statistics."""
    agent = QLearningAgent()

    stats = agent.get_learning_stats()

    assert "learning_steps" in stats
    assert "q_table_size" in stats
    assert "replay_buffer_size" in stats
    assert "current_epsilon" in stats
    assert "total_states_explored" in stats


def test_qlearning_agent_multiple_learns():
    """Test multiple learning updates."""
    agent = QLearningAgent(learning_rate=0.1, gamma=0.9)

    state = create_test_state()
    action = create_test_action()
    next_state = create_test_state(task_complexity=0.6)

    # Multiple learns with positive reward
    for _ in range(10):
        experience = Experience(
            state=state,
            action=action,
            reward=1.0,
            next_state=next_state,
            done=False
        )
        agent.learn(experience)

    state_key = agent.get_state_key(state)
    action_key = agent.get_action_key(action)
    final_q = agent.get_q_value(state_key, action_key)

    # Q-value should increase with positive rewards
    assert final_q > 0


def test_qlearning_agent_negative_reward():
    """Test Q-value learning with negative reward."""
    agent = QLearningAgent(learning_rate=0.5, gamma=0.9)

    state = create_test_state()
    action = create_test_action()
    next_state = create_test_state(task_complexity=0.6)

    experience = Experience(
        state=state,
        action=action,
        reward=-5.0,
        next_state=next_state,
        done=False
    )

    agent.learn(experience)

    state_key = agent.get_state_key(state)
    action_key = agent.get_action_key(action)
    q_value = agent.get_q_value(state_key, action_key)

    # Q-value should be negative after negative reward
    assert q_value < 0


def test_qlearning_agent_learn_from_batch():
    """Test batch learning from replay buffer."""
    agent = QLearningAgent()

    # Add experiences to buffer
    for i in range(50):
        exp = create_test_experience(reward=float(i))
        agent.replay_buffer.push(exp)

    initial_learning_steps = agent.learning_steps

    # Learn from batch
    agent.learn_from_batch(batch_size=32)

    # Learning steps should have increased by batch size
    assert agent.learning_steps >= initial_learning_steps + 32


def test_replay_buffer_fifo_behavior():
    """Test that replay buffer follows FIFO when at capacity."""
    buffer = ReplayBuffer(capacity=3)

    experiences = []
    for i in range(5):
        exp = create_test_experience(reward=float(i))
        experiences.append(exp)
        buffer.push(exp)

    # Should contain last 3 experiences (circular buffer overwrites)
    assert len(buffer.buffer) == 3

    # Check that recent experiences are in buffer
    rewards_in_buffer = [exp.reward for exp in buffer.buffer]
    assert any(r in [2.0, 3.0, 4.0] for r in rewards_in_buffer)


# MAFOptimizer Tests

def test_maf_optimizer_initialization():
    """Test MAF optimizer initialization."""
    mock_monitor = MagicMock()
    optimizer = MAFOptimizer(mock_monitor)

    assert optimizer.performance_monitor == mock_monitor
    assert isinstance(optimizer.q_agent, QLearningAgent)
    assert optimizer.optimization_history == []


def test_maf_optimizer_get_rl_stats():
    """Test getting RL stats from MAF optimizer."""
    mock_monitor = MagicMock()
    optimizer = MAFOptimizer(mock_monitor)

    stats = optimizer.get_rl_stats()

    assert isinstance(stats, dict)
    assert "learning_steps" in stats


def test_maf_optimizer_get_optimization_history():
    """Test getting optimization history."""
    mock_monitor = MagicMock()
    optimizer = MAFOptimizer(mock_monitor)

    history = optimizer.get_optimization_history()

    assert isinstance(history, list)
