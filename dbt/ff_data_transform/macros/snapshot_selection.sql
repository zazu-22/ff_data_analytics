{% macro snapshot_selection_strategy(source_glob, strategy='latest_only', baseline_dt=none) %}
  {#
  Flexible snapshot selection macro supporting multiple strategies.

  Eliminates hardcoded snapshot dates in staging models by providing
  a parameterizable approach to snapshot selection that can be configured
  via dbt vars and environment variables.

  Args:
    source_glob: Path pattern for parquet files (e.g., 'data/raw/nflverse/weekly/dt=*/*.parquet')
    strategy: Selection strategy - one of:
      - 'latest_only': Select only the most recent snapshot (default)
      - 'baseline_plus_latest': Select baseline snapshot + latest for historical continuity
      - 'all': No filter (load all snapshots for backfills)
    baseline_dt: Required for 'baseline_plus_latest' strategy (e.g., '2024-10-01')

  Usage in staging models:

    -- Latest only (default)
    SELECT * FROM read_parquet('path/dt=*/*.parquet', hive_partitioning=true) w
    WHERE {{ snapshot_selection_strategy(source_glob) }}

    -- Baseline + latest for NFLverse (historical continuity)
    SELECT * FROM read_parquet('path/dt=*/*.parquet', hive_partitioning=true) w
    WHERE {{ snapshot_selection_strategy(source_glob, 'baseline_plus_latest', '2024-10-01') }}

    -- All snapshots (backfills)
    SELECT * FROM read_parquet('path/dt=*/*.parquet', hive_partitioning=true) w
    WHERE {{ snapshot_selection_strategy(source_glob, 'all') }}

  Strategy Details:

    latest_only:
      - Filters to MAX(dt) from source data
      - Ensures idempotent reads when multiple snapshots exist
      - Best for: Sheets, KTC, FFAnalytics, Sleeper (current state only)

    baseline_plus_latest:
      - Selects baseline snapshot (historical anchor) + latest snapshot
      - Maintains historical continuity while incorporating new data
      - Best for: NFLverse (preserve historical stats, add current season)
      - Requires baseline_dt parameter

    all:
      - No dt filter applied (reads all snapshots)
      - Best for: Backfills, historical analysis, debugging
      - Use with caution (may cause duplicates if not deduplicated downstream)

  Relationship to latest_snapshot_only() helper:
    This macro calls the existing latest_snapshot_only() helper for the 'latest_only'
    strategy, ensuring a single source of truth for "latest" logic. Both helpers remain
    available for use:
      - Use latest_snapshot_only() directly for simple "just get latest" cases
      - Use snapshot_selection_strategy() for flexible multi-strategy needs
  #}
  {% if strategy == 'latest_only' %}
    {# Select only the most recent snapshot #}
    {{ latest_snapshot_only(source_glob) }}
  {% elif strategy == 'baseline_plus_latest' %}
    {# Select baseline snapshot + latest (for historical continuity) #}
    {% if baseline_dt is none %}
      {{ exceptions.raise_compiler_error("baseline_dt is required for 'baseline_plus_latest' strategy") }}
    {% endif %}
    (dt = '{{ baseline_dt }}' or {{ latest_snapshot_only(source_glob) }})
  {% elif strategy == 'all' %}
    {# No filter (load all snapshots for backfills) #}
    1=1
  {% else %}
    {{ exceptions.raise_compiler_error("Invalid strategy '" ~ strategy ~ "'. Must be one of: latest_only, baseline_plus_latest, all") }}
  {% endif %}
{% endmacro %}
