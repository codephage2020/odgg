"""Modeling engine — Kimball 4-step AI-guided dimensional modeling."""

from __future__ import annotations

import json
import logging
from typing import Any

from odgg.models.dimensional import Dimension, DimensionalModel, FactTable, Measure
from odgg.models.metadata import MetadataSnapshot
from odgg.models.session import SessionState, StepStatus
from odgg.services.llm_router import chat_completion
from odgg.services.sanitizer import detect_prompt_injection, sanitize_for_prompt

logger = logging.getLogger(__name__)


def _build_metadata_context(snapshot: MetadataSnapshot) -> str:
    """Build a sanitized metadata summary for LLM context."""
    lines = [f"Database: {sanitize_for_prompt(snapshot.database_name)}"]
    lines.append(f"Tables ({len(snapshot.tables)}):")

    for table in snapshot.tables:
        cols = ", ".join(
            f"{sanitize_for_prompt(c.name)} ({c.data_type})"
            for c in table.columns[:20]  # Cap at 20 columns per table
        )
        row_info = f" ~{table.row_count} rows" if table.row_count else ""
        lines.append(f"  - {sanitize_for_prompt(table.name)}{row_info}: [{cols}]")

    lines.append(f"\nRelationships ({len(snapshot.relationships)}):")
    for rel in snapshot.relationships:
        inferred = " (inferred)" if rel.is_inferred else ""
        lines.append(
            f"  - {sanitize_for_prompt(rel.source_table)}.{sanitize_for_prompt(rel.source_column)} "
            f"-> {sanitize_for_prompt(rel.target_table)}.{sanitize_for_prompt(rel.target_column)}{inferred}"
        )

    context = "\n".join(lines)

    # Final injection check on the assembled context
    if detect_prompt_injection(context):
        logger.warning("Potential prompt injection detected in metadata context")
        # Strip the suspicious content but continue with basic table names
        safe_lines = [f"Database: {sanitize_for_prompt(snapshot.database_name)}"]
        safe_lines.append("Tables: " + ", ".join(
            sanitize_for_prompt(t.name) for t in snapshot.tables
        ))
        return "\n".join(safe_lines)

    return context


async def suggest_business_process(
    session: SessionState,
    snapshot: MetadataSnapshot,
) -> dict[str, Any]:
    """Step 3: Suggest business processes based on metadata."""
    context = _build_metadata_context(snapshot)

    messages = [
        {
            "role": "system",
            "content": (
                "You are a Kimball dimensional modeling expert. Analyze the database schema "
                "and suggest business processes suitable for dimensional modeling. "
                "A business process is a measurable event (e.g., order processing, inventory management). "
                "Return JSON with: {\"processes\": [{\"name\": str, \"description\": str, "
                "\"involved_tables\": [str], \"confidence\": float}]}"
            ),
        },
        {
            "role": "user",
            "content": f"Analyze this database and suggest business processes:\n\n{context}",
        },
    ]

    result = await chat_completion(messages)
    return result if isinstance(result, dict) else result.model_dump()


async def suggest_grain(
    session: SessionState,
    snapshot: MetadataSnapshot,
) -> dict[str, Any]:
    """Step 4: Suggest grain for the selected business process."""
    context = _build_metadata_context(snapshot)

    messages = [
        {
            "role": "system",
            "content": (
                "You are a Kimball dimensional modeling expert. Given a business process "
                "and database schema, suggest the appropriate grain (level of detail) for "
                "the fact table. Explain the tradeoffs between different grain options. "
                "Return JSON with: {\"options\": [{\"description\": str, "
                "\"grain_columns\": [str], \"source_table\": str, \"row_count\": int|null, "
                "\"recommended\": bool, \"reasoning\": str}]}"
            ),
        },
        {
            "role": "user",
            "content": (
                f"Business process: {sanitize_for_prompt(session.business_process)}\n\n"
                f"Database schema:\n{context}"
            ),
        },
    ]

    result = await chat_completion(messages)
    return result if isinstance(result, dict) else result.model_dump()


async def suggest_dimensions(
    session: SessionState,
    snapshot: MetadataSnapshot,
) -> dict[str, Any]:
    """Step 5: Suggest dimensions for the fact table."""
    context = _build_metadata_context(snapshot)

    messages = [
        {
            "role": "system",
            "content": (
                "You are a Kimball dimensional modeling expert. Given a business process, "
                "grain, and schema, suggest dimensions for the star schema. Include a date "
                "dimension if time-based data exists. Identify degenerate dimensions. "
                "Return JSON with: {\"dimensions\": [{\"name\": str (use dim_ prefix), "
                "\"source_table\": str, \"columns\": [str], \"natural_key\": str, "
                "\"is_date_dimension\": bool, \"is_degenerate\": bool, "
                "\"description\": str, \"confidence\": float}]}"
            ),
        },
        {
            "role": "user",
            "content": (
                f"Business process: {sanitize_for_prompt(session.business_process)}\n"
                f"Grain: {sanitize_for_prompt(session.grain_description)}\n\n"
                f"Database schema:\n{context}"
            ),
        },
    ]

    result = await chat_completion(messages)
    return result if isinstance(result, dict) else result.model_dump()


async def suggest_measures(
    session: SessionState,
    snapshot: MetadataSnapshot,
) -> dict[str, Any]:
    """Step 6: Suggest measures for the fact table."""
    context = _build_metadata_context(snapshot)

    messages = [
        {
            "role": "system",
            "content": (
                "You are a Kimball dimensional modeling expert. Given a business process, "
                "grain, dimensions, and schema, suggest measures for the fact table. "
                "Identify numeric columns suitable for aggregation. "
                "Return JSON with: {\"measures\": [{\"name\": str, "
                "\"source_column\": str, \"source_table\": str, "
                "\"aggregation\": str (SUM|AVG|COUNT|MIN|MAX|COUNT_DISTINCT), "
                "\"data_type\": str, \"description\": str, \"confidence\": float}]}"
            ),
        },
        {
            "role": "user",
            "content": (
                f"Business process: {sanitize_for_prompt(session.business_process)}\n"
                f"Grain: {sanitize_for_prompt(session.grain_description)}\n"
                f"Dimensions: {json.dumps(session.selected_dimensions)}\n\n"
                f"Database schema:\n{context}"
            ),
        },
    ]

    result = await chat_completion(messages)
    return result if isinstance(result, dict) else result.model_dump()


def build_dimensional_model(session: SessionState) -> DimensionalModel:
    """Step 7: Assemble and validate the dimensional model from session state."""
    dimensions = []
    for dim_data in session.selected_dimensions:
        if isinstance(dim_data, str):
            # Simple string reference — create minimal dimension
            dimensions.append(Dimension(
                name=f"dim_{dim_data}" if not dim_data.startswith("dim_") else dim_data,
                source_table=dim_data.replace("dim_", ""),
            ))
        elif isinstance(dim_data, dict):
            dimensions.append(Dimension(**dim_data))

    measures = [
        Measure(**m) if isinstance(m, dict) else m
        for m in session.selected_measures
    ]

    # Build fact table
    fact = FactTable(
        name=f"fact_{session.business_process.lower().replace(' ', '_')}",
        grain_description=session.grain_description,
        grain_columns=["id"],  # Will be refined from grain selection
        measures=measures,
        dimension_keys=[f"{d.name}_key" for d in dimensions if not d.is_degenerate],
        source_tables=[d.source_table for d in dimensions],
    )

    # Build and validate the complete model
    model = DimensionalModel(
        business_process=session.business_process,
        fact_table=fact,
        dimensions=dimensions,
    )

    return model
