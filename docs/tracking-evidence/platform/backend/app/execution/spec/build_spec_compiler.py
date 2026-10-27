"""
ProjectForge AI — Build Specification Compiler.

Transforms human-readable architectural artifacts and versioned ProjectContext
into the strict, machine-readable BuildSpec (.projectforge/build_spec.json).
Enforces requirement source provenance (USER, AGENT, INFERRED) and validates
that no critical architectural decisions are missing before code execution begins.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.models.schemas import ProjectContext, ProjectState
from app.execution.spec.build_spec_models import (
    APIEndpointDef,
    ArchitecturalDecision,
    BuildRequirementItem,
    BuildSpec,
    BuildSpecStatus,
    DatabaseEntityDef,
    DatabaseFieldDef,
    DependencyDef,
    ProjectType,
    RequirementSourceType,
    TargetFileDef,
    TechStackSelection,
    TestRequirementDef,
    UIComponentDef,
)

logger = logging.getLogger(__name__)


class BuildSpecCompiler:
    """Deterministic compiler from architectural planning state to execution specification."""

    async def compile_model(self, context, state, llm_client):
        from app.execution.spec.model_compiler import compile_model
        return await compile_model(context, state, llm_client)

    def compile(
        self,
        context: Optional[ProjectContext] = None,
        state: Optional[ProjectState] = None,
        override_project_type: Optional[ProjectType] = None,
    ) -> BuildSpec:
        """
        Compile ProjectContext / ProjectState into a verified BuildSpec.
        Returns BuildSpec with status=BLOCKED if critical requirements are unresolved.
        """
        project_id = context.project_id if context else (state.project_id if state else "PROJ-UNKNOWN")
        raw_text = context.raw_request if context else (state.raw_idea if state else "")
        project_name = (
            context.project_name if context and context.project_name
            else self._infer_project_name(raw_text)
        )

        blocked_reasons: List[str] = []

        # 1. Check for blocking conditions
        if not raw_text.strip():
            blocked_reasons.append("EMPTY_PROJECT_IDEA: Raw user idea is empty.")
        if context and any(q.status == "PENDING" for q in context.clarification_questions):
            blocked_reasons.append("PENDING_CLARIFICATION: Resolve material unknowns first.")
        if context and context.conflicts:
            blocked_reasons.append("UNRESOLVED_CONFLICT: Review specialist contradictions first.")

        # 2. Extract and tag requirements with provenance (USER, AGENT, INFERRED)
        requirements: List[BuildRequirementItem] = []
        assumptions: List[BuildRequirementItem] = []

        if context and context.requirements:
            for idx, r in enumerate(context.requirements, 1):
                src = RequirementSourceType.INFERRED
                if hasattr(r, "source"):
                    if r.source.value == "USER":
                        src = RequirementSourceType.USER
                    elif r.source.value == "AGENT":
                        src = RequirementSourceType.AGENT
                    else:
                        src = RequirementSourceType.INFERRED

                req_item = BuildRequirementItem(
                    id=r.id or f"FR-{idx:03d}",
                    title=r.title,
                    description=r.description,
                    dimension=r.dimension or "functional",
                    source=src,
                    confidence=getattr(r, "confidence", 0.95),
                    traceability_path=[f"Extracted from {src.value} specification", f"Dimension: {r.dimension}"],
                )
                if src == RequirementSourceType.INFERRED:
                    assumptions.append(req_item)
                else:
                    requirements.append(req_item)
        else:
            # Baseline functional requirements from state/idea
            requirements.append(
                BuildRequirementItem(
                    id="FR-001",
                    title="Core System Entrypoint",
                    description=f"Primary workflow implementation for: {raw_text[:80]}",
                    dimension="functional",
                    source=RequirementSourceType.USER,
                    confidence=1.0,
                    traceability_path=["Raw user input prompt"],
                )
            )

        # 3. Determine Project Type
        lower_idea = raw_text.lower()
        if override_project_type:
            proj_type = override_project_type
        elif "api" in lower_idea and "frontend" not in lower_idea and "web" not in lower_idea:
            proj_type = ProjectType.BACKEND_API
        elif "cli" in lower_idea or "command line" in lower_idea:
            proj_type = ProjectType.CLI_TOOL
        else:
            proj_type = override_project_type or ProjectType.FULLSTACK_WEB

        # 4. Tech Stack Selection
        tech_stack = TechStackSelection(
            frontend_framework="React",
            frontend_language="TypeScript",
            frontend_styling="TailwindCSS",
            backend_framework="FastAPI",
            backend_language="Python 3.11",
            primary_database="SQLite" if "sqlite" in lower_idea or "simple" in lower_idea else "PostgreSQL",
            cache_broker="Redis" if "realtime" in lower_idea or "streaming" in lower_idea else None,
            auth_provider="JWT",
        )

        # 5. Database Entities
        entities: List[DatabaseEntityDef] = [
            DatabaseEntityDef(
                entity_name="Item",
                table_name="items",
                fields=[
                    DatabaseFieldDef(name="id", data_type="INTEGER", is_primary_key=True),
                    DatabaseFieldDef(name="title", data_type="VARCHAR(255)", is_nullable=False),
                    DatabaseFieldDef(name="description", data_type="TEXT", is_nullable=True),
                    DatabaseFieldDef(name="status", data_type="VARCHAR(64)", default_value="'PENDING'"),
                    DatabaseFieldDef(name="created_at", data_type="DATETIME", is_nullable=False),
                ],
            ),
            DatabaseEntityDef(
                entity_name="User",
                table_name="users",
                fields=[
                    DatabaseFieldDef(name="id", data_type="INTEGER", is_primary_key=True),
                    DatabaseFieldDef(name="username", data_type="VARCHAR(128)", is_unique=True),
                    DatabaseFieldDef(name="email", data_type="VARCHAR(255)", is_unique=True),
                    DatabaseFieldDef(name="hashed_password", data_type="VARCHAR(255)"),
                ],
            ),
        ]

        # 6. API Endpoints
        endpoints: List[APIEndpointDef] = [
            APIEndpointDef(
                endpoint_id="API-001",
                method="GET",
                path="/api/health",
                description="Liveness and health check endpoint",
                auth_required=False,
                traceable_requirements=["NFR-001"],
            ),
            APIEndpointDef(
                endpoint_id="API-002",
                method="GET",
                path="/api/items",
                description="List all items with pagination",
                auth_required=False,
                traceable_requirements=["FR-001"],
            ),
            APIEndpointDef(
                endpoint_id="API-003",
                method="POST",
                path="/api/items",
                description="Create a new item",
                auth_required=False,
                traceable_requirements=["FR-001"],
            ),
        ]

        # 7. UI Components (for fullstack/frontend)
        ui_components: List[UIComponentDef] = []
        if proj_type in (ProjectType.FULLSTACK_WEB, ProjectType.FRONTEND_SPA):
            ui_components = [
                UIComponentDef(
                    component_id="UI-001",
                    name="App",
                    file_path="frontend/src/App.tsx",
                    type="layout",
                    description="Main application shell and layout wrapper",
                ),
                UIComponentDef(
                    component_id="UI-002",
                    name="ItemDashboard",
                    file_path="frontend/src/components/ItemDashboard.tsx",
                    type="page",
                    description="Primary operational dashboard and list view",
                ),
            ]

        # 8. Dependencies
        dependencies: List[DependencyDef] = [
            DependencyDef(package_name="fastapi", version_spec=">=0.110.0", target_env="backend"),
            DependencyDef(package_name="uvicorn", version_spec=">=0.28.0", target_env="backend"),
            DependencyDef(package_name="pydantic", version_spec=">=2.6.0", target_env="backend"),
            DependencyDef(package_name="pytest", version_spec=">=8.0.0", target_env="test"),
            DependencyDef(package_name="httpx", version_spec=">=0.27.0", target_env="test"),
        ]

        # 9. Files to Create in Repository
        files_to_create: List[TargetFileDef] = [
            TargetFileDef(
                file_path="backend/app/__init__.py",
                description="Backend package marker",
                target_module="backend",
            ),
            TargetFileDef(
                file_path="backend/app/main.py",
                description="FastAPI ASGI entrypoint with route registrations",
                target_module="backend",
                traceable_requirements=["FR-001"],
            ),
            TargetFileDef(
                file_path="backend/app/models.py",
                description="Data models and Pydantic schemas",
                target_module="backend",
                traceable_requirements=["FR-001"],
            ),
            TargetFileDef(
                file_path="backend/tests/__init__.py",
                description="Test package marker",
                target_module="test",
                is_test_file=True,
            ),
            TargetFileDef(
                file_path="backend/tests/test_api.py",
                description="Integration tests for health check and item creation",
                target_module="test",
                is_test_file=True,
                traceable_requirements=["TEST-001"],
            ),
            TargetFileDef(
                file_path="README.md",
                description="Project documentation and run instructions",
                target_module="docs",
            ),
        ]

        if proj_type in (ProjectType.FULLSTACK_WEB, ProjectType.FRONTEND_SPA):
            files_to_create.extend([
                TargetFileDef(
                    file_path="frontend/package.json",
                    description="Frontend dependency manifest and npm scripts",
                    target_module="frontend",
                ),
                TargetFileDef(
                    file_path="frontend/src/App.tsx",
                    description="React root component with state and API fetch",
                    target_module="frontend",
                    traceable_requirements=["FR-001"],
                ),
            ])

        # 10. QA & Verification Requirements
        test_requirements: List[TestRequirementDef] = [
            TestRequirementDef(
                test_id="TEST-001",
                test_type="integration",
                target_file="backend/tests/test_api.py",
                scenario="Health check returns status: ok with 200 HTTP code",
                expected_outcome="assert response.status_code == 200 and response.json()['status'] == 'ok'",
                traceable_requirements=["FR-001"],
            ),
            TestRequirementDef(
                test_id="TEST-002",
                test_type="integration",
                target_file="backend/tests/test_api.py",
                scenario="Create item via POST and retrieve via GET",
                expected_outcome="assert response.status_code == 200 and len(items) >= 1",
                traceable_requirements=["FR-001"],
            ),
        ]

        # 11. Architectural Decisions from Context
        decisions: List[ArchitecturalDecision] = []
        if context and context.decisions:
            for d in context.decisions:
                decisions.append(
                    ArchitecturalDecision(
                        decision_id=d.decision_id,
                        category=d.category,
                        chosen_solution=d.selected_option,
                        rejected_alternatives=[str(a) for a in d.rejected_alternatives],
                        rationale=d.evidence[0] if d.evidence else "Validated in context",
                    )
                )

        status = BuildSpecStatus.BLOCKED if blocked_reasons else BuildSpecStatus.COMPILED

        return BuildSpec(
            project_id=project_id,
            project_name=project_name,
            project_type=proj_type,
            status=status,
            version=context.version if context else 1,
            requirements=requirements,
            constraints=[r.description for r in context.constraints] if context else [],
            assumptions=assumptions,
            tech_stack=tech_stack,
            database_entities=entities,
            api_endpoints=endpoints,
            ui_components=ui_components,
            environment_variables={"PORT": "8000", "ENV": "development"},
            dependencies=dependencies,
            files_to_create=files_to_create,
            test_requirements=test_requirements,
            security_requirements=["JWT authentication", "Input sanitization with Pydantic"],
            deployment_requirements=["Uvicorn ASGI runner", "Vite local dev server"],
            decisions=decisions,
            overall_confidence=0.0,
            blocked_reasons=blocked_reasons if blocked_reasons else None,
        )

    def _infer_project_name(self, raw_idea: str) -> str:
        """Create a clean project identifier name from prompt."""
        if not raw_idea:
            return "ProjectForge App"
        words = raw_idea.strip().split()
        cleaned = [w.capitalize() for w in words[:4] if w.isalnum()]
        return " ".join(cleaned) if cleaned else "ProjectForge App"
