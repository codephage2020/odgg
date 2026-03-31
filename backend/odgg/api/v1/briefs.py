"""Modeling Brief CRUD + section management + SSE cascade drafting."""

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sse_starlette.sse import EventSourceResponse

from odgg.core.database import async_session, get_db
from odgg.models.brief import (
    BriefCreate,
    BriefListItem,
    BriefResponse,
    BriefRow,
    BriefUpdate,
    RegenerateRequest,
    SectionCreate,
    SectionResponse,
    SectionRow,
    SectionType,
    SectionUpdate,
)
from odgg.models.metadata import MetadataSnapshot
from odgg.services.codegen import generate_brief_export
from odgg.services.modeling_engine import (
    suggest_business_process,
    suggest_dimensions,
    suggest_grain,
    suggest_measures,
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
        selected_tables=row.selected_tables,
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
        selected_tables=body.selected_tables,
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
    """Update brief title, status, or selected tables."""
    brief = await _get_brief_or_404(brief_id, db)
    if body.title is not None:
        brief.title = body.title
    if body.status is not None:
        brief.status = body.status.value
    if body.selected_tables is not None:
        brief.selected_tables = body.selected_tables
    await db.commit()
    await db.refresh(brief, ["sections"])
    return _brief_to_response(brief)


@router.get("/{brief_id}/export", response_class=PlainTextResponse)
async def export_brief(brief_id: str, db: AsyncSession = Depends(get_db)):
    """Export a brief as stakeholder-friendly Markdown."""
    brief = await _get_brief_or_404(brief_id, db)
    sorted_sections = sorted(brief.sections, key=lambda s: s.position)
    md = generate_brief_export(
        title=brief.title,
        status=brief.status,
        source_db_type=brief.source_db_type,
        database_name=brief.database_name,
        updated_at=brief.updated_at.isoformat(),
        sections=[
            {"section_type": s.section_type, "content": s.content or ""}
            for s in sorted_sections
        ],
    )
    return PlainTextResponse(content=md, media_type="text/markdown")


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

    # Prevent duplicate section types (except dimension/measure which can have multiple)
    multi_allowed = {"dimension", "measure"}
    if body.section_type.value not in multi_allowed:
        existing = [s for s in brief.sections if s.section_type == body.section_type.value]
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"此 Brief 已有 {body.section_type.value} 章节",
            )

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
    body: RegenerateRequest | None = None,
    db: AsyncSession = Depends(get_db),
) -> SectionResponse:
    """Regenerate AI draft for a section.

    Optionally accepts user instructions to guide the re-draft.
    Appends the new draft to ai_drafts history and replaces content.
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

    # Load brief for metadata context
    brief = await _get_brief_or_404(brief_id, db)
    snapshot = MetadataSnapshot(**(brief.metadata_snapshot or {}))

    instructions = body.instructions if body else None
    new_draft = await _draft_section_content(
        section.section_type, brief, snapshot, instructions=instructions,
    )
    drafts = list(section.ai_drafts or [])
    drafts.append(new_draft)
    section.ai_drafts = drafts
    section.content = new_draft
    section.user_edited = False

    await db.commit()
    await db.refresh(section)
    return _section_to_response(section)


# ---------------------------------------------------------------------------
# Code Generation from Brief
# ---------------------------------------------------------------------------


@router.post("/{brief_id}/generate")
async def generate_from_brief(
    brief_id: str,
    include_dbt: bool = True,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Generate DDL, ETL, and dbt code from a brief's sections.

    Uses the Protocol-based ModelSource bridge to extract structured
    data from brief sections and feed it into the codegen engine.
    """
    from odgg.services.brief_bridge import BriefModelSource, build_model_from_source
    from odgg.services.codegen import (
        generate_data_dictionary,
        generate_dbt_model,
        generate_ddl,
        generate_etl,
    )

    brief = await _get_brief_or_404(brief_id, db)
    source = BriefModelSource(brief)

    # Validate we have enough data
    if not source.get_business_process():
        raise HTTPException(
            status_code=400,
            detail="Brief has no business process section — draft sections first",
        )
    if not source.get_measures():
        raise HTTPException(
            status_code=400,
            detail="Brief has no measure sections — add measures first",
        )

    model = build_model_from_source(source)

    result = {
        "ddl": generate_ddl(model),
        "etl": generate_etl(model),
        "data_dictionary": generate_data_dictionary(model),
    }

    if include_dbt:
        result["dbt"] = generate_dbt_model(model)

    return result


# ---------------------------------------------------------------------------
# SSE Cascade Drafting
# ---------------------------------------------------------------------------


async def _draft_section_content(
    section_type: str,
    brief: BriefRow,
    snapshot: MetadataSnapshot,
    *,
    business_process: str = "",
    grain_description: str = "",
    dimensions: list | None = None,
    selected_tables: list[str] | None = None,
    instructions: str | None = None,
) -> str:
    """Generate AI draft content for a section type.

    Uses the modeling engine's decoupled functions.
    Falls back to placeholder if no metadata available.
    When instructions are provided, they're appended to the LLM prompt.
    """
    dimensions = dimensions or []

    if not snapshot.tables:
        return "[No metadata available — connect a database first]"

    try:
        if section_type == SectionType.BUSINESS_PROCESS:
            result = await suggest_business_process(
                snapshot, selected_tables, instructions=instructions,
            )
            processes = result.get("processes", [])
            if processes:
                bp = processes[0]
                return (
                    f"**{bp.get('name', 'Unknown')}**\n\n"
                    f"{bp.get('description', '')}\n\n"
                    f"Involved tables: {', '.join(bp.get('involved_tables', []))}"
                )
            return "[AI could not identify a business process]"

        elif section_type == SectionType.GRAIN:
            result = await suggest_grain(
                business_process, snapshot, selected_tables, instructions=instructions,
            )
            options = result.get("options", [])
            recommended = next((o for o in options if o.get("recommended")), None)
            opt = recommended or (options[0] if options else None)
            if opt:
                return (
                    f"{opt.get('description', '')}\n\n"
                    f"Grain columns: {', '.join(opt.get('grain_columns', []))}\n"
                    f"Reasoning: {opt.get('reasoning', '')}"
                )
            return "[AI could not determine grain]"

        elif section_type == SectionType.DIMENSION:
            result = await suggest_dimensions(
                business_process, grain_description, snapshot, selected_tables,
                instructions=instructions,
            )
            dims = result.get("dimensions", [])
            if dims:
                lines = []
                for d in dims:
                    lines.append(
                        f"- **{d.get('name', '?')}** "
                        f"({d.get('source_table', '?')}): "
                        f"{d.get('description', '')}"
                    )
                return "\n".join(lines)
            return "[AI could not suggest dimensions]"

        elif section_type == SectionType.MEASURE:
            result = await suggest_measures(
                business_process, grain_description, dimensions, snapshot, selected_tables,
                instructions=instructions,
            )
            measures = result.get("measures", [])
            if measures:
                lines = []
                for m in measures:
                    lines.append(
                        f"- **{m.get('name', '?')}** "
                        f"({m.get('aggregation', 'SUM')} of "
                        f"{m.get('source_column', '?')}): "
                        f"{m.get('description', '')}"
                    )
                return "\n".join(lines)
            return "[AI could not suggest measures]"

        else:
            return ""

    except Exception as e:
        logger.error("AI draft failed for %s: %s", section_type, e)
        return "[AI draft failed — check server logs for details]"


async def _run_cascade(
    brief_id: str,
    title: str,
    snapshot: MetadataSnapshot,
    db: AsyncSession,
    selected_tables: list[str] | None = None,
) -> list[SectionResponse]:
    """Execute the 2-stage AI cascade and persist sections.

    Stage 1: Business Process → Grain (sequential)
    Stage 2: Dimensions + Measures (parallel)
    Returns list of created section responses.
    """
    results: list[SectionResponse] = []

    # --- Stage 1a: Business Process ---
    brief = await _get_brief_or_404(brief_id, db)
    bp_text = await _draft_section_content(
        SectionType.BUSINESS_PROCESS, brief, snapshot, selected_tables=selected_tables
    )
    bp_section = SectionRow(
        brief_id=brief_id,
        section_type=SectionType.BUSINESS_PROCESS,
        position=0,
        content=bp_text,
        ai_drafts=[bp_text],
    )
    db.add(bp_section)
    await db.flush()
    results.append(_section_to_response(bp_section))

    # Extract BP name for downstream prompts
    bp_name = bp_text.split("**")[1] if "**" in bp_text else bp_text[:100]

    # --- Stage 1b: Grain ---
    grain_text = await _draft_section_content(
        SectionType.GRAIN,
        brief,
        snapshot,
        business_process=bp_name,
        selected_tables=selected_tables,
    )
    grain_section = SectionRow(
        brief_id=brief_id,
        section_type=SectionType.GRAIN,
        position=1,
        content=grain_text,
        ai_drafts=[grain_text],
    )
    db.add(grain_section)
    await db.flush()
    results.append(_section_to_response(grain_section))

    # --- Stage 2: Dimensions + Measures (parallel) ---
    dim_text, measure_text = await asyncio.gather(
        _draft_section_content(
            SectionType.DIMENSION,
            brief,
            snapshot,
            business_process=bp_name,
            grain_description=grain_text,
            selected_tables=selected_tables,
        ),
        _draft_section_content(
            SectionType.MEASURE,
            brief,
            snapshot,
            business_process=bp_name,
            grain_description=grain_text,
            dimensions=[],
            selected_tables=selected_tables,
        ),
    )

    dim_section = SectionRow(
        brief_id=brief_id,
        section_type=SectionType.DIMENSION,
        position=2,
        content=dim_text,
        ai_drafts=[dim_text],
    )
    measure_section = SectionRow(
        brief_id=brief_id,
        section_type=SectionType.MEASURE,
        position=3,
        content=measure_text,
        ai_drafts=[measure_text],
    )
    db.add(dim_section)
    db.add(measure_section)
    await db.commit()

    results.append(_section_to_response(dim_section))
    results.append(_section_to_response(measure_section))
    return results


@router.api_route("/{brief_id}/draft", methods=["GET", "POST"])
async def draft_brief_sections(
    brief_id: str,
    stream: bool = True,
    db: AsyncSession = Depends(get_db),
):
    """Draft all brief sections via 2-stage AI cascade.

    With ?stream=true (default): returns SSE events as sections complete.
    With ?stream=false: returns JSON array of all created sections.

    Stage 1: Business Process → Grain (sequential, ~6s)
    Stage 2: Dimensions + Measures (parallel, ~5s)
    Total: ~11s with progressive section delivery.
    """
    brief = await _get_brief_or_404(brief_id, db)

    if not brief.metadata_snapshot or not brief.metadata_snapshot.get("tables"):
        raise HTTPException(
            status_code=400,
            detail="Brief has no metadata snapshot — connect a database first",
        )

    # Guard: delete existing sections before re-drafting (prevents duplicates)
    if brief.sections:
        for sec in list(brief.sections):
            await db.delete(sec)
        await db.commit()
        # Refresh to clear stale references
        await db.refresh(brief)

    snapshot = MetadataSnapshot(**brief.metadata_snapshot)
    sel_tables = brief.selected_tables

    if not stream:
        # Synchronous JSON mode — easier to test
        sections = await _run_cascade(brief_id, brief.title, snapshot, db, sel_tables)
        return [s.model_dump() for s in sections]

    # SSE streaming mode
    async def event_generator():
        try:
            async with async_session() as sse_db:
                sse_brief = await _get_brief_or_404(brief_id, sse_db)

                # Sections already deleted by outer guard before SSE starts

                # Stage 1a: BP
                yield _sse_event("drafting", {"section": "business_process"})
                bp_text = await _draft_section_content(
                    SectionType.BUSINESS_PROCESS, sse_brief, snapshot,
                    selected_tables=sel_tables,
                )
                bp_section = SectionRow(
                    brief_id=brief_id,
                    section_type=SectionType.BUSINESS_PROCESS,
                    position=0,
                    content=bp_text,
                    ai_drafts=[bp_text],
                )
                sse_db.add(bp_section)
                await sse_db.flush()
                yield _sse_event(
                    "section_ready",
                    {
                        "section": "business_process",
                        "data": _section_to_response(bp_section).model_dump(),
                    },
                )

                bp_name = bp_text.split("**")[1] if "**" in bp_text else bp_text[:100]

                # Stage 1b: Grain
                yield _sse_event("drafting", {"section": "grain"})
                grain_text = await _draft_section_content(
                    SectionType.GRAIN,
                    sse_brief,
                    snapshot,
                    business_process=bp_name,
                    selected_tables=sel_tables,
                )
                grain_section = SectionRow(
                    brief_id=brief_id,
                    section_type=SectionType.GRAIN,
                    position=1,
                    content=grain_text,
                    ai_drafts=[grain_text],
                )
                sse_db.add(grain_section)
                await sse_db.flush()
                yield _sse_event(
                    "section_ready",
                    {
                        "section": "grain",
                        "data": _section_to_response(grain_section).model_dump(),
                    },
                )

                # Stage 2: Dims + Measures (parallel)
                yield _sse_event("drafting", {"section": "dimensions_and_measures"})
                dim_text, measure_text = await asyncio.gather(
                    _draft_section_content(
                        SectionType.DIMENSION,
                        sse_brief,
                        snapshot,
                        business_process=bp_name,
                        grain_description=grain_text,
                        selected_tables=sel_tables,
                    ),
                    _draft_section_content(
                        SectionType.MEASURE,
                        sse_brief,
                        snapshot,
                        business_process=bp_name,
                        grain_description=grain_text,
                        dimensions=[],
                        selected_tables=sel_tables,
                    ),
                )

                dim_section = SectionRow(
                    brief_id=brief_id,
                    section_type=SectionType.DIMENSION,
                    position=2,
                    content=dim_text,
                    ai_drafts=[dim_text],
                )
                measure_section = SectionRow(
                    brief_id=brief_id,
                    section_type=SectionType.MEASURE,
                    position=3,
                    content=measure_text,
                    ai_drafts=[measure_text],
                )
                sse_db.add(dim_section)
                sse_db.add(measure_section)
                await sse_db.commit()

                yield _sse_event(
                    "section_ready",
                    {
                        "section": "dimension",
                        "data": _section_to_response(dim_section).model_dump(),
                    },
                )
                yield _sse_event(
                    "section_ready",
                    {
                        "section": "measure",
                        "data": _section_to_response(measure_section).model_dump(),
                    },
                )

                yield _sse_event("done", {"sections_created": 4})

        except Exception as e:
            logger.error("Cascade drafting failed for brief %s: %s", brief_id, e)
            yield _sse_event("error", {"error": str(e)[:500]})

    return EventSourceResponse(event_generator())


def _sse_event(event: str, data: dict) -> dict:
    """Format an SSE event dict for EventSourceResponse."""
    return {"event": event, "data": json.dumps(data, default=str)}
