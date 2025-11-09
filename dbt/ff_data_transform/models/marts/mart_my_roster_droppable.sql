{{ config(materialized="table", unique_key=['player_key', 'asof_date']) }}

-- Grain: player_key, asof_date
-- Purpose: Identify drop candidates on Jason's roster
with
    my_franchise as (
        select franchise_id from {{ ref("dim_franchise") }} where gm_tab = 'Jason' and is_current_owner = true
    ),

    my_roster as (
        select distinct c.player_id as player_key, d.position
        from {{ ref("stg_sheets__contracts_active") }} c
        inner join {{ ref("dim_player") }} d on c.player_id = d.player_id
        where c.franchise_id in (select franchise_id from my_franchise) and c.obligation_year = year(current_date)
    ),

    contracts as (
        select
            player_id as player_key,
            count(distinct obligation_year) as years_remaining,
            sum(case when obligation_year = year(current_date) then cap_hit end) as current_year_cap_hit,
            sum(case when obligation_year > year(current_date) then cap_hit end) as future_years_cap_hit,
            sum(cap_hit) as total_remaining
        from {{ ref("stg_sheets__contracts_active") }}
        where franchise_id in (select franchise_id from my_franchise)
        group by player_id
    ),

    dead_cap as (
        -- Calculate dead cap if cut now using dim_cut_liability_schedule
        select c.player_key, c.total_remaining * dl.dead_cap_pct as dead_cap_if_cut_now
        from contracts c
        inner join {{ ref("dim_cut_liability_schedule") }} dl on c.years_remaining = dl.contract_year
    ),

    performance as (
        select player_id as player_key, avg(case when game_recency <= 8 then fantasy_points end) as fantasy_ppg_last_8
        from
            (
                select
                    player_id,
                    fantasy_points,
                    row_number() over (partition by player_id order by season desc, week desc) as game_recency
                from {{ ref("mart_fantasy_actuals_weekly") }}
                where season = year(current_date)
            )
        where game_recency <= 8
        group by player_id
    ),

    projections as (
        select
            player_id,
            avg(projected_fantasy_points) as projected_ppg_ros,
            sum(projected_fantasy_points) as projected_total_ros,
            count(*) as weeks_remaining
        from {{ ref("mart_fantasy_projections") }}
        where
            season = year(current_date)
            and week > (
                select max(week)
                from {{ ref("dim_schedule") }}
                where season = year(current_date) and cast(game_date as date) < current_date
            )
            and horizon = 'weekly'
        group by player_id
    ),

    position_depth as (
        -- Rank players at each position on my roster
        select
            player_key, row_number() over (partition by position order by projected_ppg_ros desc) as position_depth_rank
        from my_roster
        left join projections on my_roster.player_key = projections.player_id
    )

select
    -- Identity
    r.player_key,
    dim.display_name as player_name,
    r.position,

    -- Contract
    c.years_remaining,
    c.current_year_cap_hit,
    c.future_years_cap_hit,
    c.total_remaining,
    dc.dead_cap_if_cut_now,
    c.current_year_cap_hit - dc.dead_cap_if_cut_now as cap_space_freed,

    -- Performance
    perf.fantasy_ppg_last_8,
    proj.projected_ppg_ros,

    -- Value Assessment
    proj.projected_ppg_ros / nullif(c.current_year_cap_hit, 0) as points_per_dollar,
    proj.projected_ppg_ros - (
        select percentile_cont(0.5) within group (order by projected_ppg_ros)
        from {{ ref("mart_fasa_targets") }}
        where position = r.position
    ) as replacement_surplus,

    -- Droppable score (0-100, higher = more droppable)
    (
        case when proj.projected_ppg_ros < 5 then 30 else 0 end  -- Low production
        + case when c.current_year_cap_hit > 10 then 30 else 0 end  -- High cap hit
        + case when dc.dead_cap_if_cut_now < 5 then 20 else 0 end  -- Low dead cap
        + case when pd.position_depth_rank > 3 then 20 else 0 end  -- Roster depth
    ) as droppable_score,

    -- Opportunity cost
    (c.current_year_cap_hit - dc.dead_cap_if_cut_now) - (proj.projected_ppg_ros / 10) as opportunity_cost,

    -- Roster Context
    pd.position_depth_rank,
    case
        when pd.position_depth_rank <= 2 then 'STARTER' when pd.position_depth_rank = 3 then 'FLEX' else 'BENCH'
    end as roster_tier,
    c.years_remaining as weeks_until_contract_expires,

    -- Recommendation
    case
        when droppable_score >= 80
        then 'DROP_FOR_CAP'
        when droppable_score >= 60 and proj.projected_ppg_ros < 8
        then 'CONSIDER'
        when droppable_score >= 40
        then 'DROP_FOR_UPSIDE'
        else 'KEEP'
    end as drop_recommendation,

    -- Metadata
    current_date as asof_date

from my_roster r
left join contracts c on r.player_key = c.player_key
left join dead_cap dc on r.player_key = dc.player_key
left join performance perf on r.player_key = perf.player_key
left join projections proj on r.player_key = proj.player_id
left join position_depth pd on r.player_key = pd.player_key
left join {{ ref("dim_player") }} dim on r.player_key = dim.player_id

order by droppable_score desc
