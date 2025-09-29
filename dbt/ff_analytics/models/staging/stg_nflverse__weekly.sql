{{ config(materialized='view') }}

-- Local development reads weekly snapshots from Parquet under data/raw.
-- Keep raw-like field names; minimal casting for stability.

with src as (
  select *
  from read_parquet(
    '{{ env_var("RAW_NFLVERSE_WEEKLY_GLOB", "data/raw/nflverse/weekly/dt=*/*.parquet") }}'
  )
)

select
  cast(season as int) as season,
  cast(week as int) as week,
  coalesce(cast(gsis_id as varchar), cast(player_id as varchar)) as gsis_id,
  team,
  position,
  player_name,
  attempts,
  completions,
  passing_yards,
  rushing_yards,
  receiving_yards
from src
where season is not null and week is not null and gsis_id is not null
;
