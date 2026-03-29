"""Code generation engine — DDL, ETL SQL, and dbt models via Jinja2 templates."""

from __future__ import annotations

from jinja2 import Environment, PackageLoader, select_autoescape

from odgg.models.dimensional import DimensionalModel
from odgg.services.sanitizer import quote_identifier

_env = Environment(
    loader=PackageLoader("odgg", "templates"),
    autoescape=select_autoescape([]),
    trim_blocks=True,
    lstrip_blocks=True,
)

# Register quote_identifier as a Jinja2 filter
_env.filters["quote_id"] = quote_identifier


def generate_ddl(model: DimensionalModel, schema: str = "dw") -> str:
    """Generate PostgreSQL DDL (CREATE TABLE) for the dimensional model."""
    template = _env.get_template("ddl.sql.j2")
    return template.render(model=model, schema=schema)


def generate_etl(
    model: DimensionalModel,
    schema: str = "dw",
    source_schema: str = "public",
    mode: str = "full",  # full | incremental
) -> str:
    """Generate ETL SQL (INSERT/SELECT or MERGE) for the dimensional model."""
    template = _env.get_template("etl.sql.j2")
    return template.render(
        model=model,
        schema=schema,
        source_schema=source_schema,
        mode=mode,
    )


def generate_dbt_model(model: DimensionalModel) -> dict[str, str]:
    """Generate dbt model files (.sql + schema.yml).

    Returns a dict of filename -> content.
    """
    files: dict[str, str] = {}

    # Fact table model
    fact_template = _env.get_template("dbt_fact.sql.j2")
    files[f"models/marts/{model.fact_table.name}.sql"] = fact_template.render(
        model=model
    )

    # Dimension models
    dim_template = _env.get_template("dbt_dimension.sql.j2")
    for dim in model.dimensions:
        if dim.is_degenerate:
            continue
        files[f"models/marts/{dim.name}.sql"] = dim_template.render(
            model=model, dim=dim
        )

    # schema.yml
    schema_template = _env.get_template("dbt_schema.yml.j2")
    files["models/marts/schema.yml"] = schema_template.render(model=model)

    return files


def generate_data_dictionary(model: DimensionalModel) -> str:
    """Generate a Markdown data dictionary for the model."""
    template = _env.get_template("data_dictionary.md.j2")
    return template.render(model=model)


def generate_brief_export(
    title: str,
    status: str,
    source_db_type: str,
    database_name: str | None,
    updated_at: str,
    sections: list[dict],
) -> str:
    """Generate stakeholder-friendly Markdown export of a modeling brief."""
    template = _env.get_template("brief_export.md.j2")
    return template.render(
        title=title,
        status=status,
        source_db_type=source_db_type,
        database_name=database_name,
        updated_at=updated_at,
        sections=sections,
    )
