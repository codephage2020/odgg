"""Tests for code generation engine — DDL, ETL SQL, dbt models, data dictionary."""

import pytest

from odgg.models.dimensional import Dimension, DimensionalModel, FactTable, Measure
from odgg.services.codegen import (
    generate_data_dictionary,
    generate_dbt_model,
    generate_ddl,
    generate_etl,
)


@pytest.fixture
def sample_model() -> DimensionalModel:
    """A minimal valid dimensional model for testing."""
    return DimensionalModel(
        business_process="Order Processing",
        fact_table=FactTable(
            name="fact_orders",
            grain_description="One row per order line item",
            grain_columns=["order_id", "line_number"],
            measures=[
                Measure(
                    name="quantity",
                    source_column="l_quantity",
                    source_table="lineitem",
                    aggregation="SUM",
                    data_type="NUMERIC",
                    description="Order quantity",
                ),
                Measure(
                    name="extended_price",
                    source_column="l_extendedprice",
                    source_table="lineitem",
                    aggregation="SUM",
                    data_type="NUMERIC",
                    description="Extended price",
                ),
            ],
            dimension_keys=["dim_customer_key", "dim_date_key"],
            degenerate_dimensions=["order_number"],
            source_tables=["lineitem", "orders"],
        ),
        dimensions=[
            Dimension(
                name="dim_customer",
                source_table="customer",
                columns=["name", "address", "phone"],
                natural_key="c_custkey",
                description="Customer dimension",
            ),
            Dimension(
                name="dim_date",
                source_table="dates",
                columns=["year", "month", "day"],
                natural_key="d_datekey",
                description="Date dimension",
                is_date_dimension=True,
            ),
            Dimension(
                name="order_status",
                source_table="orders",
                is_degenerate=True,
                description="Degenerate dimension",
            ),
        ],
    )


class TestGenerateDDL:
    def test_contains_schema(self, sample_model):
        ddl = generate_ddl(sample_model, schema="dw")
        assert 'CREATE SCHEMA IF NOT EXISTS "dw"' in ddl

    def test_contains_dimension_tables(self, sample_model):
        ddl = generate_ddl(sample_model)
        assert '"dim_customer"' in ddl
        assert '"dim_date"' in ddl

    def test_skips_degenerate_dimensions(self, sample_model):
        ddl = generate_ddl(sample_model)
        assert 'CREATE TABLE IF NOT EXISTS "dw"."order_status"' not in ddl

    def test_contains_fact_table(self, sample_model):
        ddl = generate_ddl(sample_model)
        assert '"fact_orders"' in ddl

    def test_contains_measures(self, sample_model):
        ddl = generate_ddl(sample_model)
        assert '"quantity" NUMERIC' in ddl
        assert '"extended_price" NUMERIC' in ddl

    def test_contains_fk_references(self, sample_model):
        ddl = generate_ddl(sample_model)
        assert "REFERENCES" in ddl
        assert "dim_customer_key" in ddl

    def test_custom_schema(self, sample_model):
        ddl = generate_ddl(sample_model, schema="analytics")
        assert '"analytics"' in ddl

    def test_dimension_columns_in_ddl(self, sample_model):
        ddl = generate_ddl(sample_model)
        assert '"name" TEXT' in ddl
        assert '"address" TEXT' in ddl

    def test_loaded_at_column(self, sample_model):
        ddl = generate_ddl(sample_model)
        assert "_loaded_at TIMESTAMP WITH TIME ZONE" in ddl


class TestGenerateETL:
    def test_full_mode_truncates(self, sample_model):
        etl = generate_etl(sample_model, mode="full")
        assert "TRUNCATE TABLE" in etl

    def test_incremental_mode_upserts(self, sample_model):
        etl = generate_etl(sample_model, mode="incremental")
        assert "ON CONFLICT" in etl

    def test_contains_dimension_loads(self, sample_model):
        etl = generate_etl(sample_model)
        assert "Load dimension: dim_customer" in etl
        assert "Load dimension: dim_date" in etl

    def test_contains_fact_load(self, sample_model):
        etl = generate_etl(sample_model)
        assert "Load fact table: fact_orders" in etl

    def test_source_schema(self, sample_model):
        etl = generate_etl(sample_model, source_schema="raw")
        assert '"raw"' in etl

    def test_skips_degenerate_in_dimension_load(self, sample_model):
        etl = generate_etl(sample_model)
        # order_status is degenerate, should not have its own load section
        assert "Load dimension: order_status" not in etl


class TestGenerateDBTModel:
    def test_returns_fact_model(self, sample_model):
        files = generate_dbt_model(sample_model)
        assert "models/marts/fact_orders.sql" in files

    def test_returns_dimension_models(self, sample_model):
        files = generate_dbt_model(sample_model)
        assert "models/marts/dim_customer.sql" in files
        assert "models/marts/dim_date.sql" in files

    def test_skips_degenerate_dimensions(self, sample_model):
        files = generate_dbt_model(sample_model)
        assert "models/marts/order_status.sql" not in files

    def test_returns_schema_yml(self, sample_model):
        files = generate_dbt_model(sample_model)
        assert "models/marts/schema.yml" in files

    def test_schema_yml_content(self, sample_model):
        files = generate_dbt_model(sample_model)
        schema = files["models/marts/schema.yml"]
        assert "fact_orders" in schema
        assert "dim_customer" in schema


class TestGenerateDataDictionary:
    def test_contains_model_info(self, sample_model):
        dd = generate_data_dictionary(sample_model)
        assert "Order Processing" in dd
        assert "fact_orders" in dd

    def test_contains_dimensions(self, sample_model):
        dd = generate_data_dictionary(sample_model)
        assert "dim_customer" in dd
        assert "dim_date" in dd

    def test_contains_measures(self, sample_model):
        dd = generate_data_dictionary(sample_model)
        assert "quantity" in dd
        assert "extended_price" in dd
