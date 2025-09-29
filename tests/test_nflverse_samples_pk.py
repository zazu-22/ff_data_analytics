from pathlib import Path

import pandas as pd
import pytest

SAMPLES = Path("samples/nflverse")


def _require_sample(path: Path):
    if not path.exists():
        pytest.skip(f"Sample not found: {path}")


def test_players_primary_key_unique():
    """Validate players sample has non-null unique gsis_id primary key."""
    parquet = SAMPLES / "players" / "players.parquet"
    _require_sample(parquet)
    players_df = pd.read_parquet(parquet)
    assert "gsis_id" in players_df.columns, "players should include 'gsis_id' field"
    non_null = players_df["gsis_id"].dropna()
    assert len(non_null) > 0, "gsis_id should not be all null"
    assert non_null.is_unique, "gsis_id must be unique in players sample"


def test_weekly_composite_key_unique():
    """Validate weekly sample has unique composite key (season, week, gsis_id)."""
    parquet = SAMPLES / "weekly" / "weekly.parquet"
    _require_sample(parquet)
    weekly_df = pd.read_parquet(parquet)
    # Accept either 'gsis_id' or 'player_id' as the raw identifier; staging will normalize
    id_col = "gsis_id" if "gsis_id" in weekly_df.columns else "player_id"
    for col in ("season", "week", id_col):
        assert col in weekly_df.columns, f"weekly should include '{col}'"
    key = weekly_df[["season", "week", id_col]].astype(str).agg("|".join, axis=1)
    assert key.is_unique, "(season, week, gsis_id) must be unique in weekly sample"
