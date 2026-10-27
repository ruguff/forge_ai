"""
ProjectForge AI — Machine-Readable Build Specification Models.

Defines the exact Pydantic v2 data contract for `.projectforge/build_spec.json`.
Represents the bridge between high-level architectural planning and
low-level software execution.
"""

from __future__ import annotations

from enum import Enum
import re
from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, Field
from app.execution.spec.commerce_contract import CommerceContract, RelationalContract
from app.execution.spec.catalogue_contract import CatalogueContract
from app.execution.spec.identity_contract import IdentityContract
from app.execution.spec.order_contract import OrderContract
from app.execution.spec.payment_contract import PaymentSimulationContract
from app.execution.spec.razorpay_contract import RazorpayTestContract


class RequirementSourceType(str, Enum):
    """Origin of a requirement or constraint."""
    USER = "USER"
    AGENT = "AGENT"
    INFERRED = "INFERRED"


class ProjectType(str, Enum):
    """Class of software application being built."""
    FULLSTACK_WEB = "FULLSTACK_WEB"
    BACKEND_API = "BACKEND_API"
    FRONTEND_SPA = "FRONTEND_SPA"
    CLI_TOOL = "CLI_TOOL"
    DATA_PIPELINE = "DATA_PIPELINE"


class BuildRequirementItem(BaseModel):
    """Atomic requirement with stable ID and explicit audit provenance."""
    id: str = Field(..., description="Stable ID e.g. FR-001, NFR-001, SEC-001, TEST-001")
    title: str
    description: str
    dimension: str = Field("functional", description="Architectural dimension")
    source: RequirementSourceType = Field(..., description="USER, AGENT, or INFERRED")
    confidence: float = Field(1.0, ge=0.0, le=1.0)
    traceability_path: Optional[List[str]] = Field(default_factory=list)


class TechStackSelection(BaseModel):
    """Concrete technology choices validated by the compiler."""
    frontend_framework: str = Field("React", description="Frontend framework (React, Vue, None)")
    frontend_language: str = Field("TypeScript", description="TypeScript or JavaScript")
    frontend_styling: str = Field("TailwindCSS", description="Styling solution")
    backend_framework: str = Field("FastAPI", description="FastAPI, Express, Django, etc.")
    backend_language: str = Field("Python 3.11", description="Backend language runtime")
    primary_database: str = Field("SQLite", description="SQLite, PostgreSQL, MongoDB, etc.")
    cache_broker: Optional[str] = Field(None, description="Redis, In-Memory, etc.")
    auth_provider: str = Field("JWT", description="JWT, OAuth2, Session, None")


class DatabaseFieldDef(BaseModel):
    """Column / attribute schema."""
    name: str
    data_type: str
    is_primary_key: bool = False
    is_nullable: bool = False
    is_unique: bool = False
    default_value: Optional[str] = None


class DatabaseEntityDef(BaseModel):
    """Database model / table schema definition."""
    entity_name: str
    table_name: str
    fields: List[DatabaseFieldDef] = Field(default_factory=list)
    relationships: List[str] = Field(default_factory=list)


class APIEndpointDef(BaseModel):
    """HTTP/REST/WebSocket route contract."""
    endpoint_id: str
    method: str = Field(..., description="GET, POST, PUT, DELETE, WS")
    path: str
    description: str
    request_body_schema: Optional[Dict[str, Any]] = None
    response_schema: Optional[Dict[str, Any]] = None
    auth_required: bool = True
    traceable_requirements: List[str] = Field(default_factory=list)


class UIComponentDef(BaseModel):
    """Frontend view, screen, or modular component."""
    component_id: str
    name: str
    file_path: str
    type: str = Field("page", description="page, component, layout, modal")
    props: Optional[Dict[str, str]] = None
    description: str


class DependencyDef(BaseModel):
    """Pinned library or package dependency."""
    package_name: str
    version_spec: str
    target_env: str = Field("all", description="backend, frontend, dev, test")


class TargetFileDef(BaseModel):
    """Specification of an exact file to be created in the repository."""
    file_path: str = Field(..., description="Relative path from project root")
    description: str
    target_module: str
    is_test_file: bool = False
    dependencies: List[str] = Field(default_factory=list)
    traceable_requirements: List[str] = Field(default_factory=list)


class TestRequirementDef(BaseModel):
    """Test assertions and QA verification targets."""
    test_id: str = Field(..., description="e.g. TEST-001")
    test_type: str = Field("unit", description="unit, integration, e2e, sla")
    target_file: str
    scenario: str
    expected_outcome: str
    traceable_requirements: List[str] = Field(default_factory=list)


class ArchitecturalDecision(BaseModel):
    """Key ADR decisions affecting code structure."""
    decision_id: str
    category: str
    chosen_solution: str
    rejected_alternatives: List[str] = Field(default_factory=list)
    rationale: str


class BuildSpecStatus(str, Enum):
    """Status of Build Spec compilation."""
    COMPILED = "COMPILED"
    BLOCKED = "BLOCKED"
    VALIDATED = "VALIDATED"


class UIContract(BaseModel):
    """Stable selectors owned by the platform, not inferred from assertions."""
    version: Literal[1] = 1
    namespace: str = Field(default='records', pattern=r'^[a-z][a-z0-9-]{0,40}$')

    def selector(self, control: str, record_id: int | None = None) -> str:
        allowed = {'create', 'save', 'list', 'row', 'edit', 'delete', 'error', 'loading'}
        if control not in allowed and not re.fullmatch(r'field-[a-zA-Z_][a-zA-Z0-9_]*', control):
            raise ValueError('Unknown UI control')
        selector = f'[data-testid="{self.namespace}-{control}"]'
        return selector if record_id is None else selector + f'[data-record-id="{int(record_id)}"]'


class BuildSpec(BaseModel):
    """
    Complete Machine-Readable Build Specification.
    Single source of truth for the Task Graph and Coding Orchestrator.
    """
    project_id: str
    project_name: str
    project_type: ProjectType = ProjectType.FULLSTACK_WEB
    status: BuildSpecStatus = BuildSpecStatus.COMPILED
    version: int = 1
    generation_mode: str = "TEMPLATE"
    source_generation_strategy: str = 'MODEL_CODE'
    acceptance_checks: List[Dict[str, Any]] = Field(default_factory=list)
    browser_checks: List[Dict[str, Any]] = Field(default_factory=list)
    ui_contract: Optional[UIContract] = None
    commerce_contract: Optional[CommerceContract] = None
    relational_contract: Optional[RelationalContract] = None
    catalogue_contract: Optional[CatalogueContract] = None
    identity_contract: Optional[IdentityContract] = None
    order_contract: Optional[OrderContract] = None
    razorpay_test_contract: Optional[RazorpayTestContract] = None
    payment_simulation_contract: Optional[PaymentSimulationContract] = None

    # Requirements & Traceability
    requirements: List[BuildRequirementItem] = Field(default_factory=list)
    constraints: List[str] = Field(default_factory=list)
    assumptions: List[BuildRequirementItem] = Field(default_factory=list)

    # Core Architecture Specs
    tech_stack: TechStackSelection = Field(default_factory=TechStackSelection)
    database_entities: List[DatabaseEntityDef] = Field(default_factory=list)
    api_endpoints: List[APIEndpointDef] = Field(default_factory=list)
    ui_components: List[UIComponentDef] = Field(default_factory=list)
    environment_variables: Dict[str, str] = Field(default_factory=dict)
    dependencies: List[DependencyDef] = Field(default_factory=list)

    # Physical File Tree & Modules Required
    files_to_create: List[TargetFileDef] = Field(default_factory=list)

    # QA & Security
    test_requirements: List[TestRequirementDef] = Field(default_factory=list)
    security_requirements: List[str] = Field(default_factory=list)
    deployment_requirements: List[str] = Field(default_factory=list)

    # Governance
    decisions: List[ArchitecturalDecision] = Field(default_factory=list)
    overall_confidence: float = Field(0.95, ge=0.0, le=1.0)
    blocked_reasons: Optional[List[str]] = None
