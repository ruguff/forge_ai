"""
ProjectForge AI — Task Graph Data Contracts.

Defines atomic implementation tasks, dependency linkages, and execution states.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """Lifecycle state of an implementation task."""
    PENDING = "PENDING"
    READY = "READY"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    RETRYING = "RETRYING"
    REQUIRES_HUMAN = "REQUIRES_HUMAN"


class ImplementationTask(BaseModel):
    """
    Atomic coding task dispatched to the Coding Agent.
    Guarantees strict file scope boundaries so agents cannot modify unauthorized files.
    """
    task_id: str = Field(..., description="e.g. TASK-001, TASK-002")
    title: str
    description: str
    dependencies: List[str] = Field(default_factory=list, description="IDs of prerequisite tasks")
    files_to_create: List[str] = Field(default_factory=list)
    files_allowed_to_modify: List[str] = Field(default_factory=list)
    requirements: List[str] = Field(default_factory=list, description="Traceable requirement IDs e.g. FR-001")
    architecture_constraints: List[str] = Field(default_factory=list)
    expected_output: str
    tests: List[str] = Field(default_factory=list, description="Test IDs required to verify this task")
    status: TaskStatus = TaskStatus.PENDING
    retry_count: int = 0
    max_retries: int = 3
    error_message: Optional[str] = None
    output_summary: Optional[str] = None
