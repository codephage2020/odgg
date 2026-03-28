"""Modeling Brief ORM models — SQLAlchemy + Pydantic schemas.

The brief is a structured document with editable sections for Kimball
dimensional model discovery. AI drafts each section from discovered
schema metadata; the user edits inline.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, field_validator
from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from odgg.core.database import Base

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class BriefStatus(StrEnum):
    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    EXPORTED = "exported"


class SectionType(StrEnum):
    BUSINESS_PROCESS = "business_process"
    GRAIN = "grain"
    DIMENSION = "dimension"
    MEASURE = "measure"
    RELATIONSHIP = "relationship"
    NOTES = "notes"


class DimensionType(StrEnum):
    REGULAR = "regular"
    DEGENERATE = "degenerate"
    JUNK = "junk"
    ROLE_PLAYING = "role_playing"


class AggregationType(StrEnum):
    SUM = "sum"
    COUNT = "count"
    AVG = "avg"
    MIN = "min"
    MAX = "max"
    COUNT_DISTINCT = "count_distinct"


# ---------------------------------------------------------------------------
# SQLAlchemy ORM Models
# ---------------------------------------------------------------------------


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _uuid() -> str:
    return str(uuid.uuid4())


class BriefRow(Base):
    """Modeling brief — the top-level document."""

    __tablename__ = "briefs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(String(255), default="Untitled Brief")
    status: Mapped[str] = mapped_column(String(20), default=BriefStatus.DRAFT.value)

    # DB connection context (no credentials stored)
    source_db_type: Mapped[str] = mapped_column(String(50), default="postgresql")
    database_name: Mapped[str] = mapped_column(String(255), default="")

    # Schema snapshot stored as JSON blob
    metadata_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # User-selected tables for LLM context (None = all tables)
    selected_tables: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    # Relationships
    sections: Mapped[list[SectionRow]] = relationship(
        back_populates="brief",
        cascade="all, delete-orphan",
        order_by="SectionRow.position",
    )


class SectionRow(Base):
    """A single section of a modeling brief."""

    __tablename__ = "brief_sections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    brief_id: Mapped[str] = mapped_column(String(36), ForeignKey("briefs.id", ondelete="CASCADE"))
    section_type: Mapped[str] = mapped_column(String(30))
    position: Mapped[int] = mapped_column(Integer, default=0)

    # Content
    content: Mapped[str] = mapped_column(Text, default="")
    ai_drafts: Mapped[list[str]] = mapped_column(JSON, default=list)  # Append-only history
    user_edited: Mapped[bool] = mapped_column(default=False)

    # Structured fields for typed sections (dimension/measure/relationship)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_table: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_columns: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    source_column: Mapped[str | None] = mapped_column(String(255), nullable=True)
    data_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    dimension_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    scd_type: Mapped[int | None] = mapped_column(Integer, nullable=True)
    aggregation_type: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Relationship fields
    from_dimension: Mapped[str | None] = mapped_column(String(255), nullable=True)
    to_fact: Mapped[str | None] = mapped_column(String(255), nullable=True)
    join_column: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cardinality: Mapped[str | None] = mapped_column(String(20), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    # Back-reference
    brief: Mapped[BriefRow] = relationship(back_populates="sections")


# ---------------------------------------------------------------------------
# Pydantic Schemas (API request/response)
# ---------------------------------------------------------------------------


class SectionCreate(BaseModel):
    """Create a new section."""

    section_type: SectionType
    content: str = ""
    name: str | None = None
    source_table: str | None = None
    source_columns: list[str] | None = None
    source_column: str | None = None
    data_type: str | None = None
    dimension_type: DimensionType | None = None
    scd_type: int | None = None
    aggregation_type: AggregationType | None = None
    from_dimension: str | None = None
    to_fact: str | None = None
    join_column: str | None = None
    cardinality: str | None = None


class SectionUpdate(BaseModel):
    """Partial update for a section."""

    content: str | None = None
    name: str | None = None
    source_table: str | None = None
    source_columns: list[str] | None = None
    source_column: str | None = None
    data_type: str | None = None
    dimension_type: DimensionType | None = None
    scd_type: int | None = None
    aggregation_type: AggregationType | None = None
    from_dimension: str | None = None
    to_fact: str | None = None
    join_column: str | None = None
    cardinality: str | None = None


class SectionResponse(BaseModel):
    """Section as returned by the API."""

    id: str
    brief_id: str
    section_type: SectionType
    position: int
    content: str
    ai_drafts: list[str]
    user_edited: bool
    name: str | None = None
    source_table: str | None = None
    source_columns: list[str] | None = None
    source_column: str | None = None
    data_type: str | None = None
    dimension_type: DimensionType | None = None
    scd_type: int | None = None
    aggregation_type: AggregationType | None = None
    from_dimension: str | None = None
    to_fact: str | None = None
    join_column: str | None = None
    cardinality: str | None = None
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


MAX_SELECTED_TABLES = 500


class BriefCreate(BaseModel):
    """Create a new modeling brief."""

    title: str = "Untitled Brief"
    source_db_type: str = "postgresql"
    database_name: str = ""
    metadata_snapshot: dict[str, Any] | None = None
    selected_tables: list[str] | None = None

    @field_validator("selected_tables")
    @classmethod
    def validate_selected_tables(cls, v: list[str] | None) -> list[str] | None:
        if v is not None and len(v) > MAX_SELECTED_TABLES:
            raise ValueError(f"selected_tables cannot exceed {MAX_SELECTED_TABLES} entries")
        return v


class BriefUpdate(BaseModel):
    """Partial update for a brief."""

    title: str | None = None
    status: BriefStatus | None = None
    selected_tables: list[str] | None = None

    @field_validator("selected_tables")
    @classmethod
    def validate_selected_tables(cls, v: list[str] | None) -> list[str] | None:
        if v is not None and len(v) > MAX_SELECTED_TABLES:
            raise ValueError(f"selected_tables cannot exceed {MAX_SELECTED_TABLES} entries")
        return v


class BriefResponse(BaseModel):
    """Brief as returned by the API."""

    id: str
    title: str
    status: BriefStatus
    source_db_type: str
    database_name: str
    metadata_snapshot: dict[str, Any] | None = None
    selected_tables: list[str] | None = None
    sections: list[SectionResponse] = []
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class BriefListItem(BaseModel):
    """Brief summary for list endpoints."""

    id: str
    title: str
    status: BriefStatus
    database_name: str
    section_count: int = 0
    created_at: str
    updated_at: str
