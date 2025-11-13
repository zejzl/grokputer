#!/usr/bin/env python3
"""
Test script for the notification system.
Run this to verify email/Slack alerts are working correctly.

Usage:
    # Test with console output only (no credentials needed)
    python test_alerts.py

    # Test with real email/Slack (requires .env configuration)
    python test_alerts.py --send
"""

import asyncio
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from alerts import Notifier, AlertLevel, Alert
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


async def test_notifications(send_real: bool = False):
    """Test notification system with various alert types."""

    print("=" * 70)
    print("GROKPUTER ALERT NOTIFICATION SYSTEM TEST")
    print("=" * 70)

    # Initialize notifier
    if send_real:
        print("\n[*] Testing with REAL notifications (Email + Slack)")
        notifier = Notifier(min_level=AlertLevel.INFO)
    else:
        print("\n[*] Testing with CONSOLE-ONLY mode (no sends)")
        print("   To test real sends: python test_alerts.py --send\n")
        # Force disable to test logic without sending
        notifier = Notifier(enable_email=False, enable_slack=False, min_level=AlertLevel.INFO)

    print(f"   Email alerts: {notifier.enable_email}")
    print(f"   Slack alerts: {notifier.enable_slack}")
    print(f"   Min level: {notifier.min_level.value}")
    print()

    # Test 1: INFO alert (low priority)
    print("[INFO] Test 1: INFO Alert - Daemon Started")
    info_alert = Alert(
        title="Grokputer Daemon Started",
        message="Autonomous monitoring daemon initialized.\n\nTarget: src/\nInterval: 60s\nEvolution chance: 30%",
        level=AlertLevel.INFO,
        metadata={"target": "src/", "interval": "60s", "agents": "scanner, proposer"},
    )
    result = await notifier.send(info_alert)
    print(f"   Result: {result}\n")

    # Test 2: WARNING alert (evolution detected)
    print("[WARNING] Test 2: WARNING Alert - High-Impact Evolution")
    await notifier.send_evolution_alert(
        {
            "agent": "scanner",
            "metric": "detection_threshold",
            "old_value": "0.75",
            "new_value": "0.60",
            "improvement_percent": 160,
        }
    )
    print()

    # Test 3: CRITICAL alert (security vulnerability)
    print("[CRITICAL] Test 3: CRITICAL Alert - Security Vulnerability")
    await notifier.send_critical_proposal_alert(
        {
            "finding_id": "SEC-001",
            "severity": "critical",
            "description": "Shell injection vulnerability detected in executor.py:141",
            "risk_level": "high",
            "file_path": "src/executor.py",
            "auto_applied": False,
        }
    )
    print()

    # Test 4: CRITICAL alert (multiple security issues)
    print("[CRITICAL] Test 4: CRITICAL Alert - Multiple Security Issues")
    critical_alert = Alert(
        title="5 Critical Security Issues Detected",
        message="Security scan found 5 critical and 3 high severity issues in src/.\n\nTop issues:\n* Shell injection in executor.py\n* SQL injection in database.py\n* XSS vulnerability in web_ui.py",
        level=AlertLevel.CRITICAL,
        metadata={"critical_count": 5, "high_count": 3, "total_findings": 8, "scan_target": "src/"},
    )
    result = await notifier.send(critical_alert)
    print(f"   Result: {result}\n")

    # Test 5: WARNING alert (auto-apply yolo mode)
    print("[WARNING] Test 5: WARNING Alert - Auto-Apply (YOLO Mode)")
    await notifier.send_yolo_apply_alert(
        {
            "proposal_id": "PROP-123",
            "file_path": "src/grok_client.py",
            "changes_made": "Fixed async timeout handling",
            "risk_level": "low",
        }
    )
    print()

    print("=" * 70)
    print("[SUCCESS] All tests completed!")
    print("=" * 70)

    if not send_real:
        print("\n[INFO] No actual emails or Slack messages were sent (console-only mode).")
        print("   To test with real notifications:")
        print("   1. Configure SMTP and/or Slack in .env file")
        print("   2. Run: python test_alerts.py --send")
    else:
        print("\n[SUCCESS] Real notifications were sent!")
        print("   Check your email and Slack for test alerts.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test Grokputer notification system")
    parser.add_argument("--send", action="store_true", help="Send real email/Slack alerts (requires .env config)")
    args = parser.parse_args()

    asyncio.run(test_notifications(send_real=args.send))
