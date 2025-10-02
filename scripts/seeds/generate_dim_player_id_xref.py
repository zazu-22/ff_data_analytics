#!/usr/bin/env python3
"""Generate dim_player_id_xref seed from nflverse ff_playerids data.

This script creates the player ID crosswalk seed by:
1. Loading the latest nflverse ff_playerids parquet
2. Filtering out team placeholder entries (those with only mfl_id)
3. Adding player_id as sequential surrogate key
4. Selecting the 27 columns needed for the seed schema
5. Exporting to CSV seed format

The filtering step is critical to prevent join explosions in the parser when
team names (e.g., "Buffalo Bills") match multiple placeholder entries.

Architecture Note:
This is a transitional solution. Ideally, dim_player_id_xref should be a
staging model (stg_nflverse__ff_playerids) that's always fresh from raw data.
For now, this script automates seed regeneration when ff_playerids updates.
"""

from pathlib import Path

import polars as pl


def generate_dim_player_id_xref(
    raw_path: Path,
    output_path: Path,
    verbose: bool = True,
) -> None:
    """Generate dim_player_id_xref seed from raw nflverse data.

    Args:
        raw_path: Path to nflverse ff_playerids parquet file
        output_path: Path to write seed CSV
        verbose: Print diagnostic info
    """
    # Load raw nflverse player IDs
    df = pl.read_parquet(raw_path)

    if verbose:
        print(f"Loaded {df.height:,} rows from {raw_path}")

    # Filter out team placeholder entries
    # These are entries with only mfl_id and no other platform IDs
    # They represent team names (e.g., "Buffalo Bills" DT/OT) used in MFL
    df_filtered = df.filter(
        pl.col("gsis_id").is_not_null()
        | pl.col("sleeper_id").is_not_null()
        | pl.col("espn_id").is_not_null()
        | pl.col("yahoo_id").is_not_null()
        | pl.col("pfr_id").is_not_null()
    )

    if verbose:
        removed = df.height - df_filtered.height
        print(f"Filtered out {removed:,} team placeholder entries")
        print(f"Remaining: {df_filtered.height:,} valid player entries")

    # Add surrogate player_id as sequential key
    df_with_id = df_filtered.with_columns(
        pl.int_range(1, df_filtered.height + 1).alias("player_id")
    )

    # Select columns matching dbt seed schema (27 columns total)
    # Order matches original seed: player_id + 26 nflverse columns
    seed_columns = [
        "player_id",
        "mfl_id",
        "gsis_id",
        "sleeper_id",
        "espn_id",
        "yahoo_id",
        "pfr_id",
        "fantasypros_id",
        "pff_id",
        "cbs_id",
        "ktc_id",
        "sportradar_id",
        "fleaflicker_id",
        "rotowire_id",
        "rotoworld_id",
        "stats_id",
        "stats_global_id",
        "fantasy_data_id",
        "swish_id",
        "cfbref_id",
        "nfl_id",
        "name",
        "merge_name",
        "position",
        "team",
        "birthdate",
        "draft_year",
    ]

    df_final = df_with_id.select(seed_columns)

    # Write to CSV seed
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df_final.write_csv(output_path)

    if verbose:
        print(f"Wrote seed to {output_path}")
        print(f"Final row count: {df_final.height:,}")
        print(f"Columns: {len(df_final.columns)}")


if __name__ == "__main__":
    import sys
    from glob import glob

    # Find latest nflverse ff_playerids parquet
    pattern = "data/raw/nflverse/ff_playerids/dt=*/ff_playerids*.parquet"
    files = sorted(glob(pattern), reverse=True)

    if not files:
        print(f"ERROR: No nflverse ff_playerids files found matching: {pattern}")
        sys.exit(1)

    raw_path = Path(files[0])
    output_path = Path("dbt/ff_analytics/seeds/dim_player_id_xref.csv")

    print(f"Using latest raw data: {raw_path}")
    print()

    generate_dim_player_id_xref(raw_path, output_path, verbose=True)
