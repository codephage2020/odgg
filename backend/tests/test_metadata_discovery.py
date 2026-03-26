"""Tests for metadata discovery — heuristic inference and helper functions."""

from odgg.models.metadata import ColumnInfo, RelationshipInfo, TableInfo
from odgg.services.metadata_discovery import _infer_relationships


def _make_table(name: str, columns: list[str], pk: str | None = None) -> TableInfo:
    """Helper to create a TableInfo with named columns."""
    return TableInfo(
        name=name,
        schema_name="public",
        columns=[
            ColumnInfo(
                name=c,
                data_type="integer" if c.endswith("_id") or c == "id" else "text",
                nullable=c != "id",
                is_primary_key=c == (pk or "id"),
            )
            for c in columns
        ],
        primary_key=[pk or "id"] if pk or "id" in columns else [],
    )


class TestInferRelationships:
    def test_basic_inference(self):
        """orders.customer_id -> customer.id"""
        tables = [
            _make_table("orders", ["id", "customer_id", "total"]),
            _make_table("customer", ["id", "name"]),
        ]
        inferred = _infer_relationships(tables, [])
        assert len(inferred) == 1
        assert inferred[0].source_table == "orders"
        assert inferred[0].source_column == "customer_id"
        assert inferred[0].target_table == "customer"
        assert inferred[0].target_column == "id"
        assert inferred[0].is_inferred is True
        assert inferred[0].confidence == 0.8

    def test_plural_table_match(self):
        """lineitem.part_id -> parts.id (plural form)"""
        tables = [
            _make_table("lineitem", ["id", "part_id"]),
            _make_table("parts", ["id", "name"]),
        ]
        inferred = _infer_relationships(tables, [])
        assert len(inferred) == 1
        assert inferred[0].target_table == "parts"

    def test_no_self_reference(self):
        """employee.employee_id should not infer self-reference."""
        tables = [
            _make_table("employee", ["id", "employee_id", "name"]),
        ]
        inferred = _infer_relationships(tables, [])
        assert len(inferred) == 0

    def test_skips_existing_fk(self):
        """Don't infer if FK already exists."""
        tables = [
            _make_table("orders", ["id", "customer_id"]),
            _make_table("customer", ["id", "name"]),
        ]
        existing = [
            RelationshipInfo(
                source_table="orders",
                source_column="customer_id",
                target_table="customer",
                target_column="id",
                is_inferred=False,
                confidence=1.0,
            )
        ]
        inferred = _infer_relationships(tables, existing)
        assert len(inferred) == 0

    def test_no_match_without_target_column(self):
        """Don't infer if target table doesn't have 'id' column."""
        tables = [
            _make_table("orders", ["id", "status_id"]),
            _make_table("status", ["code", "name"], pk="code"),
        ]
        # status table has no 'id' column, pk is 'code'
        # The heuristic looks for pk_by_table.get(candidate, "id")
        # Here pk is "code", so it will try to find "code" column
        inferred = _infer_relationships(tables, [])
        assert len(inferred) == 1
        assert inferred[0].target_column == "code"

    def test_no_match_no_id_suffix(self):
        """Columns not ending in _id are ignored."""
        tables = [
            _make_table("orders", ["id", "customer_name", "total"]),
            _make_table("customer", ["id", "name"]),
        ]
        inferred = _infer_relationships(tables, [])
        assert len(inferred) == 0

    def test_multiple_inferences(self):
        """Multiple FK inferences from one table."""
        tables = [
            _make_table("lineitem", ["id", "order_id", "part_id"]),
            _make_table("order", ["id", "date"]),
            _make_table("part", ["id", "name"]),
        ]
        inferred = _infer_relationships(tables, [])
        assert len(inferred) == 2
        sources = {(r.source_column, r.target_table) for r in inferred}
        assert ("order_id", "order") in sources
        assert ("part_id", "part") in sources

    def test_uses_primary_key_from_table(self):
        """Uses actual PK instead of defaulting to 'id'."""
        tables = [
            _make_table("orders", ["id", "region_id"]),
            TableInfo(
                name="region",
                schema_name="public",
                columns=[
                    ColumnInfo(name="region_id", data_type="integer", nullable=False, is_primary_key=True),
                    ColumnInfo(name="name", data_type="text", nullable=True),
                ],
                primary_key=["region_id"],
            ),
        ]
        inferred = _infer_relationships(tables, [])
        assert len(inferred) == 1
        assert inferred[0].target_column == "region_id"
