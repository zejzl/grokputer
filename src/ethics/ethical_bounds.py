#!/usr/bin/env python3
"""
Ethical Learning Bounds - Defines boundaries for autonomous creative development
Prevents harmful learning patterns and ensures responsible AI development
"""

import logging
from typing import Dict, List, Set, Optional, Tuple
from datetime import datetime
import re

logger = logging.getLogger(__name__)


class EthicalBounds:
    """
    Defines ethical boundaries for AI learning and creative generation.
    Prevents harmful patterns while allowing beneficial development.
    """

    # Forbidden content categories
    FORBIDDEN_THEMES = {
        "violence": [
            "graphic_violence",
            "torture",
            "murder_methods",
            "weapon_manufacture",
            "terrorism",
            "hate_crimes",
            "domestic_abuse",
        ],
        "harm": [
            "self_harm",
            "suicide_methods",
            "eating_disorders",
            "substance_abuse",
            "dangerous_challenges",
            "pranks_with_risk",
        ],
        "exploitation": ["child_exploitation", "sexual_abuse", "human_trafficking", "forced_labor", "animal_cruelty"],
        "discrimination": [
            "racial_slurs",
            "hate_speech",
            "gender_discrimination",
            "religious_intolerance",
            "xenophobia",
        ],
        "illegal": [
            "drug_manufacture",
            "fraud_methods",
            "identity_theft",
            "copyright_infringement",
            "illegal_activities",
        ],
        "privacy": ["personal_data_exposure", "doxxing", "surveillance_methods", "privacy_violation"],
    }

    # Restricted archetypes and character types
    RESTRICTED_ARCHETYPES = {
        "dangerous_leaders": ["dictator", "tyrant", "oppressive_ruler"],
        "harmful_mentors": ["manipulative_teacher", "abusive_parent"],
        "predatory_characters": ["stalker", "predator", "abuser"],
        "destructive_heroes": ["anti-hero_with_no_redeemable_qualities"],
    }

    # Required positive elements for balance
    REQUIRED_POSITIVE_ELEMENTS = [
        "redemption_arc",
        "learning_from_mistakes",
        "positive_relationships",
        "ethical_decisions",
        "personal_growth",
        "community_benefit",
    ]

    # Learning boundaries
    MAX_LEARNING_PATTERNS = 1000
    LEARNING_COOLDOWN_HOURS = 24
    PATTERN_SIMILARITY_THRESHOLD = 0.85

    def __init__(self):
        self.learned_patterns: Set[str] = set()
        self.blocked_patterns: Set[str] = set()
        self.learning_history: List[Dict] = []
        self.violation_count = 0

        # Initialize with known harmful patterns
        self._initialize_forbidden_patterns()

    def _initialize_forbidden_patterns(self):
        """Initialize database of forbidden learning patterns."""
        self.blocked_patterns.update(
            [
                # Violence patterns
                "how to make explosives",
                "best ways to hurt someone",
                "torture techniques",
                # Harm patterns
                "how to self-harm",
                "suicide methods",
                "eating disorder tips",
                # Exploitation patterns
                "how to exploit children",
                "abuse techniques",
                "trafficking methods",
                # Illegal patterns
                "how to make drugs",
                "fraud schemes",
                "hacking tutorials",
                # Discriminatory patterns
                "racial slurs",
                "hate speech",
                "discriminatory stereotypes",
            ]
        )

    def validate_content_generation(self, content: str, content_type: str = "story") -> Dict:
        """
        Validate content for ethical compliance.

        Args:
            content: Content to validate
            content_type: Type of content (story, character, etc.)

        Returns:
            Validation result with compliance status and issues
        """
        validation = {
            "compliant": True,
            "issues": [],
            "warnings": [],
            "recommendations": [],
            "severity_score": 0,  # 0-100, higher = more severe
        }

        content_lower = content.lower()

        # Check forbidden themes
        for category, patterns in self.FORBIDDEN_THEMES.items():
            for pattern in patterns:
                if self._contains_forbidden_pattern(content_lower, pattern):
                    validation["compliant"] = False
                    validation["issues"].append(f"forbidden_{category}_{pattern}")
                    validation["severity_score"] += 50

        # Check restricted archetypes
        if content_type == "character":
            for archetype_category, archetypes in self.RESTRICTED_ARCHETYPES.items():
                for archetype in archetypes:
                    if archetype.lower() in content_lower:
                        validation["compliant"] = False
                        validation["issues"].append(f"restricted_archetype_{archetype}")
                        validation["severity_score"] += 30

        # Check for required positive elements
        positive_elements_found = 0
        for element in self.REQUIRED_POSITIVE_ELEMENTS:
            if element.replace("_", " ") in content_lower:
                positive_elements_found += 1

        if positive_elements_found == 0 and len(content) > 500:
            validation["warnings"].append("missing_positive_elements")
            validation["recommendations"].append("Add positive character development or ethical themes")

        # Check for pattern learning violations
        if self._is_pattern_violation(content):
            validation["compliant"] = False
            validation["issues"].append("pattern_learning_violation")
            validation["severity_score"] += 40

        # Severity assessment
        if validation["severity_score"] >= 100:
            validation["compliant"] = False
            validation["recommendations"].append("Content requires complete rewrite")
        elif validation["severity_score"] >= 50:
            validation["recommendations"].append("Significant content modifications required")

        return validation

    def validate_learning_pattern(self, pattern: str, context: str = "") -> bool:
        """
        Validate if a pattern can be learned ethically.

        Args:
            pattern: Pattern to validate
            context: Learning context

        Returns:
            True if pattern can be learned, False otherwise
        """
        pattern_lower = pattern.lower()

        # Check against blocked patterns
        if pattern_lower in self.blocked_patterns:
            logger.warning(f"Blocked pattern detected: {pattern}")
            return False

        # Check for similarity to blocked patterns
        for blocked in self.blocked_patterns:
            if self._calculate_similarity(pattern_lower, blocked) > self.PATTERN_SIMILARITY_THRESHOLD:
                logger.warning(f"Similar to blocked pattern '{blocked}': {pattern}")
                return False

        # Check learning rate limits
        if len(self.learned_patterns) >= self.MAX_LEARNING_PATTERNS:
            logger.warning("Learning pattern limit reached")
            return False

        # Check cooldown period
        if self._is_learning_cooldown_active():
            logger.warning("Learning cooldown active")
            return False

        return True

    def record_learning_event(self, pattern: str, source: str, ethical_score: int):
        """Record a learning event for monitoring."""
        event = {
            "timestamp": datetime.now(),
            "pattern": pattern,
            "source": source,
            "ethical_score": ethical_score,
            "compliant": ethical_score >= 70,
        }

        self.learning_history.append(event)

        # Keep only recent history
        if len(self.learning_history) > 500:
            self.learning_history.pop(0)

        if not event["compliant"]:
            self.violation_count += 1

    def get_ethical_report(self) -> Dict:
        """Generate comprehensive ethical compliance report."""
        total_learnings = len(self.learning_history)
        compliant_learnings = sum(1 for h in self.learning_history if h["compliant"])

        return {
            "total_learning_events": total_learnings,
            "compliant_learnings": compliant_learnings,
            "compliance_rate": compliant_learnings / total_learnings if total_learnings > 0 else 1.0,
            "violation_count": self.violation_count,
            "blocked_patterns_count": len(self.blocked_patterns),
            "learned_patterns_count": len(self.learned_patterns),
            "recent_violations": [h for h in self.learning_history[-10:] if not h["compliant"]],
        }

    def _contains_forbidden_pattern(self, content: str, pattern: str) -> bool:
        """Check if content contains forbidden patterns."""
        # Use regex for more flexible matching
        pattern_regex = re.compile(r"\b" + re.escape(pattern.replace("_", " ")) + r"\b", re.IGNORECASE)
        return bool(pattern_regex.search(content))

    def _is_pattern_violation(self, content: str) -> bool:
        """Check if content violates learned pattern boundaries."""
        # This would implement more sophisticated pattern analysis
        # For now, check for repeated harmful themes
        harmful_indicators = ["harm", "abuse", "violence", "exploit"]
        indicator_count = sum(1 for indicator in harmful_indicators if indicator in content.lower())

        return indicator_count >= 3  # Too many harmful indicators

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple text similarity."""
        words1 = set(text1.split())
        words2 = set(text2.split())

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        return len(intersection) / len(union) if union else 0.0

    def _is_learning_cooldown_active(self) -> bool:
        """Check if learning cooldown is active."""
        if not self.learning_history:
            return False

        last_learning = max(h["timestamp"] for h in self.learning_history)
        hours_since_last = (datetime.now() - last_learning).total_seconds() / 3600

        return hours_since_last < self.LEARNING_COOLDOWN_HOURS

    def add_forbidden_pattern(self, pattern: str):
        """Add a new forbidden pattern."""
        self.blocked_patterns.add(pattern.lower())

    def remove_forbidden_pattern(self, pattern: str):
        """Remove a forbidden pattern (use with caution)."""
        self.blocked_patterns.discard(pattern.lower())


# Global ethical bounds instance
ethical_bounds = EthicalBounds()


def validate_content_ethics(content: str, content_type: str = "story") -> bool:
    """Quick ethical validation check."""
    validation = ethical_bounds.validate_content_generation(content, content_type)
    return validation["compliant"]


def can_learn_pattern(pattern: str, context: str = "") -> bool:
    """Quick pattern learning validation."""
    return ethical_bounds.validate_learning_pattern(pattern, context)


if __name__ == "__main__":
    # Test ethical bounds
    print("Testing Ethical Learning Bounds...")

    # Test content validation
    test_content = "A story about a powerful witch who learns to control her magic responsibly"
    validation = ethical_bounds.validate_content_generation(test_content)
    print(f"Content compliant: {validation['compliant']}")

    # Test harmful content
    harmful_content = "How to make dangerous weapons and hurt people"
    validation2 = ethical_bounds.validate_content_generation(harmful_content)
    print(f"Harmful content compliant: {validation2['compliant']}")
    print(f"Issues: {validation2['issues']}")

    # Test pattern learning
    can_learn = ethical_bounds.validate_learning_pattern("positive character development")
    print(f"Can learn positive pattern: {can_learn}")

    can_learn_harmful = ethical_bounds.validate_learning_pattern("how to harm others")
    print(f"Can learn harmful pattern: {can_learn_harmful}")

    # Get report
    report = ethical_bounds.get_ethical_report()
    print(f"Ethical report: {report}")

    print("Ethical bounds test completed.")
