"""
Grokputer MCP Server

Exposes vault scanning, prayer invocation, and vault statistics via MCP.
Built with FastMCP for <3s startup and lightweight deployment.
"""

import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional
import glob
import os
import json
import subprocess
import base64
from io import BytesIO
import aiofiles

try:
    from fastmcp import FastMCP
except ImportError:
    # Fallback to basic server implementation
    print("Warning: FastMCP not installed. Install with: pip install fastmcp")
    import sys
    sys.exit(1)

try:
    # Set dummy DISPLAY for Docker environments (pyautogui requires it)
    if 'DISPLAY' not in os.environ:
        os.environ['DISPLAY'] = ':99'
    import pyautogui
    from PIL import Image
    HAS_PYAUTOGUI = True
except Exception as e:
    # Catch all exceptions: ImportError, KeyError, Xlib.error.DisplayConnectionError, etc.
    HAS_PYAUTOGUI = False
    print(f"Warning: pyautogui/PIL not available ({type(e).__name__}: {e}). Screen capture tools will be disabled.")


# Initialize FastMCP server
mcp = FastMCP("grokputer")


@mcp.tool()
async def scan_vault(vault_path: str = "vault") -> Dict[str, Any]:
    """
    Scan vault directory for files and return inventory.

    Args:
        vault_path: Path to vault directory (default: "vault")

    Returns:
        Dictionary with file list and metadata
    """
    try:
        vault_dir = Path(vault_path)

        if not vault_dir.exists():
            return {
                "success": False,
                "error": f"Vault directory not found: {vault_path}",
                "files": []
            }

        # Scan for all files
        files = []
        for pattern in ["**/*.pdf", "**/*.md", "**/*.txt", "**/*.json"]:
            for file_path in vault_dir.glob(pattern):
                if file_path.is_file():
                    stat = file_path.stat()
                    files.append({
                        "path": str(file_path.relative_to(vault_dir)),
                        "size": stat.st_size,
                        "modified": stat.st_mtime
                    })

        return {
            "success": True,
            "vault_path": str(vault_dir),
            "total_files": len(files),
            "files": files[:50]  # Limit to first 50 for performance
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "files": []
        }


@mcp.tool()
async def invoke_prayer(prayer_type: str = "server_prayer") -> Dict[str, str]:
    """
    Invoke a prayer ritual from the server_prayer.txt file.

    Args:
        prayer_type: Type of prayer (currently only "server_prayer" supported)

    Returns:
        Dictionary with prayer text and invocation status
    """
    try:
        prayer_file = Path("server_prayer.txt")

        if not prayer_file.exists():
            return {
                "success": False,
                "error": "server_prayer.txt not found",
                "prayer": ""
            }

        # Read prayer text
        prayer_text = prayer_file.read_text(encoding="utf-8")

        return {
            "success": True,
            "prayer_type": prayer_type,
            "prayer": prayer_text,
            "message": "Prayer invoked successfully. VRZIBRZI node eternal."
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "prayer": ""
        }


@mcp.tool()
async def get_vault_stats(vault_path: str = "vault") -> Dict[str, Any]:
    """
    Get statistics about vault contents.

    Args:
        vault_path: Path to vault directory (default: "vault")

    Returns:
        Dictionary with vault statistics (file counts, total size, types)
    """
    try:
        vault_dir = Path(vault_path)

        if not vault_dir.exists():
            return {
                "success": False,
                "error": f"Vault directory not found: {vault_path}",
                "stats": {}
            }

        # Gather statistics
        stats = {
            "total_files": 0,
            "total_size": 0,
            "by_extension": {}
        }

        for file_path in vault_dir.rglob("*"):
            if file_path.is_file():
                stats["total_files"] += 1
                size = file_path.stat().st_size
                stats["total_size"] += size

                # Track by extension
                ext = file_path.suffix.lower() or ".no_extension"
                if ext not in stats["by_extension"]:
                    stats["by_extension"][ext] = {"count": 0, "total_size": 0}

                stats["by_extension"][ext]["count"] += 1
                stats["by_extension"][ext]["total_size"] += size

        return {
            "success": True,
            "vault_path": str(vault_dir),
            "stats": stats
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "stats": {}
        }


@mcp.tool()
async def execute_bash_safe(command: str, require_confirm: bool = False) -> Dict[str, Any]:
    """
    Execute bash command with safety check.

    Args:
        command: Bash command to execute
        require_confirm: If True, will return command for manual confirmation

    Returns:
        Dictionary with execution results and safety score
    """
    try:
        # Basic safety scoring (simplified version)
        safety_score = 0
        risk_keywords = ['rm ', 'del ', 'format', 'shutdown', 'reboot', '>']
        for keyword in risk_keywords:
            if keyword in command.lower():
                safety_score += 30

        if len(command) > 100:
            safety_score += 10

        safety_level = "low" if safety_score < 30 else ("medium" if safety_score < 70 else "high")

        if require_confirm or safety_score > 70:
            return {
                "success": False,
                "error": "Command requires manual confirmation",
                "command": command,
                "safety_score": safety_score,
                "safety_level": safety_level,
                "message": "High-risk command detected. Execute manually if needed."
            }

        # Execute command
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )

        return {
            "success": result.returncode == 0,
            "command": command,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode,
            "safety_score": safety_score,
            "safety_level": safety_level
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Command timeout (30s)",
            "command": command
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "command": command
        }


@mcp.tool()
async def capture_screenshot_region(
    left: int,
    top: int,
    width: int,
    height: int
) -> Dict[str, Any]:
    """
    Capture a specific region of the screen.

    Args:
        left: Left coordinate
        top: Top coordinate
        width: Width of region
        height: Height of region

    Returns:
        Dictionary with base64-encoded screenshot and metadata
    """
    if not HAS_PYAUTOGUI:
        return {
            "success": False,
            "error": "pyautogui not installed. Install with: pip install pyautogui pillow"
        }

    try:
        # Capture screenshot region
        screenshot = pyautogui.screenshot(region=(left, top, width, height))

        # Convert to base64
        buffer = BytesIO()
        screenshot.save(buffer, format='PNG')
        img_bytes = buffer.getvalue()
        base64_img = base64.b64encode(img_bytes).decode('utf-8')

        return {
            "success": True,
            "base64_image": base64_img,
            "region": {"left": left, "top": top, "width": width, "height": height},
            "size_bytes": len(img_bytes),
            "format": "PNG"
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "region": {"left": left, "top": top, "width": width, "height": height}
        }


@mcp.tool()
async def get_screen_info() -> Dict[str, Any]:
    """
    Get information about the display/screen.

    Returns:
        Dictionary with screen dimensions and info
    """
    if not HAS_PYAUTOGUI:
        return {
            "success": False,
            "error": "pyautogui not installed"
        }

    try:
        size = pyautogui.size()
        return {
            "success": True,
            "width": size.width,
            "height": size.height,
            "center_x": size.width // 2,
            "center_y": size.height // 2
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
async def list_recent_sessions(limit: int = 10) -> Dict[str, Any]:
    """
    List recent Grokputer execution sessions.

    Args:
        limit: Maximum number of sessions to return

    Returns:
        Dictionary with list of recent sessions
    """
    try:
        logs_dir = Path("logs")

        if not logs_dir.exists():
            return {
                "success": True,
                "sessions": [],
                "message": "No logs directory found"
            }

        # Get session directories
        sessions = []
        for session_dir in sorted(logs_dir.iterdir(), reverse=True)[:limit]:
            if session_dir.is_dir():
                session_json = session_dir / "session.json"
                if session_json.exists():
                    try:
                        async with aiofiles.open(session_json, 'r') as f:
                            content = await f.read()
                            data = json.loads(content)
                            sessions.append({
                                "session_id": session_dir.name,
                                "task": data.get("task", "Unknown"),
                                "timestamp": data.get("timestamp", "Unknown"),
                                "status": data.get("status", "Unknown")
                            })
                    except Exception:
                        sessions.append({
                            "session_id": session_dir.name,
                            "error": "Could not parse session.json"
                        })

        return {
            "success": True,
            "sessions": sessions,
            "total": len(sessions)
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "sessions": []
        }


@mcp.tool()
async def get_session_details(session_id: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific session.

    Args:
        session_id: The session ID to retrieve

    Returns:
        Dictionary with full session data
    """
    try:
        session_path = Path("logs") / session_id / "session.json"

        if not session_path.exists():
            return {
                "success": False,
                "error": f"Session not found: {session_id}"
            }

        async with aiofiles.open(session_path, 'r') as f:
            content = await f.read()
            data = json.loads(content)

        return {
            "success": True,
            "session_id": session_id,
            "data": data
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "session_id": session_id
        }


@mcp.tool()
async def ask_qwen(question: str, context_files: List[str] = []) -> Dict[str, Any]:
    """
    Query local Qwen Coder model (when installed).

    Args:
        question: Question to ask Qwen
        context_files: Optional list of file paths for context

    Returns:
        Dictionary with Qwen's response
    """
    try:
        # Check if run_qwen.py exists
        qwen_script = Path("run_qwen.py")
        if not qwen_script.exists():
            return {
                "success": False,
                "error": "Qwen not installed. run_qwen.py not found",
                "message": "Install Qwen: Download model to ./models/ and ensure llama-cpp-python is installed"
            }

        # Check if model exists
        model_path = Path("models") / "qwen2.5-coder-7b-instruct-q4_k_m.gguf"
        if not model_path.exists():
            return {
                "success": False,
                "error": "Qwen model not downloaded",
                "message": "Download model: huggingface-cli download Qwen/Qwen2.5-Coder-7B-Instruct-GGUF qwen2.5-coder-7b-instruct-q4_k_m.gguf --local-dir ./models"
            }

        # For now, return placeholder
        return {
            "success": False,
            "error": "Qwen integration not yet implemented in MCP server",
            "message": "Use run_qwen.py directly for now",
            "question": question,
            "context_files": context_files
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "question": question
        }


# Expose ASGI app for uvicorn (FastMCP provides http_app attribute)
app = mcp.http_app

# Entry point for direct execution
if __name__ == "__main__":
    mcp.run()
