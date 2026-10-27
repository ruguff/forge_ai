"""
ProjectForge AI — VS Code Launcher.

Safely opens the generated project workspace in VS Code.
Enforces pre-flight verification: refuses to open if the project does not exist
or if automated verification tests have not passed.
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from pathlib import Path
from typing import Tuple

logger = logging.getLogger(__name__)


class VSCodeLauncher:
    """Pre-flight verified launcher for Visual Studio Code."""

    @classmethod
    def open_project(
        cls,
        workspace_root: Path | str,
        require_verified_tests: bool = True,
    ) -> Tuple[bool, str]:
        """
        Verify project readiness and launch VS Code.
        Returns (success: bool, message: str).
        """
        root = Path(workspace_root).resolve()

        # 1. Verify directory exists
        if not root.is_dir():
            return False, f"Workspace directory does not exist: {root}"

        # 2. Verify required scaffold files exist
        required_files = ["README.md"]
        for f in required_files:
            if not (root / f).is_file():
                return False, f"Pre-flight verification failed: Missing required file '{f}'."

        # 3. Verify tests passed according to criteria
        if require_verified_tests:
            verification_file = root / ".projectforge" / "verification.json"
            if not verification_file.is_file():
                return False, "Pre-flight verification failed: Complete verification report is missing."
            from app.execution.verification import source_digest
            verification = json.loads(verification_file.read_text(encoding="utf-8"))
            if verification.get("status") != "VERIFIED" or verification.get("source_digest") != source_digest(root):
                return False, "Pre-flight verification failed: Source changed or required checks did not pass."
            results_file = root / ".projectforge" / "test_results.json"
            if not results_file.is_file():
                return False, "Pre-flight verification failed: No test results found in .projectforge/."

            try:
                data = json.loads(results_file.read_text(encoding="utf-8"))
                if data.get("exit_code") != 0 or data.get("failed_count", 0) > 0:
                    return (
                        False,
                        f"Pre-flight verification failed: Test suite reported {data.get('failed_count')} failures. Resolve before launching editor.",
                    )
            except Exception as e:
                return False, f"Failed to parse test results: {e}"

        # 4. Check for VS Code binary on system PATH or Windows standard path
        code_bin = shutil.which("code") or shutil.which("code.cmd")
        if not code_bin:
            import os
            local_app = os.environ.get("LOCALAPPDATA", "")
            if local_app:
                candidate = Path(local_app) / "Programs" / "Microsoft VS Code" / "bin" / "code.cmd"
                if candidate.is_file():
                    code_bin = str(candidate)

        if not code_bin:
            return (
                False,
                "VS Code CLI ('code') not found on system PATH. Please ensure VS Code is installed with shell command enabled.",
            )

        # 5. Launch VS Code
        try:
            subprocess.Popen([code_bin, str(root)], shell=True, cwd=str(root))
            return True, f"Visual Studio Code launched successfully for {root.name}"
        except Exception as e:
            return False, f"Failed to launch VS Code process: {e}"
