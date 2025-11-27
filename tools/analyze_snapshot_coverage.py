"""tools/analyze_snapshot_coverage.py.

Analyze snapshot coverage for any data source to understand what data is in each snapshot.

This tool analyzes Parquet files organized in date-partitioned directories (dt=YYYY-MM-DD)
and generates reports showing data coverage, freshness, entity counts, row deltas, coverage
gaps, and player mapping rates.

Usage:
    # Analyze nflverse (default)
    python tools/analyze_snapshot_coverage.py

    # Analyze a different source
    python tools/analyze_snapshot_coverage.py --source data/raw/sleeper

    # Analyze specific datasets only
    python tools/analyze_snapshot_coverage.py --datasets weekly snap_counts

    # Report row deltas between snapshots
    python tools/analyze_snapshot_coverage.py --report-deltas

    # Detect coverage gaps and check player mappings
    python tools/analyze_snapshot_coverage.py --detect-gaps --check-mappings

    # Custom output directory
    python tools/analyze_snapshot_coverage.py --out-dir data/review/custom
"""

import argparse
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import duckdb
import polars as pl

# Delta thresholds for anomaly detection (configurable)
DELTA_THRESHOLDS = {
    "nflverse": {
        "weekly": {"min_pct": -5, "max_pct": 20},  # Allow 20% growth during season
        "snap_counts": {"min_pct": -5, "max_pct": 20},
    },
    "commissioner": {
        "roster": {"min_pct": -10, "max_pct": 30},  # Trades can cause swings
        "transactions": {"min_pct": 0, "max_pct": 100},  # Cumulative, always grows
        "cap_space": {"min_pct": -10, "max_pct": 10},
        "contracts_active": {"min_pct": -10, "max_pct": 30},
        "contracts_cut": {"min_pct": 0, "max_pct": 100},  # Cumulative
        "draft_picks": {"min_pct": -10, "max_pct": 30},
        "draft_pick_conditions": {"min_pct": -20, "max_pct": 50},
    },
    "ktc": {
        "players": {"min_pct": -10, "max_pct": 10},  # Valuations fairly stable
    },
    "sleeper": {
        "rosters": {"min_pct": -10, "max_pct": 10},
        "transactions": {"min_pct": 0, "max_pct": 100},  # Cumulative
    },
}


def load_snapshot_registry(registry_path: Path | None = None) -> pl.DataFrame:
    """Load the snapshot registry CSV file.

    Args:
        registry_path: Optional path to registry file. Defaults to standard location.

    Returns:
        Polars DataFrame with snapshot registry data

    """
    if registry_path is None:
        registry_path = Path("dbt/ff_data_transform/seeds/snapshot_registry.csv")

    if not registry_path.exists():
        raise FileNotFoundError(f"Snapshot registry not found: {registry_path}")

    return pl.read_csv(registry_path)


def calculate_deltas(source: str, dataset: str, registry_df: pl.DataFrame) -> dict:
    """Calculate row count deltas between current and previous snapshots.

    Args:
        source: Data source (e.g., 'nflverse')
        dataset: Dataset within source (e.g., 'weekly')
        registry_df: Snapshot registry DataFrame

    Returns:
        Dictionary with delta statistics

    """
    # Filter registry to source/dataset
    snapshots = (
        registry_df.filter((pl.col("source") == source) & (pl.col("dataset") == dataset))
        .sort("snapshot_date", descending=True)
        .select(["snapshot_date", "row_count"])
    )

    if len(snapshots) < 2:
        return {"error": "Need at least 2 snapshots for delta calculation"}

    current = snapshots.row(0, named=True)
    previous = snapshots.row(1, named=True)

    current_count = current["row_count"] if current["row_count"] is not None else 0
    previous_count = previous["row_count"] if previous["row_count"] is not None else 0

    delta = current_count - previous_count
    pct_change = (delta / previous_count * 100) if previous_count > 0 else 0

    # Get thresholds for this source/dataset (with fallback defaults)
    thresholds = DELTA_THRESHOLDS.get(source, {}).get(dataset, {"min_pct": -50, "max_pct": 50})

    # Anomaly detection
    is_anomaly = pct_change < thresholds["min_pct"] or pct_change > thresholds["max_pct"]
    is_data_loss = delta < 0
    # Stagnant if very small delta for sources that should be growing
    is_stagnant = abs(delta) < 10 and source == "nflverse" and dataset in ["weekly", "snap_counts"]

    return {
        "source": source,
        "dataset": dataset,
        "current_snapshot": str(current["snapshot_date"]),
        "current_count": current_count,
        "previous_snapshot": str(previous["snapshot_date"]),
        "previous_count": previous_count,
        "delta": delta,
        "pct_change": round(pct_change, 2),
        "is_anomaly": is_anomaly,
        "is_data_loss": is_data_loss,
        "is_stagnant": is_stagnant,
        "thresholds": thresholds,
    }


def _detect_weeks_gaps_for_season(
    season: int, season_data: pl.DataFrame, current_year: int
) -> list[dict]:
    """Detect missing weeks for a specific season.

    Args:
        season: Season to check
        season_data: DataFrame filtered to this season
        current_year: Current year (to skip incomplete seasons)

    Returns:
        List of gap dictionaries

    """
    gaps = []
    weeks_present = set(season_data["week"].unique().to_list())

    # Expected weeks (1-18 for NFL regular season)
    # Note: Some datasets may have playoff weeks 19-22
    expected_weeks = set(range(1, 19))
    missing_weeks = expected_weeks - weeks_present

    # Only flag as gaps if season is complete (not current or future year)
    is_current_or_future = season >= current_year
    if missing_weeks and not is_current_or_future:
        for week in sorted(missing_weeks):
            gaps.append({"season": season, "week": week, "type": "missing_week"})

    return gaps


def _check_has_baseline(registry_df: pl.DataFrame, source: str, dataset: str) -> bool:
    """Check if a baseline snapshot exists for this source/dataset.

    Args:
        registry_df: Snapshot registry
        source: Data source
        dataset: Dataset name

    Returns:
        True if baseline snapshot exists

    """
    baseline_count = len(
        registry_df.filter(
            (pl.col("source") == source)
            & (pl.col("dataset") == dataset)
            & (pl.col("status").is_in(["historical", "baseline"]))
        )
    )
    return baseline_count > 0


def detect_coverage_gaps(
    source: str,
    dataset: str,
    snapshot_path: Path,
    registry_df: pl.DataFrame,
    snapshot_dt: str,
) -> dict:
    """Detect season/week coverage gaps in snapshot data.

    Args:
        source: Data source (e.g., 'nflverse')
        dataset: Dataset within source (e.g., 'weekly')
        snapshot_path: Path to snapshot Parquet files
        registry_df: Snapshot registry for expected coverage
        snapshot_dt: Date partition of this snapshot (e.g., '2025-11-16')

    Returns:
        Dictionary with gap analysis

    """
    try:
        # Read snapshot data
        df = pl.read_parquet(snapshot_path)

        # Check if data has season/week columns
        if "season" not in df.columns or "week" not in df.columns:
            return {"error": "No season/week columns in data"}

        # Get registry entry for THIS specific snapshot
        this_snapshot = registry_df.filter(
            (pl.col("source") == source)
            & (pl.col("dataset") == dataset)
            & (pl.col("snapshot_date") == snapshot_dt)
        ).select(["coverage_start_season", "coverage_end_season", "status"])

        if len(this_snapshot) == 0:
            return {"error": f"Snapshot {snapshot_dt} not found in registry"}

        snapshot_info = this_snapshot.row(0, named=True)
        start_season = snapshot_info["coverage_start_season"]
        end_season = snapshot_info["coverage_end_season"]
        status = snapshot_info["status"]

        if start_season is None or end_season is None:
            return {"error": "Missing coverage season info in registry"}

        # Check if there's a baseline snapshot available
        has_baseline = _check_has_baseline(registry_df, source, dataset)

        # Get actual seasons present in this snapshot
        actual_seasons = set(df["season"].unique().to_list())

        # Get current date to determine in-progress season
        current_year = datetime.now().year

        # Detect missing weeks
        gaps = []
        for season in range(start_season, end_season + 1):
            # Skip if this is a current snapshot with baseline_plus_latest strategy
            # (expected to only have current season, baseline has historical)
            if status == "current" and has_baseline and season < current_year:
                continue

            # Skip if season not in actual data
            if season not in actual_seasons:
                # Only flag missing season if it's not current/future year
                if season < current_year:
                    gaps.append({"season": season, "week": None, "type": "missing_season"})
                continue

            season_data = df.filter(pl.col("season") == season)
            season_gaps = _detect_weeks_gaps_for_season(season, season_data, current_year)
            gaps.extend(season_gaps)

        return {
            "source": source,
            "dataset": dataset,
            "snapshot_dt": snapshot_dt,
            "status": status,
            "has_baseline": has_baseline,
            "gaps": gaps,
            "gap_count": len(gaps),
            "coverage_seasons": f"{start_season}-{end_season}",
            "strategy_note": (
                "Uses baseline_plus_latest strategy - historical data in baseline snapshot"
                if status == "current" and has_baseline
                else None
            ),
        }

    except Exception as e:
        return {"error": f"Failed to detect gaps: {e}"}


def _determine_join_column(id_col: str | None) -> str | None:
    """Determine which xref column to join on based on the ID column.

    Args:
        id_col: Player ID column name from snapshot

    Returns:
        Join column name to use with dim_player_id_xref, or None if undeterminable

    """
    if not id_col:
        return None

    # Direct mappings
    if id_col in ("gsis_id", "mfl_id", "pfr_player_id"):
        return id_col

    # For generic player_id, try gsis_id
    if id_col == "player_id":
        return "gsis_id"

    return None


def _find_player_id_columns(
    snapshot_df: pl.DataFrame,
) -> tuple[str | None, str | None]:
    """Find player ID and name columns in the snapshot.

    Args:
        snapshot_df: Snapshot DataFrame

    Returns:
        Tuple of (id_col, name_col) or (None, None)

    """
    player_id_cols = ["player_id", "gsis_id", "pfr_player_id", "mfl_id"]
    player_name_cols = ["player_name", "player_display_name", "player"]

    id_col = None
    for col in player_id_cols:
        if col in snapshot_df.columns:
            id_col = col
            break

    name_col = None
    for col in player_name_cols:
        if col in snapshot_df.columns:
            name_col = col
            break

    return id_col, name_col


def _get_unmapped_players_query(
    id_col_safe: str, join_col_safe: str, name_col_safe: str | None
) -> str:
    """Build query to get unmapped players for the given columns.

    Args:
        id_col_safe: Validated and quoted ID column name
        join_col_safe: Validated and quoted join column name
        name_col_safe: Validated and quoted name column (optional)

    Returns:
        SQL query string

    """
    select_cols = f"s.{id_col_safe}"
    if name_col_safe:
        select_cols = f"s.{id_col_safe}, s.{name_col_safe}"

    return f"""
        SELECT {select_cols}
        FROM sample_players s
        LEFT JOIN dim_player_id_xref x ON s.{id_col_safe} = x.{join_col_safe}
        WHERE x.mfl_id IS NULL
        ORDER BY s.{id_col_safe}
        LIMIT 10
    """  # noqa: S608


def calculate_mapping_rate(
    snapshot_path: Path,
    xref_path: str = "dbt/ff_data_transform/target/dev.duckdb",
) -> dict:
    """Calculate player mapping rate to dim_player_id_xref.

    Args:
        snapshot_path: Path to snapshot Parquet files
        xref_path: Path to DuckDB database with dim_player_id_xref

    Returns:
        Dictionary with mapping statistics

    """
    try:
        # Read snapshot
        snapshot_df = pl.read_parquet(snapshot_path)

        # Find player ID and name columns
        id_col, name_col = _find_player_id_columns(snapshot_df)

        if not id_col and not name_col:
            return {"error": "No player identification columns found"}

        # Get distinct players
        select_cols = [c for c in [id_col, name_col] if c is not None]
        sample_players = snapshot_df.select(select_cols).unique()

        if len(sample_players) == 0:
            return {
                "total_players": 0,
                "mapped_players": 0,
                "mapping_rate": 100.0,
                "unmapped_sample": [],
            }

        # Connect to DuckDB and join to xref
        xref_db_path = Path(xref_path)
        if not xref_db_path.exists():
            return {"error": f"DuckDB file not found: {xref_path}"}

        conn = duckdb.connect(str(xref_db_path), read_only=True)

        # Determine which column to join on
        join_col = _determine_join_column(id_col)

        if join_col:
            # Validate column names before using in SQL
            id_col_safe = _validate_column_name(id_col)
            join_col_safe = _validate_column_name(join_col)

            # Column names are validated and quoted by _validate_column_name()
            # which checks they contain only alphanumeric/underscore and adds quotes.
            # The column names come from schema introspection (df.columns), not user
            # input, so they are inherently safe. Using noqa to suppress false positive.
            mapped_count = conn.execute(
                f"""
                SELECT COUNT(DISTINCT s.{id_col_safe})
                FROM sample_players s
                JOIN dim_player_id_xref x ON s.{id_col_safe} = x.{join_col_safe}
            """  # noqa: S608
            ).fetchone()[0]

            # Get top unmapped players
            name_col_safe = None
            if name_col:
                name_col_safe = _validate_column_name(name_col)

            unmapped_query = _get_unmapped_players_query(id_col_safe, join_col_safe, name_col_safe)
            unmapped_players = conn.execute(unmapped_query).fetchall()
        else:
            # Cannot join without ID column
            mapped_count = 0
            unmapped_players = []

        conn.close()

        total_count = len(sample_players)
        mapping_rate = (mapped_count / total_count * 100) if total_count > 0 else 0

        unmapped_sample = []
        if name_col:
            unmapped_sample = [
                {"player_id": str(p[0]), "player_name": str(p[1])} for p in unmapped_players
            ]
        else:
            unmapped_sample = [{"player_id": str(p[0])} for p in unmapped_players]

        return {
            "total_players": total_count,
            "mapped_players": mapped_count,
            "mapping_rate": round(mapping_rate, 2),
            "unmapped_sample": unmapped_sample,
            "id_column_used": id_col,
            "join_column_used": join_col,
        }

    except Exception as e:
        return {"error": f"Failed to calculate mapping rate: {e}"}


def _sanitize_path_for_sql(parquet_path: Path) -> str:
    """Sanitize a file path for safe use in SQL queries.

    Args:
        parquet_path: Path to sanitize

    Returns:
        Escaped string path safe for SQL

    Raises:
        ValueError: If path is invalid or doesn't exist

    """
    # Resolve to absolute path and validate
    resolved = parquet_path.resolve()
    if not resolved.exists():
        raise ValueError(f"Path does not exist: {parquet_path}")
    if not resolved.is_file():
        raise ValueError(f"Path is not a file: {parquet_path}")

    # Convert to string and escape single quotes (SQL standard)
    path_str = str(resolved)
    # Escape single quotes by doubling them
    escaped = path_str.replace("'", "''")

    return escaped


def _validate_column_name(col_name: str) -> str:
    """Validate and quote a column name for safe SQL use.

    Args:
        col_name: Column name to validate

    Returns:
        Quoted column name safe for SQL

    Raises:
        ValueError: If column name contains invalid characters

    """
    # Only allow alphanumeric, underscore, and basic identifiers
    if not all(c.isalnum() or c == "_" for c in col_name):
        raise ValueError(f"Invalid column name: {col_name}")
    return f'"{col_name}"'


def _get_basic_file_info(
    conn: duckdb.DuckDBPyConnection, parquet_path: Path
) -> tuple[int, list[str]]:
    """Get row count and column names from a Parquet file."""
    safe_path = _sanitize_path_for_sql(parquet_path)
    # Path is sanitized and validated by _sanitize_path_for_sql
    result = conn.execute(f"""
        SELECT COUNT(*) as row_count
        FROM read_parquet('{safe_path}')
    """).fetchone()  # noqa: S608
    row_count = result[0] if result else 0

    schema_info = conn.execute(f"""
        DESCRIBE SELECT * FROM read_parquet('{safe_path}') LIMIT 1
    """).fetchall()  # noqa: S608
    columns = [col[0] for col in schema_info]

    return row_count, columns


def _analyze_season_coverage(
    conn: duckdb.DuckDBPyConnection, parquet_path: Path, columns: list[str]
) -> dict[str, Any]:
    """Analyze season coverage metrics."""
    metrics: dict[str, Any] = {}

    if "season" not in columns:
        return metrics

    safe_path = _sanitize_path_for_sql(parquet_path)
    if "week" in columns:
        # Path is sanitized and validated by _sanitize_path_for_sql
        season_info = conn.execute(f"""
            SELECT
                MIN(season) as min_season,
                MAX(season) as max_season,
                COUNT(DISTINCT season) as distinct_seasons,
                COUNT(DISTINCT week) as distinct_weeks
            FROM read_parquet('{safe_path}')
            WHERE season IS NOT NULL
        """).fetchone()  # noqa: S608
    else:
        # Path is sanitized and validated by _sanitize_path_for_sql
        season_info = conn.execute(f"""
            SELECT
                MIN(season) as min_season,
                MAX(season) as max_season,
                COUNT(DISTINCT season) as distinct_seasons,
                NULL as distinct_weeks
            FROM read_parquet('{safe_path}')
            WHERE season IS NOT NULL
        """).fetchone()  # noqa: S608

    if season_info:
        metrics["season_min"] = season_info[0]
        metrics["season_max"] = season_info[1]
        metrics["distinct_seasons"] = season_info[2]
        if season_info[3] is not None:
            metrics["distinct_weeks"] = season_info[3]

    return metrics


def _analyze_week_coverage(
    conn: duckdb.DuckDBPyConnection, parquet_path: Path, columns: list[str]
) -> dict[str, Any]:
    """Analyze week coverage metrics."""
    metrics: dict[str, Any] = {}

    if "week" not in columns or "season" not in columns:
        return metrics

    safe_path = _sanitize_path_for_sql(parquet_path)
    # Path is sanitized and validated by _sanitize_path_for_sql
    week_info = conn.execute(f"""
        SELECT
            MIN(week) as min_week,
            MAX(week) as max_week
        FROM read_parquet('{safe_path}')
        WHERE week IS NOT NULL AND season IS NOT NULL
    """).fetchone()  # noqa: S608

    if week_info:
        metrics["week_min"] = week_info[0]
        metrics["week_max"] = week_info[1]

    return metrics


def _count_distinct_entities(
    conn: duckdb.DuckDBPyConnection, parquet_path: Path, columns: list[str]
) -> dict[str, Any]:
    """Count distinct entities (players, teams, games) based on ID columns."""
    metrics: dict[str, Any] = {}

    entity_columns = {
        "player_id": "distinct_players",
        "pfr_player_id": "distinct_players_pfr",
        "gsis_id": "distinct_players_gsis",
        "mfl_id": "distinct_players_mfl",
        "game_id": "distinct_games",
        "team": "distinct_teams",
    }

    safe_path = _sanitize_path_for_sql(parquet_path)
    for col_name, metric_key in entity_columns.items():
        if col_name in columns:
            # Path is sanitized and validated by _sanitize_path_for_sql
            # Column name is from schema introspection, not user input
            result = conn.execute(f"""
                SELECT COUNT(DISTINCT {col_name})
                FROM read_parquet('{safe_path}')
                WHERE {col_name} IS NOT NULL
            """).fetchone()  # noqa: S608
            if result:
                metrics[metric_key] = result[0]

    return metrics


def _get_season_week_breakdown(
    conn: duckdb.DuckDBPyConnection, parquet_path: Path, columns: list[str]
) -> list[dict[str, Any]]:
    """Get season/week breakdown if available."""
    if "season" not in columns or "week" not in columns:
        return []

    safe_path = _sanitize_path_for_sql(parquet_path)
    # Path is sanitized and validated by _sanitize_path_for_sql
    season_week_breakdown = conn.execute(f"""
        SELECT
            season,
            COUNT(DISTINCT week) as weeks,
            MIN(week) as min_week,
            MAX(week) as max_week
        FROM read_parquet('{safe_path}')
        WHERE season IS NOT NULL AND week IS NOT NULL
        GROUP BY season
        ORDER BY season
    """).fetchall()  # noqa: S608

    return [
        {"season": s, "weeks": w, "min_week": mw, "max_week": Mw}
        for s, w, mw, Mw in season_week_breakdown
    ]


def analyze_parquet_file(parquet_path: Path) -> dict:
    """Analyze a single Parquet file and return coverage metrics."""
    conn = duckdb.connect()
    metrics: dict[str, Any] = {"row_count": 0}  # Initialize metrics dict before try block

    try:
        # Get basic file info
        row_count, columns = _get_basic_file_info(conn, parquet_path)
        metrics.update({"row_count": row_count, "columns": columns})

        # Analyze various coverage metrics
        metrics.update(_analyze_season_coverage(conn, parquet_path, columns))
        metrics.update(_analyze_week_coverage(conn, parquet_path, columns))
        metrics.update(_count_distinct_entities(conn, parquet_path, columns))

        # Get season/week breakdown
        breakdown = _get_season_week_breakdown(conn, parquet_path, columns)
        if breakdown:
            metrics["season_week_breakdown"] = breakdown

    except Exception as e:
        metrics["error"] = str(e)
        # metrics dict already initialized, row_count defaults to 0
    finally:
        conn.close()

    return metrics


def _group_parquet_files_by_dataset(
    parquet_files: list[Path], source_name: str, datasets_filter: list[str] | None = None
) -> dict[str, list[tuple[str, Path]]]:
    """Group parquet files by dataset name.

    Args:
        parquet_files: List of parquet file paths
        source_name: Name of the source
        datasets_filter: Optional list of dataset names to filter by

    Returns:
        Dictionary mapping dataset name -> list of (dt, path) tuples

    """
    datasets = defaultdict(list)
    for pf in parquet_files:
        dataset, dt = extract_dataset_and_dt(pf, source_name)

        # Filter by dataset if specified
        if datasets_filter and dataset not in datasets_filter:
            continue

        datasets[dataset].append((dt, pf))

    return datasets


def _print_basic_metrics(metrics: dict[str, Any]) -> None:
    """Print basic metrics (rows, seasons, weeks)."""
    print(f"    Rows: {metrics['row_count']:,}")

    if "season_min" in metrics:
        seasons_str = (
            f"{metrics['season_min']}-{metrics['season_max']} "
            f"({metrics['distinct_seasons']} distinct)"
        )
        print(f"    Seasons: {seasons_str}")

    if "week_min" in metrics:
        print(f"    Weeks: {metrics['week_min']}-{metrics['week_max']}")

    if "distinct_weeks" in metrics:
        print(f"    Distinct weeks: {metrics['distinct_weeks']}")


def _print_distinct_entities(metrics: dict[str, Any]) -> None:
    """Print distinct entity counts."""
    entity_labels = {
        "distinct_players": "Distinct players (player_id)",
        "distinct_players_pfr": "Distinct players (pfr_player_id)",
        "distinct_players_gsis": "Distinct players (gsis_id)",
        "distinct_players_mfl": "Distinct players (mfl_id)",
        "distinct_games": "Distinct games",
        "distinct_teams": "Distinct teams",
    }

    for key, label in entity_labels.items():
        if key in metrics:
            value = metrics[key]
            if key == "distinct_teams":
                print(f"    {label}: {value}")
            else:
                print(f"    {label}: {value:,}")


def _print_season_week_breakdown(metrics: dict[str, Any]) -> None:
    """Print season/week breakdown if available."""
    if "season_week_breakdown" not in metrics or not metrics["season_week_breakdown"]:
        return

    print("    Season/Week breakdown:")
    breakdown = metrics["season_week_breakdown"]
    for sw in breakdown[:5]:  # Show first 5
        print(
            f"      {sw['season']}: weeks {sw['min_week']}-{sw['max_week']} ({sw['weeks']} weeks)"
        )
    if len(breakdown) > 5:
        print(f"      ... and {len(breakdown) - 5} more seasons")


def _print_delta_info(delta_info: dict) -> None:
    """Print delta information for a snapshot.

    Args:
        delta_info: Delta statistics from calculate_deltas

    """
    delta = delta_info["delta"]
    pct_change = delta_info["pct_change"]

    # Format delta with sign
    delta_str = f"+{delta:,}" if delta >= 0 else f"{delta:,}"
    pct_str = f"+{pct_change:.1f}%" if pct_change >= 0 else f"{pct_change:.1f}%"

    print(f"    Delta: {delta_str} rows ({pct_str}) vs {delta_info['previous_snapshot']}")

    # Show warnings for anomalies
    warnings = []
    if delta_info["is_data_loss"]:
        warnings.append("⚠️  DATA LOSS")
    if delta_info["is_anomaly"]:
        thresholds = delta_info["thresholds"]
        warnings.append(
            f"⚠️  ANOMALY (expected {thresholds['min_pct']}% to {thresholds['max_pct']}%)"
        )
    if delta_info["is_stagnant"]:
        warnings.append("⚠️  STAGNANT (expected growth during season)")

    if warnings:
        for warning in warnings:
            print(f"    {warning}")


def _print_gap_info(gap_info: dict) -> None:
    """Print coverage gap information.

    Args:
        gap_info: Gap analysis from detect_coverage_gaps

    """
    if "error" in gap_info:
        print(f"    Gap detection: {gap_info['error']}")
        return

    # Show strategy note if present
    strategy_note = gap_info.get("strategy_note")
    if strategy_note:
        print(f"    Coverage strategy: {strategy_note}")

    gap_count = gap_info.get("gap_count", 0)
    if gap_count == 0:
        coverage_msg = f"None (complete coverage for {gap_info['coverage_seasons']})"
        if strategy_note:
            coverage_msg = "None (expected for current snapshot - baseline has historical data)"
        print(f"    Coverage gaps: {coverage_msg}")
        return

    print(f"    Coverage gaps: {gap_count} missing weeks")
    gaps = gap_info.get("gaps", [])
    for gap in gaps[:5]:  # Show first 5 gaps
        if gap["week"] is None:
            print(f"      - {gap['season']} (entire season missing)")
        else:
            print(f"      - {gap['season']} Week {gap['week']}")
    if len(gaps) > 5:
        print(f"      ... and {len(gaps) - 5} more gaps")


def _print_mapping_info(mapping_info: dict) -> None:
    """Print player mapping rate information.

    Args:
        mapping_info: Mapping statistics from calculate_mapping_rate

    """
    if "error" in mapping_info:
        print(f"    Player mapping: {mapping_info['error']}")
        return

    rate = mapping_info.get("mapping_rate", 0)
    total = mapping_info.get("total_players", 0)
    mapped = mapping_info.get("mapped_players", 0)
    unmapped_count = total - mapped

    print(f"    Player mapping: {rate:.1f}% ({mapped:,}/{total:,} players)")

    if rate < 90 and unmapped_count > 0:
        print(f"      ⚠️  LOW MAPPING RATE ({unmapped_count:,} unmapped players)")

        unmapped_sample = mapping_info.get("unmapped_sample", [])
        if unmapped_sample:
            print("      Top unmapped players:")
            for player in unmapped_sample[:3]:
                if "player_name" in player:
                    print(f"        - {player['player_name']} ({player['player_id']})")
                else:
                    print(f"        - {player['player_id']}")


def _print_snapshot_metrics(
    metrics: dict[str, Any],
    dt: str,
    parquet_path: Path,
    delta_info: dict | None = None,
    gap_info: dict | None = None,
    mapping_info: dict | None = None,
) -> None:
    """Print metrics for a single snapshot.

    Args:
        metrics: Dictionary of metrics from analyze_parquet_file
        dt: Snapshot date partition
        parquet_path: Path to the parquet file
        delta_info: Optional delta information from calculate_deltas
        gap_info: Optional gap information from detect_coverage_gaps
        mapping_info: Optional mapping information from calculate_mapping_rate

    """
    print(f"\n  Snapshot: dt={dt}")
    print(f"  File: {parquet_path.name}")

    if "error" in metrics:
        print(f"    ERROR: {metrics['error']}")
        return

    _print_basic_metrics(metrics)

    # Print delta information if available
    if delta_info and "error" not in delta_info and delta_info.get("current_snapshot") == dt:
        _print_delta_info(delta_info)

    # Print gap information if available
    if gap_info and gap_info.get("current_snapshot") == dt:
        _print_gap_info(gap_info)

    # Print mapping information if available
    if mapping_info and mapping_info.get("current_snapshot") == dt:
        _print_mapping_info(mapping_info)

    _print_distinct_entities(metrics)
    _print_season_week_breakdown(metrics)


def _compute_delta_info(
    source_name: str, dataset: str, registry_df: pl.DataFrame | None
) -> dict | None:
    """Compute delta information if registry is available.

    Args:
        source_name: Name of the source
        dataset: Dataset name
        registry_df: Optional snapshot registry

    Returns:
        Delta info dictionary or None

    """
    if registry_df is None:
        return None

    delta_info = calculate_deltas(source_name, dataset, registry_df)
    if "error" in delta_info:
        print(f"  Note: {delta_info['error']}")
        return None

    return delta_info


def _compute_gap_info(
    detect_gaps: bool,
    registry_df: pl.DataFrame | None,
    source_name: str,
    dataset: str,
    current_path: Path | None,
    current_dt: str | None,
) -> dict | None:
    """Compute gap detection information for current snapshot.

    Args:
        detect_gaps: Whether gap detection is requested
        registry_df: Optional snapshot registry
        source_name: Data source name
        dataset: Dataset name
        current_path: Path to current snapshot
        current_dt: Date of current snapshot

    Returns:
        Gap info dictionary or None

    """
    if not (detect_gaps and registry_df is not None and current_path and current_dt):
        return None

    gap_info = detect_coverage_gaps(source_name, dataset, current_path, registry_df, current_dt)
    if "error" not in gap_info:
        gap_info["current_snapshot"] = current_dt

    return gap_info


def _compute_mapping_info(
    check_mappings: bool, current_path: Path | None, current_dt: str | None
) -> dict | None:
    """Compute player mapping information for current snapshot.

    Args:
        check_mappings: Whether mapping check is requested
        current_path: Path to current snapshot
        current_dt: Date of current snapshot

    Returns:
        Mapping info dictionary or None

    """
    if not (check_mappings and current_path):
        return None

    mapping_info = calculate_mapping_rate(current_path)
    if "error" not in mapping_info:
        mapping_info["current_snapshot"] = current_dt

    return mapping_info


def _add_analysis_to_metrics(
    metrics: dict[str, Any],
    dt: str,
    delta_info: dict | None,
    gap_info: dict | None,
    mapping_info: dict | None,
) -> None:
    """Add delta/gap/mapping analysis results to metrics dictionary.

    Args:
        metrics: Metrics dictionary to update
        dt: Current snapshot date
        delta_info: Delta information if available
        gap_info: Gap information if available
        mapping_info: Mapping information if available

    """
    if delta_info and delta_info.get("current_snapshot") == dt:
        metrics["delta"] = delta_info

    if gap_info and gap_info.get("current_snapshot") == dt:
        metrics["gaps"] = gap_info

    if mapping_info and mapping_info.get("current_snapshot") == dt:
        metrics["mapping"] = mapping_info


def _analyze_dataset(
    dataset: str,
    files: list[tuple[str, Path]],
    source_name: str,
    registry_df: pl.DataFrame | None = None,
    detect_gaps: bool = False,
    check_mappings: bool = False,
) -> dict[str, dict[str, Any]]:
    """Analyze all snapshots for a single dataset.

    Args:
        dataset: Name of the dataset
        files: List of (dt, parquet_path) tuples
        source_name: Name of the source (for delta calculation)
        registry_df: Optional snapshot registry DataFrame for delta calculation
        detect_gaps: Whether to detect coverage gaps
        check_mappings: Whether to check player mapping rates

    Returns:
        Dictionary mapping dt -> metrics

    """
    print(f"\n{'=' * 60}")
    print(f"Dataset: {dataset}")
    print(f"{'=' * 60}")

    # Get current snapshot for gap and mapping detection
    sorted_files = sorted(files, reverse=True)
    current_dt, current_path = sorted_files[0] if sorted_files else (None, None)

    # Compute analysis information
    delta_info = _compute_delta_info(source_name, dataset, registry_df)
    gap_info = _compute_gap_info(
        detect_gaps, registry_df, source_name, dataset, current_path, current_dt
    )
    mapping_info = _compute_mapping_info(check_mappings, current_path, current_dt)

    # Analyze each snapshot
    dataset_results = {}
    for dt, parquet_path in sorted(files):
        metrics = analyze_parquet_file(parquet_path)
        metrics["file_path"] = str(parquet_path)

        # Add analysis results to metrics
        _add_analysis_to_metrics(metrics, dt, delta_info, gap_info, mapping_info)

        dataset_results[dt] = metrics
        _print_snapshot_metrics(metrics, dt, parquet_path, delta_info, gap_info, mapping_info)

    return dataset_results


def extract_dataset_and_dt(parquet_path: Path, source_name: str) -> tuple[str, str]:
    """Extract dataset name and dt partition from a parquet file path.

    Args:
        parquet_path: Path to the parquet file
        source_name: Name of the source (e.g., 'nflverse', 'sleeper')

    Returns:
        Tuple of (dataset_name, dt_partition)

    """
    parts = list(parquet_path.parts)

    # Find source index to get dataset name
    try:
        source_idx = parts.index(source_name)
        dataset = parts[source_idx + 1] if source_idx + 1 < len(parts) else "unknown"
    except ValueError:
        # Fallback: use parent directory name
        dataset = (
            parquet_path.parent.parent.name
            if parquet_path.parent.parent.name != source_name
            else "unknown"
        )

    # Find dt partition
    dt = "unknown"
    for part in parts:
        if part.startswith("dt="):
            dt = part.replace("dt=", "")
            break

    return dataset, dt


def analyze_snapshots(
    base_dir: Path,
    source_name: str | None = None,
    datasets_filter: list[str] | None = None,
    report_deltas: bool = False,
    detect_gaps: bool = False,
    check_mappings: bool = False,
    registry_path: Path | None = None,
) -> dict:
    """Analyze all snapshots in a directory.

    Args:
        base_dir: Base directory containing snapshots (e.g., data/raw/nflverse)
        source_name: Name of the source (extracted from path if None)
        datasets_filter: Optional list of dataset names to filter by
        report_deltas: Whether to calculate and report deltas between snapshots
        detect_gaps: Whether to detect coverage gaps
        check_mappings: Whether to check player mapping rates
        registry_path: Optional path to snapshot registry (for delta calculation)

    Returns:
        Dictionary mapping dataset -> dt -> metrics

    """
    if not base_dir.exists():
        raise FileNotFoundError(f"Source directory not found: {base_dir}")

    # Extract source name from path if not provided
    if source_name is None:
        source_name = base_dir.name

    # Load registry if delta reporting or gap detection requested
    registry_df = None
    if report_deltas or detect_gaps:
        try:
            registry_df = load_snapshot_registry(registry_path)
            features = []
            if report_deltas:
                features.append("delta calculation")
            if detect_gaps:
                features.append("gap detection")
            print(f"Loaded snapshot registry for {', '.join(features)}\n")
        except FileNotFoundError as e:
            print(f"Warning: {e}")
            print("Continuing without registry-based features\n")

    # Find all parquet files
    parquet_files = sorted(base_dir.glob("*/dt=*/*.parquet"))

    if not parquet_files:
        print(f"No Parquet files found in {base_dir}!")
        return {}

    print(f"Found {len(parquet_files)} Parquet files in {base_dir}\n")

    # Group by dataset
    datasets = _group_parquet_files_by_dataset(parquet_files, source_name, datasets_filter)

    if not datasets:
        print("No datasets found matching filter criteria!")
        return {}

    # Analyze each dataset
    results = {}
    for dataset, files in sorted(datasets.items()):
        results[dataset] = _analyze_dataset(
            dataset, files, source_name, registry_df, detect_gaps, check_mappings
        )

    return results


def main():
    """Analyze snapshot coverage with command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Analyze snapshot coverage for data sources",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze nflverse (default)
  python tools/analyze_snapshot_coverage.py

  # Analyze a different source
  python tools/analyze_snapshot_coverage.py --source data/raw/sleeper

  # Analyze specific datasets only
  python tools/analyze_snapshot_coverage.py --datasets weekly snap_counts

  # Report row deltas between snapshots
  python tools/analyze_snapshot_coverage.py --report-deltas

  # Detect coverage gaps and check player mappings (nflverse)
  python tools/analyze_snapshot_coverage.py --detect-gaps --check-mappings

  # Full analysis with all features
  python tools/analyze_snapshot_coverage.py --report-deltas --detect-gaps --check-mappings

  # Custom output directory and filename
  python tools/analyze_snapshot_coverage.py --out-dir data/review --out-name custom_report
        """,
    )

    parser.add_argument(
        "--source",
        type=Path,
        default=Path("data/raw/nflverse"),
        help="Source directory containing snapshots (default: data/raw/nflverse)",
    )

    parser.add_argument(
        "--datasets",
        nargs="*",
        help="Specific datasets to analyze (default: all datasets)",
    )

    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("data/review"),
        help="Output directory for reports (default: data/review)",
    )

    parser.add_argument(
        "--out-name",
        type=str,
        default=None,
        help="Base name for output files (default: {source_name}_snapshot_coverage)",
    )

    parser.add_argument(
        "--no-report",
        action="store_true",
        help="Skip generating markdown report (only generate JSON)",
    )

    parser.add_argument(
        "--report-deltas",
        action="store_true",
        help="Calculate and report row count deltas between snapshots",
    )

    parser.add_argument(
        "--detect-gaps",
        action="store_true",
        help="Detect season/week coverage gaps in snapshot data",
    )

    parser.add_argument(
        "--check-mappings",
        action="store_true",
        help="Check player mapping rates to dim_player_id_xref",
    )

    parser.add_argument(
        "--registry-path",
        type=Path,
        default=None,
        help=(
            "Path to snapshot registry CSV "
            "(default: dbt/ff_data_transform/seeds/snapshot_registry.csv)"
        ),
    )

    args = parser.parse_args()

    # Determine source name and output filename
    source_name = args.source.name
    output_base = args.out_name or f"{source_name}_snapshot_coverage"

    # Analyze snapshots
    results = analyze_snapshots(
        base_dir=args.source,
        source_name=source_name,
        datasets_filter=args.datasets,
        report_deltas=args.report_deltas,
        detect_gaps=args.detect_gaps,
        check_mappings=args.check_mappings,
        registry_path=args.registry_path,
    )

    if not results:
        print("\nNo results to save.")
        return

    # Write results to JSON
    args.out_dir.mkdir(parents=True, exist_ok=True)
    json_file = args.out_dir / f"{output_base}.json"
    json_file.write_text(json.dumps(results, indent=2, default=str))

    print(f"\n\nResults saved to: {json_file}")

    # Generate markdown report unless disabled
    if not args.no_report:
        report_file = args.out_dir / f"{output_base}_report.md"
        generate_markdown_report(results, report_file, source_name, args.source)
        print(f"Report saved to: {report_file}")


def _generate_report_header(source_name: str, source_path: Path, results: dict) -> list[str]:
    """Generate the header and executive summary section."""
    return [
        f"# {source_name.title()} Snapshot Coverage Analysis",
        "",
        f"**Generated**: Analysis of all {source_name} snapshots in `{source_path}/`",
        f"**Analysis Date**: {datetime.now().strftime('%Y-%m-%d')}",
        f"**Total Snapshots**: "
        f"{sum(len(snapshots) for snapshots in results.values())} "
        f"Parquet files across {len(results)} datasets",
        "",
        "## Executive Summary",
        "",
        f"This report analyzes the data coverage, freshness, and usage "
        f"of all {source_name} snapshots. Key findings:",
        "",
        "- **Coverage**: See detailed breakdown below",
        "- **Freshness**: Latest snapshot dates shown in summary table",
        "- **Issues**: See recommendations section",
        "",
        "## Summary",
        "",
    ]


def _generate_summary_table(results: dict) -> list[str]:
    """Generate the summary table section."""
    lines = [
        "| Dataset | Snapshots | Latest Snapshot | Total Rows | Season Range |",
        "|---------|-----------|-----------------|------------|--------------|",
    ]

    for dataset, snapshots in sorted(results.items()):
        snapshot_dates = sorted(snapshots.keys())
        latest = snapshot_dates[-1] if snapshot_dates else "N/A"

        # Aggregate metrics
        total_rows = sum(s.get("row_count", 0) for s in snapshots.values())

        season_ranges = []
        for metrics in snapshots.values():
            if "season_min" in metrics and "season_max" in metrics:
                season_ranges.append(f"{metrics['season_min']}-{metrics['season_max']}")

        season_range = ", ".join(set(season_ranges)) if season_ranges else "N/A"

        lines.append(
            f"| {dataset} | {len(snapshots)} | {latest} | {total_rows:,} | {season_range} |"
        )

    return lines


def _generate_snapshot_details(metrics: dict[str, Any], dataset: str, dt: str) -> list[str]:
    """Generate detailed lines for a single snapshot."""
    lines = [f"### Snapshot: `dt={dt}` ({dataset})", ""]

    if "error" in metrics:
        lines.extend([f"**ERROR**: {metrics['error']}", ""])
        return lines

    file_path = Path(metrics.get("file_path", "unknown")).name if "file_path" in metrics else "N/A"
    lines.append(f"- **File**: `{file_path}`")
    lines.append(f"- **Rows**: {metrics.get('row_count', 0):,}")
    lines.append("")

    if "season_min" in metrics:
        lines.extend(
            [
                f"#### Season Coverage ({dataset} {dt})",
                "",
                f"- Range: {metrics['season_min']} - {metrics['season_max']}",
                f"- Distinct seasons: {metrics.get('distinct_seasons', 'N/A')}",
                "",
            ]
        )

    if "week_min" in metrics:
        lines.extend(
            [
                f"#### Week Coverage ({dataset} {dt})",
                "",
                f"- Range: {metrics['week_min']} - {metrics['week_max']}",
                f"- Distinct weeks: {metrics.get('distinct_weeks', 'N/A')}",
                "",
            ]
        )

    if "season_week_breakdown" in metrics and metrics["season_week_breakdown"]:
        lines.append(f"#### Season/Week Breakdown ({dataset} {dt})")
        lines.append("")
        lines.append("| Season | Weeks | Min Week | Max Week |")
        lines.append("|--------|-------|----------|----------|")
        for sw in metrics["season_week_breakdown"]:
            lines.append(
                f"| {sw['season']} | {sw['weeks']} | {sw['min_week']} | {sw['max_week']} |"
            )
        lines.append("")

    # Entity counts
    entity_labels = {
        "distinct_players": "Players (player_id)",
        "distinct_players_pfr": "Players (pfr_player_id)",
        "distinct_players_gsis": "Players (gsis_id)",
        "distinct_players_mfl": "Players (mfl_id)",
        "distinct_games": "Games",
        "distinct_teams": "Teams",
    }

    entity_lines = []
    for key, label in entity_labels.items():
        if key in metrics:
            value = metrics[key]
            if key == "distinct_teams":
                entity_lines.append(f"- {label}: {value}")
            else:
                entity_lines.append(f"- {label}: {value:,}")

    if entity_lines:
        lines.extend(
            [
                f"#### Entity Counts ({dataset} {dt})",
                "",
                *entity_lines,
                "",
            ]
        )

    lines.extend(["---", ""])
    return lines


def _generate_detailed_breakdown(results: dict) -> list[str]:
    """Generate detailed breakdown section for all datasets."""
    lines = []
    for dataset, snapshots in sorted(results.items()):
        lines.append(f"## {dataset}")
        lines.append("")

        for dt, metrics in sorted(snapshots.items()):
            lines.extend(_generate_snapshot_details(metrics, dataset, dt))

    return lines


def _generate_comparison_section(results: dict) -> list[str]:
    """Generate snapshot comparison section."""
    lines = [
        "## Snapshot Comparison",
        "",
        "### Overlap Analysis",
        "",
    ]

    for dataset, snapshots in sorted(results.items()):
        if len(snapshots) < 2:
            continue

        lines.append(f"#### {dataset} Overlap")
        lines.append("")

        snapshot_dates = sorted(snapshots.keys())
        lines.append("| Snapshot | Season Range | Distinct Seasons | Rows |")
        lines.append("|----------|--------------|------------------|------|")

        for dt in snapshot_dates:
            m = snapshots[dt]
            if "season_min" in m:
                season_range = f"{m['season_min']}-{m['season_max']}"
                distinct = m.get("distinct_seasons", "N/A")
            else:
                season_range = "N/A"
                distinct = "N/A"

            lines.append(f"| {dt} | {season_range} | {distinct} | {m.get('row_count', 0):,} |")

        lines.append("")

    return lines


def generate_markdown_report(
    results: dict,
    output_file: Path,
    source_name: str,
    source_path: Path,
) -> None:
    """Generate a markdown coverage report.

    Args:
        results: Dictionary mapping dataset -> dt -> metrics
        output_file: Path to write the markdown report
        source_name: Name of the data source (e.g., 'nflverse')
        source_path: Path to the source directory

    """
    lines = _generate_report_header(source_name, source_path, results)
    lines.extend(_generate_summary_table(results))
    lines.extend(["", "---", ""])
    lines.extend(_generate_detailed_breakdown(results))
    lines.extend(_generate_comparison_section(results))

    output_file.write_text("\n".join(lines))


if __name__ == "__main__":
    main()
