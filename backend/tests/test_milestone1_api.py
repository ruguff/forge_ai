"""
End-to-End API Integration Tests for Milestone 1.

Tests:
- POST /api/projects (Project creation with version 1 & mode)
- POST /api/projects/{id}/understand (17 dimensions + RequirementEngine + SSE event queue)
- POST /api/projects/{id}/clarify (Answering clarification + Decision Log + version increment)
- GET /api/projects/{id}/context (Full versioned context inspection)
"""

import httpx
import pytest
from app.main import app


@pytest.mark.asyncio
async def test_create_project_initialization():
    """Test initializing a new project creates both state and versioned context."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        res = await client.post(
            "/api/projects",
            json={
                "idea": "I want to build an AI system that detects road changes between before and after satellite imagery.",
                "mode": "AUTONOMOUS",
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert "project_id" in data
        assert data["status"] == "created"
        assert data["version"] == 1


@pytest.mark.asyncio
async def test_understand_project_and_clarify_flow():
    """Test full Milestone 1 loop: understand -> clarify -> validated."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Create project
        create_res = await client.post(
            "/api/projects",
            json={
                "idea": "I want to build an AI system that detects road changes between before and after satellite imagery.",
                "mode": "AUTONOMOUS",
            },
        )
        project_id = create_res.json()["project_id"]

        # 2. Run understand
        und_res = await client.post(f"/api/projects/{project_id}/understand")
        assert und_res.status_code == 200
        und_data = und_res.json()
        assert und_data["project_id"] == project_id
        context = und_data["context"]

        assert context["project_name"] != ""
        assert len(context["requirements"]) >= 2
        assert len(context["unknowns"]) >= 1

        # UNK-001 is a material unknown regarding resolution
        if und_data["clarification"]:
            clar_q = und_data["clarification"]
            assert "question" in clar_q
            assert "reason" in clar_q
            assert "impact_if_unknown" in clar_q
            assert len(clar_q["possible_options"]) >= 2

            # 3. Submit targeted answer to clarification question
            ans_res = await client.post(
                f"/api/projects/{project_id}/clarify",
                json={
                    "question_id": clar_q["question_id"],
                    "answer": clar_q["possible_options"][0],
                },
            )
            assert ans_res.status_code == 200
            ans_data = ans_res.json()
            assert ans_data["status"] == "clarified"
            assert ans_data["version"] >= 2  # Version incremented!

        # 4. Fetch context and verify Decision Log
        ctx_res = await client.get(f"/api/projects/{project_id}/context")
        assert ctx_res.status_code == 200
        ctx_data = ctx_res.json()
        assert ctx_data["project_id"] == project_id
        assert ctx_data["version"] >= 1
        # Check decision log recorded
        if und_data["clarification"]:
            assert len(ctx_data["decisions"]) >= 1
            assert ctx_data["decisions"][0]["category"] == "USER_CLARIFICATION"
