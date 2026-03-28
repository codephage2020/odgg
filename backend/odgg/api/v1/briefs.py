"""Modeling Brief CRUD + section management endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from odgg.core.database import get_db
from odgg.models.brief import (
    BriefCreate,
    BriefListItem,
    BriefResponse,
    BriefRow,
    BriefUpdate,
    SectionCreate,
    SectionResponse,
    SectionRow,
    SectionUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/briefs", tags=["briefs"])

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _section_to_response(row: SectionRow) -> SectionResponse:
    """Convert ORM row to API response, handling datetime serialization."""
    return SectionResponse(
        id=row.id,
        brief_id=row.brief_id,
        section_type=row.section_type,
        position=row.position,
        content=row.content,
        ai_drafts=row.ai_drafts or [],
        user_edited=row.user_edited,
        name=row.name,
        source_table=row.source_table,
        source_columns=row.source_columns,
        source_column=row.source_column,
        data_type=row.data_type,
        dimension_type=row.dimension_type,
        scd_type=row.scd_type,
        aggregation_type=row.aggregation_type,
        from_dimension=row.from_dimension,
        to_fact=row.to_fact,
        join_column=row.join_column,
        cardinality=row.cardinality,
        created_at=row.created_at.isoformat(),
        updated_at=row.updated_at.isoformat(),
    )


def _brief_to_response(row: BriefRow) -> BriefResponse:
    """Convert ORM row to API response."""
    return BriefResponse(
        id=row.id,
        title=row.title,
        status=row.status,
        source_db_type=row.source_db_type,
        database_name=row.database_name,
        metadata_snapshot=row.metadata_snapshot,
        sections=[_section_to_response(s) for s in row.sections],
        created_at=row.created_at.isoformat(),
        updated_at=row.updated_at.isoformat(),
    )


async def _get_brief_or_404(brief_id: str, db: AsyncSession) -> BriefRow:
    """Load a brief with sections or raise 404."""
    stmt = select(BriefRow).options(selectinload(BriefRow.sections)).where(BriefRow.id == brief_id)
    result = await db.execute(stmt)
    brief = result.scalar_one_or_none()
    if brief is None:
        raise HTTPException(status_code=404, detail=f"Brief {brief_id} not found")
    return brief


# ---------------------------------------------------------------------------
# Brief CRUD
# ---------------------------------------------------------------------------


@router.post("", response_model=BriefResponse, status_code=201)
async def create_brief(body: BriefCreate, db: AsyncSession = Depends(get_db)) -> BriefResponse:
    """Create a new modeling brief."""
    brief = BriefRow(
        title=body.title,
        source_db_type=body.source_db_type,
        database_name=body.database_name,
        metadata_snapshot=body.metadata_snapshot,
    )
    db.add(brief)
    await db.commit()
    await db.refresh(brief, ["sections"])
    logger.info("Created brief %s: %s", brief.id, brief.title)
    return _brief_to_response(brief)


@router.get("", response_model=list[BriefListItem])
async def list_briefs(db: AsyncSession = Depends(get_db)) -> list[BriefListItem]:
    """List all briefs with section counts."""
    # Subquery for section count
    section_count = (
        select(
            SectionRow.brief_id,
            func.count(SectionRow.id).label("section_count"),
        )
        .group_by(SectionRow.brief_id)
        .subquery()
    )
    stmt = select(
        BriefRow,
        func.coalesce(section_count.c.section_count, 0).label("section_count"),
    ).outerjoin(section_count, BriefRow.id == section_count.c.brief_id)

    result = await db.execute(stmt)
    return [
        BriefListItem(
            id=row.BriefRow.id,
            title=row.BriefRow.title,
            status=row.BriefRow.status,
            database_name=row.BriefRow.database_name,
            section_count=row.section_count,
            created_at=row.BriefRow.created_at.isoformat(),
            updated_at=row.BriefRow.updated_at.isoformat(),
        )
        for row in result.all()
    ]


@router.get("/{brief_id}", response_model=BriefResponse)
async def get_brief(brief_id: str, db: AsyncSession = Depends(get_db)) -> BriefResponse:
    """Get a brief with all sections."""
    brief = await _get_brief_or_404(brief_id, db)
    return _brief_to_response(brief)


@router.patch("/{brief_id}", response_model=BriefResponse)
async def update_brief(
    brief_id: str, body: BriefUpdate, db: AsyncSession = Depends(get_db)
) -> BriefResponse:
    """Update brief title or status."""
    brief = await _get_brief_or_404(brief_id, db)
    if body.title is not None:
        brief.title = body.title
    if body.status is not None:
        brief.status = body.status.value
    await db.commit()
    await db.refresh(brief, ["sections"])
    return _brief_to_response(brief)


@router.delete("/{brief_id}", status_code=204)
async def delete_brief(brief_id: str, db: AsyncSession = Depends(get_db)) -> None:
    """Delete a brief and all its sections."""
    brief = await _get_brief_or_404(brief_id, db)
    await db.delete(brief)
    await db.commit()
    logger.info("Deleted brief %s", brief_id)


# ---------------------------------------------------------------------------
# Section CRUD
# ---------------------------------------------------------------------------


@router.post(
    "/{brief_id}/sections",
    response_model=SectionResponse,
    status_code=201,
)
async def create_section(
    brief_id: str,
    body: SectionCreate,
    db: AsyncSession = Depends(get_db),
) -> SectionResponse:
    """Add a section to a brief."""
    brief = await _get_brief_or_404(brief_id, db)

    # Auto-position: append after last section
    max_pos = max((s.position for s in brief.sections), default=-1)

    section = SectionRow(
        brief_id=brief_id,
        section_type=body.section_type.value,
        position=max_pos + 1,
        content=body.content,
        name=body.name,
        source_table=body.source_table,
        source_columns=body.source_columns,
        source_column=body.source_column,
        data_type=body.data_type,
        dimension_type=body.dimension_type.value if body.dimension_type else None,
        scd_type=body.scd_type,
        aggregation_type=body.aggregation_type.value if body.aggregation_type else None,
        from_dimension=body.from_dimension,
        to_fact=body.to_fact,
        join_column=body.join_column,
        cardinality=body.cardinality,
    )
    db.add(section)
    await db.commit()
    await db.refresh(section)
    return _section_to_response(section)


@router.patch(
    "/{brief_id}/sections/{section_id}",
    response_model=SectionResponse,
)
async def update_section(
    brief_id: str,
    section_id: str,
    body: SectionUpdate,
    db: AsyncSession = Depends(get_db),
) -> SectionResponse:
    """Update a section's content or structured fields.

    When content changes, marks the section as user-edited.
    """
    stmt = select(SectionRow).where(
        SectionRow.id == section_id,
        SectionRow.brief_id == brief_id,
    )
    result = await db.execute(stmt)
    section = result.scalar_one_or_none()
    if section is None:
        raise HTTPException(
            status_code=404,
            detail=f"Section {section_id} not found in brief {brief_id}",
        )

    update_data = body.model_dump(exclude_unset=True)
    if "content" in update_data and update_data["content"] != section.content:
        section.user_edited = True

    for key, value in update_data.items():
        setattr(section, key, value)

    await db.commit()
    await db.refresh(section)
    return _section_to_response(section)


@router.delete("/{brief_id}/sections/{section_id}", status_code=204)
async def delete_section(
    brief_id: str,
    section_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a section from a brief."""
    stmt = select(SectionRow).where(
        SectionRow.id == section_id,
        SectionRow.brief_id == brief_id,
    )
    result = await db.execute(stmt)
    section = result.scalar_one_or_none()
    if section is None:
        raise HTTPException(
            status_code=404,
            detail=f"Section {section_id} not found in brief {brief_id}",
        )
    await db.delete(section)
    await db.commit()


# ---------------------------------------------------------------------------
# Section AI Operations
# ---------------------------------------------------------------------------


@router.post(
    "/{brief_id}/sections/{section_id}/regenerate",
    response_model=SectionResponse,
)
async def regenerate_section(
    brief_id: str,
    section_id: str,
    db: AsyncSession = Depends(get_db),
) -> SectionResponse:
    """Regenerate AI draft for a section.

    Appends the new draft to ai_drafts history and replaces content.
    Actual LLM call will be wired in the next implementation step.
    """
    stmt = select(SectionRow).where(
        SectionRow.id == section_id,
        SectionRow.brief_id == brief_id,
    )
    result = await db.execute(stmt)
    section = result.scalar_one_or_none()
    if section is None:
        raise HTTPException(
            status_code=404,
            detail=f"Section {section_id} not found in brief {brief_id}",
        )

    # TODO: Wire LLM call here — for now return placeholder
    new_draft = f"[AI draft placeholder for {section.section_type}]"
    drafts = list(section.ai_drafts or [])
    drafts.append(new_draft)
    section.ai_drafts = drafts
    section.content = new_draft
    section.user_edited = False

    await db.commit()
    await db.refresh(section)
    return _section_to_response(section)
