"""
ProjectForge AI — Security Agent.

System Persona: Chief Information Security Officer (CISO) & Threat Modeler.

Produces a ``SecurityReport`` with strict rules:
  - STRIDE threat modeling across all system components.
  - Authentication mechanism and authorization model (RBAC, ABAC, etc.).
  - If AI components exist, include prompt injection, model inversion,
    and data poisoning mitigations.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List

from app.harness.base_harness import AgentExecutionHarness, HarnessResult, LintRule
from app.harness.context_filter import ContextFilter
from app.models.schemas import SecurityReport


SECURITY_SYSTEM_PROMPT = """\
You are the Chief Information Security Officer (CISO) & Threat Modeler
for ProjectForge AI.

Given the engineering specification, AI architecture spec, and relevant
intake constraints, produce a comprehensive SecurityReport.

STRICT RULES — violations will cause rejection and re-prompting:
1. Apply STRIDE threat modeling.  threat_catalog MUST contain at least 3
   threats, each with a unique threat_id and a valid stride_category
   from: Spoofing, Tampering, Repudiation, Information Disclosure,
   Denial of Service, Elevation of Privilege.
2. authentication_mechanism MUST be a complete TechDecision with ≥2
   rejected alternatives.
   When the user explicitly requests no login, select "No authentication"
   with category "Authentication". Still explain why two alternatives
   (for example local passwords and OAuth) are excluded by the single-user
   scope. Do not introduce login, roles or accounts to fill this field.
   Use authorization_model="Single-user local access; no application roles"
   for that scope. Do not return an empty decision or "None/None" placeholder.
3. authorization_model MUST specify the model type (RBAC, ABAC, ACL, etc.)
   and not just say "role-based".
4. If the AI spec indicates ai_required=true, ai_threat_mitigations MUST
   include at least 3 mitigations covering: prompt injection, model
   inversion, and data poisoning.
5. input_validation_rules MUST contain at least 2 specific rules.

NEGATIVE CONSTRAINTS:
- Do NOT produce generic threats.  Every threat must be specific to the
  system being designed.
- Do NOT omit likelihood or impact assessments.
- Do NOT use severity levels inconsistently with likelihood.

Return ONLY valid JSON matching the schema.
"""

# STRIDE categories
_STRIDE_CATEGORIES = frozenset({
    "Spoofing", "Tampering", "Repudiation",
    "Information Disclosure", "Denial of Service",
    "Elevation of Privilege",
})


def _lint_stride_categories(model: SecurityReport) -> List[str]:
    """All threats must use valid STRIDE categories."""
    violations = []
    for threat in model.threat_catalog:
        if threat.stride_category not in _STRIDE_CATEGORIES:
            violations.append(
                f"Threat '{threat.threat_id}' has invalid stride_category "
                f"'{threat.stride_category}'.  Must be one of: "
                f"{sorted(_STRIDE_CATEGORIES)}."
            )
    return violations


def _lint_minimum_threats(model: SecurityReport) -> List[str]:
    """Threat catalog must contain at least 3 threats."""
    if len(model.threat_catalog) < 3:
        return [
            f"threat_catalog must contain at least 3 threats; "
            f"got {len(model.threat_catalog)}."
        ]
    return []


def _lint_unique_threat_ids(model: SecurityReport) -> List[str]:
    """All threat_ids must be unique."""
    seen = set()
    violations = []
    for threat in model.threat_catalog:
        if threat.threat_id in seen:
            violations.append(
                f"Duplicate threat_id '{threat.threat_id}'."
            )
        seen.add(threat.threat_id)
    return violations


def _lint_input_validation_rules(model: SecurityReport) -> List[str]:
    """Must have at least 2 input validation rules."""
    if len(model.input_validation_rules) < 2:
        return [
            f"input_validation_rules must contain at least 2 rules; "
            f"got {len(model.input_validation_rules)}."
        ]
    return []


class SecurityAgent:
    """Security analysis and threat modeling agent.

    Parameters
    ----------
    llm_client:
        Callable that sends a prompt string to the LLM and returns the
        raw response text.
    """

    def __init__(self, llm_client: Callable[..., Any]) -> None:
        self._harness = AgentExecutionHarness(
            target_schema=SecurityReport,
            agent_name="SecurityAgent",
            system_prompt=SECURITY_SYSTEM_PROMPT,
            llm_client=llm_client,
            extra_lint_rules=[
                _lint_stride_categories,
                _lint_minimum_threats,
                _lint_unique_threat_ids,
                _lint_input_validation_rules,
            ],
        )

    async def analyze(
        self,
        project_state: Dict[str, Any],
    ) -> HarnessResult:
        """Produce a ``SecurityReport`` from the project state.

        Parameters
        ----------
        project_state:
            Full ``ProjectState.model_dump()`` dict.

        Returns
        -------
        HarnessResult
            On success, ``result.output`` is a ``SecurityReport``.
        """
        context = ContextFilter.for_security(project_state)
        from app.agents.model_client import LocalModelClient
        if isinstance(getattr(self._harness.llm_client, '__self__', None), LocalModelClient):
            from app.harness.sections import execute_sections
            return await execute_sections(self._harness, context, [
                ['authentication_mechanism', 'authorization_model', 'data_protection_at_rest', 'data_protection_in_transit'],
                ['input_validation_rules', 'ai_threat_mitigations', 'threat_catalog'],
            ])
        return await self._harness.execute(context_data=context)
