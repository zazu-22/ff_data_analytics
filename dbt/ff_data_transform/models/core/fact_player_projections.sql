{{
    config(
        materialized="table",
        indexes=[
            {"columns": ["player_id"]},
            {"columns": ["season", "week"]},
            {"columns": ["stat_name"]},
            {"columns": ["asof_date"]},
        ],
    )
}}

/*
Fact table for fantasy football projections (real-world stats only).

Grain: One row per player per stat per horizon per as-of date
Sources: stg_ffanalytics__projections (weighted consensus)

Part of 2×2 model:
- Real-world projections: This fact (measure_domain='real_world')
- Fantasy projections: mart_fantasy_projections (applies dim_scoring_rule)

Key differences from fact_player_stats:
- No game_id (projections are weekly/season-long, not per-game)
- Includes horizon column ('weekly', 'full_season', 'rest_of_season')
- Includes asof_date (when projection was made)
- Week can be NULL for full_season projections

ADR-007: Separate fact table from actuals to avoid nullable game_id in primary key
*/
with
    base as (
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

            -- Stats
            completions,
            attempts,
            passing_yards,
            passing_tds,
            interceptions,
            rushing_attempts,
            rushing_yards,
            rushing_tds,
            targets,
            receptions,
            receiving_yards,
            receiving_tds,
            fumbles_lost,

            -- IDP stats
            idp_solo_tackles,
            idp_assisted_tackles,
            idp_sacks,
            idp_passes_defended,
            idp_interceptions,
            idp_fumbles_forced,
            idp_fumbles_recovered,
            idp_touchdowns

        from {{ ref("stg_ffanalytics__projections") }}
    ),

    -- Unpivot to long form (one row per stat)
    unpivoted as (
        -- Passing stats
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
            'completions' as stat_name,
            completions as stat_value,
            'real_world' as measure_domain,
            'projection' as stat_kind
        from base
        where completions is not null

        union all

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
            'attempts' as stat_name,
            attempts as stat_value,
            'real_world' as measure_domain,
            'projection' as stat_kind
        from base
        where attempts is not null

        union all

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
            'passing_yards' as stat_name,
            passing_yards as stat_value,
            'real_world' as measure_domain,
            'projection' as stat_kind
        from base
        where passing_yards is not null

        union all

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
            'passing_tds' as stat_name,
            passing_tds as stat_value,
            'real_world' as measure_domain,
            'projection' as stat_kind
        from base
        where passing_tds is not null

        union all

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
            'interceptions' as stat_name,
            interceptions as stat_value,
            'real_world' as measure_domain,
            'projection' as stat_kind
        from base
        where interceptions is not null

        -- Rushing stats
        union all

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
            'rushing_attempts' as stat_name,
            rushing_attempts as stat_value,
            'real_world' as measure_domain,
            'projection' as stat_kind
        from base
        where rushing_attempts is not null

        union all

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
            'rushing_yards' as stat_name,
            rushing_yards as stat_value,
            'real_world' as measure_domain,
            'projection' as stat_kind
        from base
        where rushing_yards is not null

        union all

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
            'rushing_tds' as stat_name,
            rushing_tds as stat_value,
            'real_world' as measure_domain,
            'projection' as stat_kind
        from base
        where rushing_tds is not null

        -- Receiving stats
        union all

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
            'targets' as stat_name,
            targets as stat_value,
            'real_world' as measure_domain,
            'projection' as stat_kind
        from base
        where targets is not null

        union all

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
            'receptions' as stat_name,
            receptions as stat_value,
            'real_world' as measure_domain,
            'projection' as stat_kind
        from base
        where receptions is not null

        union all

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
            'receiving_yards' as stat_name,
            receiving_yards as stat_value,
            'real_world' as measure_domain,
            'projection' as stat_kind
        from base
        where receiving_yards is not null

        union all

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
            'receiving_tds' as stat_name,
            receiving_tds as stat_value,
            'real_world' as measure_domain,
            'projection' as stat_kind
        from base
        where receiving_tds is not null

        -- Turnovers
        union all

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
            'fumbles_lost' as stat_name,
            fumbles_lost as stat_value,
            'real_world' as measure_domain,
            'projection' as stat_kind
        from base
        where fumbles_lost is not null

        -- IDP stats
        union all

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
            'idp_solo_tackles' as stat_name,
            idp_solo_tackles as stat_value,
            'real_world' as measure_domain,
            'projection' as stat_kind
        from base
        where idp_solo_tackles is not null

        union all

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
            'idp_assisted_tackles' as stat_name,
            idp_assisted_tackles as stat_value,
            'real_world' as measure_domain,
            'projection' as stat_kind
        from base
        where idp_assisted_tackles is not null

        union all

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
            'idp_sacks' as stat_name,
            idp_sacks as stat_value,
            'real_world' as measure_domain,
            'projection' as stat_kind
        from base
        where idp_sacks is not null

        union all

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
            'idp_passes_defended' as stat_name,
            idp_passes_defended as stat_value,
            'real_world' as measure_domain,
            'projection' as stat_kind
        from base
        where idp_passes_defended is not null

        union all

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
            'idp_interceptions' as stat_name,
            idp_interceptions as stat_value,
            'real_world' as measure_domain,
            'projection' as stat_kind
        from base
        where idp_interceptions is not null

        union all

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
            'idp_fumbles_forced' as stat_name,
            idp_fumbles_forced as stat_value,
            'real_world' as measure_domain,
            'projection' as stat_kind
        from base
        where idp_fumbles_forced is not null

        union all

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
            'idp_fumbles_recovered' as stat_name,
            idp_fumbles_recovered as stat_value,
            'real_world' as measure_domain,
            'projection' as stat_kind
        from base
        where idp_fumbles_recovered is not null

        union all

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
            'idp_touchdowns' as stat_name,
            idp_touchdowns as stat_value,
            'real_world' as measure_domain,
            'projection' as stat_kind
        from base
        where idp_touchdowns is not null
    )

select *
from unpivoted
