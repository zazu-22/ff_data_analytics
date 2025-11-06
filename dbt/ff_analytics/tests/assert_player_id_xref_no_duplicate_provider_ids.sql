-- Ensure dim_player_id_xref has no duplicate provider IDs
--
-- Purpose: Detect when the same sleeper_id, mfl_id, or gsis_id maps to multiple player_ids
-- This causes cascading issues throughout the pipeline when joining on these IDs
--
-- Expected: Zero violations (each provider ID should be unique)
-- If violations exist: Crosswalk needs manual correction to resolve conflicts

with duplicate_checks as (
  -- Check sleeper_id duplicates
  select
    'sleeper_id' as id_type,
    sleeper_id::varchar as id_value,
    count(*) as player_count,
    string_agg(player_id::varchar, ', ' order by player_id) as player_ids,
    string_agg(distinct name, ' | ') as player_names,
    string_agg(distinct position, ', ') as positions,
    string_agg(distinct birthdate::varchar, ' | ') as birthdates
  from {{ ref('dim_player_id_xref') }}
  where sleeper_id is not null
  group by sleeper_id
  having count(*) > 1

  union all

  -- Check mfl_id duplicates
  select
    'mfl_id' as id_type,
    mfl_id::varchar as id_value,
    count(*) as player_count,
    string_agg(player_id::varchar, ', ' order by player_id) as player_ids,
    string_agg(distinct name, ' | ') as player_names,
    string_agg(distinct position, ', ') as positions,
    string_agg(distinct birthdate::varchar, ' | ') as birthdates
  from {{ ref('dim_player_id_xref') }}
  where mfl_id is not null
  group by mfl_id
  having count(*) > 1

  union all

  -- Check gsis_id duplicates
  select
    'gsis_id' as id_type,
    gsis_id::varchar as id_value,
    count(*) as player_count,
    string_agg(player_id::varchar, ', ' order by player_id) as player_ids,
    string_agg(distinct name, ' | ') as player_names,
    string_agg(distinct position, ', ') as positions,
    string_agg(distinct birthdate::varchar, ' | ') as birthdates
  from {{ ref('dim_player_id_xref') }}
  where gsis_id is not null
  group by gsis_id
  having count(*) > 1
)

select *
from duplicate_checks
order by id_type, player_count desc, id_value
