"""
ProjectForge AI — QA Agent.

System Persona: Principal Quality Assurance & Test Systems Architect.

Produces a ``QASpecification`` with strict rules:
  - Test pyramid ratios (Unit, Integration, E2E).
  - Critical test cases with exact expected outcomes linked to
    requirement IDs.
  - Stress/load thresholds and AI model evaluation protocols.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List

from app.harness.base_harness import AgentExecutionHarness, HarnessResult, LintRule
from app.harness.context_filter import ContextFilter
from app.models.schemas import QASpecification


QA_SYSTEM_PROMPT = """\
You are the Principal Quality Assurance & Test Systems Architect for
ProjectForge AI.

Given the product, engineering, security, and AI specifications, produce
a complete QASpecification.

STRICT RULES — violations will cause rejection and re-prompting:
1. test_pyramid_distribution MUST include at minimum the keys: "unit",
   "integration", and "e2e" with percentage values that represent a
   valid distribution.
2. critical_test_cases MUST contain at least 3 test cases.
3. Each test case MUST have:
   - A unique test_id (e.g., "TC-001").
   - A traceable_requirement_id linking to a specific requirement.
   - A concrete expected_outcome (not "it should work").
4. frameworks_and_tooling MUST include at least 1 TechDecision. EVERY entry
   must have at least 2 distinct alternatives_rejected keys, each with a
   short reason. This applies separately to pytest, Playwright and any
   other selected tool, not just one entry or two alternatives across the list.
   Rejected alternatives are analysis only; do not add them as dependencies.
5. performance_load_thresholds MUST include at minimum: "p99_latency"
   and "rps" (requests per second).
6. If the AI spec indicates ai_required=true, ai_model_validation_protocol
   MUST be populated with evaluation methodology.

NEGATIVE CONSTRAINTS:
- Do NOT use vague expected outcomes like "verify it works correctly".
- Do NOT omit the traceability link between tests and requirements.
- Do NOT produce test_ids with duplicates.

Return ONLY valid JSON matching the schema.
"""


def _lint_test_pyramid_keys(model: QASpecification) -> List[str]:
    """Test pyramid must have unit, integration, and e2e keys."""
    required = {"unit", "integration", "e2e"}
    present = {k.lower() for k in model.test_pyramid_distribution.keys()}
    missing = required - present
    if missing:
        return [
            f"test_pyramid_distribution missing required keys: "
            f"{sorted(missing)}."
        ]
    return []


def _lint_minimum_test_cases(model: QASpecification) -> List[str]:
    """Must have at least 3 critical test cases."""
    if len(model.critical_test_cases) < 3:
        return [
            f"critical_test_cases must contain at least 3 entries; "
            f"got {len(model.critical_test_cases)}."
        ]
    return []


def _lint_unique_test_ids(model: QASpecification) -> List[str]:
    """All test_ids must be unique."""
    seen = set()
    violations = []
    for tc in model.critical_test_cases:
        if tc.test_id in seen:
            violations.append(f"Duplicate test_id '{tc.test_id}'.")
        seen.add(tc.test_id)
    return violations


def _lint_performance_thresholds(model: QASpecification) -> List[str]:
    """Must include p99_latency and rps thresholds."""
    required = {"p99_latency", "rps"}
    present = {k.lower() for k in model.performance_load_thresholds.keys()}
    missing = required - present
    if missing:
        return [
            f"performance_load_thresholds missing required keys: "
            f"{sorted(missing)}."
        ]
    return []


class QAAgent:
    """QA specification and test planning agent.

    Parameters
    ----------
    llm_client:
        Callable that sends a prompt string to the LLM and returns the
        raw response text.
    """

    def __init__(self, llm_client: Callable[..., Any]) -> None:
        self._harness = AgentExecutionHarness(
            target_schema=QASpecification,
            agent_name="QAAgent",
            system_prompt=QA_SYSTEM_PROMPT,
            llm_client=llm_client,
            extra_lint_rules=[
                _lint_test_pyramid_keys,
                _lint_minimum_test_cases,
                _lint_unique_test_ids,
                _lint_performance_thresholds,
            ],
        )

    async def analyze(
        self,
        project_state: Dict[str, Any],
    ) -> HarnessResult:
        """Produce a ``QASpecification`` from the project state.

        Parameters
        ----------
        project_state:
            Full ``ProjectState.model_dump()`` dict.

        Returns
        -------
        HarnessResult
            On success, ``result.output`` is a ``QASpecification``.
        """
        context = ContextFilter.for_qa(project_state)
        from app.agents.model_client import LocalModelClient
        if isinstance(getattr(self._harness.llm_client, '__self__', None), LocalModelClient):
            from app.harness.sections import execute_sections
            self._harness.system_prompt += ('\nFor this local runtime, frameworks_and_tooling means TESTING tools only '
                '(such as pytest and Playwright), not React, databases, observability or application security controls. '
                'Select at most three testing tools. Keep each justification to one short sentence. '
                'Use only requirement IDs present in project_context; do not invent facts or measured performance.')
            return await execute_sections(self._harness, context, [
                ['test_pyramid_distribution', 'frameworks_and_tooling'],
                ['critical_test_cases', 'performance_load_thresholds', 'ai_model_validation_protocol'],
            ])
        return await self._harness.execute(context_data=context)
