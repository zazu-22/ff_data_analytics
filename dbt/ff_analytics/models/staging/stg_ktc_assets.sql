{{ config(materialized='view') }}

/*
Stage KeepTradeCut dynasty market values for players and picks.

Source: data/raw/ktc/{players,picks}/ (KTC dynasty rankings scraper)
Output grain: one row per asset per market_scope per asof_date
Crosswalk: player_name → mfl_id via dim_player_id_xref (for players only)

Key transformations:
- UNION players and picks into unified asset table
- Map player names to canonical player_id (using merge_name for fuzzy matching)
- Use player_key for grain uniqueness (handles unmapped players)
- Preserve pick identity (no mapping needed)
- Normalize asset_type enum ('player', 'pick')

NULL filtering: Players with no matching player_id in crosswalk are preserved
with player_id = -1 and player_key = player_name for identity preservation.

Mapping coverage: To be documented after sample testing.

Data source: KeepTradeCut (https://keeptradecut.com/dynasty-rankings)
Attribution: Per KTC usage guidelines, data sourced with attribution.
*/

with players_raw as (
  select
    player_name,
    position,
    team as current_team,
    asset_type,
    rank,
    value as ktc_value,
    positional_rank,
    market_scope,
    asof_date
  from read_parquet(
    '{{ var("external_root", "data/raw") }}/ktc/players/dt=*/*.parquet',
    hive_partitioning = true
  )
),

picks_raw as (
  select
    pick_name,
    draft_year,
    pick_tier,
    pick_round,
    asset_type,
    rank,
    value as ktc_value,
    market_scope,
    asof_date
  from read_parquet(
    '{{ var("external_root", "data/raw") }}/ktc/picks/dt=*/*.parquet',
    hive_partitioning = true
  )
),

-- Map player names to canonical player_id via crosswalk
players_mapped as (
  select
    p.player_name,
    p.position,
    p.current_team,
    p.asset_type,
    p.rank,
    p.ktc_value,
    p.positional_rank,
    p.market_scope,
    p.asof_date,
    -- Map player_name → mfl_id using merge_name for fuzzy matching
    -- merge_name is normalized (lowercase, no punctuation) for better matching
    coalesce(xref.mfl_id, -1) as player_id,
    -- Player key for grain uniqueness
    -- Mapped players: player_key = mfl_id (as varchar)
    -- Unmapped players: player_key = player_name (preserves identity)
    case
      when coalesce(xref.mfl_id, -1) != -1
        then cast(xref.mfl_id as varchar)
      else coalesce(p.player_name, 'UNKNOWN_' || cast(p.rank as varchar))
    end as player_key,
    -- Null fields for picks (union compatibility)
    cast(null as integer) as draft_year,
    cast(null as varchar) as pick_tier,
    cast(null as integer) as pick_round,
    cast(null as varchar) as pick_name
  from players_raw as p
  left join {{ ref('dim_player_id_xref') }} as xref
    -- Use merge_name for better matching (handles case differences, punctuation)
    on
      lower(trim(p.player_name)) = lower(trim(xref.merge_name))
      or lower(trim(p.player_name)) = lower(trim(xref.name))
),

-- Picks don't need player mapping, create compatible structure
picks_normalized as (
  select
    pick_name as asset_name,
    cast(null as varchar) as position,
    cast(null as varchar) as current_team,
    asset_type,
    rank,
    ktc_value,
    cast(null as integer) as positional_rank,
    market_scope,
    asof_date,
    -1 as player_id,  -- Picks don't have player_id
    -- Pick key: use pick_name for identity
    pick_name as player_key,
    draft_year,
    pick_tier,
    pick_round,
    pick_name
  from picks_raw
),

-- Convert players to same schema
players_normalized as (
  select
    player_name as asset_name,
    position,
    current_team,
    asset_type,
    rank,
    ktc_value,
    positional_rank,
    market_scope,
    asof_date,
    player_id,
    player_key,
    draft_year,
    pick_tier,
    pick_round,
    pick_name
  from players_mapped
),

-- Union players and picks
unified as (
  select * from players_normalized
  union all
  select * from picks_normalized
)

select
  asset_name,
  position,
  current_team,
  asset_type,
  rank as overall_rank,
  ktc_value,
  positional_rank,
  market_scope,
  asof_date,
  player_id,
  player_key,
  draft_year,
  pick_tier,
  pick_round,
  pick_name,
  -- Add metadata
  'keeptradecut' as provider,
  current_timestamp as loaded_at
from unified
