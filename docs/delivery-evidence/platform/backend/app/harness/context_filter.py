"""
ProjectForge AI — Agent Context Isolation Filter.

Extracts strictly necessary subsets of ``ProjectState`` for each agent
to prevent token bloat and hallucination.  Each method returns only the
intake Q&A keys and specification fields the target agent needs.

Design rationale
----------------
- Intake questions are referenced by key (Q1–Q10) so agents only receive
  the questions relevant to their domain.
- Nested fields (e.g. ``engineering_spec.frontend_architecture``) are
  extracted individually to further minimise context.
- All returned dicts are deep-copied to prevent mutation of shared state.
"""

from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional


__all__ = ["ContextFilter"]


def _pick_intake_keys(
    intake_qa: Dict[str, str],
    keys: List[str],
) -> Dict[str, str]:
    """Extract only the specified Q-keys from the intake Q&A dict."""
    return {k: copy.deepcopy(intake_qa[k]) for k in keys if k in intake_qa}


def _safe_get(data: Optional[Dict[str, Any]], key: str) -> Any:
    """Safely retrieve a nested key from a dict, returning None on miss."""
    if data is None:
        return None
    value = data.get(key)
    return copy.deepcopy(value) if value is not None else None


class ContextFilter:
    """Produces minimal, agent-scoped context slices from a ProjectState.

    Every ``for_*`` method accepts a ``ProjectState`` instance (or a dict
    representation via ``.model_dump()``) and returns a plain dict
    containing **only** the fields that agent is authorised to see.

    Usage::

        ctx = ContextFilter.for_product(project_state)
    """

    # ──────────────────────────────────────────────────────────────────────
    # Product Manager
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod
    def for_product(state: Dict[str, Any]) -> Dict[str, Any]:
        """Context for the Product Manager agent.

        Returns ``raw_idea`` and intake Q1, Q2, Q3, Q4, Q10.
        """
        intake = state.get("intake_qa", {})
        return {
            "raw_idea": copy.deepcopy(state.get("raw_idea")),
            "intake_qa": _pick_intake_keys(
                intake, ["Q1", "Q2", "Q3", "Q4", "Q10"]
            ),
        }

    # ──────────────────────────────────────────────────────────────────────
    # AI / ML Architect
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod
    def for_aiml(state: Dict[str, Any]) -> Dict[str, Any]:
        """Context for the AI/ML Architect agent.

        Returns intake Q4, Q5, Q6, Q7, Q8, Q9, Q10 and
        ``product_spec.functional_requirements``.
        """
        intake = state.get("intake_qa", {})
        product_spec = state.get("product_spec")

        result: Dict[str, Any] = {
            "intake_qa": _pick_intake_keys(
                intake, ["Q4", "Q5", "Q6", "Q7", "Q8", "Q9", "Q10"]
            ),
        }

        # Extract only functional_requirements from product_spec
        func_reqs = _safe_get(product_spec, "functional_requirements")
        if func_reqs is not None:
            result["functional_requirements"] = func_reqs

        return result

    # ──────────────────────────────────────────────────────────────────────
    # Engineering Lead
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod
    def for_engineering(state: Dict[str, Any]) -> Dict[str, Any]:
        """Context for the Engineering Lead agent.

        Returns intake Q5, Q6, Q8, Q9, ``product_spec``, and ``ai_spec``.
        """
        intake = state.get("intake_qa", {})
        return {
            "intake_qa": _pick_intake_keys(
                intake, ["Q5", "Q6", "Q8", "Q9"]
            ),
            "product_spec": copy.deepcopy(state.get("product_spec")),
            "ai_spec": copy.deepcopy(state.get("ai_spec")),
        }

    # ──────────────────────────────────────────────────────────────────────
    # UX Designer
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod
    def for_ux(state: Dict[str, Any]) -> Dict[str, Any]:
        """Context for the UX Designer agent.

        Returns intake Q2, Q3, ``product_spec``, and
        ``engineering_spec.frontend_architecture``.
        """
        intake = state.get("intake_qa", {})
        eng_spec = state.get("engineering_spec")

        result: Dict[str, Any] = {
            "intake_qa": _pick_intake_keys(intake, ["Q2", "Q3"]),
            "product_spec": copy.deepcopy(state.get("product_spec")),
        }

        frontend = _safe_get(eng_spec, "frontend_architecture")
        if frontend is not None:
            result["frontend_architecture"] = frontend

        return result

    # ──────────────────────────────────────────────────────────────────────
    # Security Auditor
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod
    def for_security(state: Dict[str, Any]) -> Dict[str, Any]:
        """Context for the Security Auditor agent.

        Returns intake Q5, Q8, Q9, ``engineering_spec``, and ``ai_spec``.
        """
        intake = state.get("intake_qa", {})
        return {
            "intake_qa": _pick_intake_keys(intake, ["Q5", "Q8", "Q9"]),
            "engineering_spec": copy.deepcopy(state.get("engineering_spec")),
            "ai_spec": copy.deepcopy(state.get("ai_spec")),
        }

    # ──────────────────────────────────────────────────────────────────────
    # QA Strategist
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod
    def for_qa(state: Dict[str, Any]) -> Dict[str, Any]:
        """Context for the QA Strategist agent.

        Returns ``product_spec``, ``engineering_spec``,
        ``security_report``, and ``ai_spec``.
        """
        return {
            "product_spec": copy.deepcopy(state.get("product_spec")),
            "engineering_spec": copy.deepcopy(state.get("engineering_spec")),
            "security_report": copy.deepcopy(state.get("security_report")),
            "ai_spec": copy.deepcopy(state.get("ai_spec")),
        }

    # ──────────────────────────────────────────────────────────────────────
    # Conflict Resolver
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod
    def for_conflict_resolver(state: Dict[str, Any]) -> Dict[str, Any]:
        """Context for the Conflict Resolver agent.

        Returns all generated specs and user constraints (Q8, Q9).
        """
        intake = state.get("intake_qa", {})
        return {
            "intake_qa": _pick_intake_keys(intake, ["Q8", "Q9"]),
            "product_spec": copy.deepcopy(state.get("product_spec")),
            "ai_spec": copy.deepcopy(state.get("ai_spec")),
            "engineering_spec": copy.deepcopy(state.get("engineering_spec")),
            "ux_spec": copy.deepcopy(state.get("ux_spec")),
            "security_report": copy.deepcopy(state.get("security_report")),
            "qa_spec": copy.deepcopy(state.get("qa_spec")),
            "detected_conflicts": copy.deepcopy(
                state.get("detected_conflicts", [])
            ),
        }

    # ──────────────────────────────────────────────────────────────────────
    # Final / Blueprint Architect
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod
    def for_final_architect(state: Dict[str, Any]) -> Dict[str, Any]:
        """Context for the Final Blueprint Architect agent.

        Returns the entire state including resolved conflicts.
        """
        return copy.deepcopy(state)


# All specialists retain user constraints and their provenance alongside their
# existing scoped inputs. They must never lose a clarified requirement.
def _with_requirements(method):
    def wrapped(state):
        result = method(state)
        if state.get("project_context") is not None:
            result["project_context"] = copy.deepcopy(state["project_context"])
        return result
    return staticmethod(wrapped)


for _name in ("for_product", "for_aiml", "for_engineering", "for_ux", "for_security", "for_qa"):
    setattr(ContextFilter, _name, _with_requirements(getattr(ContextFilter, _name)))
