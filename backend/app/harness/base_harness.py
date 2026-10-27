"""
ProjectForge AI — Generic Agent Execution Harness.

``AgentExecutionHarness[T]`` is a generic, schema-parameterised controller
that wraps every AI agent call.  It enforces:

1. **Structured JSON prompt** — the target schema's JSON-Schema is injected
   into the prompt so the LLM returns conformant output.
2. **Pydantic schema validation** — the raw response is parsed against
   ``target_schema``.  On ``ValidationError`` a diagnostic retry prompt
   containing the Pydantic errors is constructed and resubmitted.
3. **Domain-specific lint rules** — deterministic checks run against the
   validated model (e.g. ``TechDecision`` must have ≥ 2 rejected
   alternatives).  Violations trigger a lint-retry prompt.
4. **Empirical confidence calibration** — every ``ConfidenceScore`` in the
   output tree is recalculated with the evidence-grounded formula.
"""

from __future__ import annotations

import inspect
import json
import logging
from dataclasses import dataclass, field
from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    List,
    Optional,
    Type,
    TypeVar,
)

from pydantic import BaseModel, ValidationError

from app.harness.calibration import compute_calibrated_confidence
from app.models.schemas import ConfidenceScore, TechDecision

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

# Type alias for external lint rules: (validated_output) → list of violations
LintRule = Callable[[BaseModel], List[str]]


# ──────────────────────────────────────────────────────────────────────────────
# Harness result
# ──────────────────────────────────────────────────────────────────────────────


@dataclass
class HarnessResult:
    """Outcome of a single agent execution through the harness."""

    success: bool = False
    """Whether a schema-valid, lint-clean output was obtained."""

    output: Optional[BaseModel] = None
    """The validated & calibrated Pydantic model (``None`` on failure)."""

    attempts: int = 0
    """Total number of LLM calls made (initial + retries)."""

    validation_errors: List[str] = field(default_factory=list)
    """Pydantic validation errors from the *last* failed attempt."""

    lint_violations: List[str] = field(default_factory=list)
    """Lint violations from the *last* failed attempt."""

    raw_responses: List[str] = field(default_factory=list)
    """Raw LLM response strings for every attempt (audit trail)."""


# ──────────────────────────────────────────────────────────────────────────────
# Prompt builders
# ──────────────────────────────────────────────────────────────────────────────


def build_initial_prompt(
    system_prompt: str,
    context_json: str,
    json_schema: Dict[str, Any],
) -> str:
    """Build the first prompt sent to the LLM.

    Includes the system prompt, serialised context, and the JSON-Schema
    the response must conform to.
    """
    schema_str = json.dumps(json_schema, indent=2)
    return (
        f"{system_prompt}\n\n"
        f"--- CONTEXT ---\n{context_json}\n--- END CONTEXT ---\n\n"
        f"Respond with a single JSON object that strictly conforms to "
        f"the following JSON Schema:\n```json\n{schema_str}\n```\n"
        f"Return ONLY valid JSON. No markdown fences, no commentary."
    )


def build_diagnostic_retry_prompt(
    original_prompt: str,
    raw_response: str,
    validation_errors: List[str],
) -> str:
    """Build a retry prompt that feeds Pydantic validation errors back
    to the LLM for self-correction."""
    error_block = "\n".join(f"  • {e}" for e in validation_errors)
    return (
        f"{original_prompt}\n\n"
        f"--- VALIDATION FAILED ---\n"
        f"Your previous response could not be parsed.  "
        f"Fix EVERY error listed below and respond with corrected JSON only.\n\n"
        f"Previous response (invalid):\n{raw_response}\n\n"
        f"Validation errors:\n{error_block}\n"
        f"--- END ---"
    )


def build_lint_retry_prompt(
    original_prompt: str,
    raw_response: str,
    lint_violations: List[str],
) -> str:
    """Build a retry prompt that feeds deterministic lint violations back
    to the LLM for self-correction."""
    violation_block = "\n".join(f"  • {v}" for v in lint_violations)
    return (
        f"{original_prompt}\n\n"
        f"--- LINT VIOLATIONS ---\n"
        f"Your response was valid JSON and parsed successfully, but it "
        f"violates the following rules.  Fix ALL violations and return "
        f"corrected JSON only.\n\n"
        f"Previous response:\n{raw_response}\n\n"
        f"Violations:\n{violation_block}\n"
        f"--- END ---"
    )


# ──────────────────────────────────────────────────────────────────────────────
# Built-in domain lint rules
# ──────────────────────────────────────────────────────────────────────────────


def _collect_tech_decisions(obj: Any) -> List[TechDecision]:
    """Recursively collect all ``TechDecision`` instances from a model tree."""
    found: List[TechDecision] = []

    if isinstance(obj, TechDecision):
        found.append(obj)
        return found

    if isinstance(obj, BaseModel):
        for field_name in type(obj).model_fields:
            child = getattr(obj, field_name, None)
            if child is not None:
                found.extend(_collect_tech_decisions(child))
        return found

    if isinstance(obj, list):
        for item in obj:
            found.extend(_collect_tech_decisions(item))
        return found

    if isinstance(obj, dict):
        for value in obj.values():
            found.extend(_collect_tech_decisions(value))

    return found


def lint_tech_decision_alternatives(model: BaseModel) -> List[str]:
    """Every ``TechDecision`` must have at least 2 rejected alternatives."""
    violations: List[str] = []
    decisions = _collect_tech_decisions(model)
    for td in decisions:
        if len(td.alternatives_rejected) < 2:
            violations.append(
                f"TechDecision '{td.category}/{td.selected}' has "
                f"{len(td.alternatives_rejected)} rejected alternative(s); "
                f"minimum is 2."
            )
    return violations


def lint_non_empty_non_goals(model: BaseModel) -> List[str]:
    """``ProductSpecification.non_goals`` must not be empty."""
    # Import here to avoid circular imports at module level
    from app.models.schemas import ProductSpecification

    if isinstance(model, ProductSpecification):
        if not model.non_goals:
            return ["ProductSpecification.non_goals must not be empty."]
    return []


# Registry of built-in lint rules applied to all harness executions
BUILTIN_LINT_RULES: List[LintRule] = [
    lint_tech_decision_alternatives,
    lint_non_empty_non_goals,
]


# ──────────────────────────────────────────────────────────────────────────────
# Confidence calibration walk
# ──────────────────────────────────────────────────────────────────────────────


def calibrate_confidence_in_place(obj: Any) -> None:
    """Recursively walk a Pydantic model tree and recalibrate every
    ``ConfidenceScore`` instance using the empirical formula.

    Mutates models **in place** for efficiency.
    """
    if isinstance(obj, ConfidenceScore):
        calibrated = compute_calibrated_confidence(
            fact_count=len(obj.fact_references),
            unverified_assumptions_count=len(obj.unverified_assumptions),
            risk_penalty=obj.risk_penalty,
        )
        obj.score = calibrated
        return

    if isinstance(obj, BaseModel):
        for field_name in type(obj).model_fields:
            child = getattr(obj, field_name, None)
            if child is not None:
                calibrate_confidence_in_place(child)
        return

    if isinstance(obj, list):
        for item in obj:
            calibrate_confidence_in_place(item)
        return

    if isinstance(obj, dict):
        for value in obj.values():
            calibrate_confidence_in_place(value)


# ──────────────────────────────────────────────────────────────────────────────
# Generic Agent Execution Harness
# ──────────────────────────────────────────────────────────────────────────────


class AgentExecutionHarness(Generic[T]):
    """Schema-parameterised execution harness for a single AI agent.

    Parameters
    ----------
    target_schema:
        The Pydantic model class the LLM must produce.
    agent_name:
        Human-readable agent name for logging and audit trail.
    system_prompt:
        The system-level instruction prompt for the agent.
    llm_client:
        A callable ``(prompt: str) -> str`` that calls the LLM and
        returns the raw response text.  May be sync or async.
    extra_lint_rules:
        Optional additional lint rules beyond the built-in set.
    """

    def __init__(
        self,
        *,
        target_schema: Type[T],
        agent_name: str,
        system_prompt: str,
        llm_client: Callable[..., Any],
        extra_lint_rules: Optional[List[LintRule]] = None,
    ) -> None:
        self.target_schema = target_schema
        self.agent_name = agent_name
        self.system_prompt = system_prompt
        self.llm_client = llm_client
        self.lint_rules: List[LintRule] = list(BUILTIN_LINT_RULES)
        if extra_lint_rules:
            self.lint_rules.extend(extra_lint_rules)

    async def execute(
        self,
        context_data: dict,
        max_retries: int = 2,
    ) -> HarnessResult:
        """Execute the agent through the full harness pipeline.

        Workflow
        --------
        1. Serialise ``context_data`` into structured JSON.
        2. Build prompt with JSON-Schema of ``target_schema``.
        3. Call the LLM.
        4. Parse response against ``target_schema``.
           • On ``ValidationError`` → diagnostic retry.
        5. Run lint rules against validated model.
           • On violations → lint retry.
        6. Calibrate all ``ConfidenceScore`` instances.
        7. Return ``HarnessResult``.

        Parameters
        ----------
        context_data:
            Pre-filtered context dict (use ``ContextFilter`` methods).
        max_retries:
            Maximum retry attempts (not counting initial call).

        Returns
        -------
        HarnessResult
        """
        # Step 1 — Serialise context
        context_json = json.dumps(context_data, indent=2, default=str)

        # Step 2 — Build initial prompt with schema enforcement
        json_schema = self.target_schema.model_json_schema()
        initial_prompt = build_initial_prompt(
            system_prompt=self.system_prompt,
            context_json=context_json,
            json_schema=json_schema,
        )
        current_prompt = initial_prompt

        result = HarnessResult()
        total_attempts = 1 + max_retries

        for attempt in range(total_attempts):
            result.attempts = attempt + 1

            # Step 3 — Call the LLM
            try:
                if inspect.iscoroutinefunction(self.llm_client):
                    raw_response = await self.llm_client(current_prompt)
                else:
                    raw_response = self.llm_client(current_prompt)
            except Exception as exc:
                from app.agents.model_client import ModelBudgetExceeded, ModelOutputTruncatedError
                if isinstance(exc, (ModelBudgetExceeded, ModelOutputTruncatedError)):
                    raise
                logger.error(
                    "[%s] LLM call failed (attempt %d): %s",
                    self.agent_name, attempt + 1, exc,
                )
                result.validation_errors = [f"LLM call exception: {exc}"]
                result.raw_responses.append(f"<LLM_ERROR: {exc}>")
                continue

            if not isinstance(raw_response, str):
                raw_response = str(raw_response)

            result.raw_responses.append(raw_response)

            # Step 4 — Schema validation
            try:
                validated: T = self.target_schema.model_validate_json(
                    raw_response
                )
            except ValidationError as ve:
                error_messages = [
                    f"{'.'.join(str(loc) for loc in e['loc'])}: {e['msg']}"
                    for e in ve.errors()
                ]
                result.validation_errors = error_messages
                result.lint_violations = []
                logger.warning(
                    "[%s] Schema validation failed (attempt %d/%d): %s",
                    self.agent_name, attempt + 1, total_attempts,
                    error_messages,
                )
                current_prompt = build_diagnostic_retry_prompt(
                    original_prompt=initial_prompt,
                    raw_response=raw_response,
                    validation_errors=error_messages,
                )
                continue

            # Step 5 — Deterministic lint rules
            all_violations: List[str] = []
            for rule in self.lint_rules:
                violations = rule(validated)
                all_violations.extend(violations)

            if all_violations:
                result.lint_violations = all_violations
                result.validation_errors = []
                logger.warning(
                    "[%s] Lint violations (attempt %d/%d): %s",
                    self.agent_name, attempt + 1, total_attempts,
                    all_violations,
                )
                current_prompt = build_lint_retry_prompt(
                    original_prompt=initial_prompt,
                    raw_response=raw_response,
                    lint_violations=all_violations,
                )
                continue

            # Step 6 — Calibrate confidence scores
            calibrate_confidence_in_place(validated)

            # Success
            result.success = True
            result.output = validated
            result.validation_errors = []
            result.lint_violations = []
            return result

        # Exhausted all attempts
        result.success = False
        logger.error(
            "[%s] Harness exhausted all %d attempts",
            self.agent_name, total_attempts,
        )
        return result
