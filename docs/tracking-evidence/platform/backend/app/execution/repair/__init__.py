"""Repair and self-healing package."""
from app.execution.repair.failure_classifier import FailureCategory, DiagnosticReport, FailureClassifier
from app.execution.repair.debugger_agent import DebuggerAgent, RepairPlan, RepairPatch
from app.execution.repair.self_healing_loop import SelfHealingLoop, SelfHealingReport, RepairAttemptRecord

__all__ = [
    "FailureCategory",
    "DiagnosticReport",
    "FailureClassifier",
    "DebuggerAgent",
    "RepairPlan",
    "RepairPatch",
    "SelfHealingLoop",
    "SelfHealingReport",
    "RepairAttemptRecord",
]
