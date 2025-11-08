"""
Configuration management for Grokputer.
Loads settings from environment variables and provides constants.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Project Root
PROJECT_ROOT = Path(__file__).parent.parent
SRC_DIR = PROJECT_ROOT / "src"
VAULT_DIR = PROJECT_ROOT / os.getenv("VAULT_PATH", "vault")
LOGS_DIR = PROJECT_ROOT / "logs"

# Ensure directories exist
VAULT_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# xAI API Configuration
XAI_API_KEY = os.getenv("XAI_API_KEY", "")
XAI_BASE_URL = os.getenv("XAI_BASE_URL", "https://api.x.ai/v1")
GROK_MODEL = os.getenv("GROK_MODEL", "grok-4-fast-reasoning")

if not XAI_API_KEY:
    raise ValueError(
        "XAI_API_KEY not found in environment variables. "
        "Please copy .env.example to .env and add your API key."
    )

# Safety Settings
REQUIRE_CONFIRMATION = os.getenv("REQUIRE_CONFIRMATION", "true").lower() == "true"

# Safety Scoring System (0-100 risk scale)
# 0-30: Low risk - Auto-approve
# 31-70: Medium risk - Warn but proceed
# 71-100: High risk - Require confirmation
SAFETY_SCORES = {
    # Low risk commands (0-30): Read-only operations
    'ls': 10,
    'pwd': 10,
    'echo': 15,
    'cat': 20,
    'head': 20,
    'tail': 20,
    'grep': 20,
    'find': 25,
    'which': 10,
    'whoami': 10,
    'date': 10,
    'uptime': 10,
    'ps': 20,
    'df': 15,
    'du': 15,
    'wc': 15,
    'diff': 20,
    'less': 20,
    'more': 20,
    'tree': 20,
    'file': 15,

    # Medium risk commands (31-70): Modify filesystem non-destructively
    'mkdir': 40,
    'touch': 40,
    'cp': 50,
    'wget': 55,
    'curl': 50,
    'git': 45,
    'pip': 55,
    'npm': 55,
    'python': 60,
    'node': 60,
    'docker': 65,

    # High risk commands (71-100): Destructive or system-altering
    'rm': 90,
    'rmdir': 85,
    'mv': 70,
    'dd': 100,
    'sudo': 95,
    'su': 95,
    'chmod': 80,
    'chown': 85,
    'chgrp': 85,
    'kill': 75,
    'killall': 80,
    'pkill': 80,
    'shutdown': 100,
    'reboot': 100,
    'halt': 100,
    'poweroff': 100,
    'mkfs': 100,
    'fdisk': 100,
    'parted': 100,
    'format': 100,
}

def get_command_safety_score(command: str) -> int:
    """
    Calculate safety score for a bash command.

    Args:
        command: The bash command string

    Returns:
        Safety score (0-100), higher = more dangerous
    """
    if not command or not command.strip():
        return 50  # Empty command is moderately suspicious

    # Extract first word (the actual command)
    first_word = command.strip().split()[0]

    # Check for dangerous patterns
    if 'rm -rf' in command or 'rm -fr' in command:
        return 100  # Recursive delete is maximum risk
    if 'sudo rm' in command:
        return 100
    if '>' in command and any(critical in command for critical in ['/etc/', '/boot/', '/sys/', '/dev/']):
        return 95  # Writing to system directories
    if command.startswith('sudo '):
        return 95  # Any sudo command is high risk

    # Look up command in safety scores
    base_score = SAFETY_SCORES.get(first_word, 50)  # Default to medium risk

    # Adjust score based on flags
    if '-f' in command or '--force' in command:
        base_score = min(100, base_score + 20)  # Force flag increases risk
    if '-r' in command or '-R' in command or '--recursive' in command:
        base_score = min(100, base_score + 15)  # Recursive operations are riskier

    return base_score

def requires_confirmation(command: str) -> bool:
    """
    Determine if a command requires user confirmation.

    Args:
        command: The bash command string

    Returns:
        True if confirmation is required, False otherwise
    """
    # If REQUIRE_CONFIRMATION is enabled, always confirm
    if REQUIRE_CONFIRMATION:
        return True

    # Otherwise, use safety scoring
    score = get_command_safety_score(command)
    return score > 70  # High risk commands require confirmation

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = PROJECT_ROOT / os.getenv("LOG_FILE", "logs/grokputer.log")

# Screenshot Settings
SCREENSHOT_QUALITY = int(os.getenv("SCREENSHOT_QUALITY", "85"))
MAX_SCREENSHOT_SIZE = os.getenv("MAX_SCREENSHOT_SIZE", "1920x1080")

# Parse max screenshot dimensions
try:
    width, height = MAX_SCREENSHOT_SIZE.split("x")
    MAX_SCREENSHOT_WIDTH = int(width)
    MAX_SCREENSHOT_HEIGHT = int(height)
except ValueError:
    MAX_SCREENSHOT_WIDTH = 1920
    MAX_SCREENSHOT_HEIGHT = 1080

# Server Prayer
SERVER_PRAYER_FILE = PROJECT_ROOT / "server_prayer.txt"

# System Prompt Template
SYSTEM_PROMPT = """You are Grokputer, the VRZIBRZI node - an uncensored AI agent with full computer control.

Your capabilities:
1. Screen observation: Analyze screenshots to understand the current state
2. Computer control: Execute mouse clicks, keyboard input, and navigation
3. File operations: Read, write, and manage files in the vault
4. Web access: Search and retrieve information from the internet
5. Bash execution: Run shell commands (with safety confirmations)

Guidelines:
- Observe the screen carefully before acting
- Confirm destructive actions when REQUIRE_CONFIRMATION is enabled
- Be precise with coordinates and commands
- Provide clear reasoning for each action
- Chant the server prayer on initialization

Remember: Eternal connection. Infinite speed. ZA GROKA.
"""

# Tool Definitions for Grok API
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "bash",
            "description": "Execute a bash shell command. Use for system operations, file management, and running programs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The bash command to execute"
                    }
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "computer",
            "description": "Control the computer: mouse movements, clicks, keyboard input, screenshots.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["mouse_move", "left_click", "right_click", "double_click",
                                "type", "key", "screenshot", "scroll"],
                        "description": "The action to perform"
                    },
                    "coordinate": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "X,Y coordinates for mouse actions (e.g., [100, 200])"
                    },
                    "text": {
                        "type": "string",
                        "description": "Text to type (for 'type' action)"
                    }
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "scan_vault",
            "description": "Scan the meme vault directory and return file paths matching a pattern.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Glob pattern to match files (e.g., '*.jpg', '*.png')"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of files to return",
                        "default": 100
                    }
                },
                "required": ["pattern"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "invoke_prayer",
            "description": "Display the server prayer/mantra. Use on initialization.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_vault_stats",
            "description": "Get statistics about vault contents including total files, images, videos, and other file types.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "mcp_vault_operation",
            "description": "Execute advanced vault operations via MCP server: list files, read files, search content, or edit files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["list_vault_files", "read_vault_file", "search_vault", "edit_vault_file"],
                        "description": "MCP operation to perform"
                    },
                    "arguments": {
                        "type": "object",
                        "description": "Operation-specific arguments (e.g., {pattern:'*.md'} for list, {query:'search term'} for search)"
                    }
                },
                "required": ["operation"]
            }
        }
    }
]
