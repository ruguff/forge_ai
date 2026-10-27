"""
ProjectForge AI — Empirical Confidence Calibration Engine.

Replaces self-reported LLM confidence scores with a formula grounded in
verifiable evidence counts and declared risk, preventing hallucination-
inflated scores from propagating through the pipeline.

Formula
-------
    C = (E_count / (E_count + A_unverified)) × (1.0 − P_risk)

    Where:
        E_count             = number of fact references (verifiable evidence)
        A_unverified        = number of unverified assumptions
        P_risk              = declared risk penalty ∈ [0.0, 0.4]

    The result is clamped to [0.05, 0.98] to avoid pathological extremes
    (absolute certainty or total ignorance).
"""

from __future__ import annotations

__all__ = ["compute_calibrated_confidence"]

# Absolute floor / ceiling — no agent should ever claim 0 % or 100 %.
_CONFIDENCE_FLOOR = 0.05
_CONFIDENCE_CEILING = 0.98


def compute_calibrated_confidence(
    fact_count: int,
    unverified_assumptions_count: int,
    risk_penalty: float,
) -> float:
    """Compute an empirically calibrated confidence score.

    Parameters
    ----------
    fact_count:
        Number of verifiable fact references provided by the agent.
        Must be ``>= 0``.
    unverified_assumptions_count:
        Number of unverified assumptions the agent declared.
        Must be ``>= 0``.
    risk_penalty:
        Risk penalty declared by the agent. Expected in ``[0.0, 0.4]``
        but clamped internally to ``[0.0, 1.0]`` for safety.

    Returns
    -------
    float
        Calibrated confidence score clamped to ``[0.05, 0.98]``.

    Raises
    ------
    ValueError
        If *fact_count* or *unverified_assumptions_count* is negative.
    """
    if fact_count < 0:
        raise ValueError(
            f"fact_count must be >= 0, got {fact_count}"
        )
    if unverified_assumptions_count < 0:
        raise ValueError(
            f"unverified_assumptions_count must be >= 0, "
            f"got {unverified_assumptions_count}"
        )

    # Clamp risk_penalty to [0.0, 1.0] defensively
    risk_penalty = max(0.0, min(risk_penalty, 1.0))

    total = fact_count + unverified_assumptions_count

    # Edge case: no evidence AND no assumptions → minimally confident
    if total == 0:
        evidence_ratio = 0.0
    else:
        evidence_ratio = fact_count / total

    raw = evidence_ratio * (1.0 - risk_penalty)

    return max(_CONFIDENCE_FLOOR, min(raw, _CONFIDENCE_CEILING))
