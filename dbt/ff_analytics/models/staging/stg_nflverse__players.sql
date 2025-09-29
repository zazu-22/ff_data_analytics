{{ config(materialized='view') }}

-- Local development reads all player snapshots from Parquet under data/raw.
-- Keep raw-like field names; minimal casting for stability.

with src as (
  select *
  from read_parquet(
    '{{ env_var("RAW_NFLVERSE_PLAYERS_GLOB", "data/raw/nflverse/players/dt=*/*.parquet") }}'
  )
)

select
  cast(gsis_id as varchar) as gsis_id,
  coalesce(full_name, name) as full_name,
  first_name,
  last_name,
  position,
  team,
  birth_date,
  college,
  height,
  weight
from src
where gsis_id is not null
;
