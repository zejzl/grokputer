"""
Unit tests for CodeScannerAgent.
"""

import pytest
from pathlib import Path
import tempfile
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from autonomous.scanner import CodeScannerAgent


@pytest.mark.asyncio
async def test_scanner_detects_hardcoded_secret():
    """Test that scanner detects hardcoded secrets."""
    scanner = CodeScannerAgent()

    # Create temp file with hardcoded secret
    code = '''
API_KEY = "sk_live_1234567890abcdef"
password = "my_super_secret_password"

def connect():
    return API_KEY
'''

    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(code)
        f.flush()
        temp_path = Path(f.name)

    try:
        findings = await scanner.scan_file(temp_path)

        # Should detect at least one hardcoded secret
        secret_findings = [f for f in findings if f.category == 'security' and 'secret' in f.description.lower()]
        assert len(secret_findings) > 0, "Should detect hardcoded secrets"

        # Check severity
        for finding in secret_findings:
            assert finding.severity == 'critical', "Hardcoded secrets should be critical severity"

    finally:
        temp_path.unlink()


@pytest.mark.asyncio
async def test_scanner_detects_unsafe_eval():
    """Test that scanner detects eval/exec usage."""
    scanner = CodeScannerAgent()

    code = '''
def dangerous_function(user_input):
    result = eval(user_input)
    return result
'''

    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(code)
        f.flush()
        temp_path = Path(f.name)

    try:
        findings = await scanner.scan_file(temp_path)

        # Should detect eval usage
        eval_findings = [f for f in findings if 'eval' in f.description.lower()]
        assert len(eval_findings) > 0, "Should detect unsafe eval"

        # Check severity
        assert eval_findings[0].severity == 'critical'

    finally:
        temp_path.unlink()


@pytest.mark.asyncio
async def test_scanner_detects_missing_type_hints():
    """Test that scanner detects missing type hints."""
    scanner = CodeScannerAgent()

    code = '''
def calculate_sum(a, b):
    return a + b

def get_name():
    return "Alice"
'''

    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(code)
        f.flush()
        temp_path = Path(f.name)

    try:
        findings = await scanner.scan_file(temp_path)

        # Should detect missing type hints
        type_hint_findings = [f for f in findings if 'type hint' in f.description.lower()]
        assert len(type_hint_findings) >= 2, "Should detect missing type hints for both functions"

    finally:
        temp_path.unlink()


@pytest.mark.asyncio
async def test_scanner_detects_long_function():
    """Test that scanner detects long functions."""
    scanner = CodeScannerAgent()

    # Create a function with 60 lines
    lines = ['def long_function():']
    for i in range(60):
        lines.append(f'    x{i} = {i}')
    lines.append('    return x0')

    code = '\n'.join(lines)

    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(code)
        f.flush()
        temp_path = Path(f.name)

    try:
        findings = await scanner.scan_file(temp_path)

        # Should detect long function
        long_func_findings = [f for f in findings if 'too long' in f.description.lower()]
        assert len(long_func_findings) > 0, "Should detect long function"

    finally:
        temp_path.unlink()


@pytest.mark.asyncio
async def test_scanner_detects_bare_except():
    """Test that scanner detects bare except clauses."""
    scanner = CodeScannerAgent()

    code = '''
def risky_operation():
    try:
        dangerous_call()
    except:
        pass
'''

    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(code)
        f.flush()
        temp_path = Path(f.name)

    try:
        findings = await scanner.scan_file(temp_path)

        # Should detect bare except
        bare_except_findings = [f for f in findings if 'bare except' in f.description.lower()]
        assert len(bare_except_findings) > 0, "Should detect bare except clause"

    finally:
        temp_path.unlink()


@pytest.mark.asyncio
async def test_scan_report_statistics():
    """Test that scan report calculates statistics correctly."""
    scanner = CodeScannerAgent()

    code = '''
API_KEY = "secret123"  # Critical security issue

def func1():  # Missing type hints (low)
    pass

def func2():  # Missing type hints (low)
    try:
        pass
    except:  # Bare except (medium)
        pass
'''

    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(code)
        f.flush()
        temp_path = Path(f.name)

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            dest_file = tmpdir_path / 'test.py'
            dest_file.write_text(code)

            report = await scanner.scan_directory(tmpdir_path)

            # Check statistics
            assert report.files_scanned == 1
            assert report.issues_found > 0
            assert report.critical_count >= 1  # Hardcoded secret
            assert report.security_issues >= 1

    finally:
        temp_path.unlink()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
