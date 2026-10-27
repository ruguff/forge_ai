"""
ProjectForge AI — Test & Build Runner.

Executes test suites and builds inside the generated project directory.
Persists structured results into `.projectforge/test_results.json`.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Optional

from app.execution.sandbox.executor import SafeCommandExecutor
from app.execution.sandbox.result_parser import ResultParser, TestRunResult

logger = logging.getLogger(__name__)


class TestRunner:
    """Automated test and build runner for generated projects."""

    __test__ = False

    def __init__(self, workspace_root: Path | str) -> None:
        self.workspace_root = Path(workspace_root).resolve()
        self.executor = SafeCommandExecutor(self.workspace_root)
        self.results_file = self.workspace_root / ".projectforge" / "test_results.json"

    def run_backend_tests(self, test_path: str = "backend/tests") -> TestRunResult:
        """
        Run pytest on the backend test suite using the current Python interpreter.
        """
        cmd = f'python -m pytest {test_path} -v --no-header'
        exec_res = self.executor.execute(cmd, timeout_sec=60.0)

        test_result = ResultParser.parse_pytest(
            stdout=exec_res.stdout,
            stderr=exec_res.stderr,
            exit_code=exec_res.exit_code,
            duration_ms=exec_res.duration_ms,
        )

        self._save_results(test_result)
        return test_result

    def run_identity_checks(self):
        """Platform-owned assertions, outside repairable generated tests."""
        from app.execution.sandbox.identity_gate import SOURCE
        target=self.workspace_root/'.projectforge/test_identity_gate.py'
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(SOURCE,encoding='utf-8')
        execution=self.executor.execute('python -m pytest /source/.projectforge/test_identity_gate.py -v --no-header -p no:cacheprovider',timeout_sec=120)
        return ResultParser.parse_pytest(execution.stdout,execution.stderr,execution.exit_code,execution.duration_ms)

    def run_order_checks(self):
        """Platform-owned pricing, idempotency, ownership and stock-reservation gate."""
        from app.execution.sandbox.order_gate import SOURCE
        target=self.workspace_root/'.projectforge/test_order_gate.py'
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(SOURCE,encoding='utf-8')
        execution=self.executor.execute('python -m pytest /source/.projectforge/test_order_gate.py -v --no-header -p no:cacheprovider',timeout_sec=120)
        return ResultParser.parse_pytest(execution.stdout,execution.stderr,execution.exit_code,execution.duration_ms)

    def run_order_browser_checks(self):
        """Platform-owned rendered customer journey through cart and cancellation."""
        from app.execution.sandbox.order_browser import SOURCE
        target=self.workspace_root/'.projectforge/test_order_browser.py'
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(SOURCE,encoding='utf-8')
        capture=' -s' if (target.parent/'capture_order_screenshots').exists() else ''
        execution=self.executor.execute('python -m pytest /source/.projectforge/test_order_browser.py -v'+capture+' --no-header -p no:cacheprovider',timeout_sec=120)
        return ResultParser.parse_pytest(execution.stdout,execution.stderr,execution.exit_code,execution.duration_ms)

    def run_acceptance(self, checks):
        """Platform-controlled cases are generated before coding, outside agent scope."""
        contract = self.workspace_root / ".projectforge" / "acceptance.json"
        contract.parent.mkdir(parents=True, exist_ok=True)
        contract.write_text(json.dumps(checks, indent=2), encoding="utf-8")
        target = self.workspace_root / ".projectforge" / "test_acceptance.py"
        target.write_text('''import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from app.main import app

CASES = json.loads(Path(__file__).with_name("acceptance.json").read_text())

def contains(actual, expected):
    if isinstance(expected, dict):
        return isinstance(actual, dict) and all(k in actual and contains(actual[k], v) for k, v in expected.items())
    if isinstance(expected, list):
        return isinstance(actual, list) and all(any(contains(a, e) for a in actual) for e in expected)
    return actual == expected

def test_requirement_contract():
    assert CASES, "No acceptance cases were provided"
    with TestClient(app,client=('127.0.0.1',50000)) as client:
        for case in CASES:
            response = client.request(case["method"], case["path"], json=case.get("json"))
            assert response.status_code == case["status"], case
            if "body_contains" in case:
                assert contains(response.json(), case["body_contains"]), case
''', encoding="utf-8")
        result = self.executor.execute("python -m pytest /source/.projectforge/test_acceptance.py -v --no-header -p no:cacheprovider")
        return ResultParser.parse_pytest(result.stdout, result.stderr, result.exit_code, result.duration_ms)

    def run_razorpay_checks(self):
        from app.execution.sandbox.razorpay_gate import SOURCE
        return self._payment_gate('razorpay_gate',SOURCE)

    def run_razorpay_browser_checks(self):
        from app.execution.sandbox.razorpay_browser import SOURCE
        return self._payment_gate('razorpay_browser',SOURCE)

    def run_payment_checks(self):
        from app.execution.sandbox.payment_gate import SOURCE
        return self._payment_gate('payment_gate',SOURCE)

    def run_payment_browser_checks(self):
        from app.execution.sandbox.payment_browser import SOURCE
        return self._payment_gate('payment_browser',SOURCE)

    def _payment_gate(self,name,source):
        target=self.workspace_root/'.projectforge'/('test_'+name+'.py')
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(source,encoding='utf-8')
        capture=' -s' if (target.parent/'capture_payment_screenshots').exists() else ''
        result=self.executor.execute('python -m pytest /source/.projectforge/test_'+name+'.py -v'+capture+' --no-header -p no:cacheprovider',timeout_sec=120)
        return ResultParser.parse_pytest(result.stdout,result.stderr,result.exit_code,result.duration_ms)

    def run_frontend_build(self):
        return self.executor.execute("npm --prefix frontend run build", timeout_sec=120)

    def run_browser_checks(self, journeys):
        from app.execution.sandbox.browser_verification import BROWSER_TEST_SOURCE
        root = self.workspace_root / ".projectforge"
        root.mkdir(exist_ok=True)
        (root / "browser.json").write_text(json.dumps(journeys), encoding="utf-8")
        (root / "test_browser.py").write_text(BROWSER_TEST_SOURCE, encoding="utf-8")
        result = self.executor.execute("python -m pytest /source/.projectforge/test_browser.py -v --no-header -p no:cacheprovider", timeout_sec=120)
        return ResultParser.parse_pytest(result.stdout, result.stderr, result.exit_code, result.duration_ms)

    def _save_results(self, result: TestRunResult) -> None:
        """Save results to .projectforge/test_results.json."""
        self.results_file.parent.mkdir(parents=True, exist_ok=True)
        self.results_file.write_text(
            json.dumps(result.model_dump(), indent=2),
            encoding="utf-8",
        )
