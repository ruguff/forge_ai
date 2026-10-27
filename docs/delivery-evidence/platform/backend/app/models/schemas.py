"""
ProjectForge AI — Pydantic v2 Validation Schema Registry.

Every data contract used across the agent pipeline is defined here with
strict field-level validation so that upstream producers and downstream
consumers share a single source of truth.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ──────────────────────────────────────────────────────────────────────────────
# Intake question models
# ──────────────────────────────────────────────────────────────────────────────


class Question(BaseModel):
    """A single adaptive clarification question for the intake flow."""

    question_id: str
    question_text: str
    why_asked: str
    expected_answer_type: str = Field(
        ...,
        description="E.g. 'free_text', 'single_choice', 'multi_choice', 'numeric'",
    )


class IntakeClarifications(BaseModel):
    """Batch of adaptive follow-up questions produced by the Intake Agent."""

    questions: List[Question]



# ──────────────────────────────────────────────────────────────────────────────
# Enumerations
# ──────────────────────────────────────────────────────────────────────────────


class SeverityLevel(str, Enum):
    """Risk severity classification."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ProblemType(str, Enum):
    """AI/ML problem domain classification."""

    NONE = "NONE"
    CLASSICAL_ML = "CLASSICAL_ML"
    NLP_LLM = "NLP_LLM"
    COMPUTER_VISION = "COMPUTER_VISION"
    RECOMMENDER = "RECOMMENDER"
    TIME_SERIES = "TIME_SERIES"


class ProjectStatus(str, Enum):
    """Lifecycle status of a project inside the pipeline."""

    INTAKE = "INTAKE"
    ANALYZING_CORE = "ANALYZING_CORE"
    ANALYZING_ENGINEERING = "ANALYZING_ENGINEERING"
    ANALYZING_VERIFICATION = "ANALYZING_VERIFICATION"
    RESOLVING_CONFLICTS = "RESOLVING_CONFLICTS"
    ARCHITECTING = "ARCHITECTING"
    AWAITING_HUMAN_REVIEW = "AWAITING_HUMAN_REVIEW"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    CANCELLED = "CANCELLED"


# ──────────────────────────────────────────────────────────────────────────────
# Core building blocks
# ──────────────────────────────────────────────────────────────────────────────


class ConfidenceScore(BaseModel):
    """Quantified confidence with auditability metadata."""

    score: float = Field(..., ge=0.0, le=1.0)
    fact_references: List[str]
    unverified_assumptions: List[str]
    risk_penalty: float = Field(..., ge=0.0, le=0.4)
    justification: str


class TechDecision(BaseModel):
    """A single technology choice with full rationale and audit trail."""

    category: str
    selected: str
    version: Optional[str] = None
    why: str
    alternatives_rejected: Dict[str, str] = Field(
        ...,
        description=(
            "At least two distinct rejected alternatives for THIS decision, each mapped "
            "to a concise reason. These are evaluated options, not requested features."
        ),
        json_schema_extra={"minProperties": 2},
    )
    tradeoffs: List[str]
    failure_conditions: List[str]
    confidence: ConfidenceScore


# ──────────────────────────────────────────────────────────────────────────────
# Specification models
# ──────────────────────────────────────────────────────────────────────────────


class ProductSpecification(BaseModel):
    """Product-level requirements and scope definition."""

    problem_statement: str
    target_users: List[str]
    user_personas: List[Dict[str, str]]
    core_value_proposition: str
    functional_requirements: List[str]
    mvp_features: List[str] = Field(..., max_length=5)
    future_scope: List[str]
    non_goals: List[str] = Field(..., min_length=1)
    success_metrics: List[Dict[str, str]]
    product_risks: List[str]


class AIArchitectureSpecification(BaseModel):
    """AI/ML architecture specification produced by the AI Architect agent."""

    ai_required: bool
    necessity_justification: str
    problem_type: ProblemType
    problem_formulation: Optional[str] = None
    candidate_models: List[TechDecision] = []
    recommended_model: Optional[TechDecision] = None
    dataset_requirements: Optional[Dict[str, Any]] = None
    training_vs_api_strategy: Optional[str] = None
    inference_latency_sla_ms: Optional[int] = None
    evaluation_metrics: List[str] = []
    baseline_heuristic: Optional[str] = None
    compute_and_cost_estimation: Optional[Dict[str, str]] = None
    hallucination_and_drift_mitigation: List[str] = []


class EngineeringSpecification(BaseModel):
    """System-level engineering architecture."""

    system_architecture_pattern: str
    frontend_architecture: TechDecision
    backend_architecture: TechDecision
    database_primary: TechDecision
    database_cache: Optional[TechDecision] = None
    api_protocol: TechDecision
    async_processing: Optional[TechDecision] = None
    storage_strategy: TechDecision
    observability_stack: Dict[str, str]
    mermaid_diagram: str
    scalability_limits_and_bottlenecks: List[str]


class ViewStateSpecification(BaseModel):
    """UX state definitions for a single view / screen."""

    view_name: str
    loading_state: str
    empty_state: str
    error_state: str
    success_state: str


class UXSpecification(BaseModel):
    """User experience specification."""

    primary_user_journey: List[str]
    information_architecture: Dict[str, List[str]]
    view_states: List[ViewStateSpecification]
    accessibility_standards: List[str]
    responsive_breakpoints: Dict[str, str]


class SecurityThreat(BaseModel):
    """Individual STRIDE-categorised security threat."""

    threat_id: str
    stride_category: str
    threat_description: str
    severity: SeverityLevel
    impact: str
    likelihood: SeverityLevel
    mitigation_strategy: str
    priority: int = Field(..., ge=1, le=5)


class SecurityReport(BaseModel):
    """Full security analysis report."""

    authentication_mechanism: TechDecision
    authorization_model: str
    data_protection_at_rest: str
    data_protection_in_transit: str
    input_validation_rules: List[str]
    ai_threat_mitigations: List[str] = []
    threat_catalog: List[SecurityThreat]


class TestCase(BaseModel):
    __test__ = False
    """A single test case with requirement traceability."""

    test_id: str
    target_component: str
    category: str
    scenario: str
    expected_outcome: str
    traceable_requirement_id: str


class QASpecification(BaseModel):
    """Quality assurance specification and test plan."""

    test_pyramid_distribution: Dict[str, str]
    frameworks_and_tooling: List[TechDecision]
    critical_test_cases: List[TestCase]
    performance_load_thresholds: Dict[str, str]
    ai_model_validation_protocol: Optional[Dict[str, Any]] = None


class Conflict(BaseModel):
    """A detected inter-agent conflict and its arbitrated resolution."""

    conflict_id: str
    issue: str
    participating_agents: List[str]
    conflicting_recommendations: Dict[str, str]
    evaluation_criteria_scores: Dict[str, Dict[str, float]]
    arbitrated_resolution: str
    technical_justification: str
    compromise_penalties: List[str]
    confidence: float = Field(..., ge=0.0, le=1.0)


# ──────────────────────────────────────────────────────────────────────────────
# Top-level project state
# ──────────────────────────────────────────────────────────────────────────────


class ProjectState(BaseModel):
    """Complete snapshot of a project flowing through the agent pipeline."""

    project_id: str
    revision: int = 1
    status: ProjectStatus
    raw_idea: str
    intake_qa: Dict[str, str]
    product_spec: Optional[ProductSpecification] = None
    ai_spec: Optional[AIArchitectureSpecification] = None
    engineering_spec: Optional[EngineeringSpecification] = None
    ux_spec: Optional[UXSpecification] = None
    security_report: Optional[SecurityReport] = None
    qa_spec: Optional[QASpecification] = None
    detected_conflicts: List[Conflict] = []
    final_blueprint_markdown: Optional[str] = None
    audit_traceability_matrix: Dict[str, List[str]] = Field(
        default_factory=dict,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Structured Artifact Schemas & Evidence Engine Models
# ──────────────────────────────────────────────────────────────────────────────


class DecisionRecord(BaseModel):
    """Structured architectural decision record with evidence justification."""

    decision_id: str
    category: str  # e.g. 'DATABASE', 'API_PROTOCOL', 'ML_MODEL'
    selected_option: str
    rejected_alternatives: List[Dict[str, str]]  # [{'option': 'MongoDB', 'reason': 'Less suitable for relational transactions'}]
    evidence: List[str]
    facts: List[str] = Field(default_factory=list)
    inferences: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    confidence: float = Field(default=0.90, ge=0.0, le=1.0)


class RequirementType(str, Enum):
    """Categorization for extracted requirements."""

    EXPLICIT = "EXPLICIT"
    INFERRED = "INFERRED"
    ASSUMPTION = "ASSUMPTION"
    UNKNOWN = "UNKNOWN"


class RequirementSource(str, Enum):
    """Origin source of the requirement item."""

    USER = "USER"
    AGENT = "AGENT"
    INFERENCE = "INFERENCE"


class ExtractedRequirementItem(BaseModel):
    """A granular requirement item extracted across the 17 dimensions."""

    id: str
    dimension: str
    title: str
    description: str
    type: RequirementType
    source: RequirementSource
    confidence: float = Field(default=0.90, ge=0.0, le=1.0)
    evidence: str = ""


class ClarificationQuestion(BaseModel):
    """A targeted clarification question for material unknowns."""

    question_id: str
    unknown_item_id: Optional[str] = None
    question: str
    reason: str
    impact_if_unknown: str
    possible_options: List[str] = Field(default_factory=list)
    status: str = "PENDING"
    answer: Optional[str] = None


class ProjectUnderstandingOutput(BaseModel):
    """Structured 17-dimension extraction output from ProjectUnderstandingAgent."""

    project_name: str
    problem: ExtractedRequirementItem
    goal: ExtractedRequirementItem
    target_users: List[ExtractedRequirementItem] = Field(default_factory=list)
    user_journeys: List[ExtractedRequirementItem] = Field(default_factory=list)
    functional_requirements: List[ExtractedRequirementItem] = Field(default_factory=list)
    non_functional_requirements: List[ExtractedRequirementItem] = Field(default_factory=list)
    constraints: List[ExtractedRequirementItem] = Field(default_factory=list)
    technology_preferences: List[ExtractedRequirementItem] = Field(default_factory=list)
    expected_outputs: List[ExtractedRequirementItem] = Field(default_factory=list)
    non_goals: List[ExtractedRequirementItem] = Field(default_factory=list)
    assumptions: List[ExtractedRequirementItem] = Field(default_factory=list)
    unknowns: List[ExtractedRequirementItem] = Field(default_factory=list)
    ambiguities: List[ExtractedRequirementItem] = Field(default_factory=list)
    risks: List[ExtractedRequirementItem] = Field(default_factory=list)
    evidence: List[str] = Field(default_factory=list)
    confidence: float = Field(default=0.90, ge=0.0, le=1.0)


class RequirementEngineOutput(BaseModel):
    """Evaluation result of unknowns by RequirementEngine."""

    evaluated_unknowns_count: int
    can_continue_autonomously: bool
    clarification_questions: List[ClarificationQuestion] = Field(default_factory=list)
    inferred_resolutions: List[Dict[str, Any]] = Field(default_factory=list)
    delegated_to_agents: List[Dict[str, Any]] = Field(default_factory=list)


class ProjectContext(BaseModel):
    """Versioned single source of truth for the autonomous engineering system."""

    project_id: str
    version: int = 1
    raw_request: str
    raw_idea: Optional[str] = None
    project_name: str = "Untitled Project"
    problem_statement: str = ""
    goals: List[str] = Field(default_factory=list)
    target_users: List[str] = Field(default_factory=list)
    user_journeys: List[str] = Field(default_factory=list)
    requirements: List[ExtractedRequirementItem] = Field(default_factory=list)
    assumptions: List[ExtractedRequirementItem] = Field(default_factory=list)
    unknowns: List[ExtractedRequirementItem] = Field(default_factory=list)
    constraints: List[ExtractedRequirementItem] = Field(default_factory=list)
    clarification_questions: List[ClarificationQuestion] = Field(default_factory=list)
    decisions: List[DecisionRecord] = Field(default_factory=list)
    agent_outputs: Dict[str, Any] = Field(default_factory=dict)
    conflicts: List[Conflict] = Field(default_factory=list)
    architecture: Optional[str] = None
    build_spec: Optional[Dict[str, Any]] = None
    execution_state: str = "INITIALIZED"
    mode: str = "AUTONOMOUS"

    # Backward compatibility helpers
    intake_answers: Dict[str, str] = Field(default_factory=dict)
    user_constraints: List[str] = Field(default_factory=list)
    budget_limit_usd: float = Field(default=200.0)
    target_sla_ms: float = Field(default=100.0)

    def model_post_init(self, __context: Any) -> None:
        if not self.raw_idea and self.raw_request:
            self.raw_idea = self.raw_request
        elif not self.raw_request and self.raw_idea:
            self.raw_request = self.raw_idea


class BuildPlan(BaseModel):
    """Post-synthesis build specification provided to coding agent."""

    build_id: str
    project_id: str
    architecture_version: str = "1.0.0"
    target_directory: str = "./workspace"
    modules_to_create: List[Dict[str, Any]]  # [{'path': 'backend/main.py', 'purpose': 'FastAPI entrypoint'}]
    key_dependencies: List[str]
    acceptance_tests: List[str]
    status: str = "APPROVED"


class TestPlan(BaseModel):
    """Execution strategy for automated QA testing."""

    test_plan_id: str
    project_id: str
    unit_test_cases: List[Dict[str, Any]]
    integration_test_cases: List[Dict[str, Any]]
    e2e_test_cases: List[Dict[str, Any]]
    performance_benchmarks: Dict[str, str]


class EvaluationResult(BaseModel):
    """Internal quantitative evaluation score metrics for agent executions."""

    evaluation_id: str
    project_id: str
    agent_id: str
    completeness: float = Field(..., ge=0.0, le=1.0)
    correctness: float = Field(..., ge=0.0, le=1.0)
    consistency: float = Field(..., ge=0.0, le=1.0)
    evidence_quality: float = Field(..., ge=0.0, le=1.0)
    requirement_coverage: float = Field(..., ge=0.0, le=1.0)
    constraint_compliance: float = Field(..., ge=0.0, le=1.0)
    specificity: float = Field(..., ge=0.0, le=1.0)
    overall_score: float = Field(..., ge=0.0, le=1.0)
    score_label: str = "INTERNAL EVALUATION SCORE"

