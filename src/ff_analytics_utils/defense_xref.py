"""Helpers for loading the NFL team defense crosswalk (defense_id mapping)."""

from __future__ import annotations

import os
from collections.abc import Sequence
from pathlib import Path

import polars as pl

from ff_analytics_utils.duckdb_helper import fetch_table_as_polars

DEFAULT_DUCKDB_TABLE = os.environ.get("DEFENSE_XREF_DUCKDB_TABLE", "main.dim_team_defense_xref")
DEFAULT_CSV_PATH = os.environ.get(
    "DEFENSE_XREF_CSV_PATH",
    "dbt/ff_data_transform/seeds/seed_team_defense_xref.csv",
)


def get_defense_xref(
    *,
    source: str = "auto",
    duckdb_table: str = DEFAULT_DUCKDB_TABLE,
    db_path: str | Path | None = None,
    csv_path: str | Path | None = None,
    columns: Sequence[str] | None = None,
) -> pl.DataFrame:
    """Return the NFL team defense crosswalk as a Polars DataFrame.

    Defense IDs use the 90,000 range (90001-90036) to ensure clear separation
    from individual player IDs (1-9757, max ~28K with full NFL history).

    This provides mapping from various team name formats (FFAnalytics providers)
    to canonical defense_id values compatible with player_id joins.

    **DuckDB-first with CSV fallback pattern:**
    - Default (source='auto'): Try DuckDB first, fall back to CSV seed
    - DuckDB is faster (~9K+ projections processed)
    - CSV fallback ensures first-run works without `dbt seed`

    Args:
        source: 'duckdb', 'csv', or 'auto' to try DuckDB then CSV fallback.
        duckdb_table: Fully qualified DuckDB table name to query.
        db_path: Override path to DuckDB database (defaults to DBT_DUCKDB_PATH/env).
        csv_path: Path to seed CSV file (defaults to
            dbt/ff_data_transform/seeds/seed_team_defense_xref.csv).
        columns: Optional subset of columns to select.

    Returns:
        Polars DataFrame with columns:
            - defense_id (90001-90036): Canonical defense player_id
            - team_abbrev: 3-letter NFL code (ARI, ATL, etc.)
            - team_name_primary: Full name ("Arizona Cardinals")
            - team_name_alias_1: Reversed format ("Cardinals, Arizona")
            - team_name_alias_2: Nickname only ("Cardinals")
            - team_name_alias_3: City only ("Arizona")
            - team_name_alias_4: With suffix ("Cardinals D/ST")
            - position_primary: Always "DST"
            - position_alias_1: "D"
            - position_alias_2: "D/ST"
            - position_alias_3: "DEF"

    Examples:
        >>> # Default: Try DuckDB first, fall back to CSV
        >>> defense_xref = get_defense_xref()

        >>> # Force CSV (for testing or first run without dbt seed)
        >>> defense_xref = get_defense_xref(source='csv')

        >>> # Force DuckDB (fails if table doesn't exist)
        >>> defense_xref = get_defense_xref(source='duckdb')

        >>> # Select specific columns only
        >>> defense_xref = get_defense_xref(columns=['defense_id', 'team_abbrev'])

    Raises:
        RuntimeError: If unable to load from either DuckDB or CSV.

    Related:
        - P1-028: Add DST team defense seed for FFAnalytics mapping
        - ADR-011: Sequential Surrogate Key for player_id (90K range strategy)
        - dim_team_defense_xref: dbt model (DuckDB table)
        - seed_team_defense_xref.csv: Source of truth (version-controlled)

    """
    errors: list[str] = []
    source = source.lower()
    csv_path = csv_path or DEFAULT_CSV_PATH

    if source in {"auto", "duckdb"}:
        try:
            df = fetch_table_as_polars(duckdb_table, columns=columns, db_path=db_path)
            # Optionally filter to only selected columns if specified
            if columns:
                df = df.select(columns)
            return df
        except Exception as exc:  # pragma: no cover - depends on local db state
            errors.append(f"DuckDB: {exc}")
            if source == "duckdb":
                raise RuntimeError(
                    f"Failed to load defense xref from DuckDB table '{duckdb_table}'"
                ) from exc

    if source in {"auto", "csv"}:
        try:
            df = pl.read_csv(csv_path)
            # Optionally filter to only selected columns if specified
            if columns:
                df = df.select(columns)
            return df
        except Exception as exc:
            errors.append(f"CSV: {exc}")
            if source == "csv":
                raise RuntimeError(f"Failed to load defense xref from CSV '{csv_path}'") from exc

    error_detail = "; ".join(errors) if errors else "unknown error"
    raise RuntimeError(
        "Unable to load defense crosswalk from DuckDB or CSV. "
        "Ensure `dbt seed --select seed_team_defense_xref` and "
        "`dbt run --select dim_team_defense_xref` have completed, "
        f"or provide valid csv_path.\nDetails: {error_detail}"
    )
