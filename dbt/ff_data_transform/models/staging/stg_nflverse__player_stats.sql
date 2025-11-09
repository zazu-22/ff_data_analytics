{{
    config(
        materialized="view",
        unique_key=['player_key', 'game_id', 'stat_name', 'provider', 'measure_domain', 'stat_kind']
    )
}}
/*
Stage nflverse weekly player stats with mfl_id crosswalk and long-form unpivot.
Source: data/raw/nflverse/weekly/ (load_player_stats with summary_level='week')
Output grain: one row per player per game per stat
Crosswalk: player_id (gsis_id) → mfl_id via dim_player_id_xref
ADR-009: Feeds into consolidated fct_player_stats
ADR-010: Uses mfl_id as canonical player_id
*/
with
    base as (
        select
            -- Raw player_id column contains gsis_id values
            w.player_id as gsis_id_raw,
            -- Generate surrogate game_id (raw data doesn't have it)
            cast(w.season as varchar)
            || '_'
            || cast(w.week as varchar)
            || '_'
            || w.team
            || '_'
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
            -- Fantasy points (pre-calculated, not used in fact table but useful for
            -- validation)
            w.fantasy_points,
            w.fantasy_points_ppr
        from
            -- noqa: disable=references.qualification
            read_parquet(
                '{{ var("external_root", "data/raw") }}/nflverse/weekly/dt=*/*.parquet', hive_partitioning = true
            ) w
        -- noqa: enable=references.qualification
        -- Data quality filters: Exclude records missing required identifiers
        -- player_id (gsis_id): ~0.12% of raw data has NULL (113/97,415 rows)
        -- These are unidentifiable players with no position info
        -- Cannot perform player-level analysis without player identification
        where
            w.player_id is not null
            and w.season is not null
            and w.week is not null
            -- Load multiple snapshots to get historical coverage (2020-2025)
            -- Historical snapshot (2020-2024 + partial 2025) + latest snapshot
            -- (complete 2025)
            and (
                w.dt = '2025-10-01'  -- Historical: 2020-2024 + partial 2025
                or w.dt = '2025-10-27'  -- Latest: Complete 2024-2025
            )
    ),
    crosswalk as (
        -- Map raw provider IDs to canonical player_id via ff_playerids crosswalk
        -- Crosswalk source: nflverse ff_playerids dataset (9,734 players, 20 provider
        -- IDs)
        -- Mapping coverage: ~99.9% of identifiable weekly players map successfully
        select
            base.gsis_id_raw,
            base.game_id,
            base.season,
            base.week,
            base.season_type,
            base.team,
            base.opponent_team,
            -- Map gsis_id → player_id (canonical sequential surrogate per ADR-011)
            coalesce(xref.player_id, -1) as player_id,
            -- Use position from crosswalk if raw data has null
            coalesce(base.position, xref.position) as position,
            -- All stat columns
            base.completions,
            base.attempts,
            base.passing_yards,
            base.passing_tds,
            base.passing_interceptions,
            base.passing_air_yards,
            base.passing_yards_after_catch,
            base.passing_first_downs,
            base.passing_epa,
            base.passing_2pt_conversions,
            base.passing_cpoe,
            base.carries,
            base.rushing_yards,
            base.rushing_tds,
            base.rushing_fumbles,
            base.rushing_fumbles_lost,
            base.rushing_first_downs,
            base.rushing_epa,
            base.rushing_2pt_conversions,
            base.targets,
            base.receptions,
            base.receiving_yards,
            base.receiving_tds,
            base.receiving_fumbles,
            base.receiving_fumbles_lost,
            base.receiving_air_yards,
            base.receiving_yards_after_catch,
            base.receiving_first_downs,
            base.receiving_epa,
            base.receiving_2pt_conversions,
            base.def_tackles_solo,
            base.def_tackles_with_assist,
            base.def_tackle_assists,
            base.def_tackles_for_loss,
            base.def_tackles_for_loss_yards,
            base.def_fumbles,
            base.def_fumbles_forced,
            base.def_interceptions,
            base.def_interception_yards,
            base.def_pass_defended,
            base.def_sacks,
            base.def_sack_yards,
            base.def_qb_hits,
            base.def_tds,
            base.def_safeties,
            base.sacks_suffered,
            base.sack_yards_lost,
            base.sack_fumbles,
            base.sack_fumbles_lost,
            base.special_teams_tds,
            base.fg_att,
            base.fg_made,
            base.fg_missed,
            base.fg_made_0_19,
            base.fg_made_20_29,
            base.fg_made_30_39,
            base.fg_made_40_49,
            base.fg_made_50_59,
            base.fg_made_60_,
            base.fg_missed_0_19,
            base.fg_missed_20_29,
            base.fg_missed_30_39,
            base.fg_missed_40_49,
            base.fg_missed_50_59,
            base.fg_missed_60_,
            base.pat_att,
            base.pat_made,
            base.pat_missed,
            base.gwfg_att,
            base.gwfg_made,
            base.gwfg_missed,
            -- Composite key for grain uniqueness (uses raw ID when unmapped)
            -- Prevents duplicate grain violations when multiple unmapped players in
            -- same game
            -- Mapped players: player_key = player_id (as varchar)
            -- Unmapped players: player_key = gsis_id (preserves identity via raw
            -- provider ID)
            -- Unknown edge case: player_key = 'UNKNOWN_' || game_id (defensive
            -- fail-safe)
            case
                when coalesce(xref.player_id, -1) != -1
                then cast(xref.player_id as varchar)
                else coalesce(base.gsis_id_raw, 'UNKNOWN_' || base.game_id)
            end as player_key
        from base
        left join {{ ref("dim_player_id_xref") }} xref on base.gsis_id_raw = xref.gsis_id
    ),
    unpivoted as (
        -- Unpivot all stats to long form
        -- Pattern: SELECT player_id, player_key, game_id, season, week, season_type,
        -- position,
        -- 'stat_name' AS stat_name, stat_value,
        -- 'real_world' AS measure_domain, 'actual' AS stat_kind, 'nflverse' AS provider
        -- FROM crosswalk WHERE stat_value IS NOT NULL
        -- Passing
        select
            player_id,
            player_key,
            game_id,
            season,
            week,
            season_type,
            position,
            team,
            opponent_team,
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
            team,
            opponent_team,
            'attempts' as stat_name,
            cast(attempts as double) as stat_value,
            'real_world' as measure_domain,
            'actual' as stat_kind,
            'nflverse' as provider
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
            team,
            opponent_team,
            'passing_yards' as stat_name,
            cast(passing_yards as double) as stat_value,
            'real_world' as measure_domain,
            'actual' as stat_kind,
            'nflverse' as provider
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
            team,
            opponent_team,
            'passing_tds' as stat_name,
            cast(passing_tds as double) as stat_value,
            'real_world' as measure_domain,
            'actual' as stat_kind,
            'nflverse' as provider
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
            team,
            opponent_team,
            'passing_interceptions' as stat_name,
            cast(passing_interceptions as double) as stat_value,
            'real_world' as measure_domain,
            'actual' as stat_kind,
            'nflverse' as provider
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
            team,
            opponent_team,
            'passing_air_yards' as stat_name,
            cast(passing_air_yards as double) as stat_value,
            'real_world' as measure_domain,
            'actual' as stat_kind,
            'nflverse' as provider
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
            team,
            opponent_team,
            'passing_yards_after_catch' as stat_name,
            cast(passing_yards_after_catch as double) as stat_value,
            'real_world' as measure_domain,
            'actual' as stat_kind,
            'nflverse' as provider
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
            team,
            opponent_team,
            'passing_first_downs' as stat_name,
            cast(passing_first_downs as double) as stat_value,
            'real_world' as measure_domain,
            'actual' as stat_kind,
            'nflverse' as provider
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
            team,
            opponent_team,
            'passing_epa' as stat_name,
            cast(passing_epa as double) as stat_value,
            'real_world' as measure_domain,
            'actual' as stat_kind,
            'nflverse' as provider
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
            team,
            opponent_team,
            'passing_2pt_conversions' as stat_name,
            cast(passing_2pt_conversions as double) as stat_value,
            'real_world' as measure_domain,
            'actual' as stat_kind,
            'nflverse' as provider
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
            team,
            opponent_team,
            'passing_cpoe' as stat_name,
            cast(passing_cpoe as double) as stat_value,
            'real_world' as measure_domain,
            'actual' as stat_kind,
            'nflverse' as provider
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
            team,
            opponent_team,
            'carries' as stat_name,
            cast(carries as double) as stat_value,
            'real_world' as measure_domain,
            'actual' as stat_kind,
            'nflverse' as provider
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
            team,
            opponent_team,
            'rushing_yards' as stat_name,
            cast(rushing_yards as double) as stat_value,
            'real_world' as measure_domain,
            'actual' as stat_kind,
            'nflverse' as provider
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
            team,
            opponent_team,
            'rushing_tds' as stat_name,
            cast(rushing_tds as double) as stat_value,
            'real_world' as measure_domain,
            'actual' as stat_kind,
            'nflverse' as provider
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
            team,
            opponent_team,
            'rushing_fumbles' as stat_name,
            cast(rushing_fumbles as double) as stat_value,
            'real_world' as measure_domain,
            'actual' as stat_kind,
            'nflverse' as provider
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
            team,
            opponent_team,
            'rushing_fumbles_lost' as stat_name,
            cast(rushing_fumbles_lost as double) as stat_value,
            'real_world' as measure_domain,
            'actual' as stat_kind,
            'nflverse' as provider
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
            team,
            opponent_team,
            'rushing_first_downs' as stat_name,
            cast(rushing_first_downs as double) as stat_value,
            'real_world' as measure_domain,
            'actual' as stat_kind,
            'nflverse' as provider
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
            team,
            opponent_team,
            'rushing_epa' as stat_name,
            cast(rushing_epa as double) as stat_value,
            'real_world' as measure_domain,
            'actual' as stat_kind,
            'nflverse' as provider
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
            team,
            opponent_team,
            'rushing_2pt_conversions' as stat_name,
            cast(rushing_2pt_conversions as double) as stat_value,
            'real_world' as measure_domain,
            'actual' as stat_kind,
            'nflverse' as provider
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
            team,
            opponent_team,
            'targets' as stat_name,
            cast(targets as double) as stat_value,
            'real_world' as measure_domain,
            'actual' as stat_kind,
            'nflverse' as provider
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
            team,
            opponent_team,
            'receptions' as stat_name,
            cast(receptions as double) as stat_value,
            'real_world' as measure_domain,
            'actual' as stat_kind,
            'nflverse' as provider
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
            team,
            opponent_team,
            'receiving_yards' as stat_name,
            cast(receiving_yards as double) as stat_value,
            'real_world' as measure_domain,
            'actual' as stat_kind,
            'nflverse' as provider
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
            team,
            opponent_team,
            'receiving_tds' as stat_name,
            cast(receiving_tds as double) as stat_value,
            'real_world' as measure_domain,
            'actual' as stat_kind,
            'nflverse' as provider
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
            team,
            opponent_team,
            'receiving_fumbles' as stat_name,
            cast(receiving_fumbles as double) as stat_value,
            'real_world' as measure_domain,
            'actual' as stat_kind,
            'nflverse' as provider
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
            team,
            opponent_team,
            'receiving_fumbles_lost' as stat_name,
            cast(receiving_fumbles_lost as double) as stat_value,
            'real_world' as measure_domain,
            'actual' as stat_kind,
            'nflverse' as provider
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
            team,
            opponent_team,
            'receiving_air_yards' as stat_name,
            cast(receiving_air_yards as double) as stat_value,
            'real_world' as measure_domain,
            'actual' as stat_kind,
            'nflverse' as provider
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
            team,
            opponent_team,
            'receiving_yards_after_catch' as stat_name,
            cast(receiving_yards_after_catch as double) as stat_value,
            'real_world' as measure_domain,
            'actual' as stat_kind,
            'nflverse' as provider
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
            team,
            opponent_team,
            'receiving_first_downs' as stat_name,
            cast(receiving_first_downs as double) as stat_value,
            'real_world' as measure_domain,
            'actual' as stat_kind,
            'nflverse' as provider
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
            team,
            opponent_team,
            'receiving_epa' as stat_name,
            cast(receiving_epa as double) as stat_value,
            'real_world' as measure_domain,
            'actual' as stat_kind,
            'nflverse' as provider
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
            team,
            opponent_team,
            'receiving_2pt_conversions' as stat_name,
            cast(receiving_2pt_conversions as double) as stat_value,
            'real_world' as measure_domain,
            'actual' as stat_kind,
            'nflverse' as provider
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
            team,
            opponent_team,
            'def_tackles_solo' as stat_name,
            cast(def_tackles_solo as double) as stat_value,
            'real_world' as measure_domain,
            'actual' as stat_kind,
            'nflverse' as provider
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
            team,
            opponent_team,
            'def_tackles_with_assist' as stat_name,
            cast(def_tackles_with_assist as double) as stat_value,
            'real_world' as measure_domain,
            'actual' as stat_kind,
            'nflverse' as provider
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
            team,
            opponent_team,
            'def_tackle_assists' as stat_name,
            cast(def_tackle_assists as double) as stat_value,
            'real_world' as measure_domain,
            'actual' as stat_kind,
            'nflverse' as provider
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
            team,
            opponent_team,
            'def_tackles_for_loss' as stat_name,
            cast(def_tackles_for_loss as double) as stat_value,
            'real_world' as measure_domain,
            'actual' as stat_kind,
            'nflverse' as provider
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
            team,
            opponent_team,
            'def_tackles_for_loss_yards' as stat_name,
            cast(def_tackles_for_loss_yards as double) as stat_value,
            'real_world' as measure_domain,
            'actual' as stat_kind,
            'nflverse' as provider
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
            team,
            opponent_team,
            'def_fumbles' as stat_name,
            cast(def_fumbles as double) as stat_value,
            'real_world' as measure_domain,
            'actual' as stat_kind,
            'nflverse' as provider
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
            team,
            opponent_team,
            'def_fumbles_forced' as stat_name,
            cast(def_fumbles_forced as double) as stat_value,
            'real_world' as measure_domain,
            'actual' as stat_kind,
            'nflverse' as provider
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
            team,
            opponent_team,
            'def_interceptions' as stat_name,
            cast(def_interceptions as double) as stat_value,
            'real_world' as measure_domain,
            'actual' as stat_kind,
            'nflverse' as provider
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
            team,
            opponent_team,
            'def_interception_yards' as stat_name,
            cast(def_interception_yards as double) as stat_value,
            'real_world' as measure_domain,
            'actual' as stat_kind,
            'nflverse' as provider
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
            team,
            opponent_team,
            'def_pass_defended' as stat_name,
            cast(def_pass_defended as double) as stat_value,
            'real_world' as measure_domain,
            'actual' as stat_kind,
            'nflverse' as provider
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
            team,
            opponent_team,
            'def_sacks' as stat_name,
            cast(def_sacks as double) as stat_value,
            'real_world' as measure_domain,
            'actual' as stat_kind,
            'nflverse' as provider
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
            team,
            opponent_team,
            'def_sack_yards' as stat_name,
            cast(def_sack_yards as double) as stat_value,
            'real_world' as measure_domain,
            'actual' as stat_kind,
            'nflverse' as provider
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
            team,
            opponent_team,
            'def_qb_hits' as stat_name,
            cast(def_qb_hits as double) as stat_value,
            'real_world' as measure_domain,
            'actual' as stat_kind,
            'nflverse' as provider
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
            team,
            opponent_team,
            'def_tds' as stat_name,
            cast(def_tds as double) as stat_value,
            'real_world' as measure_domain,
            'actual' as stat_kind,
            'nflverse' as provider
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
            team,
            opponent_team,
            'def_safeties' as stat_name,
            cast(def_safeties as double) as stat_value,
            'real_world' as measure_domain,
            'actual' as stat_kind,
            'nflverse' as provider
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
            team,
            opponent_team,
            'sacks_suffered' as stat_name,
            cast(sacks_suffered as double) as stat_value,
            'real_world' as measure_domain,
            'actual' as stat_kind,
            'nflverse' as provider
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
            team,
            opponent_team,
            'sack_yards_lost' as stat_name,
            cast(sack_yards_lost as double) as stat_value,
            'real_world' as measure_domain,
            'actual' as stat_kind,
            'nflverse' as provider
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
            team,
            opponent_team,
            'sack_fumbles' as stat_name,
            cast(sack_fumbles as double) as stat_value,
            'real_world' as measure_domain,
            'actual' as stat_kind,
            'nflverse' as provider
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
            team,
            opponent_team,
            'sack_fumbles_lost' as stat_name,
            cast(sack_fumbles_lost as double) as stat_value,
            'real_world' as measure_domain,
            'actual' as stat_kind,
            'nflverse' as provider
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
            team,
            opponent_team,
            'special_teams_tds' as stat_name,
            cast(special_teams_tds as double) as stat_value,
            'real_world' as measure_domain,
            'actual' as stat_kind,
            'nflverse' as provider
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
            team,
            opponent_team,
            'fg_att' as stat_name,
            cast(fg_att as double) as stat_value,
            'real_world' as measure_domain,
            'actual' as stat_kind,
            'nflverse' as provider
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
            team,
            opponent_team,
            'fg_made' as stat_name,
            cast(fg_made as double) as stat_value,
            'real_world' as measure_domain,
            'actual' as stat_kind,
            'nflverse' as provider
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
            team,
            opponent_team,
            'fg_missed' as stat_name,
            cast(fg_missed as double) as stat_value,
            'real_world' as measure_domain,
            'actual' as stat_kind,
            'nflverse' as provider
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
            team,
            opponent_team,
            'fg_made_0_19' as stat_name,
            cast(fg_made_0_19 as double) as stat_value,
            'real_world' as measure_domain,
            'actual' as stat_kind,
            'nflverse' as provider
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
            team,
            opponent_team,
            'fg_made_20_29' as stat_name,
            cast(fg_made_20_29 as double) as stat_value,
            'real_world' as measure_domain,
            'actual' as stat_kind,
            'nflverse' as provider
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
            team,
            opponent_team,
            'fg_made_30_39' as stat_name,
            cast(fg_made_30_39 as double) as stat_value,
            'real_world' as measure_domain,
            'actual' as stat_kind,
            'nflverse' as provider
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
            team,
            opponent_team,
            'fg_made_40_49' as stat_name,
            cast(fg_made_40_49 as double) as stat_value,
            'real_world' as measure_domain,
            'actual' as stat_kind,
            'nflverse' as provider
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
            team,
            opponent_team,
            'fg_made_50_59' as stat_name,
            cast(fg_made_50_59 as double) as stat_value,
            'real_world' as measure_domain,
            'actual' as stat_kind,
            'nflverse' as provider
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
            team,
            opponent_team,
            'fg_made_60_' as stat_name,
            cast(fg_made_60_ as double) as stat_value,
            'real_world' as measure_domain,
            'actual' as stat_kind,
            'nflverse' as provider
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
            team,
            opponent_team,
            'fg_missed_0_19' as stat_name,
            cast(fg_missed_0_19 as double) as stat_value,
            'real_world' as measure_domain,
            'actual' as stat_kind,
            'nflverse' as provider
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
            team,
            opponent_team,
            'fg_missed_20_29' as stat_name,
            cast(fg_missed_20_29 as double) as stat_value,
            'real_world' as measure_domain,
            'actual' as stat_kind,
            'nflverse' as provider
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
            team,
            opponent_team,
            'fg_missed_30_39' as stat_name,
            cast(fg_missed_30_39 as double) as stat_value,
            'real_world' as measure_domain,
            'actual' as stat_kind,
            'nflverse' as provider
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
            team,
            opponent_team,
            'fg_missed_40_49' as stat_name,
            cast(fg_missed_40_49 as double) as stat_value,
            'real_world' as measure_domain,
            'actual' as stat_kind,
            'nflverse' as provider
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
            team,
            opponent_team,
            'fg_missed_50_59' as stat_name,
            cast(fg_missed_50_59 as double) as stat_value,
            'real_world' as measure_domain,
            'actual' as stat_kind,
            'nflverse' as provider
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
            team,
            opponent_team,
            'fg_missed_60_' as stat_name,
            cast(fg_missed_60_ as double) as stat_value,
            'real_world' as measure_domain,
            'actual' as stat_kind,
            'nflverse' as provider
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
            team,
            opponent_team,
            'pat_att' as stat_name,
            cast(pat_att as double) as stat_value,
            'real_world' as measure_domain,
            'actual' as stat_kind,
            'nflverse' as provider
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
            team,
            opponent_team,
            'pat_made' as stat_name,
            cast(pat_made as double) as stat_value,
            'real_world' as measure_domain,
            'actual' as stat_kind,
            'nflverse' as provider
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
            team,
            opponent_team,
            'pat_missed' as stat_name,
            cast(pat_missed as double) as stat_value,
            'real_world' as measure_domain,
            'actual' as stat_kind,
            'nflverse' as provider
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
            team,
            opponent_team,
            'gwfg_att' as stat_name,
            cast(gwfg_att as double) as stat_value,
            'real_world' as measure_domain,
            'actual' as stat_kind,
            'nflverse' as provider
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
            team,
            opponent_team,
            'gwfg_made' as stat_name,
            cast(gwfg_made as double) as stat_value,
            'real_world' as measure_domain,
            'actual' as stat_kind,
            'nflverse' as provider
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
            team,
            opponent_team,
            'gwfg_missed' as stat_name,
            cast(gwfg_missed as double) as stat_value,
            'real_world' as measure_domain,
            'actual' as stat_kind,
            'nflverse' as provider
        from crosswalk
        where gwfg_missed is not null
    ),
    deduplicated as (
        -- Deduplicate overlapping seasons (2024 appears in both snapshots)
        -- Prefer latest snapshot for any overlaps
        select *
        from unpivoted
        qualify
            row_number() over (
                partition by player_key, game_id, stat_name, provider, measure_domain, stat_kind
                order by season desc, week desc
            )
            = 1
    )
select
    player_id,
    player_key,
    game_id,
    season,
    week,
    season_type,
    position,
    stat_name,
    stat_value,
    measure_domain,
    stat_kind,
    provider,
    team,
    opponent_team
from deduplicated
