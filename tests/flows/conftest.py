"""Shared fixtures for flow tests.

This module provides common test fixtures for:
- Mock snapshot registries
- Sample manifests
- Temporary file paths
- Mock DataFrames
"""

import polars as pl
import pytest


@pytest.fixture
def mock_registry_empty(tmp_path):
    """Create an empty snapshot registry CSV with proper schema."""
    registry_path = tmp_path / "snapshot_registry.csv"

    # Write header-only CSV manually to avoid schema issues
    registry_path.write_text(
        "source,dataset,snapshot_date,status,coverage_start_season,coverage_end_season,row_count,notes\n"
    )

    return registry_path


@pytest.fixture
def mock_registry_with_data(tmp_path):
    """Create temporary registry with existing snapshots."""
    registry_data = pl.DataFrame(
        [
            {
                "source": "nflverse",
                "dataset": "weekly",
                "snapshot_date": "2024-01-01",
                "status": "current",
                "coverage_start_season": 2023,
                "coverage_end_season": 2024,
                "row_count": 10000,
                "notes": "Initial snapshot",
            },
            {
                "source": "ktc",
                "dataset": "players",
                "snapshot_date": "2024-01-01",
                "status": "current",
                "coverage_start_season": None,
                "coverage_end_season": None,
                "row_count": 5000,
                "notes": "KTC dynasty_1qb ingestion",
            },
        ]
    )

    registry_path = tmp_path / "snapshot_registry.csv"
    registry_data.write_csv(registry_path)
    return registry_path


@pytest.fixture
def sample_ktc_players_valid(tmp_path):
    """Create sample KTC players dataset with valid valuations."""
    data = pl.DataFrame(
        {
            "player_name": ["Player A", "Player B", "Player C"],
            "value": [5000, 8000, 3500],
            "position": ["QB", "RB", "WR"],
        }
    )

    path = tmp_path / "ktc_players.parquet"
    data.write_parquet(path)
    return path


@pytest.fixture
def sample_ktc_players_invalid(tmp_path):
    """Create sample KTC players with invalid valuations (negative, excessive)."""
    data = pl.DataFrame(
        {
            "player_name": ["Player D", "Player E", "Player F"],
            "value": [-100, 15000, 5000],  # Invalid: negative and > 10000
            "position": ["QB", "RB", "WR"],
        }
    )

    path = tmp_path / "ktc_invalid.parquet"
    data.write_parquet(path)
    return path


@pytest.fixture
def sample_nflverse_weekly(tmp_path):
    """Create sample NFLverse weekly dataset."""
    data = pl.DataFrame(
        {
            "player_id": ["P001", "P002", "P003"],
            "player_name": ["Player 1", "Player 2", "Player 3"],
            "season": [2024, 2024, 2024],
            "week": [1, 1, 1],
            "fantasy_points": [25.5, 18.2, 12.8],
        }
    )

    path = tmp_path / "nflverse_weekly.parquet"
    data.write_parquet(path)
    return path


@pytest.fixture
def sample_manifest_ktc(sample_ktc_players_valid):
    """Create a sample KTC manifest dictionary."""
    return {
        "output_path": str(sample_ktc_players_valid),
        "row_count": 3,
        "dataset": "players",
        "market_scope": "dynasty_1qb",
    }


@pytest.fixture
def sample_manifest_nflverse(sample_nflverse_weekly):
    """Create a sample NFLverse manifest dictionary."""
    return {
        "parquet_file": str(sample_nflverse_weekly),
        "meta": {"output_parquet": str(sample_nflverse_weekly)},
        "dataset": "weekly",
        "seasons": [2024],
    }


@pytest.fixture
def mock_duckdb_xref(tmp_path, monkeypatch):
    """Mock dim_player_id_xref DuckDB database."""
    import duckdb

    db_path = tmp_path / "dev.duckdb"

    # Create mock xref table
    pl.DataFrame(
        {
            "name": ["Player A", "Player B", "Player C", "Player 1", "Player 2"],
            "player_id": ["PA001", "PB002", "PC003", "P001", "P002"],
        }
    )

    # Write to DuckDB
    conn = duckdb.connect(str(db_path))
    conn.execute("CREATE TABLE dim_player_id_xref AS SELECT * FROM xref_data")
    conn.close()

    return db_path
