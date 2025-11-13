{{ config(severity='error') }}

-- Test: Detect name collision merging in projections
-- Fails if same player_name + position has multiple teams but same player_id
--
-- CONTEXT: FFAnalytics consensus calculation should group by (player, pos, week, team)
-- to avoid merging different players with same name (e.g., Jordan Phillips BUF vs MIA)
--
-- This test catches the bug fixed in 2025-11-13 where the R script grouped without team,
-- causing different players with same name to be merged with averaged stats.
--
-- EXPECTED: Each unique (player_name, position, team) should map to a unique player_id
-- FAILURE: Same player_id appears with multiple teams = name collision merging occurred

with player_team_combos as (
  select
    player_id,
    player_name,
    position,
    current_team,
    count(distinct week) as weeks_affected
  from {{ ref('stg_ffanalytics__projections') }}
  where player_id > 0  -- Exclude unmapped players
  group by player_id, player_name, position, current_team
),

collision_candidates as (
  select
    player_name,
    position,
    count(distinct player_id) as player_id_count,
    count(distinct current_team) as team_count,
    array_agg(distinct player_id order by player_id) as player_ids,
    array_agg(distinct current_team order by current_team) as teams
  from player_team_combos
  group by player_name, position
  having count(distinct current_team) > 1  -- Same name, multiple teams
),

name_collision_errors as (
  select
    player_name,
    position,
    player_id_count,
    team_count,
    player_ids,
    teams,
    case
      when player_id_count = 1 and team_count > 1 then 'NAME_COLLISION_MERGE'
      when player_id_count = team_count then 'OK_SEPARATE_PLAYERS'
      else 'UNEXPECTED_PATTERN'
    end as status
  from collision_candidates
)

-- Return only actual merging errors
select
  player_name,
  position,
  player_ids,
  teams,
  team_count,
  'ERROR: Different teams merged to same player_id' as error_message
from name_collision_errors
where status = 'NAME_COLLISION_MERGE'
order by player_name, position
