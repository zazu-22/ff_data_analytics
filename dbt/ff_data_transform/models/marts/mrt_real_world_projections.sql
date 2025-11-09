{{ config(materialized="table", unique_key=['player_id', 'season', 'week', 'horizon', 'provider']) }}

/*
Real-world projections mart - weekly/season player projections (no fantasy scoring).

Grain: One row per player per season per week per horizon per asof_date
Source: fct_player_projections (pivoted from long to wide form)

Part of 2×2 model:
- Real-world base: This mart (physical stats)
- Fantasy scoring: mrt_fantasy_projections (applies dim_scoring_rule)

Usage: Analysis of raw projections, input to variance analysis
*/
with
    projections_long as (
        select
            player_id,
            player_name,
            position,
            current_team,
            season,
            week,
            horizon,
            asof_date,
            provider,
            source_count,
            total_weight,
            stat_name,
            stat_value
        from {{ ref("fct_player_projections") }}
        where measure_domain = 'real_world' and stat_kind = 'projection' and provider = 'ffanalytics_consensus'
    ),

    -- Pivot stats to wide format
    projections_wide as (
        select
            player_id,
            player_name,
            position,
            current_team,
            season,
            week,
            horizon,
            asof_date,
            provider,
            source_count,
            total_weight,

            -- Passing stats
            sum(case when stat_name = 'completions' then stat_value else 0 end) as completions,
            sum(case when stat_name = 'attempts' then stat_value else 0 end) as attempts,
            sum(case when stat_name = 'passing_yards' then stat_value else 0 end) as passing_yards,
            sum(case when stat_name = 'passing_tds' then stat_value else 0 end) as passing_tds,
            sum(case when stat_name = 'interceptions' then stat_value else 0 end) as interceptions,

            -- Rushing stats
            sum(case when stat_name = 'rushing_attempts' then stat_value else 0 end) as rushing_attempts,
            sum(case when stat_name = 'rushing_yards' then stat_value else 0 end) as rushing_yards,
            sum(case when stat_name = 'rushing_tds' then stat_value else 0 end) as rushing_tds,

            -- Receiving stats
            sum(case when stat_name = 'targets' then stat_value else 0 end) as targets,
            sum(case when stat_name = 'receptions' then stat_value else 0 end) as receptions,
            sum(case when stat_name = 'receiving_yards' then stat_value else 0 end) as receiving_yards,
            sum(case when stat_name = 'receiving_tds' then stat_value else 0 end) as receiving_tds,

            -- Turnovers
            sum(case when stat_name = 'fumbles_lost' then stat_value else 0 end) as fumbles_lost

        from projections_long
        group by 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11
    )

select
    -- Grain columns
    player_id,
    player_name,
    position,
    current_team,
    season,
    week,
    horizon,
    asof_date,
    provider,
    source_count,
    total_weight,

    -- Passing stats
    completions,
    attempts,
    passing_yards,
    passing_tds,
    interceptions,

    -- Rushing stats
    rushing_attempts,
    rushing_yards,
    rushing_tds,

    -- Receiving stats
    targets,
    receptions,
    receiving_yards,
    receiving_tds,

    -- Turnovers
    fumbles_lost

from projections_wide
