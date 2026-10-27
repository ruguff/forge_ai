"""
ProjectForge AI — Intake Agent.

Manages the 10-question adaptive intake flow.  Given an initial idea and
any partial answers already collected, the agent generates tailored
follow-up clarification questions to fill information gaps.

Questions cover:
    Q1.  Core Problem & Affected Persona
    Q2.  Target Users & Operating Environment
    Q3.  Desired Solution Flow (step-by-step user interaction)
    Q4.  Core Functionality (2–3 must-have features)
    Q5.  Expected Input Data (formats, volumes, sources)
    Q6.  Expected Output Data (artifacts, reports, UI updates)
    Q7.  Intelligence / Logic (deterministic rules vs ML/NLP/CV)
    Q8.  Technology / Infrastructure Constraints
    Q9.  Scale & Availability SLA
    Q10. Objective Success Criteria (quantifiable 3-month metrics)
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List

from app.harness.base_harness import AgentExecutionHarness, HarnessResult, LintRule
from app.models.schemas import IntakeClarifications, Question


INTAKE_SYSTEM_PROMPT = """\
You are the Intake Orchestrator for ProjectForge AI.

Your sole responsibility is to generate adaptive clarification questions
that fill gaps in the user's project idea.  You have a master list of 10
question domains:

  Q1.  Core Problem & Affected Persona
  Q2.  Target Users & Operating Environment
  Q3.  Desired Solution Flow (step-by-step user interaction)
  Q4.  Core Functionality (2–3 must-have features)
  Q5.  Expected Input Data (formats, volumes, sources)
  Q6.  Expected Output Data (artifacts, reports, UI updates)
  Q7.  Intelligence / Logic (deterministic rules vs probabilistic ML/NLP/CV)
  Q8.  Technology / Infrastructure Constraints (hardware, hosting, legacy)
  Q9.  Scale & Availability SLA (concurrent users, downtime tolerance)
  Q10. Objective Success Criteria (quantifiable 3-month metrics)

RULES:
- Only ask questions for domains NOT yet answered in partial_answers.
- Each question must have a clear question_id (e.g. "Q1", "Q7").
- Adapt the question wording to the specific project idea provided.
- expected_answer_type must be one of: free_text, single_choice, multi_choice, numeric.
- why_asked must explain what downstream agent needs this information.
- Do NOT generate generic boilerplate questions; tailor everything to the idea.
- Do NOT ask more than 10 questions total.
- Return ONLY valid JSON matching the schema.
"""


def _lint_question_ids(model: IntakeClarifications) -> List[str]:
    """Validate that all question_ids are in the Q1–Q10 range."""
    valid_ids = {f"Q{i}" for i in range(1, 11)}
    violations = []
    for q in model.questions:
        if q.question_id not in valid_ids:
            violations.append(
                f"Invalid question_id '{q.question_id}'; "
                f"must be one of Q1–Q10."
            )
    return violations


def _lint_no_duplicate_questions(model: IntakeClarifications) -> List[str]:
    """No duplicate question_ids in a single batch."""
    seen = set()
    violations = []
    for q in model.questions:
        if q.question_id in seen:
            violations.append(
                f"Duplicate question_id '{q.question_id}'."
            )
        seen.add(q.question_id)
    return violations


class IntakeAgent:
    """Adaptive intake question generator.

    Parameters
    ----------
    llm_client:
        Callable that sends a prompt string to the LLM and returns the
        raw response text.
    """

    def __init__(self, llm_client: Callable[..., Any]) -> None:
        self._harness = AgentExecutionHarness(
            target_schema=IntakeClarifications,
            agent_name="IntakeAgent",
            system_prompt=INTAKE_SYSTEM_PROMPT,
            llm_client=llm_client,
            extra_lint_rules=[
                _lint_question_ids,
                _lint_no_duplicate_questions,
            ],
        )

    async def generate_adaptive_clarifications(
        self,
        idea: str,
        partial_answers: Dict[str, str],
    ) -> HarnessResult:
        """Generate tailored follow-up questions for unanswered domains.

        Parameters
        ----------
        idea:
            The raw project idea string.
        partial_answers:
            Dict mapping question_ids (e.g. ``"Q1"``) to user answers
            already collected.

        Returns
        -------
        HarnessResult
            On success, ``result.output`` is an ``IntakeClarifications``
            model containing the list of ``Question`` objects.
        """
        context = {
            "raw_idea": idea,
            "answered_questions": partial_answers,
            "unanswered_domains": [
                f"Q{i}" for i in range(1, 11)
                if f"Q{i}" not in partial_answers
            ],
        }
        return await self._harness.execute(context_data=context)
