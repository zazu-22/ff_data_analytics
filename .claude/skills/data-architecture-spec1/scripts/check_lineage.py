#!/usr/bin/env python3
"""Check metadata lineage for raw data partitions.

Validates that _meta.json files exist and contain required fields for data quality tracking.
"""

import argparse
import json
import sys
from pathlib import Path

REQUIRED_FIELDS = {
    "loader_path",
    "source_version",
    "asof_datetime",
    "row_count",
    "schema_hash",
    "dataset_name",
    "partition_date",
}


def check_lineage(partition_path: Path) -> tuple[bool, list[str]]:
    """Check metadata lineage for a single partition.

    Args:
        partition_path: Path to partition directory (e.g., data/raw/nflverse/players/dt=2025-10-24)

    Returns:
        (success: bool, errors: list[str])

    """
    errors = []

    # Check partition exists
    if not partition_path.exists():
        errors.append(f"Partition path does not exist: {partition_path}")
        return False, errors

    if not partition_path.is_dir():
        errors.append(f"Partition path is not a directory: {partition_path}")
        return False, errors

    # Check for _meta.json
    meta_path = partition_path / "_meta.json"
    if not meta_path.exists():
        errors.append(f"Missing _meta.json in partition: {partition_path}")
        return False, errors

    # Parse metadata
    try:
        with meta_path.open() as f:
            metadata = json.load(f)
    except json.JSONDecodeError as e:
        errors.append(f"Invalid JSON in {meta_path}: {e}")
        return False, errors

    # Check required fields
    missing_fields = REQUIRED_FIELDS - set(metadata.keys())
    if missing_fields:
        errors.append(f"Missing required fields in {meta_path}: {sorted(missing_fields)}")

    # Validate field values
    if "row_count" in metadata and not isinstance(metadata["row_count"], int):
        errors.append(f"row_count must be integer, got: {type(metadata['row_count']).__name__}")

    if "row_count" in metadata and metadata["row_count"] < 0:
        errors.append(f"row_count must be non-negative, got: {metadata['row_count']}")

    # Check for Parquet files
    parquet_files = list(partition_path.glob("*.parquet"))
    if not parquet_files:
        errors.append(f"No Parquet files found in partition: {partition_path}")

    success = len(errors) == 0
    return success, errors


def main():
    """CLI entry point for checking metadata lineage."""
    parser = argparse.ArgumentParser(
        description="Check metadata lineage for raw data partitions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check single partition
  python check_lineage.py --path data/raw/nflverse/players/dt=2025-10-24

  # Check with verbose output
  python check_lineage.py --path data/raw/nflverse/players/dt=2025-10-24 --verbose
        """,
    )
    parser.add_argument(
        "--path",
        type=Path,
        required=True,
        help="Path to partition directory (e.g., data/raw/nflverse/players/dt=2025-10-24)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed output",
    )

    args = parser.parse_args()

    print(f"Checking lineage for: {args.path}")
    success, errors = check_lineage(args.path)

    if success:
        print("✅ Lineage check passed")
        if args.verbose:
            meta_path = args.path / "_meta.json"
            with meta_path.open() as f:
                metadata = json.load(f)
            print("\nMetadata:")
            for key in sorted(metadata.keys()):
                print(f"  {key}: {metadata[key]}")
        sys.exit(0)
    else:
        print("❌ Lineage check failed")
        print("\nErrors:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
