"""
Pydantic models for code analysis findings.
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Literal, Any, Optional
from pydantic import BaseModel, Field


class Finding(BaseModel):
    """Issue discovered by CodeScannerAgent."""

    finding_id: str
    severity: Literal["critical", "high", "medium", "low", "info"]
    category: str  # "security", "quality", "performance", "completeness", "architecture"
    file_path: Path
    line_number: int

    description: str
    code_snippet: str
    recommendation: str
    confidence: float = Field(ge=0, le=1, description="Confidence score 0-1")

    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {
            Path: str,
            datetime: lambda v: v.isoformat()
        }


class CodeSmell(BaseModel):
    """Specific code smell detected in analysis."""

    smell_type: str  # "long_function", "deep_nesting", "duplicate_code", etc.
    severity: Literal["high", "medium", "low"]
    location: str  # "file:line"
    description: str
    suggestion: str

    # Metrics
    complexity_score: Optional[int] = None  # McCabe complexity
    lines_of_code: Optional[int] = None
    nesting_depth: Optional[int] = None


class ScanReport(BaseModel):
    """Complete report from code scanning."""

    report_id: str
    scan_target: str  # File path or directory
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    # Results
    findings: List[Finding] = Field(default_factory=list)
    code_smells: List[CodeSmell] = Field(default_factory=list)

    # Statistics
    files_scanned: int = 0
    total_lines: int = 0
    issues_found: int = 0

    # Breakdown by severity
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    info_count: int = 0

    # Breakdown by category
    security_issues: int = 0
    quality_issues: int = 0
    performance_issues: int = 0
    completeness_issues: int = 0
    architecture_issues: int = 0

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

    def update_statistics(self) -> None:
        """Update statistics from findings list."""
        self.issues_found = len(self.findings)

        # Count by severity
        self.critical_count = sum(1 for f in self.findings if f.severity == "critical")
        self.high_count = sum(1 for f in self.findings if f.severity == "high")
        self.medium_count = sum(1 for f in self.findings if f.severity == "medium")
        self.low_count = sum(1 for f in self.findings if f.severity == "low")
        self.info_count = sum(1 for f in self.findings if f.severity == "info")

        # Count by category
        self.security_issues = sum(1 for f in self.findings if f.category == "security")
        self.quality_issues = sum(1 for f in self.findings if f.category == "quality")
        self.performance_issues = sum(1 for f in self.findings if f.category == "performance")
        self.completeness_issues = sum(1 for f in self.findings if f.category == "completeness")
        self.architecture_issues = sum(1 for f in self.findings if f.category == "architecture")
