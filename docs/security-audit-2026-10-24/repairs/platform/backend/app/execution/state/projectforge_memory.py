"""
ProjectForge AI — Project Memory & State Manager.

Manages the persistent `.projectforge/` directory inside generated projects.
Stores machine-readable specifications, task graphs, audit logs, test outcomes,
and checkpoint histories.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


class ProjectForgeMemoryManager:
    """Manages the .projectforge persistent metadata directory."""

    def __init__(self, workspace_root: Path | str) -> None:
        self.workspace_root = Path(workspace_root).resolve()
        self.memory_dir = self.workspace_root / ".projectforge"
        self.memory_dir.mkdir(parents=True, exist_ok=True)

    def write_json(self, filename: str, data: Any) -> Path:
        """Write JSON data to a file inside .projectforge/."""
        target = self.memory_dir / filename
        target.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        return target

    def read_json(self, filename: str) -> Optional[Any]:
        """Read JSON data from a file inside .projectforge/."""
        target = self.memory_dir / filename
        if not target.is_file():
            return None
        try:
            return json.loads(target.read_text(encoding="utf-8"))
        except Exception:
            return None

    def append_log(self, entry: Dict[str, Any]) -> None:
        """Append entry to .projectforge/execution_log.json."""
        log_file = self.memory_dir / "execution_log.json"
        entries: List[Dict[str, Any]] = []
        if log_file.is_file():
            try:
                entries = json.loads(log_file.read_text(encoding="utf-8"))
            except Exception:
                entries = []
        entries.append(entry)
        log_file.write_text(json.dumps(entries, indent=2, default=str), encoding="utf-8")

    def initialize_memory(self, project_id: str, project_name: str, raw_idea: str) -> None:
        """Initialize base project metadata."""
        self.write_json("project.json", {
            "project_id": project_id,
            "project_name": project_name,
            "raw_idea": raw_idea,
            "status": "INITIALIZED",
        })
