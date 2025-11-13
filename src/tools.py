#!/usr/bin/env python3
"""
Tools for Grokputer - Including dynamic code generation and execution.
"""

import ast
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, List


def invoke_prayer() -> Dict[str, Any]:
    """
    Invoke the server prayer.
    """
    return {"status": "success", "message": "ETERNAL | INFINITE"}


def generate_code(filename: str, code_content: str, sandbox_dir: str = "outputs") -> Dict[str, Any]:
    """
    Generate a Python script file with the provided code content.

    Args:
        filename: Name of the file to create (e.g., 'season_haiku.py').
        code_content: The full Python code as string.
        sandbox_dir: Directory to write the file (default 'outputs').

    Returns:
        Dict with status, path, and any errors.
    """
    try:
        # Validate syntax before writing
        ast.parse(code_content)

        # Create sandbox dir if needed
        sandbox_path = Path(sandbox_dir)
        sandbox_path.mkdir(exist_ok=True)

        # Full path
        file_path = sandbox_path / filename

        # Write file
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(code_content)

        return {"status": "success", "path": str(file_path), "message": f"Generated script at {file_path}"}
    except SyntaxError as e:
        return {"status": "error", "message": f"Syntax error in generated code: {e}"}
    except Exception as e:
        return {"status": "error", "message": f"Failed to generate script: {e}"}


def execute_generated_code(filename: str, sandbox_dir: str = "outputs") -> Dict[str, Any]:
    """
    Execute the generated Python script and capture output.

    Args:
        filename: Name of the script to run (e.g., 'season_haiku.py').
        sandbox_dir: Directory where the script is located.

    Returns:
        Dict with status, output, and any errors.
    """
    try:
        file_path = Path(sandbox_dir) / filename

        if not file_path.exists():
            return {"status": "error", "message": f"Script {file_path} not found"}

        # Run the script, capture stdout/stderr
        result = subprocess.run(
            [sys.executable, str(file_path)], capture_output=True, text=True, timeout=30  # 30s timeout for safety
        )

        output = result.stdout if result.stdout else "No output."
        error = result.stderr if result.stderr else None

        if result.returncode == 0:
            return {"status": "success", "output": output, "message": f"Executed {filename} successfully"}
        else:
            return {
                "status": "error",
                "output": output,
                "error": error,
                "message": f"Script failed with code {result.returncode}",
            }
    except subprocess.TimeoutExpired:
        return {"status": "error", "message": "Script execution timed out (30s limit)"}
    except Exception as e:
        return {"status": "error", "message": f"Failed to execute script: {e}"}


def bash(command: str) -> Dict[str, Any]:
    """
    Execute a bash/shell command.

    Args:
        command: The command to execute.

    Returns:
        Dict with status, output, and any errors.
    """
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=30  # 30s timeout for safety
        )

        output = result.stdout if result.stdout else "No output."
        error = result.stderr if result.stderr else None

        if result.returncode == 0:
            return {"status": "success", "output": output, "message": f"Command executed successfully"}
        else:
            return {
                "status": "error",
                "output": output,
                "error": error,
                "message": f"Command failed with code {result.returncode}",
            }
    except subprocess.TimeoutExpired:
        return {"status": "error", "message": "Command execution timed out (30s limit)"}
    except Exception as e:
        return {"status": "error", "message": f"Failed to execute command: {e}"}


def search(query: str, path: str = ".") -> Dict[str, Any]:
    """
    Search for text in files.

    Args:
        query: Text to search for.
        path: Directory to search in.

    Returns:
        Dict with status and search results.
    """
    try:
        import os

        results = []
        for root, dirs, files in os.walk(path):
            for file in files:
                if file.endswith((".py", ".md", ".txt", ".json")):
                    try:
                        with open(os.path.join(root, file), "r", encoding="utf-8") as f:
                            content = f.read()
                            if query in content:
                                results.append(f"{os.path.join(root, file)}: {content.count(query)} matches")
                    except:
                        pass  # Skip files that can't be read

        return {"status": "success", "results": results, "message": f"Found {len(results)} files containing '{query}'"}
    except Exception as e:
        return {"status": "error", "message": f"Search failed: {e}"}
