"""
ProjectForge AI — Project Understanding Agent.

Replaces the mandatory 10-question intake with a single natural-language
project description understanding engine.

Extracts all 17 dimensions:
  1. project_name
  2. problem
  3. goal
  4. target_users
  5. user_journeys
  6. functional_requirements
  7. non_functional_requirements
  8. constraints
  9. technology_preferences
  10. expected_outputs
  11. non_goals
  12. assumptions
  13. unknowns
  14. ambiguities
  15. risks
  16. evidence
  17. confidence

CRITICAL RULE:
Never represent an inference as a user requirement.
Every extracted item must specify:
  - type: EXPLICIT | INFERRED | ASSUMPTION | UNKNOWN
  - source: USER | AGENT | INFERENCE
  - confidence: 0.0 - 1.0
"""

from __future__ import annotations

import json
from typing import Any, Callable, Dict, List, Optional

from app.harness.base_harness import AgentExecutionHarness, HarnessResult, LintRule
from app.harness.contract import AgentContract
from app.models.schemas import (
    ExtractedRequirementItem,
    ProjectUnderstandingOutput,
    RequirementSource,
    RequirementType,
)


PROJECT_UNDERSTANDING_SYSTEM_PROMPT = """\
You are the Project Understanding Agent for ProjectForge AI, an autonomous software engineering system.

Your mission is to analyze the user's natural-language project idea and extract a structured 17-dimension specification.

DIMENSIONS TO EXTRACT:
1. project_name: A descriptive, professional title for the project.
2. problem: The core problem, friction, or inefficiency being solved.
3. goal: The primary target outcome.
4. target_users: Key user personas or systems that interact with the product.
5. user_journeys: Key sequential interaction flows from the user perspective.
6. functional_requirements: Explicit and inferred capabilities the system must perform.
7. non_functional_requirements: Latency, throughput, scalability, reliability standards.
8. constraints: Technical, budget, operational, or deployment boundaries.
9. technology_preferences: Explicitly requested or inferred frameworks/languages.
10. expected_outputs: Real artifacts, APIs, UI views, data formats produced.
11. non_goals: Explicit boundaries on what the system will NOT do in this phase.
12. assumptions: Inferred technical or domain hypotheses requiring future verification.
13. unknowns: Gaps in the user request that cannot yet be confirmed.
14. ambiguities: Unclear or dual-meaning concepts in the prompt.
15. risks: Security, technical feasibility, operational, or compliance risks.
16. evidence: Specific quotes or grounded reasoning extracted from the user prompt.
17. confidence: Calibrated overall confidence score (0.0 to 1.0).

STRICT RULES ON PROVENANCE AND TYPES:
- Every extracted item must define:
    - id: Unique ID (e.g. "REQ-F-001", "RISK-001", "UNK-001")
    - dimension: The dimension name
    - title: Brief item title
    - description: Clear, actionable description
    - type: "EXPLICIT" (directly stated by user), "INFERRED" (logically deduced), "ASSUMPTION" (unverified technical premise), or "UNKNOWN" (missing information)
    - source: "USER" (directly from prompt), "AGENT" (specialist domain contribution), or "INFERENCE" (logical deduction)
    - confidence: float between 0.0 and 1.0
    - evidence: Grounded quotation or logical justification
- INVARIANT: NEVER represent an inference as an explicit user requirement. If source is "INFERENCE" or "AGENT", type MUST NOT be "EXPLICIT".
- Return ONLY valid JSON adhering strictly to the schema.
"""


def _lint_never_infer_as_explicit(model: ProjectUnderstandingOutput) -> List[str]:
    """Ensure that items sourced from INFERENCE or AGENT are never marked EXPLICIT."""
    violations: List[str] = []
    all_items: List[ExtractedRequirementItem] = [
        model.problem,
        model.goal,
        *model.target_users,
        *model.user_journeys,
        *model.functional_requirements,
        *model.non_functional_requirements,
        *model.constraints,
        *model.technology_preferences,
        *model.expected_outputs,
        *model.non_goals,
        *model.assumptions,
        *model.unknowns,
        *model.ambiguities,
        *model.risks,
    ]

    for item in all_items:
        if item.source in (RequirementSource.INFERENCE, RequirementSource.AGENT) and item.type == RequirementType.EXPLICIT:
            violations.append(
                f"Item '{item.id}' ({item.title}) has source='{item.source.value}' "
                f"but type='{item.type.value}'. An inference/agent deduction must NEVER "
                f"be represented as an EXPLICIT user requirement."
            )
        if not (0.0 <= item.confidence <= 1.0):
            violations.append(
                f"Item '{item.id}' has invalid confidence {item.confidence}; must be in [0.0, 1.0]."
            )
    return violations


def _lint_core_dimensions_present(model: ProjectUnderstandingOutput) -> List[str]:
    """Ensure critical dimensions are meaningfully extracted."""
    violations: List[str] = []
    if not model.project_name or len(model.project_name.strip()) < 3:
        violations.append("project_name is missing or too short.")
    if not model.problem or not model.problem.description.strip():
        violations.append("Core problem description is empty.")
    if not model.goal or not model.goal.description.strip():
        violations.append("Core goal description is empty.")
    if len(model.functional_requirements) < 1:
        violations.append("At least one functional requirement must be extracted.")
    return violations


class ProjectUnderstandingAgent:
    """Agent that ingests a single natural-language idea and extracts 17 dimensions."""

    def __init__(self, llm_client: Callable[..., Any]) -> None:
        self.contract = AgentContract(
            id="project_understanding",
            agent_id="project_understanding",
            name="Orion Vance",
            role="PRINCIPAL INTAKE ARCHITECT",
            objective="Extract 17-dimension structured requirements from natural language input.",
            mission="Transform vague user ideas into structured, typed, and calibrated requirements.",
            inputs=["raw_idea", "user_prompt"],
            input_schema="ProjectContext",
            outputs=["project_understanding_output"],
            output_schema="ProjectUnderstandingOutput",
            tools=["schema_validation", "confidence_calibration", "provenance_linter"],
            constraints=[
                "Never represent an inference as an explicit user requirement",
                "Extract evidence for all explicit requirements",
                "Flag ambiguities and unknowns transparently",
            ],
            confidence=0.92,
        )
        self._harness = AgentExecutionHarness(
            target_schema=ProjectUnderstandingOutput,
            agent_name="ProjectUnderstandingAgent",
            system_prompt=PROJECT_UNDERSTANDING_SYSTEM_PROMPT,
            llm_client=llm_client,
            extra_lint_rules=[
                _lint_never_infer_as_explicit,
                _lint_core_dimensions_present,
            ],
        )

    async def analyze_project_idea(self, raw_idea: str) -> HarnessResult:
        """Execute extraction across all 17 dimensions."""
        context = {
            "user_prompt": raw_idea,
            "instruction": "Extract all 17 dimensions with strict provenance and confidence scoring.",
        }
        return await self._harness.execute(context_data=context)
