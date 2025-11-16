"""
Autonomous AI agent system for code analysis and improvement.

This module provides agents that can scan code, propose improvements,
validate changes, and implement them with human oversight.
"""

__version__ = "0.1.0"

from .proposer import ProposalGeneratorAgent
from .scanner import CodeScannerAgent

__all__ = [
    "CodeScannerAgent",
    "ProposalGeneratorAgent",
]
