-- Performance Analysis: Query Execution Plans and Timing
-- Tests for specific performance concerns identified in Phase 1

-- ============================================================================
-- Test 1: VARCHAR vs INT Join Performance (fct_player_stats.player_key)
-- ============================================================================

-- Enable profiling and timing
.timer on

-- Baseline: Join on VARCHAR player_key (current implementation)
EXPLAIN ANALYZE
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
LIMIT 100;

-- ============================================================================
-- Test 2: Crosswalk Join Overhead (dim_player_id_xref)
-- ============================================================================

-- Check if crosswalk is being joined multiple times in typical query patterns
EXPLAIN ANALYZE
SELECT
    xref.player_id,
    xref.player_key,
    xref.mfl_id,
    xref.sleeper_id,
    dp.player_name,
    dp.position
FROM main.dim_player_id_xref xref
INNER JOIN main.dim_player dp ON xref.player_id = dp.player_id
WHERE xref.mfl_id IS NOT NULL
    AND dp.position IN ('QB', 'RB', 'WR', 'TE');

-- ============================================================================
-- Test 3: Large Fact Table Aggregation (typical analytics query)
-- ============================================================================

EXPLAIN ANALYZE
SELECT
    fps.season,
    fps.week,
    fps.position,
    fps.stat_name,
    COUNT(DISTINCT fps.player_key) as player_count,
    SUM(fps.stat_value_num) as total_value,
    AVG(fps.stat_value_num) as avg_value,
    MAX(fps.stat_value_num) as max_value
FROM main.fct_player_stats fps
WHERE fps.season >= 2023
    AND fps.position IN ('QB', 'RB', 'WR', 'TE')
    AND fps.stat_name IN ('passing_yards', 'rushing_yards', 'receiving_yards', 'receptions', 'targets')
GROUP BY fps.season, fps.week, fps.position, fps.stat_name
ORDER BY fps.season DESC, fps.week DESC;

-- ============================================================================
-- Test 4: Complex Mart Query Performance (mrt_fasa_targets pattern)
-- ============================================================================

EXPLAIN ANALYZE
SELECT
    fa.player_key,
    fa.player_name,
    fa.position,
    fa.age,
    COUNT(DISTINCT fps.game_id) as games_played,
    AVG(fps.stat_value_num) FILTER (WHERE fps.stat_name = 'fantasy_points') as avg_fantasy_points,
    SUM(fps.stat_value_num) FILTER (WHERE fps.stat_name = 'targets') as total_targets,
    SUM(fps.stat_value_num) FILTER (WHERE fps.stat_name = 'receptions') as total_receptions
FROM main.stg_sleeper__fa_pool fa
LEFT JOIN main.fct_player_stats fps
    ON fa.player_key = fps.player_key
    AND fps.season = YEAR(CURRENT_DATE)
WHERE fa.position IN ('WR', 'TE', 'RB')
GROUP BY fa.player_key, fa.player_name, fa.position, fa.age
HAVING COUNT(DISTINCT fps.game_id) >= 4
ORDER BY avg_fantasy_points DESC NULLS LAST
LIMIT 50;

-- ============================================================================
-- Test 5: Window Function Performance (ranking/partitioning)
-- ============================================================================

EXPLAIN ANALYZE
SELECT
    player_key,
    season,
    week,
    stat_name,
    stat_value_num,
    ROW_NUMBER() OVER (PARTITION BY player_key, stat_name ORDER BY season DESC, week DESC) as recency_rank,
    AVG(stat_value_num) OVER (
        PARTITION BY player_key, stat_name
        ORDER BY season, week
        ROWS BETWEEN 3 PRECEDING AND CURRENT ROW
    ) as rolling_avg_4wk
FROM main.fct_player_stats
WHERE season >= 2024
    AND position IN ('QB', 'RB', 'WR', 'TE')
    AND stat_name = 'fantasy_points'
ORDER BY player_key, season DESC, week DESC
LIMIT 1000;

-- ============================================================================
-- Test 6: Unpivot Performance (stg_nflverse__player_stats pattern)
-- ============================================================================

-- Simulate unpivot operation on wide table
-- Note: This would require access to raw parquet data in actual staging model
SELECT 'Unpivot test skipped - requires read_parquet from staging model' as note;

-- ============================================================================
-- Test 7: Index Effectiveness Check
-- ============================================================================

-- Check if indexes exist on foreign keys
SELECT
    table_name,
    index_name,
    expressions,
    is_unique
FROM duckdb_indexes()
WHERE schema_name = 'main'
    AND table_name IN ('fct_player_stats', 'fct_player_projections', 'dim_player_id_xref')
ORDER BY table_name, expressions;

-- ============================================================================
-- Test 8: Memory and Cache Statistics
-- ============================================================================

SELECT * FROM pragma_database_size();

-- Show table sizes for top 10 largest tables
SELECT
    table_name,
    estimated_size as estimated_rows,
    column_count,
    database_size
FROM duckdb_tables()
WHERE schema_name = 'main'
ORDER BY estimated_size DESC
LIMIT 10;
