"""
Pydantic models for autonomous agent system.
"""

from .findings import Finding, CodeSmell, ScanReport
from .proposals import Proposal, Alternative, ValidationResult

__all__ = [
    "Finding",
    "CodeSmell",
    "ScanReport",
    "Proposal",
    "Alternative",
    "ValidationResult",
]
