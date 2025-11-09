"""Utility helpers for interacting with the local DuckDB dbt artifact."""

from __future__ import annotations

import os
import re
from collections.abc import Generator, Sequence
from contextlib import contextmanager
from pathlib import Path

import duckdb
import polars as pl

DEFAULT_DBT_DB = Path("dbt/ff_data_transform/target/dev.duckdb")

# Pattern for safe SQL identifiers: alphanumeric, underscore, dot (for schema.table)
_SAFE_IDENTIFIER_PATTERN = re.compile(r"^[a-zA-Z0-9_.]+$")


def resolve_duckdb_path(explicit_path: str | Path | None = None) -> Path:
    """Return the DuckDB path, honoring DBT_DUCKDB_PATH overrides."""
    if explicit_path is not None:
        return Path(explicit_path)
    env_path = os.environ.get("DBT_DUCKDB_PATH")
    if env_path:
        return Path(env_path)
    return DEFAULT_DBT_DB


def get_duckdb_connection(
    db_path: str | Path | None = None, *, read_only: bool = True
) -> duckdb.DuckDBPyConnection:
    """Create a DuckDB connection to the dbt target database."""
    path = resolve_duckdb_path(db_path)
    return duckdb.connect(str(path), read_only=read_only)


@contextmanager
def duckdb_cursor(
    db_path: str | Path | None = None, *, read_only: bool = True
) -> Generator[duckdb.DuckDBPyConnection]:
    """Context manager yielding a DuckDB connection that is closed automatically."""
    conn = get_duckdb_connection(db_path=db_path, read_only=read_only)
    try:
        yield conn
    finally:
        conn.close()


def _validate_sql_identifier(identifier: str, name: str) -> None:
    """Validate that an identifier is safe for SQL construction.

    Args:
        identifier: The identifier to validate (table name or column name).
        name: The parameter name for error messages.

    Raises:
        ValueError: If the identifier contains unsafe characters.

    """
    if not _SAFE_IDENTIFIER_PATTERN.match(identifier):
        raise ValueError(
            f"Invalid {name}: '{identifier}'. "
            "Only alphanumeric characters, underscores, and dots are allowed."
        )


def _quote_identifier(identifier: str) -> str:
    """Quote a SQL identifier safely.

    Args:
        identifier: The identifier to quote (already validated).

    Returns:
        Properly quoted identifier for DuckDB.

    """
    # Split on dots to handle schema.table format
    parts = identifier.split(".")
    # Quote each part and escape any existing double quotes
    quoted_parts: list[str] = []
    for part in parts:
        escaped = part.replace('"', '""')
        quoted_parts.append(f'"{escaped}"')
    return ".".join(quoted_parts)


def fetch_table_as_polars(
    table: str,
    *,
    columns: Sequence[str] | None = None,
    db_path: str | Path | None = None,
) -> pl.DataFrame:
    """Fetch a table from DuckDB into a Polars DataFrame.

    Args:
        table: Fully qualified table name (e.g., 'main.dim_player_id_xref').
        columns: Optional sequence of column names to select.
        db_path: Optional path to DuckDB database file.

    Returns:
        Polars DataFrame containing the table data.

    Raises:
        ValueError: If table or column names contain unsafe characters.

    """
    _validate_sql_identifier(table, "table name")
    if columns:
        for col in columns:
            _validate_sql_identifier(col, "column name")
    # Safe: identifiers are validated and properly quoted
    column_sql = ", ".join(_quote_identifier(col) for col in columns) if columns else "*"
    quoted_table = _quote_identifier(table)
    query = f"select {column_sql} from {quoted_table}"  # noqa: S608
    with duckdb_cursor(db_path=db_path) as conn:
        arrow_table = conn.execute(query).fetch_arrow_table()
    result = pl.from_arrow(arrow_table)
    assert isinstance(result, pl.DataFrame)
    return result
