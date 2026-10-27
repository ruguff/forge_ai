"""
ProjectForge AI — Task Graph & Dependency DAG.

Converts a machine-readable BuildSpec into a Directed Acyclic Graph (DAG)
of atomic, traceable implementation tasks. Guarantees dependency ordering
and prevents cyclic deadlocks.
"""

from __future__ import annotations

import logging
from collections import defaultdict, deque
from typing import Any, Dict, List, Optional, Set

from app.execution.spec.build_spec_models import BuildSpec, ProjectType
from app.execution.tasks.task_models import ImplementationTask, TaskStatus

logger = logging.getLogger(__name__)


class TaskGraphError(Exception):
    """Raised when task graph is invalid or has cyclic dependencies."""


class TaskGraph:
    """Directed Acyclic Graph managing implementation tasks and dependencies."""

    def __init__(self) -> None:
        self.tasks: Dict[str, ImplementationTask] = {}
        self.adj_list: Dict[str, List[str]] = defaultdict(list)
        self.in_degree: Dict[str, int] = defaultdict(int)

    def add_task(self, task: ImplementationTask) -> None:
        """Add task to graph and update dependency linkages."""
        if task.task_id in self.tasks:
            raise TaskGraphError(f"Duplicate task ID: {task.task_id}")
        self.tasks[task.task_id] = task

    def build_from_spec(self, spec: BuildSpec) -> None:
        """Decompose a BuildSpec into canonical atomic implementation tasks."""
        self.tasks.clear()
        if spec.generation_mode == "MODEL":
            ids = {file.file_path: f"FILE-{index:03d}" for index, file in enumerate(spec.files_to_create, 1)}
            for file in spec.files_to_create:
                missing = set(file.dependencies) - set(ids)
                if missing:
                    raise TaskGraphError(f"Unknown dependencies for {file.file_path}: {sorted(missing)}")
                self.add_task(ImplementationTask(
                    task_id=ids[file.file_path], title=f"Implement {file.file_path}", description=file.description,
                    dependencies=[ids[d] for d in file.dependencies], files_to_create=[file.file_path],
                    requirements=file.traceable_requirements, architecture_constraints=spec.constraints,
                    expected_output=f"Complete source for {file.file_path}", tests=[],
                    status=TaskStatus.PENDING if file.dependencies else TaskStatus.READY))
            self._link_dependencies()
            self.validate_dag()
            return

        # TASK-001: Project Scaffold & Base Configuration
        t1 = ImplementationTask(
            task_id="TASK-001",
            title="Initialize Project Scaffold & Configuration",
            description=f"Create folder structure, README, and base config for {spec.project_name}.",
            dependencies=[],
            files_to_create=["README.md", ".gitignore", "backend/requirements.txt"],
            files_allowed_to_modify=["README.md", ".gitignore"],
            requirements=["FR-001"],
            architecture_constraints=["Standard repository structure"],
            expected_output="Base project directory and environment config initialized.",
            tests=[],
            status=TaskStatus.READY,  # Initial task has no dependencies
        )
        self.add_task(t1)

        # TASK-002: Backend Models & Schema Definitions
        t2 = ImplementationTask(
            task_id="TASK-002",
            title="Create Data Models and Schemas",
            description="Implement Pydantic models and database entity schemas.",
            dependencies=["TASK-001"],
            files_to_create=["backend/app/__init__.py", "backend/app/models.py"],
            files_allowed_to_modify=["backend/app/models.py"],
            requirements=["FR-001"],
            architecture_constraints=["Pydantic v2 schemas", "Type hints across all fields"],
            expected_output="Data models matching the entities defined in BuildSpec.",
            tests=[],
            status=TaskStatus.PENDING,
        )
        self.add_task(t2)

        # TASK-003: Core API Endpoints Implementation
        t3 = ImplementationTask(
            task_id="TASK-003",
            title="Implement Core API Endpoints",
            description="Implement FastAPI router with health check, item retrieval, and creation.",
            dependencies=["TASK-002"],
            files_to_create=["backend/app/main.py"],
            files_allowed_to_modify=["backend/app/main.py"],
            requirements=["FR-001", "NFR-001"],
            architecture_constraints=["FastAPI async endpoints", "Input validation using schemas"],
            expected_output="Functional API routing /api/health and /api/items.",
            tests=["TEST-001", "TEST-002"],
            status=TaskStatus.PENDING,
        )
        self.add_task(t3)

        # TASK-004: Automated Backend Verification Tests
        t4 = ImplementationTask(
            task_id="TASK-004",
            title="Implement Automated Test Suite",
            description="Write pytest integration tests covering health check and business routes.",
            dependencies=["TASK-003"],
            files_to_create=["backend/tests/__init__.py", "backend/tests/test_api.py"],
            files_allowed_to_modify=["backend/tests/test_api.py"],
            requirements=["TEST-001", "TEST-002"],
            architecture_constraints=["pytest asynchronous test client with httpx"],
            expected_output="Passing test suite asserting status codes and response bodies.",
            tests=["TEST-001", "TEST-002"],
            status=TaskStatus.PENDING,
        )
        self.add_task(t4)

        # Frontend Tasks (if fullstack)
        if spec.project_type in (ProjectType.FULLSTACK_WEB, ProjectType.FRONTEND_SPA):
            # TASK-005: Frontend Setup & Manifest
            t5 = ImplementationTask(
                task_id="TASK-005",
                title="Initialize Frontend Manifest and Configuration",
                description="Create package.json and React configuration.",
                dependencies=["TASK-001"],
                files_to_create=["frontend/package.json", "frontend/index.html", "frontend/tsconfig.json", "frontend/vite.config.ts"],
                files_allowed_to_modify=["frontend/package.json"],
                requirements=["FR-001"],
                architecture_constraints=["React 18, TypeScript"],
                expected_output="Valid package.json with scripts and dependencies.",
                tests=[],
                status=TaskStatus.PENDING,
            )
            self.add_task(t5)

            # TASK-006: Frontend UI Components & API Integration
            t6 = ImplementationTask(
                task_id="TASK-006",
                title="Implement Frontend Application Components",
                description="Create React UI dashboard communicating with the FastAPI backend.",
                dependencies=["TASK-003", "TASK-005"],
                files_to_create=["frontend/src/App.tsx", "frontend/src/main.tsx"],
                files_allowed_to_modify=["frontend/src/App.tsx"],
                requirements=["FR-001"],
                architecture_constraints=["Responsive UI layout with Tailwind styles"],
                expected_output="Interactive React dashboard with fetch integration.",
                tests=[],
                status=TaskStatus.PENDING,
            )
            self.add_task(t6)

        # Build graph linkages and validate no cycles
        self._link_dependencies()
        self.validate_dag()

    def _link_dependencies(self) -> None:
        """Construct adjacency list and in-degree counts."""
        self.adj_list.clear()
        self.in_degree.clear()

        for task_id in self.tasks:
            self.in_degree[task_id] = 0

        for task_id, task in self.tasks.items():
            for dep_id in task.dependencies:
                if dep_id not in self.tasks:
                    raise TaskGraphError(f"Task {task_id} depends on nonexistent task {dep_id}")
                self.adj_list[dep_id].append(task_id)
                self.in_degree[task_id] += 1

    def validate_dag(self) -> List[str]:
        """
        Kahn's algorithm: topological sort.
        Returns ordered task IDs. Raises TaskGraphError if cycle detected.
        """
        in_degrees = dict(self.in_degree)
        zero_in_degree = deque([tid for tid, deg in in_degrees.items() if deg == 0])
        ordered: List[str] = []

        while zero_in_degree:
            node = zero_in_degree.popleft()
            ordered.append(node)
            for neighbor in self.adj_list[node]:
                in_degrees[neighbor] -= 1
                if in_degrees[neighbor] == 0:
                    zero_in_degree.append(neighbor)

        if len(ordered) != len(self.tasks):
            cyclic_nodes = [t for t in self.tasks if t not in ordered]
            raise TaskGraphError(f"Cycle detected in task graph involving nodes: {cyclic_nodes}")

        return ordered

    def get_task(self, task_id: str) -> Optional[ImplementationTask]:
        """Get task by ID."""
        return self.tasks.get(task_id)

    def get_all_tasks(self) -> List[ImplementationTask]:
        """Return all tasks in topological execution order."""
        ordered_ids = self.validate_dag()
        return [self.tasks[tid] for tid in ordered_ids]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize task graph for storage in .projectforge/task_graph.json."""
        return {
            "total_tasks": len(self.tasks),
            "execution_order": self.validate_dag(),
            "tasks": [t.model_dump() for t in self.get_all_tasks()],
        }
