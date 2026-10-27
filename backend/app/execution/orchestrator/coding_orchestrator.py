"""
ProjectForge AI — Coding Orchestrator.

The master execution controller. Ingests a machine-readable BuildSpec,
constructs the TaskGraph, schedules atomic coding tasks to the CodingAgent,
observes test runs, triggers the SelfHealingLoop upon failure, and certifies
the project for final VS Code launch.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable, Dict, List, Optional
from pydantic import BaseModel, Field

from app.execution.agent.coding_agent import CodingAgent, TaskImplementationResult
from app.execution.agent.tools import AgentToolContext
from app.execution.repair.self_healing_loop import SelfHealingLoop, SelfHealingReport
from app.execution.repository.repository_manager import RepositoryManager
from app.execution.sandbox.result_parser import TestRunResult
from app.execution.sandbox.test_runner import TestRunner
from app.execution.spec.build_spec_models import BuildSpec, BuildSpecStatus, ProjectType
from app.execution.sandbox.executor import CommandExecutionBlockedError
from app.execution.state.projectforge_memory import ProjectForgeMemoryManager
from app.execution.tasks.task_graph import TaskGraph
from app.execution.tasks.task_models import ImplementationTask, TaskStatus
from app.execution.tasks.task_scheduler import TaskScheduler

logger = logging.getLogger(__name__)


class ExecutionPipelineReport(BaseModel):
    """Final comprehensive report of the autonomous execution run."""
    project_id: str
    project_name: str
    workspace_path: str
    status: str = Field(..., description="VERIFIED, REQUIRES_HUMAN, BLOCKED, FAILED")
    tasks_executed: int
    files_created_count: int
    tests_passed: bool
    self_healing_invoked: bool = False
    repair_report: Optional[SelfHealingReport] = None
    final_test_result: Optional[TestRunResult] = None
    verification_checks: Dict[str, str] = Field(default_factory=dict)
    limitations: List[str] = Field(default_factory=list)
    source_digest: Optional[str] = None


class CodingOrchestrator:
    """Master controller executing a BuildSpec from task DAG to verified repository."""

    def __init__(
        self,
        workspace_root: Path | str,
        on_event_callback: Optional[Callable[[str, Dict], None]] = None,
        model_client=None,
    ) -> None:
        self.workspace_root = Path(workspace_root).resolve()
        self.repo = RepositoryManager(self.workspace_root)
        self.memory = ProjectForgeMemoryManager(self.workspace_root)
        self.test_runner = TestRunner(self.workspace_root)
        self.coding_agent = CodingAgent(model_client=model_client)
        if model_client:
            self.self_healing_model = model_client
        self.self_healing = SelfHealingLoop(self.repo, self.test_runner, model_client=model_client)
        self.on_event = on_event_callback or (lambda evt, data: None)

    def execute_build(self, spec: BuildSpec, resume: bool = False) -> ExecutionPipelineReport:
        """
        Execute full autonomous construction pipeline for a BuildSpec.
        """
        logger.info("Starting autonomous build for project %s (%s)", spec.project_id, spec.project_name)
        if spec.status == BuildSpecStatus.BLOCKED:
            return ExecutionPipelineReport(project_id=spec.project_id, project_name=spec.project_name,
                workspace_path=str(self.workspace_root), status="BLOCKED", tasks_executed=0,
                files_created_count=0, tests_passed=False, limitations=spec.blocked_reasons or ["Build specification blocked."])
        from app.execution.verification import source_digest
        # A new build cannot inherit a previous run's verification evidence.
        verification_file = self.workspace_root / ".projectforge" / "verification.json"
        if verification_file.exists():
            verification_file.unlink()
        self.on_event("BUILD_STARTED", {"project_id": spec.project_id, "project_name": spec.project_name})

        # 1. Initialize project workspace & .projectforge memory
        self.repo.initialize_project()
        if spec.source_generation_strategy in ('RELATIONAL_CRUD','CATALOGUE','IDENTITY','ORDERS','PAYMENT_SIMULATOR','RAZORPAY_TEST') and spec.tech_stack.primary_database.lower() == 'postgresql':
            self.test_runner.executor.image = 'projectforge-relational-runtime:local'
        from app.execution.state.build_checkpoint import BuildCheckpoint
        checkpoint = BuildCheckpoint(self.workspace_root, spec, resume=resume)
        self.memory.write_json("build_spec.json", spec.model_dump())
        self.memory.initialize_memory(spec.project_id, spec.project_name, spec.requirements[0].description if spec.requirements else "")

        # 2. Construct Task Graph & Scheduler
        graph = TaskGraph()
        graph.build_from_spec(spec)
        self.self_healing.allowed_repair_files = {p for task in graph.get_all_tasks() for p in task.files_to_create
                                               if '/tests/' not in p and not Path(p).name.startswith('test_')}
        scheduler = TaskScheduler(graph)
        self.memory.write_json("task_graph.json", graph.to_dict())

        total_files_created = 0
        tasks_count = 0

        # 3. Task Execution Loop
        while True:
            ready_tasks = scheduler.get_ready_tasks()
            if not ready_tasks:
                break

            for task in ready_tasks:
                if resume and checkpoint.can_reuse(task):
                    scheduler.mark_completed(task.task_id, 'Recovered unchanged source checkpoint; verification pending.')
                    self.on_event('TASK_RECOVERED', {'task_id': task.task_id})
                    continue
                checkpoint.invalidate(task.task_id, graph.get_all_tasks())
                scheduler.mark_running(task.task_id)
                self.on_event("TASK_STARTED", {
                    "task_id": task.task_id,
                    "title": task.title,
                    "files": task.files_to_create,
                })

                # Prepare focused context and authorized tool harness
                allowed_files = task.files_to_create + task.files_allowed_to_modify
                tools = AgentToolContext(self.repo, task.task_id, allowed_files)
                focused_context = {
                    "task": task.model_dump(),
                    "relevant_requirements": [r for r in spec.requirements if r.id in task.requirements],
                    "tech_stack": spec.tech_stack.model_dump(),
                }

                try:
                    result: TaskImplementationResult = self.coding_agent.execute_task(
                        task=task,
                        spec=spec,
                        tools=tools,
                        focused_context=focused_context,
                    )
                    total_files_created += len(result.files_created)
                    tasks_count += 1

                    checkpoint.completed(task)
                    scheduler.mark_completed(task.task_id, result.implementation_summary)
                    self.on_event("TASK_COMPLETED", {
                        "task_id": task.task_id,
                        "summary": result.implementation_summary,
                        "files_created": result.files_created,
                    })

                except Exception as e:
                    logger.error("Task %s execution failed: %s", task.task_id, e)
                    # CodingAgent has already exhausted its bounded repair attempts.
                    scheduler.mark_failed(task.task_id, str(e), retryable=False)
                    self.on_event("TASK_FAILED", {"task_id": task.task_id, "error": str(e)})
                finally:
                    self.memory.write_json("task_graph.json", graph.to_dict())

        self.memory.write_json("task_graph.json", graph.to_dict())

        # Check for permanent task failures
        if scheduler.has_failures() or not scheduler.is_finished():
            return ExecutionPipelineReport(
                project_id=spec.project_id,
                project_name=spec.project_name,
                workspace_path=str(self.workspace_root),
                status="FAILED",
                tasks_executed=tasks_count,
                files_created_count=total_files_created,
                tests_passed=False,
                verification_checks={'source_generation': 'FAILED'},
                limitations=[f'{task.task_id}: {task.error_message or task.status.value}'
                    for task in graph.get_all_tasks() if task.status != TaskStatus.COMPLETED],
            )

        # 4. Checkpoint code complete
        self.repo.create_checkpoint("code_complete", "All tasks compiled successfully")

        # 5. Execute Tests & Observation
        self.on_event("TESTS_RUNNING", {"project_id": spec.project_id})
        available, reason = self.test_runner.executor.preflight()
        if not available:
            self.on_event("BUILD_BLOCKED", {"reason": reason})
            report = ExecutionPipelineReport(project_id=spec.project_id, project_name=spec.project_name,
                workspace_path=str(self.workspace_root), status="BLOCKED", tasks_executed=tasks_count,
                files_created_count=total_files_created, tests_passed=False,
                verification_checks={"execution_isolation": "UNAVAILABLE"}, limitations=[reason],
                source_digest=source_digest(self.workspace_root))
            self.memory.write_json("verification.json", report.model_dump(mode="json"))
            return report
        try:
            test_result = self.test_runner.run_backend_tests()
        except CommandExecutionBlockedError as exc:
            return ExecutionPipelineReport(project_id=spec.project_id, project_name=spec.project_name,
                workspace_path=str(self.workspace_root), status="BLOCKED", tasks_executed=tasks_count,
                files_created_count=total_files_created, tests_passed=False, limitations=[str(exc)])
        self.on_event("TESTS_COMPLETED", {
            "passed": test_result.passed_count,
            "failed": test_result.failed_count,
            "is_success": test_result.is_success,
        })

        # 6. Self-Healing Loop if tests failed
        repair_report: Optional[SelfHealingReport] = None
        if not test_result.is_success:
            self.on_event("DEBUGGING_ACTIVE", {"failed_tests": test_result.failed_count})
            repair_report = self.self_healing.execute_loop(
                project_id=spec.project_id,
                initial_test_result=test_result,
                on_attempt_callback=lambda attempt: self.on_event("REPAIR_ATTEMPT", attempt.model_dump()),
            )
            test_result = repair_report.final_test_result or test_result

        # 7. Final Verification Check
        checks = {"backend_tests": "PASSED" if test_result.is_success else "FAILED"}
        if spec.project_type == ProjectType.FULLSTACK_WEB:
            frontend = self.test_runner.run_frontend_build()
            checks["frontend_build"] = "PASSED" if frontend.exit_code == 0 else "FAILED"
            self.memory.write_json("frontend_build.json", frontend.model_dump(mode="json"))
        if spec.acceptance_checks:
            acceptance = self.test_runner.run_acceptance(spec.acceptance_checks)
            checks["requirement_acceptance"] = "PASSED" if acceptance.is_success else "FAILED"
            self.memory.write_json("acceptance_results.json", acceptance.model_dump(mode="json"))
        else:
            checks["requirement_acceptance"] = "UNVERIFIED"
        # Browser, security and performance results must never be implied by
        # backend success. They remain an explicit verification limitation.
        if spec.project_type == ProjectType.FULLSTACK_WEB:
            if spec.browser_checks:
                browser = self.test_runner.run_browser_checks(spec.browser_checks)
                checks["browser_journeys"] = "PASSED" if browser.is_success else "FAILED"
                self.memory.write_json("browser_results.json", browser.model_dump(mode="json"))
            else:
                checks["browser_journeys"] = "UNVERIFIED"
        if spec.source_generation_strategy in ('IDENTITY','ORDERS','PAYMENT_SIMULATOR','RAZORPAY_TEST'):
            identity=self.test_runner.run_identity_checks()
            checks['identity_authority']='PASSED' if identity.is_success else 'FAILED'
            self.memory.write_json('identity_authority_results.json',identity.model_dump(mode='json'))
        if spec.source_generation_strategy in ('ORDERS','PAYMENT_SIMULATOR','RAZORPAY_TEST'):
            order=self.test_runner.run_order_checks()
            checks['order_integrity']='PASSED' if order.is_success else 'FAILED'
            self.memory.write_json('order_integrity_results.json',order.model_dump(mode='json'))
            order_browser=self.test_runner.run_order_browser_checks()
            checks['order_browser_journey']='PASSED' if order_browser.is_success else 'FAILED'
            self.memory.write_json('order_browser_results.json',order_browser.model_dump(mode='json'))
        if spec.source_generation_strategy == 'PAYMENT_SIMULATOR':
            for name,runner in (('payment_simulation',self.test_runner.run_payment_checks),('payment_simulation_browser',self.test_runner.run_payment_browser_checks)):
                result=runner()
                checks[name]='PASSED' if result.is_success else 'FAILED'
                self.memory.write_json(name+'_results.json',result.model_dump(mode='json'))
        if spec.source_generation_strategy == 'RAZORPAY_TEST':
            for name,runner in (('razorpay_mock_contract',self.test_runner.run_razorpay_checks),('razorpay_browser',self.test_runner.run_razorpay_browser_checks)):
                result=runner()
                checks[name]='PASSED' if result.is_success else 'FAILED'
                self.memory.write_json(name+'_results.json',result.model_dump(mode='json'))
            checks['razorpay_provider_integration']='UNVERIFIED'
        final_status = "VERIFIED" if all(v == "PASSED" for v in checks.values()) else "REQUIRES_HUMAN"
        if final_status == "VERIFIED":
            self.repo.create_checkpoint("verified", "Automated test assertions 100% passed")
            self.on_event("VERIFICATION_SUCCESS", {"project_id": spec.project_id, "checks": checks})
        else:
            self.on_event("REQUIRES_HUMAN", {"project_id": spec.project_id})

        report = ExecutionPipelineReport(
            project_id=spec.project_id,
            project_name=spec.project_name,
            workspace_path=str(self.workspace_root),
            status=final_status,
            tasks_executed=tasks_count,
            files_created_count=total_files_created,
            tests_passed=test_result.is_success,
            self_healing_invoked=repair_report is not None,
            repair_report=repair_report,
            final_test_result=test_result,
            verification_checks=checks,
            limitations=["Verification covers declared acceptance cases; load and security scans remain unverified."] + (["Razorpay local checks use synthetic provider evidence; real test-account checkout and webhooks remain unverified. Live payments are disabled."] if spec.source_generation_strategy == "RAZORPAY_TEST" else []),
            source_digest=source_digest(self.workspace_root),
        )
        self.memory.write_json("verification.json", report.model_dump(mode="json"))
        return report
