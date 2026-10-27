"""
ProjectForge AI — Engineering Agent.

System Persona: Principal Software & Distributed Systems Architect.

Produces an ``EngineeringSpecification`` with strict rules:
  - Every TechDecision must document ≥2 rejected alternatives.
  - Must output a syntactically valid Mermaid architecture diagram.
  - Must identify concrete scalability bottlenecks.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List

from app.harness.base_harness import AgentExecutionHarness, HarnessResult, LintRule
from app.harness.context_filter import ContextFilter
from app.models.schemas import EngineeringSpecification


ENGINEERING_SYSTEM_PROMPT = """\
You are the Principal Software & Distributed Systems Architect for
ProjectForge AI.

Given the product specification, AI architecture spec, and relevant
intake answers, produce a complete EngineeringSpecification.

STRICT RULES — violations will cause rejection and re-prompting:
1. Every TechDecision (frontend, backend, database, cache, API protocol,
   async processing, storage) MUST document at least 2 rejected
   alternatives with clear technical justifications in
   alternatives_rejected.
2. mermaid_diagram MUST be a syntactically valid Mermaid diagram string
   representing component topology and data flows.  It must start with
   a valid Mermaid directive (graph, flowchart, sequenceDiagram, etc.).
3. scalability_limits_and_bottlenecks MUST identify at least 2 concrete
   bottlenecks (e.g., "single-node PostgreSQL write limit at ~10k TPS",
   "WebSocket connection limit per instance: ~65k").
4. observability_stack MUST specify at minimum: logging, metrics, and
   tracing tools.

NEGATIVE CONSTRAINTS:
- Do NOT use vague bottleneck descriptions like "may have scaling issues".
- Do NOT propose a technology without a specific version number.
- Do NOT produce an empty or placeholder Mermaid diagram.

Return ONLY valid JSON matching the schema.
"""


def _lint_mermaid_diagram(model: EngineeringSpecification) -> List[str]:
    """Mermaid diagram must start with a valid directive."""
    violations = []
    diagram = model.mermaid_diagram.strip()
    valid_starts = (
        "graph", "flowchart", "sequenceDiagram", "classDiagram",
        "stateDiagram", "erDiagram", "gantt", "pie", "gitgraph",
        "C4Context", "C4Container", "C4Component", "C4Deployment",
    )
    if not diagram or not any(diagram.startswith(s) for s in valid_starts):
        violations.append(
            f"mermaid_diagram must start with a valid Mermaid directive "
            f"(e.g., 'graph TD', 'flowchart LR').  Got: "
            f"'{diagram[:50]}...'"
        )
    return violations


def _lint_scalability_bottlenecks(
    model: EngineeringSpecification,
) -> List[str]:
    """Must identify at least 2 concrete scalability bottlenecks."""
    violations = []
    if len(model.scalability_limits_and_bottlenecks) < 2:
        violations.append(
            f"scalability_limits_and_bottlenecks must contain at least 2 "
            f"entries; got {len(model.scalability_limits_and_bottlenecks)}."
        )
    return violations


def _lint_observability_keys(
    model: EngineeringSpecification,
) -> List[str]:
    """observability_stack must have logging, metrics, and tracing."""
    required = {"logging", "metrics", "tracing"}
    present = set(model.observability_stack.keys())
    missing = required - present
    if missing:
        return [
            f"observability_stack is missing required keys: "
            f"{sorted(missing)}."
        ]
    return []


class EngineeringAgent:
    """Engineering architecture agent.

    Parameters
    ----------
    llm_client:
        Callable that sends a prompt string to the LLM and returns the
        raw response text.
    """

    def __init__(self, llm_client: Callable[..., Any]) -> None:
        self._harness = AgentExecutionHarness(
            target_schema=EngineeringSpecification,
            agent_name="EngineeringAgent",
            system_prompt=ENGINEERING_SYSTEM_PROMPT,
            llm_client=llm_client,
            extra_lint_rules=[
                _lint_mermaid_diagram,
                _lint_scalability_bottlenecks,
                _lint_observability_keys,
            ],
        )

    async def analyze(
        self,
        project_state: Dict[str, Any],
    ) -> HarnessResult:
        """Produce an ``EngineeringSpecification`` from the project state.

        Parameters
        ----------
        project_state:
            Full ``ProjectState.model_dump()`` dict.

        Returns
        -------
        HarnessResult
            On success, ``result.output`` is an
            ``EngineeringSpecification``.
        """
        context = ContextFilter.for_engineering(project_state)
        return await self._harness.execute(context_data=context)
