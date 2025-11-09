-- Ensure Sleeper roster snapshot matches commissioner contract snapshot for current season
with sleeper_roster as (
  select distinct player_id
  from {{ ref('stg_sleeper__rosters') }}
  where player_id is not null
),
commissioner_cut as (
  select distinct player_id,
    franchise_id,
    obligation_year
  from {{ ref('stg_sheets__contracts_cut') }}
  where player_id is not null
    and player_id != -1
    and franchise_id is not null
),
commissioner_active as (
  select distinct player_id,
    franchise_id
  from {{ ref('stg_sheets__contracts_active') }}
  where player_id is not null
    and player_id != -1
),
commissioner_roster as (
  select distinct c.player_id
  from {{ ref('mrt_contract_snapshot_current') }} c
  where c.obligation_year = year(current_date)
    and (
      not exists (
        select 1
        from commissioner_cut cc
        where cc.player_id = c.player_id
          and cc.franchise_id = c.franchise_id
          and cc.obligation_year = c.obligation_year
      )
      or exists (
        select 1
        from commissioner_active ca
        where ca.player_id = c.player_id
          and ca.franchise_id = c.franchise_id
      )
    )
),
mismatches as (
  select player_id,
    'sleeper_only' as discrepancy_source
  from sleeper_roster
  except
  select player_id,
    'sleeper_only'
  from commissioner_roster
  union all
  select player_id,
    'commissioner_only' as discrepancy_source
  from commissioner_roster
  except
  select player_id,
    'commissioner_only'
  from sleeper_roster
)
select *
from mismatches
