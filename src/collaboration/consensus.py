"""
Consensus detector for analyzing agreement and convergence between agents.
"""

import re
from typing import List, Set
import logging

from src.collaboration.message_models import (
    CollaborationMessage,
    ConsensusSignal
)

logger = logging.getLogger(__name__)


class ConsensusDetector:
    """Detects agreement, disagreement, and convergence between agents."""

    # Agreement indicators (case-insensitive)
    AGREEMENT_PATTERNS = [
        r'\bI agree\b',
        r'\bsounds good\b',
        r'\bI align with\b',
        r'\bI concur\b',
        r'\blets proceed\b',
        r'\blet\'s go with\b',
        r'\bI support\b',
        r'\bgood point\b',
        r'\bI like this approach\b',
        r'\bthis makes sense\b',
        r'\bI\'m on board\b'
    ]

    # Disagreement indicators
    DISAGREEMENT_PATTERNS = [
        r'\bI disagree\b',
        r'\bhowever,\b',
        r'\bbut I think\b',
        r'\balternatively\b',
        r'\bI would suggest\b',
        r'\binstead of\b',
        r'\bI have concerns\b',
        r'\bnot sure about\b',
        r'\bmight be better to\b'
    ]

    # Convergence threshold (0-1, lower = more strict)
    CONVERGENCE_THRESHOLD = 0.6

    def __init__(self, convergence_threshold: float = 0.6):
        """
        Initialize consensus detector.

        Args:
            convergence_threshold: Minimum convergence score for consensus (0-1)
        """
        self.convergence_threshold = convergence_threshold

        # Compile patterns for efficiency
        self.agreement_regex = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in self.AGREEMENT_PATTERNS
        ]
        self.disagreement_regex = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in self.DISAGREEMENT_PATTERNS
        ]

        logger.info(f"ConsensusDetector initialized (threshold: {convergence_threshold})")

    def analyze_round(
        self,
        messages: List[CollaborationMessage],
        round_number: int
    ) -> ConsensusSignal:
        """
        Analyze messages from a specific round for consensus.

        Args:
            messages: All messages from the conversation
            round_number: Which round to analyze

        Returns:
            ConsensusSignal with recommendation
        """
        # Filter messages for this round
        round_messages = [m for m in messages if m.round_number == round_number]

        if len(round_messages) < 2:
            return ConsensusSignal(
                is_consensus=False,
                confidence=0.0,
                convergence_score=0.0,
                recommendation="CONTINUE",
                reasoning="Waiting for both agents to respond"
            )

        # Extract agreement/disagreement indicators
        agreement_found = []
        disagreement_found = []

        for msg in round_messages:
            agreement_found.extend(self._find_patterns(msg.content, self.agreement_regex))
            disagreement_found.extend(self._find_patterns(msg.content, self.disagreement_regex))

        # Calculate convergence score (simple keyword overlap)
        convergence = self._calculate_convergence(round_messages)

        # Determine if consensus reached
        has_agreement = len(agreement_found) >= 2  # Both agents signal agreement
        has_no_disagreement = len(disagreement_found) == 0
        high_convergence = convergence >= self.convergence_threshold

        is_consensus = has_agreement and has_no_disagreement and high_convergence
        confidence = self._calculate_confidence(
            len(agreement_found),
            len(disagreement_found),
            convergence
        )

        # Generate recommendation
        if is_consensus:
            recommendation = "FINALIZE"
            reasoning = f"Both agents show agreement ({len(agreement_found)} signals), no conflicts, {convergence:.2f} convergence"
        elif round_number >= 5:
            recommendation = "FINALIZE"
            reasoning = f"Max rounds reached (5/5). Convergence: {convergence:.2f}"
        elif len(disagreement_found) > 3:
            recommendation = "MEDIATE"
            reasoning = f"Multiple disagreements detected ({len(disagreement_found)} signals). Manual review suggested"
        else:
            recommendation = "CONTINUE"
            reasoning = f"Partial agreement. Convergence: {convergence:.2f}. Continue discussion"

        logger.info(
            f"Round {round_number} analysis: {recommendation} "
            f"(consensus: {is_consensus}, confidence: {confidence:.2f}, "
            f"convergence: {convergence:.2f})"
        )

        return ConsensusSignal(
            is_consensus=is_consensus,
            confidence=confidence,
            agreement_indicators=agreement_found,
            disagreement_indicators=disagreement_found,
            convergence_score=convergence,
            recommendation=recommendation,
            reasoning=reasoning
        )

    def _find_patterns(self, text: str, patterns: List[re.Pattern]) -> List[str]:
        """Find all pattern matches in text."""
        matches = []
        for pattern in patterns:
            found = pattern.findall(text)
            matches.extend(found)
        return matches

    def _calculate_convergence(self, messages: List[CollaborationMessage]) -> float:
        """
        Calculate semantic convergence between messages.

        Simple implementation: Keyword overlap / union (Jaccard similarity).
        Production: Use sentence-transformers for cosine similarity.

        Args:
            messages: Messages to compare

        Returns:
            Convergence score (0-1)
        """
        if len(messages) < 2:
            return 0.0

        # Extract keywords (simple tokenization)
        def get_keywords(text: str) -> Set[str]:
            # Remove markdown, lowercase, split on non-alphanumeric
            clean = re.sub(r'[#*`]', '', text.lower())
            words = re.findall(r'\b\w{4,}\b', clean)  # 4+ char words only
            return set(words)

        keyword_sets = [get_keywords(msg.content) for msg in messages]

        # Calculate Jaccard similarity (intersection / union)
        intersection = set.intersection(*keyword_sets)
        union = set.union(*keyword_sets)

        if not union:
            return 0.0

        return len(intersection) / len(union)

    def _calculate_confidence(
        self,
        agreement_count: int,
        disagreement_count: int,
        convergence: float
    ) -> float:
        """
        Calculate confidence score (0-1).

        Weighted average of three factors:
        - Agreement signals (40%)
        - Lack of disagreement (30%)
        - Convergence score (30%)

        Args:
            agreement_count: Number of agreement indicators found
            disagreement_count: Number of disagreement indicators found
            convergence: Convergence score (0-1)

        Returns:
            Confidence score (0-1)
        """
        # Weighted average of three factors
        agreement_score = min(agreement_count / 4.0, 1.0)  # Cap at 4 signals
        disagreement_penalty = max(1.0 - (disagreement_count / 4.0), 0.0)

        confidence = (
            0.4 * agreement_score +
            0.3 * disagreement_penalty +
            0.3 * convergence
        )

        return max(0.0, min(1.0, confidence))
