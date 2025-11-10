"""
Custom tools for Grokputer.
Implements vault scanning, prayer invocation, and other VRZIBRZI-specific functions.
"""

import glob
import logging
import subprocess
import json
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


def mcp_vault_operation(operation: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Execute MCP vault server operation.

    Args:
        operation: Tool name (list_vault_files, read_vault_file, search_vault, edit_vault_file)
        arguments: Tool-specific arguments

    Returns:
        MCP server response
    """
    if arguments is None:
        arguments = {}

    try:
        # Construct JSON-RPC request
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": operation,
                "arguments": arguments
            }
        }

        # Run MCP server container
        vault_path = config.VAULT_DIR.resolve()
        cmd = [
            "docker", "run", "-i", "--rm",
            "-v", f"{vault_path}:/app/vault",
            "grokputer-mcp-vault"
        ]

        logger.info(f"Calling MCP operation: {operation} with args: {arguments}")

        result = subprocess.run(
            cmd,
            input=json.dumps(request),
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            logger.error(f"MCP server error: {result.stderr}")
            return {
                "status": "error",
                "error": result.stderr or "MCP server failed"
            }

        # Parse JSON-RPC response
        try:
            response = json.loads(result.stdout.strip())

            if "error" in response:
                return {
                    "status": "error",
                    "error": response["error"].get("message", "Unknown error")
                }

            result_data = response.get("result", {})

            # Extract text content from MCP response
            content = result_data.get("content", [])
            if content and len(content) > 0:
                text_content = content[0].get("text", "")

                # Try to parse as JSON for structured data
                try:
                    parsed = json.loads(text_content)
                    return {
                        "status": "success",
                        "operation": operation,
                        "data": parsed
                    }
                except json.JSONDecodeError:
                    # Return as plain text
                    return {
                        "status": "success",
                        "operation": operation,
                        "text": text_content
                    }

            return {
                "status": "success",
                "operation": operation,
                "result": result_data
            }

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse MCP response: {e}")
            return {
                "status": "error",
                "error": f"Invalid MCP response: {result.stdout}"
            }

    except subprocess.TimeoutExpired:
        logger.error("MCP operation timed out")
        return {
            "status": "error",
            "error": "MCP operation timed out (30s)"
        }
    except Exception as e:
        logger.error(f"Error calling MCP: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


# Tool registry for easy lookup
TOOL_REGISTRY = {
    "scan_vault": scan_vault,
    "invoke_prayer": invoke_prayer,
    "get_vault_stats": get_vault_stats,
    "mcp_vault_operation": mcp_vault_operation
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
