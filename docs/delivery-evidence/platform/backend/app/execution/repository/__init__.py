"""Repository and filesystem management package."""
from app.execution.repository.file_manager import SafeFileManager, FileAccessViolationError
from app.execution.repository.git_manager import GitManager
from app.execution.repository.repository_manager import RepositoryManager, TaskScopeViolationError

__all__ = [
    "SafeFileManager",
    "FileAccessViolationError",
    "GitManager",
    "RepositoryManager",
    "TaskScopeViolationError",
]
