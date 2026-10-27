"""
ProjectForge AI — Controlled Agent Tools.

Provides a safe tool interface for Coding and Debugging agents.
All interactions route strictly through the RepositoryManager.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from app.execution.repository.repository_manager import RepositoryManager


class AgentToolContext:
    """Tool execution harness scoped to a specific task and repository manager."""

    def __init__(self, repo_manager: RepositoryManager, task_id: str, allowed_files: List[str]) -> None:
        self.repo = repo_manager
        self.task_id = task_id
        self.allowed_files = allowed_files

    def read_file(self, relative_path: str) -> str:
        """Read file content."""
        return self.repo.read_file(relative_path)

    def write_file(self, relative_path: str, content: str) -> str:
        """Write file within task permission scope."""
        self.repo.write_task_file(
            task_id=self.task_id,
            relative_path=relative_path,
            content=content,
            allowed_files=self.allowed_files,
        )
        return f"Successfully wrote {relative_path}"

    def modify_file(self, relative_path: str, old_content: str, new_content: str) -> str:
        """Modify existing file within task permission scope and return diff."""
        diff = self.repo.modify_task_file(
            task_id=self.task_id,
            relative_path=relative_path,
            old_content=old_content,
            new_content=new_content,
            allowed_files=self.allowed_files,
        )
        return diff

    def list_files(self, sub_dir: str = "") -> List[str]:
        """List repository files."""
        return self.repo.list_files(sub_dir)

    def search_code(self, query: str) -> List[dict]:
        """Search code in repository."""
        return self.repo.search_code(query)
