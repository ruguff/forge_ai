"""
ProjectForge AI — Failure Classifier.

Classifies compilation, runtime, and test execution errors into 12 distinct
failure taxonomy categories to guide targeted automated repair strategies.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Optional
from pydantic import BaseModel


class FailureCategory(str, Enum):
    """Canonical 12-category diagnostic taxonomy."""
    BUILD_ERROR = "BUILD_ERROR"
    DEPENDENCY_ERROR = "DEPENDENCY_ERROR"
    TYPE_ERROR = "TYPE_ERROR"
    SYNTAX_ERROR = "SYNTAX_ERROR"
    RUNTIME_ERROR = "RUNTIME_ERROR"
    API_ERROR = "API_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    TEST_FAILURE = "TEST_FAILURE"
    FRONTEND_ERROR = "FRONTEND_ERROR"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    ENVIRONMENT_ERROR = "ENVIRONMENT_ERROR"
    UNKNOWN = "UNKNOWN"


class DiagnosticReport(BaseModel):
    """Structured failure diagnosis output."""
    category: FailureCategory
    root_cause_summary: str
    confidence: float
    affected_file: Optional[str] = None
    affected_line: Optional[int] = None
    suggested_repair_strategy: str


class FailureClassifier:
    """Rule-based and heuristic failure classifier."""

    @classmethod
    def classify(cls, error_text: str, test_name: Optional[str] = None) -> DiagnosticReport:
        """Analyze traceback and error text to determine exact failure category."""
        text = error_text.lower()

        # 1. Syntax Error
        if "syntaxerror" in text or "invalid syntax" in text:
            return DiagnosticReport(
                category=FailureCategory.SYNTAX_ERROR,
                root_cause_summary="Python syntax error or malformed code structure.",
                confidence=0.98,
                suggested_repair_strategy="Fix syntax token, unclosed parenthesis, or indentation.",
            )

        # 2. Dependency Error
        if "modulenotfounderror" in text or "no module named" in text or "cannot find module" in text:
            mod_match = re.search(r"no module named ['\"](.*?)['\"]", text)
            mod_name = mod_match.group(1) if mod_match else "unknown"
            return DiagnosticReport(
                category=FailureCategory.DEPENDENCY_ERROR,
                root_cause_summary=f"Missing module or library: '{mod_name}'",
                confidence=0.95,
                suggested_repair_strategy=f"Add '{mod_name}' to requirements.txt or install it.",
            )

        # 3. Type Error
        if "typeerror" in text or "type error" in text or "ts2322" in text or "ts2345" in text:
            return DiagnosticReport(
                category=FailureCategory.TYPE_ERROR,
                root_cause_summary="Type mismatch or invalid argument type passed to function.",
                confidence=0.92,
                suggested_repair_strategy="Align parameter types or schema field definitions.",
            )

        # 4. Database Error
        if "sqlite3.operationalerror" in text or "sqlalchemy.exc" in text or "database" in text and "error" in text:
            return DiagnosticReport(
                category=FailureCategory.DATABASE_ERROR,
                root_cause_summary="Database schema, constraint, or connection failure.",
                confidence=0.90,
                suggested_repair_strategy="Verify table creation, column names, and migration states.",
            )

        # 5. API Error / HTTP Status code mismatch
        if "assert response.status_code ==" in text or "404" in text or "500 internal server error" in text:
            return DiagnosticReport(
                category=FailureCategory.API_ERROR,
                root_cause_summary="HTTP API route returned unexpected status code or payload.",
                confidence=0.94,
                suggested_repair_strategy="Verify route path, request schema, and response serialization in main.py.",
            )

        # 6. Test Assertion Failure
        if "assertionerror" in text or "assert" in text:
            return DiagnosticReport(
                category=FailureCategory.TEST_FAILURE,
                root_cause_summary="Test assertion failed against actual returned application output.",
                confidence=0.95,
                suggested_repair_strategy="Inspect endpoint logic or update test expectation if contract evolved.",
            )

        # 7. Frontend Build Error
        if "vite build" in text or "rollup" in text or "tsconfig" in text:
            return DiagnosticReport(
                category=FailureCategory.FRONTEND_ERROR,
                root_cause_summary="Frontend bundling or TypeScript compilation failure.",
                confidence=0.90,
                suggested_repair_strategy="Fix frontend import paths and TS configuration.",
            )

        return DiagnosticReport(
            category=FailureCategory.UNKNOWN,
            root_cause_summary="Unclassified execution error.",
            confidence=0.60,
            suggested_repair_strategy="Examine full traceback and application logs.",
        )
