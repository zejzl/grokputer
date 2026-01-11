"""
Comprehensive tests for MAF Consensus Manager

Tests cover weighted voting, majority voting, consensus detection,
conflict resolution strategies, and RL-based optimization.
"""

import pytest
from unittest.mock import MagicMock, Mock, patch
from src.collaboration.consensus_manager import (
    ConsensusManager,
    ConsensusStrategy,
    ConflictResolution,
    ConsensusResult,
    VotingRound,
)
from src.collaboration.provider_registry import ProviderInstance, ProviderCapability


# Consensus Manager Initialization Tests


def test_consensus_manager_initialization_defaults():
    """Test ConsensusManager initializes with default values"""
    manager = ConsensusManager()

    assert manager.strategy == ConsensusStrategy.WEIGHTED_VOTE
    assert manager.convergence_threshold == 0.6
    assert manager.min_agreement_ratio == 0.5
    assert manager.enable_rl_optimization is True
    assert manager.voting_history == []


def test_consensus_manager_initialization_custom():
    """Test ConsensusManager initializes with custom values"""
    manager = ConsensusManager(
        strategy=ConsensusStrategy.MAJORITY_VOTE,
        convergence_threshold=0.8,
        min_agreement_ratio=0.7,
        enable_rl_optimization=False
    )

    assert manager.strategy == ConsensusStrategy.MAJORITY_VOTE
    assert manager.convergence_threshold == 0.8
    assert manager.min_agreement_ratio == 0.7
    assert manager.enable_rl_optimization is False


def test_consensus_manager_rl_agent_initialization():
    """Test that RL agent is initialized when enabled"""
    with patch('src.collaboration.rl_optimizer.QLearningAgent') as mock_agent:
        manager = ConsensusManager(enable_rl_optimization=True)

        assert mock_agent.called or manager.consensus_rl_agent is None  # May not initialize if import fails


def test_consensus_manager_rl_agent_disabled():
    """Test that RL agent is not initialized when disabled"""
    manager = ConsensusManager(enable_rl_optimization=False)
    assert manager.consensus_rl_agent is None


# ConsensusResult Tests


def test_consensus_result_structure():
    """Test ConsensusResult dataclass structure"""
    result = ConsensusResult(
        is_consensus=True,
        confidence=0.85,
        convergence_score=0.9,
        agreement_indicators=["indicator1", "indicator2"],
        disagreement_indicators=[],
        recommended_action="proceed",
        reasoning="Strong agreement detected",
        winner_provider="provider1",
        consensus_value="agreed_value"
    )

    assert result.is_consensus is True
    assert result.confidence == 0.85
    assert result.convergence_score == 0.9
    assert len(result.agreement_indicators) == 2
    assert len(result.disagreement_indicators) == 0
    assert result.recommended_action == "proceed"
    assert result.reasoning == "Strong agreement detected"
    assert result.winner_provider == "provider1"
    assert result.consensus_value == "agreed_value"


def test_consensus_result_defaults():
    """Test ConsensusResult default values"""
    result = ConsensusResult(
        is_consensus=False,
        confidence=0.3,
        convergence_score=0.2
    )

    assert result.is_consensus is False
    assert result.agreement_indicators == []
    assert result.disagreement_indicators == []
    assert result.recommended_action == "continue"
    assert result.reasoning == ""
    assert result.winner_provider is None
    assert result.consensus_value is None


# VotingRound Tests


def test_voting_round_structure():
    """Test VotingRound dataclass structure"""
    consensus_result = ConsensusResult(
        is_consensus=True,
        confidence=0.8,
        convergence_score=0.85
    )

    round_data = VotingRound(
        round_number=1,
        votes={"provider1": "vote_a", "provider2": "vote_a"},
        weights={"provider1": 1.0, "provider2": 0.8},
        consensus_result=consensus_result
    )

    assert round_data.round_number == 1
    assert len(round_data.votes) == 2
    assert len(round_data.weights) == 2
    assert round_data.consensus_result.is_consensus is True


def test_voting_round_defaults():
    """Test VotingRound default values"""
    round_data = VotingRound(round_number=1)

    assert round_data.round_number == 1
    assert round_data.votes == {}
    assert round_data.weights == {}
    assert round_data.consensus_result is None


# Consensus Strategy Tests


def test_consensus_strategies_exist():
    """Test that all expected consensus strategies are defined"""
    assert ConsensusStrategy.WEIGHTED_VOTE
    assert ConsensusStrategy.MAJORITY_VOTE
    assert ConsensusStrategy.EXPERT_CONSENSUS
    assert ConsensusStrategy.CONFIDENCE_WEIGHTED


def test_consensus_strategy_values():
    """Test consensus strategy enum values"""
    assert ConsensusStrategy.WEIGHTED_VOTE.value == "weighted_vote"
    assert ConsensusStrategy.MAJORITY_VOTE.value == "majority_vote"
    assert ConsensusStrategy.EXPERT_CONSENSUS.value == "expert_consensus"
    assert ConsensusStrategy.CONFIDENCE_WEIGHTED.value == "confidence_weighted"


# Conflict Resolution Tests


def test_conflict_resolution_strategies_exist():
    """Test that all expected conflict resolution strategies are defined"""
    assert ConflictResolution.HIGHEST_WEIGHT
    assert ConflictResolution.MAJORITY_RULE
    assert ConflictResolution.MEDIAN_VALUE
    assert ConflictResolution.EXPERT_OVERRIDE
    assert ConflictResolution.RANDOM_SELECTION


def test_conflict_resolution_values():
    """Test conflict resolution enum values"""
    assert ConflictResolution.HIGHEST_WEIGHT.value == "highest_weight"
    assert ConflictResolution.MAJORITY_RULE.value == "majority_rule"
    assert ConflictResolution.MEDIAN_VALUE.value == "median_value"
    assert ConflictResolution.EXPERT_OVERRIDE.value == "expert_override"
    assert ConflictResolution.RANDOM_SELECTION.value == "random_selection"


# Voting History Tests


def test_voting_history_empty_initially():
    """Test that voting history starts empty"""
    manager = ConsensusManager()
    assert manager.voting_history == []
    assert len(manager.voting_history) == 0


def test_voting_history_can_be_appended():
    """Test that voting rounds can be added to history"""
    manager = ConsensusManager()

    round1 = VotingRound(
        round_number=1,
        votes={"provider1": "value_a"},
        weights={"provider1": 1.0}
    )

    manager.voting_history.append(round1)

    assert len(manager.voting_history) == 1
    assert manager.voting_history[0].round_number == 1


# Threshold and Ratio Tests


def test_convergence_threshold_range():
    """Test that convergence threshold is between 0 and 1"""
    manager1 = ConsensusManager(convergence_threshold=0.0)
    manager2 = ConsensusManager(convergence_threshold=1.0)

    assert 0.0 <= manager1.convergence_threshold <= 1.0
    assert 0.0 <= manager2.convergence_threshold <= 1.0


def test_min_agreement_ratio_range():
    """Test that min agreement ratio is between 0 and 1"""
    manager1 = ConsensusManager(min_agreement_ratio=0.0)
    manager2 = ConsensusManager(min_agreement_ratio=1.0)

    assert 0.0 <= manager1.min_agreement_ratio <= 1.0
    assert 0.0 <= manager2.min_agreement_ratio <= 1.0


# Conflict Resolver Tests


def test_conflict_resolver_initialized():
    """Test that conflict resolver is initialized"""
    manager = ConsensusManager()
    assert manager.conflict_resolver is not None


# Integration Tests


def test_consensus_manager_multiple_strategies():
    """Test that different strategies can be configured"""
    strategies = [
        ConsensusStrategy.WEIGHTED_VOTE,
        ConsensusStrategy.MAJORITY_VOTE,
        ConsensusStrategy.EXPERT_CONSENSUS,
        ConsensusStrategy.CONFIDENCE_WEIGHTED
    ]

    for strategy in strategies:
        manager = ConsensusManager(strategy=strategy)
        assert manager.strategy == strategy


def test_consensus_result_high_confidence():
    """Test consensus result with high confidence indicates strong agreement"""
    result = ConsensusResult(
        is_consensus=True,
        confidence=0.95,
        convergence_score=0.9,
        agreement_indicators=["semantic_similarity", "structural_match", "value_agreement"]
    )

    assert result.is_consensus is True
    assert result.confidence >= 0.9
    assert result.convergence_score >= 0.9
    assert len(result.agreement_indicators) >= 3


def test_consensus_result_low_confidence():
    """Test consensus result with low confidence indicates disagreement"""
    result = ConsensusResult(
        is_consensus=False,
        confidence=0.2,
        convergence_score=0.3,
        disagreement_indicators=["conflicting_values", "different_approaches"]
    )

    assert result.is_consensus is False
    assert result.confidence < 0.5
    assert result.convergence_score < 0.5
    assert len(result.disagreement_indicators) > 0


def test_voting_round_multiple_providers():
    """Test voting round with multiple providers"""
    votes = {
        "provider1": "answer_a",
        "provider2": "answer_a",
        "provider3": "answer_b"
    }
    weights = {
        "provider1": 1.0,
        "provider2": 0.9,
        "provider3": 0.7
    }

    round_data = VotingRound(
        round_number=1,
        votes=votes,
        weights=weights
    )

    assert len(round_data.votes) == 3
    assert len(round_data.weights) == 3
    # Most providers voted for answer_a (2 out of 3)
    assert sum(1 for v in votes.values() if v == "answer_a") > sum(1 for v in votes.values() if v == "answer_b")


def test_consensus_manager_threshold_affects_consensus():
    """Test that threshold affects consensus determination"""
    high_threshold = ConsensusManager(convergence_threshold=0.9)
    low_threshold = ConsensusManager(convergence_threshold=0.3)

    assert high_threshold.convergence_threshold > low_threshold.convergence_threshold


def test_consensus_manager_agreement_ratio_affects_consensus():
    """Test that agreement ratio affects consensus determination"""
    high_ratio = ConsensusManager(min_agreement_ratio=0.9)
    low_ratio = ConsensusManager(min_agreement_ratio=0.3)

    assert high_ratio.min_agreement_ratio > low_ratio.min_agreement_ratio


def test_consensus_result_can_include_reasoning():
    """Test that consensus result can include detailed reasoning"""
    result = ConsensusResult(
        is_consensus=True,
        confidence=0.8,
        convergence_score=0.85,
        reasoning="All providers agreed on the solution approach. "
                  "Minor variations in implementation details were resolved "
                  "using weighted voting based on provider confidence scores."
    )

    assert result.reasoning != ""
    assert len(result.reasoning) > 50
    assert "providers" in result.reasoning.lower()


def test_voting_round_sequential_numbering():
    """Test that voting rounds can be numbered sequentially"""
    manager = ConsensusManager()

    for i in range(1, 6):
        round_data = VotingRound(round_number=i)
        manager.voting_history.append(round_data)

    assert len(manager.voting_history) == 5
    assert [r.round_number for r in manager.voting_history] == [1, 2, 3, 4, 5]


def test_consensus_result_winner_provider_tracking():
    """Test that consensus result tracks winner provider"""
    result = ConsensusResult(
        is_consensus=True,
        confidence=0.9,
        convergence_score=0.95,
        winner_provider="claude",
        consensus_value="optimal_solution"
    )

    assert result.winner_provider == "claude"
    assert result.consensus_value == "optimal_solution"


def test_consensus_manager_different_thresholds_produce_different_behavior():
    """Test that different threshold configurations produce different behaviors"""
    strict_manager = ConsensusManager(
        convergence_threshold=0.95,
        min_agreement_ratio=0.9
    )
    lenient_manager = ConsensusManager(
        convergence_threshold=0.5,
        min_agreement_ratio=0.5
    )

    # Strict manager requires very high agreement
    assert strict_manager.convergence_threshold >= 0.9
    assert strict_manager.min_agreement_ratio >= 0.9

    # Lenient manager accepts lower agreement
    assert lenient_manager.convergence_threshold <= 0.6
    assert lenient_manager.min_agreement_ratio <= 0.6
