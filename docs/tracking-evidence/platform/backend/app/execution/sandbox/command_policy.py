"""
ProjectForge AI — Command Execution Policy.

Enforces command safety boundaries. Prevents arbitrary shell injection,
destructive system commands, and unauthorized execution.
"""

from __future__ import annotations

import shlex
from enum import Enum
from typing import List, Tuple


class CommandSafetyLevel(str, Enum):
    """Classification of command risk level."""
    ALLOWED = "ALLOWED"
    REQUIRES_APPROVAL = "REQUIRES_APPROVAL"
    BLOCKED = "BLOCKED"


class CommandPolicy:
    """Evaluates and filters commands against an approved development whitelist."""

    ALLOWED_BINARIES = {
        "python",
        "py",
        "python3",
        "pytest",
        "pip",
        "npm",
        "npx",
        "node",
        "git",
    }

    FORBIDDEN_PATTERNS = [
        "rm -rf",
        "rmdir /s",
        "del /f",
        "format ",
        "mkfs",
        "dd if=",
        ":(){ :|:& };:",
        "curl | sh",
        "wget | sh",
        "Invoke-WebRequest",
        "powershell -c",
        "shutdown",
        "reboot",
        "> /dev/sd",
    ]

    ALLOWED_GIT_SUBCOMMANDS = {
        "init",
        "status",
        "add",
        "commit",
        "diff",
        "reset",
        "checkout",
        "branch",
        "log",
        "rev-parse",
        "config",
    }

    @classmethod
    def evaluate(cls, command_str: str) -> Tuple[CommandSafetyLevel, str]:
        """
        Evaluate safety of a command string.
        Returns (SafetyLevel, reason).
        """
        cmd_clean = command_str.strip()
        if not cmd_clean:
            return CommandSafetyLevel.BLOCKED, "Empty command."

        # Check blacklisted dangerous patterns
        for pattern in cls.FORBIDDEN_PATTERNS:
            if pattern.lower() in cmd_clean.lower():
                return (
                    CommandSafetyLevel.BLOCKED,
                    f"Command contains forbidden destructive pattern: '{pattern}'",
                )

        # Parse binary name
        try:
            tokens = shlex.split(cmd_clean, posix=False)
        except Exception:
            tokens = cmd_clean.split()

        if not tokens:
            return CommandSafetyLevel.BLOCKED, "Cannot parse command tokens."

        raw_binary = tokens[0].strip("\"'").lower().replace(".exe", "").replace(".cmd", "")
        # Strip path if full path passed
        binary = raw_binary.split("\\")[-1].split("/")[-1].strip("\"'")

        if binary not in cls.ALLOWED_BINARIES:
            return (
                CommandSafetyLevel.BLOCKED,
                f"Binary '{binary}' is not in the approved development whitelist ({sorted(cls.ALLOWED_BINARIES)}).",
            )

        # Additional checks for git
        if binary == "git" and len(tokens) > 1:
            sub = tokens[1].lower()
            if sub not in cls.ALLOWED_GIT_SUBCOMMANDS:
                return (
                    CommandSafetyLevel.BLOCKED,
                    f"Git subcommand '{sub}' is not authorized. Allowed: {sorted(cls.ALLOWED_GIT_SUBCOMMANDS)}",
                )

        return CommandSafetyLevel.ALLOWED, "Command verified against development whitelist."
