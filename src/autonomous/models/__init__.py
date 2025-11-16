"""
Pydantic models for autonomous agent system.
"""

from .findings import CodeSmell, Finding, ScanReport
from .proposals import Alternative, Proposal, ValidationResult

__all__ = [
    "Finding",
    "CodeSmell",
    "ScanReport",
    "Proposal",
    "Alternative",
    "ValidationResult",
]
