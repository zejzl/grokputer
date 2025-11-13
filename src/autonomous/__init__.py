"""
Autonomous AI agent system for code analysis and improvement.

This module provides agents that can scan code, propose improvements,
validate changes, and implement them with human oversight.
"""

__version__ = "0.1.0"

from .scanner import CodeScannerAgent
from .proposer import ProposalGeneratorAgent

__all__ = [
    "CodeScannerAgent",
    "ProposalGeneratorAgent",
]
