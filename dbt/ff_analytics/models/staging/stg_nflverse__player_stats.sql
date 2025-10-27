{{ config(materialized='view') }}

/*
Stage nflverse weekly player stats with mfl_id crosswalk and long-form unpivot.

Source: data/raw/nflverse/weekly/ (load_player_stats with summary_level='week')
Output grain: one row per player per game per stat
Crosswalk: player_id (gsis_id) → mfl_id via dim_player_id_xref

ADR-009: Feeds into consolidated fact_player_stats
ADR-010: Uses mfl_id as canonical player_id
*/

with base as (
  select
    -- Raw player_id column contains gsis_id values
    w.player_id as gsis_id_raw,
    -- Generate surrogate game_id (raw data doesn't have it)
    cast(w.season as varchar) || '_'
    || cast(w.week as varchar) || '_'
    || w.team || '_'
    || w.opponent_team as game_id,
    w.season,
    w.week,
    w.season_type,
    w.team,
    w.opponent_team,
    w.position,

    -- Passing stats (11 columns)
    w.completions,
    w.attempts,
    w.passing_yards,
    w.passing_tds,
    w.passing_interceptions,
    w.passing_air_yards,
    w.passing_yards_after_catch,
    w.passing_first_downs,
    w.passing_epa,
    w.passing_2pt_conversions,
    w.passing_cpoe,

    -- Rushing stats (8 columns)
    w.carries,
    w.rushing_yards,
    w.rushing_tds,
    w.rushing_fumbles,
    w.rushing_fumbles_lost,
    w.rushing_first_downs,
    w.rushing_epa,
    w.rushing_2pt_conversions,

    -- Receiving stats (11 columns)
    w.targets,
    w.receptions,
    w.receiving_yards,
    w.receiving_tds,
    w.receiving_fumbles,
    w.receiving_fumbles_lost,
    w.receiving_air_yards,
    w.receiving_yards_after_catch,
    w.receiving_first_downs,
    w.receiving_epa,
    w.receiving_2pt_conversions,

    -- Defensive stats (15 columns)
    w.def_tackles_solo,
    w.def_tackles_with_assist,
    w.def_tackle_assists,
    w.def_tackles_for_loss,
    w.def_tackles_for_loss_yards,
    w.def_fumbles,
    w.def_fumbles_forced,
    w.def_interceptions,
    w.def_interception_yards,
    w.def_pass_defended,
    w.def_sacks,
    w.def_sack_yards,
    w.def_qb_hits,
    w.def_tds,
    w.def_safeties,

    -- Sacks suffered (QB stat)
    w.sacks_suffered,
    w.sack_yards_lost,
    w.sack_fumbles,
    w.sack_fumbles_lost,

    -- Special teams
    w.special_teams_tds,

    -- Kicking stats (21 columns)
    w.fg_att,
    w.fg_made,
    w.fg_missed,
    w.fg_made_0_19,
    w.fg_made_20_29,
    w.fg_made_30_39,
    w.fg_made_40_49,
    w.fg_made_50_59,
    w.fg_made_60_,
    w.fg_missed_0_19,
    w.fg_missed_20_29,
    w.fg_missed_30_39,
    w.fg_missed_40_49,
    w.fg_missed_50_59,
    w.fg_missed_60_,
    w.pat_att,
    w.pat_made,
    w.pat_missed,
    w.gwfg_att,
    w.gwfg_made,
    w.gwfg_missed,

    -- Fantasy points (pre-calculated, not used in fact table but useful for validation)
    w.fantasy_points,
    w.fantasy_points_ppr

  from
    read_parquet(
      '{{ var("external_root", "data/raw") }}/nflverse/weekly/dt=*/*.parquet',
      w.hive_partitioning = true
    ) w
  -- Data quality filters: Exclude records missing required identifiers
  -- player_id (gsis_id): ~0.12% of raw data has NULL (113/97,415 rows)
  --   These are unidentifiable players with no position info
  --   Cannot perform player-level analysis without player identification
  where
    w.player_id is not null
    and w.season is not null
    and w.week is not null
    -- Keep only latest snapshot (idempotent reads across multiple dt partitions)
    and {{ latest_snapshot_only(var("external_root", "data/raw") ~ "/nflverse/weekly/dt=*/*.parquet") }}
),

crosswalk as (
  -- Map raw provider IDs to canonical mfl_id via ff_playerids crosswalk
  -- Crosswalk source: nflverse ff_playerids dataset (12,133 players, 19 provider IDs)
  -- Mapping coverage: ~99.9% of identifiable weekly players map successfully
  select
    base.* exclude (position),
    -- Map gsis_id → mfl_id (canonical player_id per ADR-010)
    coalesce(xref.mfl_id, -1) as player_id,
    -- Use position from crosswalk if raw data has null
    coalesce(base.position, xref.position) as position,
    -- Composite key for grain uniqueness (uses raw ID when unmapped)
    -- Prevents duplicate grain violations when multiple unmapped players in same game
    -- Mapped players: player_key = mfl_id (as varchar)
    -- Unmapped players: player_key = gsis_id (preserves identity via raw provider ID)
    -- Unknown edge case: player_key = 'UNKNOWN_' || game_id (defensive fail-safe)
    case
      when coalesce(xref.mfl_id, -1) != -1
        then cast(xref.mfl_id as varchar)
      else coalesce(base.gsis_id_raw, 'UNKNOWN_' || base.game_id)
    end as player_key
  from base
  left join {{ ref('dim_player_id_xref') }} xref
    on base.gsis_id_raw = xref.gsis_id
),

unpivoted as (
  -- Unpivot all stats to long form
  -- Pattern: SELECT player_id, player_key, game_id, season, week, season_type, position,
  --          'stat_name' AS stat_name, stat_value,
  --          'real_world' AS measure_domain, 'actual' AS stat_kind, 'nflverse' AS provider
  --  FROM crosswalk WHERE stat_value IS NOT NULL

  -- Passing
  select
    player_id,
    player_key,
    game_id,
    season,
    week,
    season_type,
    position,
    'completions' as stat_name,
    cast(completions as double) as stat_value,
    'real_world' as measure_domain,
    'actual' as stat_kind,
    'nflverse' as provider
  from crosswalk
  where completions is not null
  union all
  select
    player_id,
    player_key,
    game_id,
    season,
    week,
    season_type,
    position,
    'attempts',
    cast(attempts as double),
    'real_world',
    'actual',
    'nflverse'
  from crosswalk
  where attempts is not null
  union all
  select
    player_id,
    player_key,
    game_id,
    season,
    week,
    season_type,
    position,
    'passing_yards',
    cast(passing_yards as double),
    'real_world',
    'actual',
    'nflverse'
  from crosswalk
  where passing_yards is not null
  union all
  select
    player_id,
    player_key,
    game_id,
    season,
    week,
    season_type,
    position,
    'passing_tds',
    cast(passing_tds as double),
    'real_world',
    'actual',
    'nflverse'
  from crosswalk
  where passing_tds is not null
  union all
  select
    player_id,
    player_key,
    game_id,
    season,
    week,
    season_type,
    position,
    'passing_interceptions',
    cast(passing_interceptions as double),
    'real_world',
    'actual',
    'nflverse'
  from crosswalk
  where passing_interceptions is not null
  union all
  select
    player_id,
    player_key,
    game_id,
    season,
    week,
    season_type,
    position,
    'passing_air_yards',
    cast(passing_air_yards as double),
    'real_world',
    'actual',
    'nflverse'
  from crosswalk
  where passing_air_yards is not null
  union all
  select
    player_id,
    player_key,
    game_id,
    season,
    week,
    season_type,
    position,
    'passing_yards_after_catch',
    cast(passing_yards_after_catch as double),
    'real_world',
    'actual',
    'nflverse'
  from crosswalk
  where passing_yards_after_catch is not null
  union all
  select
    player_id,
    player_key,
    game_id,
    season,
    week,
    season_type,
    position,
    'passing_first_downs',
    cast(passing_first_downs as double),
    'real_world',
    'actual',
    'nflverse'
  from crosswalk
  where passing_first_downs is not null
  union all
  select
    player_id,
    player_key,
    game_id,
    season,
    week,
    season_type,
    position,
    'passing_epa',
    cast(passing_epa as double),
    'real_world',
    'actual',
    'nflverse'
  from crosswalk
  where passing_epa is not null
  union all
  select
    player_id,
    player_key,
    game_id,
    season,
    week,
    season_type,
    position,
    'passing_2pt_conversions',
    cast(passing_2pt_conversions as double),
    'real_world',
    'actual',
    'nflverse'
  from crosswalk
  where passing_2pt_conversions is not null
  union all
  select
    player_id,
    player_key,
    game_id,
    season,
    week,
    season_type,
    position,
    'passing_cpoe',
    cast(passing_cpoe as double),
    'real_world',
    'actual',
    'nflverse'
  from crosswalk
  where passing_cpoe is not null

  -- Rushing
  union all
  select
    player_id,
    player_key,
    game_id,
    season,
    week,
    season_type,
    position,
    'carries',
    cast(carries as double),
    'real_world',
    'actual',
    'nflverse'
  from crosswalk
  where carries is not null
  union all
  select
    player_id,
    player_key,
    game_id,
    season,
    week,
    season_type,
    position,
    'rushing_yards',
    cast(rushing_yards as double),
    'real_world',
    'actual',
    'nflverse'
  from crosswalk
  where rushing_yards is not null
  union all
  select
    player_id,
    player_key,
    game_id,
    season,
    week,
    season_type,
    position,
    'rushing_tds',
    cast(rushing_tds as double),
    'real_world',
    'actual',
    'nflverse'
  from crosswalk
  where rushing_tds is not null
  union all
  select
    player_id,
    player_key,
    game_id,
    season,
    week,
    season_type,
    position,
    'rushing_fumbles',
    cast(rushing_fumbles as double),
    'real_world',
    'actual',
    'nflverse'
  from crosswalk
  where rushing_fumbles is not null
  union all
  select
    player_id,
    player_key,
    game_id,
    season,
    week,
    season_type,
    position,
    'rushing_fumbles_lost',
    cast(rushing_fumbles_lost as double),
    'real_world',
    'actual',
    'nflverse'
  from crosswalk
  where rushing_fumbles_lost is not null
  union all
  select
    player_id,
    player_key,
    game_id,
    season,
    week,
    season_type,
    position,
    'rushing_first_downs',
    cast(rushing_first_downs as double),
    'real_world',
    'actual',
    'nflverse'
  from crosswalk
  where rushing_first_downs is not null
  union all
  select
    player_id,
    player_key,
    game_id,
    season,
    week,
    season_type,
    position,
    'rushing_epa',
    cast(rushing_epa as double),
    'real_world',
    'actual',
    'nflverse'
  from crosswalk
  where rushing_epa is not null
  union all
  select
    player_id,
    player_key,
    game_id,
    season,
    week,
    season_type,
    position,
    'rushing_2pt_conversions',
    cast(rushing_2pt_conversions as double),
    'real_world',
    'actual',
    'nflverse'
  from crosswalk
  where rushing_2pt_conversions is not null

  -- Receiving
  union all
  select
    player_id,
    player_key,
    game_id,
    season,
    week,
    season_type,
    position,
    'targets',
    cast(targets as double),
    'real_world',
    'actual',
    'nflverse'
  from crosswalk
  where targets is not null
  union all
  select
    player_id,
    player_key,
    game_id,
    season,
    week,
    season_type,
    position,
    'receptions',
    cast(receptions as double),
    'real_world',
    'actual',
    'nflverse'
  from crosswalk
  where receptions is not null
  union all
  select
    player_id,
    player_key,
    game_id,
    season,
    week,
    season_type,
    position,
    'receiving_yards',
    cast(receiving_yards as double),
    'real_world',
    'actual',
    'nflverse'
  from crosswalk
  where receiving_yards is not null
  union all
  select
    player_id,
    player_key,
    game_id,
    season,
    week,
    season_type,
    position,
    'receiving_tds',
    cast(receiving_tds as double),
    'real_world',
    'actual',
    'nflverse'
  from crosswalk
  where receiving_tds is not null
  union all
  select
    player_id,
    player_key,
    game_id,
    season,
    week,
    season_type,
    position,
    'receiving_fumbles',
    cast(receiving_fumbles as double),
    'real_world',
    'actual',
    'nflverse'
  from crosswalk
  where receiving_fumbles is not null
  union all
  select
    player_id,
    player_key,
    game_id,
    season,
    week,
    season_type,
    position,
    'receiving_fumbles_lost',
    cast(receiving_fumbles_lost as double),
    'real_world',
    'actual',
    'nflverse'
  from crosswalk
  where receiving_fumbles_lost is not null
  union all
  select
    player_id,
    player_key,
    game_id,
    season,
    week,
    season_type,
    position,
    'receiving_air_yards',
    cast(receiving_air_yards as double),
    'real_world',
    'actual',
    'nflverse'
  from crosswalk
  where receiving_air_yards is not null
  union all
  select
    player_id,
    player_key,
    game_id,
    season,
    week,
    season_type,
    position,
    'receiving_yards_after_catch',
    cast(receiving_yards_after_catch as double),
    'real_world',
    'actual',
    'nflverse'
  from crosswalk
  where receiving_yards_after_catch is not null
  union all
  select
    player_id,
    player_key,
    game_id,
    season,
    week,
    season_type,
    position,
    'receiving_first_downs',
    cast(receiving_first_downs as double),
    'real_world',
    'actual',
    'nflverse'
  from crosswalk
  where receiving_first_downs is not null
  union all
  select
    player_id,
    player_key,
    game_id,
    season,
    week,
    season_type,
    position,
    'receiving_epa',
    cast(receiving_epa as double),
    'real_world',
    'actual',
    'nflverse'
  from crosswalk
  where receiving_epa is not null
  union all
  select
    player_id,
    player_key,
    game_id,
    season,
    week,
    season_type,
    position,
    'receiving_2pt_conversions',
    cast(receiving_2pt_conversions as double),
    'real_world',
    'actual',
    'nflverse'
  from crosswalk
  where receiving_2pt_conversions is not null

  -- Defensive
  union all
  select
    player_id,
    player_key,
    game_id,
    season,
    week,
    season_type,
    position,
    'def_tackles_solo',
    cast(def_tackles_solo as double),
    'real_world',
    'actual',
    'nflverse'
  from crosswalk
  where def_tackles_solo is not null
  union all
  select
    player_id,
    player_key,
    game_id,
    season,
    week,
    season_type,
    position,
    'def_tackles_with_assist',
    cast(def_tackles_with_assist as double),
    'real_world',
    'actual',
    'nflverse'
  from crosswalk
  where def_tackles_with_assist is not null
  union all
  select
    player_id,
    player_key,
    game_id,
    season,
    week,
    season_type,
    position,
    'def_tackle_assists',
    cast(def_tackle_assists as double),
    'real_world',
    'actual',
    'nflverse'
  from crosswalk
  where def_tackle_assists is not null
  union all
  select
    player_id,
    player_key,
    game_id,
    season,
    week,
    season_type,
    position,
    'def_tackles_for_loss',
    cast(def_tackles_for_loss as double),
    'real_world',
    'actual',
    'nflverse'
  from crosswalk
  where def_tackles_for_loss is not null
  union all
  select
    player_id,
    player_key,
    game_id,
    season,
    week,
    season_type,
    position,
    'def_tackles_for_loss_yards',
    cast(def_tackles_for_loss_yards as double),
    'real_world',
    'actual',
    'nflverse'
  from crosswalk
  where def_tackles_for_loss_yards is not null
  union all
  select
    player_id,
    player_key,
    game_id,
    season,
    week,
    season_type,
    position,
    'def_fumbles',
    cast(def_fumbles as double),
    'real_world',
    'actual',
    'nflverse'
  from crosswalk
  where def_fumbles is not null
  union all
  select
    player_id,
    player_key,
    game_id,
    season,
    week,
    season_type,
    position,
    'def_fumbles_forced',
    cast(def_fumbles_forced as double),
    'real_world',
    'actual',
    'nflverse'
  from crosswalk
  where def_fumbles_forced is not null
  union all
  select
    player_id,
    player_key,
    game_id,
    season,
    week,
    season_type,
    position,
    'def_interceptions',
    cast(def_interceptions as double),
    'real_world',
    'actual',
    'nflverse'
  from crosswalk
  where def_interceptions is not null
  union all
  select
    player_id,
    player_key,
    game_id,
    season,
    week,
    season_type,
    position,
    'def_interception_yards',
    cast(def_interception_yards as double),
    'real_world',
    'actual',
    'nflverse'
  from crosswalk
  where def_interception_yards is not null
  union all
  select
    player_id,
    player_key,
    game_id,
    season,
    week,
    season_type,
    position,
    'def_pass_defended',
    cast(def_pass_defended as double),
    'real_world',
    'actual',
    'nflverse'
  from crosswalk
  where def_pass_defended is not null
  union all
  select
    player_id,
    player_key,
    game_id,
    season,
    week,
    season_type,
    position,
    'def_sacks',
    cast(def_sacks as double),
    'real_world',
    'actual',
    'nflverse'
  from crosswalk
  where def_sacks is not null
  union all
  select
    player_id,
    player_key,
    game_id,
    season,
    week,
    season_type,
    position,
    'def_sack_yards',
    cast(def_sack_yards as double),
    'real_world',
    'actual',
    'nflverse'
  from crosswalk
  where def_sack_yards is not null
  union all
  select
    player_id,
    player_key,
    game_id,
    season,
    week,
    season_type,
    position,
    'def_qb_hits',
    cast(def_qb_hits as double),
    'real_world',
    'actual',
    'nflverse'
  from crosswalk
  where def_qb_hits is not null
  union all
  select
    player_id,
    player_key,
    game_id,
    season,
    week,
    season_type,
    position,
    'def_tds',
    cast(def_tds as double),
    'real_world',
    'actual',
    'nflverse'
  from crosswalk
  where def_tds is not null
  union all
  select
    player_id,
    player_key,
    game_id,
    season,
    week,
    season_type,
    position,
    'def_safeties',
    cast(def_safeties as double),
    'real_world',
    'actual',
    'nflverse'
  from crosswalk
  where def_safeties is not null

  -- Sacks suffered
  union all
  select
    player_id,
    player_key,
    game_id,
    season,
    week,
    season_type,
    position,
    'sacks_suffered',
    cast(sacks_suffered as double),
    'real_world',
    'actual',
    'nflverse'
  from crosswalk
  where sacks_suffered is not null
  union all
  select
    player_id,
    player_key,
    game_id,
    season,
    week,
    season_type,
    position,
    'sack_yards_lost',
    cast(sack_yards_lost as double),
    'real_world',
    'actual',
    'nflverse'
  from crosswalk
  where sack_yards_lost is not null
  union all
  select
    player_id,
    player_key,
    game_id,
    season,
    week,
    season_type,
    position,
    'sack_fumbles',
    cast(sack_fumbles as double),
    'real_world',
    'actual',
    'nflverse'
  from crosswalk
  where sack_fumbles is not null
  union all
  select
    player_id,
    player_key,
    game_id,
    season,
    week,
    season_type,
    position,
    'sack_fumbles_lost',
    cast(sack_fumbles_lost as double),
    'real_world',
    'actual',
    'nflverse'
  from crosswalk
  where sack_fumbles_lost is not null

  -- Special teams
  union all
  select
    player_id,
    player_key,
    game_id,
    season,
    week,
    season_type,
    position,
    'special_teams_tds',
    cast(special_teams_tds as double),
    'real_world',
    'actual',
    'nflverse'
  from crosswalk
  where special_teams_tds is not null

  -- Kicking
  union all
  select
    player_id,
    player_key,
    game_id,
    season,
    week,
    season_type,
    position,
    'fg_att',
    cast(fg_att as double),
    'real_world',
    'actual',
    'nflverse'
  from crosswalk
  where fg_att is not null
  union all
  select
    player_id,
    player_key,
    game_id,
    season,
    week,
    season_type,
    position,
    'fg_made',
    cast(fg_made as double),
    'real_world',
    'actual',
    'nflverse'
  from crosswalk
  where fg_made is not null
  union all
  select
    player_id,
    player_key,
    game_id,
    season,
    week,
    season_type,
    position,
    'fg_missed',
    cast(fg_missed as double),
    'real_world',
    'actual',
    'nflverse'
  from crosswalk
  where fg_missed is not null
  union all
  select
    player_id,
    player_key,
    game_id,
    season,
    week,
    season_type,
    position,
    'fg_made_0_19',
    cast(fg_made_0_19 as double),
    'real_world',
    'actual',
    'nflverse'
  from crosswalk
  where fg_made_0_19 is not null
  union all
  select
    player_id,
    player_key,
    game_id,
    season,
    week,
    season_type,
    position,
    'fg_made_20_29',
    cast(fg_made_20_29 as double),
    'real_world',
    'actual',
    'nflverse'
  from crosswalk
  where fg_made_20_29 is not null
  union all
  select
    player_id,
    player_key,
    game_id,
    season,
    week,
    season_type,
    position,
    'fg_made_30_39',
    cast(fg_made_30_39 as double),
    'real_world',
    'actual',
    'nflverse'
  from crosswalk
  where fg_made_30_39 is not null
  union all
  select
    player_id,
    player_key,
    game_id,
    season,
    week,
    season_type,
    position,
    'fg_made_40_49',
    cast(fg_made_40_49 as double),
    'real_world',
    'actual',
    'nflverse'
  from crosswalk
  where fg_made_40_49 is not null
  union all
  select
    player_id,
    player_key,
    game_id,
    season,
    week,
    season_type,
    position,
    'fg_made_50_59',
    cast(fg_made_50_59 as double),
    'real_world',
    'actual',
    'nflverse'
  from crosswalk
  where fg_made_50_59 is not null
  union all
  select
    player_id,
    player_key,
    game_id,
    season,
    week,
    season_type,
    position,
    'fg_made_60_',
    cast(fg_made_60_ as double),
    'real_world',
    'actual',
    'nflverse'
  from crosswalk
  where fg_made_60_ is not null
  union all
  select
    player_id,
    player_key,
    game_id,
    season,
    week,
    season_type,
    position,
    'fg_missed_0_19',
    cast(fg_missed_0_19 as double),
    'real_world',
    'actual',
    'nflverse'
  from crosswalk
  where fg_missed_0_19 is not null
  union all
  select
    player_id,
    player_key,
    game_id,
    season,
    week,
    season_type,
    position,
    'fg_missed_20_29',
    cast(fg_missed_20_29 as double),
    'real_world',
    'actual',
    'nflverse'
  from crosswalk
  where fg_missed_20_29 is not null
  union all
  select
    player_id,
    player_key,
    game_id,
    season,
    week,
    season_type,
    position,
    'fg_missed_30_39',
    cast(fg_missed_30_39 as double),
    'real_world',
    'actual',
    'nflverse'
  from crosswalk
  where fg_missed_30_39 is not null
  union all
  select
    player_id,
    player_key,
    game_id,
    season,
    week,
    season_type,
    position,
    'fg_missed_40_49',
    cast(fg_missed_40_49 as double),
    'real_world',
    'actual',
    'nflverse'
  from crosswalk
  where fg_missed_40_49 is not null
  union all
  select
    player_id,
    player_key,
    game_id,
    season,
    week,
    season_type,
    position,
    'fg_missed_50_59',
    cast(fg_missed_50_59 as double),
    'real_world',
    'actual',
    'nflverse'
  from crosswalk
  where fg_missed_50_59 is not null
  union all
  select
    player_id,
    player_key,
    game_id,
    season,
    week,
    season_type,
    position,
    'fg_missed_60_',
    cast(fg_missed_60_ as double),
    'real_world',
    'actual',
    'nflverse'
  from crosswalk
  where fg_missed_60_ is not null
  union all
  select
    player_id,
    player_key,
    game_id,
    season,
    week,
    season_type,
    position,
    'pat_att',
    cast(pat_att as double),
    'real_world',
    'actual',
    'nflverse'
  from crosswalk
  where pat_att is not null
  union all
  select
    player_id,
    player_key,
    game_id,
    season,
    week,
    season_type,
    position,
    'pat_made',
    cast(pat_made as double),
    'real_world',
    'actual',
    'nflverse'
  from crosswalk
  where pat_made is not null
  union all
  select
    player_id,
    player_key,
    game_id,
    season,
    week,
    season_type,
    position,
    'pat_missed',
    cast(pat_missed as double),
    'real_world',
    'actual',
    'nflverse'
  from crosswalk
  where pat_missed is not null
  union all
  select
    player_id,
    player_key,
    game_id,
    season,
    week,
    season_type,
    position,
    'gwfg_att',
    cast(gwfg_att as double),
    'real_world',
    'actual',
    'nflverse'
  from crosswalk
  where gwfg_att is not null
  union all
  select
    player_id,
    player_key,
    game_id,
    season,
    week,
    season_type,
    position,
    'gwfg_made',
    cast(gwfg_made as double),
    'real_world',
    'actual',
    'nflverse'
  from crosswalk
  where gwfg_made is not null
  union all
  select
    player_id,
    player_key,
    game_id,
    season,
    week,
    season_type,
    position,
    'gwfg_missed',
    cast(gwfg_missed as double),
    'real_world',
    'actual',
    'nflverse'
  from crosswalk
  where gwfg_missed is not null
)

select * from unpivoted
