#!/usr/bin/env python3
"""Validate snapshot manifests against registry expectations.

Usage:
    uv run python tools/validate_manifests.py --sources nflverse sheets
    uv run python tools/validate_manifests.py --sources all --fail-on-gaps
"""

import json
import sys
from pathlib import Path

import click
import polars as pl


def validate_snapshot(
    source: str,
    dataset: str,
    snapshot_date: str,
    expected_row_count: int,
    raw_dir: Path = Path("data/raw"),
) -> dict:
    """Validate a single snapshot entry.

    Returns:
        Dictionary with validation results and issues

    """
    issues = []

    # Check snapshot directory exists
    snapshot_path = raw_dir / source / dataset / f"dt={snapshot_date}"
    if not snapshot_path.exists():
        issues.append(f"Snapshot directory missing: {snapshot_path}")
        return {"valid": False, "issues": issues}

    # Check manifest exists
    manifest_path = snapshot_path / "_meta.json"
    if not manifest_path.exists():
        issues.append(f"Manifest missing: {manifest_path}")
        return {"valid": False, "issues": issues}

    # Load and validate manifest
    try:
        with manifest_path.open() as f:
            manifest = json.load(f)
    except json.JSONDecodeError as e:
        issues.append(f"Manifest JSON malformed: {e}")
        return {"valid": False, "issues": issues}

    # Check required fields
    required_fields = ["dataset", "loader_path", "source_version", "asof_datetime"]
    for field in required_fields:
        if field not in manifest:
            issues.append(f"Manifest missing required field: {field}")

    # Verify actual Parquet row count
    parquet_files = list(snapshot_path.glob("*.parquet"))
    if not parquet_files:
        issues.append(f"No Parquet files found in {snapshot_path}")
        return {"valid": False, "issues": issues}

    try:
        actual_df = pl.read_parquet(parquet_files)
        actual_row_count = len(actual_df)

        # Compare with registry expectation (if provided)
        if expected_row_count > 0 and actual_row_count != expected_row_count:
            issues.append(
                f"Row count mismatch: registry={expected_row_count}, actual={actual_row_count}"
            )
    except Exception as e:
        issues.append(f"Failed to read Parquet files: {e}")
        return {"valid": False, "issues": issues}

    return {"valid": len(issues) == 0, "issues": issues, "actual_row_count": actual_row_count}


@click.command()
@click.option("--sources", default="all", help='Comma-separated sources or "all"')
@click.option("--fail-on-gaps", is_flag=True, help="Exit with code 1 if validation fails")
@click.option(
    "--output-format",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@click.option(
    "--registry",
    default="dbt/ff_data_transform/seeds/snapshot_registry.csv",
    help="Path to snapshot registry",
)
def main(sources, fail_on_gaps, output_format, registry):
    """Validate snapshot manifests against registry."""
    # Load registry
    registry_path = Path(registry)
    if not registry_path.exists():
        click.echo(f"ERROR: Registry not found at {registry_path}", err=True)
        sys.exit(1)

    registry_df = pl.read_csv(registry_path)

    # Filter sources
    if sources != "all":
        source_list = [s.strip() for s in sources.split(",")]
        registry_df = registry_df.filter(pl.col("source").is_in(source_list))

    if len(registry_df) == 0:
        click.echo("No snapshots to validate", err=True)
        sys.exit(1)

    # Validate each entry
    results = []
    for row in registry_df.iter_rows(named=True):
        result = validate_snapshot(
            source=row["source"],
            dataset=row["dataset"],
            snapshot_date=row["snapshot_date"],
            expected_row_count=row["row_count"] or 0,
        )

        results.append(
            {
                "source": row["source"],
                "dataset": row["dataset"],
                "snapshot_date": row["snapshot_date"],
                "valid": result["valid"],
                "issues": result["issues"],
                "actual_row_count": result.get("actual_row_count", 0),
            }
        )

    # Output results
    if output_format == "json":
        print(json.dumps({"results": results}, indent=2))
    else:
        print("Snapshot Manifest Validation")
        print("=" * 70)

        valid_count = sum(1 for r in results if r["valid"])
        total_count = len(results)

        print(f"\nValidated: {valid_count}/{total_count} snapshots")

        # Show failures
        failures = [r for r in results if not r["valid"]]
        if failures:
            print(f"\nFailed Validations ({len(failures)}):")
            for f in failures:
                print(
                    f"\n  {f['source']}.{f['dataset']} [{f['snapshot_date']}] "
                    f"({f['actual_row_count']} rows):"
                )
                for issue in f["issues"]:
                    print(f"    - {issue}")
        else:
            print("\n✓ All validations passed!")

    # Exit code
    if fail_on_gaps and any(not r["valid"] for r in results):
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
