"""
Tests for RequirementEngine (Phase 2 — 7-Criteria Materiality Filter on Unknowns).
"""

import pytest
from app.agents.requirement_engine import RequirementEngine
from app.models.schemas import (
    ExtractedRequirementItem,
    ProjectUnderstandingOutput,
    RequirementSource,
    RequirementType,
)


def test_benign_unknown_safely_inferred():
    """Test that benign UI/theme unknowns bypass user clarification and are safely inferred."""
    engine = RequirementEngine()
    item = ExtractedRequirementItem(
        id="UNK-UI-01",
        dimension="unknowns",
        title="UI Dark Mode Theme Styling",
        description="User did not specify color theme styling or button font preferences.",
        type=RequirementType.UNKNOWN,
        source=RequirementSource.AGENT,
        confidence=0.5,
    )

    is_material, meta, clar_q = engine.evaluate_unknown_item(item)
    assert not is_material
    assert clar_q is None
    assert meta["can_safely_infer"] is True


def test_agent_delegatable_unknown():
    """Test that specialist domain questions (e.g. QA test framework) are delegated to agents."""
    engine = RequirementEngine()
    item = ExtractedRequirementItem(
        id="UNK-QA-01",
        dimension="unknowns",
        title="Automated Test Framework Selection",
        description="Whether to use pytest or unittest for unit test coverage threshold.",
        type=RequirementType.UNKNOWN,
        source=RequirementSource.AGENT,
        confidence=0.5,
    )

    is_material, meta, clar_q = engine.evaluate_unknown_item(item)
    assert not is_material
    assert clar_q is None
    assert meta["can_agent_determine"] is True
    assert meta["delegated_agent"] == "qa_strategist"


def test_material_unknown_generates_targeted_clarification():
    """Test that an unknown affecting Architecture/Cost/Security generates a single targeted question."""
    engine = RequirementEngine()
    item = ExtractedRequirementItem(
        id="UNK-SAT-01",
        dimension="unknowns",
        title="Satellite Imagery Resolution & Source",
        description="Target input satellite imagery resolution and commercial licensing boundaries.",
        type=RequirementType.UNKNOWN,
        source=RequirementSource.AGENT,
        confidence=0.5,
    )

    is_material, meta, clar_q = engine.evaluate_unknown_item(item)
    assert is_material is True
    assert clar_q is not None
    assert clar_q.question_id == "CLAR-UNK-SAT-01"
    assert "Satellite Imagery Resolution & Source" in clar_q.question
    assert "materially impacts" in clar_q.reason
    assert len(clar_q.possible_options) >= 2
    assert any("commercial" in opt.lower() or "sentinel" in opt.lower() for opt in clar_q.possible_options)


def test_full_requirement_engine_flow():
    """Test evaluating a full ProjectUnderstandingOutput with mixed unknowns."""
    engine = RequirementEngine()

    output = ProjectUnderstandingOutput(
        project_name="SatRoadChange-AI",
        problem=ExtractedRequirementItem(
            id="P1", dimension="problem", title="Road surveying", description="Slow surveys",
            type=RequirementType.EXPLICIT, source=RequirementSource.USER, confidence=0.9
        ),
        goal=ExtractedRequirementItem(
            id="G1", dimension="goal", title="Auto detection", description="Detect changes",
            type=RequirementType.EXPLICIT, source=RequirementSource.USER, confidence=0.9
        ),
        unknowns=[
            ExtractedRequirementItem(
                id="UNK-01", dimension="unknowns", title="UI theme color", description="Button styling color",
                type=RequirementType.UNKNOWN, source=RequirementSource.AGENT, confidence=0.5
            ),
            ExtractedRequirementItem(
                id="UNK-02", dimension="unknowns", title="Satellite imagery resolution", description="Resolution requirement",
                type=RequirementType.UNKNOWN, source=RequirementSource.AGENT, confidence=0.5
            ),
        ],
        ambiguities=[
            ExtractedRequirementItem(
                id="AMB-01", dimension="ambiguities", title="Output format", description="GeoJSON vs PDF export",
                type=RequirementType.UNKNOWN, source=RequirementSource.AGENT, confidence=0.5
            )
        ]
    )

    result = engine.evaluate_requirements(output)
    assert result.evaluated_unknowns_count == 3
    # UI theme color was safely inferred
    assert len(result.inferred_resolutions) >= 1
    # Satellite imagery resolution and Output format generated clarification questions
    assert len(result.clarification_questions) >= 1
    assert result.can_continue_autonomously is False
