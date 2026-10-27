"""
ProjectForge AI — Coding Agent.

Executes atomic implementation tasks using controlled tools.
Produces production-grade, lint-compliant, tested source files.
"""

from __future__ import annotations

import logging
import json
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.execution.agent.tools import AgentToolContext
from app.execution.spec.build_spec_models import BuildSpec
from app.execution.tasks.task_models import ImplementationTask

logger = logging.getLogger(__name__)


def focused_spec(spec, paths):
    data = {
        'project_name': spec.project_name,
        'requirements': [{'id': r.id, 'description': r.description, 'dimension': r.dimension,
                          'source': r.source.value} for r in spec.requirements],
        'constraints': spec.constraints,
        'tech_stack': spec.tech_stack.model_dump(mode='json'),
        'dependencies': [d.model_dump(mode='json') for d in spec.dependencies],
        'authorized_files': [f.model_dump(mode='json') for f in spec.files_to_create if f.file_path in paths],
        'declared_paths': [f.file_path for f in spec.files_to_create],
    }
    source_file = any(p.endswith(('.py', '.tsx', '.ts')) and not p.endswith(('__init__.py', 'vite.config.ts')) for p in paths)
    if source_file or 'README.md' in paths:
        data['api_endpoints'] = [e.model_dump(mode='json') for e in spec.api_endpoints]
        data['database_entities'] = [e.model_dump(mode='json') for e in spec.database_entities]
        data['security_requirements'] = spec.security_requirements
    if any(p.startswith('frontend/') and p.endswith(('.tsx', '.ts')) for p in paths):
        data['ui_components'] = [c.model_dump(mode='json') for c in spec.ui_components]
        if spec.ui_contract:
            data['ui_contract'] = spec.ui_contract.model_dump(mode='json')
        else:
            data['browser_checks'] = spec.browser_checks
    elif any(p.startswith('backend/') and p.endswith('.py') for p in paths):
        data['acceptance_checks'] = spec.acceptance_checks
    if any('/tests/' in p for p in paths):
        data['test_requirements'] = [t.model_dump(mode='json') for t in spec.test_requirements]
    return data


class TaskImplementationResult(BaseModel):
    """Structured report returned after a coding task executes."""
    task_id: str
    files_created: List[str] = Field(default_factory=list)
    files_modified: List[str] = Field(default_factory=list)
    implementation_summary: str
    commands_requested: List[str] = Field(default_factory=list)
    tests_requested: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class CodingAgent:
    """Specialized software engineering coding agent."""

    def __init__(self, agent_name: str = "TemplateGenerator", model_client=None) -> None:
        self.agent_name = agent_name
        self.model_client = model_client

    def execute_task(
        self,
        task: ImplementationTask,
        spec: BuildSpec,
        tools: AgentToolContext,
        focused_context: Optional[Dict[str, Any]] = None,
    ) -> TaskImplementationResult:
        """
        Execute an atomic implementation task and write source files.
        Enforces file boundaries via the AgentToolContext.
        """
        files_created: List[str] = []
        files_modified: List[str] = []
        summary = ""
        if spec.source_generation_strategy in ('RELATIONAL_CRUD','CATALOGUE','IDENTITY','ORDERS','PAYMENT_SIMULATOR','RAZORPAY_TEST'):
            if spec.source_generation_strategy == 'RAZORPAY_TEST':
                from app.execution.agent.razorpay import sources
            elif spec.source_generation_strategy == 'PAYMENT_SIMULATOR':
                from app.execution.agent.payments import sources
            elif spec.source_generation_strategy == 'ORDERS':
                from app.execution.agent.orders import sources
            elif spec.source_generation_strategy == 'IDENTITY':
                from app.execution.agent.identity import sources
            elif spec.source_generation_strategy == 'CATALOGUE':
                from app.execution.agent.catalogue import sources
            else:
                from app.execution.agent.relational import sources
            generated = sources(spec)
            for path in task.files_to_create:
                if path not in generated:
                    raise ValueError('File outside reviewed runtime: '+path)
                tools.write_file(path, generated[path])
            module = {'ORDERS': 'cart and unpaid-order', 'IDENTITY': 'identity and permissions',
                      'CATALOGUE': 'public catalogue', 'RELATIONAL_CRUD': 'related CRUD'}.get(
                          spec.source_generation_strategy, 'reviewed application')
            return TaskImplementationResult(task_id=task.task_id, files_created=task.files_to_create,
                implementation_summary=f'Compiled reviewed {module} module; independent runtime verification pending.')
        if spec.generation_mode == "MODEL":
            if self.model_client is None:
                raise RuntimeError("Model-generated projects require a configured coding model.")
            from app.agents.model_client import LocalModelClient
            if isinstance(self.model_client, LocalModelClient) and self.model_client.settings.LOCAL_CODE_GENERATION_STRATEGY == 'declarative_crud':
                from app.execution.agent.declarative import file_source
                sources = {path:file_source(spec,path) for path in task.files_to_create}
                for path,source in sources.items():
                    if path.endswith('.py'):
                        compile(source,path,'exec')
                    tools.write_file(path,source)
                return TaskImplementationResult(task_id=task.task_id,files_created=list(sources),
                    implementation_summary='Source compiled from the validated AI-designed specification using DECLARATIVE_CRUD; runtime verification is separate.')
            if isinstance(self.model_client, LocalModelClient) and task.files_to_create == ['backend/app/main.py']:
                from app.execution.agent.local_backend import build_module
                source = build_module(spec, self.model_client)
                tools.write_file('backend/app/main.py', source)
                return TaskImplementationResult(task_id=task.task_id, files_created=['backend/app/main.py'],
                    implementation_summary='Model-generated endpoint business logic assembled with trusted FastAPI/SQLite scaffolding.')
            dependencies = {}
            for file in spec.files_to_create:
                if file.file_path in task.files_to_create:
                    for dependency in file.dependencies:
                        if task.files_to_create[0].startswith('frontend/') and dependency.startswith('backend/'):
                            dependencies[dependency] = {'interface': 'Declared API contracts and entity fields in the focused specification'}
                        else:
                            dependencies[dependency] = tools.read_file(dependency)
            prompt = """Implement the authorized source file for this website.
Follow the full BuildSpec and user constraints. No placeholders or fake success.
Do not change acceptance checks. Match interfaces in dependency source files.
Return JSON: {"files": {"authorized/path": "complete source text"}, "summary": "..."}.
Write only authorized paths. Do not add secrets, package lifecycle scripts or external download hooks.
Use /api paths and a Vite proxy to http://127.0.0.1:8001 for generated local preview.
Frontend must expose a build script 'tsc --noEmit && vite build'.
The Python module app/main.py must define the variable app = FastAPI(). Python has NO 'export' statement.
Do not write 'export app' or import __init__ in Python files. Declare all required dependencies.
For Pydantic 2 ORM responses use model_config = {'from_attributes': True}, not the old orm_mode option.
Match the HTTP status codes and JSON contracts in acceptance_checks. A 204 response has no JSON body.
Implement only the current file's role. __init__.py contains only a package docstring; do not put routes or models there.
Configuration files contain configuration only; application behavior belongs in App.tsx and app/main.py.
In frontend/tsconfig.json, include paths are relative to frontend/: use ["src"], never ["frontend/src"].
SQLAlchemy sessions use Depends(get_db) or a with-session block, never plain HTTP parameters.
Fetch ORM records once, update their attributes and commit. SQL Result objects have no update() method.
""" + json.dumps({"spec": focused_spec(spec, task.files_to_create), "task": task.model_dump(mode="json"),
                     "dependency_sources": dependencies})
            schema = {'type': 'object', 'properties': {
                'files': {'type': 'object', 'properties': {p: {'type': 'object', 'additionalProperties': True}
                            if p.endswith('.json') else {'type': 'string'} for p in task.files_to_create},
                          'required': task.files_to_create, 'additionalProperties': False},
                'summary': {'type': 'string'}}, 'required': ['files', 'summary'], 'additionalProperties': False}
            for path in task.files_to_create:
                if path.endswith('package.json'):
                    schema['properties']['files']['properties'][path] = {
                        'type': 'object', 'properties': {
                            'name': {'type': 'string'}, 'version': {'type': 'string'}, 'private': {'type': 'boolean'},
                            'scripts': {'type': 'object', 'properties': {
                                'dev': {'type': 'string', 'enum': ['vite']},
                                'build': {'type': 'string', 'enum': ['tsc --noEmit && vite build']}},
                                'required': ['dev', 'build'], 'additionalProperties': False},
                            'dependencies': {'type': 'object', 'properties': {n: {'type': 'string'} for n in ['react', 'react-dom']},
                                'required': ['react', 'react-dom'], 'additionalProperties': {'type': 'string'}},
                            'devDependencies': {'type': 'object', 'properties': {n: {'type': 'string'} for n in ['typescript', 'vite', '@vitejs/plugin-react', '@types/react', '@types/react-dom']},
                                'required': ['typescript', 'vite', '@vitejs/plugin-react', '@types/react', '@types/react-dom'], 'additionalProperties': {'type': 'string'}}},
                        'required': ['scripts', 'dependencies', 'devDependencies'], 'additionalProperties': False}
            prompt += '\nRequired response schema:\n```json\n' + json.dumps(schema) + '\n```'
            if any(p.endswith('.json') for p in task.files_to_create):
                prompt += '\nFor JSON files, return their contents as JSON OBJECTS, not escaped strings. Use JSON booleans true/false. Do not add comments.'
            previous_error = ""
            for attempt in range(2):
                raw = ''
                try:
                    from app.agents.model_client import LocalModelClient
                    raw = (self.model_client.generate_sync(prompt + previous_error, output_tokens=3072)
                           if isinstance(self.model_client, LocalModelClient)
                           else self.model_client.generate_sync(prompt + previous_error))
                    output = json.loads(raw)
                    files = output.get("files", {})
                    if set(files) != set(task.files_to_create):
                        raise ValueError("Output must contain exactly the authorized file paths.")
                    for path, source in files.items():
                        if path.endswith('tsconfig.json'):
                            from app.execution.agent.source_review import normalize_tsconfig
                            config = source if isinstance(source, dict) else json.loads(source)
                            source = json.dumps(normalize_tsconfig(config), indent=2)
                            files[path] = source
                        if path.endswith('.json') and isinstance(source, dict):
                            source = json.dumps(source, indent=2)
                            files[path] = source
                        if not isinstance(source, str) or not source.strip():
                            raise ValueError(f"Empty source: {path}")
                        if path.endswith("package.json"):
                            package = json.loads(source)
                            scripts = package.get("scripts", {})
                            if any(name not in ("dev", "build", "preview", "test", "lint") for name in scripts):
                                raise ValueError("Only development scripts are permitted.")
                            if scripts.get("build") != "tsc --noEmit && vite build":
                                raise ValueError("Frontend build must be tsc --noEmit && vite build.")
                        elif path.endswith('.json'):
                            json.loads(source)
                        from app.execution.agent.source_review import review_python, review_json
                        issues = review_python(source, path, spec.acceptance_checks) if path.endswith('.py') else (
                            review_json(json.loads(source), path) if path.endswith('.json') else [])
                        if issues:
                            raise ValueError('; '.join(issues))
                        if path.endswith(".py"):
                            compile(source, path, "exec")  # Syntax only; never execute on the host.
                    for path, source in files.items():
                        tools.write_file(path, source)
                    return TaskImplementationResult(task_id=task.task_id, files_created=list(files),
                        implementation_summary=output.get("summary", "Model source generated."))
                except (ValueError, SyntaxError) as exc:
                    detail = ''
                    if isinstance(exc, SyntaxError):
                        detail = f'\nInvalid Python line {exc.lineno}: {exc.text!r}. Python has no export statement.'
                    previous_error = (f"\nPrevious output failed validation: {exc}.{detail} Return corrected JSON. "
                        'Keep the file focused on its stated role.\nLatest failed response:\n' + raw[:3500])
                    if attempt == 1:
                        raise

        # Dispatch based on task ID or target files
        if task.task_id == "TASK-001":
            # Scaffold: README.md and .gitignore
            readme_content = f"""# {spec.project_name}

{spec.project_type.value} generated autonomously by **PROJECTFORGE AI**.

## Architecture & Tech Stack
- **Backend**: {spec.tech_stack.backend_framework} ({spec.tech_stack.backend_language})
- **Database**: {spec.tech_stack.primary_database}
- **Frontend**: {spec.tech_stack.frontend_framework} + {spec.tech_stack.frontend_language}
- **Auth**: {spec.tech_stack.auth_provider}

## Quick Start

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --port 8000 --reload
```

### Running Tests
```bash
pytest backend/tests -v
```
"""
            tools.write_file("README.md", readme_content)
            files_created.append("README.md")

            gitignore_content = """__pycache__/
*.py[cod]
*$py.class
.pytest_cache/
node_modules/
dist/
.env
.projectforge/checkpoints/
"""
            tools.write_file(".gitignore", gitignore_content)
            files_created.append(".gitignore")
            tools.write_file("backend/requirements.txt", "fastapi>=0.110.0\nuvicorn>=0.28.0\npydantic>=2.6.0\nhttpx>=0.27.0\npytest>=8.0.0\npytest-asyncio>=0.23.0\n")
            files_created.append("backend/requirements.txt")
            summary = "Initialized project repository, README.md, and .gitignore."

        elif task.task_id == "TASK-002":
            # Models: backend/app/__init__.py and backend/app/models.py
            tools.write_file("backend/app/__init__.py", '"""Backend application package."""\n')
            files_created.append("backend/app/__init__.py")

            models_content = '''"""
Data models and schemas for application entities.
"""

from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field


class ItemBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    status: str = Field("PENDING", max_length=64)


class ItemCreate(ItemBase):
    pass


class ItemResponse(ItemBase):
    id: int
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"from_attributes": True}


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "1.0.0"
    service: str = "backend"
'''
            tools.write_file("backend/app/models.py", models_content)
            files_created.append("backend/app/models.py")
            summary = "Created Item and Health Pydantic data schemas."

        elif task.task_id == "TASK-003":
            # API: backend/app/main.py
            main_content = '''"""
FastAPI application router and service entrypoint.
"""

from typing import Dict, List
from fastapi import FastAPI, HTTPException
from app.models import HealthResponse, ItemCreate, ItemResponse

app = FastAPI(title="ProjectForge Generated Application", version="1.0.0")

# In-memory item store
_ITEMS_DB: Dict[int, ItemResponse] = {}
_NEXT_ID: int = 1


@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Liveness health check endpoint."""
    return HealthResponse(status="ok", version="1.0.0", service="backend")


@app.get("/api/items", response_model=List[ItemResponse])
async def list_items():
    """Retrieve all items."""
    return list(_ITEMS_DB.values())


@app.post("/api/items", response_model=ItemResponse)
async def create_item(payload: ItemCreate):
    """Create a new item record."""
    global _NEXT_ID
    item_id = _NEXT_ID
    _NEXT_ID += 1
    new_item = ItemResponse(
        id=item_id,
        title=payload.title,
        description=payload.description,
        status=payload.status,
    )
    _ITEMS_DB[item_id] = new_item
    return new_item
'''
            tools.write_file("backend/app/main.py", main_content)
            files_created.append("backend/app/main.py")
            summary = "Implemented FastAPI endpoints for health check and item CRUD operations."

        elif task.task_id == "TASK-004":
            # Tests: backend/tests/__init__.py and backend/tests/test_api.py
            tools.write_file("backend/tests/__init__.py", '"""Backend tests package."""\n')
            files_created.append("backend/tests/__init__.py")

            test_content = '''"""
Automated integration test suite for FastAPI backend.
"""

import pytest
import httpx
from app.main import app


@pytest.mark.asyncio
async def test_health_check_endpoint():
    """Assert /api/health returns 200 OK and status ok."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "backend"


@pytest.mark.asyncio
async def test_create_and_list_items():
    """Assert item creation and listing flow."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Create item
        res = await client.post("/api/items", json={"title": "Test Task Item", "description": "Verify task flow"})
        assert res.status_code == 200
        item = res.json()
        assert item["title"] == "Test Task Item"
        assert item["id"] >= 1

        # List items
        list_res = await client.get("/api/items")
        assert list_res.status_code == 200
        items = list_res.json()
        assert len(items) >= 1
'''
            tools.write_file("backend/tests/test_api.py", test_content)
            files_created.append("backend/tests/test_api.py")
            summary = "Created comprehensive pytest test suite asserting health and item operations."

        elif task.task_id == "TASK-005":
            # Frontend package.json
            pkg_json = '''{
  "name": "projectforge-generated-frontend",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "typescript": "^5.0.0",
    "vite": "6.4.5"
  }
}
'''
            tools.write_file("frontend/package.json", pkg_json)
            files_created.append("frontend/package.json")
            tools.write_file("frontend/index.html", '<!doctype html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Generated App</title></head><body><div id="root"></div><script type="module" src="/src/main.tsx"></script></body></html>')
            tools.write_file("frontend/tsconfig.json", json.dumps({"compilerOptions": {"target": "ES2020", "lib": ["ES2020", "DOM", "DOM.Iterable"], "module": "ESNext", "moduleResolution": "bundler", "jsx": "react-jsx", "strict": True, "skipLibCheck": True, "esModuleInterop": True, "allowSyntheticDefaultImports": True, "noEmit": True}, "include": ["src"]}, indent=2))
            tools.write_file("frontend/vite.config.ts", "import { defineConfig } from 'vite';\nexport default defineConfig({ server: { port: 3001, proxy: { '/api': 'http://127.0.0.1:8001' } } });\n")
            files_created.extend(["frontend/index.html", "frontend/tsconfig.json", "frontend/vite.config.ts"])
            summary = "Created React frontend package.json manifest."

        elif task.task_id == "TASK-006":
            # Frontend App.tsx
            app_tsx = '''import React, { useState, useEffect } from 'react';

export const App: React.FC = () => {
  const [items, setItems] = useState<any[]>([]);
  const [title, setTitle] = useState('');

  useEffect(() => {
    fetch('/api/items')
      .then((r) => r.json())
      .then((data) => setItems(data))
      .catch((err) => console.warn('Fetch items offline:', err));
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title) return;
    try {
      const res = await fetch('/api/items', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title }),
      });
      const newItem = await res.json();
      setItems((prev) => [...prev, newItem]);
      setTitle('');
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div style={{ padding: 24, fontFamily: 'sans-serif' }}>
      <h1>ProjectForge Generated Application</h1>
      <form onSubmit={handleCreate}>
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="New Item Title"
        />
        <button type="submit">Add Item</button>
      </form>
      <ul>
        {items.map((it) => (
          <li key={it.id}>{it.title}</li>
        ))}
      </ul>
    </div>
  );
};

export default App;
'''
            tools.write_file("frontend/src/App.tsx", app_tsx)
            files_created.append("frontend/src/App.tsx")
            tools.write_file("frontend/src/main.tsx", "import React from 'react';\nimport { createRoot } from 'react-dom/client';\nimport App from './App';\ncreateRoot(document.getElementById('root')!).render(<React.StrictMode><App /></React.StrictMode>);\n")
            files_created.append("frontend/src/main.tsx")
            summary = "Created React application component communicating with backend API."

        if not summary:
            raise ValueError(f"Unsupported template task: {task.task_id}")
        return TaskImplementationResult(
            task_id=task.task_id,
            files_created=files_created,
            files_modified=files_modified,
            implementation_summary=summary,
            commands_requested=[],
            tests_requested=task.tests,
            assumptions=[],
            warnings=[],
        )
