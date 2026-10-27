"""
ProjectForge AI — Task Scheduler.

Dynamically manages task state transitions. When a task completes,
evaluates dependent tasks and transitions them from PENDING to READY
once all prerequisites are met.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from app.execution.tasks.task_graph import TaskGraph
from app.execution.tasks.task_models import ImplementationTask, TaskStatus

logger = logging.getLogger(__name__)


class TaskScheduler:
    """State machine scheduler over a TaskGraph."""

    def __init__(self, task_graph: TaskGraph) -> None:
        self.graph = task_graph

    def get_ready_tasks(self) -> List[ImplementationTask]:
        """Return all tasks that are in READY state and can be executed."""
        ready: List[ImplementationTask] = []
        for task in self.graph.tasks.values():
            if task.status in (TaskStatus.READY, TaskStatus.RETRYING):
                ready.append(task)
            elif task.status == TaskStatus.PENDING:
                # Check if all dependencies are completed
                if self._all_dependencies_met(task):
                    task.status = TaskStatus.READY
                    ready.append(task)
        return ready

    def mark_running(self, task_id: str) -> None:
        """Mark task as currently executing."""
        task = self.graph.get_task(task_id)
        if task:
            task.status = TaskStatus.RUNNING

    def mark_completed(self, task_id: str, output_summary: Optional[str] = None) -> List[ImplementationTask]:
        """
        Mark task as COMPLETED and unlock newly ready dependent tasks.
        Returns the list of tasks that became READY as a result of this completion.
        """
        task = self.graph.get_task(task_id)
        if not task:
            return []

        task.status = TaskStatus.COMPLETED
        task.output_summary = output_summary

        # Find dependent tasks that are now unlocked
        unlocked: List[ImplementationTask] = []
        for dependent_id in self.graph.adj_list.get(task_id, []):
            dep_task = self.graph.get_task(dependent_id)
            if dep_task and dep_task.status == TaskStatus.PENDING:
                if self._all_dependencies_met(dep_task):
                    dep_task.status = TaskStatus.READY
                    unlocked.append(dep_task)

        return unlocked

    def mark_failed(self, task_id: str, error_message: str, retryable: bool = True) -> None:
        """Mark task as FAILED and increment retry count."""
        task = self.graph.get_task(task_id)
        if not task:
            return

        task.retry_count += 1
        task.error_message = error_message

        if retryable and task.retry_count <= task.max_retries:
            task.status = TaskStatus.RETRYING
        else:
            task.status = TaskStatus.FAILED
            # Mark downstream tasks as BLOCKED
            self._cascade_blocked(task_id)

    def _cascade_blocked(self, failed_task_id: str) -> None:
        """Recursively mark downstream tasks as BLOCKED."""
        for dependent_id in self.graph.adj_list.get(failed_task_id, []):
            dep_task = self.graph.get_task(dependent_id)
            if dep_task and dep_task.status in (TaskStatus.PENDING, TaskStatus.READY):
                dep_task.status = TaskStatus.BLOCKED
                dep_task.error_message = f"Prerequisite {failed_task_id} failed."
                self._cascade_blocked(dependent_id)

    def _all_dependencies_met(self, task: ImplementationTask) -> bool:
        """Check if all prerequisite tasks are COMPLETED."""
        for dep_id in task.dependencies:
            dep_task = self.graph.get_task(dep_id)
            if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                return False
        return True

    def is_finished(self) -> bool:
        """True if all tasks are COMPLETED."""
        return all(t.status == TaskStatus.COMPLETED for t in self.graph.tasks.values())

    def has_failures(self) -> bool:
        """True if any task permanently FAILED or BLOCKED."""
        return any(t.status in (TaskStatus.FAILED, TaskStatus.BLOCKED, TaskStatus.REQUIRES_HUMAN) for t in self.graph.tasks.values())
