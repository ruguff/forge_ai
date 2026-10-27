"""
ProjectForge AI — Milestone 3 Autonomous Execution Engine.

Exports the core build specification compiler, task graph, repository manager,
command executor, coding orchestrator, self-healing loop, and VS Code launcher.
"""

from app.execution.spec import (
    BuildSpec,
    BuildSpecStatus,
    BuildRequirementItem,
    RequirementSourceType,
    ProjectType,
    TechStackSelection,
    TargetFileDef,
    TestRequirementDef,
)
from app.execution.spec.build_spec_compiler import BuildSpecCompiler
from app.execution.tasks import (
    ImplementationTask,
    TaskStatus,
    TaskGraph,
    TaskGraphError,
    TaskScheduler,
)
from app.execution.repository import (
    SafeFileManager,
    GitManager,
    RepositoryManager,
    TaskScopeViolationError,
    FileAccessViolationError,
)
from app.execution.sandbox import (
    CommandPolicy,
    CommandSafetyLevel,
    SafeCommandExecutor,
    ExecutionResult,
    ResultParser,
    TestRunResult,
    TestRunner,
)
from app.execution.agent import (
    CodingAgent,
    AgentToolContext,
    TaskImplementationResult,
)
from app.execution.repair import (
    FailureCategory,
    DiagnosticReport,
    FailureClassifier,
    DebuggerAgent,
    RepairPlan,
    SelfHealingLoop,
    SelfHealingReport,
)
from app.execution.state import ProjectForgeMemoryManager
from app.execution.orchestrator import CodingOrchestrator, ExecutionPipelineReport
from app.execution.integration import VSCodeLauncher

__all__ = [
    "BuildSpec",
    "BuildSpecStatus",
    "BuildRequirementItem",
    "RequirementSourceType",
    "ProjectType",
    "TechStackSelection",
    "TargetFileDef",
    "TestRequirementDef",
    "BuildSpecCompiler",
    "ImplementationTask",
    "TaskStatus",
    "TaskGraph",
    "TaskGraphError",
    "TaskScheduler",
    "SafeFileManager",
    "GitManager",
    "RepositoryManager",
    "TaskScopeViolationError",
    "FileAccessViolationError",
    "CommandPolicy",
    "CommandSafetyLevel",
    "SafeCommandExecutor",
    "ExecutionResult",
    "ResultParser",
    "TestRunResult",
    "TestRunner",
    "CodingAgent",
    "AgentToolContext",
    "TaskImplementationResult",
    "FailureCategory",
    "DiagnosticReport",
    "FailureClassifier",
    "DebuggerAgent",
    "RepairPlan",
    "SelfHealingLoop",
    "SelfHealingReport",
    "ProjectForgeMemoryManager",
    "CodingOrchestrator",
    "ExecutionPipelineReport",
    "VSCodeLauncher",
]
