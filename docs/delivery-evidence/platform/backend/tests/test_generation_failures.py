from unittest.mock import Mock
from app.execution.orchestrator.coding_orchestrator import CodingOrchestrator
from app.execution.spec.build_spec_models import BuildSpec, TargetFileDef
from app.execution.tasks.task_graph import TaskGraph
from app.execution.tasks.task_scheduler import TaskScheduler
from app.execution.tasks.task_models import ImplementationTask, TaskStatus


def test_failed_generation_never_proceeds_to_verification(tmp_path):
    spec = BuildSpec(project_id='PROJ-FAILED-GENERATION', project_name='Failure', generation_mode='MODEL',
        files_to_create=[TargetFileDef(file_path='backend/app/main.py', description='App', target_module='backend')])
    orchestrator = CodingOrchestrator(tmp_path)
    orchestrator.coding_agent.execute_task = Mock(side_effect=RuntimeError('Source generation failed'))
    orchestrator.test_runner.executor.preflight = Mock(return_value=(True, 'Available'))
    report = orchestrator.execute_build(spec)
    assert report.status == 'FAILED'
    assert report.tasks_executed == 0
    assert not report.tests_passed
    orchestrator.test_runner.executor.preflight.assert_not_called()


def test_retrying_tasks_are_schedulable():
    graph = TaskGraph()
    graph.add_task(ImplementationTask(task_id='FILE-1', title='App', description='App',
        expected_output='Source', status=TaskStatus.READY))
    scheduler = TaskScheduler(graph)
    scheduler.mark_failed('FILE-1', 'Temporary issue')
    assert [task.task_id for task in scheduler.get_ready_tasks()] == ['FILE-1']
    scheduler.mark_failed('FILE-1', 'Permanent issue', retryable=False)
    assert scheduler.has_failures()
    assert not scheduler.get_ready_tasks()
