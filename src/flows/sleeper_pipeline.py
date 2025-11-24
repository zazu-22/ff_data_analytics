"""Prefect flow for Sleeper league platform data ingestion with governance.

This flow handles Sleeper data ingestion with integrated governance:
- Roster size validations (thresholds in src/flows/config.py)
- Player mapping validation (thresholds in src/flows/config.py)
- Atomic snapshot registry updates

Architecture:
    1. Fetch Sleeper league data (rosters, users, players, fa_pool)
    2. Validate roster sizes (governance)
    3. Validate player mapping coverage (governance)
    4. Write Parquet files + manifests (already done by loader)
    5. Update snapshot registry atomically
    6. Validate manifests (governance)

Dependencies:
    - scripts/ingest/load_sleeper.py (existing loader)
    - src/flows/utils/validation.py (governance tasks)
    - src/flows/utils/notifications.py (logging)
    - src/flows/config.py (governance thresholds)

Architecture Decision:
    - This flow uses existing load_sleeper() from scripts/ingest/load_sleeper.py
    - Rationale: Sleeper loader is already well-tested and handles all datasets
    - Governance layer added AFTER ingestion for validation checks
    - Note: Transaction data not yet implemented in Sleeper API client

Production Hardening:
    - fetch_sleeper_data: 3 retries with 60s delay, 3min timeout (handles API transients)
"""

import sys
from datetime import datetime
from pathlib import Path

# Ensure src package is importable
repo_root = Path(__file__).parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

# Import existing Sleeper loader using importlib
import importlib.util  # noqa: E402

import polars as pl  # noqa: E402
from prefect import flow, task  # noqa: E402

from src.flows.config import ROSTER_SIZE_RANGES, get_player_mapping_threshold  # noqa: E402
from src.flows.utils.notifications import log_error, log_info, log_warning  # noqa: E402
from src.flows.utils.validation import validate_manifests_task  # noqa: E402

sleeper_loader_path = repo_root / "scripts" / "ingest" / "load_sleeper.py"
spec = importlib.util.spec_from_file_location("load_sleeper", sleeper_loader_path)
load_sleeper_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(load_sleeper_module)
load_sleeper = load_sleeper_module.load_sleeper


@task(
    name="fetch_sleeper_data",
    retries=3,
    retry_delay_seconds=60,
    timeout_seconds=180,
    tags=["external_api"],
)
def fetch_sleeper_data(
    league_id: str,
    output_dir: str = "data/raw/sleeper",
) -> dict:
    """Fetch Sleeper league data (rosters, users, players, fa_pool).

    Args:
        league_id: Sleeper league ID
        output_dir: Output directory for Parquet files

    Returns:
        Manifest dict with dataset results

    """
    log_info(
        "Fetching Sleeper league data",
        context={
            "league_id": league_id,
            "output_dir": output_dir,
        },
    )

    try:
        # Call existing loader
        manifest = load_sleeper(league_id=league_id, out_dir=output_dir)

        log_info(
            "Sleeper fetch complete",
            context={
                "datasets_fetched": len(manifest.get("datasets", {})),
                "league_id": league_id,
            },
        )

        return manifest

    except Exception as e:
        log_error(
            "Failed to fetch Sleeper data",
            context={"league_id": league_id, "error": str(e)},
        )


@task(name="validate_roster_sizes")
def validate_roster_sizes(
    manifest: dict,
    min_roster_size: int = 25,
    max_roster_size: int = 35,
) -> dict:
    """Validate that roster sizes are within expected league settings.

    Args:
        manifest: Manifest dict from load_sleeper
        min_roster_size: Minimum expected roster size (default: 25 for dynasty)
        max_roster_size: Maximum expected roster size (default: 35 for dynasty)

    Returns:
        Validation result dictionary

    """
    log_info(
        "Validating roster sizes",
        context={"min": min_roster_size, "max": max_roster_size},
    )

    # Extract roster path from manifest
    rosters_info = manifest.get("datasets", {}).get("rosters")
    if not rosters_info:
        log_warning(
            "No rosters dataset in manifest",
            context={"available_datasets": list(manifest.get("datasets", {}).keys())},
        )
        return {"is_valid": False, "reason": "No rosters dataset found"}

    rosters_path = rosters_info.get("path")
    if not rosters_path:
        log_error("Rosters dataset missing path", context={"rosters_info": rosters_info})

    # Read rosters data
    rosters_df = pl.read_parquet(rosters_path)

    # Calculate roster sizes (count players in each roster)
    # The 'players' column is a list of player IDs
    if "players" not in rosters_df.columns:
        log_error(
            "Missing 'players' column in rosters dataset",
            context={"columns": rosters_df.columns},
        )

    # Calculate roster sizes
    roster_sizes = rosters_df.select(
        pl.col("roster_id"),
        pl.col("players").list.len().alias("roster_size"),
    )

    # Validate ranges
    min_size = roster_sizes["roster_size"].min()
    max_size = roster_sizes["roster_size"].max()
    mean_size = roster_sizes["roster_size"].mean()

    anomalies = []

    if min_size < min_roster_size:
        anomalies.append(f"Roster too small: min={min_size} < threshold={min_roster_size}")
        log_warning(
            "Roster size below minimum",
            context={"min_size": min_size, "min_roster_size": min_roster_size},
        )

    if max_size > max_roster_size:
        anomalies.append(f"Roster too large: max={max_size} > threshold={max_roster_size}")
        log_warning(
            "Roster size above maximum",
            context={"max_size": max_size, "max_roster_size": max_roster_size},
        )

    # Report rosters outside expected range
    outliers = roster_sizes.filter(
        (pl.col("roster_size") < min_roster_size) | (pl.col("roster_size") > max_roster_size)
    )

    if len(outliers) > 0:
        log_warning(
            f"Found {len(outliers)} rosters outside expected size range",
            context={
                "outlier_count": len(outliers),
                "outlier_roster_ids": outliers["roster_id"].to_list(),
            },
        )

    result = {
        "is_valid": len(anomalies) == 0,
        "anomalies": anomalies,
        "min_size": int(min_size),
        "max_size": int(max_size),
        "mean_size": float(mean_size),
        "outlier_count": len(outliers),
        "total_rosters": len(roster_sizes),
    }

    if result["is_valid"]:
        log_info(
            "Roster sizes valid",
            context={"min": min_size, "max": max_size, "mean": f"{mean_size:.1f}"},
        )
    else:
        log_warning(
            "Roster size anomalies detected",
            context=result,
        )

    return result


@task(name="validate_sleeper_player_mapping")
def validate_sleeper_player_mapping(manifest: dict, min_coverage_pct: float = 85.0) -> dict:
    """Validate that Sleeper players map to dim_player_id_xref.

    Args:
        manifest: Manifest dict from load_sleeper
        min_coverage_pct: Minimum acceptable coverage percentage (default: 85%)

    Returns:
        Validation result dictionary with coverage stats and unmapped players

    Note:
        Sleeper may have more players than NFLverse (e.g., practice squad, recently retired)
        so we use a lower threshold (85%) vs KTC (90%)

    """
    log_info(
        "Validating player mapping coverage",
        context={"min_coverage_pct": min_coverage_pct},
    )

    # Extract players path from manifest
    players_info = manifest.get("datasets", {}).get("players")
    if not players_info:
        log_warning(
            "No players dataset in manifest",
            context={"available_datasets": list(manifest.get("datasets", {}).keys())},
        )
        return {"is_valid": False, "reason": "No players dataset found"}

    players_path = players_info.get("path")
    if not players_path:
        log_error("Players dataset missing path", context={"players_info": players_info})

    # Read Sleeper players
    sleeper_players = pl.read_parquet(players_path)

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
    xref = conn.execute(
        "SELECT DISTINCT sleeper_id FROM dim_player_id_xref WHERE sleeper_id IS NOT NULL"
    ).pl()
    conn.close()

    # Join to find unmapped players
    # Cast sleeper_id to string to match sleeper_player_id type
    sleeper_unique = sleeper_players.select("sleeper_player_id").unique()
    xref_ids = xref.select(pl.col("sleeper_id").cast(pl.Utf8).alias("xref_sleeper_id"))

    sleeper_with_mapping = sleeper_unique.join(
        xref_ids.with_columns(pl.col("xref_sleeper_id").alias("sleeper_player_id")),
        on="sleeper_player_id",
        how="left",
    )

    unmapped = sleeper_with_mapping.filter(pl.col("xref_sleeper_id").is_null())
    total_players = len(sleeper_with_mapping)
    mapped_count = total_players - len(unmapped)
    coverage_pct = (mapped_count / total_players * 100) if total_players > 0 else 0

    # Report top 10 unmapped players for investigation
    # Join back to get player names
    unmapped_with_names = unmapped.join(
        sleeper_players.select(["sleeper_player_id", "full_name"]),
        on="sleeper_player_id",
        how="left",
    )
    top_unmapped = (
        unmapped_with_names.head(10).select(["sleeper_player_id", "full_name"]).to_dicts()
    )

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
                "top_unmapped": [p["full_name"] for p in top_unmapped[:3]],
            },
        )

    return result


@task(name="update_snapshot_registry_sleeper")
def update_snapshot_registry(
    source: str,
    dataset: str,
    snapshot_date: str,
    row_count: int,
    notes: str = "",
) -> dict:
    """Update snapshot registry with new Sleeper snapshot metadata.

    This task atomically updates the registry, marking old snapshots as
    'superseded' and adding the new snapshot as 'current'.

    Args:
        source: Data source (e.g., 'sleeper')
        dataset: Dataset name (e.g., 'rosters', 'players', 'fa_pool', 'users')
        snapshot_date: Snapshot date (YYYY-MM-DD)
        row_count: Number of rows in snapshot
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
                    "coverage_start_season": None,  # Sleeper doesn't have season coverage
                    "coverage_end_season": None,
                    "row_count": row_count,
                    "notes": notes or "Sleeper league platform data",
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


@flow(name="sleeper_pipeline")
def sleeper_pipeline(
    league_id: str | None = None,
    output_dir: str = "data/raw/sleeper",
    snapshot_date: str | None = None,
    min_roster_size: int | None = None,
    max_roster_size: int | None = None,
) -> dict:
    """Prefect flow for Sleeper league platform data ingestion with governance.

    This flow handles Sleeper league data with integrated governance:
    - Roster size validations (25-35 players per team for dynasty)
    - Player mapping validation (>85% coverage against dim_player_id_xref)
    - Atomic snapshot registry updates

    Args:
        league_id: Sleeper league ID (defaults to SLEEPER_LEAGUE_ID env var)
        output_dir: Output directory for Parquet files
        snapshot_date: Snapshot date (defaults to today)
        min_roster_size: Minimum expected roster size (default: 25)
        max_roster_size: Maximum expected roster size (default: 35)

    Returns:
        Flow result with governance validation status

    """
    import os

    # Defaults
    if league_id is None:
        league_id = os.getenv("SLEEPER_LEAGUE_ID")
        if not league_id:
            log_error(
                "No league_id provided and SLEEPER_LEAGUE_ID env var not set",
                context={"action": "Set SLEEPER_LEAGUE_ID or pass league_id parameter"},
            )

    if snapshot_date is None:
        snapshot_date = datetime.now().strftime("%Y-%m-%d")

    # Apply config defaults for roster size validation
    if min_roster_size is None:
        min_roster_size = ROSTER_SIZE_RANGES["dynasty"]["min"]
    if max_roster_size is None:
        max_roster_size = ROSTER_SIZE_RANGES["dynasty"]["max"]

    log_info(
        "Starting Sleeper data pipeline",
        context={
            "league_id": league_id,
            "snapshot_date": snapshot_date,
            "min_roster_size": min_roster_size,
            "max_roster_size": max_roster_size,
        },
    )

    # Fetch Sleeper data
    manifest = fetch_sleeper_data(
        league_id=league_id,
        output_dir=output_dir,
    )

    # Governance: Validate roster sizes
    roster_validation = validate_roster_sizes(
        manifest,
        min_roster_size=min_roster_size,
        max_roster_size=max_roster_size,
    )

    if not roster_validation["is_valid"]:
        log_warning(
            "Roster size validation issues detected",
            context=roster_validation,
        )

    # Governance: Validate player mapping
    player_mapping_validation = validate_sleeper_player_mapping(
        manifest, min_coverage_pct=get_player_mapping_threshold("sleeper")
    )

    if not player_mapping_validation.get("is_valid", True):
        log_warning(
            "Player mapping coverage below threshold",
            context=player_mapping_validation,
        )

    # Update snapshot registry for each dataset
    registry_updates = {}
    datasets = manifest.get("datasets", {})

    for dataset_name, dataset_info in datasets.items():
        row_count = dataset_info.get("rows", 0)

        registry_update = update_snapshot_registry(
            source="sleeper",
            dataset=dataset_name,
            snapshot_date=snapshot_date,
            row_count=row_count,
            notes=f"Sleeper league {league_id}",
        )

        registry_updates[dataset_name] = registry_update

    # Governance: Validate manifests
    manifest_validation = validate_manifests_task(
        sources=["sleeper"],
        fail_on_gaps=False,
    )

    log_info(
        "Sleeper data pipeline complete",
        context={
            "datasets_processed": len(registry_updates),
            "roster_issues": not roster_validation["is_valid"],
        },
    )

    return {
        "snapshot_date": snapshot_date,
        "league_id": league_id,
        "manifest": manifest,
        "roster_validation": roster_validation,
        "player_mapping_validation": player_mapping_validation,
        "registry_updates": registry_updates,
        "manifest_validation": manifest_validation,
    }


if __name__ == "__main__":
    import os

    # For local testing
    league_id = os.getenv("SLEEPER_LEAGUE_ID", "1230330435511275520")

    result = sleeper_pipeline(
        league_id=league_id,
        min_roster_size=25,
        max_roster_size=35,
    )

    print("\n" + "=" * 70)
    print("Sleeper Data Pipeline Result")
    print("=" * 70)
    print(f"League ID: {result['league_id']}")
    print(f"Snapshot date: {result['snapshot_date']}")
    print(f"Datasets processed: {len(result['registry_updates'])}")

    # Roster validation summary
    roster_val = result["roster_validation"]
    print(f"Roster validation: {'PASS' if roster_val['is_valid'] else 'FAIL'}")
    roster_range = f"{roster_val['min_size']}-{roster_val['max_size']}"
    print(f"  Roster size range: {roster_range} (mean: {roster_val['mean_size']:.1f})")

    # Player mapping summary
    if result["player_mapping_validation"]:
        pmap = result["player_mapping_validation"]
        if "coverage_pct" in pmap:
            print(f"Player mapping coverage: {pmap.get('coverage_pct', 0):.1f}%")
            if pmap.get("top_unmapped"):
                print(f"Top unmapped players: {[p['full_name'] for p in pmap['top_unmapped'][:3]]}")

    print("=" * 70)
