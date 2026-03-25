"""Dimensional model definitions with Kimball constraint validation."""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class Measure(BaseModel):
    """A measure (metric) in a fact table."""

    name: str
    source_column: str
    source_table: str
    aggregation: str = "SUM"  # SUM | AVG | COUNT | MIN | MAX | COUNT_DISTINCT
    data_type: str = "NUMERIC"
    description: str = ""


class Dimension(BaseModel):
    """A dimension table in the star schema."""

    name: str  # e.g. dim_customer
    source_table: str
    columns: list[str] = Field(default_factory=list)
    surrogate_key: str = ""  # Auto-generated if empty
    natural_key: str = ""  # Source primary key
    description: str = ""
    is_date_dimension: bool = False
    is_degenerate: bool = False  # Degenerate dimensions live in fact table


class FactTable(BaseModel):
    """A fact table in the star schema."""

    name: str  # e.g. fact_order_items
    grain_description: str  # e.g. "One row per order line item"
    grain_columns: list[str] = Field(min_length=1)  # Columns that define the grain
    measures: list[Measure] = Field(min_length=1)
    dimension_keys: list[str] = Field(default_factory=list)  # FK columns to dimensions
    degenerate_dimensions: list[str] = Field(default_factory=list)
    source_tables: list[str] = Field(default_factory=list)


class DimensionalModel(BaseModel):
    """Complete dimensional model with Kimball constraint validation."""

    version: str = "1.0"
    business_process: str  # e.g. "Order Processing"
    fact_table: FactTable
    dimensions: list[Dimension] = Field(min_length=1)
    description: str = ""

    @model_validator(mode="after")
    def validate_kimball_constraints(self) -> DimensionalModel:
        """Enforce Kimball dimensional modeling rules."""
        # Rule 1: Fact table must have at least one measure
        if not self.fact_table.measures:
            raise ValueError("Fact table must have at least one measure")

        # Rule 2: Must have at least one non-degenerate dimension
        non_degenerate = [d for d in self.dimensions if not d.is_degenerate]
        if not non_degenerate:
            raise ValueError("Model must have at least one non-degenerate dimension")

        # Rule 3: No circular references - dimension source tables must not
        # reference the fact table's source tables in a way that creates cycles
        fact_sources = set(self.fact_table.source_tables)
        dim_sources = set()
        for dim in self.dimensions:
            if dim.source_table in dim_sources:
                raise ValueError(f"Duplicate dimension source table: {dim.source_table}")
            dim_sources.add(dim.source_table)

        # Rule 4: Grain must be defined
        if not self.fact_table.grain_description.strip():
            raise ValueError("Fact table grain must be described")

        # Rule 5: Dimension names should follow naming convention
        for dim in self.dimensions:
            if not dim.is_degenerate and not dim.name.startswith("dim_"):
                raise ValueError(
                    f"Dimension '{dim.name}' should follow 'dim_' naming convention"
                )

        if not self.fact_table.name.startswith("fact_"):
            raise ValueError(
                f"Fact table '{self.fact_table.name}' should follow 'fact_' naming convention"
            )

        return self
