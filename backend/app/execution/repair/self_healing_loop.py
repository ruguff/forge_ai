"""
ProjectForge AI — Bounded Self-Healing Loop.

Automates the diagnosis, patching, and verification cycle:
WRITE → TEST → FAILURE → DIAGNOSE → PATCH → RETEST.
Guarantees strict boundedness (MAX_REPAIR_ATTEMPTS = 3) to prevent infinite loops.
Creates Git checkpoints before repairs and provides rollback on failure.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from app.execution.repair.debugger_agent import DebuggerAgent, RepairPlan
from app.execution.repository.repository_manager import RepositoryManager
from app.execution.sandbox.result_parser import TestRunResult
from app.execution.sandbox.test_runner import TestRunner

logger = logging.getLogger(__name__)


class RepairAttemptRecord(BaseModel):
    """Audit record for a single automated repair attempt."""
    attempt_number: int
    diagnosis_category: str
    patches_applied: List[str] = Field(default_factory=list)
    test_passed_after: bool
    checkpoint_created: str


class SelfHealingReport(BaseModel):
    """Final outcome of the self-healing loop."""
    project_id: str
    total_attempts: int
    success: bool
    status: str = Field(..., description="VERIFIED, REQUIRES_HUMAN, BLOCKED")
    attempts_history: List[RepairAttemptRecord] = Field(default_factory=list)
    final_test_result: Optional[TestRunResult] = None


class SelfHealingLoop:
    """Bounded automated self-healing controller."""

    MAX_REPAIR_ATTEMPTS = 3

    def __init__(self, repo_manager: RepositoryManager, test_runner: TestRunner, model_client=None) -> None:
        self.repo = repo_manager
        self.runner = test_runner
        self.debugger = DebuggerAgent(model_client=model_client)
        self.allowed_repair_files = None
        self.repair_history_file = self.repo.workspace_root / ".projectforge" / "repair_history.json"

    def execute_loop(
        self,
        project_id: str,
        initial_test_result: TestRunResult,
        on_attempt_callback: Optional[callable] = None,
    ) -> SelfHealingReport:
        """
        Execute bounded repair loop over failing tests.
        """
        history: List[RepairAttemptRecord] = []
        current_test_res = initial_test_result

        if current_test_res.is_success:
            return SelfHealingReport(
                project_id=project_id,
                total_attempts=0,
                success=True,
                status="VERIFIED",
                final_test_result=current_test_res,
            )

        for attempt in range(1, self.MAX_REPAIR_ATTEMPTS + 1):
            logger.info("Self-healing attempt %d/%d for project %s", attempt, self.MAX_REPAIR_ATTEMPTS, project_id)

            # 1. Take pre-repair Git checkpoint
            chk_name = f"pre_repair_attempt_{attempt}"
            self.repo.create_checkpoint(chk_name, f"Pre-repair checkpoint attempt {attempt}")

            # 2. Diagnose failure
            sources = lambda: {p: self.repo.read_file(p) for p in self.repo.list_files()
                               if self._repair_allowed(p)}
            plan = self.debugger.diagnose_test_run(current_test_res, file_getter=sources)
            if not plan or plan.requires_human or not plan.patches:
                logger.warning("No automated patch could be formulated. Escalating to REQUIRES_HUMAN.")
                self._record_history(history)
                return SelfHealingReport(
                    project_id=project_id,
                    total_attempts=attempt,
                    success=False,
                    status="REQUIRES_HUMAN",
                    attempts_history=history,
                    final_test_result=current_test_res,
                )

            # 3. Apply patches through RepositoryManager
            applied_summaries: List[str] = []
            originals = {}
            for patch in plan.patches:
                try:
                    if not self._repair_allowed(patch.target_file) or not patch.old_content:
                        raise ValueError("Repair cannot modify tests, contracts, or unauthorized files.")
                    originals.setdefault(patch.target_file, self.repo.read_file(patch.target_file))
                    self.repo.modify_task_file(
                        task_id=f"REPAIR-{attempt}",
                        relative_path=patch.target_file,
                        old_content=patch.old_content,
                        new_content=patch.new_content,
                        allowed_files=list(originals),
                    )
                    applied_summaries.append(f"{patch.target_file}: {patch.rationale}")
                except Exception as e:
                    logger.error("Failed to apply patch on %s: %s", patch.target_file, e)

            # 4. Retest
            current_test_res = self.runner.run_backend_tests()
            if not current_test_res.is_success:
                # Failed attempts leave the source at the pre-repair state.
                for path, source in originals.items():
                    self.repo.write_task_file(f"ROLLBACK-{attempt}", path, source, allowed_files=list(originals))
                current_test_res = self.runner.run_backend_tests()

            attempt_rec = RepairAttemptRecord(
                attempt_number=attempt,
                diagnosis_category=plan.diagnosis.category.value,
                patches_applied=applied_summaries,
                test_passed_after=current_test_res.is_success,
                checkpoint_created=chk_name,
            )
            history.append(attempt_rec)

            if on_attempt_callback:
                on_attempt_callback(attempt_rec)

            # 5. Check if healed
            if current_test_res.is_success:
                logger.info("Project healed successfully on attempt %d!", attempt)
                self.repo.create_checkpoint("repair_successful", f"Self-healing succeeded on attempt {attempt}")
                self._record_history(history)
                return SelfHealingReport(
                    project_id=project_id,
                    total_attempts=attempt,
                    success=True,
                    status="VERIFIED",
                    attempts_history=history,
                    final_test_result=current_test_res,
                )

        # Reached MAX_REPAIR_ATTEMPTS without passing
        logger.warning("Max repair attempts reached (%d). Project requires human assistance.", self.MAX_REPAIR_ATTEMPTS)
        self._record_history(history)
        return SelfHealingReport(
            project_id=project_id,
            total_attempts=self.MAX_REPAIR_ATTEMPTS,
            success=False,
            status="REQUIRES_HUMAN",
            attempts_history=history,
            final_test_result=current_test_res,
        )

    def _record_history(self, history: List[RepairAttemptRecord]) -> None:
        """Write .projectforge/repair_history.json."""
        self.repair_history_file.parent.mkdir(parents=True, exist_ok=True)
        data = [r.model_dump() for r in history]
        self.repair_history_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _repair_allowed(self, path):
        from pathlib import PurePosixPath
        parsed = PurePosixPath(path)
        return (not parsed.is_absolute() and ".." not in parsed.parts and "\\" not in path
                and parsed.parts and parsed.parts[0] in ("backend", "frontend")
                and not any(p.startswith(".") or p == "tests" or p.startswith("test_") for p in parsed.parts)
                and parsed.suffix in (".py", ".tsx", ".ts", ".css")
                and (self.allowed_repair_files is None or path in self.allowed_repair_files))
