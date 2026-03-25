"""ODGG CLI — command-line interface for dimensional modeling."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(
    name="odgg",
    help="ODGG — Conversational Dimensional Modeling Notebook CLI",
    no_args_is_help=True,
)
console = Console()


@app.command()
def connect(
    url: str = typer.Option(..., "--url", "-u", help="PostgreSQL connection URL"),
    schema: str = typer.Option("public", "--schema", "-s", help="Schema to scan"),
    output: str = typer.Option("metadata.json", "--output", "-o", help="Output file"),
) -> None:
    """Connect to a database and discover metadata."""
    import asyncio

    from odgg.services.metadata_discovery import discover_metadata

    console.print(f"[bold blue]Connecting to database...[/bold blue]")

    try:
        snapshot = asyncio.run(discover_metadata(url, schema))
        Path(output).write_text(json.dumps(snapshot.model_dump(), indent=2))
        console.print(f"[green]Discovered {len(snapshot.tables)} tables, "
                      f"{len(snapshot.relationships)} relationships[/green]")
        console.print(f"[dim]Saved to {output}[/dim]")

        # Summary table
        table = Table(title="Tables")
        table.add_column("Name")
        table.add_column("Columns", justify="right")
        table.add_column("Rows", justify="right")
        for t in snapshot.tables:
            table.add_row(t.name, str(len(t.columns)), str(t.row_count or "?"))
        console.print(table)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from None


@app.command()
def model(
    metadata_file: str = typer.Option("metadata.json", "--metadata", "-m"),
    output: str = typer.Option("model.json", "--output", "-o"),
) -> None:
    """Load metadata and display modeling summary (interactive mode via Web UI)."""
    try:
        data = json.loads(Path(metadata_file).read_text())
        from odgg.models.metadata import MetadataSnapshot
        snapshot = MetadataSnapshot(**data)

        console.print(f"[bold blue]Loaded metadata: {snapshot.database_name}[/bold blue]")
        console.print(f"Tables: {len(snapshot.tables)}")
        console.print(f"Relationships: {len(snapshot.relationships)}")
        console.print("\n[yellow]Interactive modeling is available via the Web UI.[/yellow]")
        console.print("[dim]Run: uvicorn odgg.app:app --reload[/dim]")

    except FileNotFoundError:
        console.print(f"[red]Metadata file not found: {metadata_file}[/red]")
        console.print("[dim]Run 'odgg connect' first to discover metadata.[/dim]")
        raise typer.Exit(1) from None


@app.command()
def generate(
    model_file: str = typer.Option("model.json", "--model", "-m"),
    output_dir: str = typer.Option("output", "--output", "-o"),
    mode: str = typer.Option("full", "--mode", help="ETL mode: full | incremental"),
    include_dbt: bool = typer.Option(True, "--dbt/--no-dbt", help="Generate dbt models"),
) -> None:
    """Generate DDL, ETL SQL, and dbt models from a saved model file."""
    try:
        data = json.loads(Path(model_file).read_text())
        from odgg.models.dimensional import DimensionalModel
        from odgg.services.codegen import (
            generate_data_dictionary,
            generate_dbt_model,
            generate_ddl,
            generate_etl,
        )

        dm = DimensionalModel(**data)

        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        # DDL
        ddl = generate_ddl(dm)
        (out / "ddl.sql").write_text(ddl)
        console.print(f"[green]Generated DDL → {out / 'ddl.sql'}[/green]")

        # ETL
        etl = generate_etl(dm, mode=mode)
        (out / "etl.sql").write_text(etl)
        console.print(f"[green]Generated ETL → {out / 'etl.sql'}[/green]")

        # Data dictionary
        dd = generate_data_dictionary(dm)
        (out / "data_dictionary.md").write_text(dd)
        console.print(f"[green]Generated Data Dictionary → {out / 'data_dictionary.md'}[/green]")

        # dbt
        if include_dbt:
            dbt_files = generate_dbt_model(dm)
            for filename, content in dbt_files.items():
                filepath = out / filename
                filepath.parent.mkdir(parents=True, exist_ok=True)
                filepath.write_text(content)
                console.print(f"[green]Generated dbt → {filepath}[/green]")

        console.print(f"\n[bold green]All outputs generated in {out}/[/bold green]")

    except FileNotFoundError:
        console.print(f"[red]Model file not found: {model_file}[/red]")
        console.print("[dim]Complete the modeling flow in the Web UI first, then export.[/dim]")
        raise typer.Exit(1) from None
    except Exception as e:
        console.print(f"[red]Generation failed: {e}[/red]")
        raise typer.Exit(1) from None


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", "--host"),
    port: int = typer.Option(8000, "--port"),
    reload: bool = typer.Option(False, "--reload"),
) -> None:
    """Start the ODGG API server."""
    import uvicorn
    uvicorn.run("odgg.app:app", host=host, port=port, reload=reload)


if __name__ == "__main__":
    app()
