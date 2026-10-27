"""Generated-code execution in an offline, resource-limited Docker container.

No host-execution fallback. The prebuilt runtime image is a setup requirement.
"""
from __future__ import annotations
import os
import re
import shlex
import shutil
import subprocess
import tempfile
import time
import threading
import uuid
from pathlib import Path
from typing import Callable, Optional
from pydantic import BaseModel
from app.execution.sandbox.command_policy import CommandPolicy, CommandSafetyLevel


class CommandExecutionBlockedError(Exception):
    pass


class ExecutionResult(BaseModel):
    command: str
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: float
    timed_out: bool = False
    safety_level: CommandSafetyLevel = CommandSafetyLevel.ALLOWED


class SafeCommandExecutor:
    def __init__(self, workspace_root, default_timeout_sec=60.0):
        self.workspace_root = Path(workspace_root).resolve()
        self.default_timeout_sec = default_timeout_sec
        self.docker = shutil.which("docker")
        self.image = os.environ.get("PROJECTFORGE_SANDBOX_IMAGE", "projectforge-runtime:local")

    def preflight(self):
        if not self.docker:
            return False, "Docker is unavailable. Generated code is never executed on the host."
        if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._/:@-]*", self.image):
            return False, "Invalid sandbox image name."
        try:
            result = subprocess.run([self.docker, "image", "inspect", self.image],
                                    capture_output=True, timeout=15)
            if result.returncode:
                return False, "Build the projectforge-runtime:local image using backend/sandbox/Dockerfile."
        except (OSError, subprocess.TimeoutExpired):
            return False, "Docker daemon is unavailable."
        return True, "Offline container runtime available."

    def execute(self, command_str, timeout_sec=None, on_stdout_line: Optional[Callable] = None):
        level, reason = CommandPolicy.evaluate(command_str)
        if level != CommandSafetyLevel.ALLOWED:
            raise CommandExecutionBlockedError(reason)
        available, reason = self.preflight()
        if not available:
            raise CommandExecutionBlockedError(reason)
        tokens = [token.strip('"\'') for token in shlex.split(command_str, posix=False)]
        if Path(tokens[0]).name.lower().startswith("python"):
            tokens[0] = "python"
        timeout = min(timeout_sec or self.default_timeout_sec, 120.0)
        start = time.perf_counter()
        container = "projectforge-" + uuid.uuid4().hex
        # Stage plain files outside the source workspace. The container never
        # receives a writable bind mount of the host project.
        with tempfile.TemporaryDirectory(prefix="projectforge_isolation_") as staging:
            stage = Path(staging)
            total = 0
            for root, dirs, files in os.walk(self.workspace_root, followlinks=False):
                base = Path(root)
                for name in list(dirs):
                    directory = base / name
                    if directory.is_symlink() or (hasattr(directory, "is_junction") and directory.is_junction()):
                        raise CommandExecutionBlockedError("Linked directories are forbidden in generated workspaces.")
                dirs[:] = [d for d in dirs if d not in (".git", "node_modules", ".venv", "__pycache__", "dist")]
                for name in files:
                    source = base / name
                    if source.is_symlink() or not source.resolve().is_relative_to(self.workspace_root):
                        raise CommandExecutionBlockedError("Linked files are forbidden in generated workspaces.")
                    if name == ".env" or name.startswith(".env."):
                        continue
                    size = source.stat().st_size
                    total += size
                    if size > 2_000_000 or total > 20_000_000:
                        raise CommandExecutionBlockedError("Generated workspace exceeds source-size limits.")
                    target = stage / source.relative_to(self.workspace_root)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, target)
            # PostgreSQL + Vite + Chromium share this one offline container.
            # Cold-start measurement hit 128 tasks and prevented FastAPI from
            # starting worker threads. Keep a bounded 192-task budget only for
            # the reviewed PostgreSQL test image; memory/CPU/privileges stay fixed.
            pids_limit = "192" if self.image == "projectforge-relational-runtime:local" else "128"
            argv = [self.docker, "run", "--rm", "--name", container,
                    "--log-driver", "none",
                    "--network", "none", "--read-only", "--cap-drop", "ALL",
                    "--security-opt", "no-new-privileges", "--user", "65534:65534",
                    "--memory", "768m", "--memory-swap", "768m", "--cpus", "1", "--pids-limit", pids_limit,
                    "--tmpfs", "/tmp:rw,nosuid,size=256m,mode=1777",
                    "--mount", f"type=bind,source={stage},target=/source,readonly",
                    self.image, *tokens]
            process = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False)
            captured_out, captured_err = bytearray(), bytearray()
            def capture(pipe, buffer):
                try:
                    while True:
                        chunk = pipe.read(65536)
                        if not chunk:
                            break
                        # Drain both pipes, retaining only bounded output.
                        buffer.extend(chunk[:max(0, 1_000_000-len(buffer))])
                finally:
                    pipe.close()
            readers = [threading.Thread(target=capture, args=(process.stdout, captured_out), daemon=True),
                       threading.Thread(target=capture, args=(process.stderr, captured_err), daemon=True)]
            for reader in readers:
                reader.start()
            timed_out = False
            try:
                process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
                process.kill()
            finally:
                subprocess.run([self.docker, "rm", "-f", container], capture_output=True, timeout=15)
                process.wait(timeout=15)
                for reader in readers:
                    reader.join(timeout=5)
            stdout = captured_out.decode("utf-8", errors="replace")
            stderr = captured_err.decode("utf-8", errors="replace")
        if on_stdout_line:
            for line in stdout.splitlines():
                on_stdout_line(line)
        return ExecutionResult(command=command_str, exit_code=-1 if timed_out else process.returncode,
            stdout=stdout, stderr=stderr, duration_ms=round((time.perf_counter()-start)*1000, 2),
            timed_out=timed_out, safety_level=level)
