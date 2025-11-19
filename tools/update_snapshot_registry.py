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
) -> pl.DataFrame:
    """Merge scanned snapshot metadata into current registry.

    Args:
        current_registry: Current registry DataFrame
        scanned_snapshots: List of scanned snapshot metadata

    Returns:
        Updated registry DataFrame

    """
    if not scanned_snapshots:
        print("No snapshots found to merge")
        return current_registry

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

    # Join with current registry to preserve other columns (status, description)
    # Update strategy: prefer registry values for status/description,
    # scanned values for row_count/coverage
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

    return updated


def print_changes(current: pl.DataFrame, updated: pl.DataFrame) -> None:
    """Print summary of changes that will be made.

    Args:
        current: Current registry
        updated: Updated registry

    """
    changes = []

    for i in range(len(current)):
        curr_row = current.row(i, named=True)
        upd_row = updated.row(i, named=True)

        row_changes = []
        for col in ["row_count", "coverage_start_season", "coverage_end_season"]:
            if curr_row[col] != upd_row[col]:
                row_changes.append(f"{col}: {curr_row[col]} → {upd_row[col]}")

        if row_changes:
            changes.append(
                {
                    "source": curr_row["source"],
                    "dataset": curr_row["dataset"],
                    "snapshot_date": curr_row["snapshot_date"],
                    "changes": ", ".join(row_changes),
                }
            )

    if not changes:
        print("✓ No changes needed - registry is up to date")
        return

    print(f"\n📝 Found {len(changes)} snapshots to update:\n")
    for change in changes:
        source = change["source"]
        dataset = change["dataset"]
        snapshot_date = change["snapshot_date"]
        changes_str = change["changes"]
        print(f"  {source}/{dataset}/dt={snapshot_date}: {changes_str}")


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
    updated_registry = merge_registry_updates(current_registry, scanned)

    # Show changes
    print_changes(current_registry, updated_registry)

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
