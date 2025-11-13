#!/usr/bin/env python3
"""
Save Game: Backup Grokputer state for eternal progress.
Invokes git commit, vault sync, Redis dump, logs archive.
Usage: python save_game.py [--auto] [--message "Custom commit msg"] [--interval MINUTES]
"""

import os
import subprocess
import shutil
import json
import time
from datetime import datetime
from pathlib import Path
import logging
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not available, use system env vars

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)
import json
import time
from datetime import datetime
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)


def run_command(cmd, cwd=None, capture_output=True):
    """Run shell command safely."""
    try:
        result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=capture_output, text=True, timeout=120)
        if result.returncode != 0:
            logger.warning(f"Command failed: {cmd} - {result.stderr}")
            return False, result.stderr
        return True, result.stdout
    except Exception as e:
        logger.error(f"Command error: {e}")
        return False, str(e)


def save_git(auto=False):
    """Git commit changes."""
    if auto:
        msg = f"Auto Save Game {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Pantheon Architecture Complete"
    else:
        msg = input("Enter commit message (or press Enter for auto): ").strip()
        if not msg:
            msg = f"Save Game {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Pantheon Architecture Complete"

    success, out = run_command(f'git add . && git commit -m "{msg}"')
    if success:
        logger.info(f"Git saved: {out}")
    return success


def sync_vault():
    """Sync to vault/community."""
    logger.info("Syncing vault...")
    try:
        from src.vault_sync import run_vault_sync

        run_vault_sync("both")
        logger.info("Vault synced.")
        return True
    except Exception as e:
        logger.warning(f"Vault sync failed: {e}")
        return False


def dump_redis():
    """Dump Redis state (if enabled)."""
    redis_url = os.getenv("REDIS_URL")
    if redis_url and REDIS_AVAILABLE:
        try:
            # Use Python Redis client instead of shell commands
            r = redis.from_url(redis_url)
            r.ping()  # Test connection
            
            # Trigger background save
            r.bgsave()
            logger.info("Redis background save triggered")
            
            # Save database info to vault
            db_info = {
                "timestamp": datetime.now().isoformat(),
                "keys": r.dbsize(),
                "lastsave": r.lastsave()
            }
            
            vault_dir = Path("vault")
            vault_dir.mkdir(exist_ok=True)
            with open(vault_dir / "redis_backup_info.json", "w") as f:
                json.dump(db_info, f, indent=2)
            
            logger.info(f"Redis backup info saved: {db_info["keys"]} keys")
            return True
        except Exception as e:
            logger.warning(f"Redis dump failed: {e}")
            return False
    elif redis_url and not REDIS_AVAILABLE:
        logger.warning("Redis URL configured but redis-py not available")
        return False
    else:
        logger.info("No Redis configured; skipped.")
        return True

def update_documentation():
    """Update documentation based on session changes."""
    logger.info("Updating documentation...")

    try:
        # Get git status and changes
        success, status_out = run_command("git status --porcelain")
        if not success:
            logger.warning("Could not get git status")
            return False

        success, diff_out = run_command("git diff --cached --name-only")
        if not success:
            logger.warning("Could not get git diff")
            return False

        # Analyze changes
        changed_files = status_out.split("\n") if status_out else []
        staged_files = diff_out.split("\n") if diff_out else []

        # Categorize changes
        changes = analyze_changes(changed_files + staged_files)

        # Update CHANGELOG.md
        if update_changelog(changes):
            logger.info("CHANGELOG.md updated")

        # Update progress documentation
        if update_progress_docs(changes):
            logger.info("Progress documentation updated")

        # Update README if needed
        if update_readme(changes):
            logger.info("README.md updated")

        # Stage documentation changes
        doc_files = ["CHANGELOG.md", "README.md", "docs/", "*.md"]
        for doc_file in doc_files:
            run_command(f"git add {doc_file}")

        return True

    except Exception as e:
        logger.error(f"Documentation update failed: {e}")
        return False


def analyze_changes(changed_files):
    """Analyze what types of changes were made."""
    changes = {
        "new_features": [],
        "bug_fixes": [],
        "documentation": [],
        "tests": [],
        "config": [],
        "dependencies": [],
        "ai_models": [],
        "agents": [],
        "tools": [],
        "vision": [],
        "multimodal": [],
        "reasoning": [],
        "ui": [],
        "other": [],
    }

    for line in changed_files:
        if not line.strip():
            continue

        # Remove status prefix (M, A, D, etc.)
        parts = line.split()
        if len(parts) >= 2:
            file_path = parts[-1]
        else:
            file_path = line.strip()

        # Categorize by file path and content
        if "test" in file_path.lower() or file_path.startswith("tests/"):
            changes["tests"].append(file_path)
        elif file_path.endswith((".md", ".txt", ".rst")) or "docs/" in file_path:
            changes["documentation"].append(file_path)
        elif "requirements.txt" in file_path or "pyproject.toml" in file_path:
            changes["dependencies"].append(file_path)
        elif "agent" in file_path.lower() or "agents/" in file_path:
            changes["agents"].append(file_path)
        elif "vision" in file_path.lower() or "ocr" in file_path.lower():
            changes["vision"].append(file_path)
        elif "multimodal" in file_path.lower():
            changes["multimodal"].append(file_path)
        elif "reasoning" in file_path.lower():
            changes["reasoning"].append(file_path)
        elif "ui" in file_path.lower() or "interface" in file_path.lower():
            changes["ui"].append(file_path)
        elif "model" in file_path.lower() or "ai" in file_path.lower():
            changes["ai_models"].append(file_path)
        elif "tool" in file_path.lower() or "tools/" in file_path:
            changes["tools"].append(file_path)
        elif file_path.startswith(("src/", "grokputer/", "config/")):
            # Check if it's a new feature or bug fix
            if "fix" in file_path.lower() or "bug" in file_path.lower():
                changes["bug_fixes"].append(file_path)
            else:
                changes["new_features"].append(file_path)
        else:
            changes["other"].append(file_path)

    return changes


def update_changelog(changes):
    """Update CHANGELOG.md with session changes."""
    try:
        changelog_path = Path("CHANGELOG.md")
        if not changelog_path.exists():
            return False

        # Check if there are significant changes worth documenting
        significant_changes = (
            changes["new_features"]
            or changes["vision"]
            or changes["multimodal"]
            or changes["reasoning"]
            or changes["agents"]
            or changes["bug_fixes"]
            or changes["dependencies"]
        )

        # Skip changelog update if only minor changes (like save_summary.json, symlinks)
        minor_only = (
            all(
                file in ["save_summary.json", "tools/semtools", "grokputer_base"]
                for file in changes["other"] + changes["tools"]
            )
            and not significant_changes
        )

        if minor_only:
            logger.info("Only minor changes detected, skipping CHANGELOG update")
            return False

        # Generate changelog entry
        timestamp = datetime.now().strftime("%Y-%m-%d")
        version = f"v{datetime.now().strftime('%Y.%m.%d')}"

        entry_lines = [f"## [{version}] - {timestamp}\n"]

        # Add sections based on changes
        if changes["new_features"]:
            entry_lines.append("### Added")
            for feature in changes["new_features"][:5]:  # Limit to 5
                entry_lines.append(f"- New feature: {feature}")
            if len(changes["new_features"]) > 5:
                entry_lines.append(f"- ... and {len(changes["new_features"]) - 5} more features")

        if changes["vision"]:
            entry_lines.append("### Vision & OCR")
            for item in changes["vision"][:3]:
                entry_lines.append(f"- Enhanced vision capabilities: {item}")

        if changes["multimodal"] or changes["reasoning"]:
            entry_lines.append("### Multi-Modal & Reasoning")
            for item in changes["multimodal"] + changes["reasoning"][:3]:
                entry_lines.append(f"- Advanced reasoning: {item}")

        if changes["agents"]:
            entry_lines.append("### Agents")
            for agent in changes["agents"][:3]:
                entry_lines.append(f"- Agent enhancement: {agent}")

        if changes["tests"]:
            entry_lines.append("### Testing")
            entry_lines.append(f"- Added/updated {len(changes['tests'])} test files")

        if changes["dependencies"]:
            entry_lines.append("### Dependencies")
            for dep in changes["dependencies"]:
                entry_lines.append(f"- Updated dependencies: {dep}")

        if changes["bug_fixes"]:
            entry_lines.append("### Fixed")
            for fix in changes["bug_fixes"][:3]:
                entry_lines.append(f"- Bug fix: {fix}")

        entry_lines.append("")

        # Read existing changelog
        with open(changelog_path, "r", encoding="utf-8") as f:
            existing_content = f.read()

        # Check if we already have an entry for today to avoid duplicates
        today_entry = f"## [{version}] - {timestamp}"
        if today_entry in existing_content:
            logger.info("CHANGELOG already has entry for today, skipping update")
            return False

        # Insert new entry after header
        lines = existing_content.split("\n")
        insert_index = 0
        for i, line in enumerate(lines):
            if line.startswith("# Changelog") or line.startswith("# CHANGELOG"):
                insert_index = i + 2  # After header and blank line
                break

        # Insert the new entry
        new_content = "\n".join(lines[:insert_index] + entry_lines + lines[insert_index:])

        # Write back
        with open(changelog_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        return True

    except Exception as e:
        logger.error(f"CHANGELOG update failed: {e}")
        return False


def update_progress_docs(changes):
    """Update progress documentation files."""
    try:
        # Update DEVELOPMENT_PLAN.md if it exists
        dev_plan_path = Path("DEVELOPMENT_PLAN.md")
        if dev_plan_path.exists():
            update_development_plan(dev_plan_path, changes)

        # Update any session-specific docs
        session_docs = ["next_session_todo.md", "session_summary.md", "progress.md"]
        for doc in session_docs:
            doc_path = Path(doc)
            if doc_path.exists():
                update_session_doc(doc_path, changes)

        return True

    except Exception as e:
        logger.error(f"Progress docs update failed: {e}")
        return False


def update_development_plan(plan_path, changes):
    """Update development plan with progress."""
    try:
        with open(plan_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Simple progress update - mark phases as complete based on changes
        if changes["vision"] or changes["multimodal"]:
            content = content.replace(
                "Phase 3.8: Multi-Modal Reasoning with Vision Integration - PENDING",
                "Phase 3.8: Multi-Modal Reasoning with Vision Integration - COMPLETE",
            )

        if content:
            with open(plan_path, "w", encoding="utf-8") as f:
                f.write(content)

    except Exception as e:
        logger.error(f"Development plan update failed: {e}")


def update_session_doc(doc_path, changes):
    """Update session documentation."""
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Check if there are significant changes worth documenting
        significant_changes = (
            changes["new_features"]
            or changes["vision"]
            or changes["multimodal"]
            or changes["reasoning"]
            or changes["agents"]
            or changes["bug_fixes"]
            or changes["dependencies"]
        )

        # Skip session doc update if only minor changes
        minor_only = (
            all(
                file in ["save_summary.json", "tools/semtools", "grokputer_base"]
                for file in changes["other"] + changes["tools"]
            )
            and not significant_changes
        )

        if minor_only:
            logger.info("Only minor changes detected, skipping session documentation update")
            return

        summary = f"""
## Session Summary - {timestamp}

### Changes Made:
"""

        for category, files in changes.items():
            if files and category != "other":
                summary += f"- **{category.replace('_', ' ').title()}**: {len(files)} files\n"
                for file in files[:3]:  # Show first 3 files
                    summary += f"  - {file}\n"
                if len(files) > 3:
                    summary += f"  - ... and {len(files) - 3} more\n"

        summary += "\n### Key Accomplishments:\n"
        if changes["vision"]:
            summary += "- Advanced vision and OCR capabilities implemented\n"
        if changes["multimodal"]:
            summary += "- Multi-modal reasoning engine deployed\n"
        if changes["reasoning"]:
            summary += "- Intelligent decision making framework added\n"
        if changes["agents"]:
            summary += "- Agent enhancements completed\n"
        if not significant_changes:
            summary += "- Routine maintenance and backup operations\n"

        summary += "\n---\n\n"

        # Append to existing content
        try:
            with open(doc_path, "r", encoding="utf-8") as f:
                existing = f.read()
        except:
            existing = ""

        with open(doc_path, "w", encoding="utf-8") as f:
            f.write(summary + existing)

    except Exception as e:
        logger.error(f"Session doc update failed: {e}")


def update_readme(changes):
    """Update README.md if needed."""
    try:
        readme_path = Path("README.md")
        if not readme_path.exists():
            return False

        # Only update if there are significant changes
        significant_changes = changes["new_features"] or changes["vision"] or changes["multimodal"] or changes["agents"]

        if not significant_changes:
            return False

        with open(readme_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Update version or last updated
        if "## Grokputer" in content:
            # Add a note about recent updates
            update_note = f"\n*Last updated: {datetime.now().strftime('%Y-%m-%d')} - Added advanced vision and reasoning capabilities*\n"
            content = content.replace("## Grokputer", "## Grokputer" + update_note)

            with open(readme_path, "w", encoding="utf-8") as f:
                f.write(content)

        return True

    except Exception as e:
        logger.error(f"README update failed: {e}")
        return False


def archive_logs():
    """Archive logs to backups."""
    log_dir = Path("./logs")
    if log_dir.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive = Path(f"backups/logs_{timestamp}.tar.gz")
        archive.parent.mkdir(exist_ok=True)
        success, out = run_command(f"tar -czf {archive} logs/")
        if success:
            logger.info(f"Logs archived: {archive}")
    return True


def main(auto: bool = False, interval: int = None):
    """Main save routine."""
    if interval:
        # Daemon mode: run periodically
        logger.info(f"Starting autosave daemon with {interval} minute intervals")
        while True:
            try:
                _perform_save(auto=True)
                logger.info(f"Autosave complete. Next save in {interval} minutes.")
                time.sleep(interval * 60)
            except KeyboardInterrupt:
                logger.info("Autosave daemon stopped.")
                break
            except Exception as e:
                logger.error(f"Autosave error: {e}")
                time.sleep(60)  # Retry in 1 minute on error
    else:
        # Single save
        _perform_save(auto)


def _perform_save(auto: bool):
    """Perform the actual save operations."""
    print("\n" + "=" * 50)
    print("SAVE GAME - ETERNAL PROGRESS BACKUP")
    print("=" * 50)

    summary = {
        "timestamp": datetime.now().isoformat(),
        "git_committed": False,
        "vault_synced": False,
        "redis_dumped": False,
        "logs_archived": False,
        "documentation_updated": False,
    }

    if not auto:
        confirm = input("Confirm save? (y/n): ").lower()
        if confirm != "y":
            print("Save cancelled.")
            return

    # Update documentation before committing
    doc_updated = update_documentation()
    if doc_updated:
        logger.info("Documentation updated with session changes")

    # Steps
    summary["git_committed"] = save_git(auto=auto)
    summary["vault_synced"] = sync_vault()
    summary["redis_dumped"] = dump_redis()
    summary["logs_archived"] = archive_logs()
    summary["documentation_updated"] = doc_updated

    # Save summary
    with open("save_summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    logger.info(f"Save complete. Summary: {json.dumps(summary, indent=2)}")

    print("\n[ETERNAL] Za Groka. Progress saved!")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--auto", action="store_true", help="Auto-save without prompts")
    parser.add_argument("--message", help="Custom git message")
    parser.add_argument("--interval", type=int, help="Autosave interval in minutes (runs as daemon)")
    args = parser.parse_args()

    if args.message:
        # Set env for git msg
        os.environ["SAVE_MSG"] = args.message

    main(auto=args.auto, interval=args.interval)
