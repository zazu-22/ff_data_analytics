-- Performance Analysis: Database Statistics
-- Gather baseline metrics for DuckDB database

-- Table row counts and sizes
SELECT
    table_name,
    estimated_size as row_count,
    round(column_count, 0) as column_count,
    round(total_compressed_size / 1024.0 / 1024.0, 2) as size_mb
FROM duckdb_tables()
WHERE schema_name = 'main'
ORDER BY total_compressed_size DESC
LIMIT 50;

-- Fact table grain analysis
SELECT
    'fct_player_stats' as table_name,
    count(*) as total_rows,
    count(DISTINCT player_key) as distinct_players,
    count(DISTINCT game_id) as distinct_games,
    count(DISTINCT stat_name) as distinct_stats,
    count(DISTINCT provider) as distinct_providers,
    min(season) as min_season,
    max(season) as max_season
FROM main.fct_player_stats;

-- Player dimension size
SELECT
    'dim_player' as table_name,
    count(*) as total_rows,
    count(DISTINCT player_id) as distinct_player_ids,
    count(DISTINCT position) as distinct_positions
FROM main.dim_player;

-- Crosswalk table analysis
SELECT
    'dim_player_id_xref' as table_name,
    count(*) as total_rows,
    count(DISTINCT player_id) as distinct_canonical_ids,
    count(DISTINCT mfl_id) as distinct_mfl_ids,
    count(DISTINCT sleeper_player_id) as distinct_sleeper_ids,
    count(DISTINCT gsis_id) as distinct_gsis_ids
FROM main.dim_player_id_xref;

-- Memory usage statistics
SELECT * FROM pragma_database_size();

-- Check for indexes
SELECT * FROM duckdb_indexes() WHERE schema_name = 'main';
