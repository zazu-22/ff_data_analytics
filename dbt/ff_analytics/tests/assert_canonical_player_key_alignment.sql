-- Ensure all player-centric tables use canonical player_id for player_key when mapped
--
-- Pattern: When player_id exists (and != -1), player_key MUST equal cast(player_id as varchar)
-- This test validates the canonical player identifier contract across staging, fact, and mart layers.
--
-- Exclusions:
-- - mart_fasa_targets: player_key intentionally preserved from Sleeper source for reference
--
-- Coverage (15 tables):
-- Staging: 8 tables (sheets, sleeper, nflverse, ktc)
-- Facts: 3 tables (stats, transactions, market values)
-- Marts: 4 tables (contract history, FA acquisition, actuals)

with checks as (
  -- ====================
  -- STAGING LAYER
  -- ====================

  -- Commissioner sheets (3 tables)
  select 'stg_sheets__contracts_active' as table_name,
    count(*) as violations
  from {{ ref('stg_sheets__contracts_active') }}
  where player_id is not null
    and player_id != -1
    and cast(player_key as varchar) <> cast(player_id as varchar)

  union all

  select 'stg_sheets__contracts_cut' as table_name,
    count(*) as violations
  from {{ ref('stg_sheets__contracts_cut') }}
  where player_id is not null
    and player_id != -1
    and cast(player_key as varchar) <> cast(player_id as varchar)

  union all

  select 'stg_sheets__transactions' as table_name,
    count(*) as violations
  from {{ ref('stg_sheets__transactions') }}
  where asset_type = 'player'
    and player_id is not null
    and player_id != -1
    and cast(player_key as varchar) <> cast(player_id as varchar)

  union all

  -- Sleeper API (1 table)
  select 'stg_sleeper__fa_pool' as table_name,
    count(*) as violations
  from {{ ref('stg_sleeper__fa_pool') }}
  where player_id is not null
    and player_id != -1
    and cast(player_key as varchar) <> cast(player_id as varchar)

  union all

  -- NFLverse stats (3 tables)
  select 'stg_nflverse__player_stats' as table_name,
    count(*) as violations
  from {{ ref('stg_nflverse__player_stats') }}
  where player_id is not null
    and player_id != -1
    and cast(player_key as varchar) <> cast(player_id as varchar)

  union all

  select 'stg_nflverse__snap_counts' as table_name,
    count(*) as violations
  from {{ ref('stg_nflverse__snap_counts') }}
  where player_id is not null
    and player_id != -1
    and cast(player_key as varchar) <> cast(player_id as varchar)

  union all

  select 'stg_nflverse__ff_opportunity' as table_name,
    count(*) as violations
  from {{ ref('stg_nflverse__ff_opportunity') }}
  where player_id is not null
    and player_id != -1
    and cast(player_key as varchar) <> cast(player_id as varchar)

  union all

  -- KTC market data (1 table)
  select 'stg_ktc_assets' as table_name,
    count(*) as violations
  from {{ ref('stg_ktc_assets') }}
  where asset_type = 'player'
    and player_id is not null
    and player_id != -1
    and cast(player_key as varchar) <> cast(player_id as varchar)

  union all

  -- ====================
  -- FACT LAYER
  -- ====================

  select 'fact_player_stats' as table_name,
    count(*) as violations
  from {{ ref('fact_player_stats') }}
  where player_id is not null
    and player_id != -1
    and cast(player_key as varchar) <> cast(player_id as varchar)

  union all

  select 'fact_league_transactions' as table_name,
    count(*) as violations
  from {{ ref('fact_league_transactions') }}
  where asset_type = 'player'
    and player_id is not null
    and player_id != -1
    and cast(player_key as varchar) <> cast(player_id as varchar)

  union all

  select 'fact_asset_market_values' as table_name,
    count(*) as violations
  from {{ ref('fact_asset_market_values') }}
  where asset_type = 'player'
    and player_id is not null
    and player_id != -1
    and cast(player_key as varchar) <> cast(player_id as varchar)

  union all

  -- ====================
  -- MART LAYER
  -- ====================

  select 'mart_contract_snapshot_history' as table_name,
    count(*) as violations
  from {{ ref('mart_contract_snapshot_history') }}
  where player_id is not null
    and player_id != -1
    and cast(player_key as varchar) <> cast(player_id as varchar)

  union all

  select 'mart_fa_acquisition_history' as table_name,
    count(*) as violations
  from {{ ref('mart_fa_acquisition_history') }}
  where player_id is not null
    and player_id != -1
    and cast(player_key as varchar) <> cast(player_id as varchar)

  union all

  select 'mart_fantasy_actuals_weekly' as table_name,
    count(*) as violations
  from {{ ref('mart_fantasy_actuals_weekly') }}
  where player_id is not null
    and player_id != -1
    and cast(player_key as varchar) <> cast(player_id as varchar)

  union all

  select 'mart_real_world_actuals_weekly' as table_name,
    count(*) as violations
  from {{ ref('mart_real_world_actuals_weekly') }}
  where player_id is not null
    and player_id != -1
    and cast(player_key as varchar) <> cast(player_id as varchar)
)

select *
from checks
where violations > 0

