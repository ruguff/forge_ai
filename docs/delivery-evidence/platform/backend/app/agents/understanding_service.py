"""
ProjectForge AI — Project Understanding Service.

Runs ProjectUnderstandingAgent through the configured cloud or local provider,
with a labelled heuristic fallback when model extraction is unavailable.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Callable, Dict, List, Optional

from app.agents.project_understanding_agent import ProjectUnderstandingAgent
from app.models.schemas import (
    ExtractedRequirementItem,
    ProjectUnderstandingOutput,
    RequirementSource,
    RequirementType,
)

logger = logging.getLogger(__name__)


def generate_heuristic_understanding(raw_idea: str) -> ProjectUnderstandingOutput:
    """Generate a structured, schema-compliant 17-dimension specification from raw natural language.

    Used when offline or as an empirical baseline.
    """
    clean_idea = raw_idea.strip()
    idea_lower = clean_idea.lower()

    # Extract clean title from prompt
    named_match = re.search(r'(?:called|named)\s+["\']?([^"\',.!?]+)["\']?', clean_idea, re.IGNORECASE)
    quoted_match = re.search(r'["\']([^"\']{2,40})["\']', clean_idea)

    if named_match:
        extracted_name = named_match.group(1).strip()
        title = f"{extracted_name.title()} Platform"
    elif quoted_match:
        extracted_name = quoted_match.group(1).strip()
        title = f"{extracted_name.title()} Platform"
    elif "satellite" in idea_lower:
        title = "Satellite Geospatial Change Detection AI"
    elif "review" in idea_lower:
        title = "Customer Review Intelligence Platform"
    elif any(k in idea_lower for k in ["cake", "bakery"]):
        title = "Cake and Joy Artisan Bakery Platform"
    else:
        words = clean_idea.split()
        first_few = " ".join(words[:5]) if len(words) >= 5 else clean_idea
        title = f"{first_few.title()} Platform"

    # Domain flags
    is_bakery_ecommerce = any(k in idea_lower for k in ["cake", "bakery", "pastry", "confectionery", "dessert", "food ordering"])
    is_satellite = any(k in idea_lower for k in ["satellite", "geospatial", "remote sensing", "imagery", "gis"])

    if is_bakery_ecommerce:
        problem_text = (
            f"Traditional manual cake ordering via phone and messaging creates order errors, "
            f"scheduling bottlenecks, and lacks real-time custom cake visualization for: {clean_idea}."
        )
        goal_text = (
            f"Provide an interactive e-commerce platform with a visual custom cake builder, "
            f"real-time delivery scheduling, and automated kitchen fulfillment tracking for {title}."
        )
        reqs = [
            ExtractedRequirementItem(
                id="REQ-F-001",
                dimension="functional_requirements",
                title="Artisan Cake Catalog & Allergen Filter",
                description="Browse artisan cake collections with rich photography, dietary labels (gluten-free, vegan), and price tiers.",
                type=RequirementType.EXPLICIT,
                source=RequirementSource.USER,
                confidence=0.95,
                evidence=clean_idea[:100],
            ),
            ExtractedRequirementItem(
                id="REQ-F-002",
                dimension="functional_requirements",
                title="Interactive Custom Cake Builder",
                description="Select cake size, number of tiers, sponge flavor, fillings, frosting styles, and custom piped message.",
                type=RequirementType.INFERRED,
                source=RequirementSource.INFERENCE,
                confidence=0.92,
                evidence="Inferred from bakery custom cake ordering workflow.",
            ),
            ExtractedRequirementItem(
                id="REQ-F-003",
                dimension="functional_requirements",
                title="Delivery Slot Scheduling & Local Radius Check",
                description="Select delivery or pickup date and 2-hour time window with postal code delivery radius verification.",
                type=RequirementType.INFERRED,
                source=RequirementSource.INFERENCE,
                confidence=0.90,
                evidence="Inferred from perishable bakery fulfillment constraints.",
            ),
            ExtractedRequirementItem(
                id="REQ-F-004",
                dimension="functional_requirements",
                title="Cart & Stripe Payment Gateway",
                description="Secure payment processing with automated customer email confirmation and receipt generation.",
                type=RequirementType.INFERRED,
                source=RequirementSource.INFERENCE,
                confidence=0.92,
                evidence="Inferred from e-commerce checkout requirements.",
            ),
            ExtractedRequirementItem(
                id="REQ-F-005",
                dimension="functional_requirements",
                title="Kitchen Order Fulfillment Queue",
                description="Real-time order kanban dashboard for bakery staff showing baking deadlines, custom specs, and dispatch status.",
                type=RequirementType.INFERRED,
                source=RequirementSource.INFERENCE,
                confidence=0.88,
                evidence="Inferred from commercial bakery operations.",
            ),
        ]
        target_users = [
            ExtractedRequirementItem(
                id="USR-001",
                dimension="target_users",
                title="Online Cake Shoppers & Party Hosts",
                description="Customers ordering birthday, wedding, and celebration cakes online.",
                type=RequirementType.INFERRED,
                source=RequirementSource.INFERENCE,
                confidence=0.95,
                evidence="Primary consumer persona for bakery website.",
            ),
            ExtractedRequirementItem(
                id="USR-002",
                dimension="target_users",
                title="Bakery Kitchen Staff & Cake Decorators",
                description="Pastry chefs and decorators viewing custom cake specifications and delivery schedules.",
                type=RequirementType.INFERRED,
                source=RequirementSource.INFERENCE,
                confidence=0.90,
                evidence="Operations persona managing cake production.",
            ),
        ]
        user_journeys = [
            ExtractedRequirementItem(
                id="JRN-001",
                dimension="user_journeys",
                title="Customer Order-to-Delivery Flow",
                description="Customer browses catalog -> Customizes cake layers and message -> Selects delivery date/slot -> Completes Stripe payment -> Receives live SMS/email status updates.",
                type=RequirementType.INFERRED,
                source=RequirementSource.INFERENCE,
                confidence=0.92,
                evidence="Standard e-commerce bakery customer journey.",
            )
        ]
        unknowns = [
            ExtractedRequirementItem(
                id="UNK-001",
                dimension="unknowns",
                title="Fulfillment Method: Local Delivery vs In-Store Pickup",
                description="Whether the bakery supports local door-to-door courier delivery, scheduled in-store pickup, or both.",
                type=RequirementType.UNKNOWN,
                source=RequirementSource.AGENT,
                confidence=0.70,
                evidence="Prompt does not state whether delivery or in-store pickup is required.",
            )
        ]
        non_goals = [
            ExtractedRequirementItem(
                id="NON-001",
                dimension="non_goals",
                title="Long-Distance Frozen Freight Shipping",
                description="Phase 1 excludes international or long-distance frozen courier shipping.",
                type=RequirementType.INFERRED,
                source=RequirementSource.AGENT,
                confidence=0.95,
                evidence="Scope containment for local bakery operations.",
            )
        ]
    elif is_satellite:
        problem_text = f"Manual inspection of satellite imagery for road changes is slow and subjective for: {clean_idea}."
        goal_text = f"Automate bi-temporal satellite imagery comparison and road infrastructure change detection for: {clean_idea}."
        reqs = [
            ExtractedRequirementItem(
                id="REQ-F-001",
                dimension="functional_requirements",
                title="Satellite Tile Ingestion & Orthorectification",
                description="Ingest pre/post GeoTIFF satellite tiles with geospatial coordinate alignment.",
                type=RequirementType.EXPLICIT,
                source=RequirementSource.USER,
                confidence=0.95,
                evidence=clean_idea[:100],
            ),
            ExtractedRequirementItem(
                id="REQ-F-002",
                dimension="functional_requirements",
                title="Bi-Temporal Change Segmentation Engine",
                description="Execute deep learning segmentation to highlight new, modified, or demolished road segments.",
                type=RequirementType.INFERRED,
                source=RequirementSource.INFERENCE,
                confidence=0.92,
                evidence="Inferred from satellite road change detection objective.",
            ),
        ]
        target_users = [
            ExtractedRequirementItem(
                id="USR-001",
                dimension="target_users",
                title="GIS Analysts & Urban Planners",
                description="Specialists monitoring infrastructure changes and road development.",
                type=RequirementType.INFERRED,
                source=RequirementSource.INFERENCE,
                confidence=0.90,
                evidence="Inferred from geospatial domain.",
            )
        ]
        user_journeys = [
            ExtractedRequirementItem(
                id="JRN-001",
                dimension="user_journeys",
                title="Imagery Analysis & Vector Export Journey",
                description="User uploads pre/post satellite rasters -> Model computes change mask -> User reviews vector overlays -> Exports GeoJSON report.",
                type=RequirementType.INFERRED,
                source=RequirementSource.INFERENCE,
                confidence=0.90,
                evidence="Standard GIS workflow.",
            )
        ]
        unknowns = [
            ExtractedRequirementItem(
                id="UNK-001",
                dimension="unknowns",
                title="Satellite Tile Resolution & Provider Format",
                description="Target spatial resolution (e.g. 30cm vs 1m) and provider API integration (Sentinel, Planet, Maxar).",
                type=RequirementType.UNKNOWN,
                source=RequirementSource.AGENT,
                confidence=0.65,
                evidence="Satellite imagery provider not specified.",
            )
        ]
        non_goals = [
            ExtractedRequirementItem(
                id="NON-001",
                dimension="non_goals",
                title="Real-Time Video Feed Streaming",
                description="Phase 1 excludes real-time drone full-motion video feeds.",
                type=RequirementType.INFERRED,
                source=RequirementSource.AGENT,
                confidence=0.95,
                evidence="Scope containment.",
            )
        ]
    else:
        problem_text = f"Manual execution and delayed inspection for: {clean_idea}."
        goal_text = f"Automate and optimize software workflows for: {clean_idea}."
        reqs = [
            ExtractedRequirementItem(
                id="REQ-F-001",
                dimension="functional_requirements",
                title="Core Processing & Transformation Pipeline",
                description=f"Ingest input parameters and execute primary computation for {clean_idea}.",
                type=RequirementType.EXPLICIT,
                source=RequirementSource.USER,
                confidence=0.95,
                evidence=clean_idea[:100],
            ),
            ExtractedRequirementItem(
                id="REQ-F-002",
                dimension="functional_requirements",
                title="Automated Validation & Result Export",
                description="Validate processing outputs against schema benchmarks and provide export interfaces.",
                type=RequirementType.INFERRED,
                source=RequirementSource.INFERENCE,
                confidence=0.88,
                evidence="Inferred from standard software delivery requirements.",
            ),
        ]
        target_users = [
            ExtractedRequirementItem(
                id="USR-001",
                dimension="target_users",
                title="System Operators & Domain Specialists",
                description="Users responsible for monitoring and configuring the autonomous pipeline.",
                type=RequirementType.INFERRED,
                source=RequirementSource.INFERENCE,
                confidence=0.85,
                evidence="Inferred from autonomous system context.",
            )
        ]
        user_journeys = [
            ExtractedRequirementItem(
                id="JRN-001",
                dimension="user_journeys",
                title="Input Ingestion, Processing, and Inspection",
                description="User submits input prompt, system processes specifications, and renders output.",
                type=RequirementType.INFERRED,
                source=RequirementSource.INFERENCE,
                confidence=0.85,
                evidence="Standard end-to-end journey.",
            )
        ]
        unknowns = [
            ExtractedRequirementItem(
                id="UNK-001",
                dimension="unknowns",
                title="Real-Time Streaming vs Batch Ingestion",
                description="Whether data processing must be real-time streaming or scheduled batch ingestion.",
                type=RequirementType.UNKNOWN,
                source=RequirementSource.AGENT,
                confidence=0.65,
                evidence="Ingestion cadence not explicitly defined in prompt.",
            )
        ]
        non_goals = [
            ExtractedRequirementItem(
                id="NON-001",
                dimension="non_goals",
                title="Legacy Monolithic Support",
                description="System explicitly will NOT support legacy synchronous batch architectures.",
                type=RequirementType.INFERRED,
                source=RequirementSource.AGENT,
                confidence=0.95,
                evidence="Scope containment rule.",
            )
        ]

    # Shared engineering standards
    nfrs = [
        ExtractedRequirementItem(
            id="REQ-NF-001",
            dimension="non_functional_requirements",
            title="System Response Latency & Availability",
            description="Ensure 99.9% availability and API endpoint response time under 200ms.",
            type=RequirementType.INFERRED,
            source=RequirementSource.INFERENCE,
            confidence=0.85,
            evidence="Standard engineering SLA threshold.",
        )
    ]
    constraints = [
        ExtractedRequirementItem(
            id="CON-001",
            dimension="constraints",
            title="Deployment & Security Boundary",
            description="Must execute within containerized environment with TLS 1.3 and zero-trust networking.",
            type=RequirementType.INFERRED,
            source=RequirementSource.INFERENCE,
            confidence=0.90,
            evidence="Modern microservices security baseline.",
        )
    ]
    tech_prefs = [
        ExtractedRequirementItem(
            id="TECH-001",
            dimension="technology_preferences",
            title="Modern API & Storage Architecture",
            description="Asynchronous backend API (FastAPI) with ACID-compliant storage engine (PostgreSQL).",
            type=RequirementType.INFERRED,
            source=RequirementSource.INFERENCE,
            confidence=0.85,
            evidence="Architecture best practices.",
        )
    ]
    outputs = [
        ExtractedRequirementItem(
            id="OUT-001",
            dimension="expected_outputs",
            title="Structured Machine-Readable Output",
            description="REST API JSON payloads accompanied by telemetry metrics and interactive client interface.",
            type=RequirementType.INFERRED,
            source=RequirementSource.INFERENCE,
            confidence=0.90,
            evidence="Primary expected delivery artifact.",
        )
    ]
    assumptions = [
        ExtractedRequirementItem(
            id="ASM-001",
            dimension="assumptions",
            title="Standard Data Formats",
            description="Assumes modern web standards (HTTPS, JSON, WebSocket/SSE) across client and server.",
            type=RequirementType.ASSUMPTION,
            source=RequirementSource.AGENT,
            confidence=0.80,
            evidence="Standard operational assumption.",
        )
    ]
    ambiguities = [
        ExtractedRequirementItem(
            id="AMB-001",
            dimension="ambiguities",
            title="Primary Notification Channel",
            description="Whether order/pipeline updates should prioritize email notifications, SMS, or web push.",
            type=RequirementType.UNKNOWN,
            source=RequirementSource.AGENT,
            confidence=0.60,
            evidence="Notification channels not specified in initial prompt.",
        )
    ]
    risks = [
        ExtractedRequirementItem(
            id="RSK-001",
            dimension="risks",
            title="High-Concurrency Peak Load",
            description="Peak holiday order surges or heavy traffic bursts may degrade checkout latency without connection pooling.",
            type=RequirementType.INFERRED,
            source=RequirementSource.AGENT,
            confidence=0.80,
            evidence="Standard distributed e-commerce risk.",
        )
    ]

    output = ProjectUnderstandingOutput(
        project_name=title,
        problem=ExtractedRequirementItem(
            id="PROB-001",
            dimension="problem",
            title="Operational Challenge",
            description=problem_text,
            type=RequirementType.EXPLICIT,
            source=RequirementSource.USER,
            confidence=0.95,
            evidence=clean_idea[:100],
        ),
        goal=ExtractedRequirementItem(
            id="GOAL-001",
            dimension="goal",
            title="Strategic Objective",
            description=goal_text,
            type=RequirementType.EXPLICIT,
            source=RequirementSource.USER,
            confidence=0.95,
            evidence=clean_idea[:100],
        ),
        target_users=target_users,
        user_journeys=user_journeys,
        functional_requirements=reqs,
        non_functional_requirements=nfrs,
        constraints=constraints,
        technology_preferences=tech_prefs,
        expected_outputs=outputs,
        non_goals=non_goals,
        assumptions=assumptions,
        unknowns=unknowns,
        ambiguities=ambiguities,
        risks=risks,
        evidence=[clean_idea[:120]],
        confidence=0.0,
    )
    # Offline suggestions are not extracted user facts. Preserve the raw request
    # and mark generated domain details as unverified proposals.
    output.problem.description = clean_idea
    output.goal.description = clean_idea
    for name in ("target_users", "user_journeys", "functional_requirements", "non_functional_requirements",
                 "constraints", "technology_preferences", "expected_outputs", "non_goals", "risks"):
        for item in getattr(output, name):
            if item.type == RequirementType.EXPLICIT or item.source == RequirementSource.USER:
                item.type = RequirementType.INFERRED
                item.source = RequirementSource.INFERENCE
                item.confidence = 0.0
                item.evidence = "Offline rule-based suggestion; not explicitly requested or verified."
    output.evidence.append("UNDERSTANDING_MODE=HEURISTIC; suggestions require specialist review")
    if not is_satellite and not is_bakery_ecommerce and not any(word in idea_lower for word in ("ingestion", "streaming", "batch", "pipeline")):
        # Do not invent a streaming/batch decision for an ordinary website.
        output.unknowns = []
    return output


async def execute_understanding(raw_idea: str) -> ProjectUnderstandingOutput:
    """Execute project understanding with fallback to heuristic generator if LLM is unavailable."""
    try:
        # The shared adapter selects LLM_PROVIDER and validates its own settings.
        # Local inference must not depend on a cloud API key or SDK import.
        from app.agents.model_client import GeminiModelClient
        client = GeminiModelClient()
        agent = ProjectUnderstandingAgent(llm_client=client.generate)
        result = await agent.analyze_project_idea(raw_idea)
        if result.success and isinstance(result.output, ProjectUnderstandingOutput):
            result.output.evidence.append("UNDERSTANDING_MODE=MODEL")
            return result.output
        logger.warning("Model understanding failed validation; using labelled heuristic suggestions.")
    except Exception as exc:
        logger.warning("Configured model extraction unavailable; falling back to heuristic understanding: %s", exc)

    # Fallback to domain-aware heuristic generator
    return generate_heuristic_understanding(raw_idea)
