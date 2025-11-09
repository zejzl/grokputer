"""
Grokputer MCP Server

Exposes vault scanning, prayer invocation, and vault statistics via MCP.
Built with FastMCP for <3s startup and lightweight deployment.
"""

import asyncio
from pathlib import Path
from typing import Dict, List, Any
import glob
import os
import aiofiles

try:
    from fastmcp import FastMCP
except ImportError:
    # Fallback to basic server implementation
    print("Warning: FastMCP not installed. Install with: pip install fastmcp")
    import sys
    sys.exit(1)


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


# Expose ASGI app for uvicorn (FastMCP provides http_app attribute)
app = mcp.http_app

# Entry point for direct execution
if __name__ == "__main__":
    mcp.run()
