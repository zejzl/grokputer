"""
Pydantic models for collaboration messages and signals.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class MessageType(str, Enum):
    """Collaboration message types."""
    PROPOSAL = "proposal"          # Initial idea/plan from agent
    FEEDBACK = "feedback"          # Response to another agent's message
    QUESTION = "question"          # Request for clarification
    AGREEMENT = "agreement"        # Explicit consensus signal
    DISAGREEMENT = "disagreement"  # Explicit conflict signal
    FINAL_PLAN = "final_plan"      # Synthesized output


class AgentRole(str, Enum):
    """Agent identifiers."""
    CLAUDE = "claude"
    GROK = "grok"
    COORDINATOR = "coordinator"


class CollaborationMessage(BaseModel):
    """Base message for agent collaboration."""

    message_id: str = Field(description="Unique message identifier")
    correlation_id: str = Field(description="Thread/conversation ID")
    message_type: MessageType
    sender: AgentRole
    recipient: Optional[AgentRole] = Field(default=None, description="Broadcast if None")

    round_number: int = Field(ge=1, description="Conversation round (1-indexed)")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    content: str = Field(description="Message payload (can be markdown)")
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # References for threading
    in_reply_to: Optional[str] = Field(default=None, description="Parent message_id")

    class Config:
        json_schema_extra = {
            "example": {
                "message_id": "msg_001_claude",
                "correlation_id": "collab_20251108_143052",
                "message_type": "proposal",
                "sender": "claude",
                "recipient": None,
                "round_number": 1,
                "content": "I propose we structure the MCP server with...",
                "metadata": {"api_latency": 1.23, "model": "claude-sonnet-4-5"}
            }
        }


class ConsensusSignal(BaseModel):
    """Signals from consensus detector."""

    is_consensus: bool
    confidence: float = Field(ge=0.0, le=1.0, description="0-1 confidence score")

    agreement_indicators: List[str] = Field(
        default_factory=list,
        description="Keywords/phrases indicating agreement"
    )
    disagreement_indicators: List[str] = Field(
        default_factory=list,
        description="Keywords/phrases indicating conflict"
    )

    convergence_score: float = Field(
        ge=0.0, le=1.0,
        description="Semantic similarity between agent proposals"
    )

    recommendation: str = Field(
        description="CONTINUE | FINALIZE | MEDIATE"
    )

    reasoning: Optional[str] = None


class FinalPlan(BaseModel):
    """Synthesized output from collaboration."""

    task_description: str
    consensus_reached: bool
    total_rounds: int

    claude_perspective: str
    grok_perspective: str
    unified_plan: str

    key_agreements: List[str]
    key_disagreements: List[str] = Field(default_factory=list)

    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Metrics: API costs, latency, token counts"
    )
