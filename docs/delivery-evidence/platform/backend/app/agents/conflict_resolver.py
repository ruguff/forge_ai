"""
ProjectForge AI — Conflict Resolver Engine.

Detects structural contradictions across agent specifications and resolves
them using a weighted multi-criteria decision matrix.

Conflict categories
-------------------
1. **AI necessity** — AI agent recommends custom LLM vs. Engineering
   agent recommends static regex/SQL.
2. **Framework / Protocol** — Engineering specifies REST vs. UX/AI
   requiring low-latency bi-directional WebSockets.
3. **Database** — Relational transactional requirements vs. unstructured
   document storage vs. graph requirements.
4. **Security vs. UX friction** — Strict MFA session timeouts vs.
   seamless persistent state.
5. **Latency SLA vs. Compute budget** — Low latency demands exceed
   declared infrastructure budget.

Resolution uses weighted utility scoring:
    U = Σ (weight × score)
    Maintainability (0.25), Latency/Performance (0.20),
    Implementation Complexity (0.20), Infrastructure Cost (0.20),
    Scalability (0.15).
"""

from __future__ import annotations

import logging
import re
from typing import Any, Callable, Dict, List, Optional, Tuple

from app.harness.base_harness import AgentExecutionHarness, HarnessResult
from app.harness.context_filter import ContextFilter
from app.models.schemas import (
    Conflict,
    ProjectState,
)

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Weighted decision matrix criteria
# ──────────────────────────────────────────────────────────────────────────────

CRITERIA_WEIGHTS: Dict[str, float] = {
    "maintainability": 0.25,
    "latency_performance": 0.20,
    "implementation_complexity": 0.20,
    "infrastructure_cost": 0.20,
    "scalability": 0.15,
}

# Type alias for structured conflict detector
ConflictDetector = Callable[[Dict[str, Any]], Optional[Conflict]]


# ──────────────────────────────────────────────────────────────────────────────
# Utility computation
# ──────────────────────────────────────────────────────────────────────────────


def compute_weighted_utility(
    option_scores: Dict[str, float],
) -> float:
    """Compute total utility for one option across all criteria.

    Parameters
    ----------
    option_scores:
        Mapping from criterion name to score (1.0–10.0).

    Returns
    -------
    float
        Weighted sum: U = Σ (weight × score).
    """
    total = 0.0
    for criterion, weight in CRITERIA_WEIGHTS.items():
        score = option_scores.get(criterion, 5.0)
        # Clamp score to [1.0, 10.0]
        score = max(1.0, min(score, 10.0))
        total += weight * score
    return round(total, 4)


# ──────────────────────────────────────────────────────────────────────────────
# Individual conflict detectors
# ──────────────────────────────────────────────────────────────────────────────


def _detect_ai_necessity_conflict(
    state: Dict[str, Any],
) -> Optional[Conflict]:
    """Detect AI necessity contradiction.

    Fires when AI agent says ``ai_required=True`` (recommending custom ML)
    but Engineering agent's backend or system pattern suggests a simple
    deterministic approach (regex, SQL, rule engine).
    """
    ai_spec = state.get("ai_spec")
    eng_spec = state.get("engineering_spec")
    if ai_spec is None or eng_spec is None:
        return None

    ai_required = ai_spec.get("ai_required", False)
    if not ai_required:
        return None

    # Check if engineering backend/pattern suggests deterministic approach
    backend = eng_spec.get("backend_architecture", {})
    backend_selected = str(backend.get("selected", "")).lower()
    pattern = str(eng_spec.get("system_architecture_pattern", "")).lower()

    deterministic_signals = {"regex", "sql", "rule engine", "heuristic",
                             "static", "deterministic"}
    combined = f"{backend_selected} {pattern}"
    if any(signal in combined for signal in deterministic_signals):
        return Conflict(
            conflict_id="CONFLICT-AI-001",
            issue=(
                "AI agent recommends custom ML/LLM pipeline but Engineering "
                "agent's architecture suggests deterministic approach."
            ),
            participating_agents=["AIMLAgent", "EngineeringAgent"],
            conflicting_recommendations={
                "AIMLAgent": f"ai_required=True, problem_type={ai_spec.get('problem_type', 'UNKNOWN')}",
                "EngineeringAgent": f"backend={backend_selected}, pattern={pattern}",
            },
            evaluation_criteria_scores={},
            arbitrated_resolution="",
            technical_justification="",
            compromise_penalties=[],
            confidence=0.0,
        )
    return None


def _detect_protocol_conflict(
    state: Dict[str, Any],
) -> Optional[Conflict]:
    """Detect framework/protocol contradiction.

    Fires when Engineering specifies REST but AI inference latency SLA
    or UX real-time requirements imply WebSocket/gRPC is needed.
    """
    eng_spec = state.get("engineering_spec")
    ai_spec = state.get("ai_spec")
    ux_spec = state.get("ux_spec")
    if eng_spec is None:
        return None

    api = eng_spec.get("api_protocol", {})
    api_selected = str(api.get("selected", "")).lower()

    # REST protocol
    is_rest = "rest" in api_selected and "websocket" not in api_selected

    if not is_rest:
        return None

    # Check for low-latency requirements
    needs_realtime = False
    reasons: List[str] = []

    if ai_spec:
        sla_ms = ai_spec.get("inference_latency_sla_ms")
        if sla_ms is not None and sla_ms < 100:
            needs_realtime = True
            reasons.append(f"AI inference SLA = {sla_ms}ms requires streaming")

    if ux_spec:
        journey = ux_spec.get("primary_user_journey", [])
        journey_text = " ".join(str(s).lower() for s in journey)
        if any(kw in journey_text for kw in ("real-time", "realtime",
                                              "live", "streaming", "websocket")):
            needs_realtime = True
            reasons.append("UX journey references real-time/streaming interaction")

    if needs_realtime:
        return Conflict(
            conflict_id="CONFLICT-PROTO-001",
            issue=(
                f"Engineering specifies REST API but downstream agents "
                f"require low-latency bi-directional communication: "
                f"{'; '.join(reasons)}."
            ),
            participating_agents=["EngineeringAgent", "AIMLAgent", "UXAgent"],
            conflicting_recommendations={
                "EngineeringAgent": f"api_protocol={api_selected}",
                "RequiringAgents": "; ".join(reasons),
            },
            evaluation_criteria_scores={},
            arbitrated_resolution="",
            technical_justification="",
            compromise_penalties=[],
            confidence=0.0,
        )
    return None


def _detect_database_conflict(
    state: Dict[str, Any],
) -> Optional[Conflict]:
    """Detect database type contradiction.

    Fires when product spec or AI spec implies graph/document data model
    but engineering spec selects a purely relational database (or vice versa).
    """
    eng_spec = state.get("engineering_spec")
    ai_spec = state.get("ai_spec")
    product_spec = state.get("product_spec")
    if eng_spec is None:
        return None

    db_primary = eng_spec.get("database_primary", {})
    db_selected = str(db_primary.get("selected", "")).lower()

    relational_dbs = {"postgresql", "postgres", "mysql", "mariadb",
                      "sqlite", "sql server", "oracle"}
    document_dbs = {"mongodb", "dynamodb", "firestore", "couchdb",
                    "cosmosdb"}
    graph_dbs = {"neo4j", "neptune", "arangodb", "janusgraph",
                 "dgraph", "tigergraph"}

    is_relational = any(r in db_selected for r in relational_dbs)
    is_document = any(d in db_selected for d in document_dbs)
    is_graph = any(g in db_selected for g in graph_dbs)

    # Look for signals in functional requirements or AI spec
    signals: List[str] = []
    req_text = ""
    if product_spec:
        reqs = product_spec.get("functional_requirements", [])
        req_text = " ".join(str(r).lower() for r in reqs)

    if ai_spec:
        ai_type = str(ai_spec.get("problem_type", "")).lower()
        if "graph" in ai_type or "recommender" in ai_type:
            signals.append(f"AI problem_type={ai_type} implies graph traversal")

    if "graph" in req_text or "relationship" in req_text or "network" in req_text:
        signals.append("Functional requirements reference graph/relationship data")

    if "document" in req_text or "unstructured" in req_text or "json" in req_text:
        signals.append("Functional requirements reference unstructured/document data")

    conflict_found = False
    if is_relational and any("graph" in s.lower() for s in signals):
        conflict_found = True
    if is_relational and any("document" in s.lower() or "unstructured" in s.lower()
                             for s in signals):
        conflict_found = True
    if is_document and "transaction" in req_text:
        signals.append("Functional requirements need ACID transactions")
        conflict_found = True

    if conflict_found and signals:
        return Conflict(
            conflict_id="CONFLICT-DB-001",
            issue=(
                f"Engineering selects '{db_selected}' but downstream "
                f"requirements suggest a different data model: "
                f"{'; '.join(signals)}."
            ),
            participating_agents=["EngineeringAgent", "AIMLAgent", "ProductAgent"],
            conflicting_recommendations={
                "EngineeringAgent": f"database_primary={db_selected}",
                "DownstreamSignals": "; ".join(signals),
            },
            evaluation_criteria_scores={},
            arbitrated_resolution="",
            technical_justification="",
            compromise_penalties=[],
            confidence=0.0,
        )
    return None


def _detect_security_ux_conflict(
    state: Dict[str, Any],
) -> Optional[Conflict]:
    """Detect security vs. UX friction.

    Fires when security requires strict session controls (MFA, short
    timeouts) but UX specifies seamless persistent state.
    """
    security = state.get("security_report")
    ux_spec = state.get("ux_spec")
    if security is None or ux_spec is None:
        return None

    # Look for strict session indicators in security
    auth_model = str(security.get("authorization_model", "")).lower()
    auth_mechanism = security.get("authentication_mechanism", {})
    auth_selected = str(auth_mechanism.get("selected", "")).lower()
    security_text = f"{auth_model} {auth_selected}"

    strict_signals = {"mfa", "multi-factor", "short-lived", "session timeout",
                      "re-authenticate", "step-up"}
    has_strict = any(s in security_text for s in strict_signals)

    # Look for seamless UX indicators
    journey = ux_spec.get("primary_user_journey", [])
    accessibility = ux_spec.get("accessibility_standards", [])
    ux_text = " ".join(str(s).lower() for s in journey + accessibility)

    seamless_signals = {"persistent", "remember me", "seamless",
                        "stay logged in", "auto-login", "sso"}
    needs_seamless = any(s in ux_text for s in seamless_signals)

    if has_strict and needs_seamless:
        return Conflict(
            conflict_id="CONFLICT-SEC-UX-001",
            issue=(
                "Security mandates strict session controls (MFA, short "
                "timeouts) but UX requires seamless persistent state."
            ),
            participating_agents=["SecurityAgent", "UXAgent"],
            conflicting_recommendations={
                "SecurityAgent": f"auth={auth_selected}, model={auth_model}",
                "UXAgent": "Requires seamless/persistent session experience",
            },
            evaluation_criteria_scores={},
            arbitrated_resolution="",
            technical_justification="",
            compromise_penalties=[],
            confidence=0.0,
        )
    return None


def _detect_latency_budget_conflict(
    state: Dict[str, Any],
) -> Optional[Conflict]:
    """Detect latency SLA vs. compute budget conflict.

    Fires when AI inference latency SLA demands expensive compute but
    intake Q8 (budget constraints) indicates a tight budget.
    """
    ai_spec = state.get("ai_spec")
    intake = state.get("intake_qa", {})
    if ai_spec is None:
        return None

    sla_ms = ai_spec.get("inference_latency_sla_ms")
    if sla_ms is None:
        return None

    budget_text = str(intake.get("Q8", "")).lower()
    cost_est = ai_spec.get("compute_and_cost_estimation", {})
    monthly_cost = str(cost_est.get("monthly", "")).lower() if cost_est else ""

    # Extract budget numbers
    budget_numbers = [int(n) for n in re.findall(r"\$?([\d,]+)", budget_text.replace(",", ""))
                      if n.isdigit()]
    cost_numbers = [int(n) for n in re.findall(r"\$?([\d,]+)", monthly_cost.replace(",", ""))
                    if n.isdigit()]

    tight_budget = any(
        kw in budget_text for kw in ("tight", "limited", "minimal",
                                     "constrained", "low")
    )

    # Budget explicitly stated and cost exceeds it
    budget_exceeded = False
    if budget_numbers and cost_numbers:
        max_budget = max(budget_numbers)
        min_cost = min(cost_numbers)
        if min_cost > max_budget:
            budget_exceeded = True

    if (sla_ms < 200 and tight_budget) or budget_exceeded:
        return Conflict(
            conflict_id="CONFLICT-COST-001",
            issue=(
                f"AI inference SLA of {sla_ms}ms demands high-performance "
                f"compute infrastructure but budget constraints are tight: "
                f"'{budget_text}'."
            ),
            participating_agents=["AIMLAgent", "EngineeringAgent"],
            conflicting_recommendations={
                "AIMLAgent": f"inference_sla={sla_ms}ms, cost={monthly_cost or 'unspecified'}",
                "UserConstraint": f"Q8={budget_text}",
            },
            evaluation_criteria_scores={},
            arbitrated_resolution="",
            technical_justification="",
            compromise_penalties=[],
            confidence=0.0,
        )
    return None


# All registered detectors
_CONFLICT_DETECTORS: List[ConflictDetector] = [
    _detect_ai_necessity_conflict,
    _detect_protocol_conflict,
    _detect_database_conflict,
    _detect_security_ux_conflict,
    _detect_latency_budget_conflict,
]


# ──────────────────────────────────────────────────────────────────────────────
# Conflict Resolver
# ──────────────────────────────────────────────────────────────────────────────


class ConflictResolver:
    """Detects and resolves inter-agent conflicts using a weighted
    multi-criteria decision matrix.

    Parameters
    ----------
    llm_client:
        Optional callable for LLM-assisted resolution narrative
        generation.  When ``None``, resolutions are generated from
        the utility scores alone (deterministic mode).
    """

    def __init__(
        self,
        llm_client: Optional[Callable[..., Any]] = None,
    ) -> None:
        self.llm_client = llm_client

    def detect_conflicts(
        self,
        state: Dict[str, Any],
    ) -> List[Conflict]:
        """Scan all agent specifications for structural contradictions.

        Parameters
        ----------
        state:
            Full ``ProjectState.model_dump()`` dict (or already-filtered
            via ``ContextFilter.for_conflict_resolver``).

        Returns
        -------
        list[Conflict]
            List of detected conflicts with empty resolution fields.
        """
        conflicts: List[Conflict] = []
        for detector in _CONFLICT_DETECTORS:
            conflict = detector(state)
            if conflict is not None:
                conflicts.append(conflict)
                logger.info(
                    "Detected conflict: %s — %s",
                    conflict.conflict_id, conflict.issue,
                )
        return conflicts

    def resolve_conflict(
        self,
        conflict: Conflict,
        project_constraints: Dict[str, Any],
        option_a_scores: Optional[Dict[str, float]] = None,
        option_b_scores: Optional[Dict[str, float]] = None,
    ) -> Conflict:
        """Apply weighted multi-criteria decision matrix to arbitrate.

        Parameters
        ----------
        conflict:
            A detected conflict with empty resolution fields.
        project_constraints:
            Dict containing user constraints (e.g. budget, timeline)
            used to contextualise the resolution narrative.
        option_a_scores:
            Scores (1.0–10.0) for each criterion for Option A.
            Keys must be from ``CRITERIA_WEIGHTS``.
        option_b_scores:
            Scores for Option B.

        Returns
        -------
        Conflict
            Updated conflict with filled ``evaluation_criteria_scores``,
            ``arbitrated_resolution``, ``technical_justification``,
            ``compromise_penalties``, and ``confidence``.
        """
        # Default scores if not provided (neutral)
        if option_a_scores is None:
            option_a_scores = {k: 5.0 for k in CRITERIA_WEIGHTS}
        if option_b_scores is None:
            option_b_scores = {k: 5.0 for k in CRITERIA_WEIGHTS}

        agents = conflict.participating_agents
        recs = conflict.conflicting_recommendations
        option_a_label = agents[0] if agents else "Option A"
        option_b_label = agents[1] if len(agents) > 1 else "Option B"

        utility_a = compute_weighted_utility(option_a_scores)
        utility_b = compute_weighted_utility(option_b_scores)

        # Build evaluation matrix
        evaluation = {
            option_a_label: {
                **{k: option_a_scores.get(k, 5.0) for k in CRITERIA_WEIGHTS},
                "total_utility": utility_a,
            },
            option_b_label: {
                **{k: option_b_scores.get(k, 5.0) for k in CRITERIA_WEIGHTS},
                "total_utility": utility_b,
            },
        }

        # Determine winner
        if utility_a >= utility_b:
            winner, loser = option_a_label, option_b_label
            winner_utility, loser_utility = utility_a, utility_b
            winner_rec = recs.get(option_a_label, "")
        else:
            winner, loser = option_b_label, option_a_label
            winner_utility, loser_utility = utility_b, utility_a
            winner_rec = recs.get(option_b_label, "")

        margin = winner_utility - loser_utility

        # Compute confidence from utility margin (higher margin = higher confidence)
        # Margin ranges from 0 to ~9.0; map to [0.3, 0.95]
        raw_confidence = 0.3 + (min(margin, 5.0) / 5.0) * 0.65
        confidence = round(min(raw_confidence, 0.95), 2)

        # Build resolution narrative
        resolution = (
            f"Adopt {winner}'s recommendation. {winner_rec}. "
            f"Utility: {winner}={winner_utility:.2f} vs "
            f"{loser}={loser_utility:.2f} (margin={margin:.2f})."
        )
        justification = (
            f"Multi-criteria weighted decision matrix applied with "
            f"criteria: {', '.join(CRITERIA_WEIGHTS.keys())}. "
            f"{winner} scored higher across the weighted dimensions, "
            f"yielding a total utility advantage of {margin:.2f}."
        )

        # Compromise penalties
        penalties = [
            f"{loser}'s recommendation deferred — may impact "
            f"its optimised use case.",
            f"Margin of {margin:.2f} indicates "
            f"{'strong' if margin > 2.0 else 'moderate' if margin > 0.5 else 'weak'} "
            f"preference; monitor for regressions.",
        ]

        # Return updated Conflict
        return Conflict(
            conflict_id=conflict.conflict_id,
            issue=conflict.issue,
            participating_agents=conflict.participating_agents,
            conflicting_recommendations=conflict.conflicting_recommendations,
            evaluation_criteria_scores=evaluation,
            arbitrated_resolution=resolution,
            technical_justification=justification,
            compromise_penalties=penalties,
            confidence=confidence,
        )

    def detect_and_resolve_all(
        self,
        state: Dict[str, Any],
        default_option_scores: Optional[
            Dict[str, Tuple[Dict[str, float], Dict[str, float]]]
        ] = None,
    ) -> List[Conflict]:
        """Convenience: detect all conflicts and resolve each.

        Parameters
        ----------
        state:
            Full project state dict.
        default_option_scores:
            Optional mapping from ``conflict_id`` to
            ``(option_a_scores, option_b_scores)`` tuples.

        Returns
        -------
        list[Conflict]
            Fully resolved conflicts.
        """
        if default_option_scores is None:
            default_option_scores = {}

        constraints = {
            "intake_qa": state.get("intake_qa", {}),
        }

        raw_conflicts = self.detect_conflicts(state)
        resolved: List[Conflict] = []

        for conflict in raw_conflicts:
            scores = default_option_scores.get(conflict.conflict_id)
            if scores:
                a_scores, b_scores = scores
            else:
                a_scores, b_scores = None, None

            resolved_conflict = self.resolve_conflict(
                conflict=conflict,
                project_constraints=constraints,
                option_a_scores=a_scores,
                option_b_scores=b_scores,
            )
            resolved.append(resolved_conflict)

        return resolved
