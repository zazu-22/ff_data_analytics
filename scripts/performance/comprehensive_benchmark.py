#!/usr/bin/env python3
"""Comprehensive performance benchmarking for FF Analytics project.

Tests specific Phase 1 concerns:
1. VARCHAR player_key join performance vs INT joins
2. Crosswalk join overhead
3. Large fact table aggregations
4. Complex mart query patterns
5. Window function performance
6. Concurrent query performance
"""

import json
import time
from pathlib import Path

import duckdb
import psutil


class PerformanceBenchmark:
    """Benchmark DuckDB query performance with detailed metrics."""

    def __init__(self, duckdb_path: Path):
        self.duckdb_path = duckdb_path
        self.results: list[dict] = []
        self.process = psutil.Process()

    def run_query_benchmark(
        self, query: str, name: str, warmup: bool = True, iterations: int = 3
    ) -> dict:
        """Run a query multiple times and collect performance metrics."""
        times = []

        # Connect with read-only mode for safety
        con = duckdb.connect(str(self.duckdb_path), read_only=True)

        try:
            # Warmup run
            if warmup:
                _ = con.execute(query).fetchdf()

            # Benchmark runs
            for _i in range(iterations):
                start_mem = self.process.memory_info().rss / 1024 / 1024
                start_time = time.time()

                result = con.execute(query).fetchdf()

                end_time = time.time()
                end_mem = self.process.memory_info().rss / 1024 / 1024

                times.append(end_time - start_time)

            # Get execution plan
            explain_query = f"EXPLAIN ANALYZE {query}"
            explain_result = con.execute(explain_query).fetchdf()

            # Parse execution plan for key metrics
            explain_text = explain_result.to_string() if len(explain_result) > 0 else ""

            metrics = {
                "name": name,
                "avg_execution_time_sec": sum(times) / len(times),
                "min_execution_time_sec": min(times),
                "max_execution_time_sec": max(times),
                "iterations": iterations,
                "row_count": len(result),
                "column_count": len(result.columns) if len(result) > 0 else 0,
                "memory_delta_mb": end_mem - start_mem,
                "execution_plan_summary": explain_text[:500]
                if len(explain_text) > 500
                else explain_text,
            }

        except Exception as e:
            metrics = {"name": name, "error": str(e), "execution_time_sec": None}

        finally:
            con.close()

        self.results.append(metrics)
        return metrics

    def test_varchar_vs_int_joins(self) -> dict:
        """Test 1: VARCHAR player_key join performance
        Phase 1 concern: Composite VARCHAR reduces join performance vs INT.
        """
        # Test 1a: Current implementation - VARCHAR player_key join
        query_varchar = """
            SELECT
                fps.player_key,
                fps.stat_name,
                SUM(fps.stat_value) as total_value,
                COUNT(*) as game_count
            FROM main.fct_player_stats fps
            INNER JOIN main.dim_player dp ON fps.player_id = dp.player_id
            WHERE fps.position IN ('QB', 'RB', 'WR', 'TE')
                AND fps.season >= 2023
            GROUP BY fps.player_key, fps.stat_name
            ORDER BY total_value DESC
            LIMIT 1000
        """

        # Test 1b: INT player_id join (for comparison)
        query_int = """
            SELECT
                fps.player_id,
                fps.stat_name,
                SUM(fps.stat_value) as total_value,
                COUNT(*) as game_count
            FROM main.fct_player_stats fps
            INNER JOIN main.dim_player dp ON fps.player_id = dp.player_id
            WHERE fps.position IN ('QB', 'RB', 'WR', 'TE')
                AND fps.season >= 2023
            GROUP BY fps.player_id, fps.stat_name
            ORDER BY total_value DESC
            LIMIT 1000
        """

        varchar_result = self.run_query_benchmark(query_varchar, "varchar_player_key_join")
        int_result = self.run_query_benchmark(query_int, "int_player_id_join")

        return {
            "varchar_join": varchar_result,
            "int_join": int_result,
            "performance_impact_pct": (
                (
                    (
                        varchar_result.get("avg_execution_time_sec", 0)
                        - int_result.get("avg_execution_time_sec", 0)
                    )
                    / int_result.get("avg_execution_time_sec", 1)
                )
                * 100
                if "error" not in varchar_result and "error" not in int_result
                else None
            ),
        }

    def test_crosswalk_join_overhead(self) -> dict:
        """Test 2: Crosswalk join overhead
        Phase 1 concern: Every staging model joins dim_player_id_xref.
        """
        # Test 2a: Query with crosswalk join
        query_with_crosswalk = """
            SELECT
                xref.player_id,
                xref.mfl_id,
                xref.sleeper_id,
                xref.gsis_id,
                dp.display_name,
                dp.position,
                dp.current_team
            FROM main.dim_player_id_xref xref
            INNER JOIN main.dim_player dp ON xref.player_id = dp.player_id
            WHERE dp.position IN ('QB', 'RB', 'WR', 'TE')
                AND xref.mfl_id IS NOT NULL
        """

        # Test 2b: Direct dim_player query (no crosswalk)
        query_direct = """
            SELECT
                dp.player_id,
                dp.mfl_id,
                dp.sleeper_id,
                dp.gsis_id,
                dp.display_name,
                dp.position,
                dp.current_team
            FROM main.dim_player dp
            WHERE dp.position IN ('QB', 'RB', 'WR', 'TE')
                AND dp.mfl_id IS NOT NULL
        """

        crosswalk_result = self.run_query_benchmark(query_with_crosswalk, "crosswalk_join")
        direct_result = self.run_query_benchmark(query_direct, "direct_dimension_query")

        return {
            "crosswalk_join": crosswalk_result,
            "direct_query": direct_result,
            "overhead_pct": (
                (
                    (
                        crosswalk_result.get("avg_execution_time_sec", 0)
                        - direct_result.get("avg_execution_time_sec", 0)
                    )
                    / direct_result.get("avg_execution_time_sec", 1)
                )
                * 100
                if "error" not in crosswalk_result and "error" not in direct_result
                else None
            ),
        }

    def test_fact_table_aggregations(self) -> dict:
        """Test 3: Large fact table aggregations
        7.8M rows in fct_player_stats.
        """
        # Test 3a: Simple aggregation
        query_simple = """
            SELECT
                fps.season,
                fps.week,
                fps.position,
                COUNT(DISTINCT fps.player_id) as player_count,
                COUNT(*) as row_count,
                AVG(fps.stat_value) as avg_value
            FROM main.fct_player_stats fps
            WHERE fps.season >= 2023
                AND fps.stat_name = 'fantasy_points'
            GROUP BY fps.season, fps.week, fps.position
        """

        # Test 3b: Complex multi-stat aggregation
        query_complex = """
            SELECT
                fps.player_id,
                fps.season,
                SUM(CASE WHEN fps.stat_name = 'passing_yards' THEN fps.stat_value ELSE 0 END) as passing_yards,
                SUM(CASE WHEN fps.stat_name = 'rushing_yards' THEN fps.stat_value ELSE 0 END) as rushing_yards,
                SUM(CASE WHEN fps.stat_name = 'receiving_yards' THEN fps.stat_value ELSE 0 END) as receiving_yards,
                SUM(CASE WHEN fps.stat_name = 'passing_tds' THEN fps.stat_value ELSE 0 END) as passing_tds,
                SUM(CASE WHEN fps.stat_name = 'rushing_tds' THEN fps.stat_value ELSE 0 END) as rushing_tds,
                SUM(CASE WHEN fps.stat_name = 'receiving_tds' THEN fps.stat_value ELSE 0 END) as receiving_tds,
                COUNT(DISTINCT fps.game_id) as games_played
            FROM main.fct_player_stats fps
            WHERE fps.season >= 2023
                AND fps.position IN ('QB', 'RB', 'WR', 'TE')
            GROUP BY fps.player_id, fps.season
        """

        # Test 3c: Full table scan
        query_full_scan = """
            SELECT
                COUNT(*) as total_rows,
                COUNT(DISTINCT player_id) as distinct_players,
                COUNT(DISTINCT game_id) as distinct_games,
                COUNT(DISTINCT stat_name) as distinct_stats,
                MIN(season) as min_season,
                MAX(season) as max_season
            FROM main.fct_player_stats
        """

        simple_result = self.run_query_benchmark(query_simple, "simple_aggregation")
        complex_result = self.run_query_benchmark(query_complex, "complex_multi_stat_aggregation")
        full_scan_result = self.run_query_benchmark(query_full_scan, "full_table_scan")

        return {
            "simple_aggregation": simple_result,
            "complex_aggregation": complex_result,
            "full_table_scan": full_scan_result,
        }

    def test_window_functions(self) -> dict:
        """Test 4: Window function performance
        Used in marts for rolling averages, rankings.
        """
        query_window = """
            SELECT
                player_id,
                season,
                week,
                stat_name,
                stat_value,
                ROW_NUMBER() OVER (PARTITION BY player_id, stat_name ORDER BY season DESC, week DESC) as recency_rank,
                AVG(stat_value) OVER (
                    PARTITION BY player_id, stat_name
                    ORDER BY season, week
                    ROWS BETWEEN 3 PRECEDING AND CURRENT ROW
                ) as rolling_avg_4wk,
                SUM(stat_value) OVER (
                    PARTITION BY player_id, season, stat_name
                    ORDER BY week
                ) as season_cumulative
            FROM main.fct_player_stats
            WHERE season >= 2024
                AND position IN ('QB', 'RB', 'WR', 'TE')
                AND stat_name IN ('fantasy_points', 'targets', 'carries')
            ORDER BY player_id, season DESC, week DESC
            LIMIT 10000
        """

        return self.run_query_benchmark(query_window, "window_functions_complex")

    def test_mart_query_patterns(self) -> dict:
        """Test 5: Typical mart query patterns
        Simulates mrt_fasa_targets complexity.
        """
        query_mart = """
            SELECT
                dp.player_id,
                dp.display_name,
                dp.position,
                dp.current_team,
                COUNT(DISTINCT fps.game_id) as games_played,
                AVG(CASE WHEN fps.stat_name = 'fantasy_points' THEN fps.stat_value END) as avg_fantasy_points,
                SUM(CASE WHEN fps.stat_name = 'targets' THEN fps.stat_value END) as total_targets,
                SUM(CASE WHEN fps.stat_name = 'receptions' THEN fps.stat_value END) as total_receptions,
                SUM(CASE WHEN fps.stat_name = 'receiving_yards' THEN fps.stat_value END) as total_receiving_yards,
                SUM(CASE WHEN fps.stat_name = 'rushing_yards' THEN fps.stat_value END) as total_rushing_yards,
                SUM(CASE WHEN fps.stat_name = 'passing_yards' THEN fps.stat_value END) as total_passing_yards
            FROM main.dim_player dp
            LEFT JOIN main.fct_player_stats fps
                ON dp.player_id = fps.player_id
                AND fps.season = 2024
            WHERE dp.position IN ('QB', 'RB', 'WR', 'TE')
            GROUP BY dp.player_id, dp.display_name, dp.position, dp.current_team
            HAVING COUNT(DISTINCT fps.game_id) >= 1
            ORDER BY avg_fantasy_points DESC NULLS LAST
            LIMIT 500
        """

        return self.run_query_benchmark(query_mart, "mart_analytics_pattern")

    def test_concurrent_queries(self, num_concurrent: int = 3) -> dict:
        """Test 6: Concurrent query performance
        Phase 1 concern: Single DuckDB file with multiple Jupyter notebooks.
        """
        import queue
        import threading

        results_queue = queue.Queue()

        def run_concurrent_query(query_idx: int):
            con = duckdb.connect(str(self.duckdb_path), read_only=True)
            start_time = time.time()

            try:
                # Each "notebook" runs a different analytical query
                queries = [
                    """
                    SELECT position, AVG(stat_value) as avg_points
                    FROM main.fct_player_stats
                    WHERE stat_name = 'fantasy_points' AND season = 2024
                    GROUP BY position
                    """,
                    """
                    SELECT season, week, COUNT(DISTINCT player_id) as players
                    FROM main.fct_player_stats
                    WHERE season >= 2023
                    GROUP BY season, week
                    """,
                    """
                    SELECT player_id, SUM(stat_value) as total_yards
                    FROM main.fct_player_stats
                    WHERE stat_name IN ('passing_yards', 'rushing_yards', 'receiving_yards')
                    AND season = 2024
                    GROUP BY player_id
                    ORDER BY total_yards DESC
                    LIMIT 100
                    """,
                ]

                query = queries[query_idx % len(queries)]
                result = con.execute(query).fetchdf()

                end_time = time.time()

                results_queue.put(
                    {
                        "query_idx": query_idx,
                        "execution_time_sec": end_time - start_time,
                        "row_count": len(result),
                        "success": True,
                    }
                )

            except Exception as e:
                results_queue.put({"query_idx": query_idx, "error": str(e), "success": False})

            finally:
                con.close()

        # Run queries concurrently
        threads = []
        overall_start = time.time()

        for i in range(num_concurrent):
            t = threading.Thread(target=run_concurrent_query, args=(i,))
            t.start()
            threads.append(t)

        for t in threads:
            t.join()

        overall_end = time.time()

        # Collect results
        concurrent_results = []
        while not results_queue.empty():
            concurrent_results.append(results_queue.get())

        return {
            "num_concurrent_queries": num_concurrent,
            "total_elapsed_sec": overall_end - overall_start,
            "individual_results": concurrent_results,
            "avg_query_time_sec": sum(r.get("execution_time_sec", 0) for r in concurrent_results)
            / len(concurrent_results),
            "all_succeeded": all(r.get("success", False) for r in concurrent_results),
        }

    def save_results(self, output_path: Path):
        """Save benchmark results to JSON."""
        with open(output_path, "w") as f:
            json.dump(self.results, f, indent=2, default=str)


def main():
    """Run comprehensive performance benchmarks."""
    project_root = Path("/Users/jason/code/ff_analytics")
    duckdb_path = project_root / "dbt/ff_data_transform/target/dev.duckdb"

    if not duckdb_path.exists():
        print(f"Error: DuckDB database not found at {duckdb_path}")
        return

    benchmark = PerformanceBenchmark(duckdb_path)

    print("=" * 80)
    print("FF Analytics Comprehensive Performance Benchmark")
    print("=" * 80)

    all_results = {}

    # Test 1: VARCHAR vs INT joins
    print("\n[1/6] Testing VARCHAR player_key vs INT player_id join performance...")
    all_results["varchar_vs_int_joins"] = benchmark.test_varchar_vs_int_joins()
    if all_results["varchar_vs_int_joins"].get("performance_impact_pct") is not None:
        print(
            f"  ✓ VARCHAR impact: {all_results['varchar_vs_int_joins']['performance_impact_pct']:+.1f}%"
        )

    # Test 2: Crosswalk join overhead
    print("\n[2/6] Testing crosswalk join overhead...")
    all_results["crosswalk_overhead"] = benchmark.test_crosswalk_join_overhead()
    if all_results["crosswalk_overhead"].get("overhead_pct") is not None:
        print(f"  ✓ Crosswalk overhead: {all_results['crosswalk_overhead']['overhead_pct']:+.1f}%")

    # Test 3: Fact table aggregations
    print("\n[3/6] Testing large fact table aggregations...")
    all_results["fact_aggregations"] = benchmark.test_fact_table_aggregations()
    simple = all_results["fact_aggregations"]["simple_aggregation"]
    complex = all_results["fact_aggregations"]["complex_aggregation"]
    print(f"  ✓ Simple aggregation: {simple.get('avg_execution_time_sec', 0):.3f}s")
    print(f"  ✓ Complex aggregation: {complex.get('avg_execution_time_sec', 0):.3f}s")

    # Test 4: Window functions
    print("\n[4/6] Testing window function performance...")
    all_results["window_functions"] = benchmark.test_window_functions()
    print(
        f"  ✓ Window functions: {all_results['window_functions'].get('avg_execution_time_sec', 0):.3f}s"
    )

    # Test 5: Mart patterns
    print("\n[5/6] Testing analytics mart query patterns...")
    all_results["mart_patterns"] = benchmark.test_mart_query_patterns()
    print(f"  ✓ Mart query: {all_results['mart_patterns'].get('avg_execution_time_sec', 0):.3f}s")

    # Test 6: Concurrent queries
    print("\n[6/6] Testing concurrent query performance (3 simultaneous queries)...")
    all_results["concurrent_queries"] = benchmark.test_concurrent_queries(num_concurrent=3)
    print(f"  ✓ Total elapsed: {all_results['concurrent_queries']['total_elapsed_sec']:.3f}s")
    print(f"  ✓ Avg per query: {all_results['concurrent_queries']['avg_query_time_sec']:.3f}s")
    print(f"  ✓ All succeeded: {all_results['concurrent_queries']['all_succeeded']}")

    # Save results
    output_path = project_root / "scripts/performance/benchmark_results.json"
    with open(output_path, "w") as f:
        json.dump(all_results, f, indent=2, default=str)

    print(f"\n✓ Benchmark results saved to: {output_path}")

    # Save individual benchmark metrics
    benchmark.save_results(project_root / "scripts/performance/detailed_metrics.json")
    print(f"✓ Detailed metrics saved to: {project_root}/scripts/performance/detailed_metrics.json")

    print("\n" + "=" * 80)
    print("Benchmark complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()
