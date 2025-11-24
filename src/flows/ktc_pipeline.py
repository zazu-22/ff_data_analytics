"""Prefect flow for KTC (Keep Trade Cut) dynasty valuations ingestion with governance.

This flow handles KTC data ingestion with integrated governance:
- Valuation range checks (0-10000 sanity check)
- Player mapping validation (>90% coverage against dim_player_id_xref)
- Missing player reporting (top 10 unmapped for investigation)
- Atomic snapshot registry updates

Architecture:
    1. Fetch KTC data (players and picks separately)
    2. Validate valuation ranges (governance)
    3. Validate player mapping coverage (governance)
    4. Write Parquet files + manifests
    5. Update snapshot registry atomically
    6. Validate manifests (governance)

Dependencies:
    - src/ingest/ktc/registry.py (load_players, load_picks)
    - src/flows/utils/validation.py (governance tasks)
    - src/flows/utils/notifications.py (logging)

Architecture Decision:
    - This flow uses DIRECT load_players()/load_picks() calls, not fetch/parse/write split
    - Rationale: KTC client is already simple, single-source, no complex transformation needed
    - Governance layer added AFTER ingestion for validation checks

Production Hardening:
    - fetch_ktc_data: 2 retries with 30s delay (handles API rate limits)
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
from src.ingest.ktc.registry import load_picks, load_players  # noqa: E402


@task(
    name="fetch_ktc_data",
    retries=2,
    retry_delay_seconds=30,
    tags=["external_api"],
)
def fetch_ktc_data(
    datasets: list[str],
    market_scope: str = "dynasty_1qb",
    output_dir: str = "data/raw/ktc",
) -> dict:
    """Fetch KTC data for specified datasets (players, picks).

    Args:
        datasets: List of dataset names to fetch (e.g., ['players', 'picks'])
        market_scope: Market scope (dynasty_1qb or dynasty_superflex)
        output_dir: Output directory for Parquet files

    Returns:
        Dict with fetch results keyed by dataset name

    """
    log_info(
        "Fetching KTC data",
        context={
            "datasets": datasets,
            "market_scope": market_scope,
            "output_dir": output_dir,
        },
    )

    results = {}

    for dataset in datasets:
        try:
            log_info(f"Fetching {dataset}", context={"market_scope": market_scope})

            # Call KTC registry loaders
            if dataset == "players":
                manifest = load_players(
                    out_dir=output_dir,
                    market_scope=market_scope,
                )
            elif dataset == "picks":
                manifest = load_picks(
                    out_dir=output_dir,
                    market_scope=market_scope,
                )
            else:
                log_error(f"Unknown dataset: {dataset}", context={"dataset": dataset})
                continue

            results[dataset] = {
                "success": True,
                "manifest": manifest,
                "dataset": dataset,
            }

            log_info(
                f"Fetched {dataset}",
                context={
                    "output_path": manifest.get("output_path", "N/A"),
                    "row_count": manifest.get("row_count", "N/A"),
                },
            )

        except Exception as e:
            log_error(
                f"Failed to fetch {dataset}",
                context={"dataset": dataset, "error": str(e)},
            )

    log_info(
        "KTC fetch complete",
        context={"datasets_fetched": len(results), "total_datasets": len(datasets)},
    )

    return results


@task(name="validate_valuation_ranges")
def validate_valuation_ranges(manifest: dict, dataset: str) -> dict:
    """Validate that KTC valuations are within reasonable ranges.

    Args:
        manifest: Manifest dict from load_players or load_picks
        dataset: Dataset name (players or picks)

    Returns:
        Validation result dictionary

    """
    log_info(f"Validating valuation ranges for {dataset}")

    output_path = manifest.get("output_path")
    if not output_path:
        log_error("Manifest missing output_path", context={"manifest": manifest})

    # Read data
    df = pl.read_parquet(output_path)

    # Check value column exists
    if "value" not in df.columns:
        log_error(f"Missing 'value' column in {dataset}", context={"columns": df.columns})

    # Validate ranges: Min 0, Max 10000
    min_value = df["value"].min()
    max_value = df["value"].max()

    anomalies = []

    if min_value < 0:
        anomalies.append(f"Negative values detected: min={min_value}")
        log_warning(f"Negative values in {dataset}", context={"min_value": min_value})

    if max_value > 10000:
        anomalies.append(f"Excessive values detected: max={max_value}")
        log_warning(f"Excessive values in {dataset}", context={"max_value": max_value})

    # Report outliers for investigation
    outliers = df.filter((pl.col("value") < 0) | (pl.col("value") > 10000))
    if len(outliers) > 0:
        log_warning(
            f"Found {len(outliers)} outliers in {dataset}",
            context={"outlier_count": len(outliers)},
        )

    result = {
        "dataset": dataset,
        "is_valid": len(anomalies) == 0,
        "anomalies": anomalies,
        "min_value": int(min_value),
        "max_value": int(max_value),
        "outlier_count": len(outliers),
    }

    if result["is_valid"]:
        log_info(
            f"Valuation ranges valid for {dataset}",
            context={"min": min_value, "max": max_value},
        )
    else:
        log_warning(
            f"Valuation range anomalies in {dataset}",
            context=result,
        )

    return result


@task(name="validate_player_mapping")
def validate_player_mapping(manifest: dict, min_coverage_pct: float = 90.0) -> dict:
    """Validate that KTC players map to dim_player_id_xref.

    Args:
        manifest: Manifest dict from load_players
        min_coverage_pct: Minimum acceptable coverage percentage (default: 90%)

    Returns:
        Validation result dictionary with coverage stats and unmapped players

    """
    log_info(
        "Validating player mapping coverage",
        context={"min_coverage_pct": min_coverage_pct},
    )

    output_path = manifest.get("output_path")
    if not output_path:
        log_error("Manifest missing output_path", context={"manifest": manifest})

    # Read KTC players
    ktc_players = pl.read_parquet(output_path)

    if "player_name" not in ktc_players.columns:
        log_error(
            "Missing 'player_name' column in players dataset",
            context={"columns": ktc_players.columns},
        )

    # Read dim_player_id_xref from dbt target
    xref_path = Path("dbt/ff_data_transform/target/dev.duckdb")

    if not xref_path.exists():
        log_warning(
            "dim_player_id_xref not built yet - skipping player mapping validation",
            context={"action": "run 'just dbt-run --select dim_player_id_xref' first"},
        )
        return {
            "is_valid": True,
            "reason": "dim_player_id_xref not available - skipping validation",
        }

    # Query DuckDB for player crosswalk
    import duckdb

    conn = duckdb.connect(str(xref_path), read_only=True)
    xref = conn.execute("SELECT DISTINCT name FROM dim_player_id_xref WHERE name IS NOT NULL").pl()
    conn.close()

    # Join to find unmapped players
    # Note: Using indicator column to track join match status
    ktc_unique = ktc_players.select("player_name").unique()
    xref_names = xref.select(pl.col("name").alias("xref_name"))

    ktc_with_mapping = ktc_unique.join(
        xref_names.with_columns(pl.col("xref_name").alias("player_name")),
        on="player_name",
        how="left",
    )

    unmapped = ktc_with_mapping.filter(pl.col("xref_name").is_null())
    total_players = len(ktc_with_mapping)
    mapped_count = total_players - len(unmapped)
    coverage_pct = (mapped_count / total_players * 100) if total_players > 0 else 0

    # Report top 10 unmapped players for investigation
    top_unmapped = unmapped.head(10)["player_name"].to_list()

    result = {
        "is_valid": coverage_pct >= min_coverage_pct,
        "total_players": total_players,
        "mapped_count": mapped_count,
        "unmapped_count": len(unmapped),
        "coverage_pct": float(coverage_pct),
        "min_coverage_pct": min_coverage_pct,
        "top_unmapped": top_unmapped,
    }

    if result["is_valid"]:
        log_info(
            "Player mapping coverage acceptable",
            context={
                "coverage_pct": f"{coverage_pct:.1f}%",
                "mapped": mapped_count,
                "total": total_players,
            },
        )
    else:
        log_warning(
            f"Player mapping coverage below threshold: {coverage_pct:.1f}% < {min_coverage_pct}%",
            context={
                "unmapped_count": len(unmapped),
                "top_unmapped": top_unmapped,
            },
        )

    return result


@task(name="update_snapshot_registry")
def update_snapshot_registry(
    source: str,
    dataset: str,
    snapshot_date: str,
    row_count: int,
    market_scope: str = "dynasty_1qb",
    notes: str = "",
) -> dict:
    """Update snapshot registry with new KTC snapshot metadata.

    This task atomically updates the registry, marking old snapshots as
    'superseded' and adding the new snapshot as 'current'.

    Args:
        source: Data source (e.g., 'ktc')
        dataset: Dataset name (e.g., 'players', 'picks')
        snapshot_date: Snapshot date (YYYY-MM-DD)
        row_count: Number of rows in snapshot
        market_scope: Market scope (dynasty_1qb or dynasty_superflex)
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
                    "coverage_start_season": None,  # KTC doesn't have season coverage
                    "coverage_end_season": None,
                    "row_count": row_count,
                    "notes": notes or f"KTC {market_scope} ingestion",
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


@flow(name="ktc_pipeline")
def ktc_pipeline(
    datasets: list[str] | None = None,
    market_scope: str = "dynasty_1qb",
    output_dir: str = "data/raw/ktc",
    snapshot_date: str | None = None,
) -> dict:
    """Prefect flow for KTC data ingestion with governance.

    This flow handles KTC dynasty valuations with integrated governance:
    - Valuation range checks (0-10000)
    - Player mapping validation (>90% coverage)
    - Missing player reporting
    - Atomic snapshot registry updates

    Args:
        datasets: List of dataset names (defaults to ['players', 'picks'])
        market_scope: dynasty_1qb or dynasty_superflex (defaults to dynasty_1qb per spec)
        output_dir: Output directory for Parquet files
        snapshot_date: Snapshot date (defaults to today)

    Returns:
        Flow result with governance validation status

    """
    # Defaults
    if datasets is None:
        datasets = ["players", "picks"]

    if snapshot_date is None:
        snapshot_date = datetime.now().strftime("%Y-%m-%d")

    log_info(
        "Starting KTC data pipeline",
        context={
            "datasets": datasets,
            "market_scope": market_scope,
            "snapshot_date": snapshot_date,
        },
    )

    # Fetch KTC data
    fetch_results = fetch_ktc_data(
        datasets=datasets,
        market_scope=market_scope,
        output_dir=output_dir,
    )

    # Process each dataset: governance validation + registry update
    valuation_validations = {}
    player_mapping_validation = None
    registry_updates = {}

    for dataset, fetch_result in fetch_results.items():
        if not fetch_result.get("success"):
            log_warning(
                f"Skipping {dataset} - fetch failed",
                context={"dataset": dataset},
            )
            continue

        manifest = fetch_result["manifest"]

        # Governance: Validate valuation ranges
        valuation_validation = validate_valuation_ranges(manifest, dataset)
        valuation_validations[dataset] = valuation_validation

        if not valuation_validation["is_valid"]:
            log_warning(
                f"Valuation validation issues for {dataset}",
                context=valuation_validation,
            )

        # Governance: Validate player mapping (players only)
        if dataset == "players":
            player_mapping_validation = validate_player_mapping(manifest, min_coverage_pct=90.0)

            if not player_mapping_validation.get("is_valid", True):
                log_warning(
                    "Player mapping coverage below threshold",
                    context=player_mapping_validation,
                )

        # Update snapshot registry
        row_count = manifest.get("row_count", 0)

        registry_update = update_snapshot_registry(
            source="ktc",
            dataset=dataset,
            snapshot_date=snapshot_date,
            row_count=row_count,
            market_scope=market_scope,
            notes=f"KTC {market_scope} ingestion",
        )

        registry_updates[dataset] = registry_update

    # Governance: Validate manifests
    manifest_validation = validate_manifests_task(
        sources=["ktc"],
        fail_on_gaps=False,
    )

    log_info(
        "KTC data pipeline complete",
        context={
            "datasets_processed": len(registry_updates),
            "valuation_issues": sum(1 for v in valuation_validations.values() if not v["is_valid"]),
        },
    )

    return {
        "snapshot_date": snapshot_date,
        "fetch_results": fetch_results,
        "valuation_validations": valuation_validations,
        "player_mapping_validation": player_mapping_validation,
        "registry_updates": registry_updates,
        "manifest_validation": manifest_validation,
    }


if __name__ == "__main__":
    # For local testing
    result = ktc_pipeline(
        datasets=["players", "picks"],
        market_scope="dynasty_1qb",
    )

    print("\n" + "=" * 70)
    print("KTC Data Pipeline Result")
    print("=" * 70)
    print(f"Snapshot date: {result['snapshot_date']}")
    print(f"Datasets processed: {len(result['registry_updates'])}")

    # Valuation validation summary
    valuation_issues = sum(1 for v in result["valuation_validations"].values() if not v["is_valid"])
    print(f"Valuation validation issues: {valuation_issues}")

    # Player mapping summary
    if result["player_mapping_validation"]:
        pmap = result["player_mapping_validation"]
        print(f"Player mapping coverage: {pmap.get('coverage_pct', 0):.1f}%")
        if pmap.get("top_unmapped"):
            print(f"Top unmapped players: {pmap['top_unmapped'][:3]}")

    print("=" * 70)
