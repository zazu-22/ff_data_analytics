-- Grain: player_key, asof_date, week
-- Purpose: Score every FA for FASA with bid recommendations

with fa_pool as (
  select * from {{ ref('stg_sleeper__fa_pool') }}
),

recent_stats as (
  -- Aggregate recent performance from fantasy actuals
  select
    player_key,

    -- Last 3/4/8 games
    AVG(case when game_recency <= 3 then fantasy_points end) as fantasy_ppg_last_3,
    AVG(case when game_recency <= 4 then fantasy_points end) as fantasy_ppg_last_4,
    AVG(case when game_recency <= 8 then fantasy_points end) as fantasy_ppg_last_8,
    AVG(fantasy_points) as fantasy_ppg_season,

    -- Real-world volume (last 4 weeks)
    AVG(case when game_recency <= 4 then attempts end) as attempts_per_game_l4,
    AVG(case when game_recency <= 4 then targets end) as targets_per_game_l4,

    -- Efficiency
    SUM(rushing_yards) / NULLIF(SUM(carries), 0) as ypc,
    SUM(receiving_yards) / NULLIF(SUM(receptions), 0) as ypr,
    SUM(receptions) / NULLIF(SUM(targets), 0) as catch_rate

  from (
    select
      player_key,
      fantasy_points,
      attempts,
      targets,
      carries,
      rushing_yards,
      receiving_yards,
      receptions,
      ROW_NUMBER() over (partition by player_key order by season desc, week desc) as game_recency
    from {{ ref('mart_fantasy_actuals_weekly') }}
    where
      season = YEAR(CURRENT_DATE)
      and week
      <= (
        select MAX(week) from {{ ref('dim_schedule') }}
        where season = YEAR(CURRENT_DATE) and CAST(game_date as DATE) < CURRENT_DATE
      )
  )
  group by player_key
),

projections as (
  -- Rest of season projections (join through dim_player to get mfl_id)
  -- NOTE: proj.player_id is actually mfl_id from ffanalytics staging
  select
    dp.mfl_id,
    SUM(proj.projected_fantasy_points) as projected_total_ros,
    AVG(proj.projected_fantasy_points) as projected_ppg_ros,
    COUNT(*) as weeks_remaining
  from {{ ref('mart_fantasy_projections') }} proj
  inner join {{ ref('dim_player') }} dp on proj.player_id = dp.mfl_id  -- Join on mfl_id, not player_id!
  where
    proj.season = YEAR(CURRENT_DATE)
    and proj.week
    > (
      select MAX(week) from {{ ref('dim_schedule') }}
      where season = YEAR(CURRENT_DATE) and CAST(game_date as DATE) < CURRENT_DATE
    )
    and proj.horizon = 'weekly'  -- Changed from 'full_season'
    and dp.mfl_id is not NULL
  group by dp.mfl_id
),

opportunity as (
  -- Calculate opportunity shares from ff_opportunity attempt metrics
  -- rec_attempt / rec_attempt_team = target share
  -- rush_attempt / rush_attempt_team = rush share
  select
    player_key,
    AVG(case when game_recency <= 4 then target_share end) as target_share_l4,
    AVG(case when game_recency <= 4 then rush_share end) as rush_share_l4,
    -- Combined opportunity share (weighted average for RB/WR/TE)
    AVG(case
      when game_recency <= 4 then
        COALESCE(target_share, 0) * 0.6 + COALESCE(rush_share, 0) * 0.4
    end) as opportunity_share_l4
  from (
    select
      player_key,
      season,
      week,
      -- Calculate target share (receiving opportunity)
      MAX(case when stat_name = 'rec_attempt' then stat_value end)
      / NULLIF(MAX(case when stat_name = 'rec_attempt_team' then stat_value end), 0) as target_share,
      -- Calculate rush share (rushing opportunity)
      MAX(case when stat_name = 'rush_attempt' then stat_value end)
      / NULLIF(MAX(case when stat_name = 'rush_attempt_team' then stat_value end), 0) as rush_share,
      ROW_NUMBER() over (partition by player_key order by season desc, week desc) as game_recency
    from {{ ref('fact_player_stats') }}
    where
      stat_kind = 'actual'
      and measure_domain = 'real_world'
      and season = YEAR(CURRENT_DATE)
      and stat_name in ('rec_attempt', 'rec_attempt_team', 'rush_attempt', 'rush_attempt_team')
    group by player_key, season, week
  )
  where game_recency <= 4
  group by player_key
),

market_values as (
  -- KTC valuations
  select
    player_key,
    ktc_value,
    overall_rank as ktc_rank_overall,
    positional_rank as ktc_rank_at_position,
    ktc_value - LAG(ktc_value, 4) over (partition by player_key order by asof_date) as ktc_trend_4wk
  from {{ ref('fact_asset_market_values') }}
  where
    asset_type = 'player'
    and market_scope = 'dynasty_1qb'
  qualify ROW_NUMBER() over (partition by player_key order by asof_date desc) = 1
),

position_baselines as (
  -- Calculate replacement level (25th percentile at position)
  select
    position,
    PERCENTILE_CONT(0.25) within group (order by projected_ppg_ros) as replacement_ppg,
    MAX(projected_ppg_ros) as max_projected_ppg
  from projections p
  inner join fa_pool fa on p.mfl_id = fa.mfl_id
  group by position
)

select
  -- Identity
  fa.player_key,
  fa.player_name,
  fa.position,
  fa.nfl_team,
  fa.age,
  fa.nfl_experience,
  fa.injury_status,

  -- Recent Performance
  rs.fantasy_ppg_last_3,
  rs.fantasy_ppg_last_4,
  rs.fantasy_ppg_last_8,
  rs.fantasy_ppg_season,

  -- Real-World Volume
  rs.attempts_per_game_l4,
  rs.targets_per_game_l4,

  -- Efficiency
  rs.ypc,
  rs.ypr,
  rs.catch_rate,

  -- Opportunity (calculated from ff_opportunity attempt metrics)
  opp.target_share_l4,
  opp.rush_share_l4,
  opp.opportunity_share_l4,  -- Combined metric (target 60% + rush 40%)

  -- Projections
  proj.projected_ppg_ros,
  proj.projected_total_ros,
  proj.weeks_remaining,

  -- Market
  ktc.ktc_value,
  ktc.ktc_rank_overall,
  ktc.ktc_rank_at_position,
  ktc.ktc_trend_4wk,

  -- Value Composite (0-100 score)
  -- Weights: Projections 40%, Opportunity 25%, Efficiency 20%, Market 15%
  -- Note: Each component normalized to 0-1 scale before applying weight
  (
    -- Projections: Normalize by position max (0-1 scale)
    0.40 * COALESCE(proj.projected_ppg_ros / NULLIF(pb.max_projected_ppg, 0), 0)

    -- Opportunity: Normalize by capping at 25% team share (0-1 scale)
    -- A player getting 25%+ of team opportunities = full 25 points
    + 0.25 * LEAST(COALESCE(opp.opportunity_share_l4, 0) / 0.25, 1.0)

    -- Efficiency: Binary scoring based on thresholds (0-1 scale)
    + 0.20 * (case
      when rs.ypc > 4.5 then 1.0
      when rs.ypr > 11.0 then 1.0
      when rs.catch_rate > 0.70 then 0.8
      else 0.3
    end)

    -- Market: Invert rank so lower rank = higher score (0-1 scale)
    -- Top 20 at position = full 15 points, rank 100+ = 0 points
    + 0.15 * GREATEST(1.0 - (COALESCE(ktc.ktc_rank_at_position, 100) / 100.0), 0)
  ) * 100 as value_score,

  -- Points above replacement
  proj.projected_ppg_ros - pb.replacement_ppg as points_above_replacement,

  -- Breakout indicator (high opportunity share + trending performance + efficiency)
  COALESCE(
    opp.opportunity_share_l4 > 0.20  -- Getting 20%+ of team's opportunities
    and rs.fantasy_ppg_last_4 > COALESCE(rs.fantasy_ppg_last_8, 0)
    and (rs.ypc > 4.5 or rs.ypr > 10.0), FALSE
  ) as breakout_indicator,

  -- Regression risk (overperforming)
  COALESCE(rs.fantasy_ppg_last_4 > proj.projected_ppg_ros * 1.3, FALSE) as regression_risk_flag,

  -- Bid Recommendations (business logic)
  case
    when fa.position = 'RB' then ROUND(proj.projected_total_ros / 10, 0)  -- $1 per 10 projected points
    when fa.position = 'WR' then ROUND(proj.projected_total_ros / 12, 0)
    when fa.position = 'TE' then ROUND(proj.projected_total_ros / 15, 0)
    when fa.position = 'QB' then ROUND(proj.projected_total_ros / 20, 0)
    else 1
  end as suggested_bid_1yr,

  case
    when proj.projected_total_ros > 100 then ROUND(proj.projected_total_ros / 8, 0)  -- Discount for multi-year
  end as suggested_bid_2yr,

  -- Bid confidence (based on recent performance + opportunity + projections)
  case
    when
      rs.fantasy_ppg_last_4 is not NULL
      and opp.opportunity_share_l4 > 0.15  -- Getting 15%+ of team opportunities
      and proj.projected_ppg_ros > pb.replacement_ppg
      then 'HIGH'
    when proj.projected_ppg_ros > pb.replacement_ppg
      then 'MEDIUM'
    else 'LOW'
  end as bid_confidence,

  -- Priority ranking
  ROW_NUMBER() over (order by value_score desc) as priority_rank_overall,
  ROW_NUMBER() over (partition by fa.position order by value_score desc) as priority_rank_at_position,

  -- Metadata
  CURRENT_DATE as asof_date,
  (
    select MAX(week) from {{ ref('dim_schedule') }}
    where season = YEAR(CURRENT_DATE) and CAST(game_date as DATE) < CURRENT_DATE
  ) as current_week

from fa_pool fa
left join recent_stats rs on fa.player_key = rs.player_key
inner join projections proj on fa.mfl_id = proj.mfl_id  -- Only FAs with projections
left join opportunity opp using (player_key)
left join market_values ktc using (player_key)
left join position_baselines pb on fa.position = pb.position

where fa.position in ('QB', 'RB', 'WR', 'TE')  -- Focus on offensive skill positions for FASA
