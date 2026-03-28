"""Bridge between ModelingBrief sections and the dimensional modeling engine.

Extracts structured data from brief sections and feeds it into
build_dimensional_model() and codegen — the same functions used by
the wizard. This is the "Protocol-based ModelSource" described in the
design doc.
"""

from __future__ import annotations

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
            (s for s in self._sections.values() if s.section_type == SectionType.DIMENSION),
            key=lambda s: s.position,
        ):
            if sec.name and sec.source_table:
                dims.append(
                    {
                        "name": sec.name,
                        "source_table": sec.source_table,
                        "columns": sec.source_columns or [],
                        "description": sec.content,
                        "is_degenerate": sec.dimension_type == "degenerate",
                    }
                )
            elif sec.name:
                dims.append(sec.name)
        return dims

    def get_measures(self) -> list[dict[str, Any]]:
        measures: list[dict[str, Any]] = []
        for sec in sorted(
            (s for s in self._sections.values() if s.section_type == SectionType.MEASURE),
            key=lambda s: s.position,
        ):
            if sec.name:
                measures.append(
                    {
                        "name": sec.name,
                        "source_column": sec.source_column or sec.name,
                        "source_table": sec.source_table or "",
                        "aggregation": (sec.aggregation_type or "SUM").upper(),
                        "data_type": sec.data_type or "NUMERIC",
                        "description": sec.content,
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
