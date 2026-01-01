"""
GG Workflow Framework

Python-native workflow orchestration system with AI-powered nodes.
Combines n8n-style visual logic with Grokputer's Pantheon agents.

Features:
- HTTP, Transform, Conditional, AI nodes
- Notion, Asana, Slack integrations
- Pantheon agent delegation
- Multi-provider AI consensus (MAF)
- Async execution with MessageBus
- Self-healing and learning

Author: Grokputer Team
Date: 2026-01-01
"""

from .engine import WorkflowEngine
from .flow import Workflow
from .healing import HealingAction, HealingStrategy, WorkflowHealer, with_healing
from .learning import (
    OptimizationSuggestion,
    PantheonLearnerIntegration,
    WorkflowLearner,
    WorkflowMetrics,
)
from .messagebus_adapter import MessageBusAdapter, MessageBusNode
from .nodes import (
    AINode,
    AsanaNode,
    BaseNode,
    ConditionalNode,
    HTTPNode,
    NodeContext,
    NotionNode,
    SlackNode,
    TransformNode,
)
from .pantheon_integration import PantheonAgent, PantheonIntegration, get_pantheon
from .state import (
    MemoryBackend,
    RedisBackend,
    SQLiteBackend,
    StateBackend,
    WorkflowState,
    create_state,
)

__version__ = "0.1.0"

__all__ = [
    # Core
    "Workflow",
    "WorkflowEngine",
    # Nodes
    "BaseNode",
    "NodeContext",
    "HTTPNode",
    "ConditionalNode",
    "TransformNode",
    "AINode",
    "NotionNode",
    "AsanaNode",
    "SlackNode",
    # State Management
    "WorkflowState",
    "StateBackend",
    "MemoryBackend",
    "SQLiteBackend",
    "RedisBackend",
    "create_state",
    # Pantheon Integration
    "PantheonIntegration",
    "PantheonAgent",
    "get_pantheon",
    # MessageBus
    "MessageBusNode",
    "MessageBusAdapter",
    # Learning & Optimization
    "WorkflowLearner",
    "WorkflowMetrics",
    "OptimizationSuggestion",
    "PantheonLearnerIntegration",
    # Self-Healing
    "WorkflowHealer",
    "HealingStrategy",
    "HealingAction",
    "with_healing",
]
