#!/usr/bin/env python3
"""
Test security hardening for bash command execution.
"""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from src.core.action_executor import ActionExecutor

async def test_security():
    """Test security features of bash execution."""
    print("Testing ActionExecutor bash security...")

    executor = ActionExecutor()

    # Test cases
    test_cases = [
        # Safe commands
        ("echo hello world", "SAFE"),
        ("dir", "SAFE"),
        ("ver", "SAFE"),

        # Dangerous commands (should be blocked)
        ("echo hello && del /Q *", "DANGEROUS"),
        ("dir | find test", "DANGEROUS"),
        ("type C:\\Windows\\System32\\config\\SAM", "DANGEROUS"),
        ("echo %USERPROFILE%", "DANGEROUS"),
        ("for /F %i in ('whoami') do echo %i", "DANGEROUS"),
    ]

    for command, expected in test_cases:
        print(f"\nTesting: {command}")
        try:
            result = await executor.execute_bash(command)
            status = result.get("status")
            error = result.get("error", "")

            if expected == "SAFE":
                if status == "success":
                    print(f"  [PASS] SAFE command executed successfully")
                else:
                    print(f"  [FAIL] SAFE command failed: {error}")
            else:  # DANGEROUS
                if "dangerous" in error.lower() or status == "error":
                    print(f"  [PASS] DANGEROUS command blocked: {error[:50]}...")
                else:
                    print(f"  [FAIL] DANGEROUS command executed! SECURITY ISSUE")

        except Exception as e:
            print(f"  [WARN] Exception: {e}")

    print("\nSecurity test complete!")

if __name__ == "__main__":
    asyncio.run(test_security())