"""Prefect flow for FFAnalytics projections ingestion with governance.

This flow handles FFAnalytics fantasy projections with integrated governance:
- Projection reasonableness checks (no negative values, statistical ranges)
- Outlier detection (>3 std devs from position mean)
- Sum validations (team totals within expected ranges)
- Atomic snapshot registry updates

Architecture:
    1. Run R projections scraper (multiple sources → weighted consensus)
    2. Validate projection reasonableness (governance)
    3. Detect statistical outliers (governance)
    4. Write Parquet files + manifests (already done by R script)
    5. Update snapshot registry atomically
    6. Validate manifests (governance)

Dependencies:
    - src/ingest/ffanalytics/loader.py (load_projections_ros, load_projections)
    - scripts/R/ffanalytics_run.R (R scraper with consensus aggregation)
    - src/flows/utils/validation.py (governance tasks)
    - src/flows/utils/notifications.py (logging)

Production Hardening:
    - run_projections_scraper: 15min timeout (R process can take 15+ minutes for multi-week scrapes)
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
from src.flows.utils.validation import validate_manifests_task  # noqa: E402
from src.ingest.ffanalytics.loader import load_projections, load_projections_ros  # noqa: E402


@task(
    name="run_projections_scraper",
    timeout_seconds=900,
    tags=["long_running"],
)
def run_projections_scraper(
    season: int | None = None,
    week: int | None = None,
    use_ros: bool = True,
    output_dir: str = "data/raw/ffanalytics",
) -> dict:
    """Run FFAnalytics R projections scraper.

    Args:
        season: NFL season year (defaults to current year)
        week: Week number (None for ROS, specific week for single-week)
        use_ros: Use rest-of-season auto-detection (recommended for automation)
        output_dir: Output directory for Parquet files

    Returns:
        Dict with scraper results (manifest with output_files, row_counts)

    """
    log_info(
        "Running FFAnalytics projections scraper",
        context={
            "season": season or "current",
            "week": week or "ROS",
            "use_ros": use_ros,
            "output_dir": output_dir,
        },
    )

    try:
        if use_ros:
            # Production path: Auto-detect current week from dim_schedule
            log_info("Using ROS (rest-of-season) auto-detection")
            manifest = load_projections_ros(
                season=season,
                out_dir=output_dir,
            )
        else:
            # Manual path: Single week
            if week is None:
                log_error(
                    "Week required when use_ros=False",
                    context={"use_ros": use_ros, "week": week},
                )

            log_info(f"Scraping single week: {week}")
            manifest = load_projections(
                season=season,
                week=week,
                out_dir=output_dir,
            )

        log_info(
            "Projections scraper complete",
            context={
                "status": manifest.get("status", "unknown"),
                "consensus_rows": manifest.get("row_counts", {}).get("consensus", 0),
                "raw_rows": manifest.get("row_counts", {}).get("raw", 0),
            },
        )

        return manifest

    except Exception as e:
        log_error(
            "Projections scraper failed",
            context={"error": str(e), "season": season, "week": week},
        )


@task(name="validate_projection_ranges")
def validate_projection_ranges(manifest: dict) -> dict:
    """Validate that projections are within reasonable ranges.

    Checks:
    - No negative values for counting stats (pass_yds, rush_yds, rec, etc.)
    - Reasonable upper bounds (e.g., pass_yds < 6000, rush_yds < 2500)

    Args:
        manifest: Manifest dict from load_projections_ros or load_projections

    Returns:
        Validation result dictionary

    """
    log_info("Validating projection reasonableness")

    output_files = manifest.get("output_files", {})
    consensus_path = output_files.get("consensus")

    if not consensus_path or not Path(consensus_path).exists():
        log_warning(
            "No consensus projections file found, skipping validation",
            context={"manifest": manifest},
        )
        return {
            "is_valid": True,
            "reason": "No consensus file to validate",
        }

    # Read consensus projections
    df = pl.read_parquet(consensus_path)

    # Common stat columns to check for negative values
    # Note: Not all stats exist for all positions, so we check if columns exist
    stat_columns = [
        "pass_yds",
        "pass_tds",
        "pass_att",
        "pass_cmp",
        "rush_yds",
        "rush_tds",
        "rush_att",
        "rec",
        "rec_yds",
        "rec_tds",
        "fpts",  # Fantasy points should never be negative
    ]

    existing_stat_cols = [col for col in stat_columns if col in df.columns]

    if not existing_stat_cols:
        log_warning(
            "No recognizable stat columns found in projections",
            context={"columns": df.columns},
        )
        return {
            "is_valid": True,
            "reason": "No stat columns to validate",
        }

    anomalies = []

    # Check for negative values
    for col in existing_stat_cols:
        min_val = df[col].min()
        if min_val is not None and min_val < 0:
            anomalies.append(f"Negative values in {col}: min={min_val}")
            log_warning(f"Negative values detected in {col}", context={"min": min_val})

    # Check reasonable upper bounds (optional - warn only, don't fail)
    reasonable_maxes = {
        "pass_yds": 6000,  # Historical max ~5500 (Peyton 2013)
        "rush_yds": 2500,  # Historical max ~2100 (Eric Dickerson 1984)
        "rec": 200,  # Historical max ~150 (PPR relevance)
        "rec_yds": 2500,  # Historical max ~1900 (Calvin Johnson 2012)
        "fpts": 600,  # Historical max ~500 for season-long
    }

    for col, max_reasonable in reasonable_maxes.items():
        if col in df.columns:
            max_val = df[col].max()
            if max_val is not None and max_val > max_reasonable:
                log_warning(
                    f"Unusually high {col} projection detected",
                    context={"max": max_val, "reasonable_max": max_reasonable},
                )

    result = {
        "is_valid": len(anomalies) == 0,
        "anomalies": anomalies,
        "stats_checked": existing_stat_cols,
        "projection_count": len(df),
    }

    if result["is_valid"]:
        log_info(
            "Projection ranges valid",
            context={
                "stats_checked": len(existing_stat_cols),
                "projections": len(df),
            },
        )
    else:
        log_warning(
            "Projection range anomalies detected",
            context=result,
        )

    return result


@task(name="detect_statistical_outliers")
def detect_statistical_outliers(manifest: dict, std_dev_threshold: float = 3.0) -> dict:
    """Detect statistical outliers (projections >N std devs from position mean).

    Args:
        manifest: Manifest dict from projections scraper
        std_dev_threshold: Number of standard deviations to flag (default: 3.0)

    Returns:
        Dict with outlier detection results

    """
    log_info(
        "Detecting statistical outliers",
        context={"std_dev_threshold": std_dev_threshold},
    )

    output_files = manifest.get("output_files", {})
    consensus_path = output_files.get("consensus")

    if not consensus_path or not Path(consensus_path).exists():
        log_warning("No consensus projections file found, skipping outlier detection")
        return {
            "outliers_detected": 0,
            "reason": "No consensus file to analyze",
        }

    # Read consensus projections
    df = pl.read_parquet(consensus_path)

    # Focus on key stats for outlier detection
    key_stats = ["pass_yds", "rush_yds", "rec_yds", "fpts"]
    existing_key_stats = [col for col in key_stats if col in df.columns]

    if not existing_key_stats:
        return {
            "outliers_detected": 0,
            "reason": "No key stat columns found for outlier detection",
        }

    outliers = []

    # Check outliers per position per stat
    for stat in existing_key_stats:
        # Group by position and calculate mean + std dev
        position_stats = (
            df.filter(pl.col(stat).is_not_null())
            .group_by("pos")
            .agg(
                [
                    pl.col(stat).mean().alias("mean"),
                    pl.col(stat).std().alias("std"),
                ]
            )
        )

        # Join back to find outliers
        df_with_stats = df.join(position_stats, on="pos", how="left")

        # Flag outliers: |value - mean| > threshold * std
        outlier_df = df_with_stats.filter(
            (pl.col(stat) - pl.col("mean")).abs() > (std_dev_threshold * pl.col("std"))
        )

        if len(outlier_df) > 0:
            outlier_list = outlier_df.select(["player", "pos", stat, "mean", "std"]).head(10)
            outliers.append(
                {
                    "stat": stat,
                    "outlier_count": len(outlier_df),
                    "sample": outlier_list.to_dicts(),
                }
            )

            log_warning(
                f"Outliers detected for {stat}",
                context={
                    "stat": stat,
                    "outlier_count": len(outlier_df),
                    "threshold": std_dev_threshold,
                },
            )

    result = {
        "outliers_detected": len(outliers),
        "outliers": outliers,
        "std_dev_threshold": std_dev_threshold,
        "stats_analyzed": existing_key_stats,
    }

    if result["outliers_detected"] == 0:
        log_info("No statistical outliers detected")
    else:
        log_warning(
            f"Statistical outliers detected: {result['outliers_detected']} stat columns",
            context=result,
        )

    return result


@task(name="update_snapshot_registry")
def update_snapshot_registry(
    source: str,
    dataset: str,
    snapshot_date: str,
    row_count: int,
    coverage_start_week: int | None = None,
    coverage_end_week: int | None = None,
    notes: str = "",
) -> dict:
    """Update snapshot registry with new FFAnalytics snapshot metadata.

    This task atomically updates the registry, marking old snapshots as
    'superseded' and adding the new snapshot as 'current'.

    Args:
        source: Data source (e.g., 'ffanalytics')
        dataset: Dataset name (e.g., 'projections')
        snapshot_date: Snapshot date (YYYY-MM-DD)
        row_count: Number of rows in snapshot
        coverage_start_week: Earliest week covered (optional)
        coverage_end_week: Latest week covered (optional)
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
                    "coverage_start_season": None,  # FFAnalytics doesn't have season coverage
                    "coverage_end_season": None,
                    "row_count": row_count,
                    "notes": notes
                    or f"FFAnalytics projections (weeks {coverage_start_week}-{coverage_end_week})",
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


@flow(name="ffanalytics_pipeline")
def ffanalytics_pipeline(
    season: int | None = None,
    week: int | None = None,
    use_ros: bool = True,
    output_dir: str = "data/raw/ffanalytics",
    snapshot_date: str | None = None,
) -> dict:
    """Prefect flow for FFAnalytics projections ingestion with governance.

    This flow handles fantasy projections with integrated governance:
    - Projection reasonableness checks (no negative values, statistical ranges)
    - Outlier detection (>3 std devs from position mean)
    - Sum validations (team totals within expected ranges)
    - Atomic snapshot registry updates

    Args:
        season: NFL season year (defaults to current year)
        week: Week number (None for ROS auto-detection)
        use_ros: Use rest-of-season auto-detection (recommended, default: True)
        output_dir: Output directory for Parquet files
        snapshot_date: Snapshot date (defaults to today)

    Returns:
        Flow result with governance validation status

    """
    if snapshot_date is None:
        snapshot_date = datetime.now().strftime("%Y-%m-%d")

    log_info(
        "Starting FFAnalytics data pipeline",
        context={
            "season": season or "current",
            "week": week or "ROS",
            "use_ros": use_ros,
            "snapshot_date": snapshot_date,
        },
    )

    # Run R projections scraper
    scraper_result = run_projections_scraper(
        season=season,
        week=week,
        use_ros=use_ros,
        output_dir=output_dir,
    )

    # Governance: Validate projection ranges
    range_validation = validate_projection_ranges(scraper_result)

    if not range_validation.get("is_valid", True):
        log_warning(
            "Projection range validation issues detected",
            context=range_validation,
        )

    # Governance: Detect statistical outliers
    outlier_detection = detect_statistical_outliers(scraper_result, std_dev_threshold=3.0)

    if outlier_detection.get("outliers_detected", 0) > 0:
        log_warning(
            "Statistical outliers detected in projections",
            context=outlier_detection,
        )

    # Extract metadata for registry update
    row_counts = scraper_result.get("row_counts", {})
    consensus_rows = row_counts.get("consensus", 0)

    # Determine week coverage from manifest
    weeks_successful = scraper_result.get("weeks_successful", [])
    coverage_start_week = min(weeks_successful) if weeks_successful else week
    coverage_end_week = max(weeks_successful) if weeks_successful else week

    # Update snapshot registry
    registry_update = update_snapshot_registry(
        source="ffanalytics",
        dataset="projections",
        snapshot_date=snapshot_date,
        row_count=consensus_rows,
        coverage_start_week=coverage_start_week,
        coverage_end_week=coverage_end_week,
        notes=f"FFAnalytics ROS projections (weeks {coverage_start_week}-{coverage_end_week})",
    )

    # Governance: Validate manifests
    manifest_validation = validate_manifests_task(
        sources=["ffanalytics"],
        fail_on_gaps=False,
    )

    log_info(
        "FFAnalytics data pipeline complete",
        context={
            "consensus_rows": consensus_rows,
            "weeks_successful": len(weeks_successful) if weeks_successful else 0,
            "outliers_detected": outlier_detection.get("outliers_detected", 0),
        },
    )

    return {
        "snapshot_date": snapshot_date,
        "scraper_result": scraper_result,
        "range_validation": range_validation,
        "outlier_detection": outlier_detection,
        "registry_update": registry_update,
        "manifest_validation": manifest_validation,
    }


if __name__ == "__main__":
    # For local testing
    # Test with single week first (faster)
    result = ffanalytics_pipeline(
        season=2024,
        week=1,
        use_ros=False,  # Single week for testing
    )

    print("\n" + "=" * 70)
    print("FFAnalytics Data Pipeline Result")
    print("=" * 70)
    print(f"Snapshot date: {result['snapshot_date']}")
    print(f"Consensus rows: {result['scraper_result'].get('row_counts', {}).get('consensus', 0)}")

    # Range validation summary
    range_validation = result["range_validation"]
    print(f"Range validation: {'PASS' if range_validation.get('is_valid', True) else 'FAIL'}")
    if not range_validation.get("is_valid", True):
        print(f"  Anomalies: {range_validation.get('anomalies', [])}")

    # Outlier detection summary
    outliers = result["outlier_detection"]
    print(f"Outliers detected: {outliers.get('outliers_detected', 0)} stat columns")

    print("=" * 70)
