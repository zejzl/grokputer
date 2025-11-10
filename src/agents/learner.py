"""
Learner Agent - Pattern recognition and skill improvement for Pantheon architecture.

Capabilities:
- Detects repeated task patterns and successful execution paths
- Learns from successes and failures
- Builds knowledge base of effective strategies
- Suggests optimizations based on historical data
- Integrates with Memory Manager for persistent learning
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from collections import defaultdict, Counter
import json
from dataclasses import dataclass, asdict

from src.core.base_agent import BaseAgent
from src.core.message_bus import MessageBus, Message, MessagePriority

logger = logging.getLogger(__name__)


@dataclass
class Pattern:
    """Represents a learned pattern."""
    pattern_id: str
    task_type: str
    execution_path: List[str]  # Sequence of actions
    success_count: int
    failure_count: int
    avg_execution_time: float
    confidence_score: float  # 0-100%
    last_seen: float
    metadata: Dict[str, Any]

    def success_rate(self) -> float:
        """Calculate success rate."""
        total = self.success_count + self.failure_count
        return (self.success_count / total * 100) if total > 0 else 0.0


@dataclass
class LearningInsight:
    """Actionable insight from learned patterns."""
    insight_type: str  # "optimization", "warning", "suggestion"
    confidence: float
    description: str
    recommended_action: str
    supporting_patterns: List[str]  # Pattern IDs


class LearnerAgent(BaseAgent):
    """
    Learner Agent (Phase 2): Recognizes patterns and improves over time.

    Features:
    - Pattern detection in task execution
    - Success/failure analysis
    - Strategy optimization
    - Knowledge base building
    """

    def __init__(
        self,
        agent_id: str,
        message_bus: MessageBus,
        session_logger: 'SessionLogger',
        config: Dict[str, Any],
        heartbeat_interval: float = 10.0
    ):
        super().__init__(agent_id, message_bus, session_logger, config, heartbeat_interval)

        # Learning storage
        self.patterns: Dict[str, Pattern] = {}  # pattern_id -> Pattern
        self.task_history: List[Dict] = []  # Recent task executions
        self.insights: List[LearningInsight] = []

        # Configuration
        self.max_history = config.get("max_history", 1000)
        self.pattern_threshold = config.get("pattern_threshold", 3)  # Min occurrences
        self.confidence_threshold = config.get("confidence_threshold", 70.0)

        # Statistics
        self.stats = {
            "patterns_learned": 0,
            "insights_generated": 0,
            "optimizations_applied": 0,
            "learning_sessions": 0
        }

        self.session_logger.log_agent_init(
            self.agent_id,
            f"Learner ready with threshold={self.pattern_threshold}"
        )

    async def process_message(self, message: Message) -> Optional[Dict]:
        """
        Process learning-related messages.

        Message types:
        - record_execution: Log task execution for learning
        - analyze_patterns: Trigger pattern analysis
        - get_insights: Return learned insights
        - suggest_optimization: Get optimization for task
        """
        msg_type = message.message_type
        self._update_state("processing")

        try:
            if msg_type == "record_execution":
                return await self._record_execution(message.content)

            elif msg_type == "analyze_patterns":
                return await self._analyze_patterns(message.content)

            elif msg_type == "get_insights":
                return await self._get_insights(message.content)

            elif msg_type == "suggest_optimization":
                return await self._suggest_optimization(message.content)

            elif msg_type == "get_stats":
                return self._get_stats()

            else:
                logger.warning(f"Unknown message type: {msg_type}")
                return {"status": "error", "reason": f"Unknown message type: {msg_type}"}

        finally:
            self._update_state("idle")

    async def _record_execution(self, content: Dict) -> Dict:
        """Record a task execution for pattern learning."""
        task_id = content.get("task_id")
        task_type = content.get("task_type", "unknown")
        actions = content.get("actions", [])
        success = content.get("success", False)
        execution_time = content.get("execution_time", 0.0)
        metadata = content.get("metadata", {})

        # Add to history
        execution_record = {
            "task_id": task_id,
            "task_type": task_type,
            "actions": actions,
            "success": success,
            "execution_time": execution_time,
            "timestamp": datetime.now().timestamp(),
            "metadata": metadata
        }

        self.task_history.append(execution_record)

        # Trim history if needed
        if len(self.task_history) > self.max_history:
            self.task_history = self.task_history[-self.max_history:]

        # Trigger pattern detection if enough history
        if len(self.task_history) % 10 == 0:  # Every 10 executions
            await self._detect_patterns()

        self.session_logger.log_agent_activity(
            self.agent_id,
            f"Recorded execution: {task_id} (success={success})"
        )

        return {
            "status": "recorded",
            "task_id": task_id,
            "history_size": len(self.task_history)
        }

    async def _detect_patterns(self) -> List[Pattern]:
        """Detect patterns in execution history."""
        # Group executions by task type
        by_type: Dict[str, List[Dict]] = defaultdict(list)
        for record in self.task_history:
            by_type[record["task_type"]].append(record)

        new_patterns = []

        for task_type, executions in by_type.items():
            if len(executions) < self.pattern_threshold:
                continue

            # Find common action sequences
            action_sequences = [
                tuple(exec["actions"]) for exec in executions if exec["actions"]
            ]

            if not action_sequences:
                continue

            # Count sequence frequencies
            sequence_counts = Counter(action_sequences)

            for sequence, count in sequence_counts.items():
                if count < self.pattern_threshold:
                    continue

                # Analyze this pattern
                pattern_executions = [
                    e for e in executions if tuple(e["actions"]) == sequence
                ]

                successes = sum(1 for e in pattern_executions if e["success"])
                failures = len(pattern_executions) - successes
                avg_time = sum(e["execution_time"] for e in pattern_executions) / len(pattern_executions)

                # Calculate confidence based on success rate and sample size
                success_rate = (successes / len(pattern_executions) * 100)
                sample_confidence = min(len(pattern_executions) / 10.0 * 20, 30)  # Up to 30% from sample size
                confidence = min(success_rate * 0.7 + sample_confidence, 100.0)

                pattern_id = f"{task_type}_{hash(sequence) % 10000}"

                pattern = Pattern(
                    pattern_id=pattern_id,
                    task_type=task_type,
                    execution_path=list(sequence),
                    success_count=successes,
                    failure_count=failures,
                    avg_execution_time=avg_time,
                    confidence_score=confidence,
                    last_seen=datetime.now().timestamp(),
                    metadata={
                        "sample_size": len(pattern_executions),
                        "first_seen": min(e["timestamp"] for e in pattern_executions)
                    }
                )

                # Update or add pattern
                if pattern_id in self.patterns:
                    # Update existing
                    existing = self.patterns[pattern_id]
                    existing.success_count += successes
                    existing.failure_count += failures
                    existing.last_seen = pattern.last_seen
                    # Recalculate confidence
                    total = existing.success_count + existing.failure_count
                    new_success_rate = (existing.success_count / total * 100)
                    existing.confidence_score = min(new_success_rate * 0.7 + sample_confidence, 100.0)
                else:
                    self.patterns[pattern_id] = pattern
                    new_patterns.append(pattern)
                    self.stats["patterns_learned"] += 1

        if new_patterns:
            self.session_logger.log_agent_activity(
                self.agent_id,
                f"Detected {len(new_patterns)} new patterns"
            )

        return new_patterns

    async def _analyze_patterns(self, content: Dict) -> Dict:
        """Analyze patterns and generate insights."""
        min_confidence = content.get("min_confidence", self.confidence_threshold)

        # Detect new patterns first
        await self._detect_patterns()

        # Generate insights from high-confidence patterns
        new_insights = []

        for pattern in self.patterns.values():
            if pattern.confidence_score < min_confidence:
                continue

            success_rate = pattern.success_rate()

            # Generate different insights based on pattern characteristics
            if success_rate > 90 and pattern.confidence_score > 80:
                # High success pattern - optimization opportunity
                insight = LearningInsight(
                    insight_type="optimization",
                    confidence=pattern.confidence_score,
                    description=f"Task '{pattern.task_type}' executes reliably with {len(pattern.execution_path)} steps",
                    recommended_action=f"Use cached execution path: {' -> '.join(pattern.execution_path[:3])}...",
                    supporting_patterns=[pattern.pattern_id]
                )
                new_insights.append(insight)

            elif success_rate < 50 and pattern.confidence_score > 70:
                # Low success pattern - warning
                insight = LearningInsight(
                    insight_type="warning",
                    confidence=pattern.confidence_score,
                    description=f"Task '{pattern.task_type}' has {success_rate:.1f}% success rate with current approach",
                    recommended_action="Consider alternative execution path or additional validation steps",
                    supporting_patterns=[pattern.pattern_id]
                )
                new_insights.append(insight)

            elif pattern.avg_execution_time > 30.0:  # Slow execution
                insight = LearningInsight(
                    insight_type="suggestion",
                    confidence=pattern.confidence_score,
                    description=f"Task '{pattern.task_type}' averages {pattern.avg_execution_time:.1f}s execution time",
                    recommended_action="Consider parallelization or caching to reduce execution time",
                    supporting_patterns=[pattern.pattern_id]
                )
                new_insights.append(insight)

        self.insights.extend(new_insights)
        self.stats["insights_generated"] += len(new_insights)
        self.stats["learning_sessions"] += 1

        return {
            "status": "analyzed",
            "patterns_found": len(self.patterns),
            "new_insights": len(new_insights),
            "insights": [asdict(i) for i in new_insights],
            "high_confidence_patterns": sum(
                1 for p in self.patterns.values() if p.confidence_score >= min_confidence
            )
        }

    async def _get_insights(self, content: Dict) -> Dict:
        """Return learned insights."""
        insight_type = content.get("type", "all")  # all, optimization, warning, suggestion
        min_confidence = content.get("min_confidence", 0.0)

        filtered_insights = [
            i for i in self.insights
            if (insight_type == "all" or i.insight_type == insight_type)
            and i.confidence >= min_confidence
        ]

        # Sort by confidence
        filtered_insights.sort(key=lambda x: x.confidence, reverse=True)

        return {
            "status": "success",
            "insights": [asdict(i) for i in filtered_insights],
            "total_insights": len(self.insights)
        }

    async def _suggest_optimization(self, content: Dict) -> Dict:
        """Suggest optimization for a specific task."""
        task_type = content.get("task_type")

        if not task_type:
            return {"status": "error", "reason": "task_type required"}

        # Find relevant patterns
        relevant_patterns = [
            p for p in self.patterns.values()
            if p.task_type == task_type and p.confidence_score >= self.confidence_threshold
        ]

        if not relevant_patterns:
            return {
                "status": "no_optimization",
                "reason": f"No high-confidence patterns found for task type: {task_type}"
            }

        # Sort by success rate and confidence
        relevant_patterns.sort(
            key=lambda p: (p.success_rate(), p.confidence_score),
            reverse=True
        )

        best_pattern = relevant_patterns[0]

        return {
            "status": "optimization_found",
            "task_type": task_type,
            "recommended_path": best_pattern.execution_path,
            "success_rate": best_pattern.success_rate(),
            "confidence": best_pattern.confidence_score,
            "avg_execution_time": best_pattern.avg_execution_time,
            "pattern_id": best_pattern.pattern_id
        }

    def _get_stats(self) -> Dict:
        """Return learning statistics."""
        return {
            "agent_id": self.agent_id,
            "stats": self.stats,
            "patterns_stored": len(self.patterns),
            "history_size": len(self.task_history),
            "insights_available": len(self.insights),
            "high_confidence_patterns": sum(
                1 for p in self.patterns.values() if p.confidence_score >= self.confidence_threshold
            )
        }

    async def on_start(self):
        """Learner-specific startup."""
        await super().on_start()
        self.session_logger.log_agent_ready(
            self.agent_id,
            "Learner active - pattern recognition enabled"
        )

    async def on_stop(self):
        """Persist learned patterns before shutdown."""
        # TODO: Integrate with Memory Manager to persist patterns
        self.session_logger.log_agent_activity(
            self.agent_id,
            f"Shutdown: {len(self.patterns)} patterns learned, {len(self.insights)} insights generated"
        )
        await super().on_stop()
