{{ config(materialized='view') }}

/*
Stage nflverse ff_opportunity metrics with mfl_id crosswalk and long-form unpivot.

Source: data/raw/nflverse/ff_opportunity/ (load_ff_opportunity)
Output grain: one row per player per game per stat (~40 selected stats)
Crosswalk: player_id (gsis_id) → mfl_id via dim_player_id_xref

Includes:
- Expected stats (*_exp): Predicted values based on opportunity
- Variance stats (*_diff): Actual minus expected (measures over/under-performance)
- Team shares (*_share, *_attempt): Player's proportion of team opportunity

ADR-009: Feeds into consolidated fact_player_stats
ADR-010: Uses mfl_id as canonical player_id
*/

with base as (
  select
    -- Raw player_id column contains gsis_id values
    o.player_id as gsis_id_raw,
    o.game_id,
    cast(o.season as int) as season,
    cast(o.week as int) as week,
    'REG' as season_type,  -- ff_opportunity doesn't have season_type column
    o.position,

    -- Expected stats (12 key columns)
    o.pass_completions_exp,
    o.receptions_exp,
    o.pass_yards_gained_exp,
    o.rec_yards_gained_exp,
    o.rush_yards_gained_exp,
    o.pass_touchdown_exp,
    o.rec_touchdown_exp,
    o.rush_touchdown_exp,
    o.pass_interception_exp,
    o.pass_first_down_exp,
    o.rec_first_down_exp,
    o.rush_first_down_exp,

    -- Variance stats (12 key columns - actual minus expected)
    o.pass_completions_diff,
    o.receptions_diff,
    o.pass_yards_gained_diff,
    o.rec_yards_gained_diff,
    o.rush_yards_gained_diff,
    o.pass_touchdown_diff,
    o.rec_touchdown_diff,
    o.rush_touchdown_diff,
    o.pass_interception_diff,
    o.pass_first_down_diff,
    o.rec_first_down_diff,
    o.rush_first_down_diff,

    -- Air yards metrics (2 columns - other advanced metrics not in sample dataset)
    o.pass_air_yards,
    o.rec_air_yards,

    -- Team shares and attempts (6 columns)
    o.pass_attempt,
    o.rec_attempt,
    o.rush_attempt,
    o.pass_attempt_team,
    o.rec_attempt_team,
    o.rush_attempt_team

  from read_parquet(
    '{{ env_var("RAW_NFLVERSE_FF_OPPORTUNITY_GLOB", "data/raw/nflverse/ff_opportunity/dt=*/*.parquet") }}'
  ) o
  -- Data quality filters: Exclude records missing required identifiers
  -- player_id (gsis_id): ~6.75% of raw data has NULL (2,115/31,339 rows)
  --   These are unidentifiable players with NULL position and small opportunity counts (1-4 targets)
  --   Consistent across all seasons (~350-440 per year)
  --   Cannot perform player-level analysis without player identification
  -- Of identifiable players (93.25%): 99.86% map to crosswalk, 0.14% unmapped
  where o.player_id is not null
    and o.season is not null
    and o.week is not null
    and o.game_id is not null
),

crosswalk as (
  -- Map raw provider IDs to canonical mfl_id via ff_playerids crosswalk
  -- Crosswalk source: nflverse ff_playerids dataset (12,133 players, 19 provider IDs)
  -- Mapping coverage: 99.86% of identifiable ff_opportunity players map successfully
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
  -- Unpivot opportunity metrics to long form (~38 stat types)

  -- Expected stats
  select player_id, player_key, game_id, season, week, season_type, position, 'pass_completions_exp' as stat_name, cast(pass_completions_exp as double) as stat_value, 'real_world' as measure_domain, 'actual' as stat_kind, 'nflverse' as provider from crosswalk where pass_completions_exp is not null
  union all select player_id, player_key, game_id, season, week, season_type, position, 'receptions_exp', cast(receptions_exp as double), 'real_world', 'actual', 'nflverse' from crosswalk where receptions_exp is not null
  union all select player_id, player_key, game_id, season, week, season_type, position, 'pass_yards_gained_exp', cast(pass_yards_gained_exp as double), 'real_world', 'actual', 'nflverse' from crosswalk where pass_yards_gained_exp is not null
  union all select player_id, player_key, game_id, season, week, season_type, position, 'rec_yards_gained_exp', cast(rec_yards_gained_exp as double), 'real_world', 'actual', 'nflverse' from crosswalk where rec_yards_gained_exp is not null
  union all select player_id, player_key, game_id, season, week, season_type, position, 'rush_yards_gained_exp', cast(rush_yards_gained_exp as double), 'real_world', 'actual', 'nflverse' from crosswalk where rush_yards_gained_exp is not null
  union all select player_id, player_key, game_id, season, week, season_type, position, 'pass_touchdown_exp', cast(pass_touchdown_exp as double), 'real_world', 'actual', 'nflverse' from crosswalk where pass_touchdown_exp is not null
  union all select player_id, player_key, game_id, season, week, season_type, position, 'rec_touchdown_exp', cast(rec_touchdown_exp as double), 'real_world', 'actual', 'nflverse' from crosswalk where rec_touchdown_exp is not null
  union all select player_id, player_key, game_id, season, week, season_type, position, 'rush_touchdown_exp', cast(rush_touchdown_exp as double), 'real_world', 'actual', 'nflverse' from crosswalk where rush_touchdown_exp is not null
  union all select player_id, player_key, game_id, season, week, season_type, position, 'pass_interception_exp', cast(pass_interception_exp as double), 'real_world', 'actual', 'nflverse' from crosswalk where pass_interception_exp is not null
  union all select player_id, player_key, game_id, season, week, season_type, position, 'pass_first_down_exp', cast(pass_first_down_exp as double), 'real_world', 'actual', 'nflverse' from crosswalk where pass_first_down_exp is not null
  union all select player_id, player_key, game_id, season, week, season_type, position, 'rec_first_down_exp', cast(rec_first_down_exp as double), 'real_world', 'actual', 'nflverse' from crosswalk where rec_first_down_exp is not null
  union all select player_id, player_key, game_id, season, week, season_type, position, 'rush_first_down_exp', cast(rush_first_down_exp as double), 'real_world', 'actual', 'nflverse' from crosswalk where rush_first_down_exp is not null

  -- Variance stats
  union all select player_id, player_key, game_id, season, week, season_type, position, 'pass_completions_diff', cast(pass_completions_diff as double), 'real_world', 'actual', 'nflverse' from crosswalk where pass_completions_diff is not null
  union all select player_id, player_key, game_id, season, week, season_type, position, 'receptions_diff', cast(receptions_diff as double), 'real_world', 'actual', 'nflverse' from crosswalk where receptions_diff is not null
  union all select player_id, player_key, game_id, season, week, season_type, position, 'pass_yards_gained_diff', cast(pass_yards_gained_diff as double), 'real_world', 'actual', 'nflverse' from crosswalk where pass_yards_gained_diff is not null
  union all select player_id, player_key, game_id, season, week, season_type, position, 'rec_yards_gained_diff', cast(rec_yards_gained_diff as double), 'real_world', 'actual', 'nflverse' from crosswalk where rec_yards_gained_diff is not null
  union all select player_id, player_key, game_id, season, week, season_type, position, 'rush_yards_gained_diff', cast(rush_yards_gained_diff as double), 'real_world', 'actual', 'nflverse' from crosswalk where rush_yards_gained_diff is not null
  union all select player_id, player_key, game_id, season, week, season_type, position, 'pass_touchdown_diff', cast(pass_touchdown_diff as double), 'real_world', 'actual', 'nflverse' from crosswalk where pass_touchdown_diff is not null
  union all select player_id, player_key, game_id, season, week, season_type, position, 'rec_touchdown_diff', cast(rec_touchdown_diff as double), 'real_world', 'actual', 'nflverse' from crosswalk where rec_touchdown_diff is not null
  union all select player_id, player_key, game_id, season, week, season_type, position, 'rush_touchdown_diff', cast(rush_touchdown_diff as double), 'real_world', 'actual', 'nflverse' from crosswalk where rush_touchdown_diff is not null
  union all select player_id, player_key, game_id, season, week, season_type, position, 'pass_interception_diff', cast(pass_interception_diff as double), 'real_world', 'actual', 'nflverse' from crosswalk where pass_interception_diff is not null
  union all select player_id, player_key, game_id, season, week, season_type, position, 'pass_first_down_diff', cast(pass_first_down_diff as double), 'real_world', 'actual', 'nflverse' from crosswalk where pass_first_down_diff is not null
  union all select player_id, player_key, game_id, season, week, season_type, position, 'rec_first_down_diff', cast(rec_first_down_diff as double), 'real_world', 'actual', 'nflverse' from crosswalk where rec_first_down_diff is not null
  union all select player_id, player_key, game_id, season, week, season_type, position, 'rush_first_down_diff', cast(rush_first_down_diff as double), 'real_world', 'actual', 'nflverse' from crosswalk where rush_first_down_diff is not null

  -- Air yards metrics
  union all select player_id, player_key, game_id, season, week, season_type, position, 'pass_air_yards', cast(pass_air_yards as double), 'real_world', 'actual', 'nflverse' from crosswalk where pass_air_yards is not null
  union all select player_id, player_key, game_id, season, week, season_type, position, 'rec_air_yards', cast(rec_air_yards as double), 'real_world', 'actual', 'nflverse' from crosswalk where rec_air_yards is not null

  -- Team shares and attempts
  union all select player_id, player_key, game_id, season, week, season_type, position, 'pass_attempt', cast(pass_attempt as double), 'real_world', 'actual', 'nflverse' from crosswalk where pass_attempt is not null
  union all select player_id, player_key, game_id, season, week, season_type, position, 'rec_attempt', cast(rec_attempt as double), 'real_world', 'actual', 'nflverse' from crosswalk where rec_attempt is not null
  union all select player_id, player_key, game_id, season, week, season_type, position, 'rush_attempt', cast(rush_attempt as double), 'real_world', 'actual', 'nflverse' from crosswalk where rush_attempt is not null
  union all select player_id, player_key, game_id, season, week, season_type, position, 'pass_attempt_team', cast(pass_attempt_team as double), 'real_world', 'actual', 'nflverse' from crosswalk where pass_attempt_team is not null
  union all select player_id, player_key, game_id, season, week, season_type, position, 'rec_attempt_team', cast(rec_attempt_team as double), 'real_world', 'actual', 'nflverse' from crosswalk where rec_attempt_team is not null
  union all select player_id, player_key, game_id, season, week, season_type, position, 'rush_attempt_team', cast(rush_attempt_team as double), 'real_world', 'actual', 'nflverse' from crosswalk where rush_attempt_team is not null
)

select * from unpivoted
