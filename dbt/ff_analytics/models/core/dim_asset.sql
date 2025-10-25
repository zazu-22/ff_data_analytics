{{
  config(
    materialized='table',
    tags=['core', 'dimension']
  )
}}

/*
Unified asset dimension combining players and draft picks.

Provides a single interface for trade analysis and market value queries,
eliminating the need to UNION players + picks in every downstream mart.

Grain: One row per asset (player or pick)
Source: UNION of dim_player + dim_pick (+ future: defense, cap_space)
*/

-- Players as assets
select
  'player_' || player_id as asset_id,
  'player' as asset_type,
  player_id,
  null as pick_id,
  display_name as asset_name,
  position,
  current_team as team,
  null as season,
  null as round,
  null as round_slot,
  'Active NFL player' as asset_category
from {{ ref('dim_player') }}

union all

-- Draft picks as assets
select
  'pick_' || pick_id as asset_id,
  'pick' as asset_type,
  null as player_id,
  pick_id,
  season || ' Round ' || round || ' Pick ' || round_slot as asset_name,
  null as position,
  null as team,
  season,
  round,
  round_slot,
  case
    when pick_type = 'compensatory' then 'Compensatory pick'
    when pick_type = 'rfa_compensation' then 'RFA compensation pick'
    else 'Standard draft pick'
  end as asset_category
from {{ ref('dim_pick') }}

-- Future: UNION additional asset types
-- - Defense assets (TEAM D/ST)
-- - Cap space (for trades involving salary cap)
