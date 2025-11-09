"""Helpers for loading the canonical player ID crosswalk."""

from __future__ import annotations

import fnmatch
import os
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

import polars as pl

from ff_analytics_utils.duckdb_helper import fetch_table_as_polars
from ingest.common import storage as storage_utils

DEFAULT_DUCKDB_TABLE = os.environ.get("PLAYER_XREF_DUCKDB_TABLE", "main.dim_player_id_xref")
DEFAULT_PARQUET_ROOT = os.environ.get("PLAYER_XREF_PARQUET_ROOT", "data/raw/nflverse/ff_playerids")
DEFAULT_PARQUET_PATTERN = os.environ.get("PLAYER_XREF_PARQUET_PATTERN", "ff_playerids*.parquet")


def get_player_xref(
    *,
    source: str = "auto",
    duckdb_table: str = DEFAULT_DUCKDB_TABLE,
    db_path: str | Path | None = None,
    parquet_root: str | Path | None = None,
    parquet_pattern: str = DEFAULT_PARQUET_PATTERN,
    columns: Sequence[str] | None = None,
) -> pl.DataFrame:
    """Return the canonical player crosswalk as a Polars DataFrame.

    Args:
        source: 'duckdb', 'parquet', or 'auto' to try DuckDB then Parquet fallback.
        duckdb_table: Fully qualified DuckDB table name to query.
        db_path: Override path to DuckDB database (defaults to DBT_DUCKDB_PATH/env).
        parquet_root: Root directory/URI containing partitioned ff_playerids parquet files.
        parquet_pattern: Glob-style pattern for parquet filenames
        (defaults to ff_playerids*.parquet).
        columns: Optional subset of columns to select.

    """
    errors: list[str] = []
    source = source.lower()
    parquet_root = parquet_root or DEFAULT_PARQUET_ROOT

    if source in {"auto", "duckdb"}:
        try:
            return fetch_table_as_polars(duckdb_table, columns=columns, db_path=db_path)
        except Exception as exc:  # pragma: no cover - depends on local db state
            errors.append(f"DuckDB: {exc}")
            if source == "duckdb":
                raise RuntimeError(
                    f"Failed to load player xref from DuckDB table '{duckdb_table}'"
                ) from exc

    if source in {"auto", "parquet"}:
        try:
            parquet_uri = _latest_parquet_uri(parquet_root, parquet_pattern)
            if parquet_uri is None:
                raise FileNotFoundError(
                    f"No parquet files found under {parquet_root} matching {parquet_pattern}"
                )
            df = storage_utils.read_parquet_any(parquet_uri, columns=columns)
            if isinstance(df, pl.DataFrame):
                return df
            return pl.from_arrow(df)
        except Exception as exc:
            errors.append(f"Parquet: {exc}")
            if source == "parquet":
                raise RuntimeError(
                    f"Failed to load player xref from parquet root '{parquet_root}'"
                ) from exc

    error_detail = "; ".join(errors) if errors else "unknown error"
    raise RuntimeError(
        "Unable to load player crosswalk from DuckDB or Parquet. "
        "Ensure `dbt run --select dim_player_id_xref` has completed or provide "
        "PLAYER_XREF_PARQUET_ROOT pointing at nflverse/ff_playerids.\n"
        f"Details: {error_detail}"
    )


def _latest_parquet_uri(root: str | Path, pattern: str) -> str | None:
    """Return the most recent parquet file under the root based on dt=YYYY-MM-DD segments."""
    entries = storage_utils.list_uri_contents(str(root), recursive=True)
    parquet_candidates: list[tuple[str, datetime | None]] = []
    for entry in entries:
        if entry.is_dir:
            continue
        filename = entry.path.split("/")[-1]
        if not fnmatch.fnmatch(filename, pattern):
            continue
        partition_value = _extract_partition(entry.path, prefix="dt=")
        partition_dt = _parse_dt(partition_value)
        parquet_candidates.append((entry.path, partition_dt))

    if not parquet_candidates:
        return None

    parquet_candidates.sort(key=lambda item: (item[1] or datetime.min, item[0]))
    return parquet_candidates[-1][0]


def _extract_partition(path: str, prefix: str) -> str | None:
    for segment in path.replace("\\", "/").split("/"):
        if segment.startswith(prefix):
            return segment.split("=", 1)[1]
    return None


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%Y%m%d"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None
