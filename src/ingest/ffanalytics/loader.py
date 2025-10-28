"""FFanalytics projections loader.

Thin Python wrapper around R-based FFanalytics scraper.
Handles subprocess invocation, error handling, and GCS writes.

Production Functions:
    - load_projections_ros: Auto-detect current week and scrape remaining season
    (default for automation)
    - load_projections_multi_week: Manual multi-week scraping with explicit week list
    - load_projections: Single-week scraping (legacy/manual use)
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

try:
    import duckdb
except ImportError:
    duckdb = None

# ============================================================================
# Constants - Define once, use everywhere
# ============================================================================

# All 9 sources configured in ffanalytics_projection_weights_mapped.csv
DEFAULT_SOURCES = "FantasyPros,NumberFire,FantasySharks,ESPN,FFToday,CBS,NFL,RTSports,Walterfootball"

# All 9 positions supported by ffanalytics package
DEFAULT_POSITIONS = "QB,RB,WR,TE,K,DST,DL,LB,DB"

# Default file paths (relative to repo root)
DEFAULT_OUT_DIR = "data/raw/ffanalytics"
DEFAULT_WEIGHTS_CSV = "config/projections/ffanalytics_projection_weights_mapped.csv"
DEFAULT_PLAYER_XREF = "dbt/ff_analytics/seeds/dim_player_id_xref.csv"

# Fantasy season constants
FANTASY_SEASON_END_WEEK = 17  # Week 18 excluded (teams rest starters)


# ============================================================================
# Helper Functions - Extract common patterns
# ============================================================================

def _get_repo_root() -> Path:
    """Get repository root directory (4 levels up from this file)."""
    return Path(__file__).parent.parent.parent.parent


def _get_current_season() -> int:
    """Get current NFL season year."""
    return datetime.now(UTC).year


def _normalize_sources(sources: str | list[str] | None) -> str:
    """Normalize sources to comma-separated string, defaulting to ALL sources."""
    if sources is None:
        return DEFAULT_SOURCES
    if isinstance(sources, list):
        return ",".join(sources)
    return sources


def _normalize_positions(positions: str | list[str]) -> str:
    """Normalize positions to comma-separated string."""
    if isinstance(positions, list):
        return ",".join(positions)
    return positions


def _parse_manifest_from_stdout(
    stdout: str, season: int, week: int, sources: str
) -> dict[str, Any]:
    """Parse JSON manifest from R script stdout.

    Args:
        stdout: R script stdout containing JSON manifest
        season: Season year for fallback manifest
        week: Week number for fallback manifest
        sources: Sources used for fallback manifest

    Returns:
        dict: Parsed manifest or fallback minimal manifest
    """
    # Parse JSON manifest from stdout (last line starting with "{")
    lines = stdout.strip().split("\n")
    manifest_line = None
    for line in reversed(lines):
        if line.startswith("{"):
            manifest_line = line
            break

    if manifest_line:
        try:
            return json.loads(manifest_line)
        except json.JSONDecodeError as e:
            # R script ran but didn't output valid JSON
            return {
                "dataset": "ffanalytics_projections",
                "season": season,
                "week": week,
                "status": "partial_success",
                "error": f"Could not parse manifest: {e}",
            }
    else:
        # Fallback: construct minimal manifest
        return {
            "dataset": "ffanalytics_projections",
            "season": season,
            "week": week,
            "sources": sources,
            "status": "success",
        }


# ============================================================================
# Main Loader Functions
# ============================================================================

def load_projections(
    sources: str | list[str] | None = None,
    positions: str | list[str] = DEFAULT_POSITIONS,
    season: int | None = None,
    week: int = 0,
    out_dir: str = DEFAULT_OUT_DIR,
    weights_csv: str = DEFAULT_WEIGHTS_CSV,
    player_xref: str = DEFAULT_PLAYER_XREF,
    **kwargs: Any,
) -> dict[str, Any]:
    """Load fantasy football projections with weighted consensus (single week).

    **NOTE**: This is the base single-week loader used internally by load_projections_multi_week
    and load_projections_ros. For production use, prefer load_projections_ros() for automatic
    rest-of-season scraping.

    This function invokes the R runner (scripts/R/ffanalytics_run.R) which:
    1. Scrapes projections from multiple sources
    2. Computes weighted consensus using site weights
    3. Maps player names to canonical mfl_id
    4. Detects projection horizon (weekly vs full_season)
    5. Outputs both raw and consensus Parquet files

    Args:
        sources: Comma-separated source names, list, or None for ALL sources (default: ALL)
        positions: Comma-separated positions or list (default: ALL 9 positions)
        season: NFL season year (default: current year)
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
    # Normalize inputs using helper functions
    sources = _normalize_sources(sources)
    positions = _normalize_positions(positions)
    season = season if season is not None else _get_current_season()

    # Find R script
    repo_root = _get_repo_root()
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
        manifest = _parse_manifest_from_stdout(result.stdout, season, week, sources)

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
    positions: str | list[str] = DEFAULT_POSITIONS,
    out_dir: str = DEFAULT_OUT_DIR,
    weights_csv: str = DEFAULT_WEIGHTS_CSV,
    player_xref: str = DEFAULT_PLAYER_XREF,
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
    # Normalize inputs
    sources = _normalize_sources(sources)
    positions = _normalize_positions(positions)

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


def _get_current_week(season: int, duckdb_path: str | None = None) -> int:
    """Determine current fantasy week from dim_schedule.

    Returns the week after the last completed week (games before today).
    If dim_schedule unavailable or no weeks completed, returns 1.

    Args:
        season: NFL season year
        duckdb_path: Path to DuckDB database (default: dbt/ff_analytics/target/dev.duckdb)

    Returns:
        int: Current fantasy week number (1-17)

    """
    if duckdb is None:
        print("⚠️  DuckDB not available, defaulting to week 1")
        return 1

    if duckdb_path is None:
        # Default to dbt project database
        repo_root = _get_repo_root()
        duckdb_path = str(repo_root / "dbt" / "ff_analytics" / "target" / "dev.duckdb")

    try:
        conn = duckdb.connect(duckdb_path, read_only=True)
        result = conn.execute(
            """
            SELECT MAX(week) as max_completed_week
            FROM dim_schedule
            WHERE season = ?
              AND CAST(game_date AS DATE) < CURRENT_DATE
            """,
            [season],
        ).fetchone()
        conn.close()

        if result and result[0] is not None:
            max_completed = result[0]
            current_week = max_completed + 1
            print(f"📅 Detected: Week {max_completed} completed, loading from week {current_week}")
            return current_week
        else:
            print(f"⚠️  No completed weeks found for season {season}, defaulting to week 1")
            return 1

    except Exception as e:
        print(f"⚠️  Could not query dim_schedule: {e}, defaulting to week 1")
        return 1


def load_projections_ros(
    season: int | None = None,
    start_week: int | None = None,
    end_week: int = FANTASY_SEASON_END_WEEK,
    sources: str | list[str] | None = None,
    positions: str | list[str] = DEFAULT_POSITIONS,
    out_dir: str = DEFAULT_OUT_DIR,
    weights_csv: str = DEFAULT_WEIGHTS_CSV,
    player_xref: str = DEFAULT_PLAYER_XREF,
    duckdb_path: str | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Load rest-of-season projections with auto-detection of current week.

    This is the PRODUCTION-READY function for automated workflows (GitHub Actions).
    It automatically determines the current week from dim_schedule and scrapes
    remaining weeks through week 17 (fantasy playoff cutoff).

    **Why week 17 and not 18?**
    Week 18 is excluded from fantasy leagues because NFL teams often rest starters
    when playoff seeding is locked in, making projections unreliable.

    **Auto-detection logic:**
    1. Query dim_schedule to find max completed week (games before today)
    2. Current week = completed week + 1
    3. Load weeks [current_week ... 17]
    4. If dim_schedule unavailable, defaults to start_week=1 or user-provided value

    **Usage examples:**
    ```python
    # Fully automatic (recommended for GH Actions)
    from src.ingest.ffanalytics.loader import load_projections_ros
    load_projections_ros()  # Auto-detects season, current week, loads through week 17

    # Manual override for specific season
    load_projections_ros(season=2025)  # Auto-detect current week for 2025

    # Manual override for testing
    load_projections_ros(season=2025, start_week=10, end_week=12)  # Weeks 10-12 only

    # Custom sources/positions (e.g., FASA offensive-only)
    load_projections_ros(
        sources="FantasyPros,ESPN,NFL",
        positions="QB,RB,WR,TE"  # No K, DST, IDP
    )
    ```

    **GitHub Actions integration:**
    ```yaml
    - name: Load ROS projections
      run: |
        uv run python -c "from src.ingest.ffanalytics.loader import load_projections_ros;
        load_projections_ros()"
    ```

    Args:
        season: NFL season year (default: current year)
        start_week: Starting week (default: auto-detect from dim_schedule)
        end_week: Ending week (default: 17, fantasy playoff cutoff)
        sources: Comma-separated source names, list, or None for ALL sources
        positions: Comma-separated positions (default: ALL 9 - QB,RB,WR,TE,K,DST,DL,LB,DB)
        out_dir: Output directory for Parquet files
        weights_csv: Path to site weights CSV
        player_xref: Path to player ID crosswalk seed
        duckdb_path: Path to DuckDB database for week detection (default: dbt target)
        **kwargs: Additional arguments passed to load_projections_multi_week

    Returns:
        dict: Manifest with combined output paths, row counts, and metadata

    Raises:
        RuntimeError: If scraping fails
        ValueError: If start_week > end_week

    """
    # Normalize inputs
    season = season if season is not None else _get_current_season()
    if season == _get_current_season() and season is None:
        print(f"📅 Season not specified, defaulting to {season}")

    # Auto-detect current week if not specified
    if start_week is None:
        start_week = _get_current_week(season, duckdb_path)

    # Validate week range
    if start_week > end_week:
        raise ValueError(f"start_week ({start_week}) cannot be greater than end_week ({end_week})")

    if start_week > FANTASY_SEASON_END_WEEK:
        print(f"⚠️  start_week ({start_week}) is beyond fantasy season (week {FANTASY_SEASON_END_WEEK}), nothing to load")
        return {
            "dataset": "ffanalytics_projections",
            "season": season,
            "status": "skipped",
            "reason": f"start_week beyond fantasy season cutoff (week {FANTASY_SEASON_END_WEEK})",
        }

    # Build week list (inclusive)
    weeks = list(range(start_week, end_week + 1))

    print(f"\n🏈 Loading ROS projections for season {season}")
    print(f"   Weeks: {start_week}-{end_week} ({len(weeks)} weeks)")
    print(f"   Sources: {sources if sources else 'ALL configured sources'}")
    print(f"   Positions: {positions}")

    # Delegate to multi-week loader
    return load_projections_multi_week(
        season=season,
        weeks=weeks,
        sources=sources,
        positions=positions,
        out_dir=out_dir,
        weights_csv=weights_csv,
        player_xref=player_xref,
        **kwargs,
    )
