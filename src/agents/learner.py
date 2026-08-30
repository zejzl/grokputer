"""
Learner Agent - Pattern recognition and skill improvement for Pantheon architecture.

Capabilities:
- Detects repeated task patterns and successful execution paths
- Learns from successes and failures
- Builds knowledge base of effective strategies
- Suggests optimizations based on historical data
- Integrates with Memory Manager for persistent learning
"""
from __future__ import annotations

import asyncio
import json
import logging
import random
from collections import Counter, defaultdict, deque
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from src.core.base_agent import BaseAgent
from src.core.message_bus import Message, MessageBus, MessagePriority

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


@dataclass
class RLState:
    """State representation for reinforcement learning."""

    task_type: str
    current_step: int
    previous_actions: Tuple[str, ...]
    context_features: Dict[str, float]

    def to_key(self) -> str:
        """Convert state to hashable key."""
        return f"{self.task_type}_{self.current_step}_{self.previous_actions}_{sorted(self.context_features.items())}"


@dataclass
class RLExperience:
    """Experience tuple for Q-learning."""

    state: RLState
    action: str
    reward: float
    next_state: RLState
    done: bool


class LearnerAgent(BaseAgent):
    """
    Learner Agent (Phase 2): Recognizes patterns and improves over time via RL.

    Features:
    - Pattern detection in task execution
    - Success/failure analysis
    - Strategy optimization
    - Knowledge base building
    - Reinforcement Learning for action selection
    - Q-learning with experience replay
    - Adaptive decision making
    """

    def __init__(
        self,
        agent_id: str,
        message_bus: MessageBus,
        session_logger: "SessionLogger",
        config: Dict[str, Any],
        memory_manager=None,
        heartbeat_interval: float = 10.0,
    ):
        super().__init__(agent_id, message_bus, session_logger, config, heartbeat_interval)

        # Memory integration
        self.memory_manager = memory_manager

        # Learning storage (now backed by hierarchical memory)
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
            "learning_sessions": 0,
            "rl_episodes": 0,
            "rl_steps": 0,
        }

        # Reinforcement Learning components
        self.q_table: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        self.experience_replay: deque = deque(maxlen=config.get("replay_buffer_size", 10000))
        self.learning_rate = config.get("learning_rate", 0.1)
        self.discount_factor = config.get("discount_factor", 0.95)
        self.epsilon = config.get("epsilon", 0.1)  # Exploration rate
        self.action_space = [
            "observe_screen",
            "click_element",
            "type_text",
            "execute_command",
            "wait_for_element",
            "scroll_page",
            "navigate_url",
            "analyze_content",
        ]

        self.session_logger.log_agent_start(self.agent_id)

    async def process_message(self, message: Message) -> Optional[Dict]:
        """
        Process learning-related messages.

        Message types:
        - record_execution: Log task execution for learning
        - analyze_patterns: Trigger pattern analysis
        - get_insights: Return learned insights
        - suggest_optimization: Get optimization for task
        - rl_decide: Get RL-based action decision
        - rl_learn: Learn from RL experience
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

            elif msg_type == "rl_learn":
                return await self._rl_learn(message.content)

            elif msg_type == "rl_decide":
                return self._rl_decide(message.content)

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
            "metadata": metadata,
        }

        self.task_history.append(execution_record)

        # Store in hierarchical memory with knowledge graph
        if self.memory_manager:
            episode_data = {
                "type": "task_execution",
                "task_id": task_id,
                "task_type": task_type,
                "actions": actions,
                "success": success,
                "execution_time": execution_time,
                "importance": 0.8 if success else 0.6,  # Higher importance for successful executions
                "metadata": metadata,
            }
            self.memory_manager.store_episode(self.agent_id, episode_data)

        # Trim history if needed
        if len(self.task_history) > self.max_history:
            self.task_history = self.task_history[-self.max_history :]

        # Trigger pattern detection if enough history
        if len(self.task_history) % 10 == 0:  # Every 10 executions
            await self._detect_patterns()

        self.session_logger.log_agent_activity(self.agent_id, f"Recorded execution: {task_id} (success={success})")

        return {"status": "recorded", "task_id": task_id, "history_size": len(self.task_history)}

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
            action_sequences = [tuple(exec["actions"]) for exec in executions if exec["actions"]]

            if not action_sequences:
                continue

            # Count sequence frequencies
            sequence_counts = Counter(action_sequences)

            for sequence, count in sequence_counts.items():
                if count < self.pattern_threshold:
                    continue

                # Analyze this pattern
                pattern_executions = [e for e in executions if tuple(e["actions"]) == sequence]

                successes = sum(1 for e in pattern_executions if e["success"])
                failures = len(pattern_executions) - successes
                avg_time = sum(e["execution_time"] for e in pattern_executions) / len(pattern_executions)

                # Calculate confidence based on success rate and sample size
                success_rate = successes / len(pattern_executions) * 100
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
                        "first_seen": min(e["timestamp"] for e in pattern_executions),
                    },
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
                    new_success_rate = existing.success_count / total * 100
                    existing.confidence_score = min(new_success_rate * 0.7 + sample_confidence, 100.0)
                else:
                    self.patterns[pattern_id] = pattern
                    new_patterns.append(pattern)
                    self.stats["patterns_learned"] += 1

                    # Store pattern discovery in memory
                    if self.memory_manager:
                        pattern_data = {
                            "type": "pattern_discovery",
                            "pattern_id": pattern_id,
                            "task_type": task_type,
                            "execution_path": list(sequence),
                            "success_rate": pattern.success_rate(),
                            "confidence": pattern.confidence_score,
                            "importance": 0.9,  # High importance for learned patterns
                        }
                        self.memory_manager.store_episode(self.agent_id, pattern_data)

        if new_patterns:
            self.session_logger.log_agent_activity(self.agent_id, f"Detected {len(new_patterns)} new patterns")

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
                    supporting_patterns=[pattern.pattern_id],
                )
                new_insights.append(insight)

            elif success_rate < 50 and pattern.confidence_score > 70:
                # Low success pattern - warning
                insight = LearningInsight(
                    insight_type="warning",
                    confidence=pattern.confidence_score,
                    description=f"Task '{pattern.task_type}' has {success_rate:.1f}% success rate with current approach",
                    recommended_action="Consider alternative execution path or additional validation steps",
                    supporting_patterns=[pattern.pattern_id],
                )
                new_insights.append(insight)

            elif pattern.avg_execution_time > 30.0:  # Slow execution
                insight = LearningInsight(
                    insight_type="suggestion",
                    confidence=pattern.confidence_score,
                    description=f"Task '{pattern.task_type}' averages {pattern.avg_execution_time:.1f}s execution time",
                    recommended_action="Consider parallelization or caching to reduce execution time",
                    supporting_patterns=[pattern.pattern_id],
                )
                new_insights.append(insight)

        self.insights.extend(new_insights)
        self.stats["insights_generated"] += len(new_insights)
        self.stats["learning_sessions"] += 1

        # Store insights in memory
        if self.memory_manager and new_insights:
            for insight in new_insights:
                insight_data = {
                    "type": "learning_insight",
                    "insight_type": insight.insight_type,
                    "confidence": insight.confidence,
                    "description": insight.description,
                    "recommended_action": insight.recommended_action,
                    "importance": 0.7,
                }
                self.memory_manager.store_episode(self.agent_id, insight_data)

        return {
            "status": "analyzed",
            "patterns_found": len(self.patterns),
            "new_insights": len(new_insights),
            "insights": [asdict(i) for i in new_insights],
            "high_confidence_patterns": sum(1 for p in self.patterns.values() if p.confidence_score >= min_confidence),
        }

    async def _get_insights(self, content: Dict) -> Dict:
        """Return learned insights."""
        insight_type = content.get("type", "all")  # all, optimization, warning, suggestion
        min_confidence = content.get("min_confidence", 0.0)

        filtered_insights = [
            i
            for i in self.insights
            if (insight_type == "all" or i.insight_type == insight_type) and i.confidence >= min_confidence
        ]

        # Sort by confidence
        filtered_insights.sort(key=lambda x: x.confidence, reverse=True)

        return {
            "status": "success",
            "insights": [asdict(i) for i in filtered_insights],
            "total_insights": len(self.insights),
        }

    async def _suggest_optimization(self, content: Dict) -> Dict:
        """Suggest optimization for a specific task."""
        task_type = content.get("task_type")

        if not task_type:
            return {"status": "error", "reason": "task_type required"}

        # Find relevant patterns
        relevant_patterns = [
            p
            for p in self.patterns.values()
            if p.task_type == task_type and p.confidence_score >= self.confidence_threshold
        ]

        if not relevant_patterns:
            return {
                "status": "no_optimization",
                "reason": f"No high-confidence patterns found for task type: {task_type}",
            }

        # Sort by success rate and confidence
        relevant_patterns.sort(key=lambda p: (p.success_rate(), p.confidence_score), reverse=True)

        best_pattern = relevant_patterns[0]

        return {
            "status": "optimization_found",
            "task_type": task_type,
            "recommended_path": best_pattern.execution_path,
            "success_rate": best_pattern.success_rate(),
            "confidence": best_pattern.confidence_score,
            "avg_execution_time": best_pattern.avg_execution_time,
            "pattern_id": best_pattern.pattern_id,
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
            ),
            "rl_states_learned": len(self.q_table),
            "experience_buffer_size": len(self.experience_replay),
            "q_table_size": sum(len(actions) for actions in self.q_table.values()),
        }

    async def get_task_patterns(self, task_description: str) -> List[Dict]:
        """
        Get patterns relevant to a task description.

        Args:
            task_description: Description of the task to find patterns for

        Returns:
            List of relevant pattern insights
        """
        # Simple keyword matching for now - could be enhanced with NLP
        keywords = task_description.lower().split()

        relevant_patterns = []
        for pattern in self.patterns.values():
            if pattern.confidence_score < self.confidence_threshold:
                continue

            # Check if task type matches keywords
            task_type_lower = pattern.task_type.lower()
            if any(keyword in task_type_lower for keyword in keywords):
                relevant_patterns.append(
                    {
                        "pattern_id": pattern.pattern_id,
                        "task_type": pattern.task_type,
                        "success_rate": pattern.success_rate(),
                        "execution_path": pattern.execution_path,
                        "agent_usage": list(set(pattern.execution_path)),  # Unique agents used
                        "subtask_types": [step.split("_")[0] for step in pattern.execution_path],  # Extract types
                        "confidence": pattern.confidence_score,
                    }
                )

        return relevant_patterns

    async def get_success_patterns(self, task_description: str) -> List[Dict]:
        """
        Get successful execution patterns for similar tasks.

        Args:
            task_description: Description of the task to find success patterns for

        Returns:
            List of successful pattern insights
        """
        patterns = await self.get_task_patterns(task_description)

        # Filter for high success rate patterns
        success_patterns = [p for p in patterns if p["success_rate"] > 80.0 and p["confidence"] > 70.0]

        # Add success indicators
        for pattern in success_patterns:
            pattern["success_patterns"] = [
                f"Use {' -> '.join(pattern['execution_path'][:3])}",
                f"Success rate: {pattern['success_rate']:.1f}%",
                f"Agent sequence: {' -> '.join(pattern['agent_usage'])}",
            ]

        return success_patterns

    def _rl_decide(self, content: Dict) -> Dict:
        """Make RL-based decision for next action."""
        state_data = content.get("state", {})
        state = RLState(
            task_type=state_data.get("task_type", "unknown"),
            current_step=state_data.get("current_step", 0),
            previous_actions=tuple(state_data.get("previous_actions", [])),
            context_features=state_data.get("context_features", {}),
        )

        # Epsilon-greedy action selection
        if random.random() < self.epsilon:
            action = random.choice(self.action_space)
        else:
            state_key = state.to_key()
            q_values = self.q_table.get(state_key, {})
            if q_values:
                action = max(q_values, key=q_values.get)
            else:
                action = random.choice(self.action_space)

        return {
            "status": "success",
            "action": action,
            "state_key": state.to_key(),
            "exploration": random.random() < self.epsilon,
        }

    async def _rl_learn(self, content: Dict) -> Dict:
        """Learn from RL experience."""
        experience_data = content.get("experience", {})
        state_data = experience_data.get("state", {})
        next_state_data = experience_data.get("next_state", {})

        state = RLState(
            task_type=state_data.get("task_type", "unknown"),
            current_step=state_data.get("current_step", 0),
            previous_actions=tuple(state_data.get("previous_actions", [])),
            context_features=state_data.get("context_features", {}),
        )

        next_state = RLState(
            task_type=next_state_data.get("task_type", "unknown"),
            current_step=next_state_data.get("current_step", 0),
            previous_actions=tuple(next_state_data.get("previous_actions", [])),
            context_features=next_state_data.get("context_features", {}),
        )

        action = experience_data.get("action", "")
        reward = experience_data.get("reward", 0.0)
        done = experience_data.get("done", False)

        # Store experience
        experience = RLExperience(state, action, reward, next_state, done)
        self.experience_replay.append(experience)

        # Q-learning update
        state_key = state.to_key()
        next_state_key = next_state.to_key()

        current_q = self.q_table[state_key][action]
        next_max_q = max(self.q_table[next_state_key].values()) if self.q_table[next_state_key] else 0.0

        new_q = current_q + self.learning_rate * (reward + self.discount_factor * next_max_q - current_q)
        self.q_table[state_key][action] = new_q

        self.stats["rl_steps"] += 1

        # Periodic learning session
        if len(self.experience_replay) >= 100 and self.stats["rl_steps"] % 50 == 0:
            await self._rl_batch_learn()

        return {"status": "success", "q_value": new_q}

    async def _rl_batch_learn(self):
        """Batch learning from experience replay."""
        if len(self.experience_replay) < 32:
            return

        # Sample batch
        batch = random.sample(list(self.experience_replay), min(32, len(self.experience_replay)))

        for experience in batch:
            state_key = experience.state.to_key()
            next_state_key = experience.next_state.to_key()

            current_q = self.q_table[state_key][experience.action]
            next_max_q = max(self.q_table[next_state_key].values()) if self.q_table[next_state_key] else 0.0

            new_q = current_q + self.learning_rate * (experience.reward + self.discount_factor * next_max_q - current_q)
            self.q_table[state_key][experience.action] = new_q

        self.stats["rl_episodes"] += 1
        self.session_logger.log_agent_activity(self.agent_id, f"RL batch learning: {len(batch)} experiences processed")

    async def on_start(self):
        """Learner-specific startup."""
        await super().on_start()
        self.session_logger.log_agent_ready(self.agent_id, "Learner active - pattern recognition enabled")

    async def on_stop(self):
        """Persist learned patterns before shutdown."""
        # Persist patterns and insights in hierarchical memory
        if self.memory_manager:
            # Store all patterns
            for pattern in self.patterns.values():
                pattern_data = {
                    "type": "learned_pattern",
                    "pattern_id": pattern.pattern_id,
                    "task_type": pattern.task_type,
                    "execution_path": pattern.execution_path,
                    "success_count": pattern.success_count,
                    "failure_count": pattern.failure_count,
                    "avg_execution_time": pattern.avg_execution_time,
                    "confidence_score": pattern.confidence_score,
                    "importance": 0.8,
                }
                self.memory_manager.store_episode(self.agent_id, pattern_data)

            # Store all insights
            for insight in self.insights:
                insight_data = {
                    "type": "stored_insight",
                    "insight_type": insight.insight_type,
                    "confidence": insight.confidence,
                    "description": insight.description,
                    "recommended_action": insight.recommended_action,
                    "importance": 0.6,
                }
                self.memory_manager.store_episode(self.agent_id, insight_data)

        self.session_logger.log_agent_activity(
            self.agent_id, f"Shutdown: {len(self.patterns)} patterns learned, {len(self.insights)} insights generated"
        )
        await super().on_stop()
