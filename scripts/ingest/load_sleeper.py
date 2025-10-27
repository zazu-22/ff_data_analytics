"""Sleeper production loader.

Usage:
    python scripts/ingest/load_sleeper.py --league-id 1230330435511275520 --out data/raw/sleeper
    python scripts/ingest/load_sleeper.py --league-id $SLEEPER_LEAGUE_ID --out gs://ff-analytics/raw/sleeper

Outputs:
    - data/raw/sleeper/rosters/dt=YYYY-MM-DD/rosters.parquet
    - data/raw/sleeper/players/dt=YYYY-MM-DD/players.parquet
    - data/raw/sleeper/fa_pool/dt=YYYY-MM-DD/fa_pool.parquet
    - data/raw/sleeper/users/dt=YYYY-MM-DD/users.parquet
"""

import argparse
import json
import sys
import uuid
from datetime import datetime
from pathlib import Path

import polars as pl

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.ingest.common.storage import write_parquet_any, write_text_sidecar
from src.ingest.sleeper.client import SleeperClient


def _write_dataset(
    df: pl.DataFrame, dataset_name: str, out_dir: str, dt: str, metadata: dict
) -> dict:
    """Write dataset to parquet with metadata sidecar.

    Args:
        df: DataFrame to write
        dataset_name: Dataset name (rosters, players, fa_pool, users)
        out_dir: Base output directory
        dt: Date partition value (YYYY-MM-DD)
        metadata: Metadata dict for sidecar

    Returns:
        Dict with rows, path, and metadata

    """
    # Build partition directory
    base = out_dir.rstrip("/")
    partition_dir = f"{base}/{dataset_name}/dt={dt}"

    # Write parquet file
    file_name = f"{dataset_name}_{uuid.uuid4().hex[:8]}.parquet"
    parquet_uri = f"{partition_dir}/{file_name}"
    write_parquet_any(df, parquet_uri)

    # Write metadata sidecar
    meta = {
        "dataset": dataset_name,
        "asof_datetime": datetime.now().isoformat(),
        "loader_path": "scripts.ingest.load_sleeper",
        "source_name": "sleeper",
        "output_parquet": parquet_uri,
        "row_count": len(df),
        **metadata,
    }
    write_text_sidecar(json.dumps(meta, indent=2), f"{partition_dir}/_meta.json")

    return {"rows": len(df), "path": parquet_uri, "meta": meta}


def load_sleeper(league_id: str, out_dir: str) -> dict:
    """Load Sleeper data: rosters, players, FA pool.

    Args:
        league_id: Sleeper league ID
        out_dir: Output directory (local or GCS)

    Returns:
        Manifest dict with row counts and paths

    """
    client = SleeperClient()
    dt = datetime.now().strftime("%Y-%m-%d")

    manifest = {"loaded_at": datetime.now().isoformat(), "league_id": league_id, "datasets": {}}

    # 1. Load rosters
    print(f"Loading rosters for league {league_id}...")
    rosters_df = client.get_rosters(league_id)
    manifest["datasets"]["rosters"] = _write_dataset(
        rosters_df, "rosters", out_dir, dt, {"league_id": league_id}
    )
    print(f"✅ Loaded {len(rosters_df)} rosters")

    # 2. Load all players
    print("Loading all NFL players...")
    players_df = client.get_players()
    manifest["datasets"]["players"] = _write_dataset(
        players_df, "players", out_dir, dt, {"note": "Full NFL player database (5MB)"}
    )
    print(f"✅ Loaded {len(players_df)} players")

    # 3. Calculate FA pool
    print("Calculating FA pool...")
    # Extract all rostered player IDs from nested lists
    rostered_player_ids = set()
    for row in rosters_df.iter_rows(named=True):
        players_list = row.get("players")
        if players_list is not None:
            rostered_player_ids.update(players_list)

    # FA pool = All active NFL players NOT on any roster
    fa_pool_df = players_df.filter(
        ~pl.col("sleeper_player_id").is_in(list(rostered_player_ids))
    ).filter(
        # Only active NFL players (exclude retired, practice squad if desired)
        pl.col("status").is_in(
            ["Active", "Injured Reserve", "Questionable", "Doubtful", "Out", "PUP"]
        )
    )

    manifest["datasets"]["fa_pool"] = _write_dataset(
        fa_pool_df,
        "fa_pool",
        out_dir,
        dt,
        {
            "note": "Calculated as: all_players - rostered_players",
            "rostered_count": len(rostered_player_ids),
            "fa_count": len(fa_pool_df),
        },
    )
    print(
        f"✅ Calculated FA pool: {len(fa_pool_df)} players available ({len(rostered_player_ids)} rostered)"
    )

    # 4. Load users
    print(f"Loading league users for league {league_id}...")
    users_df = client.get_league_users(league_id)
    manifest["datasets"]["users"] = _write_dataset(
        users_df, "users", out_dir, dt, {"league_id": league_id}
    )
    print(f"✅ Loaded {len(users_df)} users")

    return manifest


def main():
    parser = argparse.ArgumentParser(
        description="Load Sleeper league data (rosters, players, FA pool)"
    )
    parser.add_argument("--league-id", required=True, help="Sleeper league ID")
    parser.add_argument(
        "--out", default="data/raw/sleeper", help="Output directory (default: data/raw/sleeper)"
    )
    args = parser.parse_args()

    print("Starting Sleeper data load...")
    print(f"League ID: {args.league_id}")
    print(f"Output dir: {args.out}")
    print()

    manifest = load_sleeper(args.league_id, args.out)

    print()
    print("=" * 60)
    print("Sleeper data load complete!")
    print("=" * 60)
    print(f"Datasets loaded: {len(manifest['datasets'])}")
    for dataset, info in manifest["datasets"].items():
        print(f"  - {dataset}: {info['rows']} rows → {info['path']}")


if __name__ == "__main__":
    main()
