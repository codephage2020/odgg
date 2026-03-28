"""Bridge between ModelingBrief sections and the dimensional modeling engine.

Extracts structured data from brief sections and feeds it into
build_dimensional_model() and codegen — the same functions used by
the wizard. This is the "Protocol-based ModelSource" described in the
design doc.
"""

from __future__ import annotations

import re
from typing import Any, Protocol

from odgg.models.brief import BriefRow, SectionType
from odgg.models.dimensional import DimensionalModel
from odgg.services.modeling_engine import build_dimensional_model


class ModelSource(Protocol):
    """Protocol for anything that can provide Kimball modeling args."""

    def get_business_process(self) -> str: ...
    def get_grain_description(self) -> str: ...
    def get_dimensions(self) -> list[str | dict[str, Any]]: ...
    def get_measures(self) -> list[dict[str, Any]]: ...


class BriefModelSource:
    """Extract modeling args from a BriefRow's sections."""

    def __init__(self, brief: BriefRow) -> None:
        self._sections = {s.section_type: s for s in brief.sections}

    def get_business_process(self) -> str:
        sec = self._sections.get(SectionType.BUSINESS_PROCESS)
        if not sec:
            return ""
        # Extract name from markdown bold: **Name**
        content = sec.content
        if "**" in content:
            parts = content.split("**")
            if len(parts) >= 2:
                return parts[1]
        return content.split("\n")[0].strip()

    def get_grain_description(self) -> str:
        sec = self._sections.get(SectionType.GRAIN)
        if not sec:
            return ""
        return sec.content.split("\n")[0].strip()

    def get_dimensions(self) -> list[str | dict[str, Any]]:
        dims: list[str | dict[str, Any]] = []
        for sec in sorted(
            (s for s in self._sections.values()
             if s.section_type == SectionType.DIMENSION),
            key=lambda s: s.position,
        ):
            if sec.name and sec.source_table:
                columns = sec.source_columns or []
                natural_key = columns[0] if columns else "id"
                dims.append(
                    {
                        "name": sec.name,
                        "source_table": sec.source_table,
                        "columns": columns,
                        "natural_key": natural_key,
                        "description": sec.content,
                        "is_degenerate": (
                            sec.dimension_type == "degenerate"
                        ),
                    }
                )
            elif sec.name:
                dims.append(sec.name)
            else:
                # Fallback: parse markdown list items
                # e.g. "- **dim_date** (lineitem): description"
                dims.extend(_parse_dims_from_markdown(sec.content))
        return dims

    def get_measures(self) -> list[dict[str, Any]]:
        measures: list[dict[str, Any]] = []
        for sec in sorted(
            (s for s in self._sections.values()
             if s.section_type == SectionType.MEASURE),
            key=lambda s: s.position,
        ):
            if sec.name:
                measures.append(
                    {
                        "name": sec.name,
                        "source_column": sec.source_column or sec.name,
                        "source_table": sec.source_table or "",
                        "aggregation": (
                            sec.aggregation_type or "SUM"
                        ).upper(),
                        "data_type": sec.data_type or "NUMERIC",
                        "description": sec.content,
                    }
                )
            else:
                # Fallback: parse markdown list items
                # e.g. "- **Quantity** (SUM of l_quantity): desc"
                measures.extend(
                    _parse_measures_from_markdown(sec.content)
                )
        return measures


def _parse_dims_from_markdown(
    content: str,
) -> list[str | dict[str, Any]]:
    """Parse dimension names from markdown list.

    Handles patterns like:
      - **dim_date** (lineitem): Date dimension...
      - **dim_customer** (customer): Customer dimension...
    """
    dims: list[str | dict[str, Any]] = []
    # Match "- **name** (source_table): description"
    pattern = re.compile(
        r"-\s*\*\*(\w+)\*\*\s*(?:\((\w+)\))?\s*:?\s*(.*)"
    )
    for line in content.split("\n"):
        m = pattern.match(line.strip())
        if m:
            name = m.group(1)
            source_table = m.group(2) or ""
            desc = m.group(3) or ""
            if source_table:
                dims.append(
                    {
                        "name": name,
                        "source_table": source_table,
                        "columns": [],
                        "natural_key": "id",
                        "description": desc.strip(),
                        "is_degenerate": False,
                    }
                )
            else:
                dims.append(name)
    return dims


def _parse_measures_from_markdown(
    content: str,
) -> list[dict[str, Any]]:
    """Parse measures from markdown list.

    Handles patterns like:
      - **Quantity** (SUM of l_quantity): Total quantity...
      - **Extended Price** (SUM of l_extendedprice): desc
    """
    measures: list[dict[str, Any]] = []
    # Match "- **Name** (AGG of column): description"
    pattern = re.compile(
        r"-\s*\*\*([^*]+)\*\*\s*"
        r"(?:\((\w+)\s+of\s+(\w+)\))?\s*:?\s*(.*)"
    )
    for line in content.split("\n"):
        m = pattern.match(line.strip())
        if m:
            name = m.group(1).strip()
            agg = (m.group(2) or "SUM").upper()
            col = m.group(3) or name.lower().replace(" ", "_")
            desc = m.group(4) or ""
            measures.append(
                {
                    "name": name,
                    "source_column": col,
                    "source_table": "",
                    "aggregation": agg,
                    "data_type": "NUMERIC",
                    "description": desc.strip(),
                }
            )
    return measures


class SessionModelSource:
    """Extract modeling args from a wizard SessionState."""

    def __init__(self, session: Any) -> None:
        self._session = session

    def get_business_process(self) -> str:
        return self._session.business_process

    def get_grain_description(self) -> str:
        return self._session.grain_description

    def get_dimensions(self) -> list[str | dict[str, Any]]:
        return self._session.selected_dimensions

    def get_measures(self) -> list[dict[str, Any]]:
        return self._session.selected_measures


def build_model_from_source(source: ModelSource) -> DimensionalModel:
    """Build a DimensionalModel from any ModelSource.

    Works with both BriefModelSource and SessionModelSource.
    """
    return build_dimensional_model(
        business_process=source.get_business_process(),
        grain_description=source.get_grain_description(),
        selected_dimensions=source.get_dimensions(),
        selected_measures=source.get_measures(),
    )
