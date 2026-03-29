"""Eval suite — AI draft quality for brief sections against TPC-H baseline.

Structural tests (always run): verify response shape and field presence
using mock LLM responses that represent known-good Kimball modeling.

Live LLM tests (run with --run-llm): call the real LLM and score output
against TPC-H ground truth. These cost real API calls.

Usage:
    pytest tests/test_eval_brief_quality.py           # structural only
    pytest tests/test_eval_brief_quality.py --run-llm  # include live LLM
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from odgg.models.metadata import ColumnInfo, MetadataSnapshot, RelationshipInfo, TableInfo
from odgg.services.modeling_engine import (
    suggest_business_process,
    suggest_dimensions,
    suggest_grain,
    suggest_measures,
)

# ---------------------------------------------------------------------------
# TPC-H MetadataSnapshot fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def tpch_snapshot() -> MetadataSnapshot:
    """Full TPC-H schema as a MetadataSnapshot — 8 tables, all FKs."""
    return MetadataSnapshot(
        database_name="tpch",
        database_type="postgresql",
        discovered_at="2026-01-01T00:00:00Z",
        tables=[
            TableInfo(
                name="region",
                schema_name="public",
                columns=[
                    ColumnInfo(
                        name="r_regionkey",
                        data_type="integer",
                        nullable=False,
                        is_primary_key=True,
                    ),
                    ColumnInfo(name="r_name", data_type="varchar(25)", nullable=False),
                    ColumnInfo(name="r_comment", data_type="varchar(152)", nullable=True),
                ],
                primary_key=["r_regionkey"],
                row_count=5,
            ),
            TableInfo(
                name="nation",
                schema_name="public",
                columns=[
                    ColumnInfo(
                        name="n_nationkey",
                        data_type="integer",
                        nullable=False,
                        is_primary_key=True,
                    ),
                    ColumnInfo(name="n_name", data_type="varchar(25)", nullable=False),
                    ColumnInfo(name="n_regionkey", data_type="integer", nullable=False),
                    ColumnInfo(name="n_comment", data_type="varchar(152)", nullable=True),
                ],
                primary_key=["n_nationkey"],
                row_count=25,
            ),
            TableInfo(
                name="supplier",
                schema_name="public",
                columns=[
                    ColumnInfo(
                        name="s_suppkey",
                        data_type="integer",
                        nullable=False,
                        is_primary_key=True,
                    ),
                    ColumnInfo(name="s_name", data_type="varchar(25)", nullable=False),
                    ColumnInfo(name="s_address", data_type="varchar(40)", nullable=False),
                    ColumnInfo(name="s_nationkey", data_type="integer", nullable=False),
                    ColumnInfo(name="s_phone", data_type="varchar(15)", nullable=False),
                    ColumnInfo(name="s_acctbal", data_type="numeric(15,2)", nullable=False),
                    ColumnInfo(name="s_comment", data_type="varchar(101)", nullable=True),
                ],
                primary_key=["s_suppkey"],
                row_count=10000,
            ),
            TableInfo(
                name="part",
                schema_name="public",
                columns=[
                    ColumnInfo(
                        name="p_partkey",
                        data_type="integer",
                        nullable=False,
                        is_primary_key=True,
                    ),
                    ColumnInfo(name="p_name", data_type="varchar(55)", nullable=False),
                    ColumnInfo(name="p_mfgr", data_type="varchar(25)", nullable=False),
                    ColumnInfo(name="p_brand", data_type="varchar(10)", nullable=False),
                    ColumnInfo(name="p_type", data_type="varchar(25)", nullable=False),
                    ColumnInfo(name="p_size", data_type="integer", nullable=False),
                    ColumnInfo(name="p_container", data_type="varchar(10)", nullable=False),
                    ColumnInfo(name="p_retailprice", data_type="numeric(15,2)", nullable=False),
                    ColumnInfo(name="p_comment", data_type="varchar(23)", nullable=True),
                ],
                primary_key=["p_partkey"],
                row_count=200000,
            ),
            TableInfo(
                name="partsupp",
                schema_name="public",
                columns=[
                    ColumnInfo(
                        name="ps_partkey",
                        data_type="integer",
                        nullable=False,
                        is_primary_key=True,
                    ),
                    ColumnInfo(
                        name="ps_suppkey",
                        data_type="integer",
                        nullable=False,
                        is_primary_key=True,
                    ),
                    ColumnInfo(name="ps_availqty", data_type="integer", nullable=False),
                    ColumnInfo(name="ps_supplycost", data_type="numeric(15,2)", nullable=False),
                    ColumnInfo(name="ps_comment", data_type="varchar(199)", nullable=True),
                ],
                primary_key=["ps_partkey", "ps_suppkey"],
                row_count=800000,
            ),
            TableInfo(
                name="customer",
                schema_name="public",
                columns=[
                    ColumnInfo(
                        name="c_custkey",
                        data_type="integer",
                        nullable=False,
                        is_primary_key=True,
                    ),
                    ColumnInfo(name="c_name", data_type="varchar(25)", nullable=False),
                    ColumnInfo(name="c_address", data_type="varchar(40)", nullable=False),
                    ColumnInfo(name="c_nationkey", data_type="integer", nullable=False),
                    ColumnInfo(name="c_phone", data_type="varchar(15)", nullable=False),
                    ColumnInfo(name="c_acctbal", data_type="numeric(15,2)", nullable=False),
                    ColumnInfo(name="c_mktsegment", data_type="varchar(10)", nullable=False),
                    ColumnInfo(name="c_comment", data_type="varchar(117)", nullable=True),
                ],
                primary_key=["c_custkey"],
                row_count=150000,
            ),
            TableInfo(
                name="orders",
                schema_name="public",
                columns=[
                    ColumnInfo(
                        name="o_orderkey",
                        data_type="integer",
                        nullable=False,
                        is_primary_key=True,
                    ),
                    ColumnInfo(name="o_custkey", data_type="integer", nullable=False),
                    ColumnInfo(name="o_orderstatus", data_type="char(1)", nullable=False),
                    ColumnInfo(name="o_totalprice", data_type="numeric(15,2)", nullable=False),
                    ColumnInfo(name="o_orderdate", data_type="date", nullable=False),
                    ColumnInfo(name="o_orderpriority", data_type="varchar(15)", nullable=False),
                    ColumnInfo(name="o_clerk", data_type="varchar(15)", nullable=False),
                    ColumnInfo(name="o_shippriority", data_type="integer", nullable=False),
                    ColumnInfo(name="o_comment", data_type="varchar(79)", nullable=True),
                ],
                primary_key=["o_orderkey"],
                row_count=1500000,
            ),
            TableInfo(
                name="lineitem",
                schema_name="public",
                columns=[
                    ColumnInfo(
                        name="l_orderkey",
                        data_type="integer",
                        nullable=False,
                        is_primary_key=True,
                    ),
                    ColumnInfo(name="l_partkey", data_type="integer", nullable=False),
                    ColumnInfo(name="l_suppkey", data_type="integer", nullable=False),
                    ColumnInfo(
                        name="l_linenumber",
                        data_type="integer",
                        nullable=False,
                        is_primary_key=True,
                    ),
                    ColumnInfo(name="l_quantity", data_type="numeric(15,2)", nullable=False),
                    ColumnInfo(name="l_extendedprice", data_type="numeric(15,2)", nullable=False),
                    ColumnInfo(name="l_discount", data_type="numeric(15,2)", nullable=False),
                    ColumnInfo(name="l_tax", data_type="numeric(15,2)", nullable=False),
                    ColumnInfo(name="l_returnflag", data_type="char(1)", nullable=False),
                    ColumnInfo(name="l_linestatus", data_type="char(1)", nullable=False),
                    ColumnInfo(name="l_shipdate", data_type="date", nullable=False),
                    ColumnInfo(name="l_commitdate", data_type="date", nullable=False),
                    ColumnInfo(name="l_receiptdate", data_type="date", nullable=False),
                    ColumnInfo(name="l_shipinstruct", data_type="varchar(25)", nullable=False),
                    ColumnInfo(name="l_shipmode", data_type="varchar(10)", nullable=False),
                    ColumnInfo(name="l_comment", data_type="varchar(44)", nullable=True),
                ],
                primary_key=["l_orderkey", "l_linenumber"],
                row_count=6001215,
            ),
        ],
        relationships=[
            RelationshipInfo(
                source_table="nation",
                source_column="n_regionkey",
                target_table="region",
                target_column="r_regionkey",
            ),
            RelationshipInfo(
                source_table="supplier",
                source_column="s_nationkey",
                target_table="nation",
                target_column="n_nationkey",
            ),
            RelationshipInfo(
                source_table="customer",
                source_column="c_nationkey",
                target_table="nation",
                target_column="n_nationkey",
            ),
            RelationshipInfo(
                source_table="partsupp",
                source_column="ps_partkey",
                target_table="part",
                target_column="p_partkey",
            ),
            RelationshipInfo(
                source_table="partsupp",
                source_column="ps_suppkey",
                target_table="supplier",
                target_column="s_suppkey",
            ),
            RelationshipInfo(
                source_table="orders",
                source_column="o_custkey",
                target_table="customer",
                target_column="c_custkey",
            ),
            RelationshipInfo(
                source_table="lineitem",
                source_column="l_orderkey",
                target_table="orders",
                target_column="o_orderkey",
            ),
            RelationshipInfo(
                source_table="lineitem",
                source_column="l_partkey",
                target_table="part",
                target_column="p_partkey",
            ),
            RelationshipInfo(
                source_table="lineitem",
                source_column="l_suppkey",
                target_table="supplier",
                target_column="s_suppkey",
            ),
        ],
    )


# ---------------------------------------------------------------------------
# TPC-H ground truth — what a correct Kimball model looks like
# ---------------------------------------------------------------------------

# Order processing is the primary TPC-H business process
EXPECTED_BP_KEYWORDS = {"order", "lineitem", "sales", "purchase"}

# The canonical grain for TPC-H order processing
EXPECTED_GRAIN_TABLES = {"lineitem", "orders"}

# Expected dimension tables (at minimum)
EXPECTED_DIMENSIONS = {
    "customer",  # dim_customer
    "part",  # dim_part
    "supplier",  # dim_supplier
}
# Date dimension should always be suggested
EXPECTED_DATE_DIM = True

# Expected measure source columns from lineitem
EXPECTED_MEASURE_COLUMNS = {
    "l_quantity",
    "l_extendedprice",
    "l_discount",
    "l_tax",
}

VALID_AGGREGATIONS = {"SUM", "AVG", "COUNT", "MIN", "MAX", "COUNT_DISTINCT"}


# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------


def score_business_process(result: dict) -> dict:
    """Score BP suggestion against TPC-H ground truth. Returns scores dict."""
    processes = result.get("processes", [])
    scores = {
        "has_processes": len(processes) > 0,
        "has_order_process": False,
        "involves_lineitem": False,
        "involves_orders": False,
        "has_confidence": False,
    }
    for p in processes:
        name_lower = p.get("name", "").lower()
        tables_lower = [t.lower() for t in p.get("involved_tables", [])]
        if any(kw in name_lower for kw in EXPECTED_BP_KEYWORDS):
            scores["has_order_process"] = True
        if "lineitem" in tables_lower:
            scores["involves_lineitem"] = True
        if "orders" in tables_lower:
            scores["involves_orders"] = True
        if isinstance(p.get("confidence"), (int, float)):
            scores["has_confidence"] = True
    return scores


def score_grain(result: dict) -> dict:
    """Score grain suggestion against TPC-H ground truth."""
    options = result.get("options", [])
    scores = {
        "has_options": len(options) > 0,
        "has_recommended": False,
        "recommends_lineitem_grain": False,
        "has_reasoning": False,
    }
    for o in options:
        if o.get("recommended"):
            scores["has_recommended"] = True
            source = (o.get("source_table") or "").lower()
            desc = (o.get("description") or "").lower()
            if "lineitem" in source or "lineitem" in desc or "line item" in desc:
                scores["recommends_lineitem_grain"] = True
        if o.get("reasoning"):
            scores["has_reasoning"] = True
    return scores


def score_dimensions(result: dict) -> dict:
    """Score dimension suggestions against TPC-H ground truth."""
    dims = result.get("dimensions", [])
    source_tables = {(d.get("source_table") or "").lower() for d in dims}
    dim_names = {(d.get("name") or "").lower() for d in dims}
    scores = {
        "has_dimensions": len(dims) >= 2,
        "has_customer_dim": "customer" in source_tables,
        "has_part_dim": "part" in source_tables,
        "has_supplier_dim": "supplier" in source_tables,
        "has_date_dim": any(
            d.get("is_date_dimension") or "date" in (d.get("name") or "").lower() for d in dims
        ),
        "uses_dim_prefix": all(n.startswith("dim_") for n in dim_names if n),
        "has_natural_keys": all(d.get("natural_key") for d in dims),
    }
    return scores


def score_measures(result: dict) -> dict:
    """Score measure suggestions against TPC-H ground truth."""
    measures = result.get("measures", [])
    source_cols = {(m.get("source_column") or "").lower() for m in measures}
    scores = {
        "has_measures": len(measures) >= 2,
        "has_quantity": "l_quantity" in source_cols,
        "has_extended_price": "l_extendedprice" in source_cols,
        "has_discount": "l_discount" in source_cols,
        "valid_aggregations": all(
            m.get("aggregation", "").upper() in VALID_AGGREGATIONS for m in measures
        ),
        "has_data_types": all(m.get("data_type") for m in measures),
        "sources_from_lineitem": any(
            (m.get("source_table") or "").lower() == "lineitem" for m in measures
        ),
    }
    return scores


def pass_rate(scores: dict) -> float:
    """Calculate pass rate from a scores dict."""
    if not scores:
        return 0.0
    return sum(1 for v in scores.values() if v) / len(scores)


# ---------------------------------------------------------------------------
# Known-good mock responses (structural baseline)
# ---------------------------------------------------------------------------

MOCK_BP_RESPONSE = {
    "processes": [
        {
            "name": "Order Processing",
            "description": "Track customer orders and line items through fulfillment",
            "involved_tables": ["orders", "lineitem", "customer"],
            "confidence": 0.95,
        },
        {
            "name": "Supply Chain / Procurement",
            "description": "Track parts sourced from suppliers",
            "involved_tables": ["partsupp", "supplier", "part"],
            "confidence": 0.7,
        },
    ]
}

MOCK_GRAIN_RESPONSE = {
    "options": [
        {
            "description": "One row per line item (order line detail)",
            "grain_columns": ["l_orderkey", "l_linenumber"],
            "source_table": "lineitem",
            "row_count": 6001215,
            "recommended": True,
            "reasoning": (
                "Lineitem is the most granular fact table"
                " with quantity, price, and discount per item."
            ),
        },
        {
            "description": "One row per order (order header level)",
            "grain_columns": ["o_orderkey"],
            "source_table": "orders",
            "row_count": 1500000,
            "recommended": False,
            "reasoning": "Loses line-level detail. Use only if analysis is at order level.",
        },
    ]
}

MOCK_DIMENSIONS_RESPONSE = {
    "dimensions": [
        {
            "name": "dim_customer",
            "source_table": "customer",
            "columns": ["c_custkey", "c_name", "c_mktsegment", "c_nationkey"],
            "natural_key": "c_custkey",
            "is_date_dimension": False,
            "is_degenerate": False,
            "description": "Customer dimension with market segment and geography",
            "confidence": 0.95,
        },
        {
            "name": "dim_part",
            "source_table": "part",
            "columns": ["p_partkey", "p_name", "p_brand", "p_type", "p_size"],
            "natural_key": "p_partkey",
            "is_date_dimension": False,
            "is_degenerate": False,
            "description": "Part/product dimension with brand and type attributes",
            "confidence": 0.95,
        },
        {
            "name": "dim_supplier",
            "source_table": "supplier",
            "columns": ["s_suppkey", "s_name", "s_nationkey"],
            "natural_key": "s_suppkey",
            "is_date_dimension": False,
            "is_degenerate": False,
            "description": "Supplier dimension with geography",
            "confidence": 0.9,
        },
        {
            "name": "dim_date",
            "source_table": "orders",
            "columns": ["o_orderdate"],
            "natural_key": "o_orderdate",
            "is_date_dimension": True,
            "is_degenerate": False,
            "description": "Date dimension derived from order dates",
            "confidence": 0.95,
        },
    ]
}

MOCK_MEASURES_RESPONSE = {
    "measures": [
        {
            "name": "total_quantity",
            "source_column": "l_quantity",
            "source_table": "lineitem",
            "aggregation": "SUM",
            "data_type": "NUMERIC",
            "description": "Total quantity ordered",
            "confidence": 0.95,
        },
        {
            "name": "total_extended_price",
            "source_column": "l_extendedprice",
            "source_table": "lineitem",
            "aggregation": "SUM",
            "data_type": "NUMERIC",
            "description": "Total revenue before discounts",
            "confidence": 0.95,
        },
        {
            "name": "total_discount",
            "source_column": "l_discount",
            "source_table": "lineitem",
            "aggregation": "AVG",
            "data_type": "NUMERIC",
            "description": "Average discount rate",
            "confidence": 0.85,
        },
        {
            "name": "total_tax",
            "source_column": "l_tax",
            "source_table": "lineitem",
            "aggregation": "SUM",
            "data_type": "NUMERIC",
            "description": "Total tax amount",
            "confidence": 0.8,
        },
    ]
}


# ---------------------------------------------------------------------------
# Structural tests (always run, use mock responses)
# ---------------------------------------------------------------------------


class TestBPStructural:
    """Verify BP suggestion structure and scoring against mock baseline."""

    @patch("odgg.services.modeling_engine.chat_completion")
    async def test_bp_response_shape(self, mock_chat, tpch_snapshot):
        mock_chat.return_value = MOCK_BP_RESPONSE
        result = await suggest_business_process(tpch_snapshot)
        assert "processes" in result
        assert len(result["processes"]) >= 1
        for p in result["processes"]:
            assert "name" in p
            assert "involved_tables" in p

    @patch("odgg.services.modeling_engine.chat_completion")
    async def test_bp_scoring_perfect(self, mock_chat, tpch_snapshot):
        mock_chat.return_value = MOCK_BP_RESPONSE
        result = await suggest_business_process(tpch_snapshot)
        scores = score_business_process(result)
        assert pass_rate(scores) == 1.0, f"BP scoring: {scores}"

    @patch("odgg.services.modeling_engine.chat_completion")
    async def test_bp_empty_processes_scores_zero(self, mock_chat, tpch_snapshot):
        mock_chat.return_value = {"processes": []}
        result = await suggest_business_process(tpch_snapshot)
        scores = score_business_process(result)
        assert scores["has_processes"] is False


class TestGrainStructural:
    @patch("odgg.services.modeling_engine.chat_completion")
    async def test_grain_response_shape(self, mock_chat, tpch_snapshot):
        mock_chat.return_value = MOCK_GRAIN_RESPONSE
        result = await suggest_grain("Order Processing", tpch_snapshot)
        assert "options" in result
        assert len(result["options"]) >= 1
        for o in result["options"]:
            assert "description" in o
            assert "recommended" in o

    @patch("odgg.services.modeling_engine.chat_completion")
    async def test_grain_scoring_perfect(self, mock_chat, tpch_snapshot):
        mock_chat.return_value = MOCK_GRAIN_RESPONSE
        result = await suggest_grain("Order Processing", tpch_snapshot)
        scores = score_grain(result)
        assert pass_rate(scores) == 1.0, f"Grain scoring: {scores}"


class TestDimensionsStructural:
    @patch("odgg.services.modeling_engine.chat_completion")
    async def test_dimensions_response_shape(self, mock_chat, tpch_snapshot):
        mock_chat.return_value = MOCK_DIMENSIONS_RESPONSE
        result = await suggest_dimensions(
            "Order Processing", "One row per line item", tpch_snapshot
        )
        assert "dimensions" in result
        assert len(result["dimensions"]) >= 2
        for d in result["dimensions"]:
            assert "name" in d
            assert "source_table" in d

    @patch("odgg.services.modeling_engine.chat_completion")
    async def test_dimensions_scoring_perfect(self, mock_chat, tpch_snapshot):
        mock_chat.return_value = MOCK_DIMENSIONS_RESPONSE
        result = await suggest_dimensions(
            "Order Processing", "One row per line item", tpch_snapshot
        )
        scores = score_dimensions(result)
        assert pass_rate(scores) == 1.0, f"Dimension scoring: {scores}"


class TestMeasuresStructural:
    @patch("odgg.services.modeling_engine.chat_completion")
    async def test_measures_response_shape(self, mock_chat, tpch_snapshot):
        mock_chat.return_value = MOCK_MEASURES_RESPONSE
        result = await suggest_measures(
            "Order Processing",
            "One row per line item",
            ["dim_customer", "dim_part", "dim_supplier"],
            tpch_snapshot,
        )
        assert "measures" in result
        assert len(result["measures"]) >= 2
        for m in result["measures"]:
            assert "name" in m
            assert "source_column" in m
            assert "aggregation" in m

    @patch("odgg.services.modeling_engine.chat_completion")
    async def test_measures_scoring_perfect(self, mock_chat, tpch_snapshot):
        mock_chat.return_value = MOCK_MEASURES_RESPONSE
        result = await suggest_measures(
            "Order Processing",
            "One row per line item",
            ["dim_customer", "dim_part", "dim_supplier"],
            tpch_snapshot,
        )
        scores = score_measures(result)
        assert pass_rate(scores) == 1.0, f"Measure scoring: {scores}"


# ---------------------------------------------------------------------------
# Scoring thresholds
# ---------------------------------------------------------------------------

# Minimum acceptable pass rates for live LLM tests (≥90% target from plan)
MIN_BP_PASS_RATE = 0.8
MIN_GRAIN_PASS_RATE = 0.75
MIN_DIMENSIONS_PASS_RATE = 0.7
MIN_MEASURES_PASS_RATE = 0.7


# ---------------------------------------------------------------------------
# Live LLM tests (only run with --run-llm)
# ---------------------------------------------------------------------------


@pytest.mark.llm
class TestBPLive:
    """Live LLM eval for business process suggestion."""

    async def test_bp_identifies_order_processing(self, tpch_snapshot):
        result = await suggest_business_process(tpch_snapshot)
        scores = score_business_process(result)
        rate = pass_rate(scores)
        print(f"\n  BP scores: {scores}")
        print(f"  BP pass rate: {rate:.0%}")
        assert rate >= MIN_BP_PASS_RATE, (
            f"BP pass rate {rate:.0%} below {MIN_BP_PASS_RATE:.0%}: {scores}"
        )


@pytest.mark.llm
class TestGrainLive:
    async def test_grain_recommends_lineitem(self, tpch_snapshot):
        result = await suggest_grain("Order Processing", tpch_snapshot)
        scores = score_grain(result)
        rate = pass_rate(scores)
        print(f"\n  Grain scores: {scores}")
        print(f"  Grain pass rate: {rate:.0%}")
        assert rate >= MIN_GRAIN_PASS_RATE, (
            f"Grain pass rate {rate:.0%} below {MIN_GRAIN_PASS_RATE:.0%}: {scores}"
        )


@pytest.mark.llm
class TestDimensionsLive:
    async def test_dimensions_finds_core_dims(self, tpch_snapshot):
        result = await suggest_dimensions(
            "Order Processing", "One row per line item in lineitem table", tpch_snapshot
        )
        scores = score_dimensions(result)
        rate = pass_rate(scores)
        print(f"\n  Dimension scores: {scores}")
        print(f"  Dimension pass rate: {rate:.0%}")
        assert rate >= MIN_DIMENSIONS_PASS_RATE, (
            f"Dimension pass rate {rate:.0%} below {MIN_DIMENSIONS_PASS_RATE:.0%}: {scores}"
        )


@pytest.mark.llm
class TestMeasuresLive:
    async def test_measures_finds_lineitem_numerics(self, tpch_snapshot):
        result = await suggest_measures(
            "Order Processing",
            "One row per line item in lineitem table",
            ["dim_customer", "dim_part", "dim_supplier", "dim_date"],
            tpch_snapshot,
        )
        scores = score_measures(result)
        rate = pass_rate(scores)
        print(f"\n  Measure scores: {scores}")
        print(f"  Measure pass rate: {rate:.0%}")
        assert rate >= MIN_MEASURES_PASS_RATE, (
            f"Measure pass rate {rate:.0%} below {MIN_MEASURES_PASS_RATE:.0%}: {scores}"
        )


# ---------------------------------------------------------------------------
# Full pipeline eval (live LLM, cascaded)
# ---------------------------------------------------------------------------


@pytest.mark.llm
class TestFullPipelineLive:
    """Run the full 4-step cascade and score the end-to-end result."""

    async def test_full_cascade_tpch(self, tpch_snapshot):
        # Step 3: Business Process
        bp_result = await suggest_business_process(tpch_snapshot)
        bp_scores = score_business_process(bp_result)
        processes = bp_result.get("processes", [])
        assert len(processes) > 0, "No business processes suggested"
        bp_name = processes[0]["name"]

        # Step 4: Grain
        grain_result = await suggest_grain(bp_name, tpch_snapshot)
        grain_scores = score_grain(grain_result)
        options = grain_result.get("options", [])
        recommended = next(
            (o for o in options if o.get("recommended")),
            options[0] if options else None,
        )
        assert recommended, "No grain option suggested"
        grain_desc = recommended["description"]

        # Step 5: Dimensions
        dim_result = await suggest_dimensions(bp_name, grain_desc, tpch_snapshot)
        dim_scores = score_dimensions(dim_result)
        dims = dim_result.get("dimensions", [])
        dim_names = [d.get("name", "") for d in dims]

        # Step 6: Measures
        meas_result = await suggest_measures(bp_name, grain_desc, dim_names, tpch_snapshot)
        meas_scores = score_measures(meas_result)

        # Aggregate scoring
        all_scores = {
            "bp": pass_rate(bp_scores),
            "grain": pass_rate(grain_scores),
            "dimensions": pass_rate(dim_scores),
            "measures": pass_rate(meas_scores),
        }
        overall = sum(all_scores.values()) / len(all_scores)

        print("\n  === Full Pipeline Eval ===")
        print(f"  Business Process: {bp_name}")
        print(f"  Grain: {grain_desc}")
        print(f"  Dimensions: {dim_names}")
        print(f"  Measures: {[m.get('name') for m in meas_result.get('measures', [])]}")
        print("  ---")
        print(
            f"  BP: {all_scores['bp']:.0%} | Grain: {all_scores['grain']:.0%} | "
            f"Dims: {all_scores['dimensions']:.0%} | Measures: {all_scores['measures']:.0%}"
        )
        print(f"  Overall: {overall:.0%}")

        assert overall >= 0.75, f"Overall pipeline score {overall:.0%} below 75%: {all_scores}"
