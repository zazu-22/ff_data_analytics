#!/usr/bin/env python3
r"""Validate snapshot manifests against registry expectations.

Usage:
    uv run python tools/validate_manifests.py --sources nflverse sheets
    uv run python tools/validate_manifests.py --sources all --fail-on-gaps
    uv run python tools/validate_manifests.py --sources all --check-freshness \\
        --freshness-warn-days 2 --freshness-error-days 7
    uv run python tools/validate_manifests.py --sources all --check-freshness \\
        --freshness-config config/snapshot_freshness_thresholds.yaml
"""

import json
import sys
from datetime import datetime
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


def check_snapshot_freshness(
    snapshot_date: str,
    warn_threshold_days: int,
    error_threshold_days: int,
) -> dict:
    """Check if snapshot is within freshness thresholds.

    Args:
        snapshot_date: Snapshot date in YYYY-MM-DD format
        warn_threshold_days: Warn if snapshot older than this many days
        error_threshold_days: Error if snapshot older than this many days

    Returns:
        {
            'age_days': int,
            'status': 'fresh' | 'stale-warn' | 'stale-error',
            'message': str
        }

    """
    try:
        snapshot_dt = datetime.strptime(snapshot_date, "%Y-%m-%d")
    except ValueError:
        return {
            "age_days": None,
            "status": "error",
            "message": f"Invalid snapshot_date format: {snapshot_date}",
        }

    age_days = (datetime.now() - snapshot_dt).days

    if age_days > error_threshold_days:
        status = "stale-error"
        message = (
            f"Snapshot STALE (ERROR): {age_days} days old (threshold: {error_threshold_days} days)"
        )
    elif age_days > warn_threshold_days:
        status = "stale-warn"
        message = (
            f"Snapshot STALE (WARN): {age_days} days old (threshold: {warn_threshold_days} days)"
        )
    else:
        status = "fresh"
        message = f"Snapshot FRESH: {age_days} days old"

    return {"age_days": age_days, "status": status, "message": message}


def format_text_output(results: list, check_freshness: bool) -> None:
    """Format and print validation results as text."""
    # Title
    title = "Snapshot Manifest Validation"
    if check_freshness:
        title += " (with Freshness)"
    print(title)
    print("=" * 70)

    valid_count = sum(1 for r in results if r["valid"])
    total_count = len(results)

    print(f"\nValidated: {valid_count}/{total_count} snapshots (integrity)")

    if check_freshness:
        fresh_count = sum(1 for r in results if r.get("freshness", {}).get("status") == "fresh")
        print(f"Fresh: {fresh_count}/{total_count} snapshots (within thresholds)")

    # Show integrity failures
    failures = [r for r in results if not r["valid"]]
    if failures:
        print(f"\nIntegrity Issues ({len(failures)}):")
        for f in failures:
            print(
                f"\n  {f['source']}.{f['dataset']} [{f['snapshot_date']}] "
                f"({f['actual_row_count']} rows):"
            )
            for issue in f["issues"]:
                print(f"    - {issue}")

    # Show freshness warnings/errors
    if check_freshness:
        freshness_issues = [
            r
            for r in results
            if r.get("freshness", {}).get("status") in ["stale-warn", "stale-error"]
        ]
        if freshness_issues:
            print(f"\nFreshness Issues ({len(freshness_issues)}):")
            for r in freshness_issues:
                freshness = r["freshness"]
                status_label = (
                    "STALE (ERROR)" if freshness["status"] == "stale-error" else "STALE (WARN)"
                )
                print(f"\n  {r['source']}.{r['dataset']} [{r['snapshot_date']}] {status_label}:")
                print(f"    - {freshness['message']}")

    if not failures and (not check_freshness or not freshness_issues):
        print("\n✓ All validations passed!")


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
@click.option(
    "--check-freshness",
    is_flag=True,
    help="Enable freshness validation",
)
@click.option(
    "--freshness-warn-days",
    type=int,
    help="Warn if snapshot older than N days (default from config or 7)",
)
@click.option(
    "--freshness-error-days",
    type=int,
    help="Error if snapshot older than N days (default from config or 14)",
)
@click.option(
    "--freshness-config",
    type=click.Path(exists=True),
    help="Path to freshness config YAML (per-source thresholds)",
)
def main(
    sources,
    fail_on_gaps,
    output_format,
    registry,
    check_freshness,
    freshness_warn_days,
    freshness_error_days,
    freshness_config,
):
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

    # Load freshness config if provided
    freshness_thresholds = {}
    if freshness_config:
        import yaml

        with Path(freshness_config).open() as f:
            freshness_thresholds = yaml.safe_load(f)

    # Set default thresholds
    default_warn_days = freshness_warn_days or 7
    default_error_days = freshness_error_days or 14

    # Validate each entry
    results = []
    for row in registry_df.iter_rows(named=True):
        result = validate_snapshot(
            source=row["source"],
            dataset=row["dataset"],
            snapshot_date=row["snapshot_date"],
            expected_row_count=row["row_count"] or 0,
        )

        result_entry = {
            "source": row["source"],
            "dataset": row["dataset"],
            "snapshot_date": row["snapshot_date"],
            "valid": result["valid"],
            "issues": result["issues"],
            "actual_row_count": result.get("actual_row_count", 0),
        }

        # Add freshness validation if enabled
        if check_freshness:
            source = row["source"]
            # Get thresholds (per-source config or global defaults)
            warn_days = freshness_thresholds.get(source, {}).get("warn_days", default_warn_days)
            error_days = freshness_thresholds.get(source, {}).get("error_days", default_error_days)

            freshness_result = check_snapshot_freshness(
                snapshot_date=row["snapshot_date"],
                warn_threshold_days=warn_days,
                error_threshold_days=error_days,
            )

            result_entry["freshness"] = freshness_result

        results.append(result_entry)

    # Output results
    if output_format == "json":
        print(json.dumps({"results": results}, indent=2))
    else:
        format_text_output(results, check_freshness)

    # Exit code
    has_integrity_failures = any(not r["valid"] for r in results)
    has_freshness_errors = False
    if check_freshness:
        has_freshness_errors = any(
            r.get("freshness", {}).get("status") == "stale-error" for r in results
        )

    if fail_on_gaps and (has_integrity_failures or has_freshness_errors):
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
