"""
ProjectForge AI — FastAPI Main Application Entry Point.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.endpoints import router as projects_router
from app.config import get_settings

app = FastAPI(
    title="ProjectForge AI",
    description="Multi-Agent Software Architecture System API & SSE Streaming Service",
    version="1.0.0",
)

# CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects_router)


@app.get("/")
async def root():
    return {
        "system": "ProjectForge AI",
        "status": "operational",
        "pipeline": "ready",
        "model_configured": get_settings().LLM_PROVIDER == "lmstudio" or bool(get_settings().GEMINI_API_KEY and not get_settings().GEMINI_API_KEY.startswith("mock")),
        "model_provider": get_settings().LLM_PROVIDER,
    }
