"""
ProjectForge AI — SQLAlchemy ORM Models.

Defines the ``ProjectRecord`` table that persists all project data and
every specification produced by the agent pipeline.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.types import JSON

from app.database import Base


def _utcnow() -> datetime:
    """Return timezone-aware UTC now."""
    return datetime.now(timezone.utc)


def _new_uuid() -> str:
    """Generate a new UUID4 string."""
    return str(uuid.uuid4())


class ProjectRecord(Base):
    """Persistent record for a single ProjectForge project."""

    __tablename__ = "projects"

    id = Column(
        String(36),
        primary_key=True,
        default=_new_uuid,
        nullable=False,
    )
    idea = Column(Text, nullable=False)
    status = Column(
        String(64),
        nullable=False,
        default="INTAKE",
        index=True,
    )
    revision = Column(Integer, nullable=False, default=1)

    # --- Specification payloads (stored as JSON) --------------------------
    intake_qa = Column(JSON, nullable=False)
    product_spec = Column(JSON, nullable=True)
    ai_spec = Column(JSON, nullable=True)
    engineering_spec = Column(JSON, nullable=True)
    ux_spec = Column(JSON, nullable=True)
    security_report = Column(JSON, nullable=True)
    qa_spec = Column(JSON, nullable=True)

    # --- Conflict resolution & output ------------------------------------
    conflicts = Column(JSON, nullable=False, default=list)
    blueprint_markdown = Column(Text, nullable=True)
    audit_matrix = Column(JSON, nullable=False, default=dict)

    # --- Timestamps -------------------------------------------------------
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        onupdate=_utcnow,
    )

    # Explicit index on status for fast pipeline-stage queries
    __table_args__ = (
        Index("ix_projects_status", "status"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<ProjectRecord id={self.id!r} status={self.status!r} "
            f"revision={self.revision}>"
        )
