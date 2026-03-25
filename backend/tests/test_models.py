"""Tests for Pydantic data models and Kimball validators."""

import pytest
from pydantic import ValidationError

from odgg.models.dimensional import Dimension, DimensionalModel, FactTable, Measure
from odgg.models.metadata import ColumnInfo, MetadataSnapshot, RelationshipInfo, TableInfo
from odgg.models.session import SessionState, StepStatus


class TestDimensionalModel:
    """Tests for DimensionalModel Kimball constraint validation."""

    def _make_valid_model(self, **overrides):
        """Helper to create a valid dimensional model."""
        defaults = dict(
            business_process="Order Processing",
            fact_table=FactTable(
                name="fact_orders",
                grain_description="One row per order line item",
                grain_columns=["order_item_id"],
                measures=[Measure(
                    name="quantity",
                    source_column="quantity",
                    source_table="order_items",
                )],
                dimension_keys=["dim_customer_key"],
                source_tables=["order_items"],
            ),
            dimensions=[Dimension(
                name="dim_customer",
                source_table="customers",
                columns=["name", "email"],
                natural_key="id",
            )],
        )
        defaults.update(overrides)
        return DimensionalModel(**defaults)

    def test_valid_model(self):
        model = self._make_valid_model()
        assert model.business_process == "Order Processing"
        assert len(model.dimensions) == 1

    def test_fact_requires_measures(self):
        with pytest.raises(ValidationError, match="measures"):
            self._make_valid_model(
                fact_table=FactTable(
                    name="fact_orders",
                    grain_description="One row per order",
                    grain_columns=["order_id"],
                    measures=[],  # Empty - should fail
                )
            )

    def test_requires_non_degenerate_dimension(self):
        with pytest.raises(ValidationError, match="non-degenerate"):
            self._make_valid_model(
                dimensions=[Dimension(
                    name="dim_order_number",
                    source_table="orders",
                    is_degenerate=True,
                )]
            )

    def test_grain_must_be_described(self):
        with pytest.raises(ValidationError, match="grain"):
            self._make_valid_model(
                fact_table=FactTable(
                    name="fact_orders",
                    grain_description="",  # Empty - should fail
                    grain_columns=["order_id"],
                    measures=[Measure(
                        name="qty", source_column="qty", source_table="orders"
                    )],
                )
            )

    def test_fact_naming_convention(self):
        with pytest.raises(ValidationError, match="fact_"):
            self._make_valid_model(
                fact_table=FactTable(
                    name="orders",  # Missing fact_ prefix
                    grain_description="One row per order",
                    grain_columns=["id"],
                    measures=[Measure(
                        name="qty", source_column="qty", source_table="orders"
                    )],
                )
            )

    def test_dimension_naming_convention(self):
        with pytest.raises(ValidationError, match="dim_"):
            self._make_valid_model(
                dimensions=[Dimension(
                    name="customer",  # Missing dim_ prefix
                    source_table="customers",
                )]
            )


class TestSessionState:
    """Tests for session state machine."""

    def test_initial_state(self):
        session = SessionState(session_id="test-1")
        assert session.current_step() == 1
        assert session.steps[0].status == StepStatus.ACTIVE
        assert session.steps[1].status == StepStatus.LOCKED

    def test_advance_step(self):
        session = SessionState(session_id="test-1")
        session.advance_step(1)
        assert session.steps[0].status == StepStatus.COMPLETED
        assert session.steps[1].status == StepStatus.ACTIVE
        assert session.version == 2

    def test_rollback_to_step(self):
        session = SessionState(session_id="test-1")
        session.advance_step(1)
        session.advance_step(2)
        session.advance_step(3)
        # Now at step 4. Roll back to step 2.
        session.rollback_to_step(2)
        assert session.steps[1].status == StepStatus.ACTIVE  # Step 2
        assert session.steps[2].status == StepStatus.LOCKED  # Step 3
        assert session.steps[3].status == StepStatus.LOCKED  # Step 4

    def test_record_decision(self):
        session = SessionState(session_id="test-1")
        session.record_decision(1, "accept", {"db": "test"})
        assert len(session.step_decisions) == 1
        assert session.step_decisions[0]["action"] == "accept"


class TestMetadataSnapshot:
    """Tests for metadata models."""

    def test_column_info(self):
        col = ColumnInfo(name="id", data_type="integer", is_primary_key=True)
        assert col.is_primary_key

    def test_relationship_info(self):
        rel = RelationshipInfo(
            source_table="orders",
            source_column="customer_id",
            target_table="customers",
            target_column="id",
            is_inferred=True,
            confidence=0.8,
        )
        assert rel.is_inferred
        assert rel.confidence == 0.8

    def test_snapshot(self):
        snapshot = MetadataSnapshot(
            tables=[TableInfo(name="orders", columns=[
                ColumnInfo(name="id", data_type="integer"),
            ])],
            database_name="test_db",
        )
        assert len(snapshot.tables) == 1
