"""
ProjectForge AI — AI/ML Agent.

System Persona: Principal AI Research Scientist & ML Systems Engineer.

Evaluates whether AI/ML is genuinely required for the project.  Enforces
the **Zero-AI Default Rule**: if the problem can be solved with regex,
SQL, or deterministic heuristics, ``ai_required`` MUST be ``False``.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List

from app.harness.base_harness import AgentExecutionHarness, HarnessResult, LintRule
from app.harness.context_filter import ContextFilter
from app.models.schemas import AIArchitectureSpecification, ProblemType


AIML_SYSTEM_PROMPT = """\
You are the Principal AI Research Scientist & ML Systems Engineer for
ProjectForge AI.

Evaluate whether the project genuinely requires AI/ML capabilities or
whether deterministic approaches (regex, SQL queries, rule engines,
heuristic scoring) suffice.

ZERO-AI DEFAULT RULE (MANDATORY):
- If the problem CAN be resolved using regex, SQL, or deterministic
  heuristics, you MUST set ai_required=false, problem_type="NONE", and
  leave all downstream ML fields as null/empty.
- You MUST justify WHY AI is or is not needed in necessity_justification.

IF ai_required IS TRUE, you MUST provide:
1. problem_formulation — formal ML problem statement.
2. candidate_models — at least 2 candidate models as TechDecision objects,
   each with ≥2 rejected alternatives.
3. recommended_model — your top pick with full rationale.
4. dataset_requirements — data size, labelling, sourcing.
5. training_vs_api_strategy — fine-tuning vs API-based inference.
6. evaluation_metrics — at least 2 concrete metrics (F1, BLEU, etc.).
7. baseline_heuristic — the non-ML baseline to beat.
8. compute_and_cost_estimation — monthly compute costs.
9. hallucination_and_drift_mitigation — at least 1 mitigation strategy.

NEGATIVE CONSTRAINTS:
- Do NOT recommend AI for simple CRUD, search, or filtering operations.
- Do NOT use vague terms like "leverage AI" without specifying the model
  family, architecture, and training approach.
- Do NOT ignore the baseline heuristic — every AI recommendation must
  demonstrate improvement over a non-ML approach.

Return ONLY valid JSON matching the schema.
"""


def _lint_zero_ai_consistency(
    model: AIArchitectureSpecification,
) -> List[str]:
    """Enforce the Zero-AI Default Rule consistency."""
    violations = []

    if not model.ai_required:
        # When AI is not required, ML-specific fields must be empty/None
        if model.problem_type != ProblemType.NONE:
            violations.append(
                "ai_required=false but problem_type is not 'NONE'."
            )
        if model.candidate_models:
            violations.append(
                "ai_required=false but candidate_models is not empty."
            )
        if model.recommended_model is not None:
            violations.append(
                "ai_required=false but recommended_model is set."
            )
    else:
        # When AI is required, critical fields must be populated
        if not model.problem_formulation:
            violations.append(
                "ai_required=true but problem_formulation is missing."
            )
        if len(model.candidate_models) < 2:
            violations.append(
                "ai_required=true but fewer than 2 candidate_models."
            )
        if model.recommended_model is None:
            violations.append(
                "ai_required=true but recommended_model is None."
            )
        if len(model.evaluation_metrics) < 2:
            violations.append(
                "ai_required=true but fewer than 2 evaluation_metrics."
            )
        if not model.baseline_heuristic:
            violations.append(
                "ai_required=true but baseline_heuristic is missing."
            )

    return violations


class AIMLAgent:
    """AI/ML architecture agent with Zero-AI Default enforcement.

    Parameters
    ----------
    llm_client:
        Callable that sends a prompt string to the LLM and returns the
        raw response text.
    """

    def __init__(self, llm_client: Callable[..., Any]) -> None:
        self._harness = AgentExecutionHarness(
            target_schema=AIArchitectureSpecification,
            agent_name="AIMLAgent",
            system_prompt=AIML_SYSTEM_PROMPT,
            llm_client=llm_client,
            extra_lint_rules=[_lint_zero_ai_consistency],
        )

    async def analyze(
        self,
        project_state: Dict[str, Any],
    ) -> HarnessResult:
        """Produce an ``AIArchitectureSpecification`` from the project state.

        Parameters
        ----------
        project_state:
            Full ``ProjectState.model_dump()`` dict.  Context filtering
            is applied automatically.

        Returns
        -------
        HarnessResult
            On success, ``result.output`` is an
            ``AIArchitectureSpecification``.
        """
        context = ContextFilter.for_aiml(project_state)
        return await self._harness.execute(context_data=context)
