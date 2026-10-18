"""CodeSecurityScanner must work on current Python (ast.Str is gone in 3.12+)."""
import ast

from src.agents.documentation_agent import DocumentationAgent
from src.safety.code_scanner import CodeSecurityScanner


def _scan(tmp_path, source):
    path = tmp_path / "sample.py"
    path.write_text(source, encoding="utf-8")
    return CodeSecurityScanner().scan_file(str(path))


def test_flags_dangerous_call_and_unsafe_import(tmp_path):
    found = _scan(tmp_path, "import pickle\neval(input())\n")
    types = {v.vuln_type for v in found}
    assert "DANGEROUS_FUNCTION" in types
    assert "UNSAFE_IMPORT" in types


def test_flags_suspicious_string_literal(tmp_path):
    found = _scan(tmp_path, 'cmd = "sudo rm -rf / ; echo done"\n')
    assert any(v.vuln_type == "SUSPICIOUS_STRING" for v in found)


def test_code_snippet_comes_from_scanned_source(tmp_path):
    found = _scan(tmp_path, "x = 1\neval('2')\n")
    assert found and "eval" in found[0].code_snippet


def test_docstring_extraction_uses_constant():
    body = ast.parse('"""hello"""\nx = 1').body
    assert DocumentationAgent._get_docstring(None, body) == "hello"
