-- Ensure staged player-centric tables use canonical player_id when available

with checks as (
  -- KTC assets: players should use canonical player_id for player_key when mapped
  select 'stg_ktc_assets' as table_name,
    count(*) as violations
  from {{ ref('stg_ktc_assets') }}
  where asset_type = 'player'
    and player_id is not null
    and player_id != -1
    and cast(player_key as varchar) <> cast(player_id as varchar)

  union all

  -- Sleeper FA pool
  select 'stg_sleeper__fa_pool' as table_name,
    count(*) as violations
  from {{ ref('stg_sleeper__fa_pool') }}
  where player_id is not null
    and cast(player_key as varchar) <> cast(player_id as varchar)

  union all

  -- Commissioner contracts (active)
  select 'stg_sheets__contracts_active' as table_name,
    count(*) as violations
  from {{ ref('stg_sheets__contracts_active') }}
  where player_id is not null
    and cast(player_key as varchar) <> cast(player_id as varchar)

  union all

  -- Commissioner contracts (cut)
  select 'stg_sheets__contracts_cut' as table_name,
    count(*) as violations
  from {{ ref('stg_sheets__contracts_cut') }}
  where player_id is not null
    and cast(player_key as varchar) <> cast(player_id as varchar)

  union all

  -- Commissioner transactions
  select 'stg_sheets__transactions' as table_name,
    count(*) as violations
  from {{ ref('stg_sheets__transactions') }}
  where asset_type = 'player'
    and player_id is not null
    and cast(player_key as varchar) <> cast(player_id as varchar)
)

select *
from checks
where violations > 0

