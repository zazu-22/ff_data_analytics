"""tools/update_snapshot_registry.py.

Maintenance script to synchronize snapshot registry with actual data files.

WHAT THIS IS:
    Scans data/raw/ for parquet snapshots and updates snapshot_registry.csv with
    accurate row counts and metadata. This ensures the registry catalog matches
    actual data on disk.

WHEN TO USE:
    - After manual data ingestion (before Prefect automation)
    - When registry row_count column is missing/stale
    - To fix registry drift or data quality issues
    - One-time fix for missing metadata

WHEN NOT TO USE:
    - After Phase 4 orchestration is implemented (Prefect flows maintain registry)
    - For routine operations (should be automated)
    - If you're just reading data (registry updates are for writers)

DEPRECATION:
    This script will be DEPRECATED after Phase 4 (Prefect orchestration) is complete.
    Registry updates should be atomic with data writes in production flows.
    See: docs/implementation/multi_source_snapshot_governance/tickets/P4-*.md

Usage:
    # Update all sources
    python tools/update_snapshot_registry.py

    # Update specific source
    python tools/update_snapshot_registry.py --source nflverse

    # Dry run (show what would change)
    python tools/update_snapshot_registry.py --dry-run

    # Update specific datasets only
    python tools/update_snapshot_registry.py --source nflverse --datasets weekly snap_counts
"""

import argparse
import sys
from pathlib import Path

import polars as pl


def _extract_coverage_metadata(df: pl.DataFrame) -> tuple[int | None, int | None]:
    """Extract season coverage metadata from a DataFrame.

    Args:
        df: Polars DataFrame to extract metadata from

    Returns:
        Tuple of (coverage_start_season, coverage_end_season)

    """
    if "season" not in df.columns:
        return None, None

    seasons = df["season"].unique().sort()
    if len(seasons) == 0:
        return None, None

    return int(seasons.min()), int(seasons.max())


def _process_dt_partition(source: str, dataset: str, dt_dir: Path) -> dict | None:
    """Process a single dt=* partition and extract metadata.

    Args:
        source: Data source name
        dataset: Dataset name
        dt_dir: Path to dt=* directory

    Returns:
        Snapshot metadata dictionary or None if processing failed

    """
    dt = dt_dir.name.replace("dt=", "")
    parquet_files = list(dt_dir.glob("*.parquet"))

    if not parquet_files:
        print(f"Warning: No parquet files in {dt_dir}, skipping")
        return None

    try:
        df = pl.read_parquet(parquet_files[0])
        coverage_start, coverage_end = _extract_coverage_metadata(df)

        return {
            "source": source,
            "dataset": dataset,
            "snapshot_date": dt,
            "row_count": len(df),
            "coverage_start_season": coverage_start,
            "coverage_end_season": coverage_end,
            "file_path": str(parquet_files[0]),
            "file_count": len(parquet_files),
        }
    except Exception as e:
        print(f"Error reading {parquet_files[0]}: {e}")
        return None


def _process_dataset_dir(
    source: str,
    dataset_dir: Path,
    datasets_filter: list[str] | None,
) -> list[dict]:
    """Process a single dataset directory and extract all partition metadata.

    Args:
        source: Data source name
        dataset_dir: Path to dataset directory
        datasets_filter: Optional list of dataset names to include

    Returns:
        List of snapshot metadata dictionaries

    """
    dataset = dataset_dir.name

    # Apply dataset filter
    if datasets_filter and dataset not in datasets_filter:
        return []

    # Find all dt=* partitions
    dt_dirs = sorted(dataset_dir.glob("dt=*"))
    snapshots = []

    for dt_dir in dt_dirs:
        snapshot = _process_dt_partition(source, dataset, dt_dir)
        if snapshot:
            snapshots.append(snapshot)

    return snapshots


def scan_snapshots(
    base_dir: Path, source_name: str | None = None, datasets_filter: list[str] | None = None
) -> list[dict]:
    """Scan data/raw for all snapshots and extract metadata.

    Args:
        base_dir: Base directory (data/raw)
        source_name: Optional source filter (e.g., 'nflverse')
        datasets_filter: Optional dataset filter (e.g., ['weekly', 'snap_counts'])

    Returns:
        List of snapshot metadata dictionaries

    """
    # Find all sources
    if source_name:
        sources = [base_dir / source_name]
    else:
        sources = [d for d in base_dir.iterdir() if d.is_dir() and not d.name.startswith("_")]

    snapshots = []
    for source_dir in sorted(sources):
        if not source_dir.exists():
            print(f"Warning: Source {source_dir.name} not found, skipping")
            continue

        source = source_dir.name

        # Find all datasets in this source
        datasets = [d for d in source_dir.iterdir() if d.is_dir() and not d.name.startswith("_")]

        for dataset_dir in sorted(datasets):
            dataset_snapshots = _process_dataset_dir(source, dataset_dir, datasets_filter)
            snapshots.extend(dataset_snapshots)

    return snapshots


def load_current_registry(registry_path: Path) -> pl.DataFrame:
    """Load the current snapshot registry CSV.

    Args:
        registry_path: Path to snapshot_registry.csv

    Returns:
        Polars DataFrame with current registry

    """
    if not registry_path.exists():
        raise FileNotFoundError(f"Registry not found: {registry_path}")

    return pl.read_csv(registry_path)


def merge_registry_updates(
    current_registry: pl.DataFrame, scanned_snapshots: list[dict]
) -> tuple[pl.DataFrame, list[dict]]:
    """Merge scanned snapshot metadata into current registry.

    Updates existing entries and adds new snapshots not in registry.

    Args:
        current_registry: Current registry DataFrame
        scanned_snapshots: List of scanned snapshot metadata

    Returns:
        Tuple of (updated registry DataFrame, list of new snapshots added)

    """
    if not scanned_snapshots:
        print("No snapshots found to merge")
        return current_registry, []

    # Convert scanned snapshots to DataFrame
    scanned_df = pl.DataFrame(scanned_snapshots).select(
        [
            "source",
            "dataset",
            "snapshot_date",
            "row_count",
            "coverage_start_season",
            "coverage_end_season",
        ]
    )

    # Step 1: Update existing entries (left join on registry)
    updated = (
        current_registry.join(
            scanned_df,
            on=["source", "dataset", "snapshot_date"],
            how="left",
            suffix="_scanned",
        )
        .with_columns(
            [
                # Use scanned row_count if available, otherwise keep existing
                pl.when(pl.col("row_count_scanned").is_not_null())
                .then(pl.col("row_count_scanned"))
                .otherwise(pl.col("row_count"))
                .alias("row_count"),
                # Use scanned coverage if available, otherwise keep existing
                pl.when(pl.col("coverage_start_season_scanned").is_not_null())
                .then(pl.col("coverage_start_season_scanned"))
                .otherwise(pl.col("coverage_start_season"))
                .alias("coverage_start_season"),
                pl.when(pl.col("coverage_end_season_scanned").is_not_null())
                .then(pl.col("coverage_end_season_scanned"))
                .otherwise(pl.col("coverage_end_season"))
                .alias("coverage_end_season"),
            ]
        )
        .select(current_registry.columns)  # Keep only original columns
    )

    # Step 2: Find new snapshots not in registry (anti-join)
    existing_keys = current_registry.select(["source", "dataset", "snapshot_date"])
    new_snapshots_df = scanned_df.join(
        existing_keys,
        on=["source", "dataset", "snapshot_date"],
        how="anti",
    )

    new_snapshots_list = []
    if len(new_snapshots_df) > 0:
        # Step 3: Mark old "current" snapshots as "superseded" for datasets getting new entries
        # Get unique source/dataset pairs that have new snapshots
        new_pairs = new_snapshots_df.select(["source", "dataset"]).unique()

        # For each source/dataset with new data, mark existing "current" as "superseded"
        # Use a left join to identify which rows need status update
        updated = (
            updated.join(
                new_pairs.with_columns(pl.lit(True).alias("_has_new")),
                on=["source", "dataset"],
                how="left",
            )
            .with_columns(
                pl.when(
                    (pl.col("status") == "current") & (pl.col("_has_new") == True)  # noqa: E712
                )
                .then(pl.lit("superseded"))
                .otherwise(pl.col("status"))
                .alias("status")
            )
            .drop("_has_new")
        )

        # Add new entries as "current"
        new_entries = new_snapshots_df.with_columns(
            [
                pl.lit("current").alias("status"),
                pl.lit("Auto-added by update_snapshot_registry").alias("notes"),
            ]
        ).select(current_registry.columns)

        # Concatenate new entries
        updated = pl.concat([updated, new_entries])
        new_snapshots_list = new_snapshots_df.to_dicts()

    return updated, new_snapshots_list


def _detect_row_changes(
    current: pl.DataFrame, updated: pl.DataFrame
) -> tuple[list[dict], list[dict]]:
    """Detect metadata and status changes between registry versions.

    Returns:
        Tuple of (metadata_changes, status_changes)

    """
    metadata_changes = []
    status_changes = []

    for i in range(len(current)):
        curr_row = current.row(i, named=True)
        upd_row = updated.row(i, named=True)

        # Check metadata changes
        row_changes = []
        for col in ["row_count", "coverage_start_season", "coverage_end_season"]:
            if curr_row[col] != upd_row[col]:
                row_changes.append(f"{col}: {curr_row[col]} → {upd_row[col]}")

        if row_changes:
            metadata_changes.append(
                {
                    "source": curr_row["source"],
                    "dataset": curr_row["dataset"],
                    "snapshot_date": curr_row["snapshot_date"],
                    "changes": ", ".join(row_changes),
                }
            )

        # Check status changes
        if curr_row["status"] != upd_row["status"]:
            status_changes.append(
                {
                    "source": curr_row["source"],
                    "dataset": curr_row["dataset"],
                    "snapshot_date": curr_row["snapshot_date"],
                    "old_status": curr_row["status"],
                    "new_status": upd_row["status"],
                }
            )

    return metadata_changes, status_changes


def print_changes(current: pl.DataFrame, updated: pl.DataFrame, new_snapshots: list[dict]) -> None:
    """Print summary of changes that will be made."""
    metadata_changes, status_changes = _detect_row_changes(current, updated)

    if not metadata_changes and not status_changes and not new_snapshots:
        print("✓ No changes needed - registry is up to date")
        return

    if metadata_changes:
        print(f"\n📝 Found {len(metadata_changes)} snapshots to update:\n")
        for c in metadata_changes:
            print(f"  {c['source']}/{c['dataset']}/dt={c['snapshot_date']}: {c['changes']}")

    if status_changes:
        print(f"\n🔄 Found {len(status_changes)} status changes:\n")
        for c in status_changes:
            key = f"{c['source']}/{c['dataset']}/dt={c['snapshot_date']}"
            print(f"  {key}: {c['old_status']} → {c['new_status']}")

    if new_snapshots:
        print(f"\n🆕 Found {len(new_snapshots)} NEW snapshots to add:\n")
        for snap in new_snapshots:
            key = f"{snap['source']}/{snap['dataset']}/dt={snap['snapshot_date']}"
            row_count = snap.get("row_count", "?")
            print(f"  {key} ({row_count} rows)")


def main():
    """Update snapshot registry with metadata from actual data files."""
    parser = argparse.ArgumentParser(
        description="Update snapshot registry with actual file metadata",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Update all sources
  python tools/update_snapshot_registry.py

  # Update specific source
  python tools/update_snapshot_registry.py --source nflverse

  # Dry run (show changes without applying)
  python tools/update_snapshot_registry.py --dry-run

  # Update specific datasets
  python tools/update_snapshot_registry.py --source nflverse --datasets weekly snap_counts

IMPORTANT:
  This script is a TEMPORARY maintenance tool for use before Phase 4 orchestration.
  After Prefect flows are implemented, registry updates should be automatic.
  See: docs/implementation/multi_source_snapshot_governance/
        """,
    )

    parser.add_argument(
        "--base-dir",
        type=Path,
        default=Path("data/raw"),
        help="Base directory containing raw data (default: data/raw)",
    )

    parser.add_argument(
        "--registry-path",
        type=Path,
        default=Path("dbt/ff_data_transform/seeds/snapshot_registry.csv"),
        help=(
            "Path to snapshot registry CSV "
            "(default: dbt/ff_data_transform/seeds/snapshot_registry.csv)"
        ),
    )

    parser.add_argument(
        "--source",
        type=str,
        help="Update specific source only (e.g., nflverse)",
    )

    parser.add_argument(
        "--datasets",
        nargs="*",
        help="Update specific datasets only (e.g., weekly snap_counts)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without actually updating the file",
    )

    args = parser.parse_args()

    # Validate paths
    if not args.base_dir.exists():
        print(f"Error: Base directory not found: {args.base_dir}")
        sys.exit(1)

    if not args.registry_path.exists():
        print(f"Error: Registry not found: {args.registry_path}")
        sys.exit(1)

    print("🔍 Scanning snapshots in data/raw/...")

    # Scan for snapshots
    scanned = scan_snapshots(args.base_dir, args.source, args.datasets)

    if not scanned:
        print("No snapshots found to update")
        sys.exit(0)

    print(f"Found {len(scanned)} snapshots")

    # Load current registry
    print("\n📖 Loading current registry...")
    current_registry = load_current_registry(args.registry_path)

    # Merge updates
    print("🔄 Merging updates...")
    updated_registry, new_snapshots = merge_registry_updates(current_registry, scanned)

    # Show changes
    print_changes(current_registry, updated_registry, new_snapshots)

    # Apply changes
    if args.dry_run:
        print("\n🔎 DRY RUN - No changes applied")
        print(f"Run without --dry-run to update {args.registry_path}")
    else:
        # Write updated registry
        updated_registry.write_csv(args.registry_path)
        print(f"\n✅ Registry updated: {args.registry_path}")
        print("Run 'just dbt-seed' to reload the registry into dbt")


if __name__ == "__main__":
    main()
