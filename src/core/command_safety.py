"""
Shared command-safety checks.

Commands are always run without a shell (shlex.split + subprocess shell=False), so these checks
decide whether a command string may run at all.

Layer 1, shell metacharacters (`find_shell_metacharacter`): used by ActionExecutor, the toolkit's
bash() and the Actor. Rejecting them means a command cannot chain, pipe, redirect or expand.

Layer 2, blocked programs (`find_blocked_program`): destructive or network programs that contain
no metacharacters at all (`format c:`, `shutdown now`, `curl http://...`). Used by the Actor.
ActionExecutor only applies layer 1 on purpose, so its behaviour is unchanged.

`check_command` returns a human-readable reason when a command must be refused, or None when it is
acceptable. It is a guard rail, not a sandbox: an allowed program can still do harm.
"""
from __future__ import annotations

import ntpath
import shlex
from typing import List, Optional, Set

SHELL_METACHARACTERS: List[str] = [";", "&", "|", "<", ">", "$", "`", "\\", "\n", "\r", "%", "(", ")"]

# Blocked whatever their arguments (name without directory or extension, lowercase).
BLOCKED_PROGRAMS: Set[str] = {
    # disks, power
    "format", "diskpart", "fdisk", "wipefs", "shred", "dd", "shutdown", "reboot", "halt", "poweroff",
    # network
    "curl", "wget", "nc", "ncat", "netcat",
    # interpreters that would run a command string and bypass the checks
    "cmd", "powershell", "pwsh", "bash", "sh", "zsh", "wsl", "wscript", "cscript", "mshta",
}  # fmt: skip

# Fine for single files, blocked with recursive/forced flags.
_UNIX_DELETE = {"rm"}
_UNIX_DELETE_FLAGS = set("rRf")
_UNIX_DELETE_LONG = {"--recursive", "--force", "--no-preserve-root"}
_WINDOWS_DELETE = {"del", "erase", "rd", "rmdir"}
_WINDOWS_DELETE_FLAGS = {"/s", "/q", "/f"}


def find_shell_metacharacter(command: str) -> Optional[str]:
    """Return the first shell metacharacter found in `command`, or None."""
    for char in SHELL_METACHARACTERS:
        if char in command:
            return char
    return None


def _program_name(token: str) -> str:
    name = ntpath.basename(token.replace("/", "\\")).lower()
    for ext in (".exe", ".com", ".bat", ".cmd", ".ps1"):
        if name.endswith(ext):
            return name[: -len(ext)]
    return name


def find_blocked_program(command: str) -> Optional[str]:
    """Return why the program in `command` is blocked, or None."""
    try:
        argv = shlex.split(command)
    except ValueError as e:
        return f"unparseable command ({e})"
    if not argv:
        return "empty command"

    program = _program_name(argv[0])
    args = argv[1:]

    if program in BLOCKED_PROGRAMS or program.startswith("mkfs"):
        return f"program '{program}' is blocked"
    if program in _UNIX_DELETE:
        for arg in args:
            if arg in _UNIX_DELETE_LONG or (arg.startswith("-") and not arg.startswith("--") and _UNIX_DELETE_FLAGS & set(arg)):
                return f"'{program} {arg}' (recursive or forced delete) is blocked"
    if program in _WINDOWS_DELETE:
        for arg in args:
            if arg.lower() in _WINDOWS_DELETE_FLAGS:
                return f"'{program} {arg}' (recursive or forced delete) is blocked"
    return None


def check_command(command: str, block_programs: bool = True) -> Optional[str]:
    """
    Return a reason to refuse `command`, or None if it may run.

    Args:
        command: Command line (never passed to a shell)
        block_programs: Also apply layer 2 (blocked programs)
    """
    if not command or not command.strip():
        return "empty command"
    char = find_shell_metacharacter(command)
    if char is not None:
        return f"shell metacharacter {char!r} is not allowed"
    return find_blocked_program(command) if block_programs else None
