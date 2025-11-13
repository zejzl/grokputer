"""
Natural Language Interface for Human-AI Collaboration

Provides conversational interface for interacting with Grokputer agents.
Handles natural language task parsing, dialogue management, and feedback collection.
"""

import re
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import json

from src.grok_client import GrokClient
from src.agents.coordinator import Coordinator
from src.core.message_bus import MessageBus

logger = logging.getLogger(__name__)


@dataclass
class ConversationContext:
    """Maintains context for ongoing conversations."""

    conversation_id: str
    user_id: str
    start_time: datetime
    messages: List[Dict[str, Any]]
    current_task: Optional[Dict[str, Any]] = None
    pending_feedback: Optional[Dict[str, Any]] = None
    preferences: Dict[str, Any] = None
    conversation_state: str = "idle"  # idle, task_in_progress, awaiting_feedback, awaiting_confirmation
    last_intent: Optional[str] = None
    task_history: List[Dict[str, Any]] = None  # Track completed tasks
    context_variables: Dict[str, Any] = None  # Store conversation variables

    def add_message(self, role: str, content: str, metadata: Optional[Dict] = None):
        """Add a message to the conversation."""
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {},
        }
        self.messages.append(message)

    def get_recent_context(self, max_messages: int = 10) -> List[Dict[str, Any]]:
        """Get recent conversation context."""
        return self.messages[-max_messages:]

    def set_state(self, state: str):
        """Update conversation state."""
        self.conversation_state = state

    def add_completed_task(self, task: Dict[str, Any]):
        """Add a completed task to history."""
        if self.task_history is None:
            self.task_history = []
        self.task_history.append({**task, "completed_at": datetime.now().isoformat()})

    def get_context_variable(self, key: str) -> Any:
        """Get a context variable."""
        return self.context_variables.get(key) if self.context_variables else None

    def set_context_variable(self, key: str, value: Any):
        """Set a context variable."""
        if self.context_variables is None:
            self.context_variables = {}
        self.context_variables[key] = value


class NaturalLanguageInterface:
    """
    Conversational interface for human-AI collaboration.

    Features:
    - Natural language task parsing
    - Conversation context management
    - Feedback collection
    - Multi-turn dialogue support
    """

    def __init__(self, coordinator: Coordinator, grok_client: Optional[GrokClient] = None, cache_manager=None):
        """
        Initialize NLI.

        Args:
            coordinator: Agent coordinator for task execution
            grok_client: Grok client for NLP tasks (optional)
            cache_manager: Conversation cache manager for persistence
        """
        self.coordinator = coordinator
        self.grok_client = grok_client or GrokClient()
        self.cache_manager = cache_manager
        self.conversations: Dict[str, ConversationContext] = {}

        # Task parsing patterns
        self.task_patterns = {
            "file_operations": [
                r"(?:list|show|display|get) (?:files|contents) (?:in|of) (.+)",
                r"(?:read|open|view) (?:file|document) (.+)",
                r"(?:create|make|write) (?:file|document) (.+)",
            ],
            "system_info": [
                r"(?:what|show|get) (?:system|computer) (?:info|information|status)",
                r"(?:check|monitor) (?:cpu|memory|disk|performance)",
                r"(?:list|show) (?:processes|running apps)",
            ],
            "web_tasks": [
                r"(?:search|find|look up) (.+) (?:on|in) (?:google|web|internet)",
                r"(?:open|visit|go to) (?:website|url|site) (.+)",
                r"(?:take| capture|get) screenshot",
            ],
            "automation": [
                r"(?:run|execute|perform) (.+) (?:task|action|command)",
                r"automat(?:e|ion) (.+)",
                r"(?:repeat|loop) (.+) (\d+) times",
            ],
        }

        # Response templates
        self.response_templates = {
            "task_started": "I'll help you with that. Starting task: {task_description}",
            "task_completed": "Task completed successfully! {summary}",
            "task_failed": "Sorry, the task failed. {error_message}",
            "clarification_needed": "I need more details. Could you clarify: {question}",
            "feedback_request": "How did that work for you? (good/bad/indifferent)",
            "confirmation": "Are you sure you want to {action}? (yes/no)",
        }

        logger.info("Natural Language Interface initialized")

    def start_conversation(self, user_id: str) -> str:
        """Start a new conversation and return conversation ID."""
        conversation_id = f"conv_{user_id}_{int(datetime.now().timestamp())}"

        context = ConversationContext(
            conversation_id=conversation_id,
            user_id=user_id,
            start_time=datetime.now(),
            messages=[],
            preferences={},
            task_history=[],
            context_variables={},
        )

        self.conversations[conversation_id] = context

        # Welcome message
        context.add_message("assistant", "Hello! I'm Grokputer, your AI assistant. How can I help you today?")

        # Persist to cache if available
        if self.cache_manager:
            asyncio.create_task(self.cache_manager.create_conversation(conversation_id, user_id))

        logger.info(f"Started conversation {conversation_id} for user {user_id}")
        return conversation_id

    def process_message(self, conversation_id: str, user_message: str) -> Dict[str, Any]:
        """
        Process a user message and return response with multi-turn dialogue support.

        Args:
            conversation_id: Conversation identifier
            user_message: User's natural language message

        Returns:
            Response dict with message and metadata
        """
        if conversation_id not in self.conversations:
            return {"error": "Conversation not found", "message": "Please start a new conversation first."}

        context = self.conversations[conversation_id]
        context.add_message("user", user_message)

        try:
            # Handle state-specific processing first
            state_response = self._handle_state_specific(context, user_message)
            if state_response:
                context.add_message("assistant", state_response["message"], state_response.get("metadata"))
                return state_response

            # Parse intent and extract task
            intent, task_data = self._parse_intent(user_message)
            context.last_intent = intent

            if intent == "task":
                # Execute task
                response = self._handle_task(context, task_data)
            elif intent == "feedback":
                # Handle feedback
                response = self._handle_feedback(context, user_message)
            elif intent == "clarification":
                # Ask for clarification
                response = self._handle_clarification(context, task_data)
            elif intent == "conversation":
                # General conversation
                response = self._handle_conversation(context, user_message)
            else:
                response = {"message": "I'm not sure what you mean. Could you rephrase that?", "type": "clarification"}

            # Update conversation state based on response
            self._update_conversation_state(context, response)

            # Add assistant response to context
            context.add_message("assistant", response["message"], response.get("metadata"))

            # Persist messages to cache if available
            if self.cache_manager:
                asyncio.create_task(self._persist_messages_async(conversation_id, user_message, response))

            return response

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            error_response = {
                "message": "Sorry, I encountered an error. Please try again.",
                "type": "error",
                "error": str(e),
            }
            context.add_message("assistant", error_response["message"])
            return error_response

    def _parse_intent(self, message: str) -> Tuple[str, Dict[str, Any]]:
        """
        Parse user message to determine intent and extract data.

        Returns:
            Tuple of (intent_type, extracted_data)
        """
        message_lower = message.lower().strip()

        # Check for feedback responses
        if message_lower in ["good", "bad", "great", "terrible", "ok", "fine", "indifferent"]:
            return "feedback", {"rating": message_lower}

        # Check for confirmation responses
        if message_lower in ["yes", "no", "y", "n", "sure", "cancel"]:
            return "confirmation", {"response": message_lower in ["yes", "y", "sure"]}

        # Check for task patterns
        for category, patterns in self.task_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, message_lower)
                if match:
                    task_data = {"category": category, "matches": match.groups(), "original_message": message}
                    return "task", task_data

        # Check for conversational patterns
        if any(word in message_lower for word in ["hello", "hi", "hey", "how are you"]):
            return "conversation", {"type": "greeting"}

        if any(word in message_lower for word in ["thank", "thanks"]):
            return "conversation", {"type": "thanks"}

        if any(word in message_lower for word in ["help", "what can you do"]):
            return "conversation", {"type": "help"}

        # Default to task if it looks like a command
        if any(word in message_lower for word in ["run", "execute", "do", "make", "create", "list", "show", "get"]):
            return "task", {"category": "general", "original_message": message}

        return "conversation", {"type": "unknown"}

    def _handle_state_specific(self, context: ConversationContext, user_message: str) -> Optional[Dict[str, Any]]:
        """
        Handle state-specific message processing for multi-turn dialogue.

        Returns:
            Response if state-specific handling applies, None otherwise
        """
        state = context.conversation_state

        if state == "awaiting_feedback" and context.pending_feedback:
            # Handle feedback for previous task
            return self._handle_pending_feedback(context, user_message)

        elif state == "awaiting_confirmation" and context.current_task:
            # Handle confirmation for pending task
            return self._handle_confirmation(context, user_message)

        elif state == "task_in_progress":
            # Check if user is asking about task status or wants to modify
            if any(word in user_message.lower() for word in ["status", "how's it going", "progress", "done"]):
                return self._handle_task_status_query(context, user_message)

        return None

    def _update_conversation_state(self, context: ConversationContext, response: Dict[str, Any]):
        """Update conversation state based on response."""
        response_type = response.get("type", "")

        if response_type == "task_started":
            context.set_state("task_in_progress")
        elif response_type == "feedback_request":
            context.set_state("awaiting_feedback")
        elif response_type == "confirmation":
            context.set_state("awaiting_confirmation")
        elif response_type in ["task_completed", "task_failed", "error"]:
            context.set_state("idle")
        # Other states remain as they are

    def _handle_pending_feedback(self, context: ConversationContext, user_message: str) -> Dict[str, Any]:
        """Handle feedback for a pending task."""
        # Process feedback
        feedback_response = self._handle_feedback(context, user_message)

        # Clear pending feedback and reset state
        context.pending_feedback = None
        context.set_state("idle")

        return feedback_response

    def _handle_confirmation(self, context: ConversationContext, user_message: str) -> Dict[str, Any]:
        """Handle confirmation for a pending task."""
        message_lower = user_message.lower().strip()

        if message_lower in ["yes", "y", "sure", "go ahead", "confirm"]:
            # Proceed with task
            context.set_state("task_in_progress")
            return {"message": "Great! Proceeding with the task.", "type": "confirmation_accepted"}
        elif message_lower in ["no", "n", "cancel", "stop"]:
            # Cancel task
            context.current_task = None
            context.set_state("idle")
            return {"message": "Task cancelled. What else can I help you with?", "type": "confirmation_declined"}
        else:
            return {"message": "Please respond with yes or no.", "type": "confirmation_retry"}

    def _handle_task_status_query(self, context: ConversationContext, user_message: str) -> Dict[str, Any]:
        """Handle queries about current task status."""
        if context.current_task:
            task_desc = context.current_task.get("description", "the current task")
            return {
                "message": f"I'm currently working on: {task_desc}. I'll let you know when it's complete.",
                "type": "status_update",
            }
        else:
            return {
                "message": "I'm not currently working on any tasks. What would you like me to do?",
                "type": "status_idle",
            }

    def _handle_task(self, context: ConversationContext, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle task execution requests."""
        try:
            # Convert natural language to structured task
            structured_task = self._nl_to_structured_task(task_data)

            # Execute task through coordinator if available
            if self.coordinator:
                task_result = self._execute_task_with_coordinator(structured_task)
                if task_result:
                    # Task executed successfully
                    context.add_completed_task(structured_task)
                    return {
                        "message": self.response_templates["task_completed"].format(
                            summary=task_result.get("summary", "Task completed successfully")
                        ),
                        "type": "task_completed",
                        "task": structured_task,
                        "result": task_result,
                        "metadata": {"task_id": f"task_{int(datetime.now().timestamp())}"},
                    }

            # Fallback: simulate task execution
            response_message = self.response_templates["task_started"].format(
                task_description=structured_task.get("description", "your request")
            )

            # Store current task in context
            context.current_task = structured_task

            return {
                "message": response_message,
                "type": "task_started",
                "task": structured_task,
                "metadata": {"task_id": f"task_{int(datetime.now().timestamp())}"},
            }

        except Exception as e:
            return {"message": self.response_templates["task_failed"].format(error_message=str(e)), "type": "error"}

    def _execute_task_with_coordinator(self, structured_task: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Execute task using the coordinator.

        Returns:
            Task result if successful, None otherwise
        """
        try:
            # Use the coordinator's NLI task processing method
            result = self.coordinator.process_nli_task(structured_task)

            if result and result.get("success"):
                return {
                    "success": True,
                    "summary": result.get("summary", "Task completed successfully"),
                    "result": result,
                }

            return None

        except Exception as e:
            logger.error(f"Coordinator task execution failed: {e}")
            return None

    def _nl_to_structured_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert natural language task data to structured format."""
        category = task_data.get("category", "general")

        if category == "file_operations":
            matches = task_data.get("matches", [])
            if "list" in task_data["original_message"].lower():
                return {
                    "type": "bash",
                    "description": f"List files in {matches[0] if matches else 'current directory'}",
                    "command": f"ls -la {matches[0] if matches else '.'}",
                }
            elif "read" in task_data["original_message"].lower():
                return {
                    "type": "bash",
                    "description": f"Read file {matches[0] if matches else 'unknown'}",
                    "command": f"cat {matches[0] if matches else 'file.txt'}",
                }

        elif category == "system_info":
            return {"type": "bash", "description": "Get system information", "command": "uname -a && df -h && free -h"}

        elif category == "web_tasks":
            matches = task_data.get("matches", [])
            if "search" in task_data["original_message"].lower():
                return {
                    "type": "web_search",
                    "description": f"Search for {matches[0] if matches else 'information'}",
                    "query": matches[0] if matches else "general search",
                }
            elif "screenshot" in task_data["original_message"].lower():
                return {"type": "screenshot", "description": "Take a screenshot", "command": "take_screenshot"}

        # Default fallback
        return {
            "type": "general",
            "description": task_data.get("original_message", "General task"),
            "original": task_data,
        }

    def _handle_feedback(self, context: ConversationContext, message: str) -> Dict[str, Any]:
        """Handle user feedback with preference learning integration."""
        feedback_rating = message.lower().strip()

        rating_map = {
            "good": 1.0,
            "great": 1.0,
            "excellent": 1.0,
            "bad": 0.0,
            "terrible": 0.0,
            "poor": 0.0,
            "ok": 0.5,
            "fine": 0.5,
            "indifferent": 0.5,
        }

        rating = rating_map.get(feedback_rating, 0.5)

        # Store feedback for learning
        if context.pending_feedback:
            context.pending_feedback["rating"] = rating
            context.pending_feedback["timestamp"] = datetime.now().isoformat()

            # Send to preference collector for DPO learning
            self._collect_preference_feedback(context.pending_feedback)

        # Request feedback after tasks if not already pending
        elif context.current_task and context.conversation_state == "idle":
            context.pending_feedback = {
                "task": context.current_task,
                "rating": rating,
                "timestamp": datetime.now().isoformat(),
            }
            self._collect_preference_feedback(context.pending_feedback)

        return {
            "message": "Thanks for the feedback! I'll use it to improve my performance.",
            "type": "feedback_acknowledged",
            "rating": rating,
        }

    def _collect_preference_feedback(self, feedback_data: Dict[str, Any]):
        """Send feedback to preference collector for DPO learning."""
        try:
            # Extract feedback components
            rating = feedback_data.get("rating", 0.5)
            task = feedback_data.get("task", {})
            task_description = task.get("description", "Unknown task")

            # Get parameters used (from coordinator's current grok client settings)
            # In a real implementation, we'd track which parameters were used for each task
            params_used = {
                "temperature": getattr(self.coordinator.grok_client, "temperature", 0.7),
                "max_tokens": getattr(self.coordinator.grok_client, "max_tokens", 200),
                "timeout": getattr(self.coordinator.grok_client, "timeout", 15),
            }

            # Send to preference collector
            success = self.coordinator.preference_collector.collect_human_feedback(
                task_description=task_description,
                params_used=params_used,
                human_rating=rating,
                task_context={"source": "nli", "timestamp": feedback_data.get("timestamp")},
            )

            if success:
                logger.info(f"Successfully collected human feedback for DPO training: rating={rating}")
            else:
                logger.warning("Failed to collect human feedback for DPO training")

        except Exception as e:
            logger.warning(f"Failed to collect preference feedback: {e}")

    def request_feedback(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """
        Request feedback from user about recent task performance.

        Returns:
            Feedback request response if applicable, None otherwise
        """
        context = self.conversations.get(conversation_id)
        if not context or not context.current_task:
            return None

        # Set up pending feedback
        context.pending_feedback = {"task": context.current_task, "timestamp": datetime.now().isoformat()}
        context.set_state("awaiting_feedback")

        return {"message": self.response_templates["feedback_request"], "type": "feedback_request"}

    def _handle_clarification(self, context: ConversationContext, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle requests for clarification."""
        return {
            "message": self.response_templates["clarification_needed"].format(
                question="What specific task would you like me to perform?"
            ),
            "type": "clarification",
        }

    def _handle_conversation(self, context: ConversationContext, message: str) -> Dict[str, Any]:
        """Handle general conversation."""
        message_lower = message.lower()

        if "help" in message_lower or "what can you do" in message_lower:
            help_text = """
I can help you with:
• File operations (list, read, create files)
• System information (check CPU, memory, disk)
• Web tasks (search, screenshots)
• Automation (run commands, repeat tasks)
• General computer control

Just tell me what you'd like to do in natural language!
            """
            return {"message": help_text.strip(), "type": "help"}

        elif any(word in message_lower for word in ["hello", "hi", "hey"]):
            return {"message": "Hello! How can I assist you today?", "type": "greeting"}

        elif "thank" in message_lower:
            return {"message": "You're welcome! Let me know if you need anything else.", "type": "thanks"}

        else:
            return {"message": "I'm here to help! What would you like to do?", "type": "general"}

    def get_conversation_history(self, conversation_id: str) -> Optional[List[Dict[str, Any]]]:
        """Get conversation history."""
        context = self.conversations.get(conversation_id)
        return context.messages if context else None

    async def _persist_messages_async(self, conversation_id: str, user_message: str, response: Dict[str, Any]):
        """Asynchronously persist messages to cache."""
        try:
            # Save user message
            await self.cache_manager.cache.save_message(
                conversation_id=conversation_id,
                message_id=f"msg_{conversation_id}_{int(datetime.now().timestamp())}",
                role="user",
                content=user_message,
                metadata={"intent": getattr(self, "last_intent", None)},
            )

            # Save assistant response
            await self.cache_manager.cache.save_message(
                conversation_id=conversation_id,
                message_id=f"resp_{conversation_id}_{int(datetime.now().timestamp())}",
                role="assistant",
                content=response["message"],
                metadata={"type": response.get("type"), "task": response.get("task")},
            )

        except Exception as e:
            logger.warning(f"Failed to persist messages: {e}")

    def end_conversation(self, conversation_id: str):
        """End a conversation and clean up."""
        if conversation_id in self.conversations:
            # Persist final state if cache manager available
            if self.cache_manager:
                asyncio.create_task(self.cache_manager.end_conversation(conversation_id))

            del self.conversations[conversation_id]
            logger.info(f"Ended conversation {conversation_id}")


# Example usage and testing
if __name__ == "__main__":
    # Mock coordinator for testing
    class MockCoordinator:
        def __init__(self):
            from src.self_improvement.dpo_optimizer import AgentDPO
            from src.self_improvement.preference_collector import PreferenceCollector
            from src.grok_client import GrokClient

            param_space = {"temperature": (0.1, 1.0), "max_tokens": (50, 500), "timeout": (5, 30)}
            self.dpo_optimizer = AgentDPO(param_space)
            self.preference_collector = PreferenceCollector(self.dpo_optimizer, GrokClient())
            self.grok_client = GrokClient()

        def process_nli_task(self, task_data):
            # Mock task processing
            return {
                "task_id": f"mock_{int(datetime.now().timestamp())}",
                "success": True,
                "result": {"output": f"Mock execution of: {task_data.get('description', 'task')}"},
                "summary": f"Successfully executed: {task_data.get('description', 'task')}",
            }

    # Initialize NLI with mock coordinator
    coordinator = MockCoordinator()
    nli = NaturalLanguageInterface(coordinator)

    def test_conversation():
        """Test a sample conversation flow."""
        print("=== Natural Language Interface Test ===\n")

        # Start conversation
        conv_id = nli.start_conversation("test_user")
        print(f"Started conversation: {conv_id}\n")

        # Test various interactions
        test_messages = [
            "hello",
            "list files in current directory",
            "good",  # feedback
            "what can you do",
            "run a command to check system info",
            "great",  # feedback
            "take a screenshot",
            "ok",  # feedback
        ]

        for i, message in enumerate(test_messages, 1):
            print(f"User: {message}")
            response = nli.process_message(conv_id, message)
            print(f"NLI: {response['message']}")
            print(f"Type: {response.get('type', 'unknown')}")
            if "task" in response:
                print(f"Task: {response['task']}")
            print(f"--- Interaction {i} ---\n")

        # Test conversation history
        history = nli.get_conversation_history(conv_id)
        print(f"Conversation had {len(history)} messages")

        # End conversation
        nli.end_conversation(conv_id)
        print("Conversation ended.")

    # Run the test
    test_conversation()
