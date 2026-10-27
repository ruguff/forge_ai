from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class AgentContract(BaseModel):
    """
    Formal contract definition enforced for every specialized AI agent in ProjectForge AI.
    Agents operate as contract-bound autonomous engineering entities rather than unstructured chatbots.
    """

    id: str = Field(..., description="Unique canonical identifier for the agent (e.g. 'product_manager')")
    agent_id: Optional[str] = Field(default=None, description="Explicit agent_id contract property")
    name: str = Field(..., description="Human-readable name of the agent character/persona")
    role: str = Field(..., description="Formal role title (e.g. 'Principal Technical Product Manager')")
    objective: str = Field(..., description="Primary objective and responsibility of the agent")
    mission: Optional[str] = Field(default=None, description="Formal mission statement of the agent")
    responsibilities: List[str] = Field(default_factory=list, description="Explicit responsibilities executed by the agent")
    inputs: List[str] = Field(default_factory=list, description="Required input artifact keys or context subsets")
    input_schema: str = Field(default="ProjectContext", description="Name of required input schema")
    outputs: List[str] = Field(default_factory=list, description="Produced structured artifact schemas")
    output_schema: str = Field(default="BaseModel", description="Name of structured output schema")
    dependencies: List[str] = Field(default_factory=list, description="Prerequisite agent IDs or artifact IDs")
    tools: List[str] = Field(default_factory=list, description="Available tool invocations (linting, calibration, web, sandbox)")
    constraints: List[str] = Field(default_factory=list, description="Negative constraints and architectural rules")
    evidence_requirements: List[str] = Field(default_factory=list, description="Required evidence justification standards")
    evidence: List[str] = Field(default_factory=list, description="Grounded facts and source references")
    confidence: float = Field(default=0.90, ge=0.0, le=1.0, description="Empirically calibrated confidence score")
    assumptions: List[str] = Field(default_factory=list, description="Explicit unverified assumptions made by the agent")
    decisions: List[str] = Field(default_factory=list, description="Explicit technical and architectural decisions made")
    alternatives: List[Dict[str, str]] = Field(default_factory=list, description="Rejected alternative choices with trade-offs")
    risks: List[str] = Field(default_factory=list, description="Identified failure modes and risks")
    acceptance_criteria: List[str] = Field(default_factory=list, description="Validation assertions for contract completion")
    failure_conditions: List[str] = Field(default_factory=list, description="Explicit failure triggers and retry thresholds")
    status: str = Field(default="IDLE", description="Current execution status (IDLE, WORKING, DISCUSSING, COMPLETED, ERROR)")
    version: str = Field(default="1.0.0", description="Contract specification version")

    def model_post_init(self, __context: Any) -> None:
        if not self.agent_id:
            self.agent_id = self.id
        if not self.mission:
            self.mission = self.objective

    def validate_inputs(self, available_keys: List[str]) -> bool:
        """Validates that all required inputs exist in the current project context."""
        return all(key in available_keys for key in self.inputs)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the contract to a dictionary representation."""
        return self.model_dump()
