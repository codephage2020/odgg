"""Metadata snapshot models for discovered database schema."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ColumnInfo(BaseModel):
    """A single column discovered from a source database."""

    name: str
    data_type: str
    nullable: bool = True
    is_primary_key: bool = False
    default: str | None = None
    comment: str | None = None
    # Statistics populated during discovery
    distinct_count: int | None = None
    null_count: int | None = None
    sample_values: list[str] = Field(default_factory=list, max_length=5)


class RelationshipInfo(BaseModel):
    """A foreign key or inferred relationship between tables."""

    source_table: str
    source_column: str
    target_table: str
    target_column: str
    is_inferred: bool = False  # True if heuristic-detected, not FK-based
    confidence: float = 1.0  # 1.0 for FK-based, <1.0 for inferred


class TableInfo(BaseModel):
    """Metadata for a single source table."""

    name: str
    schema_name: str = "public"
    columns: list[ColumnInfo] = Field(default_factory=list)
    row_count: int | None = None
    comment: str | None = None
    primary_key: list[str] = Field(default_factory=list)


class MetadataSnapshot(BaseModel):
    """Complete snapshot of discovered database metadata."""

    tables: list[TableInfo] = Field(default_factory=list)
    relationships: list[RelationshipInfo] = Field(default_factory=list)
    database_name: str = ""
    database_type: str = "postgresql"
    discovered_at: str = ""  # ISO 8601 timestamp
