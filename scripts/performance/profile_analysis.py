#!/usr/bin/env python3
"""Performance profiling analysis for FF Analytics project.

Profiles:
1. Ingestion layer (commissioner_parser.py, Polars operations)
2. dbt transformation performance
3. DuckDB query execution
4. Memory usage patterns
"""

import json
import time
from pathlib import Path

import psutil


# Baseline metrics collection
class PerformanceProfiler:
    """Collect performance metrics for FF Analytics workflows."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.metrics: dict[str, any] = {}
        self.process = psutil.Process()

    def get_memory_usage(self) -> dict[str, float]:
        """Get current memory usage in MB."""
        mem_info = self.process.memory_info()
        return {
            "rss_mb": mem_info.rss / 1024 / 1024,
            "vms_mb": mem_info.vms / 1024 / 1024,
            "percent": self.process.memory_percent(),
        }

    def get_cpu_usage(self) -> dict[str, float]:
        """Get current CPU usage."""
        return {
            "percent": self.process.cpu_percent(interval=1),
            "num_threads": self.process.num_threads(),
        }

    def profile_database_stats(self, duckdb_path: Path) -> dict[str, any]:
        """Collect DuckDB database statistics."""
        import duckdb

        con = duckdb.connect(str(duckdb_path), read_only=True)

        stats = {}

        # Database size
        stats["database_size"] = (
            con.execute("SELECT * FROM pragma_database_size()")
            .fetchdf()
            .to_dict(orient="records")[0]
        )

        # Table counts and sizes
        stats["tables"] = (
            con.execute("""
            SELECT
                table_name,
                estimated_size as row_count,
                column_count
            FROM duckdb_tables()
            WHERE schema_name = 'main'
            ORDER BY estimated_size DESC
            LIMIT 20
        """)
            .fetchdf()
            .to_dict(orient="records")
        )

        # Fact table details
        stats["fact_player_stats"] = (
            con.execute("""
            SELECT
                COUNT(*) as total_rows,
                COUNT(DISTINCT player_key) as distinct_players,
                COUNT(DISTINCT game_id) as distinct_games,
                COUNT(DISTINCT stat_name) as distinct_stats,
                MIN(season) as min_season,
                MAX(season) as max_season
            FROM main.fct_player_stats
        """)
            .fetchdf()
            .to_dict(orient="records")[0]
        )

        # Index count
        stats["index_count"] = (
            con.execute("""
            SELECT COUNT(*) as count
            FROM duckdb_indexes()
            WHERE schema_name = 'main'
        """)
            .fetchdf()
            .iloc[0]["count"]
        )

        # Crosswalk stats
        try:
            stats["crosswalk"] = (
                con.execute("""
                SELECT
                    COUNT(*) as total_rows,
                    COUNT(DISTINCT player_id) as distinct_canonical_ids,
                    COUNT(DISTINCT mfl_id) as distinct_mfl_ids,
                    COUNT(DISTINCT sleeper_id) as distinct_sleeper_ids,
                    COUNT(DISTINCT gsis_id) as distinct_gsis_ids
                FROM main.dim_player_id_xref
            """)
                .fetchdf()
                .to_dict(orient="records")[0]
            )
        except Exception as e:
            stats["crosswalk_error"] = str(e)

        con.close()
        return stats

    def benchmark_query(self, duckdb_path: Path, query: str, name: str) -> dict[str, any]:
        """Benchmark a specific query with timing and EXPLAIN ANALYZE."""
        import duckdb

        con = duckdb.connect(str(duckdb_path), read_only=True)

        # Get execution plan
        explain_query = f"EXPLAIN ANALYZE {query}"

        start_time = time.time()
        start_mem = self.get_memory_usage()

        try:
            # Run actual query
            result = con.execute(query).fetchdf()
            end_time = time.time()
            end_mem = self.get_memory_usage()

            # Get execution plan
            plan = con.execute(explain_query).fetchdf()

            metrics = {
                "name": name,
                "execution_time_sec": end_time - start_time,
                "row_count": len(result),
                "column_count": len(result.columns) if len(result) > 0 else 0,
                "memory_delta_mb": end_mem["rss_mb"] - start_mem["rss_mb"],
                "execution_plan": plan.to_dict(orient="records") if len(plan) > 0 else [],
            }

        except Exception as e:
            metrics = {"name": name, "error": str(e)}

        con.close()
        return metrics

    def profile_parquet_read(self, parquet_path: Path) -> dict[str, any]:
        """Profile Parquet file read performance."""
        import polars as pl

        start_time = time.time()
        start_mem = self.get_memory_usage()

        try:
            df = pl.read_parquet(parquet_path)
            end_time = time.time()
            end_mem = self.get_memory_usage()

            return {
                "file_path": str(parquet_path),
                "file_size_mb": parquet_path.stat().st_size / 1024 / 1024,
                "read_time_sec": end_time - start_time,
                "row_count": len(df),
                "column_count": len(df.columns),
                "memory_delta_mb": end_mem["rss_mb"] - start_mem["rss_mb"],
                "throughput_mb_per_sec": (parquet_path.stat().st_size / 1024 / 1024)
                / (end_time - start_time),
            }
        except Exception as e:
            return {"file_path": str(parquet_path), "error": str(e)}

    def save_metrics(self, output_path: Path):
        """Save collected metrics to JSON."""
        with open(output_path, "w") as f:
            json.dump(self.metrics, f, indent=2, default=str)


def main():
    """Run performance profiling analysis."""
    project_root = Path("/Users/jason/code/ff_analytics")
    profiler = PerformanceProfiler(project_root)

    print("=" * 80)
    print("FF Analytics Performance Profiling")
    print("=" * 80)

    # 1. Database statistics
    print("\n[1/5] Collecting database statistics...")
    duckdb_path = project_root / "dbt/ff_data_transform/target/dev.duckdb"
    if duckdb_path.exists():
        profiler.metrics["database_stats"] = profiler.profile_database_stats(duckdb_path)
        print(
            f"  ✓ Database size: {profiler.metrics['database_stats']['database_size']['database_size']}"
        )
        print(
            f"  ✓ Fact table rows: {profiler.metrics['database_stats']['fact_player_stats']['total_rows']:,}"
        )
        print(f"  ✓ Tables analyzed: {len(profiler.metrics['database_stats']['tables'])}")
    else:
        print(f"  ✗ Database not found at {duckdb_path}")

    # 2. Benchmark key queries
    print("\n[2/5] Benchmarking query performance...")

    queries = [
        (
            """
            SELECT
                fps.player_key,
                fps.stat_name,
                SUM(fps.stat_value_num) as total_value,
                COUNT(*) as game_count
            FROM main.fct_player_stats fps
            INNER JOIN main.dim_player dp ON fps.player_key = dp.player_key
            WHERE fps.position IN ('QB', 'RB', 'WR', 'TE')
                AND fps.season >= 2023
            GROUP BY fps.player_key, fps.stat_name
            ORDER BY total_value DESC
            LIMIT 100
            """,
            "varchar_join_aggregation",
        ),
        (
            """
            SELECT
                fps.season,
                fps.week,
                fps.position,
                COUNT(DISTINCT fps.player_key) as player_count,
                AVG(fps.stat_value_num) as avg_value
            FROM main.fct_player_stats fps
            WHERE fps.season >= 2023
                AND fps.stat_name = 'fantasy_points'
            GROUP BY fps.season, fps.week, fps.position
            """,
            "simple_aggregation",
        ),
        (
            """
            SELECT
                xref.player_id,
                xref.player_key,
                dp.player_name,
                dp.position
            FROM main.dim_player_id_xref xref
            INNER JOIN main.dim_player dp ON xref.player_id = dp.player_id
            WHERE dp.position IN ('QB', 'RB', 'WR', 'TE')
            """,
            "crosswalk_join",
        ),
    ]

    profiler.metrics["query_benchmarks"] = []
    for query, name in queries:
        print(f"  Running: {name}...")
        result = profiler.benchmark_query(duckdb_path, query, name)
        profiler.metrics["query_benchmarks"].append(result)
        if "error" not in result:
            print(
                f"    ✓ Execution time: {result['execution_time_sec']:.3f}s, Rows: {result['row_count']}"
            )
        else:
            print(f"    ✗ Error: {result['error']}")

    # 3. Profile Parquet reads
    print("\n[3/5] Profiling Parquet read performance...")
    raw_data_dir = project_root / "data/raw"
    parquet_files = list(raw_data_dir.rglob("*.parquet"))[:5]  # Sample first 5

    profiler.metrics["parquet_reads"] = []
    for pq_file in parquet_files:
        print(f"  Reading: {pq_file.name}...")
        result = profiler.profile_parquet_read(pq_file)
        profiler.metrics["parquet_reads"].append(result)
        if "error" not in result:
            print(
                f"    ✓ Read time: {result['read_time_sec']:.3f}s, Throughput: {result['throughput_mb_per_sec']:.1f} MB/s"
            )

    # 4. System resource usage
    print("\n[4/5] Collecting system resource usage...")
    profiler.metrics["system"] = {
        "memory": profiler.get_memory_usage(),
        "cpu": profiler.get_cpu_usage(),
        "disk_usage": {
            "raw_data_mb": sum(
                f.stat().st_size for f in (project_root / "data/raw").rglob("*") if f.is_file()
            )
            / 1024
            / 1024,
            "database_mb": duckdb_path.stat().st_size / 1024 / 1024 if duckdb_path.exists() else 0,
        },
    }
    print(f"  ✓ Memory usage: {profiler.metrics['system']['memory']['rss_mb']:.1f} MB")
    print(f"  ✓ CPU usage: {profiler.metrics['system']['cpu']['percent']:.1f}%")

    # 5. Save results
    print("\n[5/5] Saving metrics...")
    output_path = project_root / "scripts/performance/baseline_metrics.json"
    profiler.save_metrics(output_path)
    print(f"  ✓ Metrics saved to: {output_path}")

    print("\n" + "=" * 80)
    print("Profiling complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()
