{% macro latest_snapshot_only(source_path) %}
  {#
  WHERE clause to keep only rows from the latest snapshot date.

  Filters to MAX(dt) from the same source data to ensure idempotent reads
  when multiple snapshots exist.

  Args:
    source_path: Path pattern for the parquet files (e.g., 'data/raw/nflverse/weekly/dt=*/*.parquet')

  Usage in staging models:
    SELECT * FROM read_parquet('path/dt=*/*.parquet', hive_partitioning=true) w
    WHERE ...
      AND {{ latest_snapshot_only('path/dt=*/*.parquet') }}

  This ensures idempotent reads when multiple snapshots exist (e.g., weekly data
  loaded multiple times creates dt=2024-01-01 and dt=2025-10-01 with overlapping weeks).
  #}
  dt = (
    select max(dt)
    from read_parquet('{{ source_path }}', hive_partitioning=true)
  )
{% endmacro %}
