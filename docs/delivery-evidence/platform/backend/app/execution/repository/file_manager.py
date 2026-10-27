"""
ProjectForge AI — Safe File Manager.

Handles atomic file writes, reads, deletions, and unified diff calculations.
Guarantees sandbox path safety (rejects path traversal outside workspace root).
"""

from __future__ import annotations

import difflib
import os
import shutil
from pathlib import Path
from typing import List, Optional


class FileAccessViolationError(Exception):
    """Raised when an operation attempts to access files outside the workspace root."""


class SafeFileManager:
    """Sandbox file manager operating within a strictly bounded directory."""

    def __init__(self, workspace_root: Path | str) -> None:
        self.workspace_root = Path(workspace_root).resolve()
        self.workspace_root.mkdir(parents=True, exist_ok=True)

    def _resolve_safe_path(self, relative_path: str) -> Path:
        """Resolve path and verify it remains strictly inside workspace_root."""
        target = (self.workspace_root / relative_path).resolve()
        if not target.is_relative_to(self.workspace_root):
            raise FileAccessViolationError(
                f"Path traversal detected: {relative_path} attempts to escape workspace root {self.workspace_root}"
            )
        return target

    def write_file(self, relative_path: str, content: str) -> Path:
        """Atomically create or overwrite a file within the workspace."""
        path = self._resolve_safe_path(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(content)
        try:
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
        return path

    def read_file(self, relative_path: str) -> str:
        """Read text contents of a file in the workspace."""
        path = self._resolve_safe_path(relative_path)
        if not path.is_file():
            raise FileNotFoundError(f"File not found: {relative_path}")
        return path.read_text(encoding="utf-8")

    def modify_file(self, relative_path: str, old_content: str, new_content: str) -> str:
        """
        Replace old_content with new_content inside an existing file.
        Returns the unified diff string.
        """
        path = self._resolve_safe_path(relative_path)
        if not path.is_file():
            raise FileNotFoundError(f"File not found to modify: {relative_path}")

        current = path.read_text(encoding="utf-8")
        if old_content not in current:
            raise ValueError(f"Target content not found in {relative_path}")

        updated = current.replace(old_content, new_content, 1)
        self.write_file(relative_path, updated)

        diff = difflib.unified_diff(
            current.splitlines(keepends=True),
            updated.splitlines(keepends=True),
            fromfile=f"a/{relative_path}",
            tofile=f"b/{relative_path}",
        )
        return "".join(diff)

    def delete_file(self, relative_path: str) -> bool:
        """Safely delete a file in workspace."""
        path = self._resolve_safe_path(relative_path)
        if path.is_file():
            path.unlink()
            return True
        return False

    def list_files(self, sub_dir: str = "") -> List[str]:
        """List all relative file paths inside the workspace (ignoring .git)."""
        search_root = self._resolve_safe_path(sub_dir) if sub_dir else self.workspace_root
        results: List[str] = []
        for root, dirs, files in os.walk(search_root):
            # Ignore git internals
            if ".git" in dirs:
                dirs.remove(".git")
            for f in files:
                full_path = Path(root) / f
                rel = full_path.relative_to(self.workspace_root)
                results.append(str(rel).replace("\\", "/"))
        return sorted(results)

    def search_code(self, query: str) -> List[dict]:
        """Search code files for an exact string query."""
        matches = []
        for rel_path in self.list_files():
            if rel_path.startswith(".projectforge/"):
                continue
            try:
                content = self.read_file(rel_path)
                lines = content.splitlines()
                for i, line in enumerate(lines, 1):
                    if query in line:
                        matches.append({
                            "file": rel_path,
                            "line_number": i,
                            "line_content": line.strip(),
                        })
            except Exception:
                continue
        return matches
