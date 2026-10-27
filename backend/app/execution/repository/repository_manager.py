"""
ProjectForge AI — Repository Manager.

Primary file & repository abstraction layer for Milestone 3.
All agent code modifications MUST pass through this manager.
Enforces task-level traceability and permission validation.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Optional

from app.execution.repository.file_manager import SafeFileManager
from app.execution.repository.git_manager import GitManager

logger = logging.getLogger(__name__)


class TaskScopeViolationError(Exception):
    """Raised when an agent attempts to create or modify a file not authorized in the task."""


class RepositoryManager:
    """Controlled repository manager with task traceability and Git versioning."""

    def __init__(self, workspace_root: Path | str) -> None:
        self.workspace_root = Path(workspace_root).resolve()
        self.file_manager = SafeFileManager(self.workspace_root)
        self.git_manager = GitManager(self.workspace_root)
        self.audit_log: List[Dict[str, str]] = []

    def initialize_project(self) -> None:
        """Create directory scaffold and initialize Git."""
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        (self.workspace_root / ".projectforge").mkdir(parents=True, exist_ok=True)
        self.git_manager.init_repository()
        self.git_manager.create_checkpoint("initial_scaffold", "Initial project scaffold created")

    def write_task_file(
        self,
        task_id: str,
        relative_path: str,
        content: str,
        allowed_files: Optional[List[str]] = None,
    ) -> Path:
        """
        Write a file on behalf of an implementation task.
        Validates that the file is in allowed_files (if specified).
        """
        norm_path = relative_path.replace("\\", "/")
        if allowed_files is not None:
            norm_allowed = [f.replace("\\", "/") for f in allowed_files]
            if norm_path not in norm_allowed:
                raise TaskScopeViolationError(
                    f"Task {task_id} attempted to write unauthorized file: {relative_path}. "
                    f"Authorized scope: {norm_allowed}"
                )

        written_path = self.file_manager.write_file(relative_path, content)
        self.audit_log.append({
            "task_id": task_id,
            "action": "WRITE_FILE",
            "file": norm_path,
        })
        return written_path

    def modify_task_file(
        self,
        task_id: str,
        relative_path: str,
        old_content: str,
        new_content: str,
        allowed_files: Optional[List[str]] = None,
    ) -> str:
        """Modify an existing file on behalf of a task and return diff."""
        norm_path = relative_path.replace("\\", "/")
        if allowed_files is not None:
            norm_allowed = [f.replace("\\", "/") for f in allowed_files]
            if norm_path not in norm_allowed:
                raise TaskScopeViolationError(
                    f"Task {task_id} attempted to modify unauthorized file: {relative_path}. "
                    f"Authorized scope: {norm_allowed}"
                )

        diff = self.file_manager.modify_file(relative_path, old_content, new_content)
        self.audit_log.append({
            "task_id": task_id,
            "action": "MODIFY_FILE",
            "file": norm_path,
        })
        return diff

    def read_file(self, relative_path: str) -> str:
        """Read file contents safely."""
        return self.file_manager.read_file(relative_path)

    def list_files(self, sub_dir: str = "") -> List[str]:
        """List repository files."""
        return self.file_manager.list_files(sub_dir)

    def search_code(self, query: str) -> List[dict]:
        """Search code files."""
        return self.file_manager.search_code(query)

    def create_checkpoint(self, checkpoint_name: str, message: Optional[str] = None) -> bool:
        """Create Git checkpoint."""
        return self.git_manager.create_checkpoint(checkpoint_name, message)

    def restore_checkpoint(self, checkpoint_name: str) -> bool:
        """Restore previous Git checkpoint."""
        return self.git_manager.restore_checkpoint(checkpoint_name)
