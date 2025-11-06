"""Sleeper data loaders following ingest patterns."""

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

import polars as pl

from src.ingest.sleeper.client import SleeperClient


def load_players(
    out_dir: str = "data/raw/sleeper",
    partition_date: str | None = None,
) -> dict:
    """Load all NFL players from Sleeper API.

    This dataset is used for:
    - Player ID crosswalk validation (dim_player_id_xref)
    - Verifying sleeper_id duplicates against authoritative Sleeper data

    Args:
        out_dir: Base output directory
        partition_date: Date partition (YYYY-MM-DD), defaults to today

    Returns:
        dict: Manifest with output_path, row_count, metadata

    """
    client = SleeperClient()

    # Fetch all players
    print("Fetching Sleeper players API (5MB file)...")
    df = client.get_players()

    # Prepare metadata
    asof_date = partition_date or datetime.now(UTC).strftime("%Y-%m-%d")
    output_filename = f"players_{uuid.uuid4().hex[:8]}.parquet"

    # Create output directory
    partition_dir = Path(out_dir) / "players" / f"dt={asof_date}"
    partition_dir.mkdir(parents=True, exist_ok=True)

    # Write parquet
    output_path = partition_dir / output_filename
    df.write_parquet(output_path)

    # Write metadata
    metadata = {
        "dataset": "players",
        "provider": "sleeper",
        "asof_datetime": datetime.now(UTC).isoformat(),
        "asof_date": asof_date,
        "loader_path": "src.ingest.sleeper.loader.load_players",
        "source_name": "Sleeper API",
        "source_url": "https://api.sleeper.app/v1/players/nfl",
        "output_parquet": [output_filename],
        "row_count": len(df),
        "column_count": len(df.columns),
    }

    meta_path = partition_dir / "_meta.json"

    with meta_path.open("w") as f:
        json.dump(metadata, f, indent=2)

    print(f"✅ Wrote {len(df):,} players to {output_path}")
    print(f"   Metadata: {meta_path}")

    return {
        "output_path": str(output_path),
        "metadata_path": str(meta_path),
        "row_count": len(df),
        "partition": asof_date,
    }


def load_fa_pool(
    out_dir: str = "data/raw/sleeper",
    partition_date: str | None = None,
) -> dict:
    """Load free agent pool from Sleeper API.

    Note: This currently calculates FA pool from all players API.
    Future: Could fetch from actual league FA pool endpoint.

    Args:
        out_dir: Base output directory
        partition_date: Date partition (YYYY-MM-DD), defaults to today

    Returns:
        dict: Manifest with output_path, row_count, metadata

    """
    client = SleeperClient()

    # Get all players and filter to FA-relevant positions
    print("Fetching Sleeper players API...")
    df = client.get_players()

    # Filter to fantasy-relevant positions
    # Include all defense/team position variants (DEF, DST, D/ST, TD)
    # Include both K and PK for kickers
    fa_positions = [
        "QB", "RB", "WR", "TE",           # Offense
        "K", "PK",                         # Kickers
        "DEF", "DST", "D/ST", "TD",       # Defense/Special Teams (all variants)
        "DL", "LB", "DB",                  # IDP general
        "S", "CB", "DE", "DT",             # IDP specific
    ]
    df_fa = df.filter(pl.col("position").is_in(fa_positions))

    # Prepare metadata
    asof_date = partition_date or datetime.now(UTC).strftime("%Y-%m-%d")
    output_filename = f"fa_pool_{uuid.uuid4().hex[:8]}.parquet"

    # Create output directory
    partition_dir = Path(out_dir) / "fa_pool" / f"dt={asof_date}"
    partition_dir.mkdir(parents=True, exist_ok=True)

    # Write parquet
    output_path = partition_dir / output_filename
    df_fa.write_parquet(output_path)

    # Write metadata
    metadata = {
        "dataset": "fa_pool",
        "provider": "sleeper",
        "asof_datetime": datetime.now(UTC).isoformat(),
        "asof_date": asof_date,
        "loader_path": "src.ingest.sleeper.loader.load_fa_pool",
        "source_name": "Sleeper API",
        "source_url": "https://api.sleeper.app/v1/players/nfl",
        "output_parquet": [output_filename],
        "row_count": len(df_fa),
        "column_count": len(df_fa.columns),
        "filter_applied": f"position IN {fa_positions}",
    }

    meta_path = partition_dir / "_meta.json"

    with meta_path.open("w") as f:
        json.dump(metadata, f, indent=2)

    print(f"✅ Wrote {len(df_fa):,} FA-eligible players to {output_path}")
    print(f"   Metadata: {meta_path}")

    return {
        "output_path": str(output_path),
        "metadata_path": str(meta_path),
        "row_count": len(df_fa),
        "partition": asof_date,
    }


if __name__ == "__main__":
    import sys

    # Simple CLI for testing
    if len(sys.argv) > 1 and sys.argv[1] == "players":
        result = load_players()
        print(f"\n✅ Success: {result}")
    elif len(sys.argv) > 1 and sys.argv[1] == "fa_pool":
        result = load_fa_pool()
        print(f"\n✅ Success: {result}")
    else:
        print("Usage: python -m src.ingest.sleeper.loader [players|fa_pool]")
        sys.exit(1)
