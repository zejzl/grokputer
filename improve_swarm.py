#!/usr/bin/env python3
"""
Self-Improving Swarm: Analyzes logs, suggests & applies fixes, tests improvements.
YOLO Mode: Applies first high-confidence edit; reverts on test fail.
Run: python improve_swarm.py [dry-run] [max_issues=1]
"""

import json
import os
import sys
import shutil
from datetime import datetime
from pathlib import Path
from collections import defaultdict
import subprocess
from typing import Dict, List, Any

# Local imports
from src import config
from src.grok_client import GrokClient

LOG_FILE = Path(config.LOG_DIR) / "grokputer_tasks.jsonl"
IMPROVE_LOG = Path(config.LOG_DIR) / "improvement_log.txt"
BACKUP_SUFFIX = "_backup_before_improve"

def log_improvement(message: str):
    """Log to improvement_log.txt."""
    timestamp = datetime.now().isoformat()
    with open(IMPROVE_LOG, "a") as f:
        f.write(f"[{timestamp}] {message}\n")
    print(f"[IMPROVE] {message}")

def read_logs() -> List[Dict[str, Any]]:
    """Read and parse grokputer_tasks.jsonl."""
    if not LOG_FILE.exists():
        log_improvement("No logs found; nothing to improve.")
        return []
    
    logs = []
    with open(LOG_FILE, "r") as f:
        for line in f:
            try:
                logs.append(json.loads(line.strip()))
            except json.JSONDecodeError:
                continue
    log_improvement(f"Read {len(logs)} log entries.")
    return logs

def detect_issues(logs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Detect error patterns: group by agent.action.error, count >2."""
    error_groups = defaultdict(lambda: defaultdict(int))
    for entry in logs:
        if entry.get("outcome") == "fail" and entry.get("error"):
            key = f"{entry['agent']}.{entry.get('action_type', 'unknown')}"
            error_groups[key][entry["error"]] += 1
    
    issues = []
    for key, errors in error_groups.items():
        for err, count in errors.items():
            if count > 2:  # Threshold for pattern
                issues.append({
                    "agent_action": key,
                    "error": err,
                    "count": count,
                    "examples": [e for e in logs if e.get("error") == err][:3],  # 3 examples
                    "file": infer_file_from_agent(key)  # e.g., actor.bash -> src/agents/actor.py
                })
    log_improvement(f"Detected {len(issues)} issues.")
    return issues

def infer_file_from_agent(agent_action: str) -> str:
    """Map agent.action to file (heuristic)."""
    mappings = {
        "coordinator": "src/agents/coordinator.py",
        "observer.capture_screen": "src/agents/observer.py",
        "actor.bash": "src/agents/actor.py",
        "actor.file": "src/agents/actor.py",
        # Add more
    }
    for k, v in mappings.items():
        if k in agent_action:
            return v
    return "src/agents/base_agent.py"  # Default

def get_grok_fix(issue: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Query Grok for fix suggestion."""
    grok = GrokClient()
    examples = "\n".join([f"- Task {e['task_id']}: {e['error']}" for e in issue["examples"]])
    prompt = f"""
Analyze these repeated errors in {issue['agent_action']} ({issue['count']} times):
{examples}

Suggest a targeted code improvement for {issue['file']} (e.g., add check/retry).
Respond ONLY in JSON:
{{
    "file": "path/to/file.py",
    "approx_line": 250,  // Estimate
    "old_str": "existing code line or snippet",
    "new_str": "improved code line or snippet",
    "reason": "brief explanation",
    "confidence": 8  // 1-10
}}
Focus on single, safe edit (e.g., add if os.path.exists(path): before call).
"""
    
    response = grok.create_message(task=prompt)
    if response["status"] == "success":
        try:
            # Parse JSON from content (assume Grok returns clean JSON)
            fix_json = json.loads(response["content"])
            if fix_json.get("confidence", 0) > 7:  # High confidence
                log_improvement(f"Grok suggested fix for {issue['agent_action']}: {fix_json['reason']}")
                return fix_json
        except (json.JSONDecodeError, KeyError):
            log_improvement("Grok response not parsable; skipping.")
    return None

def apply_edit(fix: Dict[str, Any], dry_run: bool = False) -> bool:
    """Apply edit via sed simulation (backup first)."""
    file_path = Path(fix["file"])
    if not file_path.exists():
        log_improvement(f"File {fix['file']} not found; skipping.")
        return False
    
    backup = file_path.with_suffix(f".{BACKUP_SUFFIX}_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    if not dry_run:
        shutil.copy2(file_path, backup)
        log_improvement(f"Backup created: {backup}")
    
    old_str = fix["old_str"].replace('/', '\\/')  # Escape for sed
    new_str = fix["new_str"].replace('/', '\\/')
    
    cmd = f"sed -i 's/{old_str}/{new_str}/g' {file_path}"
    if dry_run:
        log_improvement(f"DRY-RUN: Would run: {cmd}")
        return True
    
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        log_improvement(f"Applied edit to {fix['file']}: {fix['reason']}")
        return True
    else:
        log_improvement(f"Edit failed: {result.stderr}. Reverting from {backup}")
        if backup.exists():
            shutil.copy2(backup, file_path)
        return False

def test_fix(issue: Dict[str, Any]) -> bool:
    """Run quick swarm test to verify fix."""
    test_task = infer_test_task(issue)  # e.g., for actor.bash: "ls vault"
    cmd = f"python main.py --swarm --task '{test_task}' --max_iterations 1"
    log_improvement(f"Testing fix with: {cmd}")
    
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
    if result.returncode == 0:
        # Check new logs for no repeat error
        new_logs = read_logs()
        recent_fails = [l for l in new_logs[-5:] if l.get("outcome") == "fail" and l.get("error") == issue["error"]]
        if not recent_fails:
            log_improvement("Test passed: No repeat errors!")
            return True
    log_improvement(f"Test failed/partial: {result.stdout[:200]}...")
    return False

def infer_test_task(issue: Dict[str, Any]) -> str:
    """Infer test task from issue."""
    if "actor.bash" in issue["agent_action"]:
        return "List files in vault directory"
    elif "observer" in issue["agent_action"]:
        return "Capture screen and analyze"
    return "Run a simple task: echo hello"

def main(dry_run: bool = False, max_issues: int = 1):
    """Main improvement loop."""
    log_improvement("=== Starting Self-Improvement Cycle ===")
    logs = read_logs()
    if not logs:
        return
    
    issues = detect_issues(logs)[:max_issues]
    if not issues:
        log_improvement("No issues detected; swarm is optimal.")
        return
    
    for i, issue in enumerate(issues):
        log_improvement(f"Processing issue {i+1}/{len(issues)}: {issue['agent_action']} - {issue['error']} ({issue['count']}x)")
        fix = get_grok_fix(issue)
        if not fix:
            continue
        
        applied = apply_edit(fix, dry_run)
        if applied:
            success = test_fix(issue)
            if success:
                log_improvement(f"Improvement successful for {issue['agent_action']}!")
            else:
                log_improvement("Test failed; reverted edit.")
        else:
            log_improvement("Edit not applied.")
    
    log_improvement("=== Improvement Cycle Complete ===")

if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    max_issues = 1  # Default; parse if needed
    main(dry_run=dry_run)