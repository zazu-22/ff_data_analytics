{{ config(materialized='table') }}

/*
Real-world actuals mart - weekly player performance in physical stats (no fantasy scoring).

Grain: One row per player per season per week
Source: fact_player_stats (pivoted from long to wide form)

Part of 2×2 model:
- This mart: Real-world actuals (yards, TDs, receptions, etc.)
- Partner mart: mart_fantasy_actuals_weekly (applies scoring rules)

Provides denormalized player/team attributes via dimension joins for ease of querying.
*/

with fact_stats as (
  select
    player_id,
    player_key,
    season,
    week,
    season_type,
    position,
    stat_name,
    stat_value
  from {{ ref('fact_player_stats') }}
  where
    measure_domain = 'real_world'
    and stat_kind = 'actual'
    and provider = 'nflverse'
),

pivoted as (
  select
    player_id,
    player_key,
    season,
    week,
    season_type,
    -- Use arbitrary() to pick position (DuckDB-safe, one value per player per week)
    arbitrary(position) as position,

    -- Passing stats
    sum(case when stat_name = 'completions' then stat_value else 0 end) as completions,
    sum(case when stat_name = 'attempts' then stat_value else 0 end) as attempts,
    sum(case when stat_name = 'passing_yards' then stat_value else 0 end) as passing_yards,
    sum(case when stat_name = 'passing_tds' then stat_value else 0 end) as passing_tds,
    sum(case when stat_name = 'passing_interceptions' then stat_value else 0 end) as passing_interceptions,
    sum(case when stat_name = 'passing_2pt_conversions' then stat_value else 0 end) as passing_2pt_conversions,

    -- Rushing stats
    sum(case when stat_name = 'carries' then stat_value else 0 end) as carries,
    sum(case when stat_name = 'rushing_yards' then stat_value else 0 end) as rushing_yards,
    sum(case when stat_name = 'rushing_tds' then stat_value else 0 end) as rushing_tds,
    sum(case when stat_name = 'rushing_fumbles_lost' then stat_value else 0 end) as rushing_fumbles_lost,
    sum(case when stat_name = 'rushing_2pt_conversions' then stat_value else 0 end) as rushing_2pt_conversions,

    -- Receiving stats
    sum(case when stat_name = 'targets' then stat_value else 0 end) as targets,
    sum(case when stat_name = 'receptions' then stat_value else 0 end) as receptions,
    sum(case when stat_name = 'receiving_yards' then stat_value else 0 end) as receiving_yards,
    sum(case when stat_name = 'receiving_tds' then stat_value else 0 end) as receiving_tds,
    sum(case when stat_name = 'receiving_fumbles_lost' then stat_value else 0 end) as receiving_fumbles_lost,
    sum(case when stat_name = 'receiving_2pt_conversions' then stat_value else 0 end) as receiving_2pt_conversions,

    -- Defensive stats (IDP league)
    sum(case when stat_name = 'def_tackles_solo' then stat_value else 0 end) as def_tackles_solo,
    sum(case when stat_name = 'def_tackles_with_assist' then stat_value else 0 end) as def_tackles_with_assist,
    sum(case when stat_name = 'def_sacks' then stat_value else 0 end) as def_sacks,
    sum(case when stat_name = 'def_interceptions' then stat_value else 0 end) as def_interceptions,
    sum(case when stat_name = 'def_fumbles_forced' then stat_value else 0 end) as def_fumbles_forced,
    sum(case when stat_name = 'def_tds' then stat_value else 0 end) as def_tds,
    sum(case when stat_name = 'def_safeties' then stat_value else 0 end) as def_safeties,

    -- Misc stats
    sum(case when stat_name = 'sacks_suffered' then stat_value else 0 end) as sacks_suffered,
    sum(case when stat_name = 'special_teams_tds' then stat_value else 0 end) as special_teams_tds

  from fact_stats
  group by player_id, player_key, season, week, season_type
)

select
  p.*,

  -- Player attributes (from dim_player)
  d.display_name,
  d.current_team,

  -- Computed games played (always 1 for weekly grain)
  1 as games_played

from pivoted as p
left join {{ ref('dim_player') }} as d
  on p.player_id = d.player_id
