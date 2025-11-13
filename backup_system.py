#!/usr/bin/env python3
"""
Automated Backup System for Grokputer
Handles scheduled backups, vault sync, and data integrity checks.
"""

import os
import sys
import time
import subprocess
import json
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def run_save_game():
    """Run save_game.py --auto"""
    try:
        result = subprocess.run([
            sys.executable, "save_game.py", "--auto"
        ], capture_output=True, text=True, cwd=Path(__file__).parent, timeout=30)

        if result.returncode == 0:
            print(f"[BACKUP] Game save successful: {result.stdout.strip()}")
            return True
        else:
            print(f"[BACKUP] Game save failed: {result.stderr.strip()}")
            return False
    except Exception as e:
        print(f"[BACKUP] Game save error: {e}")
        return False

def sync_vault():
    """Sync vault with remote (placeholder for actual sync)"""
    try:
        # Placeholder: In real implementation, this would sync with remote vault
        vault_path = Path(__file__).parent / "vault"
        if vault_path.exists():
            print(f"[BACKUP] Vault sync placeholder: {vault_path}")
            return True
        else:
            print("[BACKUP] Vault path not found")
            return False
    except Exception as e:
        print(f"[BACKUP] Vault sync error: {e}")
        return False

def backup_logs():
    """Backup logs directory"""
    try:
        logs_path = Path(__file__).parent / "logs"
        backup_path = Path(__file__).parent / "backups" / f"logs_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        if logs_path.exists():
            # Simple copy (in production, use proper backup tool)
            import shutil
            shutil.copytree(logs_path, backup_path)
            print(f"[BACKUP] Logs backed up to: {backup_path}")
            return True
        else:
            print("[BACKUP] Logs path not found")
            return False
    except Exception as e:
        print(f"[BACKUP] Logs backup error: {e}")
        return False

def validate_backups():
    """Validate that backups are working"""
    saves_path = Path(__file__).parent / "saves"
    if saves_path.exists():
        save_files = list(saves_path.glob("*.json"))
        if save_files:
            print(f"[BACKUP] Found {len(save_files)} save files")
            # Test loading latest
            try:
                with open(save_files[-1], 'r') as f:
                    data = json.load(f)
                print(f"[BACKUP] Latest save valid: {save_files[-1].name}")
                return True
            except Exception as e:
                print(f"[BACKUP] Save validation failed: {e}")
                return False
        else:
            print("[BACKUP] No save files found")
            return False
    else:
        print("[BACKUP] Saves directory not found")
        return False

def run_full_backup():
    """Run complete backup suite"""
    print(f"[BACKUP] Starting full backup at {datetime.now()}")

    results = {
        "game_save": run_save_game(),
        "vault_sync": sync_vault(),
        "logs_backup": backup_logs(),
        "validation": validate_backups()
    }

    success_count = sum(results.values())
    total_count = len(results)

    print(f"[BACKUP] Backup complete: {success_count}/{total_count} successful")

    # Save backup report
    report = {
        "timestamp": datetime.now().isoformat(),
        "results": results,
        "success_rate": success_count / total_count
    }

    report_path = Path(__file__).parent / "backups" / f"backup_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    report_path.parent.mkdir(exist_ok=True)

    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"[BACKUP] Report saved to: {report_path}")

    return success_count == total_count

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Grokputer Automated Backup System")
    parser.add_argument("--full", action="store_true", help="Run full backup suite")
    parser.add_argument("--interval", type=int, help="Run as daemon with interval in minutes")

    args = parser.parse_args()

    if args.interval:
        print(f"[BACKUP] Starting backup daemon with {args.interval}min intervals")
        while True:
            run_full_backup()
            time.sleep(args.interval * 60)
    else:
        # Single run
        success = run_full_backup()
        sys.exit(0 if success else 1)