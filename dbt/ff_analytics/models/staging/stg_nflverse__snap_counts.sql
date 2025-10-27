{{ config(materialized='view') }}

/*
Stage nflverse snap counts with mfl_id crosswalk and long-form unpivot.

Source: data/raw/nflverse/snap_counts/ (load_snap_counts)
Output grain: one row per player per game per snap stat (6 stats)
Crosswalk: pfr_player_id → mfl_id via dim_player_id_xref

ADR-009: Feeds into consolidated fact_player_stats
ADR-010: Uses mfl_id as canonical player_id
*/

with base as (
  select
    s.pfr_player_id,
    s.game_id,
    s.season,
    s.week,
    s.game_type as season_type,
    s.team,
    s.opponent,
    s.position,

    -- Snap stats (6 columns)
    s.offense_snaps,
    s.offense_pct,
    s.defense_snaps,
    s.defense_pct,
    s.st_snaps,
    s.st_pct

  from
    read_parquet(
      '{{ env_var("RAW_NFLVERSE_SNAP_COUNTS_GLOB", "data/raw/nflverse/snap_counts/dt=*/*.parquet") }}',
      s.hive_partitioning = true
    ) s
  -- Data quality filters: Exclude records missing required identifiers
  -- pfr_player_id: 0.00% of raw data has NULL (0/136,974 rows)
  --   No data loss from NULL filtering in this dataset
  where
    s.pfr_player_id is not null
    and s.season is not null
    and s.week is not null
    -- Keep only latest snapshot (idempotent reads across multiple dt partitions)
    and     {{ latest_snapshot_only(env_var("RAW_NFLVERSE_SNAP_COUNTS_GLOB", "data/raw/nflverse/snap_counts/dt=*/*.parquet")) }}
{{ latest_snapshot_only(env_var("RAW_NFLVERSE_SNAP_COUNTS_GLOB", "data/raw/nflverse/snap_counts/dt=*/*.parquet")) }}
),

crosswalk as (
  -- Map raw provider IDs to canonical mfl_id via ff_playerids crosswalk
  -- Crosswalk source: nflverse ff_playerids dataset (12,133 players, 19 provider IDs)
  -- Mapping coverage: ~81.8% of snap_counts players map (18.2% unmapped, mostly linemen)
  select
    base.* exclude (position),
    -- Map pfr_player_id → mfl_id (canonical player_id per ADR-010)
    coalesce(xref.mfl_id, -1) as player_id,
    -- Use position from crosswalk if raw data has null
    coalesce(base.position, xref.position) as position,
    -- Composite key for grain uniqueness (uses raw ID when unmapped)
    -- Prevents duplicate grain violations when multiple unmapped players in same game
    -- Mapped players: player_key = mfl_id (as varchar)
    -- Unmapped players: player_key = pfr_id (preserves identity via raw provider ID)
    -- Unknown edge case: player_key = 'UNKNOWN_' || game_id (defensive fail-safe)
    case
      when coalesce(xref.mfl_id, -1) != -1
        then cast(xref.mfl_id as varchar)
      else coalesce(base.pfr_player_id, 'UNKNOWN_' || base.game_id)
    end as player_key
  from base
  left join {{ ref('dim_player_id_xref') }} xref
    on base.pfr_player_id = xref.pfr_id
),

unpivoted as (
  -- Unpivot snap stats to long form (6 stat types)
  select
    player_id,
    player_key,
    game_id,
    season,
    week,
    season_type,
    position,
    'offense_snaps' as stat_name,
    cast(offense_snaps as double) as stat_value,
    'real_world' as measure_domain,
    'actual' as stat_kind,
    'nflverse' as provider
  from crosswalk
  where offense_snaps is not null
  union all
  select
    player_id,
    player_key,
    game_id,
    season,
    week,
    season_type,
    position,
    'offense_pct',
    cast(offense_pct as double),
    'real_world',
    'actual',
    'nflverse'
  from crosswalk
  where offense_pct is not null
  union all
  select
    player_id,
    player_key,
    game_id,
    season,
    week,
    season_type,
    position,
    'defense_snaps',
    cast(defense_snaps as double),
    'real_world',
    'actual',
    'nflverse'
  from crosswalk
  where defense_snaps is not null
  union all
  select
    player_id,
    player_key,
    game_id,
    season,
    week,
    season_type,
    position,
    'defense_pct',
    cast(defense_pct as double),
    'real_world',
    'actual',
    'nflverse'
  from crosswalk
  where defense_pct is not null
  union all
  select
    player_id,
    player_key,
    game_id,
    season,
    week,
    season_type,
    position,
    'st_snaps',
    cast(st_snaps as double),
    'real_world',
    'actual',
    'nflverse'
  from crosswalk
  where st_snaps is not null
  union all
  select
    player_id,
    player_key,
    game_id,
    season,
    week,
    season_type,
    position,
    'st_pct',
    cast(st_pct as double),
    'real_world',
    'actual',
    'nflverse'
  from crosswalk
  where st_pct is not null
)

select * from unpivoted
