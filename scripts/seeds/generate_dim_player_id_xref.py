#!/usr/bin/env python3
"""Generate dim_player_id_xref seed from nflverse ff_playerids with duplicate resolution.

This script creates the player ID crosswalk seed by:
1. Loading the latest nflverse ff_playerids parquet
2. Loading the latest Sleeper players data for validation
3. Filtering out team placeholder entries (those with only mfl_id)
4. Resolving sleeper_id duplicates using Sleeper API birthdate matching
5. Resolving gsis_id/mfl_id duplicates by keeping newer players
6. Adding player_id as sequential surrogate key
7. Adding xref_correction_status column for visibility
8. Exporting to CSV seed format

The filtering step is critical to prevent join explosions in the parser when
team names (e.g., "Buffalo Bills") match multiple placeholder entries.

Deduplication Strategy:
- sleeper_id duplicates: Match birthdate with authoritative Sleeper API data
- gsis_id/mfl_id duplicates: Keep player with higher draft_year (newer)
- All corrections tracked in xref_correction_status column

Architecture Note:
This is a transitional solution. Ideally, dim_player_id_xref should be a
staging model (stg_nflverse__ff_playerids) that's always fresh from raw data.
For now, this script automates seed regeneration when ff_playerids updates.
"""

from pathlib import Path

import polars as pl


def load_sleeper_players(data_dir: Path) -> pl.DataFrame:
    """Load latest Sleeper players data for validation.

    Args:
        data_dir: Base data directory (e.g., data/raw)

    Returns:
        DataFrame with sleeper_player_id, birth_date, position

    """
    pattern = f"{data_dir}/sleeper/players/dt=*/players_*.parquet"
    files = sorted(Path().glob(pattern), reverse=True)

    if not files:
        raise FileNotFoundError(
            f"No Sleeper players data found matching: {pattern}\n"
            "Run: make ingest-sleeper-players"
        )

    sleeper_path = files[0]
    print(f"  Using Sleeper players data: {sleeper_path}")

    # Load and filter out team entries (sleeper_player_id should be numeric)
    df_raw = pl.read_parquet(sleeper_path)

    df = df_raw.select([
        pl.col("sleeper_player_id"),
        pl.col("birth_date").alias("sleeper_birth_date"),
        pl.col("position").alias("sleeper_position"),
    ]).filter(
        # Filter out team entries (non-numeric IDs like "HOU", "NE")
        pl.col("sleeper_player_id").str.to_integer(strict=False).is_not_null()
    ).with_columns(
        pl.col("sleeper_player_id").cast(pl.Int64)
    )

    print(f"  Loaded {len(df):,} Sleeper players (filtered out team entries)")
    return df


def deduplicate_sleeper_ids(
    df: pl.DataFrame,
    sleeper_df: pl.DataFrame,
    verbose: bool = True,
) -> pl.DataFrame:
    """Resolve sleeper_id duplicates using Sleeper API birthdate matching.

    Args:
        df: nflverse data with potential sleeper_id duplicates
        sleeper_df: Sleeper API data with authoritative birthdates
        verbose: Print diagnostic info

    Returns:
        DataFrame with sleeper_id duplicates resolved and status column added

    """
    # Add status column (default: original)
    df = df.with_columns(pl.lit("original").alias("xref_correction_status"))

    # Find sleeper_id duplicates
    dup_sleeper_ids = (
        df.filter(pl.col("sleeper_id").is_not_null())
        .group_by("sleeper_id")
        .agg(pl.count().alias("cnt"))
        .filter(pl.col("cnt") > 1)
        .select("sleeper_id")
    )

    if len(dup_sleeper_ids) == 0:
        if verbose:
            print("  ✅ No sleeper_id duplicates found")
        return df

    if verbose:
        print(f"\n  🔍 Found {len(dup_sleeper_ids)} sleeper_ids with duplicates")

    # Join with Sleeper API data
    df_with_sleeper = df.join(
        sleeper_df,
        left_on="sleeper_id",
        right_on="sleeper_player_id",
        how="left",
    )

    # Mark records with incorrect sleeper_id mappings
    df_with_sleeper = df_with_sleeper.with_columns(
        pl.when(
            # In duplicate set AND birthdate doesn't match Sleeper
            pl.col("sleeper_id").is_in(dup_sleeper_ids.to_series())
            & pl.col("sleeper_birth_date").is_not_null()
            & (pl.col("birthdate") != pl.col("sleeper_birth_date"))
        )
        .then(pl.lit("cleared_sleeper_duplicate"))
        .when(
            # In duplicate set AND birthdate DOES match Sleeper (the winner!)
            pl.col("sleeper_id").is_in(dup_sleeper_ids.to_series())
            & pl.col("sleeper_birth_date").is_not_null()
            & (pl.col("birthdate") == pl.col("sleeper_birth_date"))
        )
        .then(pl.lit("kept_sleeper_verified"))
        .otherwise(pl.col("xref_correction_status"))
        .alias("xref_correction_status")
    )

    # NULL out incorrect sleeper_id (but keep the player!)
    df_cleaned = df_with_sleeper.with_columns(
        pl.when(pl.col("xref_correction_status") == "cleared_sleeper_duplicate")
        .then(pl.lit(None))
        .otherwise(pl.col("sleeper_id"))
        .alias("sleeper_id")
    ).drop(["sleeper_birth_date", "sleeper_position"])

    cleared = (df_cleaned["xref_correction_status"] == "cleared_sleeper_duplicate").sum()
    if verbose:
        print(f"  🔧 Cleared {cleared} incorrect sleeper_id mappings (players preserved)")

    return df_cleaned


def deduplicate_provider_ids(
    df: pl.DataFrame,
    id_column: str,
    status_value: str,
    verbose: bool = True,
) -> pl.DataFrame:
    """Resolve provider ID duplicates by keeping newer player (higher draft_year).

    Args:
        df: DataFrame with potential duplicates
        id_column: Column to check for duplicates (gsis_id, mfl_id)
        status_value: Status to assign to removed records
        verbose: Print diagnostic info

    Returns:
        DataFrame with duplicates resolved

    """
    # Find duplicates
    dup_ids = (
        df.filter(pl.col(id_column).is_not_null())
        .group_by(id_column)
        .agg(pl.count().alias("cnt"))
        .filter(pl.col("cnt") > 1)
        .select(id_column)
    )

    if len(dup_ids) == 0:
        if verbose:
            print(f"  ✅ No {id_column} duplicates found")
        return df

    if verbose:
        print(f"\n  🔍 Found {len(dup_ids)} {id_column}s with duplicates")

    # For each duplicate ID, keep the one with highest draft_year
    # (nulls sort last, so draft_year=0 or null will be removed)
    df_with_rank = df.with_columns(
        pl.when(pl.col(id_column).is_in(dup_ids.to_series()))
        .then(
            pl.col("draft_year")
            .rank(method="dense", descending=True)
            .over(id_column)
        )
        .otherwise(pl.lit(1))
        .alias("_rank")
    )

    # Mark all records in duplicate sets (both kept and cleared)
    cleared_status = status_value.replace("removed", "cleared")
    kept_status = status_value.replace("removed", "kept").replace("duplicate", "newer")

    df_with_rank = df_with_rank.with_columns(
        pl.when(
            # In duplicate set AND rank > 1 (older player - clear the ID)
            pl.col(id_column).is_in(dup_ids.to_series()) & (pl.col("_rank") > 1)
        )
        .then(pl.lit(cleared_status))
        .when(
            # In duplicate set AND rank == 1 (newer player - keep the ID)
            pl.col(id_column).is_in(dup_ids.to_series()) & (pl.col("_rank") == 1)
        )
        .then(pl.lit(kept_status))
        .otherwise(pl.col("xref_correction_status"))
        .alias("xref_correction_status")
    )

    # NULL out the provider ID for older players (but keep the player!)
    df_cleaned = df_with_rank.with_columns(
        pl.when(pl.col("xref_correction_status") == cleared_status)
        .then(pl.lit(None))
        .otherwise(pl.col(id_column))
        .alias(id_column)
    ).drop("_rank")

    cleared = (df_cleaned["xref_correction_status"] == cleared_status).sum()
    if verbose:
        print(f"  🔧 Cleared {cleared} incorrect {id_column} mappings (players preserved)")

    return df_cleaned


def generate_dim_player_id_xref(
    nflverse_path: Path,
    sleeper_data_dir: Path,
    output_path: Path,
    verbose: bool = True,
) -> None:
    """Generate dim_player_id_xref seed from raw nflverse data with deduplication.

    Args:
        nflverse_path: Path to nflverse ff_playerids parquet file
        sleeper_data_dir: Path to data/raw directory (for Sleeper data)
        output_path: Path to write seed CSV
        verbose: Print diagnostic info

    """
    print("=" * 70)
    print("STEP 1: Load raw data")
    print("=" * 70)

    # Load raw nflverse player IDs
    raw_df = pl.read_parquet(nflverse_path)
    if verbose:
        print(f"  Loaded {raw_df.height:,} rows from {nflverse_path}")

    # Load Sleeper players for validation
    sleeper_df = load_sleeper_players(sleeper_data_dir)

    print("\n" + "=" * 70)
    print("STEP 2: Filter team placeholders")
    print("=" * 70)

    # Filter out team placeholder entries
    df_filtered = raw_df.filter(
        pl.col("gsis_id").is_not_null()
        | pl.col("sleeper_id").is_not_null()
        | pl.col("espn_id").is_not_null()
        | pl.col("yahoo_id").is_not_null()
        | pl.col("pfr_id").is_not_null()
    )

    if verbose:
        removed = raw_df.height - df_filtered.height
        print(f"  ❌ Removed {removed:,} team placeholder entries")
        print(f"  ✅ Remaining: {df_filtered.height:,} valid player entries")

    print("\n" + "=" * 70)
    print("STEP 3: Deduplicate provider IDs")
    print("=" * 70)

    # Deduplicate sleeper_id (using Sleeper API)
    print("\n[sleeper_id]")
    df_deduped = deduplicate_sleeper_ids(df_filtered, sleeper_df, verbose=verbose)

    # Deduplicate gsis_id (using draft_year)
    print("\n[gsis_id]")
    df_deduped = deduplicate_provider_ids(
        df_deduped,
        "gsis_id",
        "removed_gsis_duplicate",
        verbose=verbose,
    )

    # Deduplicate mfl_id (using draft_year)
    print("\n[mfl_id]")
    df_deduped = deduplicate_provider_ids(
        df_deduped,
        "mfl_id",
        "removed_mfl_duplicate",
        verbose=verbose,
    )

    print("\n" + "=" * 70)
    print("STEP 4: Add player_id and name variants")
    print("=" * 70)

    # Add surrogate player_id as sequential key
    df_with_id = df_deduped.with_columns(
        pl.int_range(1, df_deduped.height + 1).alias("player_id")
    )

    # Add "Last, First" name variant for matching with FantasySharks projections
    df_with_id = df_with_id.with_columns(
        pl.when(pl.col("name").str.contains(" "))
        .then(
            pl.col("name").str.splitn(" ", 2).struct.field("field_1")
            + pl.lit(", ")
            + pl.col("name").str.splitn(" ", 2).struct.field("field_0")
        )
        .otherwise(pl.col("name"))
        .alias("name_last_first")
    )

    if verbose:
        print(f"  ✅ Assigned player_id 1 to {df_with_id.height:,}")

    print("\n" + "=" * 70)
    print("STEP 5: Select final columns and export")
    print("=" * 70)

    # Select columns matching dbt seed schema (29 columns total now: 28 + status)
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
        "name_last_first",
        "position",
        "team",
        "birthdate",
        "draft_year",
        "xref_correction_status",  # NEW: visibility into corrections
    ]

    df_final = df_with_id.select(seed_columns)

    # Print correction summary
    correction_summary = (
        df_final.group_by("xref_correction_status")
        .agg(pl.count().alias("count"))
        .sort("count", descending=True)
    )

    print("\n  Correction Status Summary:")
    for row in correction_summary.iter_rows(named=True):
        print(f"    {row['xref_correction_status']:30} {row['count']:>6,} records")

    # Write to CSV seed
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df_final.write_csv(output_path)

    print(f"\n  ✅ Wrote seed to {output_path}")
    print(f"  📊 Final row count: {df_final.height:,}")
    print(f"  📋 Columns: {len(df_final.columns)}")
    print("\n" + "=" * 70)


if __name__ == "__main__":
    import sys

    # Find latest nflverse ff_playerids parquet
    nflverse_pattern = "data/raw/nflverse/ff_playerids/dt=*/ff_playerids*.parquet"
    nflverse_files = sorted(Path().glob(nflverse_pattern), reverse=True)

    if not nflverse_files:
        print(f"ERROR: No nflverse ff_playerids files found matching: {nflverse_pattern}")
        sys.exit(1)

    nflverse_path = nflverse_files[0]
    sleeper_data_dir = Path("data/raw")
    output_path = Path("dbt/ff_analytics/seeds/dim_player_id_xref.csv")

    print(f"Using nflverse data: {nflverse_path}")
    print()

    try:
        generate_dim_player_id_xref(
            nflverse_path,
            sleeper_data_dir,
            output_path,
            verbose=True,
        )
        print("\n✅ SUCCESS: Seed generated with duplicate resolution")
    except FileNotFoundError as e:
        print(f"\n❌ ERROR: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
