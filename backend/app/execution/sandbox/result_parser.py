"""
ProjectForge AI — Test Result Parser.

Parses test runner output (pytest, npm test) and extracts structured metrics:
passed/failed counts, assertion errors, stack traces, and failure locations.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TestFailureDetail(BaseModel):
    """Detailed diagnostic information for a single test failure."""
    test_name: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    error_type: str = "AssertionError"
    message: str
    traceback: str


class TestRunResult(BaseModel):
    """Aggregated test suite execution results."""
    __test__ = False
    command: str
    exit_code: int
    passed_count: int = 0
    failed_count: int = 0
    error_count: int = 0
    total_count: int = 0
    duration_ms: float = 0.0
    failures: List[TestFailureDetail] = Field(default_factory=list)
    raw_stdout: str = ""
    raw_stderr: str = ""

    @property
    def is_success(self) -> bool:
        return self.exit_code == 0 and self.passed_count > 0 and self.failed_count == 0 and self.error_count == 0


class ResultParser:
    """Parses raw CLI output from test runners into structured TestRunResult."""

    @classmethod
    def parse_pytest(cls, stdout: str, stderr: str, exit_code: int, duration_ms: float = 0.0) -> TestRunResult:
        """Parse pytest terminal stdout/stderr."""
        passed = 0
        failed = 0
        errors = 0

        # Pattern: "X passed, Y failed, Z errors"
        passed_match = re.search(r"(\d+)\s+passed", stdout)
        if passed_match:
            passed = int(passed_match.group(1))

        failed_match = re.search(r"(\d+)\s+failed", stdout)
        if failed_match:
            failed = int(failed_match.group(1))

        error_match = re.search(r"(\d+)\s+error", stdout)
        if error_match:
            errors = int(error_match.group(1))

        failures: List[TestFailureDetail] = []
        if failed > 0 or errors > 0 or exit_code != 0:
            failures = cls._extract_pytest_failures(stdout, stderr)

        total = passed + failed + errors
        return TestRunResult(
            command="pytest",
            exit_code=exit_code,
            passed_count=passed,
            failed_count=failed,
            error_count=errors,
            total_count=total,
            duration_ms=duration_ms,
            failures=failures,
            raw_stdout=stdout,
            raw_stderr=stderr,
        )

    @classmethod
    def _extract_pytest_failures(cls, stdout: str, stderr: str) -> List[TestFailureDetail]:
        """Extract failure blocks from pytest output."""
        failures: List[TestFailureDetail] = []
        # Look for "FAILURES" block: "___ test_name ___"
        blocks = re.split(r"_{3,}\s+(.*?)\s+_{3,}", stdout)
        if len(blocks) > 1:
            for i in range(1, len(blocks), 2):
                test_name = blocks[i].strip()
                trace_content = blocks[i + 1] if i + 1 < len(blocks) else ""

                # Extract line number if present e.g. "test_api.py:24: AssertionError"
                file_path = None
                line_no = None
                loc_match = re.search(r"(\S+\.py):(\d+):", trace_content)
                if loc_match:
                    file_path = loc_match.group(1)
                    line_no = int(loc_match.group(2))

                # Extract last error line
                err_lines = [l.strip() for l in trace_content.strip().splitlines() if "Error" in l or "assert" in l]
                msg = err_lines[-1] if err_lines else "Test assertion failed."

                failures.append(
                    TestFailureDetail(
                        test_name=test_name,
                        file_path=file_path,
                        line_number=line_no,
                        error_type="AssertionError" if "assert" in msg.lower() else "RuntimeError",
                        message=msg,
                        traceback=trace_content.strip()[:1000],
                    )
                )

        if not failures and (stderr or "ERROR" in stdout):
            failures.append(
                TestFailureDetail(
                    test_name="SuiteExecutionError",
                    message=(stderr or stdout).strip()[:300],
                    traceback=(stderr or stdout).strip()[:1000],
                )
            )

        return failures
