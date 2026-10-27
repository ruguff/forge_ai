"""
ProjectForge AI — Debugger Agent.

Diagnoses test failures and error tracebacks to formulate concrete,
targeted file patches before handing off to the self-healing engine.
"""

from __future__ import annotations

import logging
import json
import re
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from app.execution.repair.failure_classifier import DiagnosticReport, FailureCategory, FailureClassifier
from app.execution.sandbox.result_parser import TestFailureDetail, TestRunResult

logger = logging.getLogger(__name__)


class RepairPatch(BaseModel):
    """Specific code replacement patch."""
    target_file: str
    old_content: str
    new_content: str
    rationale: str


class RepairPlan(BaseModel):
    """Diagnostic plan formulated by the Debugger Agent."""
    diagnosis: DiagnosticReport
    patches: List[RepairPatch] = Field(default_factory=list)
    confidence: float = 0.90
    requires_human: bool = False


class DebuggerAgent:
    """Specialized autonomous debugging and diagnostic agent."""

    def __init__(self, model_client=None):
        self.model_client = model_client

    def diagnose_test_run(
        self,
        test_result: TestRunResult,
        file_getter: Optional[callable] = None,
    ) -> Optional[RepairPlan]:
        """
        Analyze failed test run and formulate a concrete RepairPlan.
        Returns None if all tests passed.
        """
        if test_result.is_success or not test_result.failures:
            return None

        failure = test_result.failures[0]
        diagnosis = FailureClassifier.classify(
            error_text=f"{failure.message}\n{failure.traceback}",
            test_name=failure.test_name,
        )

        patches: List[RepairPatch] = []
        if self.model_client and file_getter:
            prompt = """Diagnose the failed application test and propose minimal source repairs.
Do not modify tests, acceptance contracts, requirements or verification logic.
Use only supplied source files. Return JSON with patches: [{target_file, old_content,
new_content, rationale}]. old_content must be an exact nonempty match from source.
If uncertain return patches: [].""" + json.dumps({
                "failure": failure.model_dump(mode="json"), "sources": file_getter()})
            output = json.loads(self.model_client.generate_sync(prompt))
            patches = [RepairPatch.model_validate(p) for p in output.get("patches", [])]
            return RepairPlan(diagnosis=diagnosis, patches=patches,
                              confidence=0.0, requires_human=not patches)

        # Example: Status code mismatch or endpoint logic fix
        if diagnosis.category in (FailureCategory.API_ERROR, FailureCategory.TEST_FAILURE):
            # Check if assertion was checking status code
            if "status_code ==" in failure.traceback or "assert" in failure.message:
                status_match = re.search(r"assert\s+(\d+)\s*==\s*(\d+)", failure.traceback)
                if status_match:
                    actual = status_match.group(1)
                    expected = status_match.group(2)
                    patches.append(
                        RepairPatch(
                            target_file="backend/app/main.py",
                            old_content=f"status_code={actual}",
                            new_content=f"status_code={expected}",
                            rationale=f"Align endpoint return status code with test expectation ({expected}).",
                        )
                    )

        # Fallback generic repair plan if specific code pattern couldn't be parsed
        if not patches and failure.file_path:
            diagnosis.affected_file = failure.file_path
            diagnosis.affected_line = failure.line_number

        return RepairPlan(
            diagnosis=diagnosis,
            patches=patches,
            confidence=diagnosis.confidence,
            requires_human=len(patches) == 0 and diagnosis.category == FailureCategory.UNKNOWN,
        )
