"""
Hybrid Conversation Manager
Integrates NLI with Redis caching and SQLite persistence for optimal performance.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from src.interfaces.natural_language_interface import NaturalLanguageInterface, ConversationContext
from src.core.conversation_cache import ConversationCache
from src.agents.coordinator import Coordinator
from db_config import (
    get_conversation_history,
    get_user_conversations,
    get_user_preferences,
    save_conversation_analytics,
    get_conversation_analytics,
)

logger = logging.getLogger(__name__)


class HybridConversationManager:
    """
    Hybrid Redis/SQLite conversation manager for NLI.

    Architecture:
    - Redis: Fast access to active conversations and context
    - SQLite: Persistent storage of all conversation data
    - Automatic sync between cache and persistence
    - Analytics and preference learning
    """

    def __init__(self, coordinator: Coordinator, redis_url: str = "redis://localhost:6379"):
        self.coordinator = coordinator
        self.cache = ConversationCache(redis_url)
        self.nli = NaturalLanguageInterface(coordinator)
        self.nli.cache_manager = self  # Inject self-reference for persistence

        # In-memory conversation contexts (fallback when Redis unavailable)
        self.memory_contexts: Dict[str, ConversationContext] = {}

    async def start(self):
        """Initialize the hybrid manager."""
        await self.cache.start()
        logger.info("Hybrid conversation manager started")

    async def create_conversation(self, user_id: str, metadata: Dict[str, Any] = None) -> str:
        """Create a new conversation with persistence."""
        conversation_id = f"conv_{user_id}_{int(datetime.now().timestamp())}"

        # Create in cache
        success = await self.cache.create_conversation(conversation_id, user_id, metadata)

        if success:
            # Create in-memory context
            context = ConversationContext(
                conversation_id=conversation_id,
                user_id=user_id,
                start_time=datetime.now(),
                messages=[],
                task_history=[],
                context_variables=metadata or {},
            )
            self.memory_contexts[conversation_id] = context

        return conversation_id

    async def process_message(self, conversation_id: str, user_message: str) -> Dict[str, Any]:
        """Process a message with hybrid caching."""
        # Get context from cache or memory
        context = await self._get_conversation_context(conversation_id)

        if not context:
            return {"error": "Conversation not found", "message": "Please start a new conversation first."}

        # Process with NLI
        response = self.nli.process_message(conversation_id, user_message)

        # Save message to cache and persistence
        message_id = f"msg_{conversation_id}_{int(datetime.now().timestamp())}"
        await self.cache.save_message(
            conversation_id=conversation_id,
            message_id=message_id,
            role="user",
            content=user_message,
            metadata={"intent": getattr(self.nli, "last_intent", None)},
        )

        await self.cache.save_message(
            conversation_id=conversation_id,
            message_id=f"resp_{message_id}",
            role="assistant",
            content=response["message"],
            metadata={"type": response.get("type"), "task": response.get("task")},
        )

        # Update context in cache
        if "type" in response and response["type"] == "task_started":
            await self.cache.update_conversation_state(
                conversation_id, "task_in_progress", context.get("context_variables", {})
            )

        # Record analytics
        await self._record_analytics(conversation_id, context["user_id"], response)

        return response

    async def _get_conversation_context(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get conversation context from cache or reconstruct from persistence."""
        # Try cache first
        context = await self.cache.get_conversation_context(conversation_id)

        if context:
            return context

        # Fallback to memory
        if conversation_id in self.memory_contexts:
            mem_context = self.memory_contexts[conversation_id]
            return {
                "conversation_id": mem_context.conversation_id,
                "user_id": mem_context.user_id,
                "start_time": mem_context.start_time.isoformat(),
                "status": "active",
                "total_messages": len(mem_context.messages),
                "metadata": {},
                "context_variables": mem_context.context_variables or {},
                "conversation_state": mem_context.conversation_state,
                "last_intent": mem_context.last_intent,
                "recent_messages": [
                    {
                        "role": msg["role"],
                        "content": msg["content"],
                        "timestamp": msg["timestamp"],
                        "metadata": msg.get("metadata", {}),
                    }
                    for msg in mem_context.messages[-20:]
                ],
            }

        # Reconstruct from SQLite
        messages = get_conversation_history(conversation_id, limit=50)
        if messages:
            first_msg = messages[0]
            return {
                "conversation_id": conversation_id,
                "user_id": first_msg.get("user_id", "unknown"),
                "start_time": first_msg.get("timestamp", datetime.now().isoformat()),
                "status": "active",
                "total_messages": len(messages),
                "metadata": {},
                "context_variables": {},
                "conversation_state": "idle",
                "last_intent": "",
                "recent_messages": messages[-20:],
            }

        return None

    async def get_conversation_history(self, conversation_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get conversation history with caching."""
        # Try cache first for recent messages
        context = await self.cache.get_conversation_context(conversation_id)
        if context and context.get("recent_messages"):
            recent_cached = context["recent_messages"]
            if len(recent_cached) >= limit:
                return recent_cached[-limit:]

        # Fallback to SQLite
        return get_conversation_history(conversation_id, limit)

    async def get_user_context(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive user context."""
        # Get preferences
        preferences = get_user_preferences(user_id)

        # Get recent conversations
        conversations = get_user_conversations(user_id, limit=5)

        # Get analytics summary
        analytics = get_conversation_analytics(user_id=user_id, limit=100)

        # Calculate user insights
        insights = self._calculate_user_insights(analytics)

        return {
            "preferences": preferences,
            "recent_conversations": conversations,
            "analytics": insights,
            "total_conversations": len(conversations),
        }

    def _calculate_user_insights(self, analytics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate user behavior insights from analytics."""
        if not analytics:
            return {}

        # Group by metric type
        metrics = {}
        for analytic in analytics:
            metric_name = analytic["metric_name"]
            if metric_name not in metrics:
                metrics[metric_name] = []
            metrics[metric_name].append(analytic["metric_value"])

        insights = {}
        for metric_name, values in metrics.items():
            if metric_name == "response_time":
                insights["avg_response_time"] = sum(values) / len(values)
            elif metric_name == "task_success":
                insights["task_success_rate"] = sum(values) / len(values)
            elif metric_name == "user_satisfaction":
                insights["avg_satisfaction"] = sum(values) / len(values)

        return insights

    async def _record_analytics(self, conversation_id: str, user_id: str, response: Dict[str, Any]):
        """Record conversation analytics."""
        try:
            # Response time (mock for now)
            response_time = 1.5  # seconds

            # Task success
            task_success = 1.0 if response.get("type") in ["task_completed", "task_started"] else 0.5

            # User satisfaction (from feedback if available)
            satisfaction = 0.8  # default neutral-positive

            await asyncio.get_event_loop().run_in_executor(
                None, save_conversation_analytics, conversation_id, user_id, "response_time", response_time
            )

            await asyncio.get_event_loop().run_in_executor(
                None, save_conversation_analytics, conversation_id, user_id, "task_success", task_success
            )

            await asyncio.get_event_loop().run_in_executor(
                None, save_conversation_analytics, conversation_id, user_id, "user_satisfaction", satisfaction
            )

        except Exception as e:
            logger.warning(f"Failed to record analytics: {e}")

    async def end_conversation(self, conversation_id: str):
        """End conversation and persist final state."""
        # Update cache
        await self.cache.end_conversation(conversation_id)

        # Clean up memory
        if conversation_id in self.memory_contexts:
            del self.memory_contexts[conversation_id]

        # Update SQLite status
        from db_config import update_conversation_status

        update_conversation_status(conversation_id, "completed")

    async def cleanup_old_conversations(self, days_old: int = 30):
        """Clean up old conversations from cache and archive in SQLite."""
        # Archive old cache entries
        archived = await self.cache.archive_old_conversations(days_old)

        # Clean up old SQLite conversations
        from db_config import cleanup_old_conversations

        sqlite_cleaned = cleanup_old_conversations(days_old)

        logger.info(f"Cleaned up {archived} cached and {sqlite_cleaned} SQLite conversations")

    async def get_system_stats(self) -> Dict[str, Any]:
        """Get system-wide conversation statistics."""
        cache_stats = await self.cache.get_cache_stats()

        # Get SQLite stats
        from db_config import execute_query

        total_convs = execute_query("SELECT COUNT(*) as count FROM conversations", fetchone=True)
        active_convs = execute_query(
            "SELECT COUNT(*) as count FROM conversations WHERE status = 'active'", fetchone=True
        )
        total_messages = execute_query("SELECT COUNT(*) as count FROM conversation_messages", fetchone=True)

        return {
            "cache": cache_stats,
            "sqlite": {
                "total_conversations": total_convs["count"] if total_convs else 0,
                "active_conversations": active_convs["count"] if active_convs else 0,
                "total_messages": total_messages["count"] if total_messages else 0,
            },
        }
