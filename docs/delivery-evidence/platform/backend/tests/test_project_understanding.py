"""
Tests for ProjectUnderstandingAgent (Phase 1 — 17-Dimension Extraction & Provenance).
"""

import json
import pytest
from app.agents.project_understanding_agent import (
    ProjectUnderstandingAgent,
    _lint_never_infer_as_explicit,
    _lint_core_dimensions_present,
)
from app.models.schemas import (
    ExtractedRequirementItem,
    ProjectUnderstandingOutput,
    RequirementSource,
    RequirementType,
)


@pytest.fixture
def mock_valid_understanding_json():
    return json.dumps({
        "project_name": "SatRoadChange-AI",
        "problem": {
            "id": "PROB-001",
            "dimension": "problem",
            "title": "Road Network Degradation & Expansion Tracking Delay",
            "description": "Manual road surveys from aerial photography are slow, costly, and infrequent.",
            "type": "EXPLICIT",
            "source": "USER",
            "confidence": 0.95,
            "evidence": "detects road changes between before and after satellite imagery"
        },
        "goal": {
            "id": "GOAL-001",
            "dimension": "goal",
            "title": "Autonomous Bi-Temporal Road Change Detection",
            "description": "Automatically detect newly paved, degraded, or modified roads using paired satellite images.",
            "type": "EXPLICIT",
            "source": "USER",
            "confidence": 0.95,
            "evidence": "I want to build an AI system that detects road changes between before and after satellite imagery"
        },
        "target_users": [
            {
                "id": "USR-001",
                "dimension": "target_users",
                "title": "Municipal Urban Planners & Infrastructure Inspectors",
                "description": "Civil engineers requiring updated road network vectors.",
                "type": "INFERRED",
                "source": "INFERENCE",
                "confidence": 0.85,
                "evidence": "Inferred from municipal maintenance and satellite observation context"
            }
        ],
        "user_journeys": [
            {
                "id": "JRN-001",
                "dimension": "user_journeys",
                "title": "Upload Before/After Tiles & Inspect Change Heatmap",
                "description": "User selects spatial AOI, uploads bi-temporal rasters, and views segmented road vectors.",
                "type": "INFERRED",
                "source": "INFERENCE",
                "confidence": 0.85,
                "evidence": "Typical satellite change detection journey"
            }
        ],
        "functional_requirements": [
            {
                "id": "REQ-F-001",
                "dimension": "functional_requirements",
                "title": "Bi-Temporal Image Registration & Alignment",
                "description": "Co-register satellite before and after rasters to common coordinate frame.",
                "type": "INFERRED",
                "source": "INFERENCE",
                "confidence": 0.90,
                "evidence": "Required for comparing before/after images"
            },
            {
                "id": "REQ-F-002",
                "dimension": "functional_requirements",
                "title": "Road Mask Segmentation",
                "description": "Segment road corridors and output delta polygons.",
                "type": "EXPLICIT",
                "source": "USER",
                "confidence": 0.95,
                "evidence": "detects road changes"
            }
        ],
        "non_functional_requirements": [
            {
                "id": "REQ-NF-001",
                "dimension": "non_functional_requirements",
                "title": "Tile Processing Latency",
                "description": "Process a 2048x2048 tile in under 15 seconds.",
                "type": "INFERRED",
                "source": "INFERENCE",
                "confidence": 0.80,
                "evidence": "Engineering performance baseline"
            }
        ],
        "constraints": [
            {
                "id": "CON-001",
                "dimension": "constraints",
                "title": "Satellite Imagery Format Support",
                "description": "Must support GeoTIFF with spatial reference coordinates.",
                "type": "INFERRED",
                "source": "INFERENCE",
                "confidence": 0.90,
                "evidence": "Standard geospatial raster format"
            }
        ],
        "technology_preferences": [
            {
                "id": "TECH-001",
                "dimension": "technology_preferences",
                "title": "Computer Vision Change Detection Model",
                "description": "Siamese segmentation or bi-temporal transformer network.",
                "type": "INFERRED",
                "source": "INFERENCE",
                "confidence": 0.85,
                "evidence": "State of the art for bi-temporal satellite road changes"
            }
        ],
        "expected_outputs": [
            {
                "id": "OUT-001",
                "dimension": "expected_outputs",
                "title": "Road Change GeoJSON & Difference Mask",
                "description": "Vector polygons of new/modified roads plus raster confidence heatmap.",
                "type": "INFERRED",
                "source": "INFERENCE",
                "confidence": 0.85,
                "evidence": "Expected output for GIS engineering workflows"
            }
        ],
        "non_goals": [
            {
                "id": "NON-001",
                "dimension": "non_goals",
                "title": "Real-time Vehicle Tracking",
                "description": "System does not track moving vehicular traffic in real time.",
                "type": "INFERRED",
                "source": "AGENT",
                "confidence": 0.95,
                "evidence": "Scope boundary to keep Phase 1 focused on physical road infrastructure"
            }
        ],
        "assumptions": [
            {
                "id": "ASM-001",
                "dimension": "assumptions",
                "title": "Adequate Spatial Resolution",
                "description": "Assumes input satellite imagery has <= 1m ground sample distance.",
                "type": "ASSUMPTION",
                "source": "AGENT",
                "confidence": 0.75,
                "evidence": "Road lane identification requires sub-meter GSD"
            }
        ],
        "unknowns": [
            {
                "id": "UNK-001",
                "dimension": "unknowns",
                "title": "Target Imagery Resolution & Commercial Licensing",
                "description": "Whether inputs are public Sentinel 10m or commercial 30cm imagery.",
                "type": "UNKNOWN",
                "source": "AGENT",
                "confidence": 0.60,
                "evidence": "Not specified in prompt"
            }
        ],
        "ambiguities": [
            {
                "id": "AMB-001",
                "dimension": "ambiguities",
                "title": "Road Change Scope",
                "description": "Whether changes include potholes/surface cracks or only new road construction.",
                "type": "UNKNOWN",
                "source": "AGENT",
                "confidence": 0.60,
                "evidence": "'road changes' could mean surface defects or topology changes"
            }
        ],
        "risks": [
            {
                "id": "RSK-001",
                "dimension": "risks",
                "title": "Seasonal Cloud Cover & Parallax Shift",
                "description": "Clouds and off-nadir angles causing false change positives.",
                "type": "INFERRED",
                "source": "AGENT",
                "confidence": 0.85,
                "evidence": "Common satellite vision hazard"
            }
        ],
        "evidence": [
            "detects road changes between before and after satellite imagery"
        ],
        "confidence": 0.91
    })


@pytest.mark.asyncio
async def test_project_understanding_extraction(mock_valid_understanding_json):
    """Test successful extraction across all 17 dimensions."""
    async def mock_llm(prompt: str) -> str:
        return mock_valid_understanding_json

    agent = ProjectUnderstandingAgent(llm_client=mock_llm)
    result = await agent.analyze_project_idea(
        "I want to build an AI system that detects road changes between before and after satellite imagery."
    )

    assert result.success is True
    assert result.output is not None
    output: ProjectUnderstandingOutput = result.output

    assert output.project_name == "SatRoadChange-AI"
    assert output.problem.id == "PROB-001"
    assert output.problem.type == RequirementType.EXPLICIT
    assert output.problem.source == RequirementSource.USER
    assert len(output.functional_requirements) == 2
    assert len(output.non_goals) >= 1
    assert len(output.unknowns) >= 1
    assert output.confidence >= 0.85


def test_lint_never_infer_as_explicit_catches_violation(mock_valid_understanding_json):
    """Ensure linter fails if an INFERENCE or AGENT source is labeled EXPLICIT."""
    data = json.loads(mock_valid_understanding_json)
    # Violate invariant: source INFERENCE with type EXPLICIT
    data["functional_requirements"][0]["source"] = "INFERENCE"
    data["functional_requirements"][0]["type"] = "EXPLICIT"

    model = ProjectUnderstandingOutput.model_validate(data)
    violations = _lint_never_infer_as_explicit(model)
    assert len(violations) > 0
    assert "must NEVER be represented as an EXPLICIT user requirement" in violations[0]


def test_lint_core_dimensions_present():
    """Ensure missing project_name or problem raises lint violation."""
    model = ProjectUnderstandingOutput(
        project_name="",
        problem=ExtractedRequirementItem(
            id="P1", dimension="problem", title="", description="",
            type=RequirementType.EXPLICIT, source=RequirementSource.USER, confidence=0.9
        ),
        goal=ExtractedRequirementItem(
            id="G1", dimension="goal", title="", description="",
            type=RequirementType.EXPLICIT, source=RequirementSource.USER, confidence=0.9
        ),
        functional_requirements=[],
    )
    violations = _lint_core_dimensions_present(model)
    assert len(violations) >= 2
