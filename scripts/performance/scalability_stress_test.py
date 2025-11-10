#!/usr/bin/env python3
"""Scalability Stress Testing for FF Analytics.

Tests performance with projected 10-year data volume:
- Current: 7.8M rows (2020-2025)
- Projected: 20M+ rows (10-year horizon)
- Growth rate: ~1.2M rows/year

Simulates scalability by:
1. Analyzing current growth patterns
2. Estimating 10-year database size
3. Testing queries on full dataset
4. Projecting performance degradation
"""

import json
import time
from pathlib import Path

import duckdb


class ScalabilityTester:
    """Test scalability limits for DuckDB database."""

    def __init__(self, duckdb_path: Path):
        self.duckdb_path = duckdb_path
        self.results = {}

    def analyze_current_growth(self) -> dict:
        """Analyze current data growth patterns."""
        con = duckdb.connect(str(self.duckdb_path), read_only=True)

        # Row count per season
        growth_by_season = con.execute("""
            SELECT
                season,
                COUNT(*) as row_count,
                COUNT(DISTINCT player_id) as player_count,
                COUNT(DISTINCT game_id) as game_count,
                COUNT(DISTINCT stat_name) as stat_count
            FROM main.fct_player_stats
            GROUP BY season
            ORDER BY season
        """).fetchdf()

        # Overall statistics
        total_stats = (
            con.execute("""
            SELECT
                COUNT(*) as total_rows,
                COUNT(DISTINCT player_id) as total_players,
                COUNT(DISTINCT game_id) as total_games,
                COUNT(DISTINCT stat_name) as total_stats,
                MIN(season) as min_season,
                MAX(season) as max_season
            FROM main.fct_player_stats
        """)
            .fetchdf()
            .iloc[0]
        )

        con.close()

        # Calculate growth rate
        years = growth_by_season["season"].nunique()
        total_rows = total_stats["total_rows"]
        rows_per_year = total_rows / years if years > 0 else 0

        return {
            "current_total_rows": int(total_rows),
            "current_players": int(total_stats["total_players"]),
            "current_games": int(total_stats["total_games"]),
            "current_stats": int(total_stats["total_stats"]),
            "season_range": f"{total_stats['min_season']}-{total_stats['max_season']}",
            "years_of_data": int(years),
            "avg_rows_per_year": int(rows_per_year),
            "growth_by_season": growth_by_season.to_dict(orient="records"),
        }

    def project_10year_volume(self, current_growth: dict) -> dict:
        """Project database size for 10-year horizon."""
        # Conservative estimate: assume linear growth
        years_to_add = 10 - current_growth["years_of_data"]
        projected_additional_rows = years_to_add * current_growth["avg_rows_per_year"]
        projected_total_rows = current_growth["current_total_rows"] + projected_additional_rows

        # Database size projection
        current_db_size_gb = self.duckdb_path.stat().st_size / 1024 / 1024 / 1024
        rows_to_gb_ratio = current_db_size_gb / current_growth["current_total_rows"]
        projected_db_size_gb = projected_total_rows * rows_to_gb_ratio

        return {
            "projected_years": 10,
            "years_to_add": int(years_to_add),
            "projected_additional_rows": int(projected_additional_rows),
            "projected_total_rows": int(projected_total_rows),
            "growth_multiplier": projected_total_rows / current_growth["current_total_rows"],
            "current_db_size_gb": round(current_db_size_gb, 2),
            "projected_db_size_gb": round(projected_db_size_gb, 2),
            "db_size_increase_pct": round(
                ((projected_db_size_gb - current_db_size_gb) / current_db_size_gb) * 100, 1
            ),
        }

    def test_full_dataset_queries(self) -> dict:
        """Test query performance on current full dataset."""
        con = duckdb.connect(str(self.duckdb_path), read_only=True)

        queries = {
            "full_table_scan": """
                SELECT
                    COUNT(*) as total_rows,
                    COUNT(DISTINCT player_id) as players,
                    COUNT(DISTINCT game_id) as games,
                    AVG(stat_value) as avg_stat_value
                FROM main.fct_player_stats
            """,
            "multi_year_aggregation": """
                SELECT
                    season,
                    position,
                    stat_name,
                    COUNT(DISTINCT player_id) as players,
                    SUM(stat_value) as total_value,
                    AVG(stat_value) as avg_value
                FROM main.fct_player_stats
                WHERE position IN ('QB', 'RB', 'WR', 'TE')
                GROUP BY season, position, stat_name
            """,
            "complex_join_aggregation": """
                SELECT
                    dp.display_name,
                    dp.position,
                    COUNT(DISTINCT fps.game_id) as career_games,
                    SUM(CASE WHEN fps.stat_name = 'passing_yards' THEN fps.stat_value END) as total_pass_yards,
                    SUM(CASE WHEN fps.stat_name = 'rushing_yards' THEN fps.stat_value END) as total_rush_yards,
                    SUM(CASE WHEN fps.stat_name = 'receiving_yards' THEN fps.stat_value END) as total_rec_yards,
                    SUM(CASE WHEN fps.stat_name = 'fantasy_points' THEN fps.stat_value END) as total_fantasy_points
                FROM main.dim_player dp
                JOIN main.fct_player_stats fps ON dp.player_id = fps.player_id
                WHERE dp.position IN ('QB', 'RB', 'WR', 'TE')
                GROUP BY dp.display_name, dp.position
                HAVING career_games >= 16
                ORDER BY total_fantasy_points DESC NULLS LAST
                LIMIT 500
            """,
            "window_function_full": """
                SELECT
                    player_id,
                    season,
                    week,
                    stat_value as fantasy_points,
                    AVG(stat_value) OVER (
                        PARTITION BY player_id
                        ORDER BY season, week
                        ROWS BETWEEN 7 PRECEDING AND CURRENT ROW
                    ) as rolling_8wk_avg,
                    RANK() OVER (
                        PARTITION BY season, week
                        ORDER BY stat_value DESC
                    ) as weekly_rank
                FROM main.fct_player_stats
                WHERE stat_name = 'fantasy_points'
                    AND position IN ('QB', 'RB', 'WR', 'TE')
                LIMIT 50000
            """,
        }

        results = {}
        for name, query in queries.items():
            start_time = time.time()
            try:
                result = con.execute(query).fetchdf()
                end_time = time.time()

                results[name] = {
                    "execution_time_sec": round(end_time - start_time, 3),
                    "row_count": len(result),
                    "success": True,
                }
            except Exception as e:
                results[name] = {"error": str(e), "success": False}

        con.close()
        return results

    def estimate_10year_performance(self, current_perf: dict, projection: dict) -> dict:
        """Estimate performance degradation with 10-year data volume."""
        # DuckDB performance typically degrades sub-linearly with data volume
        # For columnar databases, assume O(n log n) worst case for joins/aggregations
        growth_factor = projection["growth_multiplier"]

        import math

        performance_degradation_factor = growth_factor * math.log2(growth_factor)

        estimated_perf = {}
        for query_name, metrics in current_perf.items():
            if metrics.get("success"):
                current_time = metrics["execution_time_sec"]
                projected_time = current_time * performance_degradation_factor

                estimated_perf[query_name] = {
                    "current_time_sec": current_time,
                    "projected_time_sec": round(projected_time, 3),
                    "slowdown_factor": round(performance_degradation_factor, 2),
                    "meets_5sec_threshold": projected_time < 5.0,
                }

        return estimated_perf

    def test_memory_limits(self) -> dict:
        """Test memory usage patterns."""
        import psutil

        con = duckdb.connect(str(self.duckdb_path), read_only=True)
        process = psutil.Process()

        # Baseline memory
        baseline_mem_mb = process.memory_info().rss / 1024 / 1024

        # Large aggregation query
        start_mem = process.memory_info().rss / 1024 / 1024
        _ = con.execute("""
            SELECT
                player_id,
                season,
                stat_name,
                SUM(stat_value) as total,
                AVG(stat_value) as avg,
                COUNT(*) as count
            FROM main.fct_player_stats
            GROUP BY player_id, season, stat_name
        """).fetchdf()
        peak_mem = process.memory_info().rss / 1024 / 1024

        con.close()

        return {
            "baseline_memory_mb": round(baseline_mem_mb, 1),
            "peak_memory_mb": round(peak_mem, 1),
            "memory_delta_mb": round(peak_mem - start_mem, 1),
            "system_memory_gb": round(psutil.virtual_memory().total / 1024 / 1024 / 1024, 1),
            "memory_available_gb": round(psutil.virtual_memory().available / 1024 / 1024 / 1024, 1),
        }

    def run_comprehensive_test(self) -> dict:
        """Run all scalability tests."""
        print("=" * 80)
        print("Scalability Stress Testing")
        print("=" * 80)

        # Step 1: Analyze current growth
        print("\n[1/5] Analyzing current data growth patterns...")
        current_growth = self.analyze_current_growth()
        print(
            f"  ✓ Current data: {current_growth['current_total_rows']:,} rows ({current_growth['season_range']})"
        )
        print(f"  ✓ Growth rate: ~{current_growth['avg_rows_per_year']:,} rows/year")

        # Step 2: Project 10-year volume
        print("\n[2/5] Projecting 10-year data volume...")
        projection = self.project_10year_volume(current_growth)
        print(f"  ✓ Projected total: {projection['projected_total_rows']:,} rows")
        print(f"  ✓ Growth multiplier: {projection['growth_multiplier']:.1f}x")
        print(f"  ✓ Projected DB size: {projection['projected_db_size_gb']:.1f} GB")

        # Step 3: Test current performance
        print("\n[3/5] Testing query performance on current dataset...")
        current_perf = self.test_full_dataset_queries()
        for name, metrics in current_perf.items():
            if metrics.get("success"):
                print(
                    f"  ✓ {name}: {metrics['execution_time_sec']:.3f}s ({metrics['row_count']} rows)"
                )

        # Step 4: Estimate 10-year performance
        print("\n[4/5] Estimating performance with 10-year data volume...")
        estimated_perf = self.estimate_10year_performance(current_perf, projection)
        for name, metrics in estimated_perf.items():
            threshold_met = "✓" if metrics["meets_5sec_threshold"] else "✗"
            print(
                f"  {threshold_met} {name}: {metrics['current_time_sec']:.3f}s → {metrics['projected_time_sec']:.3f}s"
            )

        # Step 5: Memory analysis
        print("\n[5/5] Testing memory usage patterns...")
        memory_metrics = self.test_memory_limits()
        print(f"  ✓ Peak memory: {memory_metrics['peak_memory_mb']:.1f} MB")
        print(f"  ✓ System memory: {memory_metrics['system_memory_gb']:.1f} GB")

        # Compile results
        results = {
            "current_growth": current_growth,
            "projection_10year": projection,
            "current_performance": current_perf,
            "estimated_10year_performance": estimated_perf,
            "memory_analysis": memory_metrics,
            "scalability_assessment": {
                "can_handle_10year_volume": all(
                    m.get("meets_5sec_threshold", False) for m in estimated_perf.values()
                ),
                "bottleneck_queries": [
                    name
                    for name, m in estimated_perf.items()
                    if not m.get("meets_5sec_threshold", False)
                ],
                "recommendations": self._generate_recommendations(
                    projection, estimated_perf, memory_metrics
                ),
            },
        }

        return results

    def _generate_recommendations(self, projection: dict, perf: dict, memory: dict) -> list:
        """Generate scalability recommendations."""
        recommendations = []

        # Database size check
        if projection["projected_db_size_gb"] > 5.0:
            recommendations.append(
                {
                    "area": "Database Size",
                    "issue": f"Projected size of {projection['projected_db_size_gb']:.1f} GB may impact performance",
                    "recommendation": "Consider partitioning strategy or data retention policy",
                }
            )

        # Query performance check
        slow_queries = [
            name for name, m in perf.items() if not m.get("meets_5sec_threshold", False)
        ]
        if slow_queries:
            recommendations.append(
                {
                    "area": "Query Performance",
                    "issue": f"Queries projected to exceed 5s threshold: {', '.join(slow_queries)}",
                    "recommendation": "Add indexes, materialize intermediate results, or optimize query patterns",
                }
            )

        # Memory check
        if memory["peak_memory_mb"] > 1000:
            recommendations.append(
                {
                    "area": "Memory Usage",
                    "issue": f"Peak memory usage of {memory['peak_memory_mb']:.0f} MB with current data",
                    "recommendation": "Monitor memory usage; consider query optimization or batching for large aggregations",
                }
            )

        # Growth rate check
        if projection["growth_multiplier"] > 3.0:
            recommendations.append(
                {
                    "area": "Data Growth",
                    "issue": f"Data volume will grow {projection['growth_multiplier']:.1f}x over 10 years",
                    "recommendation": "Implement incremental processing and archival strategy for historical data",
                }
            )

        return recommendations


def main():
    """Run scalability stress testing."""
    project_root = Path("/Users/jason/code/ff_analytics")
    duckdb_path = project_root / "dbt/ff_data_transform/target/dev.duckdb"

    if not duckdb_path.exists():
        print(f"Error: DuckDB database not found at {duckdb_path}")
        return

    tester = ScalabilityTester(duckdb_path)
    results = tester.run_comprehensive_test()

    # Save results
    output_path = project_root / "scripts/performance/scalability_results.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\n✓ Results saved to: {output_path}")

    # Print summary
    print("\n" + "=" * 80)
    print("Scalability Assessment Summary")
    print("=" * 80)
    assessment = results["scalability_assessment"]
    print(
        f"\nCan handle 10-year volume: {'✓ YES' if assessment['can_handle_10year_volume'] else '✗ NO'}"
    )

    if assessment["bottleneck_queries"]:
        print(f"\nBottleneck queries: {', '.join(assessment['bottleneck_queries'])}")

    print("\nRecommendations:")
    for i, rec in enumerate(assessment["recommendations"], 1):
        print(f"\n{i}. {rec['area']}")
        print(f"   Issue: {rec['issue']}")
        print(f"   → {rec['recommendation']}")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
