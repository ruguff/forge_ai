"""
ProjectForge AI — Requirement Engine.

Evaluates every extracted unknown across the 7 mandatory criteria:
  1. Can it safely be inferred?
  2. Can another agent determine it?
  3. Does it materially affect architecture?
  4. Does it materially affect security?
  5. Does it materially affect cost?
  6. Does it materially affect functionality?
  7. Does it materially affect expected output?

If NO to material impact or safely delegatable/inferrable:
  Continue autonomously.

If YES (material impact that cannot safely be decided by agents):
  Generate a targeted clarification request.
  - Minimum number of questions (prefer one question at a time).
  - Contains: question, reason, impact_if_unknown, possible_options.
  - Never asks trivial UI or implementation questions.
"""

from __future__ import annotations
import re

from typing import Any, Dict, List, Optional, Tuple

from app.harness.contract import AgentContract
from app.models.schemas import (
    ClarificationQuestion,
    ExtractedRequirementItem,
    ProjectContext,
    ProjectUnderstandingOutput,
    RequirementEngineOutput,
    RequirementSource,
    RequirementType,
)


class RequirementEngine:
    """Autonomous engine for evaluating unknowns and generating targeted clarifications."""

    def __init__(self) -> None:
        self.contract = AgentContract(
            id="requirement_engine",
            agent_id="requirement_engine",
            name="Aegis Filter",
            role="CHIEF REQUIREMENT ANALYZER",
            objective="Filter unknowns with 7-point materiality criteria and generate minimal adaptive clarifications.",
            mission="Ensure zero interruption for delegatable unknowns while surfacing critical architectural trade-offs.",
            inputs=["project_understanding_output", "unknowns", "ambiguities"],
            input_schema="ProjectUnderstandingOutput",
            outputs=["requirement_engine_output", "clarification_questions"],
            output_schema="RequirementEngineOutput",
            tools=["materiality_filter", "agent_delegation_router", "question_synthesizer"],
            constraints=[
                "Never ask trivial UI or implementation questions that an engineering agent can safely decide",
                "Prefer one question at a time",
                "Provide concrete possible options for every clarification",
            ],
            confidence=0.95,
        )

    def evaluate_unknown_item(
        self, item: ExtractedRequirementItem
    ) -> Tuple[bool, Dict[str, Any], Optional[ClarificationQuestion]]:
        """Evaluate a single unknown item across the 7 criteria.

        Returns:
            (is_material_gap, evaluation_metadata, optional_clarification_question)
        """
        desc_lower = (item.title + " " + item.description).lower()

        # 1. Can it safely be inferred?
        # Standard software conventions (e.g. REST vs GraphQL default, basic telemetry, Postgres default)
        can_safely_infer = any(
            re.search(r"(?<!\w)" + re.escape(token) + r"(?!\w)", desc_lower) is not None
            for token in [
                "color", "theme", "button", "styling", "css", "font", "layout spacing",
                "database port", "logging format", "json schema validation", "orm",
                "standard rest", "default pagination"
            ]
        )

        # 2. Can another agent determine it?
        # Specialists (Engineering, AI/ML, UX, Security, QA) have full autonomy for their domains
        can_agent_determine = False
        delegated_agent: Optional[str] = None

        if any(token in desc_lower for token in ["unit test", "test framework", "coverage threshold", "e2e"]):
            can_agent_determine = True
            delegated_agent = "qa_strategist"
        elif any(token in desc_lower for token in ["jwt", "tls", "cors", "password hash", "rate limit", "rbac policy"]):
            can_agent_determine = True
            delegated_agent = "security_auditor"
        elif any(token in desc_lower for token in ["screen state", "loading spinner", "responsive breakpoint", "modal animation"]):
            can_agent_determine = True
            delegated_agent = "ux_designer"
        elif any(token in desc_lower for token in ["microservice vs monolith", "cache layer", "docker", "connection pool"]):
            can_agent_determine = True
            delegated_agent = "engineering_lead"
        elif any(token in desc_lower for token in ["batch size", "model weights", "embedding dimensions", "vector index type"]):
            can_agent_determine = True
            delegated_agent = "aiml_architect"

        # 3. Does it materially affect architecture?
        affects_architecture = any(
            token in desc_lower
            for token in [
                "streaming vs batch", "real-time vs scheduled", "on-premise vs cloud",
                "edge vs server", "satellite imagery resolution", "satellite tile resolution", "spatial resolution", "hardware accelerator",
                "offline support", "distributed ingestion", "delivery vs in-store",
                "delivery vs pickup", "fulfillment method", "courier dispatch"
            ]
        )

        # 4. Does it materially affect security?
        affects_security = any(
            token in desc_lower
            for token in [
                "hipaa", "pci", "gdpr", "classified", "satellite imagery privacy",
                "air-gapped", "biometric", "public vs internal access"
            ]
        )

        # 5. Does it materially affect cost?
        affects_cost = any(
            token in desc_lower
            for token in [
                "multi-gpu", "terabytes per day", "cloud budget limit", "commercial api vs open-weight",
                "high resolution imagery licensing", "dedicated cluster", "courier api fees",
                "delivery fleet"
            ]
        )

        # 6. Does it materially affect functionality?
        affects_functionality = any(
            token in desc_lower
            for token in [
                "input format", "video vs image", "detection target", "cadastre data vs raster",
                "automated repair vs human-in-the-loop alerts", "core workflow",
                "fulfillment", "pickup", "courier delivery"
            ]
        )

        # 7. Does it materially affect expected output?
        affects_expected_output = any(
            token in desc_lower
            for token in [
                "geojson", "pdf report", "alert webhook", "bounding box vs segmentation mask",
                "csv export vs 3d model", "mask format"
            ]
        )

        material_impact = (
            affects_architecture
            or affects_security
            or affects_cost
            or affects_functionality
            or affects_expected_output
        )

        evaluation_metadata = {
            "item_id": item.id,
            "title": item.title,
            "can_safely_infer": can_safely_infer,
            "can_agent_determine": can_agent_determine,
            "delegated_agent": delegated_agent,
            "affects_architecture": affects_architecture,
            "affects_security": affects_security,
            "affects_cost": affects_cost,
            "affects_functionality": affects_functionality,
            "affects_expected_output": affects_expected_output,
            "material_impact": material_impact,
        }

        # Autonomous bypass: if safely inferrable or agent can decide, don't ask user!
        if can_safely_infer or can_agent_determine:
            return False, evaluation_metadata, None

        # If it has material impact and cannot be determined autonomously:
        if material_impact:
            # Build targeted question
            question_text = f"Clarification needed for {item.title}: How should the system handle {item.description}?"
            reason = (
                f"This decision materially impacts "
                f"{', '.join([k.replace('affects_', '').capitalize() for k, v in evaluation_metadata.items() if k.startswith('affects_') and v])} "
                f"and cannot be inferred without user intent."
            )
            impact = (
                f"Leaving this unknown forces assumption of default parameters which may not match your operational requirements."
            )
            options = self._synthesize_options(item)

            clarification = ClarificationQuestion(
                question_id=f"CLAR-{item.id}",
                unknown_item_id=item.id,
                question=question_text,
                reason=reason,
                impact_if_unknown=impact,
                possible_options=options,
                status="PENDING",
            )
            return True, evaluation_metadata, clarification

        # Otherwise continue autonomously
        return False, evaluation_metadata, None

    def evaluate_requirements(
        self, understanding: ProjectUnderstandingOutput
    ) -> RequirementEngineOutput:
        """Evaluate all extracted unknowns and ambiguities."""
        material_questions: List[ClarificationQuestion] = []
        inferred_resolutions: List[Dict[str, Any]] = []
        delegated_to_agents: List[Dict[str, Any]] = []

        all_candidate_unknowns = [*understanding.unknowns, *understanding.ambiguities]

        for item in all_candidate_unknowns:
            is_material, metadata, clar_q = self.evaluate_unknown_item(item)
            if is_material and clar_q:
                material_questions.append(clar_q)
            elif metadata["can_safely_infer"]:
                inferred_resolutions.append(
                    {
                        "item_id": item.id,
                        "title": item.title,
                        "resolution": "Safely inferred via engineering convention.",
                    }
                )
            elif metadata["can_agent_determine"]:
                delegated_to_agents.append(
                    {
                        "item_id": item.id,
                        "title": item.title,
                        "delegated_to": metadata["delegated_agent"],
                        "resolution": f"Delegated to specialized agent ({metadata['delegated_agent']}).",
                    }
                )

        can_continue = len(material_questions) == 0

        return RequirementEngineOutput(
            evaluated_unknowns_count=len(all_candidate_unknowns),
            can_continue_autonomously=can_continue,
            clarification_questions=material_questions,
            inferred_resolutions=inferred_resolutions,
            delegated_to_agents=delegated_to_agents,
        )

    def _synthesize_options(self, item: ExtractedRequirementItem) -> List[str]:
        """Synthesize 2-4 concrete, curated options for the user."""
        desc_lower = item.description.lower()
        if "satellite" in desc_lower or "imagery" in desc_lower or "resolution" in desc_lower:
            return [
                "High-resolution commercial satellite (e.g. 30cm–50cm GeoTIFF tiles)",
                "Medium-resolution public satellite (e.g. Sentinel-2 / Landsat 10m bands)",
                "Drone / aerial orthomosaic imagery (RGB 5cm/px)",
            ]
        if "delivery" in desc_lower or "pickup" in desc_lower or "fulfillment" in desc_lower:
            return [
                "Both scheduled local courier delivery and in-store pickup",
                "Local scheduled delivery only (within defined delivery radius)",
                "In-store scheduled customer pickup only",
            ]
        if "streaming" in desc_lower or "real-time" in desc_lower or "frequency" in desc_lower:
            return [
                "On-demand batch processing upon imagery upload",
                "Scheduled nightly/weekly pipeline ingesting delta feeds",
                "Continuous real-time change detection stream",
            ]
        if "output" in desc_lower or "export" in desc_lower or "format" in desc_lower:
            return [
                "Interactive Web GIS viewer + GeoJSON vector boundaries",
                "Binary change-mask raster tiles (PNG / Cloud-Optimized GeoTIFF)",
                "Automated PDF inspection summary report + webhook alerts",
            ]
        return [
            f"Standard recommended enterprise approach for {item.title}",
            f"Lightweight / low-cost automated configuration",
            f"Custom configuration (user specified)",
        ]
