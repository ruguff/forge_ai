"""
ProjectForge AI — Git Checkpoint Manager.

Creates deterministic checkpoints before and after major phases and autonomous repairs.
Provides rollback capability: if an autonomous repair introduces regressions,
the project can be cleanly restored to the previous checkpoint.
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class GitManager:
    """Manages Git versioning and phase checkpoints for a generated project."""

    def __init__(self, workspace_root: Path | str) -> None:
        self.workspace_root = Path(workspace_root).resolve()
        self.checkpoints_file = self.workspace_root / ".projectforge" / "checkpoints.json"
        self._git_bin = shutil.which("git")

    def _run_git(self, args: List[str]) -> subprocess.CompletedProcess:
        """Run git command inside workspace root."""
        if not self._git_bin:
            raise RuntimeError("Git binary not found on system PATH.")
        return subprocess.run(
            [self._git_bin, *args],
            cwd=str(self.workspace_root),
            capture_output=True,
            text=True,
            check=False,
        )

    def init_repository(self) -> bool:
        """Initialize git repo and configure local user if not already set."""
        if not self._git_bin:
            logger.warning("Git not available, skipping git initialization.")
            return False

        try:
            self._run_git(["init"])
            self._run_git(["config", "user.name", "ProjectForge AI"])
            self._run_git(["config", "user.email", "agent@projectforge.ai"])
            return True
        except Exception as e:
            logger.error("Failed to initialize git repository: %s", e)
            return False

    def create_checkpoint(self, checkpoint_name: str, message: Optional[str] = None) -> bool:
        """
        Stage all files and commit with a named checkpoint tag.
        Also records the checkpoint in .projectforge/checkpoints.json.
        """
        commit_msg = message or f"checkpoint: {checkpoint_name}"
        timestamp = datetime.now(timezone.utc).isoformat()
        commit_hash = "manual-snapshot"

        if self._git_bin:
            try:
                self._run_git(["add", "-A"])
                res = self._run_git(["commit", "-m", commit_msg])
                hash_res = self._run_git(["rev-parse", "HEAD"])
                if hash_res.returncode == 0:
                    commit_hash = hash_res.stdout.strip()
            except Exception as e:
                logger.warning("Git commit failed: %s", e)

        # Record in checkpoints.json
        self._record_checkpoint({
            "name": checkpoint_name,
            "message": commit_msg,
            "commit_hash": commit_hash,
            "timestamp": timestamp,
        })
        return True

    def restore_checkpoint(self, checkpoint_name: str) -> bool:
        """Restore repository state to a previous named checkpoint."""
        history = self.get_checkpoint_history()
        target = next((c for c in reversed(history) if c.get("name") == checkpoint_name), None)
        if not target:
            logger.error("Checkpoint not found: %s", checkpoint_name)
            return False

        commit_hash = target.get("commit_hash")
        if self._git_bin and commit_hash and commit_hash != "manual-snapshot":
            res = self._run_git(["reset", "--hard", commit_hash])
            return res.returncode == 0
        return False

    def get_checkpoint_history(self) -> List[Dict[str, str]]:
        """Read checkpoint history from disk."""
        if not self.checkpoints_file.is_file():
            return []
        try:
            return json.loads(self.checkpoints_file.read_text(encoding="utf-8"))
        except Exception:
            return []

    def _record_checkpoint(self, record: Dict[str, str]) -> None:
        """Append record to .projectforge/checkpoints.json."""
        self.checkpoints_file.parent.mkdir(parents=True, exist_ok=True)
        history = self.get_checkpoint_history()
        history.append(record)
        self.checkpoints_file.write_text(json.dumps(history, indent=2), encoding="utf-8")
