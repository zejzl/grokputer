from __future__ import annotations

import re
from pathlib import Path
import shlex
from typing import Dict, Any

class SecurityValidator:
    """Security checks for commands and file operations"""

    DANGEROUS_PATTERNS = [
        r';\s*rm\s+-rf',  # Command chaining with rm -rf
        r'\$\(',           # Command substitution
        r'`',              # Backtick execution
        r'\|\s*bash',      # Pipe to bash
        r'wget.*\|.*sh',   # Download and execute
        r'sudo\s+',        # Sudo without confirmation
    ]

    ALLOWED_PATHS = [
        Path("./vault").resolve(),
        Path("./logs").resolve(),
        Path("./saves").resolve(),
    ]

    SENSITIVE_KEYWORDS = [
        'api_key', 'password', 'secret', 'token', 'key', 'auth'
    ]

    @classmethod
    def sanitize_command(cls, command: str) -> str:
        """Sanitize bash command"""
        # Check for dangerous patterns
        for pattern in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                raise ValueError(f"Dangerous pattern detected: {pattern}")

        # Remove null bytes and other control chars
        command = re.sub(r'[\x00-\x1F\x7F]', '', command)

        # Quote arguments if not already
        if ' ' in command:
            command = shlex.quote(command)

        return command

    @classmethod
    def validate_path(cls, path_str: str) -> Path:
        """Validate file path is within allowed directories"""
        path = Path(path_str).resolve()
        
        # Check if path is within allowed directories
        for allowed in cls.ALLOWED_PATHS:
            try:
                path.relative_to(allowed)
                return path
            except ValueError:
                continue

        raise ValueError(f"Path outside allowed directories: {path_str}")

    @classmethod
    def check_sensitive_data(cls, content: Dict[str, Any]) -> Dict[str, Any]:
        """Redact sensitive data from content"""
        redacted = content.copy()
        for key, value in redacted.items():
            if any(keyword in key.lower() for keyword in cls.SENSITIVE_KEYWORDS):
                redacted[key] = "[REDACTED]"
            elif isinstance(value, str) and any(keyword in value.lower() for keyword in cls.SENSITIVE_KEYWORDS):
                redacted[key] = "[REDACTED]"
        return redacted

    @classmethod
    def validate_input(cls, user_input: str) -> str:
        """General input validation"""
        # Block SQL injection patterns
        sql_patterns = [r"select.*from", r"drop.*table", r"insert.*into"]
        for pattern in sql_patterns:
            if re.search(pattern, user_input, re.IGNORECASE):
                raise ValueError("SQL injection attempt detected")

        # Block path traversal
        if ".." in user_input or "/" in user_input:
            raise ValueError("Path traversal attempt detected")

        return user_input.strip()

# Integration example for Actor agent
def safe_bash_execute(command: str) -> str:
    """Execute bash command with security checks"""
    validator = SecurityValidator()
    sanitized = validator.sanitize_command(command)
    # Use subprocess.run with shell=False
    import subprocess
    result = subprocess.run(
        shlex.split(sanitized),
        capture_output=True,
        text=True,
        timeout=30
    )
    return result.stdout + result.stderr