{{ config(materialized="table", unique_key='transaction_id_unique') }}

/*
FA Acquisition History - analyze winning bids for predictive modeling.

Grain: transaction_id_unique (one row per FA signing)
Purpose: Train bid prediction model for FASA
*/
with
    fa_acquisitions as (
        select
            t.transaction_id_unique,
            t.transaction_date,
            t.season,
            t.period_type,
            t.week,
            t.player_id,
            t.player_key,
            t.player_name,
            t.position,
            t.to_franchise_id,
            t.to_franchise_name,
            t.contract_total as bid_amount,
            t.contract_years as contract_length,
            t.contract_total / nullif(t.contract_years, 0) as aav
        from {{ ref("fct_league_transactions") }} t
        where
            t.transaction_type = 'fasa_signing'  -- Only in-season FASA, exclude FAAD
            and t.asset_type = 'player'
            and t.contract_total is not null
            and t.position in ('QB', 'RB', 'WR', 'TE')
            and t.week is not null  -- Ensure we only get in-season transactions
    ),

    -- Get player performance at time of signing (calendar-based L4 weeks)
    player_performance_context_calendar as (
        select
            fa.transaction_id_unique,

            -- Recent performance (last 4 CALENDAR weeks before signing - current
            -- season only)
            avg(
                case when mfa.week between fa.week - 4 and fa.week - 1 then mfa.fantasy_points end
            ) as fantasy_ppg_l4_weeks,

            -- Season average before signing
            avg(case when mfa.week < fa.week then mfa.fantasy_points end) as fantasy_ppg_season_before_signing,

            -- Usage metrics (calendar-based)
            avg(
                case when mfa.week between fa.week - 4 and fa.week - 1 then mfa.carries + mfa.targets end
            ) as touches_per_game_l4_weeks

        from fa_acquisitions fa
        left join {{ ref("mrt_fantasy_actuals_weekly") }} mfa on fa.player_id = mfa.player_id and fa.season = mfa.season
        group by 1
    ),

    -- Get player performance based on last 4 ACTUAL GAMES played (cross-season)
    player_games_ranked as (
        select
            fa.transaction_id_unique,
            fa.transaction_date,
            fa.week as signed_week,
            fa.season as signed_season,
            mfa.season as game_season,
            mfa.week as game_week,
            mfa.fantasy_points,
            mfa.carries,
            mfa.targets,
            -- Rank games by recency (most recent = 1)
            row_number() over (
                partition by fa.transaction_id_unique order by mfa.season desc, mfa.week desc
            ) as game_rank
        from fa_acquisitions fa
        left join
            {{ ref("mrt_fantasy_actuals_weekly") }} mfa
            on fa.player_id = mfa.player_id
            -- Games before signing (any season)
            and (fa.season > mfa.season or (fa.season = mfa.season and fa.week > mfa.week))
    ),

    player_performance_context_games as (
        select
            transaction_id_unique,
            -- Last 4 actual games played before signing
            avg(case when game_rank <= 4 then fantasy_points end) as fantasy_ppg_l4_games,
            avg(case when game_rank <= 4 then carries + targets end) as touches_per_game_l4_games,
            -- Recency: estimate days since last game (approximate based on weeks)
            min(
                case when game_rank = 1 then (signed_season - game_season) * 365 + (signed_week - game_week) * 7 end
            ) as days_since_last_game
        from player_games_ranked
        group by 1
    ),

    -- Calculate position scarcity at time of signing
    position_scarcity as (
        select
            fa.transaction_id_unique,
            fa.position,
            fa.season,
            fa.week,

            -- Count quality FAs available (projected > replacement level)
            count(case when proj.projected_fantasy_points > 5.0 then 1 end) as quality_fas_available,

            -- Market depth indicator (0-1, lower = more scarce)
            count(case when proj.projected_fantasy_points > 5.0 then 1 end)
            / nullif(count(*), 0.0) as market_depth_ratio

        from fa_acquisitions fa
        left join
            {{ ref("mrt_fantasy_projections") }} proj
            on fa.season = proj.season
            and fa.week = proj.week
            and fa.position = proj.position
        group by 1, 2, 3, 4
    )

select
    -- Base transaction details
    fa.transaction_id_unique,
    fa.transaction_date,
    fa.season,
    fa.period_type,
    fa.week,
    fa.player_id,
    fa.player_key,
    fa.player_name,
    fa.position,
    fa.to_franchise_id,
    fa.to_franchise_name,
    fa.bid_amount,
    fa.contract_length,
    fa.aav,

    -- Performance context (calendar-based L4 weeks - current season only)
    ppc_cal.fantasy_ppg_l4_weeks,
    ppc_cal.fantasy_ppg_season_before_signing,
    ppc_cal.touches_per_game_l4_weeks,

    -- Performance context (game-based L4 games - cross-season)
    ppc_games.fantasy_ppg_l4_games,
    ppc_games.touches_per_game_l4_games,
    ppc_games.days_since_last_game,

    -- Market context
    ps.quality_fas_available,
    ps.market_depth_ratio,

    -- Time context (in-season FASA only)
    case
        when fa.week <= 4 then 'Early Season' when fa.week between 5 and 12 then 'Mid Season' else 'Late Season'
    end as season_phase,

    -- Performance tier at signing (use games-based as primary, fallback to weeks)
    case
        when coalesce(ppc_games.fantasy_ppg_l4_games, ppc_cal.fantasy_ppg_l4_weeks) >= 12.0
        then 'Elite'
        when coalesce(ppc_games.fantasy_ppg_l4_games, ppc_cal.fantasy_ppg_l4_weeks) >= 8.0
        then 'Strong'
        when coalesce(ppc_games.fantasy_ppg_l4_games, ppc_cal.fantasy_ppg_l4_weeks) >= 5.0
        then 'Viable'
        else 'Speculative'
    end as performance_tier,

    -- Bid efficiency metrics (use games-based as primary)
    fa.bid_amount
    / nullif(coalesce(ppc_games.fantasy_ppg_l4_games, ppc_cal.fantasy_ppg_l4_weeks), 0) as dollars_per_ppg,

    -- Metadata
    current_date as asof_date

from fa_acquisitions fa
left join player_performance_context_calendar ppc_cal on fa.transaction_id_unique = ppc_cal.transaction_id_unique
left join player_performance_context_games ppc_games on fa.transaction_id_unique = ppc_games.transaction_id_unique
left join position_scarcity ps on fa.transaction_id_unique = ps.transaction_id_unique
