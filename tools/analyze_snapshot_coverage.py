"""tools/analyze_snapshot_coverage.py.

Analyze snapshot coverage for any data source to understand what data is in each snapshot.

This tool analyzes Parquet files organized in date-partitioned directories (dt=YYYY-MM-DD)
and generates reports showing data coverage, freshness, and entity counts.

Usage:
    # Analyze nflverse (default)
    python tools/analyze_snapshot_coverage.py

    # Analyze a different source
    python tools/analyze_snapshot_coverage.py --source data/raw/sleeper

    # Analyze specific datasets only
    python tools/analyze_snapshot_coverage.py --datasets weekly snap_counts

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


def _print_snapshot_metrics(metrics: dict[str, Any], dt: str, parquet_path: Path) -> None:
    """Print metrics for a single snapshot.

    Args:
        metrics: Dictionary of metrics from analyze_parquet_file
        dt: Snapshot date partition
        parquet_path: Path to the parquet file

    """
    print(f"\n  Snapshot: dt={dt}")
    print(f"  File: {parquet_path.name}")

    if "error" in metrics:
        print(f"    ERROR: {metrics['error']}")
        return

    _print_basic_metrics(metrics)
    _print_distinct_entities(metrics)
    _print_season_week_breakdown(metrics)


def _analyze_dataset(dataset: str, files: list[tuple[str, Path]]) -> dict[str, dict[str, Any]]:
    """Analyze all snapshots for a single dataset.

    Args:
        dataset: Name of the dataset
        files: List of (dt, parquet_path) tuples

    Returns:
        Dictionary mapping dt -> metrics

    """
    print(f"\n{'=' * 60}")
    print(f"Dataset: {dataset}")
    print(f"{'=' * 60}")

    dataset_results = {}

    for dt, parquet_path in sorted(files):
        metrics = analyze_parquet_file(parquet_path)
        metrics["file_path"] = str(parquet_path)  # Store full path for reference
        dataset_results[dt] = metrics
        _print_snapshot_metrics(metrics, dt, parquet_path)

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
) -> dict:
    """Analyze all snapshots in a directory.

    Args:
        base_dir: Base directory containing snapshots (e.g., data/raw/nflverse)
        source_name: Name of the source (extracted from path if None)
        datasets_filter: Optional list of dataset names to filter by

    Returns:
        Dictionary mapping dataset -> dt -> metrics

    """
    if not base_dir.exists():
        raise FileNotFoundError(f"Source directory not found: {base_dir}")

    # Extract source name from path if not provided
    if source_name is None:
        source_name = base_dir.name

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
        results[dataset] = _analyze_dataset(dataset, files)

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

    args = parser.parse_args()

    # Determine source name and output filename
    source_name = args.source.name
    output_base = args.out_name or f"{source_name}_snapshot_coverage"

    # Analyze snapshots
    results = analyze_snapshots(
        base_dir=args.source,
        source_name=source_name,
        datasets_filter=args.datasets,
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
