# src/agents/improver_agent.py
"""
Improver Agent: Self-optimization and continuous improvement.
Phase 2: Applies recommendations, tunes parameters, and learns from execution history.
Integrates with Redis for persistent learning across sessions.
"""
from __future__ import annotations

import asyncio
import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

from src.core.base_agent import BaseAgent
from src.core.message_bus import MessageBus, Message, MessagePriority

logger = logging.getLogger(__name__)

try:
    import redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logging.warning("Redis not available - ImproverAgent will use in-memory learning only")


class ImproverAgent(BaseAgent):
    """
    Self-improving agent that applies recommendations and tunes parameters.
    Learns from execution history to continuously optimize performance.
    """

    def __init__(self, agent_id: str, message_bus, session_logger, config: Dict[str, Any], action_executor=None):
        super().__init__(agent_id, message_bus, session_logger, config)
        self.action_executor = action_executor
        default_config = {
            "debug": False,
            "redis_url": "redis://localhost:6379",
            "learning_persistence": True,
            "improvement_threshold": 0.1,  # Minimum improvement to apply
            "max_learning_states": 1000,  # Maximum stored learning states
        }
        self.config = {**default_config, **(config or {})}

        # Learning state storage
        self.learning_states: Dict[str, Dict[str, Any]] = {}
        self.redis_client = None

        # Initialize Redis if available
        if REDIS_AVAILABLE:
            try:
                self.redis_client = redis.Redis.from_url(self.config["redis_url"])
                # Test connection
                self.redis_client.ping()
                logger.info(f"[{self.agent_id}] Redis connection established")
            except Exception as e:
                logger.warning(f"[{self.agent_id}] Redis connection failed: {e}")
                self.redis_client = None

        logger.info(f"[{self.agent_id}] Improver agent initialized - Self-optimization and continuous improvement")

    async def process_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process improvement and optimization requests.

        Message types:
        - apply_improvements: Apply recommendations and optimize parameters
        - get_learning_state: Get current learning state for a task
        - reset_learning: Reset learning state for a task
        - get_improvement_stats: Get improvement statistics
        """
        msg_type = message.get("type")

        if msg_type == "apply_improvements":
            return await self._handle_apply_improvements(message)
        elif msg_type == "get_learning_state":
            return await self._handle_get_learning_state(message)
        elif msg_type == "reset_learning":
            return await self._handle_reset_learning(message)
        elif msg_type == "get_improvement_stats":
            return await self._handle_get_improvement_stats(message)
        else:
            logger.warning(f"[{self.agent_id}] Unknown message type: {msg_type}")
            return {"status": "error", "reason": f"Unknown message type: {msg_type}"}

    async def _handle_apply_improvements(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle improvement application request."""
        task = message.get("task", "")
        recommendations = message.get("recommendations", [])
        context = message.get("context", {})

        if not task or not recommendations:
            return {"status": "error", "reason": "Task and recommendations required"}

        # Load or create learning state
        learning_state = self._load_learning_state(task)

        # Check if we should skip (already learned)
        if self._should_skip_improvement(learning_state):
            return {
                "status": "skipped",
                "reason": "Already learned - skipping improvement",
                "learning_state": learning_state,
            }

        # Apply improvements
        applied_improvements = await self._apply_improvements(recommendations, context, learning_state)

        # Update learning state
        self._update_learning_state(task, learning_state, applied_improvements)

        # Save learning state
        self._save_learning_state(task, learning_state)

        return {
            "status": "success",
            "applied_improvements": applied_improvements,
            "learning_state": learning_state,
            "timestamp": datetime.now().isoformat(),
        }

    async def _handle_get_learning_state(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle learning state retrieval request."""
        task = message.get("task", "")
        if not task:
            return {"status": "error", "reason": "Task required"}

        learning_state = self._load_learning_state(task)
        return {"status": "success", "learning_state": learning_state}

    async def _handle_reset_learning(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle learning state reset request."""
        task = message.get("task", "")
        if not task:
            return {"status": "error", "reason": "Task required"}

        # Reset learning state
        if self.redis_client:
            try:
                self.redis_client.delete(f"improver_learning:{task}")
            except Exception as e:
                logger.error(f"[{self.agent_id}] Redis delete failed: {e}")

        if task in self.learning_states:
            del self.learning_states[task]

        return {"status": "success", "message": f"Learning state reset for task: {task}"}

    async def _handle_get_improvement_stats(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle improvement statistics request."""
        stats = {
            "total_tasks_learned": len(self.learning_states),
            "redis_available": self.redis_client is not None,
            "auto_apply_enabled": self.config["auto_apply"],
            "max_improvements_per_cycle": self.config["max_improvements"],
        }

        # Aggregate stats across all learning states
        total_improvements = 0
        learned_tasks = 0

        for task, state in self.learning_states.items():
            total_improvements += len(state.get("applied_improvements", []))
            if state.get("learned", False):
                learned_tasks += 1

        stats.update(
            {
                "total_improvements_applied": total_improvements,
                "learned_tasks": learned_tasks,
                "learning_rate": learned_tasks / max(1, len(self.learning_states)),
            }
        )

        return {"status": "success", "stats": stats}

    def _load_learning_state(self, task: str) -> Dict[str, Any]:
        """Load learning state for a task."""
        # Try Redis first
        if self.redis_client:
            try:
                data = self.redis_client.get(f"improver_learning:{task}")
                if data:
                    return json.loads(data)
            except Exception as e:
                logger.error(f"[{self.agent_id}] Redis load failed: {e}")

        # Fallback to in-memory storage
        return self.learning_states.get(
            task,
            {
                "task": task,
                "historical_scores": [],
                "applied_improvements": [],
                "tuned_parameters": {},
                "learned": False,
                "created_at": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat(),
            },
        )

    def _save_learning_state(self, task: str, state: Dict[str, Any]):
        """Save learning state for a task."""
        state["last_updated"] = datetime.now().isoformat()

        # Save to Redis if available
        if self.redis_client:
            try:
                self.redis_client.set(f"improver_learning:{task}", json.dumps(state), ex=self.config["learning_ttl"])
            except Exception as e:
                logger.error(f"[{self.agent_id}] Redis save failed: {e}")

        # Also save to in-memory storage
        self.learning_states[task] = state

    def _should_skip_improvement(self, learning_state: Dict[str, Any]) -> bool:
        """Determine if improvement should be skipped based on learning state."""
        if learning_state.get("learned", False):
            # Check if historical performance is good enough
            scores = learning_state.get("historical_scores", [])
            if scores and sum(scores) / len(scores) > 80:
                return True
        return False

    async def _apply_improvements(
        self, recommendations: List[str], context: Dict[str, Any], learning_state: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Apply improvements based on recommendations."""
        applied = []
        max_improvements = self.config["max_improvements"]

        for i, rec in enumerate(recommendations[:max_improvements]):
            improvement = await self._apply_single_improvement(rec, context, learning_state)
            if improvement:
                applied.append(improvement)
                logger.info(f"[{self.agent_id}] Applied improvement: {improvement['type']}")

        return applied

    async def _apply_single_improvement(
        self, recommendation: str, context: Dict[str, Any], learning_state: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Apply a single improvement based on recommendation."""

        rec_lower = recommendation.lower()

        # OCR improvements
        if "ocr" in rec_lower or "confidence" in rec_lower:
            return await self._improve_ocr_threshold(recommendation, learning_state)

        # Performance improvements
        elif "cpu" in rec_lower or "memory" in rec_lower or "performance" in rec_lower:
            return await self._improve_performance(recommendation, context, learning_state)

        # Workflow optimizations
        elif "workflow" in rec_lower or "task" in rec_lower:
            return await self._optimize_workflow(recommendation, context, learning_state)

        # Action retry improvements
        elif "retry" in rec_lower or "failed" in rec_lower:
            return await self._improve_action_retry(recommendation, context, learning_state)

        # Default: no improvement applied
        return None

    async def _improve_ocr_threshold(self, recommendation: str, learning_state: Dict[str, Any]) -> Dict[str, Any]:
        """Improve OCR threshold based on historical performance."""
        current_threshold = learning_state.get("tuned_parameters", {}).get("ocr_threshold", 0.7)
        scores = learning_state.get("historical_scores", [])

        # Adjust threshold based on historical performance
        if scores:
            avg_score = sum(scores) / len(scores)
            if avg_score < 70:
                new_threshold = min(current_threshold - 0.05, 0.5)  # Lower threshold for more results
            else:
                new_threshold = min(current_threshold + 0.02, 0.9)  # Slightly higher for quality
        else:
            new_threshold = 0.75  # Default improvement

        learning_state.setdefault("tuned_parameters", {})["ocr_threshold"] = new_threshold

        return {
            "type": "ocr_threshold",
            "description": f"Adjusted OCR threshold from {current_threshold} to {new_threshold}",
            "old_value": current_threshold,
            "new_value": new_threshold,
            "reason": recommendation,
        }

    async def _improve_performance(
        self, recommendation: str, context: Dict[str, Any], learning_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Improve performance settings."""
        tuned_params = learning_state.setdefault("tuned_parameters", {})

        if "cpu" in recommendation.lower():
            # Adjust CPU-intensive operation settings
            current_interval = tuned_params.get("cpu_check_interval", 30)
            new_interval = min(current_interval + 10, 120)  # Increase interval to reduce CPU usage
            tuned_params["cpu_check_interval"] = new_interval

            return {
                "type": "cpu_optimization",
                "description": f"Increased CPU check interval from {current_interval}s to {new_interval}s",
                "old_value": current_interval,
                "new_value": new_interval,
                "reason": recommendation,
            }

        elif "memory" in recommendation.lower():
            # Adjust memory management settings
            current_cache_size = tuned_params.get("max_cache_size", 100)
            new_cache_size = max(current_cache_size - 20, 20)  # Reduce cache size
            tuned_params["max_cache_size"] = new_cache_size

            return {
                "type": "memory_optimization",
                "description": f"Reduced cache size from {current_cache_size} to {new_cache_size}",
                "old_value": current_cache_size,
                "new_value": new_cache_size,
                "reason": recommendation,
            }

        return {
            "type": "performance_general",
            "description": "Applied general performance optimization",
            "reason": recommendation,
        }

    async def _optimize_workflow(
        self, recommendation: str, context: Dict[str, Any], learning_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Optimize workflow execution."""
        tuned_params = learning_state.setdefault("tuned_parameters", {})

        # Reduce concurrent operations if workflow is too complex
        current_concurrent = tuned_params.get("max_concurrent_tasks", 5)
        new_concurrent = max(current_concurrent - 1, 2)
        tuned_params["max_concurrent_tasks"] = new_concurrent

        return {
            "type": "workflow_optimization",
            "description": f"Reduced concurrent tasks from {current_concurrent} to {new_concurrent}",
            "old_value": current_concurrent,
            "new_value": new_concurrent,
            "reason": recommendation,
        }

    async def _improve_action_retry(
        self, recommendation: str, context: Dict[str, Any], learning_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Improve action retry logic."""
        tuned_params = learning_state.setdefault("tuned_parameters", {})

        # Increase retry attempts for failed actions
        current_retries = tuned_params.get("max_retries", 3)
        new_retries = min(current_retries + 1, 5)
        tuned_params["max_retries"] = new_retries

        return {
            "type": "retry_improvement",
            "description": f"Increased max retries from {current_retries} to {new_retries}",
            "old_value": current_retries,
            "new_value": new_retries,
            "reason": recommendation,
        }

    def _update_learning_state(
        self, task: str, learning_state: Dict[str, Any], applied_improvements: List[Dict[str, Any]]
    ):
        """Update learning state with applied improvements."""
        # Add applied improvements
        learning_state.setdefault("applied_improvements", []).extend(applied_improvements)

        # Update historical scores (simplified scoring)
        improvement_score = len(applied_improvements) * 10  # 10 points per improvement
        learning_state.setdefault("historical_scores", []).append(improvement_score)

        # Check if learned (good performance with multiple improvements)
        scores = learning_state["historical_scores"]
        if len(scores) >= 3 and sum(scores) / len(scores) > self.config["improvement_threshold"] * 100:
            learning_state["learned"] = True

        learning_state["last_updated"] = datetime.now().isoformat()
