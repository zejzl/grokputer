#!/usr/bin/env python3
"""
Test script for safety scoring system.
Demonstrates risk levels for various bash commands.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.config import get_command_safety_score, requires_confirmation, REQUIRE_CONFIRMATION

# Test commands with varying risk levels
test_commands = [
    # Low risk (0-30)
    "ls -la",
    "pwd",
    "echo 'Hello World'",
    "cat README.md",
    "grep 'pattern' file.txt",

    # Medium risk (31-70)
    "mkdir test_directory",
    "touch new_file.txt",
    "cp file.txt backup.txt",
    "git status",
    "python script.py",

    # High risk (71-100)
    "rm important_file.txt",
    "mv /etc/config /tmp/",
    "chmod 777 file.txt",
    "sudo apt-get install package",
    "rm -rf /tmp/test",
    "rm -rf /",  # Maximum risk
]

def display_risk_bar(score: int) -> str:
    """Create a visual risk bar."""
    filled = int(score / 5)
    empty = 20 - filled

    if score <= 30:
        color = "GREEN"
        symbol = "="
    elif score <= 70:
        color = "YELLOW"
        symbol = "~"
    else:
        color = "RED"
        symbol = "#"

    bar = symbol * filled + "-" * empty
    return f"[{bar}] {color}"

def main():
    print("=" * 80)
    print("GROKPUTER SAFETY SCORING SYSTEM TEST")
    print("=" * 80)
    print(f"\nREQUIRE_CONFIRMATION environment: {REQUIRE_CONFIRMATION}")
    print("\nRisk Levels:")
    print("  0-30:  LOW    (auto-approve, read-only operations)")
    print("  31-70: MEDIUM (warn but proceed, non-destructive)")
    print("  71-100: HIGH  (require confirmation, destructive)")
    print("\n" + "=" * 80)

    for command in test_commands:
        score = get_command_safety_score(command)
        needs_confirm = requires_confirmation(command)
        risk_level = "LOW" if score <= 30 else "MEDIUM" if score <= 70 else "HIGH"
        risk_bar = display_risk_bar(score)
        confirm_status = "CONFIRM REQUIRED" if needs_confirm else "AUTO-APPROVE"

        print(f"\nCommand: {command}")
        print(f"  Score: {score:3d}/100  Risk: {risk_level:6s}  {confirm_status}")
        print(f"  {risk_bar}")

    print("\n" + "=" * 80)
    print("Test complete! Safety scoring system is operational.")
    print("\nTo test with Grok:")
    print("  1. Set REQUIRE_CONFIRMATION=false in .env to enable smart scoring")
    print("  2. Run: python main.py --task 'list files in current directory'")
    print("  3. Watch logs for safety scores on bash commands")
    print("=" * 80)

if __name__ == "__main__":
    main()
