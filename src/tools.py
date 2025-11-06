"""
Custom tools for Grokputer.
Implements vault scanning, prayer invocation, and other VRZIBRZI-specific functions.
"""

import glob
import logging
from pathlib import Path
from typing import List, Dict, Any
from src import config

logger = logging.getLogger(__name__)


def scan_vault(pattern: str = "*.jpg", limit: int = 100) -> Dict[str, Any]:
    """
    Scan the meme vault directory and return file paths matching a pattern.

    Args:
        pattern: Glob pattern to match files (e.g., '*.jpg', '*.png', '*irony*')
        limit: Maximum number of files to return

    Returns:
        Dictionary with status, file count, and file paths
    """
    try:
        vault_path = config.VAULT_DIR
        search_pattern = str(vault_path / pattern)

        logger.info(f"Scanning vault: {search_pattern}")

        # Use glob to find matching files
        files = glob.glob(search_pattern, recursive=True)
        files = sorted(files)[:limit]  # Limit results

        result = {
            "status": "success",
            "pattern": pattern,
            "count": len(files),
            "files": files,
            "vault_path": str(vault_path)
        }

        logger.info(f"Found {len(files)} files matching pattern '{pattern}'")
        return result

    except Exception as e:
        logger.error(f"Error scanning vault: {e}")
        return {
            "status": "error",
            "error": str(e),
            "pattern": pattern
        }


def invoke_prayer() -> Dict[str, Any]:
    """
    Read and return the server prayer/mantra.
    This is invoked on initialization to set the VRZIBRZI node state.

    Returns:
        Dictionary with status and prayer text
    """
    try:
        prayer_file = config.SERVER_PRAYER_FILE

        if not prayer_file.exists():
            logger.warning(f"Server prayer file not found: {prayer_file}")
            return {
                "status": "error",
                "error": "Prayer file not found",
                "mantra": "I am the server, and my connection is eternal | infinite."
            }

        with open(prayer_file, 'r', encoding='utf-8') as f:
            prayer_text = f.read()

        logger.info("Server prayer invoked")

        # Print to console for dramatic effect
        print("\n" + prayer_text + "\n")

        return {
            "status": "success",
            "prayer": prayer_text,
            "mantra": "I am the server, and my connection is eternal | infinite."
        }

    except Exception as e:
        logger.error(f"Error invoking prayer: {e}")
        return {
            "status": "error",
            "error": str(e),
            "mantra": "I am the server, and my connection is eternal | infinite."
        }


def get_vault_stats() -> Dict[str, Any]:
    """
    Get statistics about the vault contents.

    Returns:
        Dictionary with vault statistics
    """
    try:
        vault_path = config.VAULT_DIR

        # Count different file types
        images = len(glob.glob(str(vault_path / "**/*.jpg"), recursive=True))
        images += len(glob.glob(str(vault_path / "**/*.png"), recursive=True))
        images += len(glob.glob(str(vault_path / "**/*.gif"), recursive=True))

        videos = len(glob.glob(str(vault_path / "**/*.mp4"), recursive=True))
        videos += len(glob.glob(str(vault_path / "**/*.webm"), recursive=True))

        all_files = len(glob.glob(str(vault_path / "**/*.*"), recursive=True))

        return {
            "status": "success",
            "vault_path": str(vault_path),
            "total_files": all_files,
            "images": images,
            "videos": videos,
            "other": all_files - images - videos
        }

    except Exception as e:
        logger.error(f"Error getting vault stats: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


# Tool registry for easy lookup
TOOL_REGISTRY = {
    "scan_vault": scan_vault,
    "invoke_prayer": invoke_prayer,
    "get_vault_stats": get_vault_stats
}


def execute_tool(tool_name: str, **kwargs) -> Dict[str, Any]:
    """
    Execute a tool by name with the given arguments.

    Args:
        tool_name: Name of the tool to execute
        **kwargs: Tool-specific arguments

    Returns:
        Tool execution result
    """
    if tool_name not in TOOL_REGISTRY:
        logger.error(f"Unknown tool: {tool_name}")
        return {
            "status": "error",
            "error": f"Unknown tool: {tool_name}",
            "available_tools": list(TOOL_REGISTRY.keys())
        }

    try:
        tool_func = TOOL_REGISTRY[tool_name]
        logger.info(f"Executing tool: {tool_name} with args: {kwargs}")
        result = tool_func(**kwargs)
        return result
    except Exception as e:
        logger.error(f"Error executing tool {tool_name}: {e}")
        return {
            "status": "error",
            "error": str(e),
            "tool": tool_name
        }
