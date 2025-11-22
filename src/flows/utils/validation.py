"""Shared validation utilities for Prefect flows."""

import subprocess
from pathlib import Path

import polars as pl
from prefect import task


@task(name="validate_manifests")
def validate_manifests_task(sources: list[str], fail_on_gaps: bool = True) -> dict:
    """Run manifest validation tool.

    Args:
        sources: List of source names to validate
        fail_on_gaps: Whether to fail on validation errors

    Returns:
        Validation results dictionary

    Raises:
        RuntimeError: If validation fails and fail_on_gaps=True

    """
    cmd = [
        "uv",
        "run",
        "python",
        "tools/validate_manifests.py",
        "--sources",
        ",".join(sources),
        "--output-format",
        "json",
    ]

    if fail_on_gaps:
        cmd.append("--fail-on-gaps")

    result = subprocess.run(cmd, capture_output=True, text=True)  # noqa: S603

    if result.returncode != 0 and fail_on_gaps:
        raise RuntimeError(f"Manifest validation failed: {result.stderr}")

    return {"success": result.returncode == 0, "output": result.stdout, "errors": result.stderr}


@task(name="check_snapshot_currency")
def check_snapshot_currency(source: str, dataset: str, max_age_days: int) -> dict:
    """Check if snapshot is current (not stale).

    Args:
        source: Data source (e.g., 'nflverse')
        dataset: Dataset within source (e.g., 'weekly')
        max_age_days: Maximum acceptable age in days

    Returns:
        Dictionary with currency check results

    """
    from datetime import datetime

    # Read snapshot registry
    registry_path = Path("dbt/ff_data_transform/seeds/snapshot_registry.csv")
    registry = pl.read_csv(registry_path)

    # Find current snapshot for source/dataset
    current = registry.filter(
        (pl.col("source") == source)
        & (pl.col("dataset") == dataset)
        & (pl.col("status") == "current")
    ).select(["snapshot_date"])

    if len(current) == 0:
        return {"is_current": False, "reason": f"No current snapshot found for {source}.{dataset}"}

    snapshot_date = datetime.strptime(current["snapshot_date"][0], "%Y-%m-%d")
    age_days = (datetime.now() - snapshot_date).days
    is_current = age_days <= max_age_days

    return {
        "is_current": is_current,
        "snapshot_date": current["snapshot_date"][0],
        "age_days": age_days,
        "max_age_days": max_age_days,
    }


@task(name="detect_row_count_anomaly")
def detect_row_count_anomaly(
    source: str, dataset: str, current_count: int, threshold_pct: float = 50.0
) -> dict:
    """Detect unusual row count changes.

    Args:
        source: Data source
        dataset: Dataset within source
        current_count: Row count from latest load
        threshold_pct: Percentage change threshold for anomaly

    Returns:
        Dictionary with anomaly detection results

    """
    # Read snapshot registry
    registry_path = Path("dbt/ff_data_transform/seeds/snapshot_registry.csv")
    registry = pl.read_csv(registry_path)

    # Get previous snapshot row count
    snapshots = (
        registry.filter((pl.col("source") == source) & (pl.col("dataset") == dataset))
        .sort("snapshot_date", descending=True)
        .select(["snapshot_date", "row_count"])
        .head(2)
    )

    if len(snapshots) < 2:
        return {"is_anomaly": False, "reason": "Not enough snapshots for comparison"}

    # Use .row() to get a dict for the second row (index 1)
    previous_row = snapshots.row(1, named=True)
    previous_count = int(previous_row["row_count"]) if previous_row["row_count"] is not None else 0

    delta = current_count - previous_count
    pct_change = (delta / previous_count * 100) if previous_count > 0 else 0

    is_anomaly = abs(pct_change) > threshold_pct

    return {
        "is_anomaly": is_anomaly,
        "current_count": current_count,
        "previous_count": previous_count,
        "delta": delta,
        "pct_change": float(pct_change),
        "threshold_pct": threshold_pct,
    }
