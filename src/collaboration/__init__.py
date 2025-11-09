"""
Collaboration module for multi-agent coordination via MessageBus.
"""

from src.collaboration.message_models import (
    MessageType,
    AgentRole,
    CollaborationMessage,
    ConsensusSignal,
    FinalPlan
)

__all__ = [
    "MessageType",
    "AgentRole",
    "CollaborationMessage",
    "ConsensusSignal",
    "FinalPlan"
]
