"""
ProjectForge AI — UX Agent.

System Persona: Lead Design Systems Architect & Accessibility Specialist.

Produces a ``UXSpecification`` with strict rules:
  - End-to-end user journey mapping.
  - Every view must specify all 4 operational states (Loading, Empty,
    Error, Success).
  - WCAG 2.1 AA compliance rules.
  - Responsive breakpoints (Mobile, Tablet, Desktop).
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List

from app.harness.base_harness import AgentExecutionHarness, HarnessResult, LintRule
from app.harness.context_filter import ContextFilter
from app.models.schemas import UXSpecification


UX_SYSTEM_PROMPT = """\
You are the Lead Design Systems Architect & Accessibility Specialist for
ProjectForge AI.

Given the product specification, relevant intake answers, and frontend
architecture context, produce a complete UXSpecification.

STRICT RULES — violations will cause rejection and re-prompting:
1. primary_user_journey MUST map the complete end-to-end user flow with
   at least 3 steps (e.g., "Sign up" → "Create project" → "View results").
2. Every entry in view_states MUST specify ALL 4 operational states:
   loading_state, empty_state, error_state, and success_state.
   None of these may be empty strings.
3. accessibility_standards MUST include at least 1 WCAG 2.1 AA rule.
4. responsive_breakpoints MUST include at minimum the keys: "mobile",
   "tablet", and "desktop" with specific pixel values.

NEGATIVE CONSTRAINTS:
- Do NOT use generic state descriptions like "show spinner" without
  specifying what content the spinner replaces.
- Do NOT omit any operational state for any view.
- Do NOT forget mobile-first responsive design.

Return ONLY valid JSON matching the schema.
"""


def _lint_view_states_complete(model: UXSpecification) -> List[str]:
    """Every view must have non-empty strings for all 4 states."""
    violations = []
    for vs in model.view_states:
        for state_name in ("loading_state", "empty_state",
                           "error_state", "success_state"):
            value = getattr(vs, state_name, "")
            if not value or not value.strip():
                violations.append(
                    f"View '{vs.view_name}' has empty {state_name}."
                )
    return violations


def _lint_responsive_breakpoints(model: UXSpecification) -> List[str]:
    """Must include mobile, tablet, and desktop breakpoints."""
    required = {"mobile", "tablet", "desktop"}
    present = {k.lower() for k in model.responsive_breakpoints.keys()}
    missing = required - present
    if missing:
        return [
            f"responsive_breakpoints missing required keys: "
            f"{sorted(missing)}."
        ]
    return []


def _lint_user_journey_minimum(model: UXSpecification) -> List[str]:
    """Primary user journey must have at least 3 steps."""
    if len(model.primary_user_journey) < 3:
        return [
            f"primary_user_journey must have at least 3 steps; "
            f"got {len(model.primary_user_journey)}."
        ]
    return []


class UXAgent:
    """UX specification agent.

    Parameters
    ----------
    llm_client:
        Callable that sends a prompt string to the LLM and returns the
        raw response text.
    """

    def __init__(self, llm_client: Callable[..., Any]) -> None:
        self._harness = AgentExecutionHarness(
            target_schema=UXSpecification,
            agent_name="UXAgent",
            system_prompt=UX_SYSTEM_PROMPT,
            llm_client=llm_client,
            extra_lint_rules=[
                _lint_view_states_complete,
                _lint_responsive_breakpoints,
                _lint_user_journey_minimum,
            ],
        )

    async def analyze(
        self,
        project_state: Dict[str, Any],
    ) -> HarnessResult:
        """Produce a ``UXSpecification`` from the project state.

        Parameters
        ----------
        project_state:
            Full ``ProjectState.model_dump()`` dict.

        Returns
        -------
        HarnessResult
            On success, ``result.output`` is a ``UXSpecification``.
        """
        context = ContextFilter.for_ux(project_state)
        return await self._harness.execute(context_data=context)
