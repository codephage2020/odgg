"""Tests for the brief-to-model bridge."""

from __future__ import annotations

from unittest.mock import MagicMock

from odgg.models.dimensional import DimensionalModel
from odgg.services.brief_bridge import (
    BriefModelSource,
    SessionModelSource,
    build_model_from_source,
)


def _make_section(section_type, position=0, **kwargs):
    """Create a mock SectionRow."""
    sec = MagicMock()
    sec.section_type = section_type
    sec.position = position
    sec.content = kwargs.get("content", "")
    sec.name = kwargs.get("name")
    sec.source_table = kwargs.get("source_table")
    sec.source_columns = kwargs.get("source_columns")
    sec.source_column = kwargs.get("source_column")
    sec.data_type = kwargs.get("data_type")
    sec.dimension_type = kwargs.get("dimension_type")
    sec.aggregation_type = kwargs.get("aggregation_type")
    return sec


def _make_brief(sections):
    """Create a mock BriefRow with sections."""
    brief = MagicMock()
    brief.sections = sections
    return brief


class TestBriefModelSource:
    def test_get_business_process_from_markdown(self):
        brief = _make_brief(
            [
                _make_section(
                    "business_process",
                    content="**Order Processing**\n\nTrack orders",
                )
            ]
        )
        source = BriefModelSource(brief)
        assert source.get_business_process() == "Order Processing"

    def test_get_business_process_plain_text(self):
        brief = _make_brief([_make_section("business_process", content="Inventory management")])
        source = BriefModelSource(brief)
        assert source.get_business_process() == "Inventory management"

    def test_get_business_process_empty(self):
        brief = _make_brief([])
        source = BriefModelSource(brief)
        assert source.get_business_process() == ""

    def test_get_grain_description(self):
        brief = _make_brief(
            [
                _make_section(
                    "grain",
                    content="One row per order line item\n\nGrain columns: ...",
                )
            ]
        )
        source = BriefModelSource(brief)
        assert source.get_grain_description() == "One row per order line item"

    def test_get_dimensions_structured(self):
        brief = _make_brief(
            [
                _make_section(
                    "dimension",
                    position=0,
                    name="dim_customer",
                    source_table="customers",
                    source_columns=["id", "name"],
                    content="Customer dimension",
                    dimension_type="regular",
                ),
            ]
        )
        source = BriefModelSource(brief)
        dims = source.get_dimensions()
        assert len(dims) == 1
        assert dims[0]["name"] == "dim_customer"
        assert dims[0]["source_table"] == "customers"
        assert dims[0]["columns"] == ["id", "name"]

    def test_get_dimensions_degenerate(self):
        brief = _make_brief(
            [
                _make_section(
                    "dimension",
                    position=0,
                    name="dim_order_number",
                    source_table="orders",
                    dimension_type="degenerate",
                ),
            ]
        )
        source = BriefModelSource(brief)
        dims = source.get_dimensions()
        assert dims[0]["is_degenerate"] is True

    def test_get_measures(self):
        brief = _make_brief(
            [
                _make_section(
                    "measure",
                    position=0,
                    name="total_revenue",
                    source_column="total",
                    source_table="orders",
                    aggregation_type="sum",
                    data_type="decimal",
                    content="Total order revenue",
                ),
            ]
        )
        source = BriefModelSource(brief)
        measures = source.get_measures()
        assert len(measures) == 1
        assert measures[0]["name"] == "total_revenue"
        assert measures[0]["aggregation"] == "SUM"


class TestSessionModelSource:
    def test_extracts_session_fields(self):
        session = MagicMock()
        session.business_process = "sales"
        session.grain_description = "One row per sale"
        session.selected_dimensions = ["customer", "product"]
        session.selected_measures = [{"name": "amount"}]

        source = SessionModelSource(session)
        assert source.get_business_process() == "sales"
        assert source.get_grain_description() == "One row per sale"
        assert source.get_dimensions() == ["customer", "product"]
        assert source.get_measures() == [{"name": "amount"}]


class TestBuildModelFromSource:
    def test_builds_valid_model_from_brief(self):
        brief = _make_brief(
            [
                _make_section(
                    "business_process",
                    content="**Order Processing**\n\nDescription",
                ),
                _make_section(
                    "grain",
                    content="One row per order",
                ),
                _make_section(
                    "dimension",
                    position=2,
                    name="dim_customer",
                    source_table="customers",
                    source_columns=["id", "name"],
                    dimension_type="regular",
                ),
                _make_section(
                    "measure",
                    position=3,
                    name="total_amount",
                    source_column="total",
                    source_table="orders",
                    aggregation_type="sum",
                    data_type="NUMERIC",
                ),
            ]
        )
        source = BriefModelSource(brief)
        model = build_model_from_source(source)
        assert isinstance(model, DimensionalModel)
        assert model.business_process == "Order Processing"
        assert model.fact_table.name == "fact_order_processing"
        assert len(model.dimensions) == 1
        assert len(model.fact_table.measures) == 1
