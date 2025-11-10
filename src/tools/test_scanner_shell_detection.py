#!/usr/bin/env python3
"""
Test the improved scanner's shell injection detection.
"""

import asyncio
import tempfile
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from autonomous.scanner import CodeScannerAgent


async def test_shell_detection():
    """Test that scanner detects shell=True vulnerabilities."""
    print("\n=== Testing Shell Injection Detection ===\n")

    scanner = CodeScannerAgent()

    # Test code with shell=True (VULNERABLE)
    vulnerable_code = '''
import subprocess

def run_command(user_input):
    # VULNERABLE: shell=True
    result = subprocess.run(
        user_input,
        shell=True,  # This should be detected!
        capture_output=True
    )
    return result.stdout

def another_command():
    subprocess.call("ls -la", shell=True)  # Also vulnerable
'''

    # Test code with shell=False (SECURE)
    secure_code = '''
import subprocess
import shlex

def run_command_safe(user_input):
    # SECURE: shell=False with shlex
    argv = shlex.split(user_input)
    result = subprocess.run(
        argv,
        shell=False,  # Safe!
        capture_output=True
    )
    return result.stdout
'''

    # Test vulnerable code
    print("1. Scanning VULNERABLE code (shell=True):")
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(vulnerable_code)
        f.flush()
        temp_path = Path(f.name)

    try:
        findings = await scanner.scan_file(temp_path)
        shell_findings = [f for f in findings if 'shell' in f.description.lower() and f.severity == 'critical']

        print(f"   Found {len(shell_findings)} shell injection vulnerabilities")
        for finding in shell_findings:
            print(f"   - Line {finding.line_number}: {finding.description}")
            print(f"     Severity: {finding.severity}")
            print(f"     Recommendation: {finding.recommendation[:100]}...")
        print()

        if len(shell_findings) == 2:
            print("   [OK] Detected both shell=True instances!")
        else:
            print(f"   [WARN] Expected 2 findings, got {len(shell_findings)}")
    finally:
        temp_path.unlink()

    # Test secure code
    print("\n2. Scanning SECURE code (shell=False):")
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(secure_code)
        f.flush()
        temp_path = Path(f.name)

    try:
        findings = await scanner.scan_file(temp_path)
        shell_findings = [f for f in findings if 'shell' in f.description.lower() and f.severity == 'critical']

        print(f"   Found {len(shell_findings)} shell injection vulnerabilities")

        if len(shell_findings) == 0:
            print("   [OK] No false positives - secure code passed!")
        else:
            print(f"   [WARN] False positive detected!")
            for finding in shell_findings:
                print(f"   - {finding.description}")
    finally:
        temp_path.unlink()


async def test_real_executor():
    """Test scanning the actual fixed executor.py."""
    print("\n=== Scanning Fixed executor.py ===\n")

    scanner = CodeScannerAgent()
    executor_path = Path("src/executor.py")

    if not executor_path.exists():
        print(f"   [SKIP] {executor_path} not found")
        return

    findings = await scanner.scan_file(executor_path)
    shell_findings = [f for f in findings if 'shell' in f.description.lower() and f.severity == 'critical']

    print(f"   Found {len(shell_findings)} shell injection vulnerabilities in executor.py")

    if len(shell_findings) == 0:
        print("   [OK] Fixed executor.py has NO shell injection vulnerabilities!")
    else:
        print("   [WARN] Still has shell injection issues:")
        for finding in shell_findings:
            print(f"   - Line {finding.line_number}: {finding.description}")


async def main():
    print("="*60)
    print("SCANNER SHELL INJECTION DETECTION TEST")
    print("="*60)

    await test_shell_detection()
    await test_real_executor()

    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)


if __name__ == '__main__':
    asyncio.run(main())
