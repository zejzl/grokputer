"""
Grok4Git tool for Grokputer agents.
Provides natural language GitHub management via grok4git CLI.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Optional


def run_grok4git_command(command: str, cwd: Optional[str] = None) -> str:
    """
    Run a grok4git command and return the output.

    Args:
        command: The natural language command for grok4git
        cwd: Working directory (defaults to current)

    Returns:
        Output from grok4git
    """
    try:
        # Path to grok4git main
        grok4git_path = Path(__file__).parent.parent.parent / "vault" / "git_resources" / "grok4git" / "grok4git" / "main.py"

        if not grok4git_path.exists():
            return "Error: grok4git not found. Run git clone first."

        # Run grok4git with the command
        cmd = [sys.executable, str(grok4git_path)]
        if command:
            cmd.append(command)

        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=30  # 30 second timeout
        )

        if result.returncode == 0:
            return result.stdout
        else:
            return f"Error: {result.stderr}"

    except subprocess.TimeoutExpired:
        return "Error: grok4git command timed out"
    except Exception as e:
        return f"Error running grok4git: {e}"


def list_repositories() -> str:
    """List all user repositories."""
    return run_grok4git_command("list all my repositories")


def get_repository_info(repo: str) -> str:
    """Get information about a specific repository."""
    return run_grok4git_command(f"show information about {repo}")


def create_issue(repo: str, title: str, body: str = "") -> str:
    """Create a new issue in a repository."""
    command = f"create issue in {repo} titled '{title}'"
    if body:
        command += f" with description '{body}'"
    return run_grok4git_command(command)


def search_code(query: str, repo: Optional[str] = None) -> str:
    """Search for code patterns."""
    command = f"search for '{query}'"
    if repo:
        command += f" in {repo}"
    return run_grok4git_command(command)


if __name__ == "__main__":
    # Test the tool
    print("Testing grok4git tool...")
    result = run_grok4git_command("help")
    print(result)