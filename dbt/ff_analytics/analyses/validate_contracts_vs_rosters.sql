/*
Validation script: Cross-reference current contracts with commissioner roster sheets

Purpose: Ensure dim_player_contract_history matches actual roster contract data

Prerequisites:
- Commissioner sheet data must be loaded
- stg_sheets__roster tables must exist

Validation checks:
1. Players on rosters have corresponding current contracts
2. Current contracts have corresponding roster entries
3. Contract amounts match between history and roster
4. Contract years match between history and roster
5. Franchise ownership matches
*/

-- Check 1: Roster players without contract history
-- This query will work when roster staging tables are implemented
{% set roster_check_enabled = false %}

{% if roster_check_enabled %}

with roster_players as (
  -- This will be uncommented when stg_sheets__roster is implemented
  -- select distinct
  --   player_id,
  --   franchise_id,
  --   contract_years,
  --   contract_amount,
  --   position
  -- from {{ ref('stg_sheets__roster') }}
  -- where player_id is not null
  --   and player_id != -1
  select 1 as placeholder  -- Temporary placeholder
),

current_contracts as (
  select
    player_id,
    player_name,
    franchise_id,
    franchise_name,
    contract_type,
    contract_total,
    contract_years,
    annual_amount,
    contract_start_season,
    contract_end_season,
    is_current
  from {{ ref('dim_player_contract_history') }}
  where is_current = true
)

-- Find roster players without contract history
select
  'Players on Roster Without Contracts' as issue_type,
  count(*) as count
-- from roster_players rp
-- left join current_contracts cc on rp.player_id = cc.player_id
-- where cc.player_id is null
from (select 1 as placeholder) dummy  -- Temporary
where false  -- Disabled until roster staging exists

union all

-- Find contracts without roster entries
select
  'Contracts Without Roster Entry' as issue_type,
  count(*) as count
-- from current_contracts cc
-- left join roster_players rp on cc.player_id = rp.player_id
-- where rp.player_id is null
from (select 1 as placeholder) dummy  -- Temporary
where false  -- Disabled until roster staging exists

{% else %}

-- Roster validation disabled - roster staging not yet implemented
select
  'VALIDATION SKIPPED' as status,
  'Roster staging tables not yet implemented' as reason,
  null as count
from (select 1) dummy

{% endif %}
