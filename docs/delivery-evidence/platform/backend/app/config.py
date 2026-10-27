"""
ProjectForge AI — Application Configuration.

Uses pydantic-settings to load environment variables with sensible defaults.
"""

from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration loaded from environment variables / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    GEMINI_API_KEY: str = Field(
        "",
        description="API key for Google Gemini generative AI service.",
    )

    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./projectforge.db",
        description="Async SQLAlchemy database URL.",
    )

    GEMINI_MODEL: str = "gemini-3.8-flash"
    LLM_PROVIDER: str = "gemini"
    LOCAL_MODEL_BASE_URL: str = "http://127.0.0.1:1234/v1"
    LOCAL_MODEL_NAME: str = "nvidia/nemotron-3-nano-4b"
    LOCAL_MODEL_REASONING_EFFORT: str = ""
    LOCAL_CODE_GENERATION_STRATEGY: str = "declarative_crud"
    MODEL_TIMEOUT_SECONDS: float = 90.0
    MAX_MODEL_CALLS: int = 40
    MAX_MODEL_INPUT_CHARS: int = 180000
    MAX_MODEL_OUTPUT_TOKENS: int = 16384
    PIPELINE_TIMEOUT_SECONDS: float = 900.0

    ENVIRONMENT: str = Field(
        default="development",
        description="Runtime environment (development | staging | production).",
    )

    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:5173"],
        description="Allowed CORS origins for the frontend.",
    )


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings singleton."""
    return Settings()
