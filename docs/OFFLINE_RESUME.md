# Resume isolated verification

Windows features were enabled successfully on October 14. `sandbox-setup-status.json` reports `restart_required=true`; no restart was performed automatically.

1. Save your work and restart Windows.
2. In an administrator PowerShell, finish installing the modern WSL runtime if needed:

```powershell
wsl --install --no-distribution --no-launch
wsl --status
```

3. Resume the official Docker installer download and verify its publisher:

```powershell
cd D:\capstone_project
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\prepare-docker.ps1 -Install
```

The script retains partial downloads, uses a five-minute download limit per invocation and verifies the Docker signature before executing the installer. If it reports an incomplete download, rerun it to resume. The current file is partial and must not be executed. The official download is also available through [Docker's Windows installation documentation](https://docs.docker.com/desktop/setup/install/windows-install/).

4. Open Docker Desktop and complete its initial setup. In a new terminal, confirm `docker version` succeeds, then build the trusted runtime (initial downloads require internet):

```powershell
cd D:\capstone_project
docker build -t projectforge-runtime:local -f backend\sandbox\Dockerfile backend\sandbox
```

5. Start LM Studio with one prediction at a time, then inspect readiness:

```powershell
lms load nvidia/nemotron-3-nano-4b --parallel 1 -y
lms server start --port 1234 --bind 127.0.0.1
cd D:\capstone_project\backend
..\.venv\Scripts\python.exe offline_preflight.py
```

6. Continue in this chat to run a fresh public-API workflow and isolated acceptance/browser verification. The saved diagnostic build can also be rerun:

```powershell
cd D:\capstone_project\backend
..\.venv\Scripts\python.exe offline_build.py
```

Source-generation success is separate from executable verification. Current report status is BLOCKED and tests_passed is false. The laptop has limited RAM; avoid simultaneous inference jobs and observe memory before running a repair model alongside Docker.
