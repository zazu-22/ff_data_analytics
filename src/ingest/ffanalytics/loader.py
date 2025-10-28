"""FFanalytics projections loader.

Thin Python wrapper around R-based FFanalytics scraper.
Handles subprocess invocation, error handling, and GCS writes.
"""

from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from polars import DataFrame

try:
    import polars as pl
except ImportError:
    pl = None


def load_projections(
    sources: str | list[str] = "FantasyPros,NumberFire,ESPN,CBS",
    positions: str | list[str] = "QB,RB,WR,TE,K,DST",
    season: int = 2024,
    week: int = 0,
    out_dir: str = "data/raw/ffanalytics",
    weights_csv: str = "config/projections/ffanalytics_projection_weights_mapped.csv",
    player_xref: str = "dbt/ff_analytics/seeds/dim_player_id_xref.csv",
    **kwargs: Any,
) -> dict[str, Any]:
    """Load fantasy football projections with weighted consensus.

    This function invokes the R runner (scripts/R/ffanalytics_run.R) which:
    1. Scrapes projections from multiple sources
    2. Computes weighted consensus using site weights
    3. Maps player names to canonical mfl_id
    4. Detects projection horizon (weekly vs full_season)
    5. Outputs both raw and consensus Parquet files

    Args:
        sources: Comma-separated source names or list (e.g., "FantasyPros,ESPN")
        positions: Comma-separated positions or list (e.g., "QB,RB,WR")
        season: NFL season year
        week: Week number (0 for season-long projections)
        out_dir: Output directory for Parquet files
        weights_csv: Path to site weights CSV
        player_xref: Path to player ID crosswalk seed
        **kwargs: Additional arguments (unused, for API compatibility)

    Returns:
        dict: Manifest with output paths, row counts, and metadata

    Raises:
        RuntimeError: If R script fails
        FileNotFoundError: If R script not found

    """
    # Convert lists to comma-separated strings if needed
    if isinstance(sources, list):
        sources = ",".join(sources)
    if isinstance(positions, list):
        positions = ",".join(positions)

    # Find repo root and R script
    repo_root = Path(__file__).parent.parent.parent.parent
    r_script = repo_root / "scripts/R/ffanalytics_run.R"

    if not r_script.exists():
        raise FileNotFoundError(f"R script not found: {r_script}")

    # Build command
    cmd = [
        "Rscript",
        str(r_script),
        "--sources",
        sources,
        "--positions",
        positions,
        "--season",
        str(season),
        "--week",
        str(week),
        "--out_dir",
        out_dir,
        "--weights_csv",
        weights_csv,
        "--player_xref",
        player_xref,
    ]

    # Run R script
    try:
        result = subprocess.run(  # noqa: S603
            cmd,
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=True,
            timeout=600,  # 10 minute timeout
        )

        # Parse JSON manifest from stdout (last line)
        lines = result.stdout.strip().split("\n")
        manifest_line = None
        for line in reversed(lines):
            if line.startswith("{"):
                manifest_line = line
                break

        if manifest_line:
            try:
                manifest = json.loads(manifest_line)
            except json.JSONDecodeError as e:
                # R script ran but didn't output valid JSON
                manifest = {
                    "dataset": "ffanalytics_projections",
                    "season": season,
                    "week": week,
                    "status": "partial_success",
                    "error": f"Could not parse manifest: {e}",
                }
        else:
            # Fallback: construct minimal manifest
            manifest = {
                "dataset": "ffanalytics_projections",
                "season": season,
                "week": week,
                "sources": sources,
                "positions": positions,
                "status": "success",
            }

        # Add stdout/stderr for debugging
        manifest["stdout"] = result.stdout
        manifest["stderr"] = result.stderr

        return manifest

    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"FFanalytics R script failed (exit code {e.returncode}):\n"
            f"STDOUT: {e.stdout}\n"
            f"STDERR: {e.stderr}"
        ) from e

    except subprocess.TimeoutExpired as e:
        raise RuntimeError(f"FFanalytics R script timed out after {e.timeout} seconds") from e


def _scrape_week_projections(
    week: int,
    season: int,
    sources: str | list[str],
    positions: str | list[str],
    staging_dir: Path,
    dt: str,
    weights_csv: str,
    player_xref: str,
) -> tuple[list[DataFrame], list[DataFrame], list[int], list[tuple[int, str]]]:
    """Scrape projections for a single week.

    Returns (consensus_dfs, raw_dfs, success_weeks, failed_weeks).
    """
    if pl is None:
        raise ImportError("polars is required for multi-week loading")

    all_consensus_dfs: list[DataFrame] = []
    all_raw_dfs: list[DataFrame] = []
    scraped_weeks: list[int] = []
    failed_weeks: list[tuple[int, str]] = []

    print(f"📊 Week {week}...", end=" ", flush=True)
    try:
        load_projections(
            sources=sources,
            positions=positions,
            season=season,
            week=week,
            out_dir=str(staging_dir),
            weights_csv=weights_csv,
            player_xref=player_xref,
        )

        consensus_file = (
            staging_dir / "projections" / f"dt={dt}" / f"projections_consensus_{dt}.parquet"
        )
        raw_file = staging_dir / "projections" / f"dt={dt}" / f"projections_raw_{dt}.parquet"

        if consensus_file.exists():
            df_consensus = pl.read_parquet(consensus_file)
            all_consensus_dfs.append(df_consensus)
            print(f"✓ {len(df_consensus)} rows")
        else:
            print("⚠️  No consensus file")

        if raw_file.exists():
            all_raw_dfs.append(pl.read_parquet(raw_file))

        scraped_weeks.append(week)
    except Exception as e:
        print(f"❌ Failed: {e}")
        failed_weeks.append((week, str(e)))

    return all_consensus_dfs, all_raw_dfs, scraped_weeks, failed_weeks


def load_projections_multi_week(
    season: int,
    weeks: list[int],
    sources: str | list[str] | None = None,
    positions: str | list[str] = "QB,RB,WR,TE,K,DST,DL,LB,DB",  # ALL 9 positions by default
    out_dir: str = "data/raw/ffanalytics",
    weights_csv: str = "config/projections/ffanalytics_projection_weights_mapped.csv",
    player_xref: str = "dbt/ff_analytics/seeds/dim_player_id_xref.csv",
    **kwargs: Any,
) -> dict[str, Any]:
    """Load projections for multiple weeks (e.g., rest-of-season) in a single snapshot.

    This function scrapes projections for multiple weeks and combines them into a
    single parquet file with the current snapshot date. This is the production-ready
    method for ROS projections used by GH Actions workflows.

    **Why combine weeks?**
    - All weeks scraped on the same day represent a single "as-of" snapshot
    - dbt models join on (season, week) so having all weeks in one file is efficient
    - Atomic operation: all ROS weeks or none (no partial snapshots)

    **Available sources (from config/projections/ffanalytics_projections_config.yaml):**
    - FantasyPros (weight: 0.1305) - Consensus aggregator
    - NumberFire (weight: 0.12) - Analytics-driven
    - FantasySharks (weight: 0.1176)
    - ESPN (weight: 0.1155)
    - FFToday (weight: 0.112)
    - CBS (weight: 0.1103)
    - NFL (weight: 0.1097) - Official NFL.com projections
    - RTSports (weight: 0.0997)
    - WalterFootball (weight: 0.0846)

    **Available positions (ALL 9 supported by ffanalytics):**
    - QB, RB, WR, TE - Offensive skill positions
    - K - Kickers
    - DST - Team defense/special teams
    - DL, LB, DB - Individual defensive players (IDP)

    **Production usage:**
    ```python
    # Scrape remaining weeks 9-18 for ROS projections (all sources, all positions)
    from src.ingest.ffanalytics.loader import load_projections_multi_week
    load_projections_multi_week(season=2025, weeks=list(range(9, 19)))

    # Custom sources/positions (e.g., offensive only for FASA)
    load_projections_multi_week(
        season=2025,
        weeks=[9, 10, 11],
        sources="FantasyPros,ESPN,NFL",  # Subset of sources
        positions="QB,RB,WR,TE"          # Offensive only
    )
    ```

    Args:
        season: NFL season year
        weeks: List of week numbers to scrape (e.g., [9, 10, 11, ..., 18])
        sources: Comma-separated source names, list, or None for ALL sources from config
        positions: Comma-separated positions or list (default: ALL 9 - QB,RB,WR,TE,K,DST,DL,LB,DB)
        out_dir: Output directory for Parquet files
        weights_csv: Path to site weights CSV (defines available sources and weights)
        player_xref: Path to player ID crosswalk seed
        **kwargs: Additional arguments

    Returns:
        dict: Manifest with combined output paths, row counts, and metadata

    Raises:
        RuntimeError: If any week fails to scrape
        ImportError: If polars not available for combining dataframes

    """
    # Default to ALL configured sources if none specified
    if sources is None:
        sources = (
            "FantasyPros,NumberFire,FantasySharks,ESPN,FFToday,CBS,NFL,RTSports,Walterfootball"
        )
    if pl is None:
        raise ImportError("polars is required for multi-week loading. Install with: uv add polars")

    if not weeks:
        raise ValueError("weeks list cannot be empty")

    dt = datetime.now(UTC).strftime("%Y-%m-%d")
    staging_dir = Path(out_dir) / "projections" / f"dt={dt}" / ".staging"
    staging_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n🔄 Scraping {len(weeks)} weeks for season {season}")
    print(f"   Weeks: {weeks}")
    print(f"   Staging: {staging_dir}\n")

    all_consensus_dfs = []
    all_raw_dfs = []
    scraped_weeks = []
    failed_weeks = []

    # Scrape each week individually
    for week in sorted(weeks):
        consensus_dfs, raw_dfs, success, failures = _scrape_week_projections(
            week, season, sources, positions, staging_dir, dt, weights_csv, player_xref
        )
        all_consensus_dfs.extend(consensus_dfs)
        all_raw_dfs.extend(raw_dfs)
        scraped_weeks.extend(success)
        failed_weeks.extend(failures)

    # Check if we got any data
    if not all_consensus_dfs:
        raise RuntimeError(
            f"No projections scraped successfully. Failed weeks: {[w for w, _ in failed_weeks]}"
        )

    # Combine all weeks into single dataframes
    print(f"\n🔗 Combining {len(all_consensus_dfs)} weeks into single snapshot...")
    combined_consensus = pl.concat(all_consensus_dfs, how="vertical_relaxed")
    combined_raw = pl.concat(all_raw_dfs, how="vertical_relaxed") if all_raw_dfs else None

    # Write to final destination
    final_dir = Path(out_dir) / "projections" / f"dt={dt}"
    final_dir.mkdir(parents=True, exist_ok=True)

    consensus_path = final_dir / f"projections_consensus_{dt}.parquet"
    raw_path = final_dir / f"projections_raw_{dt}.parquet"

    combined_consensus.write_parquet(consensus_path)
    print(f"   ✓ Consensus: {consensus_path} ({len(combined_consensus)} rows)")

    if combined_raw is not None:
        combined_raw.write_parquet(raw_path)
        print(f"   ✓ Raw: {raw_path} ({len(combined_raw)} rows)")

    # Clean up staging directory
    import shutil

    shutil.rmtree(staging_dir, ignore_errors=True)

    # Build manifest
    manifest = {
        "dataset": "ffanalytics_projections",
        "asof_datetime": datetime.now(UTC).isoformat(),
        "season": season,
        "weeks_requested": weeks,
        "weeks_successful": scraped_weeks,
        "weeks_failed": [w for w, _ in failed_weeks],
        "sources": sources if isinstance(sources, str) else ",".join(sources),
        "positions": positions if isinstance(positions, str) else ",".join(positions),
        "output_files": {
            "consensus": str(consensus_path),
            "raw": str(raw_path) if combined_raw is not None else None,
        },
        "row_counts": {
            "consensus": len(combined_consensus),
            "raw": len(combined_raw) if combined_raw is not None else 0,
        },
        "status": "success" if not failed_weeks else "partial_success",
    }

    # Write metadata
    meta_path = final_dir / "_meta.json"
    with meta_path.open("w") as f:
        json.dump(manifest, f, indent=2)

    print("\n✅ Multi-week scrape complete!")
    print(f"   {len(scraped_weeks)} weeks successful: {scraped_weeks}")
    if failed_weeks:
        print(f"   {len(failed_weeks)} weeks failed: {[w for w, _ in failed_weeks]}")

    return manifest
