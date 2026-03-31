"""Modeling engine — Kimball 4-step AI-guided dimensional modeling.

All suggest_* functions take plain args (not SessionState) so they can
be called from both the wizard and the brief editor.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from odgg.models.dimensional import Dimension, DimensionalModel, FactTable, Measure
from odgg.models.metadata import MetadataSnapshot
from odgg.services.llm_router import chat_completion
from odgg.services.sanitizer import detect_prompt_injection, sanitize_for_prompt

logger = logging.getLogger(__name__)


MAX_TABLES_FOR_LLM = 50


def _build_metadata_context(
    snapshot: MetadataSnapshot,
    selected_tables: list[str] | None = None,
) -> str:
    """Build a sanitized metadata summary for LLM context.

    When selected_tables is provided, only those tables (and their
    relationships) are included. This prevents token overflow on
    large schemas (500+ tables).
    """
    tables = snapshot.tables
    if selected_tables is not None:
        allowed = set(selected_tables)
        tables = [t for t in tables if t.name in allowed]

    # Server-side guard: cap tables sent to LLM regardless of selection
    if len(tables) > MAX_TABLES_FOR_LLM:
        logger.warning(
            "Capping tables from %d to %d for LLM context", len(tables), MAX_TABLES_FOR_LLM
        )
        tables = tables[:MAX_TABLES_FOR_LLM]

    lines = [f"Database: {sanitize_for_prompt(snapshot.database_name)}"]
    if selected_tables is not None:
        lines.append(
            f"Tables ({len(tables)} selected of {len(snapshot.tables)} total):"
        )
    else:
        lines.append(f"Tables ({len(tables)}):")

    for table in tables:
        cols = ", ".join(
            f"{sanitize_for_prompt(c.name)} ({c.data_type})"
            for c in table.columns[:20]  # Cap at 20 columns per table
        )
        row_info = f" ~{table.row_count} rows" if table.row_count else ""
        lines.append(f"  - {sanitize_for_prompt(table.name)}{row_info}: [{cols}]")

    rels = snapshot.relationships
    if selected_tables is not None:
        allowed = set(selected_tables)
        rels = [r for r in rels if r.source_table in allowed and r.target_table in allowed]

    lines.append(f"\nRelationships ({len(rels)}):")
    for rel in rels:
        inferred = " (inferred)" if rel.is_inferred else ""
        src = f"{sanitize_for_prompt(rel.source_table)}.{sanitize_for_prompt(rel.source_column)}"
        tgt = f"{sanitize_for_prompt(rel.target_table)}.{sanitize_for_prompt(rel.target_column)}"
        lines.append(f"  - {src} -> {tgt}{inferred}")

    context = "\n".join(lines)

    # Final injection check on the assembled context
    if detect_prompt_injection(context):
        logger.warning("Potential prompt injection detected in metadata context")
        # Strip the suspicious content but continue with basic table names
        safe_lines = [f"Database: {sanitize_for_prompt(snapshot.database_name)}"]
        safe_lines.append(
            "Tables: " + ", ".join(sanitize_for_prompt(t.name) for t in tables)
        )
        return "\n".join(safe_lines)

    return context


async def suggest_business_process(
    snapshot: MetadataSnapshot,
    selected_tables: list[str] | None = None,
    *,
    instructions: str | None = None,
) -> dict[str, Any]:
    """Step 3: Suggest business processes based on metadata."""
    context = _build_metadata_context(snapshot, selected_tables)

    user_content = f"Analyze this database and suggest business processes:\n\n{context}"
    if instructions:
        user_content += f"\n\nAdditional instructions: {sanitize_for_prompt(instructions)}"

    messages = [
        {
            "role": "system",
            "content": (
                "You are a Kimball dimensional modeling expert. Analyze the database schema "
                "and suggest business processes suitable for dimensional modeling. "
                "A business process is a measurable event "
                "(e.g., order processing, inventory management). "
                'Return JSON with: {"processes": [{"name": str, "description": str, '
                '"involved_tables": [str], "confidence": float}]}'
            ),
        },
        {"role": "user", "content": user_content},
    ]

    result = await chat_completion(messages)
    return result if isinstance(result, dict) else result.model_dump()


async def suggest_grain(
    business_process: str,
    snapshot: MetadataSnapshot,
    selected_tables: list[str] | None = None,
    *,
    instructions: str | None = None,
) -> dict[str, Any]:
    """Step 4: Suggest grain for the selected business process."""
    context = _build_metadata_context(snapshot, selected_tables)

    user_content = (
        f"Business process: {sanitize_for_prompt(business_process)}\n\n"
        f"Database schema:\n{context}"
    )
    if instructions:
        user_content += f"\n\nAdditional instructions: {sanitize_for_prompt(instructions)}"

    messages = [
        {
            "role": "system",
            "content": (
                "You are a Kimball dimensional modeling expert. Given a business process "
                "and database schema, suggest the appropriate grain (level of detail) for "
                "the fact table. Explain the tradeoffs between different grain options. "
                'Return JSON with: {"options": [{"description": str, '
                '"grain_columns": [str], "source_table": str, "row_count": int|null, '
                '"recommended": bool, "reasoning": str}]}'
            ),
        },
        {"role": "user", "content": user_content},
    ]

    result = await chat_completion(messages)
    return result if isinstance(result, dict) else result.model_dump()


async def suggest_dimensions(
    business_process: str,
    grain_description: str,
    snapshot: MetadataSnapshot,
    selected_tables: list[str] | None = None,
    *,
    instructions: str | None = None,
) -> dict[str, Any]:
    """Step 5: Suggest dimensions for the fact table."""
    context = _build_metadata_context(snapshot, selected_tables)

    user_content = (
        f"Business process: {sanitize_for_prompt(business_process)}\n"
        f"Grain: {sanitize_for_prompt(grain_description)}\n\n"
        f"Database schema:\n{context}"
    )
    if instructions:
        user_content += f"\n\nAdditional instructions: {sanitize_for_prompt(instructions)}"

    messages = [
        {
            "role": "system",
            "content": (
                "You are a Kimball dimensional modeling expert. Given a business process, "
                "grain, and schema, suggest dimensions for the star schema. Include a date "
                "dimension if time-based data exists. Identify degenerate dimensions. "
                'Return JSON with: {"dimensions": [{"name": str (use dim_ prefix), '
                '"source_table": str, "columns": [str], "natural_key": str, '
                '"is_date_dimension": bool, "is_degenerate": bool, '
                '"description": str, "confidence": float}]}'
            ),
        },
        {"role": "user", "content": user_content},
    ]

    result = await chat_completion(messages)
    return result if isinstance(result, dict) else result.model_dump()


async def suggest_measures(
    business_process: str,
    grain_description: str,
    selected_dimensions: list[str | dict[str, Any]],
    snapshot: MetadataSnapshot,
    selected_tables: list[str] | None = None,
    *,
    instructions: str | None = None,
) -> dict[str, Any]:
    """Step 6: Suggest measures for the fact table."""
    context = _build_metadata_context(snapshot, selected_tables)

    user_content = (
        f"Business process: {sanitize_for_prompt(business_process)}\n"
        f"Grain: {sanitize_for_prompt(grain_description)}\n"
        f"Dimensions: {json.dumps(selected_dimensions)}\n\n"
        f"Database schema:\n{context}"
    )
    if instructions:
        user_content += f"\n\nAdditional instructions: {sanitize_for_prompt(instructions)}"

    messages = [
        {
            "role": "system",
            "content": (
                "You are a Kimball dimensional modeling expert. Given a business process, "
                "grain, dimensions, and schema, suggest measures for the fact table. "
                "Identify numeric columns suitable for aggregation. "
                'Return JSON with: {"measures": [{"name": str, '
                '"source_column": str, "source_table": str, '
                '"aggregation": str (SUM|AVG|COUNT|MIN|MAX|COUNT_DISTINCT), '
                '"data_type": str, "description": str, "confidence": float}]}'
            ),
        },
        {"role": "user", "content": user_content},
    ]

    result = await chat_completion(messages)
    return result if isinstance(result, dict) else result.model_dump()


def build_dimensional_model(
    business_process: str,
    grain_description: str,
    selected_dimensions: list[str | dict[str, Any]],
    selected_measures: list[dict[str, Any] | Measure],
) -> DimensionalModel:
    """Assemble and validate the dimensional model from plain args.

    Works as the bridge between both wizard SessionState and brief editor.
    """
    dimensions = []
    for dim_data in selected_dimensions:
        if isinstance(dim_data, str):
            # Simple string reference — create minimal dimension
            dimensions.append(
                Dimension(
                    name=f"dim_{dim_data}" if not dim_data.startswith("dim_") else dim_data,
                    source_table=dim_data.replace("dim_", ""),
                )
            )
        elif isinstance(dim_data, dict):
            # Filter to only Dimension model fields (AI may include extra keys like confidence)
            valid_fields = Dimension.model_fields.keys()
            filtered = {k: v for k, v in dim_data.items() if k in valid_fields}
            dimensions.append(Dimension(**filtered))

    measures = []
    valid_measure_fields = Measure.model_fields.keys()
    for m in selected_measures:
        if isinstance(m, dict):
            filtered = {k: v for k, v in m.items() if k in valid_measure_fields}
            measures.append(Measure(**filtered))
        else:
            measures.append(m)

    # Build fact table
    fact = FactTable(
        name=f"fact_{business_process.lower().replace(' ', '_')}",
        grain_description=grain_description,
        grain_columns=["id"],  # Will be refined from grain selection
        measures=measures,
        dimension_keys=[f"{d.name}_key" for d in dimensions if not d.is_degenerate],
        source_tables=[d.source_table for d in dimensions],
    )

    # Build and validate the complete model
    return DimensionalModel(
        business_process=business_process,
        fact_table=fact,
        dimensions=dimensions,
    )
