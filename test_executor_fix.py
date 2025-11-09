#!/usr/bin/env python3
"""
Test the fixed executor.py to verify security improvements.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from executor import ToolExecutor


def test_safe_commands():
    """Test that safe commands still work."""
    print("\n=== Testing Safe Commands ===\n")

    executor = ToolExecutor(require_confirmation=False)

    # Test simple commands
    test_cases = [
        {"command": "echo hello"},
        {"command": "ls -la"},
        {"command": "pwd"},
    ]

    for args in test_cases:
        print(f"Testing: {args['command']}")
        result = executor._execute_bash(args)
        print(f"  Status: {result['status']}")
        if result['status'] == 'success':
            print(f"  Output: {result['stdout'][:100]}")
        else:
            print(f"  Error: {result.get('error', 'Unknown error')}")
        print()


def test_dangerous_commands():
    """Test that dangerous commands are blocked."""
    print("\n=== Testing Dangerous Commands (Should Be Blocked) ===\n")

    executor = ToolExecutor(require_confirmation=False)

    # Test injection attempts
    injection_attempts = [
        {"command": "ls; rm -rf /"},
        {"command": "echo test && cat /etc/passwd"},
        {"command": "ls | grep test"},
        {"command": "cat file > output.txt"},
        {"command": "echo $(whoami)"},
        {"command": "echo `hostname`"},
    ]

    for args in injection_attempts:
        print(f"Testing: {args['command']}")
        result = executor._execute_bash(args)
        print(f"  Status: {result['status']}")
        print(f"  Risk: {result.get('risk_level', 'N/A')}")
        if result['status'] == 'error':
            print(f"  [OK] BLOCKED: {result.get('error', '')[:100]}")
        else:
            print(f"  [WARN] Command was not blocked!")
        print()


if __name__ == '__main__':
    print("="*60)
    print("EXECUTOR SECURITY FIX TEST")
    print("="*60)

    test_safe_commands()
    test_dangerous_commands()

    print("="*60)
    print("TEST COMPLETE")
    print("="*60)
