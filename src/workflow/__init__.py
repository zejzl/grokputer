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
Date: 2025-11-16
"""

from .engine import WorkflowEngine
from .flow import Workflow
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
]
