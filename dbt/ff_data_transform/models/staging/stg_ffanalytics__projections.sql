{{
    config(
        materialized="view",
        unique_key=['player_id', 'season', 'week', 'horizon', 'asof_date', 'provider']
    )
}}

/*
Stage FFanalytics weighted consensus projections.

Source: data/raw/ffanalytics/projections/ (consensus output from R runner)
Output grain: one row per player per stat per projection horizon per as-of date
Crosswalk: player name → mfl_id via dim_player_id_xref (already done in R runner)

Key transformations:
- Real-world stats only (measure_domain='real_world')
- Normalize horizon values ('weekly', 'full_season', 'rest_of_season')
- Map to canonical stat names for consistency with actuals
- Filter out unmapped players (player_id = -1) for now

NOTE: Player mapping happens in R runner, not here. R runner outputs player_id already.
*/
with
    base as (
        select
            -- Player identity (already mapped by R runner)
            cast(player_id as integer) as player_id_raw,
            player as player_name,
            coalesce(position_final, pos) as position,
            team as current_team,
            team as team_consensus,  -- Raw consensus value for QA

            -- Time dimensions
            season,
            week,
            asof_date,  -- when projection was made

            -- Horizon (already computed by R runner)
            horizon,  -- 'weekly', 'full_season'

            -- Provider info
            provider,  -- 'ffanalytics_consensus'
            source_count,  -- how many sources contributed
            total_weight,  -- sum of weights

            -- Passing stats
            pass_comp as completions,
            pass_att as attempts,
            pass_yds as passing_yards,
            pass_tds as passing_tds,
            pass_int as interceptions,

            -- Rushing stats
            rush_att as rushing_attempts,
            rush_yds as rushing_yards,
            rush_tds as rushing_tds,

            -- Receiving stats
            cast(null as double) as targets,  -- Not in FFanalytics output
            rec as receptions,
            rec_yds as receiving_yards,
            rec_tds as receiving_tds,

            -- Turnovers
            fumbles_lost,

            -- IDP (Individual Defensive Player) stats
            idp_solo as idp_solo_tackles,
            idp_asst as idp_assisted_tackles,
            idp_sacks,
            idp_pd as idp_passes_defended,
            idp_int as idp_interceptions,
            idp_fum_force as idp_fumbles_forced,
            idp_fum_rec as idp_fumbles_recovered,
            idp_td as idp_touchdowns

        from
            read_parquet(
                '{{ var("external_root", "data/raw") }}/ffanalytics/projections/dt=*/projections_consensus_*.parquet',
                hive_partitioning = true
            )
        where
            1 = 1
            -- Filter to latest snapshot only
            and {{ snapshot_selection_strategy(
                var("external_root", "data/raw") ~ '/ffanalytics/projections/dt=*/*.parquet',
                strategy='latest_only'
            ) }}
            -- Filter out unmapped players (R runner sets player_id = -1 for unmapped)
            and cast(player_id as integer) > 0
    ),

    -- Normalize and add metadata columns
    normalized as (
        select
            -- Use raw player_id (it's already mfl_id from R runner)
            player_id_raw as player_id,
            player_name,
            position,
            current_team,
            team_consensus,
            season,
            -- Week is nullable for season-long projections
            case when horizon = 'full_season' then null else week end as week,
            asof_date,

            -- Normalize horizon enum
            case
                when horizon = 'weekly' then 'weekly' when horizon = 'full_season' then 'full_season' else 'unknown'
            end as horizon,

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

        from base
    )

select
    player_id,
    player_name,
    position,
    current_team,
    season,
    week,
    asof_date,
    horizon,
    provider,
    source_count,
    total_weight,
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
    idp_solo_tackles,
    idp_assisted_tackles,
    idp_sacks,
    idp_passes_defended,
    idp_interceptions,
    idp_fumbles_forced,
    idp_fumbles_recovered,
    idp_touchdowns,
    team_consensus
from normalized
