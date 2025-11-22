"""Prefect flow for NFLverse data ingestion with governance.

This flow handles NFLverse data ingestion with integrated governance:
- Freshness validation (warn if latest snapshot > 2 days old)
- Row delta anomaly detection (flag if row delta > 50% or < 0)
- Manifest validation (ensure all files have valid manifests)
- Atomic snapshot registry updates

Architecture:
    1. Check freshness of existing snapshots (governance)
    2. Fetch NFLverse data (multiple datasets)
    3. Detect row count anomalies (governance)
    4. Write Parquet files + manifests
    5. Update snapshot registry atomically
    6. Validate manifests (governance)

Dependencies:
    - src/ingest/nflverse/shim.py (load_nflverse)
    - src/flows/utils/validation.py (governance tasks)
    - src/flows/utils/notifications.py (logging)

Deprecates:
    - tools/update_snapshot_registry.py (manual registry updates)
"""

import sys
from datetime import datetime
from pathlib import Path

# Ensure src package is importable
repo_root = Path(__file__).parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

import polars as pl  # noqa: E402
from prefect import flow, task  # noqa: E402

from src.flows.utils.notifications import log_error, log_info, log_warning  # noqa: E402
from src.flows.utils.validation import (  # noqa: E402
    check_snapshot_currency,
    detect_row_count_anomaly,
    validate_manifests_task,
)
from src.ingest.nflverse.shim import load_nflverse  # noqa: E402


@task(name="fetch_nflverse_data")
def fetch_nflverse_data(
    datasets: list[str],
    seasons: list[int],
    weeks: list[int] | None = None,
    output_dir: str = "data/raw/nflverse",
) -> dict:
    """Fetch NFLverse data for specified datasets.

    Args:
        datasets: List of dataset names to fetch (e.g., ['weekly', 'snap_counts'])
        seasons: List of seasons to fetch
        weeks: Optional list of weeks to fetch (for weekly data)
        output_dir: Output directory for Parquet files

    Returns:
        Dict with fetch results keyed by dataset name

    """
    log_info(
        "Fetching NFLverse data",
        context={
            "datasets": datasets,
            "seasons": seasons,
            "weeks": weeks,
            "output_dir": output_dir,
        },
    )

    results = {}

    for dataset in datasets:
        try:
            log_info(f"Fetching {dataset}", context={"seasons": seasons, "weeks": weeks})

            # Call NFLverse shim
            manifest = load_nflverse(
                dataset=dataset,
                seasons=seasons,
                weeks=weeks,
                out_dir=output_dir,
            )

            results[dataset] = {
                "success": True,
                "manifest": manifest,
                "dataset": dataset,
            }

            log_info(
                f"Fetched {dataset}",
                context={
                    "output_parquet": manifest.get("output_parquet", "N/A"),
                    "partition_dir": manifest.get("partition_dir", "N/A"),
                },
            )

        except Exception as e:
            log_error(
                f"Failed to fetch {dataset}",
                context={"dataset": dataset, "error": str(e)},
            )

    log_info(
        "NFLverse fetch complete",
        context={"datasets_fetched": len(results), "total_datasets": len(datasets)},
    )

    return results


@task(name="update_snapshot_registry")
def update_snapshot_registry(
    source: str,
    dataset: str,
    snapshot_date: str,
    row_count: int,
    coverage_start_season: int | None = None,
    coverage_end_season: int | None = None,
    notes: str = "",
) -> dict:
    """Update snapshot registry with new snapshot metadata.

    This task atomically updates the registry, marking old snapshots as
    'superseded' and adding the new snapshot as 'current'.

    Args:
        source: Data source (e.g., 'nflverse')
        dataset: Dataset name (e.g., 'weekly')
        snapshot_date: Snapshot date (YYYY-MM-DD)
        row_count: Number of rows in snapshot
        coverage_start_season: Earliest season covered (optional)
        coverage_end_season: Latest season covered (optional)
        notes: Optional notes for registry

    Returns:
        Update result dictionary

    """
    log_info(
        "Updating snapshot registry",
        context={
            "source": source,
            "dataset": dataset,
            "snapshot_date": snapshot_date,
            "row_count": row_count,
        },
    )

    registry_path = Path("dbt/ff_data_transform/seeds/snapshot_registry.csv")

    # Read current registry
    registry = pl.read_csv(registry_path)

    # Check if this snapshot already exists
    existing = registry.filter(
        (pl.col("source") == source)
        & (pl.col("dataset") == dataset)
        & (pl.col("snapshot_date") == snapshot_date)
    )

    if len(existing) > 0:
        log_warning(
            f"Snapshot already exists in registry: {source}.{dataset}.{snapshot_date}",
            context={"action": "updating_existing_row"},
        )

        # Update existing row
        registry = registry.with_columns(
            pl.when(
                (pl.col("source") == source)
                & (pl.col("dataset") == dataset)
                & (pl.col("snapshot_date") == snapshot_date)
            )
            .then(pl.lit("current"))
            .otherwise(pl.col("status"))
            .alias("status"),
            pl.when(
                (pl.col("source") == source)
                & (pl.col("dataset") == dataset)
                & (pl.col("snapshot_date") == snapshot_date)
            )
            .then(pl.lit(row_count))
            .otherwise(pl.col("row_count"))
            .alias("row_count"),
        )

    else:
        # Mark previous snapshots for this source/dataset as superseded
        registry = registry.with_columns(
            pl.when(
                (pl.col("source") == source)
                & (pl.col("dataset") == dataset)
                & (pl.col("status") == "current")
            )
            .then(pl.lit("superseded"))
            .otherwise(pl.col("status"))
            .alias("status")
        )

        # Add new snapshot
        new_row = pl.DataFrame(
            [
                {
                    "source": source,
                    "dataset": dataset,
                    "snapshot_date": snapshot_date,
                    "status": "current",
                    "coverage_start_season": coverage_start_season,
                    "coverage_end_season": coverage_end_season,
                    "row_count": row_count,
                    "notes": notes,
                }
            ]
        )

        registry = pl.concat([registry, new_row])

    # Write updated registry
    registry.write_csv(registry_path)

    log_info(
        "Snapshot registry updated",
        context={
            "source": source,
            "dataset": dataset,
            "snapshot_date": snapshot_date,
            "registry_path": str(registry_path),
        },
    )

    return {
        "success": True,
        "source": source,
        "dataset": dataset,
        "snapshot_date": snapshot_date,
        "row_count": row_count,
    }


@task(name="extract_row_count_from_manifest")
def extract_row_count_from_manifest(manifest: dict) -> int:
    """Extract row count from NFLverse manifest.

    Reads the parquet file specified in manifest to get accurate row count.

    Args:
        manifest: Manifest dict from load_nflverse

    Returns:
        Row count

    """
    # Try both manifest structures (top-level and nested under meta)
    output_parquet = manifest.get("parquet_file") or manifest.get("meta", {}).get("output_parquet")

    if not output_parquet:
        log_error("Manifest missing output_parquet field", context={"manifest": manifest})

    # Read parquet to get row count
    df = pl.read_parquet(output_parquet)
    return len(df)


@task(name="extract_coverage_metadata")
def extract_coverage_metadata(manifest: dict) -> dict:
    """Extract season coverage metadata from NFLverse data.

    Args:
        manifest: Manifest dict from load_nflverse

    Returns:
        Dict with coverage_start_season and coverage_end_season

    """
    # Try both manifest structures (top-level and nested under meta)
    output_parquet = manifest.get("parquet_file") or manifest.get("meta", {}).get("output_parquet")

    if not output_parquet:
        return {"coverage_start_season": None, "coverage_end_season": None}

    # Read parquet to extract coverage
    df = pl.read_parquet(output_parquet)

    if "season" not in df.columns:
        return {"coverage_start_season": None, "coverage_end_season": None}

    seasons = df["season"].unique().sort()
    if len(seasons) == 0:
        return {"coverage_start_season": None, "coverage_end_season": None}

    return {
        "coverage_start_season": int(seasons.min()),
        "coverage_end_season": int(seasons.max()),
    }


@flow(name="nfl_data_pipeline")
def nfl_data_pipeline(
    datasets: list[str] | None = None,
    seasons: list[int] | None = None,
    weeks: list[int] | None = None,
    output_dir: str = "data/raw/nflverse",
    snapshot_date: str | None = None,
) -> dict:
    """Prefect flow for NFLverse data ingestion with governance.

    This flow handles all NFLverse datasets with integrated governance:
    - Freshness validation
    - Row delta anomaly detection
    - Manifest validation
    - Atomic snapshot registry updates

    Args:
        datasets: List of dataset names (defaults to all critical datasets)
        seasons: List of seasons to fetch (defaults to current season)
        weeks: Optional list of weeks (for weekly data)
        output_dir: Output directory for Parquet files
        snapshot_date: Snapshot date (defaults to today)

    Returns:
        Flow result with governance validation status

    """
    # Defaults
    if datasets is None:
        datasets = ["weekly", "snap_counts", "ff_opportunity", "schedule", "teams"]

    if seasons is None:
        current_year = datetime.now().year
        seasons = [current_year]

    if snapshot_date is None:
        snapshot_date = datetime.now().strftime("%Y-%m-%d")

    log_info(
        "Starting NFL data pipeline",
        context={
            "datasets": datasets,
            "seasons": seasons,
            "weeks": weeks,
            "snapshot_date": snapshot_date,
        },
    )

    # Governance: Check freshness of existing snapshots (warn if > 2 days old)
    freshness_results = {}
    for dataset in datasets:
        freshness = check_snapshot_currency(
            source="nflverse",
            dataset=dataset,
            max_age_days=2,
        )

        freshness_results[dataset] = freshness

        if not freshness["is_current"]:
            log_warning(
                f"Snapshot for {dataset} is stale",
                context=freshness,
            )

    # Fetch NFLverse data
    fetch_results = fetch_nflverse_data(
        datasets=datasets,
        seasons=seasons,
        weeks=weeks,
        output_dir=output_dir,
    )

    # Process each dataset: anomaly detection + registry update
    anomaly_results = {}
    registry_updates = {}

    for dataset, fetch_result in fetch_results.items():
        if not fetch_result.get("success"):
            log_warning(
                f"Skipping {dataset} - fetch failed",
                context={"dataset": dataset},
            )
            continue

        manifest = fetch_result["manifest"]

        # Extract row count and coverage
        row_count = extract_row_count_from_manifest(manifest)
        coverage = extract_coverage_metadata(manifest)

        # Governance: Detect row count anomalies (> 50% change or data loss)
        anomaly = detect_row_count_anomaly(
            source="nflverse",
            dataset=dataset,
            current_count=row_count,
            threshold_pct=50.0,
        )

        anomaly_results[dataset] = anomaly

        if anomaly["is_anomaly"]:
            log_warning(
                f"Row count anomaly detected for {dataset}",
                context=anomaly,
            )

        # Update snapshot registry
        registry_update = update_snapshot_registry(
            source="nflverse",
            dataset=dataset,
            snapshot_date=snapshot_date,
            row_count=row_count,
            coverage_start_season=coverage.get("coverage_start_season"),
            coverage_end_season=coverage.get("coverage_end_season"),
            notes=f"NFLverse ingestion for seasons {seasons}",
        )

        registry_updates[dataset] = registry_update

    # Governance: Validate manifests
    manifest_validation = validate_manifests_task(
        sources=["nflverse"],
        fail_on_gaps=False,
    )

    log_info(
        "NFL data pipeline complete",
        context={
            "datasets_processed": len(registry_updates),
            "anomalies_detected": sum(1 for a in anomaly_results.values() if a["is_anomaly"]),
        },
    )

    return {
        "snapshot_date": snapshot_date,
        "fetch_results": fetch_results,
        "freshness_validation": freshness_results,
        "anomaly_detection": anomaly_results,
        "registry_updates": registry_updates,
        "manifest_validation": manifest_validation,
    }


if __name__ == "__main__":
    # For local testing
    # Test with minimal data: 1 week of current season
    result = nfl_data_pipeline(
        datasets=["weekly"],
        seasons=[2024],
        weeks=[1],
    )

    print("\n" + "=" * 70)
    print("NFL Data Pipeline Result")
    print("=" * 70)
    print(f"Snapshot date: {result['snapshot_date']}")
    print(f"Datasets processed: {len(result['registry_updates'])}")
    anomalies = sum(1 for a in result["anomaly_detection"].values() if a["is_anomaly"])
    print(f"Anomalies detected: {anomalies}")
    print("=" * 70)
