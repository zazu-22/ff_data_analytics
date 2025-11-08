#!/usr/bin/env python3
"""Validate schema compliance for staging models and fact tables.

Supports multiple validation checks:
- metadata: Validate _meta.json presence and format
- schema_consistency: Check schema consistency across partitions
- player_id_mapping: Validate ID crosswalk coverage
"""

import argparse
import json
import sys
from pathlib import Path

import polars as pl
import pyarrow.parquet as pq


def check_metadata(path: Path) -> tuple[bool, list[str]]:
    """Check metadata presence and consistency across partitions."""
    errors = []

    partitions = sorted([p for p in path.glob("dt=*") if p.is_dir()])
    if not partitions:
        errors.append(f"No partitions found in: {path}")
        return False, errors

    schema_hashes = set()
    for partition in partitions:
        meta_path = partition / "_meta.json"
        if not meta_path.exists():
            errors.append(f"Missing _meta.json in: {partition}")
            continue

        try:
            with meta_path.open() as f:
                metadata = json.load(f)
            if "schema_hash" in metadata:
                schema_hashes.add(metadata["schema_hash"])
        except Exception as e:
            errors.append(f"Error reading {meta_path}: {e}")

    if len(schema_hashes) > 1:
        errors.append(f"Inconsistent schema_hash across partitions: {schema_hashes}")

    success = len(errors) == 0
    return success, errors


def check_schema_consistency(path: Path) -> tuple[bool, list[str]]:
    """Check Parquet schema consistency across partitions."""
    errors = []

    partitions = sorted([p for p in path.glob("dt=*") if p.is_dir()])
    if not partitions:
        errors.append(f"No partitions found in: {path}")
        return False, errors

    schemas = {}
    for partition in partitions:
        parquet_files = list(partition.glob("*.parquet"))
        if not parquet_files:
            errors.append(f"No Parquet files in: {partition}")
            continue

        # Read schema from first file
        parquet_file = parquet_files[0]
        try:
            schema = pq.read_schema(parquet_file)
            schemas[partition.name] = schema
        except Exception as e:
            errors.append(f"Error reading schema from {parquet_file}: {e}")

    # Compare schemas
    if len(schemas) > 1:
        first_partition, first_schema = next(iter(schemas.items()))
        for partition_name, schema in list(schemas.items())[1:]:
            if schema != first_schema:
                errors.append(f"Schema mismatch between {first_partition} and {partition_name}")

    success = len(errors) == 0
    return success, errors


def _load_id_column_from_partitions(path: Path, id_field: str) -> tuple[list, list[str]]:
    """Load ID column from all partitions.

    Returns:
        (dataframes: list, errors: list[str])

    """
    errors = []
    dfs = []
    partitions = sorted([p for p in path.glob("dt=*") if p.is_dir()])

    for partition in partitions:
        parquet_files = list(partition.glob("*.parquet"))
        if parquet_files:
            try:
                df = pl.read_parquet(parquet_files[0])
                if id_field in df.columns:
                    dfs.append(df.select([id_field]))
            except Exception as e:
                errors.append(f"Error reading {parquet_files[0]}: {e}")

    return dfs, errors


def check_player_id_mapping(path: Path, id_field: str = "gsis_id") -> tuple[bool, list[str], dict]:
    """Validate player ID crosswalk coverage.

    Args:
        path: Path to raw data directory (e.g., data/raw/nflverse/weekly)
        id_field: Provider ID field to check (e.g., 'gsis_id', 'sleeper_id')

    Returns:
        (success: bool, errors: list[str], stats: dict)

    """
    errors = []
    stats = {}

    # Load crosswalk
    crosswalk_path = Path("dbt/ff_data_transform/seeds/dim_player_id_xref.csv")
    if not crosswalk_path.exists():
        errors.append(f"Crosswalk not found: {crosswalk_path}")
        return False, errors, stats

    try:
        crosswalk = pl.read_csv(crosswalk_path)
    except Exception as e:
        errors.append(f"Error reading crosswalk: {e}")
        return False, errors, stats

    # Load data from all partitions
    dfs, load_errors = _load_id_column_from_partitions(path, id_field)
    errors.extend(load_errors)

    if not dfs:
        errors.append(f"No data found with {id_field} column")
        return False, errors, stats

    # Combine and analyze
    combined = pl.concat(dfs)
    total_records = len(combined)
    unique_ids = combined.select(pl.col(id_field)).unique()
    total_unique_ids = len(unique_ids)

    # Count mapped IDs
    if id_field in crosswalk.columns:
        mapped = unique_ids.join(
            crosswalk.select([id_field, "player_id"]), on=id_field, how="inner"
        )
        mapped_count = len(mapped)
        coverage_pct = (mapped_count / total_unique_ids * 100) if total_unique_ids > 0 else 0

        stats = {
            "total_records": total_records,
            "total_unique_ids": total_unique_ids,
            "mapped_count": mapped_count,
            "unmapped_count": total_unique_ids - mapped_count,
            "coverage_pct": coverage_pct,
        }

        # Check coverage threshold
        if coverage_pct < 90:
            errors.append(
                f"Low mapping coverage: {coverage_pct:.1f}% ({mapped_count} / {total_unique_ids})"
            )
    else:
        errors.append(f"ID field '{id_field}' not found in crosswalk")
        return False, errors, stats

    success = len(errors) == 0
    return success, errors, stats


def main():
    """CLI entry point for schema validation."""
    parser = argparse.ArgumentParser(
        description="Validate schema compliance for data models",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check metadata consistency
  python validate_schema.py --path data/raw/nflverse/players --check metadata

  # Check schema consistency across partitions
  python validate_schema.py --path data/raw/nflverse/weekly --check schema_consistency

  # Check player ID mapping coverage
  python validate_schema.py --path data/raw/nflverse/weekly \\
      --check player_id_mapping --id-field gsis_id
        """,
    )
    parser.add_argument(
        "--path",
        type=Path,
        required=True,
        help="Path to data directory (e.g., data/raw/nflverse/players)",
    )
    parser.add_argument(
        "--check",
        choices=["metadata", "schema_consistency", "player_id_mapping"],
        required=True,
        help="Type of validation check to perform",
    )
    parser.add_argument(
        "--id-field",
        default="gsis_id",
        help="Provider ID field for player_id_mapping check (default: gsis_id)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed output",
    )

    args = parser.parse_args()

    print(f"Running {args.check} validation for: {args.path}")

    stats = {}
    if args.check == "metadata":
        success, errors = check_metadata(args.path)
    elif args.check == "schema_consistency":
        success, errors = check_schema_consistency(args.path)
    elif args.check == "player_id_mapping":
        success, errors, stats = check_player_id_mapping(args.path, args.id_field)
    else:
        print(f"Unknown check type: {args.check}")
        sys.exit(1)

    if success:
        print("✅ Validation passed")
        if args.check == "player_id_mapping":
            print("\nMapping Statistics:")
            print(f"  Total records: {stats['total_records']:,}")
            print(f"  Unique IDs: {stats['total_unique_ids']:,}")
            print(f"  Mapped: {stats['mapped_count']:,}")
            print(f"  Unmapped: {stats['unmapped_count']:,}")
            print(f"  Coverage: {stats['coverage_pct']:.1f}%")
        sys.exit(0)
    else:
        print("❌ Validation failed")
        print("\nErrors:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
