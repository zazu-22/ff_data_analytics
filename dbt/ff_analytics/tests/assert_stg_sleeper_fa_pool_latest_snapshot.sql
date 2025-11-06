-- Ensure Sleeper FA staging only contains players from the latest raw snapshot

with raw_latest as (
  select distinct sleeper_player_id
  from read_parquet(
    '{{ var("external_root") }}/sleeper/fa_pool/dt=*/fa_pool_*.parquet',
    hive_partitioning = true
  )
  where dt = (
    select max(dt)
    from read_parquet(
      '{{ var("external_root") }}/sleeper/fa_pool/dt=*/fa_pool_*.parquet',
      hive_partitioning = true
    )
  )
    and position in ('QB', 'RB', 'WR', 'TE', 'K', 'PK', 'DL', 'LB', 'DB', 'DEF', 'S', 'CB', 'DE', 'DT')
),

staging as (
  select distinct sleeper_player_id
  from {{ ref('stg_sleeper__fa_pool') }}
),

stale_players as (
  select sleeper_player_id
  from staging
  except
  select sleeper_player_id from raw_latest
)

select * from stale_players
