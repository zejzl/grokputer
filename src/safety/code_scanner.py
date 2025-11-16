"""
AST-Based Code Security Scanner
==============================

Uses Python AST to analyze code for security vulnerabilities.
Detects shell injection, unsafe imports, and other security issues.
"""

import ast
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class SecurityVulnerability:
    """Represents a detected security vulnerability."""

    def __init__(self, vuln_type: str, severity: str, location: str, description: str, code_snippet: str = ""):
        self.vuln_type = vuln_type
        self.severity = severity  # CRITICAL, HIGH, MEDIUM, LOW
        self.location = location  # file:line
        self.description = description
        self.code_snippet = code_snippet

    def __str__(self):
        return f"[{self.severity}] {self.vuln_type}: {self.description} at {self.location}"


class CodeSecurityScanner:
    """
    AST-based security scanner for Python code.
    Analyzes code for common security vulnerabilities.
    """

    # Dangerous shell metacharacters
    SHELL_METACHARS = {";", "&", "|", "<", ">", "$", "`", "\\", "%", "(", ")"}

    # Dangerous functions that can execute shell commands
    DANGEROUS_FUNCTIONS = {
        "os.system",
        "os.popen",
        "os.popen2",
        "os.popen3",
        "os.popen4",
        "subprocess.call",
        "subprocess.run",
        "subprocess.Popen",
        "commands.getoutput",
        "commands.getstatusoutput",
        "eval",
        "exec",
        "compile",
    }

    # Unsafe imports
    UNSAFE_IMPORTS = {
        "pickle",
        "shelve",
        "marshal",
        "yaml",  # Can lead to code execution
        "tempfile",  # Often misused
    }

    def __init__(self):
        self.vulnerabilities: List[SecurityVulnerability] = []
        self.current_file = ""

    def scan_file(self, file_path: str) -> List[SecurityVulnerability]:
        """
        Scan a Python file for security vulnerabilities.

        Args:
            file_path: Path to the Python file

        Returns:
            List of detected vulnerabilities
        """
        self.current_file = file_path
        self.vulnerabilities = []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                source_code = f.read()

            tree = ast.parse(source_code, filename=file_path)
            self._analyze_ast(tree, source_code)

        except SyntaxError as e:
            vuln = SecurityVulnerability(
                vuln_type="SYNTAX_ERROR",
                severity="MEDIUM",
                location=f"{file_path}:{e.lineno}",
                description=f"Syntax error that could hide malicious code: {e.msg}",
                code_snippet=str(e),
            )
            self.vulnerabilities.append(vuln)

        except Exception as e:
            logger.error(f"Error scanning {file_path}: {e}")

        return self.vulnerabilities

    def scan_directory(
        self, dir_path: str, exclude_patterns: List[str] = None
    ) -> Dict[str, List[SecurityVulnerability]]:
        """
        Scan all Python files in a directory.

        Args:
            dir_path: Directory to scan
            exclude_patterns: Glob patterns to exclude

        Returns:
            Dict mapping file paths to vulnerability lists
        """
        if exclude_patterns is None:
            exclude_patterns = ["__pycache__", "*.pyc", ".git", "node_modules"]

        results = {}
        path_obj = Path(dir_path)

        for py_file in path_obj.rglob("*.py"):
            # Check exclude patterns
            excluded = False
            for pattern in exclude_patterns:
                if pattern in str(py_file):
                    excluded = True
                    break

            if not excluded:
                vulns = self.scan_file(str(py_file))
                if vulns:
                    results[str(py_file)] = vulns

        return results

    def _analyze_ast(self, tree: ast.AST, source_code: str):
        """Analyze the AST for security issues."""
        visitor = SecurityASTVisitor(self, source_code)
        visitor.visit(tree)

    def _add_vulnerability(self, vuln_type: str, severity: str, node: ast.AST, description: str):
        """Add a vulnerability finding."""
        line_no = getattr(node, "lineno", 0)
        location = f"{self.current_file}:{line_no}"

        # Extract code snippet
        lines = source_code.split("\n")
        start_line = max(0, line_no - 2)
        end_line = min(len(lines), line_no + 2)
        code_snippet = "\n".join(lines[start_line:end_line])

        vuln = SecurityVulnerability(
            vuln_type=vuln_type,
            severity=severity,
            location=location,
            description=description,
            code_snippet=code_snippet,
        )

        self.vulnerabilities.append(vuln)


class SecurityASTVisitor(ast.NodeVisitor):
    """AST visitor that detects security vulnerabilities."""

    def __init__(self, scanner: CodeSecurityScanner, source_code: str):
        self.scanner = scanner
        self.source_code = source_code

    def visit_Call(self, node: ast.Call):
        """Check function calls for dangerous operations."""
        func_name = self._get_func_name(node.func)

        # Check for dangerous function calls
        if func_name in CodeSecurityScanner.DANGEROUS_FUNCTIONS:
            severity = "CRITICAL" if func_name in ["eval", "exec"] else "HIGH"
            self.scanner._add_vulnerability(
                "DANGEROUS_FUNCTION",
                severity,
                node,
                f"Call to dangerous function '{func_name}' that can execute arbitrary code",
            )

        # Check for shell injection in subprocess calls
        if func_name in ["subprocess.call", "subprocess.run", "subprocess.Popen", "os.system", "os.popen"]:
            self._check_shell_injection(node)

        self.generic_visit(node)

    def visit_Import(self, node: ast.Import):
        """Check imports for unsafe modules."""
        for alias in node.names:
            if alias.name in CodeSecurityScanner.UNSAFE_IMPORTS:
                self.scanner._add_vulnerability(
                    "UNSAFE_IMPORT", "MEDIUM", node, f"Import of potentially unsafe module '{alias.name}'"
                )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        """Check from imports for unsafe modules."""
        if node.module in CodeSecurityScanner.UNSAFE_IMPORTS:
            self.scanner._add_vulnerability(
                "UNSAFE_IMPORT", "MEDIUM", node, f"Import from potentially unsafe module '{node.module}'"
            )
        self.generic_visit(node)

    def visit_Str(self, node: ast.Str):
        """Check string literals for suspicious patterns."""
        # Check for embedded shell commands in strings
        if any(char in node.s for char in CodeSecurityScanner.SHELL_METACHARS):
            # More sophisticated check - look for command-like patterns
            suspicious_patterns = [
                r"\b(rm|del|format|shutdown|reboot)\b",
                r"\b(sudo|su)\b",
                r"\b(/bin/|/usr/bin/|/sbin/)\b",
            ]

            for pattern in suspicious_patterns:
                if re.search(pattern, node.s, re.IGNORECASE):
                    self.scanner._add_vulnerability(
                        "SUSPICIOUS_STRING",
                        "MEDIUM",
                        node,
                        f"String contains suspicious command-like pattern: {pattern}",
                    )
                    break

        self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant):
        """Check constant values (Python 3.8+)."""
        if isinstance(node.value, str):
            self.visit_Str(ast.Str(s=node.value, lineno=node.lineno, col_offset=getattr(node, "col_offset", 0)))
        self.generic_visit(node)

    def _check_shell_injection(self, node: ast.Call):
        """Check for potential shell injection vulnerabilities."""
        # Look for shell=True parameter
        shell_true = False
        for kw in node.keywords:
            if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                shell_true = True
                break
            elif kw.arg == "shell" and isinstance(kw.value, ast.Name) and kw.value.id == "True":
                shell_true = True
                break

        if shell_true:
            # Check arguments for user input
            for arg in node.args:
                if self._contains_user_input(arg):
                    self.scanner._add_vulnerability(
                        "SHELL_INJECTION",
                        "CRITICAL",
                        node,
                        "Potential shell injection: shell=True with user-controllable input",
                    )
                    return

            # Even without obvious user input, shell=True is risky
            self.scanner._add_vulnerability(
                "SHELL_INJECTION_RISK", "HIGH", node, "Use of shell=True increases command injection risk"
            )

    def _contains_user_input(self, node: ast.AST) -> bool:
        """Check if an AST node likely contains user input."""
        # Simple heuristic: look for variables that might contain user input
        if isinstance(node, ast.Name):
            # Common user input variable names
            user_input_names = {"input", "args", "argv", "request", "query", "data", "params"}
            return node.id.lower() in user_input_names

        elif isinstance(node, ast.Attribute):
            # obj.attr patterns that might be user input
            if isinstance(node.value, ast.Name):
                attr_patterns = {"request.", "args.", "form.", "data.", "params."}
                return any(node.value.id + "." + node.attr == pattern for pattern in attr_patterns)

        elif isinstance(node, ast.Subscript):
            # array[index] patterns
            return self._contains_user_input(node.value)

        return False

    def _get_func_name(self, node: ast.AST) -> str:
        """Get the full function name from an AST node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return self._get_func_name(node.value) + "." + node.attr
        return ""


def scan_project_for_vulnerabilities(
    project_path: str = ".", output_file: str = None
) -> Dict[str, List[SecurityVulnerability]]:
    """
    Scan an entire project for security vulnerabilities.

    Args:
        project_path: Path to the project root
        output_file: Optional file to save results

    Returns:
        Dict mapping file paths to vulnerability lists
    """
    scanner = CodeSecurityScanner()
    results = scanner.scan_directory(project_path)

    if output_file:
        with open(output_file, "w") as f:
            f.write("# Security Scan Results\n\n")
            total_vulns = sum(len(vulns) for vulns in results.values())

            f.write(f"Total vulnerabilities found: {total_vulns}\n\n")

            for file_path, vulns in results.items():
                f.write(f"## {file_path}\n\n")
                for vuln in vulns:
                    f.write(f"- {vuln}\n")
                f.write("\n")

    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="AST-Based Code Security Scanner")
    parser.add_argument("--path", default=".", help="Path to scan")
    parser.add_argument("--output", help="Output file for results")

    args = parser.parse_args()

    print(f"Scanning {args.path} for security vulnerabilities...")
    results = scan_project_for_vulnerabilities(args.path, args.output)

    total_vulns = sum(len(vulns) for vulns in results.values())
    print(f"Scan complete. Found {total_vulns} vulnerabilities in {len(results)} files.")

    if results:
        print("\nVulnerabilities found:")
        for file_path, vulns in results.items():
            print(f"\n{file_path}:")
            for vuln in vulns:
                print(f"  {vuln}")
    else:
        print("No vulnerabilities detected.")
