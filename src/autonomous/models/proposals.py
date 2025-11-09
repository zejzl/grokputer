"""
Pydantic models for code change proposals.
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Literal, Any, Optional
from pydantic import BaseModel, Field


class Alternative(BaseModel):
    """Alternative approach to a proposal."""

    title: str
    description: str
    code_snippet: str
    pros: List[str] = Field(default_factory=list)
    cons: List[str] = Field(default_factory=list)


class Proposal(BaseModel):
    """Code change proposal from ProposalGeneratorAgent."""

    proposal_id: str
    finding_id: str
    title: str
    description: str

    # Changes
    file_path: Path
    old_code: str
    new_code: str
    diff: str  # Unified diff format

    # Risk assessment
    risk_level: Literal["low", "medium", "high", "critical"]
    estimated_effort: str  # "5 minutes", "1 hour", etc.
    breaking_change: bool = False
    requires_migration: bool = False

    # Justification
    rationale: str
    benefits: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    alternatives: List[Alternative] = Field(default_factory=list)

    # Testing
    test_strategy: str = "Run existing test suite"
    test_cases: List[Dict[str, Any]] = Field(default_factory=list)

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    validation: Optional["ValidationResult"] = None

    class Config:
        json_encoders = {
            Path: str,
            datetime: lambda v: v.isoformat()
        }


class ValidationResult(BaseModel):
    """Results from validating a proposal."""

    proposal_id: str
    is_valid: bool
    approval_recommendation: Literal["approve", "reject", "needs_review"]
    confidence: float = Field(ge=0, le=1)

    # Scores
    security_score: float = Field(ge=0, le=1, description="Higher = safer")
    quality_score: float = Field(ge=0, le=1, description="Higher = better")
    risk_score: float = Field(ge=0, le=1, description="Higher = riskier")

    # Issues and feedback
    issues: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)

    validated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# Forward reference resolution
Proposal.model_rebuild()
