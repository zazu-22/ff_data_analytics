from __future__ import annotations

from pathlib import Path

import duckdb
import polars as pl
import pytest

from ff_analytics_utils import player_xref


def test_get_player_xref_duckdb(monkeypatch, tmp_path: Path) -> None:
    """Test loading player xref from DuckDB table."""
    db_path = tmp_path / "dev.duckdb"
    conn = duckdb.connect(str(db_path))
    conn.execute(
        """
        create table main.dim_player_id_xref as
        select 1 as mfl_id, 'Test Player' as display_name
        """
    )
    conn.close()
    monkeypatch.setenv("DBT_DUCKDB_PATH", str(db_path))

    df = player_xref.get_player_xref(source="duckdb")
    assert df.shape == (1, df.width)
    assert df.filter(pl.col("mfl_id") == 1)["display_name"][0] == "Test Player"


def test_get_player_xref_parquet(tmp_path: Path) -> None:
    """Test loading player xref from Parquet files with partition selection."""
    root = tmp_path / "ff_playerids"
    older = root / "dt=2025-10-01"
    newer = root / "dt=2025-11-02"
    older.mkdir(parents=True, exist_ok=True)
    newer.mkdir(parents=True, exist_ok=True)

    older_df = pl.DataFrame({"mfl_id": [1], "display_name": ["Old Player"]})
    newer_df = pl.DataFrame({"mfl_id": [99], "display_name": ["New Player"]})
    older_df.write_parquet(older / "ff_playerids_old.parquet")
    newer_df.write_parquet(newer / "ff_playerids_new.parquet")

    df = player_xref.get_player_xref(source="parquet", parquet_root=str(root))
    assert df.height == 1
    assert df["display_name"][0] == "New Player"


def test_get_player_xref_failure(monkeypatch, tmp_path: Path) -> None:
    """Test error handling when DuckDB table is missing."""
    monkeypatch.setenv("DBT_DUCKDB_PATH", str(tmp_path / "missing.duckdb"))
    with pytest.raises(RuntimeError):
        player_xref.get_player_xref(source="duckdb")
