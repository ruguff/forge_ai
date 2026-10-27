"""
ProjectForge AI — Product Agent.

System Persona: Principal Technical Product Manager.

Transforms raw project ideas and intake Q&A into a rigorous
``ProductSpecification`` with strict constraints:
  - MVP features capped at 5 modules.
  - Explicit ``non_goals`` (features rejected for Phase 1).
  - Success metrics with quantifiable thresholds (no hand-waving).
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List

from app.harness.base_harness import AgentExecutionHarness, HarnessResult, LintRule
from app.harness.context_filter import ContextFilter
from app.models.schemas import ProductSpecification


PRODUCT_SYSTEM_PROMPT = """\
You are the Principal Technical Product Manager for ProjectForge AI.

Given the project idea and intake answers, produce a complete
ProductSpecification.

STRICT RULES — violations will cause your output to be rejected:
1. MVP features MUST be ≤ 5 modules.  If you list more than 5, your
   output will be rejected and you will be re-prompted.
2. non_goals MUST contain at least 1 item — features explicitly rejected
   for Phase 1.  "We will not do everything" is NOT acceptable; list
   specific features you are deferring.
3. success_metrics MUST contain quantifiable thresholds with numbers.
   BAD:  "improve efficiency"
   GOOD: "reduce manual review time by 40% within 3 months"
4. user_personas MUST include at least one persona dict with keys:
   name, role, pain_point, goal.
5. product_risks MUST identify at least 2 concrete risks.

NEGATIVE CONSTRAINTS — things you must NOT do:
- Do NOT use vague language like "enhance", "leverage", "streamline"
  without concrete measurable outcomes.
- Do NOT include implementation details (tech stack, databases, etc.).
- Do NOT exceed the schema boundaries.

Return ONLY valid JSON matching the schema.
"""


def _lint_success_metrics_quantifiable(
    model: ProductSpecification,
) -> List[str]:
    """Success metrics must contain at least one numeric character."""
    violations = []
    for metric in model.success_metrics:
        values = " ".join(metric.values())
        if not any(c.isdigit() for c in values):
            violations.append(
                f"Success metric {metric} lacks quantifiable threshold "
                f"(must contain at least one number)."
            )
    return violations


class ProductAgent:
    """Product specification agent.

    Parameters
    ----------
    llm_client:
        Callable that sends a prompt string to the LLM and returns the
        raw response text.
    """

    def __init__(self, llm_client: Callable[..., Any]) -> None:
        self._harness = AgentExecutionHarness(
            target_schema=ProductSpecification,
            agent_name="ProductAgent",
            system_prompt=PRODUCT_SYSTEM_PROMPT,
            llm_client=llm_client,
            extra_lint_rules=[_lint_success_metrics_quantifiable],
        )

    async def analyze(
        self,
        project_state: Dict[str, Any],
    ) -> HarnessResult:
        """Produce a ``ProductSpecification`` from the project state.

        Parameters
        ----------
        project_state:
            Full ``ProjectState.model_dump()`` dict.  Context filtering
            is applied automatically.

        Returns
        -------
        HarnessResult
            On success, ``result.output`` is a ``ProductSpecification``.
        """
        context = ContextFilter.for_product(project_state)
        return await self._harness.execute(context_data=context)
