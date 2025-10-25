"""KTC dataset registry and loader functions."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from ingest.common.storage import write_parquet_any
from ingest.ktc.client import KTCClient, MarketScope

# Dataset registry following nflverse pattern
DATASETS = {
    "players": {
        "loader": "load_players",
        "description": "Dynasty player market values from KeepTradeCut",
        "primary_key": ["player_name", "market_scope", "asof_date"],
    },
    "picks": {
        "loader": "load_picks",
        "description": "Dynasty draft pick market values from KeepTradeCut",
        "primary_key": ["pick_name", "market_scope", "asof_date"],
    },
}


def load_players(
    out_dir: str = "data/raw/ktc",
    market_scope: MarketScope = "dynasty_1qb",
    cache_dir: str | None = None,
) -> dict:
    """Load player market values from KeepTradeCut.

    Args:
        out_dir: Base output directory
        market_scope: "dynasty_1qb" or "dynasty_superflex"
        cache_dir: Optional cache directory for HTML responses

    Returns:
        dict: Manifest with output_path, row_count, metadata

    """
    client = KTCClient(
        market_scope=market_scope,
        cache_dir=Path(cache_dir) if cache_dir else None,
    )

    players_df = client.fetch_players()

    if len(players_df) == 0:
        raise ValueError("No player data returned from KTC")

    # Write to partitioned path
    dt = datetime.now(UTC).strftime("%Y-%m-%d")
    dest_dir = f"{out_dir.rstrip('/')}/players/dt={dt}"
    dest = f"{dest_dir}/players_{dt}.parquet"

    write_parquet_any(players_df, dest)

    # Write metadata
    meta = {
        "dataset": "players",
        "asof_datetime": datetime.now(UTC).isoformat(),
        "loader_path": "src.ingest.ktc.registry.load_players",
        "source_name": "keeptradecut",
        "source_url": "https://keeptradecut.com/dynasty-rankings",
        "market_scope": market_scope,
        "row_count": len(players_df),
        "output_parquet": [dest],
    }

    meta_path = f"{dest_dir}/_meta.json"
    import json

    Path(meta_path).parent.mkdir(parents=True, exist_ok=True)
    Path(meta_path).write_text(json.dumps(meta, indent=2))

    return {
        "output_path": dest,
        "meta_path": meta_path,
        "row_count": len(players_df),
        "metadata": meta,
    }


def load_picks(
    out_dir: str = "data/raw/ktc",
    market_scope: MarketScope = "dynasty_1qb",
    cache_dir: str | None = None,
) -> dict:
    """Load draft pick market values from KeepTradeCut.

    Args:
        out_dir: Base output directory
        market_scope: "dynasty_1qb" or "dynasty_superflex"
        cache_dir: Optional cache directory for HTML responses

    Returns:
        dict: Manifest with output_path, row_count, metadata

    """
    client = KTCClient(
        market_scope=market_scope,
        cache_dir=Path(cache_dir) if cache_dir else None,
    )

    picks_df = client.fetch_picks()

    if len(picks_df) == 0:
        raise ValueError("No pick data returned from KTC")

    # Write to partitioned path
    dt = datetime.now(UTC).strftime("%Y-%m-%d")
    dest_dir = f"{out_dir.rstrip('/')}/picks/dt={dt}"
    dest = f"{dest_dir}/picks_{dt}.parquet"

    write_parquet_any(picks_df, dest)

    # Write metadata
    meta = {
        "dataset": "picks",
        "asof_datetime": datetime.now(UTC).isoformat(),
        "loader_path": "src.ingest.ktc.registry.load_picks",
        "source_name": "keeptradecut",
        "source_url": "https://keeptradecut.com/dynasty-rankings",
        "market_scope": market_scope,
        "row_count": len(picks_df),
        "output_parquet": [dest],
    }

    meta_path = f"{dest_dir}/_meta.json"
    import json

    Path(meta_path).parent.mkdir(parents=True, exist_ok=True)
    Path(meta_path).write_text(json.dumps(meta, indent=2))

    return {
        "output_path": dest,
        "meta_path": meta_path,
        "row_count": len(picks_df),
        "metadata": meta,
    }
