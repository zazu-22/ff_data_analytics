"""Helpers for loading the player name alias table."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import polars as pl

from ff_analytics_utils.duckdb_helper import fetch_table_as_polars

DEFAULT_DUCKDB_TABLE = "main.dim_name_alias"
DEFAULT_CSV_PATH = "dbt/ff_data_transform/seeds/dim_name_alias.csv"


def get_name_alias(
    *,
    source: str = "auto",
    duckdb_table: str = DEFAULT_DUCKDB_TABLE,
    db_path: str | Path | None = None,
    csv_path: str | Path | None = None,
    columns: Sequence[str] | None = None,
) -> pl.DataFrame:
    """Return the name alias table as a Polars DataFrame.

    Args:
        source: 'duckdb', 'csv', or 'auto' to try DuckDB then CSV fallback.
        duckdb_table: Fully qualified DuckDB table name to query.
        db_path: Override path to DuckDB database (defaults to DBT_DUCKDB_PATH/env).
        csv_path: Path to CSV seed file (defaults to dim_name_alias.csv).
        columns: Optional subset of columns to select.

    Returns:
        DataFrame with columns: alias_name, canonical_name, alias_type, notes,
        position, treat_as_position

    Raises:
        RuntimeError: If unable to load from any source

    Example:
        # DuckDB-first (requires dbt seed)
        alias_df = get_name_alias()

        # Force CSV (for testing)
        alias_df = get_name_alias(source="csv")

    """
    errors: list[str] = []
    source = source.lower()
    csv_path = csv_path or DEFAULT_CSV_PATH

    if source in {"auto", "duckdb"}:
        try:
            return fetch_table_as_polars(duckdb_table, columns=columns, db_path=db_path)
        except Exception as exc:  # pragma: no cover - depends on local db state
            errors.append(f"DuckDB: {exc}")
            if source == "duckdb":
                raise RuntimeError(
                    f"Failed to load name alias from DuckDB table '{duckdb_table}'"
                ) from exc

    if source in {"auto", "csv"}:
        try:
            df = pl.read_csv(csv_path)
            if columns:
                df = df.select(columns)
            return df
        except Exception as exc:
            errors.append(f"CSV: {exc}")
            if source == "csv":
                raise RuntimeError(f"Failed to load name alias from CSV '{csv_path}'") from exc

    error_detail = "; ".join(errors) if errors else "unknown error"
    raise RuntimeError(
        "Unable to load name alias from DuckDB or CSV. "
        "Ensure `dbt seed --select dim_name_alias` has completed or provide "
        f"a valid CSV path.\nDetails: {error_detail}"
    )
