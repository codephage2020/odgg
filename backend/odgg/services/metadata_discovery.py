"""Metadata discovery service using async SQLAlchemy + information_schema."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

from odgg.models.metadata import (
    ColumnInfo,
    MetadataSnapshot,
    RelationshipInfo,
    TableInfo,
)
from odgg.services.sanitizer import is_safe_identifier

logger = logging.getLogger(__name__)


async def discover_metadata(
    connection_url: str,
    schema: str = "public",
) -> MetadataSnapshot:
    """Discover database metadata using information_schema batch queries.

    Uses batch SQL against information_schema instead of per-table Inspector
    calls for much better performance on databases with many tables.
    """
    engine = create_async_engine(connection_url, echo=False)

    try:
        async with engine.connect() as conn:
            tables = await _discover_tables(conn, schema)
            columns = await _discover_columns(conn, schema)
            pks = await _discover_primary_keys(conn, schema)
            fk_rels = await _discover_foreign_keys(conn, schema)
            stats = await _discover_statistics(conn, schema)

            # Assemble table info
            table_map: dict[str, TableInfo] = {}
            for t in tables:
                table_map[t["table_name"]] = TableInfo(
                    name=t["table_name"],
                    schema_name=schema,
                    comment=t.get("comment"),
                )

            # Attach columns to tables
            for c in columns:
                tname = c["table_name"]
                if tname not in table_map:
                    continue
                pk_cols = pks.get(tname, set())
                table_map[tname].columns.append(
                    ColumnInfo(
                        name=c["column_name"],
                        data_type=c["data_type"],
                        nullable=c["is_nullable"] == "YES",
                        is_primary_key=c["column_name"] in pk_cols,
                        default=c.get("column_default"),
                        comment=c.get("comment"),
                    )
                )
                if c["column_name"] in pk_cols:
                    table_map[tname].primary_key.append(c["column_name"])

            # Attach row counts
            for tname, count in stats.items():
                if tname in table_map:
                    table_map[tname].row_count = count

            # Build relationships from FKs
            relationships = [
                RelationshipInfo(
                    source_table=fk["source_table"],
                    source_column=fk["source_column"],
                    target_table=fk["target_table"],
                    target_column=fk["target_column"],
                    is_inferred=False,
                    confidence=1.0,
                )
                for fk in fk_rels
            ]

            # Add heuristic-inferred relationships where no FK exists
            inferred = _infer_relationships(list(table_map.values()), relationships)
            relationships.extend(inferred)

            # Get database name
            db_name = await _get_database_name(conn)

            return MetadataSnapshot(
                tables=list(table_map.values()),
                relationships=relationships,
                database_name=db_name,
                database_type="postgresql",
                discovered_at=datetime.now(timezone.utc).isoformat(),
            )
    finally:
        await engine.dispose()


async def _discover_tables(conn: AsyncConnection, schema: str) -> list[dict]:
    """Batch-discover all tables in the schema."""
    result = await conn.execute(
        text("""
            SELECT t.table_name,
                   pg_catalog.obj_description(c.oid) as comment
            FROM information_schema.tables t
            LEFT JOIN pg_catalog.pg_class c ON c.relname = t.table_name
            LEFT JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
                AND n.nspname = t.table_schema
            WHERE t.table_schema = :schema
              AND t.table_type = 'BASE TABLE'
            ORDER BY t.table_name
        """),
        {"schema": schema},
    )
    return [dict(row._mapping) for row in result]


async def _discover_columns(conn: AsyncConnection, schema: str) -> list[dict]:
    """Batch-discover all columns across all tables."""
    result = await conn.execute(
        text("""
            SELECT c.table_name,
                   c.column_name,
                   c.data_type,
                   c.is_nullable,
                   c.column_default,
                   pg_catalog.col_description(
                       (SELECT oid FROM pg_catalog.pg_class WHERE relname = c.table_name),
                       c.ordinal_position
                   ) as comment
            FROM information_schema.columns c
            WHERE c.table_schema = :schema
            ORDER BY c.table_name, c.ordinal_position
        """),
        {"schema": schema},
    )
    return [dict(row._mapping) for row in result]


async def _discover_primary_keys(
    conn: AsyncConnection, schema: str
) -> dict[str, set[str]]:
    """Batch-discover primary keys for all tables."""
    result = await conn.execute(
        text("""
            SELECT tc.table_name, kcu.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            WHERE tc.constraint_type = 'PRIMARY KEY'
              AND tc.table_schema = :schema
        """),
        {"schema": schema},
    )
    pks: dict[str, set[str]] = {}
    for row in result:
        mapping = row._mapping
        pks.setdefault(mapping["table_name"], set()).add(mapping["column_name"])
    return pks


async def _discover_foreign_keys(conn: AsyncConnection, schema: str) -> list[dict]:
    """Batch-discover all foreign key relationships."""
    result = await conn.execute(
        text("""
            SELECT
                kcu.table_name as source_table,
                kcu.column_name as source_column,
                ccu.table_name as target_table,
                ccu.column_name as target_column
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage ccu
                ON ccu.constraint_name = tc.constraint_name
                AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
              AND tc.table_schema = :schema
        """),
        {"schema": schema},
    )
    return [dict(row._mapping) for row in result]


async def _discover_statistics(
    conn: AsyncConnection, schema: str
) -> dict[str, int]:
    """Get approximate row counts for all tables using pg_stat."""
    result = await conn.execute(
        text("""
            SELECT relname as table_name,
                   n_live_tup as row_count
            FROM pg_stat_user_tables
            WHERE schemaname = :schema
        """),
        {"schema": schema},
    )
    return {row._mapping["table_name"]: row._mapping["row_count"] for row in result}


async def _get_database_name(conn: AsyncConnection) -> str:
    """Get the current database name."""
    result = await conn.execute(text("SELECT current_database()"))
    row = result.scalar()
    return row or ""


def _infer_relationships(
    tables: list[TableInfo],
    existing: list[RelationshipInfo],
) -> list[RelationshipInfo]:
    """Infer FK relationships via column naming heuristics.

    Pattern: if table A has column 'xyz_id' and table 'xyz' (or 'xyzs')
    has a column 'id', infer A.xyz_id -> xyz.id.
    """
    # Build lookup of existing relationships to avoid duplicates
    existing_pairs = {
        (r.source_table, r.source_column, r.target_table, r.target_column)
        for r in existing
    }

    # Build table name lookup (singular and plural forms)
    table_names = {t.name for t in tables}
    pk_by_table: dict[str, str] = {}
    for t in tables:
        if t.primary_key:
            pk_by_table[t.name] = t.primary_key[0]

    inferred: list[RelationshipInfo] = []

    for table in tables:
        for col in table.columns:
            if not col.name.endswith("_id"):
                continue

            # Extract potential target table name
            prefix = col.name[:-3]  # Remove '_id'
            candidates = [prefix, f"{prefix}s", f"{prefix}es", f"{prefix}ies"]

            for candidate in candidates:
                if candidate not in table_names or candidate == table.name:
                    continue

                target_col = pk_by_table.get(candidate, "id")
                key = (table.name, col.name, candidate, target_col)
                if key in existing_pairs:
                    continue

                # Verify target table has the target column
                target_table = next(
                    (t for t in tables if t.name == candidate), None
                )
                if target_table and any(
                    c.name == target_col for c in target_table.columns
                ):
                    inferred.append(
                        RelationshipInfo(
                            source_table=table.name,
                            source_column=col.name,
                            target_table=candidate,
                            target_column=target_col,
                            is_inferred=True,
                            confidence=0.8,
                        )
                    )
                    existing_pairs.add(key)
                    break  # Take first match

    return inferred
