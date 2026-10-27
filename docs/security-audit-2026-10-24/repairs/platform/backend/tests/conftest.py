"""Tests never use live credentials or modify the application's saved projects."""
import os
import tempfile
from pathlib import Path

_test_state = tempfile.TemporaryDirectory(prefix="projectforge_test_state_")
os.environ["PROJECTFORGE_STATE_DB"] = str(Path(_test_state.name) / "projects.sqlite3")
os.environ["GEMINI_API_KEY"] = "mock-tests"
os.environ["LLM_PROVIDER"] = "gemini"
