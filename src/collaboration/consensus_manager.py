"""
Consensus Manager for Multi-Agent Framework (MAF)

Implements weighted voting algorithms and conflict resolution strategies for multi-provider AI collaboration.
Provides consensus detection, agreement analysis, and decision making from multiple AI responses.
"""

import logging
import statistics
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from .message_models import CollaborationMessage, ConsensusSignal
from .provider_registry import ProviderInstance

logger = logging.getLogger(__name__)


class ConsensusStrategy(Enum):
    """Strategies for reaching consensus among providers."""

    WEIGHTED_VOTE = "weighted_vote"
    MAJORITY_VOTE = "majority_vote"
    EXPERT_CONSENSUS = "expert_consensus"
    CONFIDENCE_WEIGHTED = "confidence_weighted"


class ConflictResolution(Enum):
    """Strategies for resolving conflicts when consensus is not reached."""

    HIGHEST_WEIGHT = "highest_weight"
    MAJORITY_RULE = "majority_rule"
    MEDIAN_VALUE = "median_value"
    EXPERT_OVERRIDE = "expert_override"
    RANDOM_SELECTION = "random_selection"


@dataclass
class ConsensusResult:
    """Result of a consensus analysis."""

    is_consensus: bool
    confidence: float  # 0.0 to 1.0
    convergence_score: float  # 0.0 to 1.0
    agreement_indicators: List[str] = field(default_factory=list)
    disagreement_indicators: List[str] = field(default_factory=list)
    recommended_action: str = "continue"
    reasoning: str = ""
    winner_provider: Optional[str] = None
    consensus_value: Any = None


@dataclass
class VotingRound:
    """A single round of voting with results."""

    round_number: int
    votes: Dict[str, Any] = field(default_factory=dict)  # provider_id -> vote
    weights: Dict[str, float] = field(default_factory=dict)  # provider_id -> weight
    consensus_result: Optional[ConsensusResult] = None


class ConsensusManager:
    """
    Manages consensus detection and conflict resolution for multi-provider collaboration.

    Implements various voting algorithms and provides intelligent decision making
    when multiple AI providers have different opinions or outputs.
    """

    def __init__(
        self,
        strategy: ConsensusStrategy = ConsensusStrategy.WEIGHTED_VOTE,
        convergence_threshold: float = 0.6,
        min_agreement_ratio: float = 0.5,
    ):
        """
        Initialize consensus manager.

        Args:
            strategy: Default consensus strategy to use
            convergence_threshold: Minimum convergence score for consensus (0-1)
            min_agreement_ratio: Minimum ratio of providers that must agree
        """
        self.strategy = strategy
        self.convergence_threshold = convergence_threshold
        self.min_agreement_ratio = min_agreement_ratio

        self.voting_history: List[VotingRound] = []
        self.conflict_resolver = ConflictResolver()

        logger.info(f"ConsensusManager initialized with strategy: {strategy.value}")

    def analyze_round(self, messages: List[CollaborationMessage], round_number: int) -> ConsensusSignal:
        """
        Analyze a round of messages for consensus.

        Args:
            messages: Messages from this round
            round_number: Current round number

        Returns:
            ConsensusSignal with analysis results
        """
        # Group messages by provider
        provider_messages = {}
        for msg in messages:
            if msg.round_number == round_number:
                provider_id = msg.sender.value
                if provider_id not in provider_messages:
                    provider_messages[provider_id] = []
                provider_messages[provider_id].append(msg)

        # Extract votes/responses from messages
        votes = {}
        for provider_id, msgs in provider_messages.items():
            # For now, use the last message as the vote
            if msgs:
                votes[provider_id] = self._extract_vote_from_message(msgs[-1])

        # Create voting round
        voting_round = VotingRound(round_number=round_number, votes=votes)

        # Analyze for consensus
        consensus_result = self._analyze_consensus(votes, round_number)
        voting_round.consensus_result = consensus_result

        self.voting_history.append(voting_round)

        # Convert to ConsensusSignal
        signal = ConsensusSignal(
            is_consensus=consensus_result.is_consensus,
            confidence=consensus_result.confidence,
            convergence_score=consensus_result.convergence_score,
            agreement_indicators=consensus_result.agreement_indicators,
            disagreement_indicators=consensus_result.disagreement_indicators,
            recommendation=consensus_result.recommended_action,
            reasoning=consensus_result.reasoning,
        )

        logger.info(
            f"Round {round_number} consensus: {signal.is_consensus} "
            f"(confidence: {signal.confidence:.2f}, convergence: {signal.convergence_score:.2f})"
        )

        return signal

    def _extract_vote_from_message(self, message: CollaborationMessage) -> Any:
        """
        Extract the 'vote' or decision from a collaboration message.

        This is a simplified implementation - in practice, this would need
        to parse the message content for specific voting patterns.
        """
        # For now, return the message content as the vote
        # In a real implementation, this would parse for specific vote formats
        return message.content

    def _analyze_consensus(self, votes: Dict[str, Any], round_number: int) -> ConsensusResult:
        """
        Analyze votes for consensus using the configured strategy.

        Args:
            votes: Dictionary of provider_id -> vote
            round_number: Current round number

        Returns:
            ConsensusResult with analysis
        """
        if len(votes) < 2:
            return ConsensusResult(
                is_consensus=False,
                confidence=0.0,
                convergence_score=0.0,
                recommended_action="continue",
                reasoning="Need at least 2 providers for consensus",
            )

        if self.strategy == ConsensusStrategy.WEIGHTED_VOTE:
            return self._weighted_vote_consensus(votes, round_number)
        elif self.strategy == ConsensusStrategy.MAJORITY_VOTE:
            return self._majority_vote_consensus(votes, round_number)
        elif self.strategy == ConsensusStrategy.EXPERT_CONSENSUS:
            return self._expert_consensus(votes, round_number)
        elif self.strategy == ConsensusStrategy.CONFIDENCE_WEIGHTED:
            return self._confidence_weighted_consensus(votes, round_number)
        else:
            return self._weighted_vote_consensus(votes, round_number)

    def _weighted_vote_consensus(self, votes: Dict[str, Any], round_number: int) -> ConsensusResult:
        """
        Weighted voting consensus - each provider has a weight based on reliability.
        """
        # For now, assume equal weights - in practice, weights would come from provider metadata
        weights = {provider_id: 1.0 for provider_id in votes.keys()}

        # Count votes for each unique response
        vote_counts = {}
        weighted_counts = {}

        for provider_id, vote in votes.items():
            weight = weights[provider_id]
            vote_key = str(vote)  # Convert to string for comparison

            if vote_key not in vote_counts:
                vote_counts[vote_key] = 0
                weighted_counts[vote_key] = 0.0

            vote_counts[vote_key] += 1
            weighted_counts[vote_key] += weight

        # Find the winning vote
        winning_vote = max(weighted_counts.items(), key=lambda x: x[1])
        winning_value, winning_weight = winning_vote

        total_weight = sum(weights.values())
        agreement_ratio = winning_weight / total_weight

        # Calculate convergence score
        if len(vote_counts) == 1:
            convergence_score = 1.0  # Perfect agreement
        else:
            # Measure how concentrated the votes are
            weights_list = list(weighted_counts.values())
            if len(weights_list) > 1:
                convergence_score = winning_weight / sum(weights_list)
            else:
                convergence_score = 1.0

        # Determine if consensus reached
        is_consensus = agreement_ratio >= self.min_agreement_ratio and convergence_score >= self.convergence_threshold

        # Create agreement/disagreement indicators
        agreement_indicators = []
        disagreement_indicators = []

        if is_consensus:
            agreement_indicators.append(f"{agreement_ratio:.1%} agreement on winning choice")
        else:
            disagreement_indicators.append(f"Only {agreement_ratio:.1%} agreement, need {self.min_agreement_ratio:.1%}")

        if convergence_score < self.convergence_threshold:
            disagreement_indicators.append(
                f"Convergence score {convergence_score:.2f} below threshold {self.convergence_threshold}"
            )

        # Determine recommended action
        if is_consensus:
            recommended_action = "FINALIZE"
            reasoning = f"Consensus reached with {agreement_ratio:.1%} agreement"
        elif round_number >= 5:  # Max rounds
            recommended_action = "FINALIZE"
            reasoning = "Maximum rounds reached, finalizing with best available consensus"
        else:
            recommended_action = "CONTINUE"
            reasoning = "Need more discussion to reach consensus"

        return ConsensusResult(
            is_consensus=is_consensus,
            confidence=min(agreement_ratio, convergence_score),
            convergence_score=convergence_score,
            agreement_indicators=agreement_indicators,
            disagreement_indicators=disagreement_indicators,
            recommended_action=recommended_action,
            reasoning=reasoning,
            consensus_value=winning_value,
        )

    def _majority_vote_consensus(self, votes: Dict[str, Any], round_number: int) -> ConsensusResult:
        """
        Simple majority vote consensus.
        """
        # Count votes
        vote_counts = {}
        for vote in votes.values():
            vote_key = str(vote)
            vote_counts[vote_key] = vote_counts.get(vote_key, 0) + 1

        total_votes = len(votes)
        winning_vote, winning_count = max(vote_counts.items(), key=lambda x: x[1])
        agreement_ratio = winning_count / total_votes

        # Simple majority
        is_consensus = agreement_ratio > 0.5

        convergence_score = agreement_ratio

        agreement_indicators = [f"Majority vote: {winning_count}/{total_votes}"]
        disagreement_indicators = []

        if not is_consensus:
            disagreement_indicators.append("No majority achieved")

        recommended_action = "FINALIZE" if is_consensus else "CONTINUE"
        reasoning = f"Majority vote result: {agreement_ratio:.1%} agreement"

        return ConsensusResult(
            is_consensus=is_consensus,
            confidence=agreement_ratio,
            convergence_score=convergence_score,
            agreement_indicators=agreement_indicators,
            disagreement_indicators=disagreement_indicators,
            recommended_action=recommended_action,
            reasoning=reasoning,
            consensus_value=winning_vote,
        )

    def _expert_consensus(self, votes: Dict[str, Any], round_number: int) -> ConsensusResult:
        """
        Expert consensus - prioritize providers with higher reliability scores.
        """
        # For now, assume equal expertise - in practice, use provider metadata
        return self._weighted_vote_consensus(votes, round_number)

    def _confidence_weighted_consensus(self, votes: Dict[str, Any], round_number: int) -> ConsensusResult:
        """
        Weight votes by provider confidence scores.
        """
        # For now, assume equal confidence - in practice, extract from message metadata
        return self._weighted_vote_consensus(votes, round_number)

    def resolve_conflict(
        self, votes: Dict[str, Any], strategy: ConflictResolution = ConflictResolution.HIGHEST_WEIGHT
    ) -> Any:
        """
        Resolve conflicts when consensus cannot be reached.

        Args:
            votes: Provider votes
            strategy: Conflict resolution strategy

        Returns:
            Resolved value
        """
        return self.conflict_resolver.resolve(votes, strategy)


class ConflictResolver:
    """
    Handles conflict resolution when providers disagree.
    """

    def resolve(
        self, votes: Dict[str, Any], strategy: ConflictResolution, weights: Optional[Dict[str, float]] = None
    ) -> Any:
        """
        Resolve conflicts using the specified strategy.

        Args:
            votes: Provider votes
            strategy: Resolution strategy
            weights: Optional provider weights

        Returns:
            Resolved value
        """
        if not votes:
            return None

        if len(votes) == 1:
            return list(votes.values())[0]

        if strategy == ConflictResolution.HIGHEST_WEIGHT:
            return self._highest_weight_resolution(votes, weights)
        elif strategy == ConflictResolution.MAJORITY_RULE:
            return self._majority_resolution(votes)
        elif strategy == ConflictResolution.MEDIAN_VALUE:
            return self._median_resolution(votes)
        elif strategy == ConflictResolution.EXPERT_OVERRIDE:
            return self._expert_override_resolution(votes, weights)
        elif strategy == ConflictResolution.RANDOM_SELECTION:
            return self._random_resolution(votes)
        else:
            return self._highest_weight_resolution(votes, weights)

    def _highest_weight_resolution(self, votes: Dict[str, Any], weights: Optional[Dict[str, float]]) -> Any:
        """Select the vote from the highest weighted provider."""
        if not weights:
            # Default equal weights
            weights = {provider_id: 1.0 for provider_id in votes.keys()}

        # Find provider with highest weight
        best_provider = max(weights.items(), key=lambda x: x[1])[0]
        return votes.get(best_provider)

    def _majority_resolution(self, votes: Dict[str, Any]) -> Any:
        """Select the most common vote."""
        vote_counts = {}
        for vote in votes.values():
            vote_key = str(vote)
            vote_counts[vote_key] = vote_counts.get(vote_key, 0) + 1

        winning_vote = max(vote_counts.items(), key=lambda x: x[1])[0]
        return winning_vote

    def _median_resolution(self, votes: Dict[str, Any]) -> Any:
        """Select the median vote (for numerical values)."""
        try:
            # Try to convert to numbers
            numerical_votes = []
            for vote in votes.values():
                try:
                    numerical_votes.append(float(vote))
                except (ValueError, TypeError):
                    continue

            if numerical_votes:
                return statistics.median(numerical_votes)
        except:
            pass

        # Fallback to majority
        return self._majority_resolution(votes)

    def _expert_override_resolution(self, votes: Dict[str, Any], weights: Optional[Dict[str, float]]) -> Any:
        """Use expert weighting to select the best vote."""
        return self._highest_weight_resolution(votes, weights)

    def _random_resolution(self, votes: Dict[str, Any]) -> Any:
        """Randomly select one of the votes."""
        import random

        return random.choice(list(votes.values()))
