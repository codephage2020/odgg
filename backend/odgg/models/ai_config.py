"""AI configuration ORM model — singleton row for runtime LLM overrides.

Stores user-configured LLM settings that override environment variable defaults.
Uses a single-row pattern (id=1) in SQLite.
"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel
from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from odgg.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


# ---------------------------------------------------------------------------
# SQLAlchemy ORM
# ---------------------------------------------------------------------------


class AiConfigRow(Base):
    """Singleton AI configuration row (always id=1)."""

    __tablename__ = "ai_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    llm_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    llm_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    llm_api_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    llm_base_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    llm_timeout: Mapped[int | None] = mapped_column(Integer, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


# ---------------------------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------------------------


class AiConfigUpdate(BaseModel):
    """Request body for updating AI config. All fields optional."""

    provider: str | None = None
    model: str | None = None
    api_key: str | None = None
    base_url: str | None = None
    timeout: int | None = None


class AiConfigResponse(BaseModel):
    """AI config as returned by the API. API key is always masked."""

    provider: str
    model: str
    api_key_set: bool
    api_key_hint: str
    base_url: str
    timeout: int
    sources: dict[str, str]  # field -> "env" | "user"


class AiConfigTestRequest(BaseModel):
    """Request body for testing an AI connection."""

    provider: str | None = None
    model: str | None = None
    api_key: str | None = None
    base_url: str | None = None
    timeout: int | None = None


class AiConfigTestResponse(BaseModel):
    """Result of an AI connection test."""

    ok: bool
    message: str
    latency_ms: int | None = None


class AiPreset(BaseModel):
    """A provider preset for quick configuration."""

    label: str
    provider: str
    model: str
    base_url: str
