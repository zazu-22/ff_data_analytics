"""FFanalytics projections loader.

Thin Python wrapper around R-based FFanalytics scraper.
Handles subprocess invocation, error handling, and GCS writes.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any


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
        result = subprocess.run(
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
            manifest = json.loads(manifest_line)
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
        raise RuntimeError(
            f"FFanalytics R script timed out after {e.timeout} seconds"
        ) from e

    except json.JSONDecodeError as e:
        # R script ran but didn't output valid JSON
        return {
            "dataset": "ffanalytics_projections",
            "season": season,
            "week": week,
            "status": "partial_success",
            "error": f"Could not parse manifest: {e}",
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
