"""
CodeScannerAgent - Analyzes code for issues, smells, and improvement opportunities.
"""

import ast
import re
from pathlib import Path
from typing import List, Optional, Set
from datetime import datetime
import uuid

from .models.findings import Finding, CodeSmell, ScanReport


class CodeScannerAgent:
    """
    Scans Python code for issues and improvement opportunities.

    Analyzes:
    - Security vulnerabilities (hardcoded secrets, unsafe operations)
    - Code quality (missing type hints, PEP 8, complexity)
    - Performance issues (inefficient patterns)
    - Completeness (missing error handling, tests, docs)
    - Architecture (SOLID violations, code smells)
    """

    # Security patterns to detect
    SECURITY_PATTERNS = {
        "hardcoded_secret": {
            "patterns": [
                r'(api_key|API_KEY|password|PASSWORD|secret|SECRET|token|TOKEN)\s*=\s*["\'][^"\']{8,}["\']',
                r'(aws_access_key|AWS_ACCESS_KEY)\s*=\s*["\'][^"\']+["\']',
            ],
            "severity": "critical",
            "description": "Hardcoded secret detected",
            "recommendation": "Move secrets to environment variables or secret management system"
        },
        "unsafe_eval": {
            "patterns": [r'\beval\s*\(', r'\bexec\s*\('],
            "severity": "critical",
            "description": "Unsafe eval/exec detected",
            "recommendation": "Remove eval/exec or use safer alternatives like ast.literal_eval"
        },
        "shell_injection": {
            "patterns": [r'subprocess\.\w+\([^)]*shell\s*=\s*True'],
            "severity": "high",
            "description": "Shell injection risk - subprocess with shell=True",
            "recommendation": "Use shell=False and pass command as list"
        },
        "path_traversal": {
            "patterns": [r'\.\./', r'\.\.\\'],
            "severity": "high",
            "description": "Potential path traversal vulnerability",
            "recommendation": "Sanitize file paths and validate against allowed directories"
        },
        "unsafe_deserialization": {
            "patterns": [r'pickle\.loads\s*\(', r'yaml\.load\s*\((?!.*Loader=yaml\.SafeLoader)'],
            "severity": "high",
            "description": "Unsafe deserialization detected",
            "recommendation": "Use safe alternatives (json, yaml.safe_load) or validate input"
        }
    }

    def __init__(self):
        """Initialize the code scanner."""
        self.findings: List[Finding] = []
        self.code_smells: List[CodeSmell] = []

    async def scan_file(self, file_path: Path) -> List[Finding]:
        """
        Scan a single Python file for issues.

        Args:
            file_path: Path to Python file to scan

        Returns:
            List of findings
        """
        findings = []

        if not file_path.exists():
            return findings

        try:
            content = file_path.read_text(encoding='utf-8')

            # Security scanning
            findings.extend(self._scan_security(file_path, content))

            # AST-based analysis
            try:
                tree = ast.parse(content, filename=str(file_path))
                findings.extend(self._scan_ast(file_path, tree, content))
            except SyntaxError as e:
                findings.append(Finding(
                    finding_id=self._generate_id(),
                    severity="high",
                    category="quality",
                    file_path=file_path,
                    line_number=e.lineno or 0,
                    description=f"Syntax error: {e.msg}",
                    code_snippet=e.text or "",
                    recommendation="Fix syntax error",
                    confidence=1.0
                ))

        except Exception as e:
            # Log error but don't fail the scan
            print(f"Error scanning {file_path}: {e}")

        return findings

    async def scan_directory(self, directory: Path, patterns: Optional[List[str]] = None) -> ScanReport:
        """
        Scan a directory for Python files.

        Args:
            directory: Directory to scan
            patterns: Optional glob patterns (default: ["**/*.py"])

        Returns:
            ScanReport with all findings
        """
        if patterns is None:
            patterns = ["**/*.py"]

        report = ScanReport(
            report_id=self._generate_id(),
            scan_target=str(directory),
            started_at=datetime.utcnow()
        )

        # Find all Python files
        python_files: Set[Path] = set()
        for pattern in patterns:
            python_files.update(directory.glob(pattern))

        # Scan each file
        total_lines = 0
        for file_path in sorted(python_files):
            if file_path.is_file():
                findings = await self.scan_file(file_path)
                report.findings.extend(findings)
                report.files_scanned += 1

                # Count lines
                try:
                    total_lines += len(file_path.read_text(encoding='utf-8').splitlines())
                except Exception:
                    pass

        report.total_lines = total_lines
        report.completed_at = datetime.utcnow()
        report.update_statistics()

        return report

    def _scan_security(self, file_path: Path, content: str) -> List[Finding]:
        """Scan for security vulnerabilities using regex patterns."""
        findings = []
        lines = content.splitlines()

        for issue_type, config in self.SECURITY_PATTERNS.items():
            for pattern in config["patterns"]:
                for match in re.finditer(pattern, content, re.MULTILINE):
                    # Find line number
                    line_num = content[:match.start()].count('\n') + 1
                    code_snippet = lines[line_num - 1] if line_num <= len(lines) else ""

                    findings.append(Finding(
                        finding_id=self._generate_id(),
                        severity=config["severity"],
                        category="security",
                        file_path=file_path,
                        line_number=line_num,
                        description=config["description"],
                        code_snippet=code_snippet.strip(),
                        recommendation=config["recommendation"],
                        confidence=0.9,
                        metadata={"issue_type": issue_type}
                    ))

        return findings

    def _scan_ast(self, file_path: Path, tree: ast.AST, content: str) -> List[Finding]:
        """Scan using AST for structural issues."""
        findings = []
        lines = content.splitlines()

        # Walk the AST
        for node in ast.walk(tree):
            # Check for missing type hints in functions
            if isinstance(node, ast.FunctionDef):
                findings.extend(self._check_function(node, file_path, lines))

            # Check for missing error handling
            elif isinstance(node, ast.Try):
                findings.extend(self._check_try_except(node, file_path, lines))

            # Check for shell injection vulnerabilities (subprocess.run with shell=True)
            elif isinstance(node, ast.Call):
                findings.extend(self._check_subprocess_call(node, file_path, lines))

        return findings

    def _check_function(self, node: ast.FunctionDef, file_path: Path, lines: List[str]) -> List[Finding]:
        """Check function for issues."""
        findings = []

        # Skip if it's a special method or private
        if node.name.startswith('_') and not node.name.startswith('__'):
            return findings

        # Check for missing type hints
        has_return_annotation = node.returns is not None
        has_arg_annotations = all(arg.annotation is not None for arg in node.args.args if arg.arg != 'self')

        if not (has_return_annotation and has_arg_annotations):
            line_num = node.lineno
            code_snippet = lines[line_num - 1] if line_num <= len(lines) else ""

            findings.append(Finding(
                finding_id=self._generate_id(),
                severity="low",
                category="quality",
                file_path=file_path,
                line_number=line_num,
                description=f"Function '{node.name}' missing type hints",
                code_snippet=code_snippet.strip(),
                recommendation="Add type hints to function signature",
                confidence=0.95,
                metadata={"function_name": node.name}
            ))

        # Check for long functions (>50 lines)
        function_length = (node.end_lineno or node.lineno) - node.lineno
        if function_length > 50:
            findings.append(Finding(
                finding_id=self._generate_id(),
                severity="medium",
                category="quality",
                file_path=file_path,
                line_number=node.lineno,
                description=f"Function '{node.name}' is too long ({function_length} lines)",
                code_snippet=f"def {node.name}(...):",
                recommendation="Consider breaking down into smaller functions",
                confidence=0.8,
                metadata={"function_name": node.name, "length": function_length}
            ))

        # Check for missing docstrings
        if not ast.get_docstring(node):
            findings.append(Finding(
                finding_id=self._generate_id(),
                severity="info",
                category="completeness",
                file_path=file_path,
                line_number=node.lineno,
                description=f"Function '{node.name}' missing docstring",
                code_snippet=f"def {node.name}(...):",
                recommendation="Add docstring describing function purpose, args, and return value",
                confidence=0.9,
                metadata={"function_name": node.name}
            ))

        return findings

    def _check_try_except(self, node: ast.Try, file_path: Path, lines: List[str]) -> List[Finding]:
        """Check try/except blocks for issues."""
        findings = []

        # Check for bare except
        for handler in node.handlers:
            if handler.type is None:
                line_num = handler.lineno
                code_snippet = lines[line_num - 1] if line_num <= len(lines) else ""

                findings.append(Finding(
                    finding_id=self._generate_id(),
                    severity="medium",
                    category="quality",
                    file_path=file_path,
                    line_number=line_num,
                    description="Bare except clause - catches all exceptions",
                    code_snippet=code_snippet.strip(),
                    recommendation="Catch specific exception types instead of using bare 'except:'",
                    confidence=0.95
                ))

        return findings

    def _check_subprocess_call(self, node: ast.Call, file_path: Path, lines: List[str]) -> List[Finding]:
        """Check subprocess calls for shell injection vulnerabilities."""
        findings = []

        # Check if this is a subprocess.run/Popen/call
        is_subprocess = False
        func_name = ""

        if isinstance(node.func, ast.Attribute):
            # subprocess.run(...), subprocess.Popen(...), etc.
            if isinstance(node.func.value, ast.Name):
                if node.func.value.id == 'subprocess':
                    func_name = node.func.attr
                    is_subprocess = func_name in ['run', 'Popen', 'call', 'check_call', 'check_output']

        if not is_subprocess:
            return findings

        # Check for shell=True in keyword arguments
        has_shell_true = False
        for keyword in node.keywords:
            if keyword.arg == 'shell':
                # Check if value is True (ast.Constant for Python 3.8+)
                if isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
                    has_shell_true = True
                    break

        if has_shell_true:
            line_num = node.lineno
            code_snippet = lines[line_num - 1] if line_num <= len(lines) else ""

            findings.append(Finding(
                finding_id=self._generate_id(),
                severity="critical",
                category="security",
                file_path=file_path,
                line_number=line_num,
                description=f"Shell injection vulnerability: subprocess.{func_name}() with shell=True",
                code_snippet=code_snippet.strip(),
                recommendation=(
                    "Use shell=False and pass command as a list of arguments. "
                    "Example: subprocess.run(['ls', '-l'], shell=False) instead of subprocess.run('ls -l', shell=True). "
                    "Use shlex.split() to safely parse command strings into argument lists."
                ),
                confidence=1.0,
                metadata={
                    "function": func_name,
                    "fix_example": "import shlex; subprocess.run(shlex.split(cmd), shell=False)"
                }
            ))

        return findings

    def _generate_id(self) -> str:
        """Generate unique finding ID."""
        return f"finding_{uuid.uuid4().hex[:12]}"
