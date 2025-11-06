-- Ensure fallback matching maintains data integrity
--
-- Purpose: Validate that fallback matching for sleeper_id duplicates doesn't create
-- new duplicates or incorrect mappings. This test ensures:
-- 1. Corrected sleeper_ids don't create duplicate mappings
-- 2. Corrected sleeper_ids exist in Sleeper players database
-- 3. Status values match actual ID states (sentinel vs real ID)
--
-- Expected: Zero violations
-- If violations exist: Fallback matching logic needs review

with fallback_duplicates as (
  -- Check that corrected sleeper_ids don't create duplicates
  select
    'fallback_created_duplicate' as violation_type,
    cast(sleeper_id as varchar) as id_value,
    string_agg(cast(player_id as varchar), ', ' order by player_id) as player_id_col,
    string_agg(cast(player_id as varchar), ', ' order by player_id) as player_ids,
    string_agg(distinct name, ' | ') as player_names
  from {{ ref('stg_nflverse__ff_playerids') }}
  where sleeper_id != -1
    and sleeper_id is not null
    and xref_correction_status = 'corrected_sleeper_id'
  group by sleeper_id
  having count(*) > 1
),

fallback_invalid_ids as (
  -- Check that corrected sleeper_ids exist in Sleeper players database
  select
    'fallback_id_not_in_sleeper_db' as violation_type,
    cast(x.sleeper_id as varchar) as id_value,
    cast(x.player_id as varchar) as player_id_col,
    cast(x.player_id as varchar) as player_ids,
    x.name as player_names
  from {{ ref('stg_nflverse__ff_playerids') }} x
  left join read_parquet(
    '{{ var("external_root", "data/raw") }}/sleeper/players/dt=*/players_*.parquet',
    hive_partitioning = true
  ) sp
    on x.sleeper_id = try_cast(sp.sleeper_player_id as integer)
  where x.xref_correction_status = 'corrected_sleeper_id'
    and sp.sleeper_player_id is null
),

status_id_mismatch as (
  -- Check that status values match actual ID states
  select
    'status_id_mismatch' as violation_type,
    cast(sleeper_id as varchar) as id_value,
    cast(player_id as varchar) as player_id_col,
    cast(player_id as varchar) as player_ids,
    case
      when sleeper_id = -1 and xref_correction_status = 'corrected_sleeper_id'
        then 'corrected_sleeper_id but sleeper_id is sentinel'
      when sleeper_id != -1 and sleeper_id is not null and xref_correction_status = 'cleared_sleeper_duplicate'
        then 'cleared_sleeper_duplicate but sleeper_id is not sentinel'
      else null
    end as player_names
  from {{ ref('stg_nflverse__ff_playerids') }}
  where (
    (sleeper_id = -1 and xref_correction_status = 'corrected_sleeper_id')
    or (sleeper_id != -1 and sleeper_id is not null and xref_correction_status = 'cleared_sleeper_duplicate')
  )
)

select *
from fallback_duplicates

union all

select *
from fallback_invalid_ids

union all

select *
from status_id_mismatch
where player_names is not null

order by violation_type, id_value

