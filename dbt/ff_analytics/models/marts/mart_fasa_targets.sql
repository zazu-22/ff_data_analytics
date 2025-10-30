-- Grain: player_id, asof_date
-- Purpose: Score every FA for FASA with bid recommendations
-- Enhanced with dynasty market intelligence (aging curves, market efficiency, sustainability, league VoR)

with fa_pool as (
  select
    dp.player_id,  -- Canonical sequential surrogate (ADR-011)
    fa.player_key,  -- Sleeper player ID (for reference)
    fa.mfl_id,
    fa.sleeper_player_id,
    fa.player_name,
    fa.position,
    fa.nfl_team,
    fa.age,
    fa.nfl_experience,
    fa.injury_status,
    fa.asof_date
  from {{ ref('stg_sleeper__fa_pool') }} fa
  left join {{ ref('dim_player') }} dp
    on
      fa.sleeper_player_id = CAST(dp.sleeper_id as VARCHAR)  -- Primary join
      or (fa.mfl_id = dp.mfl_id and fa.mfl_id is not null)  -- Backstop
  -- Dedup: prioritize sleeper_id matches over mfl_id matches
  qualify ROW_NUMBER() over (
    partition by fa.player_key
    order by
      case
        when fa.sleeper_player_id = CAST(dp.sleeper_id as VARCHAR) then 1
        else 2
      end
  ) = 1
),

recent_stats as (
  -- Aggregate recent performance from fantasy actuals
  select
    player_id,

    -- Last 3/4/8 games
    AVG(case when game_recency <= 3 then fantasy_points end) as fantasy_ppg_last_3,
    AVG(case when game_recency <= 4 then fantasy_points end) as fantasy_ppg_last_4,
    AVG(case when game_recency <= 8 then fantasy_points end) as fantasy_ppg_last_8,
    AVG(fantasy_points) as fantasy_ppg_season,

    -- Real-world volume (last 4 weeks)
    AVG(case when game_recency <= 4 then attempts end) as attempts_per_game_l4,
    AVG(case when game_recency <= 4 then targets end) as targets_per_game_l4,

    -- Season totals for sustainability analysis
    SUM(rushing_tds + receiving_tds + passing_tds) as touchdowns_season,
    SUM(targets) as targets_season,

    -- Efficiency
    SUM(rushing_yards) / NULLIF(SUM(carries), 0) as ypc,
    SUM(receiving_yards) / NULLIF(SUM(receptions), 0) as ypr,
    SUM(receptions) / NULLIF(SUM(targets), 0) as catch_rate

  from (
    select
      player_id,
      fantasy_points,
      attempts,
      targets,
      carries,
      COALESCE(rushing_tds, 0) as rushing_tds,
      COALESCE(receiving_tds, 0) as receiving_tds,
      COALESCE(passing_tds, 0) as passing_tds,
      rushing_yards,
      receiving_yards,
      receptions,
      ROW_NUMBER() over (partition by player_id order by season desc, week desc) as game_recency
    from {{ ref('mart_fantasy_actuals_weekly') }}
    where
      season = YEAR(CURRENT_DATE)
      and week
      <= (
        select MAX(week) from {{ ref('dim_schedule') }}
        where season = YEAR(CURRENT_DATE) and CAST(game_date as DATE) < CURRENT_DATE
      )
  )
  group by player_id
),

projections as (
  -- Rest of season projections (player_id is already canonical in mart layer)
  select
    proj.player_id,  -- Already canonical player_id (ADR-011)
    SUM(proj.projected_fantasy_points) as projected_total_ros,
    AVG(proj.projected_fantasy_points) as projected_ppg_ros,
    COUNT(*) as weeks_remaining
  from {{ ref('mart_fantasy_projections') }} proj
  where
    proj.season = YEAR(CURRENT_DATE)
    and proj.week
    > (
      select MAX(week) from {{ ref('dim_schedule') }}
      where season = YEAR(CURRENT_DATE) and CAST(game_date as DATE) < CURRENT_DATE
    )
    and proj.horizon = 'weekly'
  group by proj.player_id
),

opportunity as (
  -- Calculate opportunity shares from ff_opportunity attempt metrics
  -- rec_attempt / rec_attempt_team = target share
  -- rush_attempt / rush_attempt_team = rush share
  select
    player_id,
    AVG(case when game_recency <= 4 then target_share end) as target_share_l4,
    AVG(case when game_recency <= 4 then rush_share end) as rush_share_l4,
    -- Combined opportunity share (weighted average for RB/WR/TE)
    AVG(case
      when game_recency <= 4 then
        COALESCE(target_share, 0) * 0.6 + COALESCE(rush_share, 0) * 0.4
    end) as opportunity_share_l4
  from (
    select
      player_id,
      season,
      week,
      -- Calculate target share (receiving opportunity)
      MAX(case when stat_name = 'rec_attempt' then stat_value end)
      / NULLIF(MAX(case when stat_name = 'rec_attempt_team' then stat_value end), 0) as target_share,
      -- Calculate rush share (rushing opportunity)
      MAX(case when stat_name = 'rush_attempt' then stat_value end)
      / NULLIF(MAX(case when stat_name = 'rush_attempt_team' then stat_value end), 0) as rush_share,
      ROW_NUMBER() over (partition by player_id order by season desc, week desc) as game_recency
    from {{ ref('fact_player_stats') }}
    where
      stat_kind = 'actual'
      and measure_domain = 'real_world'
      and season = YEAR(CURRENT_DATE)
      and stat_name in ('rec_attempt', 'rec_attempt_team', 'rush_attempt', 'rush_attempt_team')
    group by player_id, season, week
  )
  where game_recency <= 4
  group by player_id
),

market_values as (
  -- KTC valuations
  select
    player_id,
    ktc_value,
    overall_rank as ktc_rank_overall,
    positional_rank as ktc_rank_at_position,
    ktc_value - LAG(ktc_value, 4) over (partition by player_id order by asof_date) as ktc_trend_4wk
  from {{ ref('fact_asset_market_values') }}
  where
    asset_type = 'player'
    and market_scope = 'dynasty_1qb'
  qualify ROW_NUMBER() over (partition by player_id order by asof_date desc) = 1
),

position_baselines as (
  -- Calculate replacement level (25th percentile at position)
  select
    position,
    PERCENTILE_CONT(0.25) within group (order by projected_ppg_ros) as replacement_ppg,
    MAX(projected_ppg_ros) as max_projected_ppg
  from projections p
  inner join fa_pool fa on p.player_id = fa.player_id
  group by position
),

-- ============================================================================
-- PHASE 1: AGING CURVE ADJUSTMENTS & DYNASTY VALUATION
-- ============================================================================

aging_context as (
  select
    fa.player_id,
    fa.position,
    dp.birthdate,
    YEAR(CURRENT_DATE) - YEAR(dp.birthdate) as age_at_snapshot,

    -- Position-specific peak windows (from research)
    case fa.position
      when 'RB' then 23
      when 'WR' then 26
      when 'QB' then 28
      when 'TE' then 25
    end as position_peak_age_min,

    case fa.position
      when 'RB' then 26
      when 'WR' then 30
      when 'QB' then 33
      when 'TE' then 27
    end as position_peak_age_max,

    -- Position-specific annual decline rates
    case fa.position
      when 'RB' then 0.175  -- 17.5% average (research: 15-20%)
      when 'WR' then 0.100  -- 10% average (research: 8-12%)
      when 'QB' then 0.065  -- 6.5% average (research: 5-8%)
      when 'TE' then 0.125  -- 12.5% average (research: 10-15%)
    end as dynasty_discount_rate

  from fa_pool fa
  left join {{ ref('dim_player') }} dp on fa.player_id = dp.player_id
),

dynasty_valuation as (
  select
    ac.player_id,
    ac.age_at_snapshot,
    ac.position_peak_age_min,
    ac.position_peak_age_max,
    ac.dynasty_discount_rate,

    -- Peak window flag
    ac.age_at_snapshot between ac.position_peak_age_min and ac.position_peak_age_max
      as age_peak_window_flag,

    -- Years to/from peak
    case
      when ac.age_at_snapshot < ac.position_peak_age_min
        then ac.position_peak_age_min - ac.age_at_snapshot
      when ac.age_at_snapshot > ac.position_peak_age_max
        then ac.position_peak_age_max - ac.age_at_snapshot  -- Negative
      else 0  -- In peak window
    end as years_to_peak,

    -- Age decline risk (0.0 = no risk, 1.0 = extreme risk)
    case
      when ac.age_at_snapshot <= ac.position_peak_age_max then 0.0
      when ac.age_at_snapshot = ac.position_peak_age_max + 1 then 0.25
      when ac.age_at_snapshot = ac.position_peak_age_max + 2 then 0.50
      when ac.age_at_snapshot = ac.position_peak_age_max + 3 then 0.75
      else 1.0  -- 4+ years past peak
    end as age_decline_risk_score,

    -- 3-year dynasty value (discounted cash flow model)
    proj.projected_ppg_ros * proj.weeks_remaining as projected_points_year1,

    -- Year 2: Apply aging curve decline
    (proj.projected_ppg_ros * 17 * (1 - ac.dynasty_discount_rate))
      as projected_points_year2,

    -- Year 3: Compound aging decline
    (proj.projected_ppg_ros * 17 * POWER(1 - ac.dynasty_discount_rate, 2))
      as projected_points_year3,

    -- Sum to get 3-year dynasty value
    (proj.projected_ppg_ros * proj.weeks_remaining)
    + (proj.projected_ppg_ros * 17 * (1 - ac.dynasty_discount_rate))
    + (proj.projected_ppg_ros * 17 * POWER(1 - ac.dynasty_discount_rate, 2))
      as dynasty_3yr_value

  from aging_context ac
  left join projections proj on ac.player_id = proj.player_id
),

-- ============================================================================
-- PHASE 2: MARKET EFFICIENCY SCORING
-- ============================================================================

market_context as (
  select
    fa.player_id,

    -- Model value (our internal valuation)
    dv.dynasty_3yr_value as model_value,

    -- Market value (KTC consensus)
    mv.ktc_value as market_value,

    -- Value gap percentage
    case
      when mv.ktc_value > 0
        then
          ((dv.dynasty_3yr_value - mv.ktc_value) / mv.ktc_value * 100)
    end as value_gap_pct

  from fa_pool fa
  left join dynasty_valuation dv on fa.player_id = dv.player_id
  left join market_values mv on fa.player_id = mv.player_id
),

market_signals as (
  select
    mc.player_id,
    mc.model_value,
    mc.market_value,
    mc.value_gap_pct,

    -- Market efficiency signal
    case
      when mc.value_gap_pct > 25 then 'STRONG_BUY'
      when mc.value_gap_pct between 10 and 25 then 'BUY'
      when mc.value_gap_pct between -10 and 10 then 'HOLD'
      when mc.value_gap_pct between -25 and -10 then 'SELL'
      when mc.value_gap_pct < -25 then 'STRONG_SELL'
      else 'UNKNOWN'
    end as market_efficiency_signal,

    -- Inefficiency flag (actionable arbitrage)
    ABS(mc.value_gap_pct) > 25 as market_inefficiency_flag

  from market_context mc
),

-- ============================================================================
-- PHASE 3: SUSTAINABILITY ANALYSIS
-- ============================================================================

sustainability as (
  select
    fa.player_id,
    fa.position,

    -- Calculate expected TDs based on opportunity
    -- Formula: (Target_Share × Team_Pass_TDs × 0.8) + (Rush_Share × Team_Rush_TDs)
    case fa.position
      when 'WR'
        then
          (opp.target_share_l4 * 35 * 0.8)  -- Assume 35 pass TDs/team/year
      when 'RB'
        then
          (opp.target_share_l4 * 35 * 0.8 * 0.5)  -- RBs get fewer passing TDs
          + (opp.rush_share_l4 * 15)  -- Assume 15 rush TDs/team/year
      when 'TE'
        then
          (opp.target_share_l4 * 35 * 0.8 * 0.6)  -- TEs get moderate passing TDs
    end as expected_tds_season,

    -- Actual TDs (from stats)
    rs.touchdowns_season as actual_tds_season,

    -- TDOE calculation
    rs.touchdowns_season - expected_tds_season as tdoe,

    -- Regression risk flag
    ABS(rs.touchdowns_season - expected_tds_season) >= 3.0
      as td_regression_risk_flag,

    -- Regression direction
    case
      when (rs.touchdowns_season - expected_tds_season) >= 3.0 then 'POSITIVE'
      when (rs.touchdowns_season - expected_tds_season) <= -3.0 then 'NEGATIVE'
      else 'NEUTRAL'
    end as td_regression_direction,

    -- Opportunity metrics (already in CTE, reference here)
    opp.target_share_l4 * 100 as target_share_pct,
    opp.opportunity_share_l4 * 100 as opportunity_share_pct,

    -- TD rate (fluky metric)
    case
      when rs.targets_season > 0
        then
          (rs.touchdowns_season / rs.targets_season * 100)
    end as td_rate_pct,

    -- Sustainability score (high opportunity + average efficiency = sustainable)
    case
      when
        opp.target_share_l4 > 0.22  -- High target share (sticky)
        and (rs.touchdowns_season / NULLIF(rs.targets_season, 0)) between 0.08 and 0.12  -- Normal TD rate
        then 0.90  -- Very sustainable
      when
        opp.target_share_l4 > 0.18
        and (rs.touchdowns_season / NULLIF(rs.targets_season, 0)) between 0.08 and 0.14
        then 0.70  -- Sustainable
      when
        opp.target_share_l4 < 0.15
        or (rs.touchdowns_season / NULLIF(rs.targets_season, 0)) > 0.16  -- High TD rate (fluky)
        then 0.30  -- Unsustainable
      else 0.50  -- Average
    end as sustainability_score

  from fa_pool fa
  left join opportunity opp on fa.player_id = opp.player_id
  left join recent_stats rs on fa.player_id = rs.player_id
),

-- ============================================================================
-- PHASE 4: LEAGUE CONTEXT & VoR
-- ============================================================================

league_context as (
  -- Use pre-calculated replacement levels from league roster depth mart
  -- Aggregate to single row to avoid Cartesian product
  select
    MAX(case when lrd.position = 'RB' then lrd.replacement_level_ppg end) as rb_replacement_ppg,
    MAX(case when lrd.position = 'WR' then lrd.replacement_level_ppg end) as wr_replacement_ppg,
    MAX(case when lrd.position = 'TE' then lrd.replacement_level_ppg end) as te_replacement_ppg,
    MAX(case when lrd.position = 'RB' then lrd.median_starter_ppg end) as rb_median_starter_ppg,
    MAX(case when lrd.position = 'WR' then lrd.median_starter_ppg end) as wr_median_starter_ppg,
    MAX(case when lrd.position = 'RB' then lrd.total_rostered_at_position end) as rb_total_rostered,
    MAX(case when lrd.position = 'WR' then lrd.total_rostered_at_position end) as wr_total_rostered,
    MAX(case when lrd.position = 'TE' then lrd.total_rostered_at_position end) as te_total_rostered
  from {{ ref('mart_league_roster_depth') }} lrd
),

league_vor_base as (
  select
    fa.player_id,
    fa.position,
    proj.projected_ppg_ros,

    -- League replacement level
    case fa.position
      when 'RB' then lc.rb_replacement_ppg
      when 'WR' then lc.wr_replacement_ppg
      when 'TE' then lc.te_replacement_ppg
    end as league_replacement_level_ppg,

    -- League median starter
    case fa.position
      when 'RB' then lc.rb_median_starter_ppg
      when 'WR' then lc.wr_median_starter_ppg
    end as league_median_starter_ppg,

    -- True VoR (vs league replacement)
    proj.projected_ppg_ros
    - case fa.position
      when 'RB' then lc.rb_replacement_ppg
      when 'WR' then lc.wr_replacement_ppg
      when 'TE' then lc.te_replacement_ppg
    end as pts_above_league_replacement,

    -- Vs median starter
    proj.projected_ppg_ros
    - case fa.position
      when 'RB' then lc.rb_median_starter_ppg
      when 'WR' then lc.wr_median_starter_ppg
    end as pts_vs_median_starter,

    -- Hypothetical league rank (if rostered)
    (
      select COUNT(*) + 1
      from {{ ref('mart_league_roster_depth') }} lrd2
      where
        lrd2.position = fa.position
        and lrd2.projected_ppg_ros > proj.projected_ppg_ros
    ) as hypothetical_league_rank,

    -- Total rostered for context
    case fa.position
      when 'RB' then lc.rb_total_rostered
      when 'WR' then lc.wr_total_rostered
      when 'TE' then lc.te_total_rostered
    end as total_league_rostered_at_pos

  from fa_pool fa
  left join projections proj on fa.player_id = proj.player_id
  cross join league_context lc
),

league_vor as (
  select
    *,
    -- Percentile (calculated after hypothetical_league_rank is materialized)
    (1 - (CAST(hypothetical_league_rank as DECIMAL) / NULLIF(total_league_rostered_at_pos, 0))) * 100
      as hypothetical_percentile
  from league_vor_base
),

-- ============================================================================
-- PHASE 5: ENHANCED VALUE SCORE & BID RECOMMENDATIONS
-- ============================================================================

enhanced_value_score as (
  select
    fa.player_id,

    -- Weighted composite (0-100 scale)
    LEAST(100, GREATEST(
      0,
      -- Dynasty value (25% weight)
      (COALESCE(dv.dynasty_3yr_value, 0) / 500 * 25)

      -- Aging curve context (20% weight)
      + case
        when dv.age_peak_window_flag then 20
        when dv.age_decline_risk_score > 0.5 then 20 * (1 - dv.age_decline_risk_score)
        else 20 * 0.5
      end

      -- Market inefficiency (20% weight)
      + case ms.market_efficiency_signal
        when 'STRONG_BUY' then 20
        when 'BUY' then 15
        when 'HOLD' then 10
        when 'SELL' then 5
        when 'STRONG_SELL' then 0
        else 10
      end

      -- Sustainability (15% weight)
      + (COALESCE(sus.sustainability_score, 0.5) * 15)

      -- League VoR (10% weight)
      + case
        when lv.pts_above_league_replacement > 5 then 10
        when lv.pts_above_league_replacement > 2 then 7
        when lv.pts_above_league_replacement > 0 then 4
        else 0
      end

      -- Recent performance (10% weight)
      + case
        when rs.fantasy_ppg_last_4 > 12 then 10
        when rs.fantasy_ppg_last_4 > 8 then 7
        when rs.fantasy_ppg_last_4 > 5 then 4
        else 0
      end
    )) as enhanced_value_score_v2,

    -- Bid confidence
    case
      when
        ms.market_efficiency_signal in ('STRONG_BUY', 'BUY')
        and COALESCE(sus.sustainability_score, 0) > 0.6
        and dv.age_peak_window_flag
        and lv.pts_above_league_replacement > 2
        then 'VERY_HIGH'
      when
        ms.market_efficiency_signal in ('STRONG_BUY', 'BUY')
        and COALESCE(sus.sustainability_score, 0) > 0.5
        then 'HIGH'
      when
        ms.market_efficiency_signal = 'HOLD'
        and COALESCE(sus.sustainability_score, 0) > 0.4
        then 'MEDIUM'
      else 'LOW'
    end as bid_confidence_v3

  from fa_pool fa
  left join dynasty_valuation dv on fa.player_id = dv.player_id
  left join market_signals ms on fa.player_id = ms.player_id
  left join sustainability sus on fa.player_id = sus.player_id
  left join league_vor lv on fa.player_id = lv.player_id
  left join recent_stats rs on fa.player_id = rs.player_id
),

market_adjusted_bids as (
  select
    fa.player_id,

    -- Dynasty bid (3-year value / 50 = years to amortize)
    ROUND(COALESCE(dv.dynasty_3yr_value, 0) / 50, 0) as suggested_bid_dynasty_3yr,

    -- Market efficiency adjustment
    case ms.market_efficiency_signal
      when 'STRONG_BUY' then ROUND(COALESCE(dv.dynasty_3yr_value, 0) / 50 * 1.3, 0)  -- Bid 30% more
      when 'BUY' then ROUND(COALESCE(dv.dynasty_3yr_value, 0) / 50 * 1.1, 0)  -- Bid 10% more
      when 'HOLD' then ROUND(COALESCE(dv.dynasty_3yr_value, 0) / 50, 0)
      when 'SELL' then ROUND(COALESCE(dv.dynasty_3yr_value, 0) / 50 * 0.8, 0)  -- Bid 20% less
      when 'STRONG_SELL' then 1  -- Minimum bid only
      else ROUND(COALESCE(dv.dynasty_3yr_value, 0) / 50, 0)
    end as suggested_bid_market_adjusted,

    -- Competitive window adjustment (assume contending for now)
    case
      when dv.age_peak_window_flag then ROUND(COALESCE(dv.dynasty_3yr_value, 0) / 50 * 1.2, 0)
      when dv.age_decline_risk_score > 0.5 then ROUND(COALESCE(dv.dynasty_3yr_value, 0) / 50 * 0.7, 0)
      else ROUND(COALESCE(dv.dynasty_3yr_value, 0) / 50, 0)
    end as suggested_bid_contender,

    -- Rebuilder adjustment (defer aging players)
    case
      when dv.age_at_snapshot < 25 then ROUND(COALESCE(dv.dynasty_3yr_value, 0) / 50 * 1.3, 0)  -- Youth premium
      when dv.age_at_snapshot > 27 then ROUND(COALESCE(dv.dynasty_3yr_value, 0) / 50 * 0.5, 0)  -- Age discount
      else ROUND(COALESCE(dv.dynasty_3yr_value, 0) / 50, 0)
    end as suggested_bid_rebuilder

  from fa_pool fa
  left join dynasty_valuation dv on fa.player_id = dv.player_id
  left join market_signals ms on fa.player_id = ms.player_id
)

select
  -- Identity
  fa.player_id,  -- Canonical sequential surrogate (ADR-011)
  fa.player_key,  -- Sleeper ID for reference
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

  -- Market (original KTC)
  ktc.ktc_value,
  ktc.ktc_rank_overall,
  ktc.ktc_rank_at_position,
  ktc.ktc_trend_4wk,

  -- ========================================================================
  -- PHASE 1: AGING CURVE & DYNASTY VALUATION
  -- ========================================================================

  dv.age_at_snapshot,
  dv.position_peak_age_min,
  dv.position_peak_age_max,
  dv.age_peak_window_flag,
  dv.years_to_peak,
  dv.age_decline_risk_score,
  dv.projected_points_year1,
  dv.projected_points_year2,
  dv.projected_points_year3,
  dv.dynasty_3yr_value,
  dv.dynasty_discount_rate,

  -- ========================================================================
  -- PHASE 2: MARKET EFFICIENCY
  -- ========================================================================

  ms.model_value,
  ms.market_value,
  ms.value_gap_pct,
  ms.market_efficiency_signal,
  ms.market_inefficiency_flag,

  -- ========================================================================
  -- PHASE 3: SUSTAINABILITY ANALYSIS
  -- ========================================================================

  sus.expected_tds_season,
  sus.actual_tds_season,
  sus.tdoe,
  sus.td_regression_risk_flag,
  sus.td_regression_direction,
  sus.target_share_pct,
  sus.opportunity_share_pct,
  sus.td_rate_pct,
  sus.sustainability_score,

  -- ========================================================================
  -- PHASE 4: LEAGUE CONTEXT & VoR
  -- ========================================================================

  lv.league_replacement_level_ppg,
  lv.league_median_starter_ppg,
  lv.pts_above_league_replacement,
  lv.pts_vs_median_starter,
  lv.hypothetical_league_rank,
  lv.total_league_rostered_at_pos,
  lv.hypothetical_percentile,

  -- ========================================================================
  -- PHASE 5: ENHANCED SCORING & BIDS
  -- ========================================================================

  evs.enhanced_value_score_v2,
  evs.bid_confidence_v3,

  mab.suggested_bid_dynasty_3yr,
  mab.suggested_bid_market_adjusted,
  mab.suggested_bid_contender,
  mab.suggested_bid_rebuilder,

  -- ========================================================================
  -- LEGACY FIELDS (preserved for compatibility)
  -- ========================================================================

  -- Value Composite (0-100 score) - ORIGINAL
  -- Weights: Projections 40%, Opportunity 25%, Efficiency 20%, Market 15%
  (
    0.40 * COALESCE(proj.projected_ppg_ros / NULLIF(pb.max_projected_ppg, 0), 0)
    + 0.25 * LEAST(COALESCE(opp.opportunity_share_l4, 0) / 0.25, 1.0)
    + 0.20 * (case
      when rs.ypc > 4.5 then 1.0
      when rs.ypr > 11.0 then 1.0
      when rs.catch_rate > 0.70 then 0.8
      else 0.3
    end)
    + 0.15 * GREATEST(1.0 - (COALESCE(ktc.ktc_rank_at_position, 100) / 100.0), 0)
  ) * 100 as value_score,

  -- Points above replacement (original FA pool baseline)
  proj.projected_ppg_ros - pb.replacement_ppg as points_above_replacement,

  -- Breakout indicator (high opportunity share + trending performance + efficiency)
  COALESCE(
    opp.opportunity_share_l4 > 0.20
    and rs.fantasy_ppg_last_4 > COALESCE(rs.fantasy_ppg_last_8, 0)
    and (rs.ypc > 4.5 or rs.ypr > 10.0), false
  ) as breakout_indicator,

  -- Regression risk (overperforming)
  COALESCE(rs.fantasy_ppg_last_4 > proj.projected_ppg_ros * 1.3, false) as regression_risk_flag,

  -- Bid Recommendations (original 1-year business logic)
  case
    when fa.position = 'RB' then ROUND(proj.projected_total_ros / 10, 0)
    when fa.position = 'WR' then ROUND(proj.projected_total_ros / 12, 0)
    when fa.position = 'TE' then ROUND(proj.projected_total_ros / 15, 0)
    when fa.position = 'QB' then ROUND(proj.projected_total_ros / 20, 0)
    else 1
  end as suggested_bid_1yr,

  case
    when proj.projected_total_ros > 100 then ROUND(proj.projected_total_ros / 8, 0)
  end as suggested_bid_2yr,

  -- Bid confidence (original logic)
  case
    when
      rs.fantasy_ppg_last_4 is not null
      and opp.opportunity_share_l4 > 0.15
      and proj.projected_ppg_ros > pb.replacement_ppg
      then 'HIGH'
    when proj.projected_ppg_ros > pb.replacement_ppg
      then 'MEDIUM'
    else 'LOW'
  end as bid_confidence,

  -- Priority ranking (using enhanced value score)
  ROW_NUMBER() over (order by evs.enhanced_value_score_v2 desc) as priority_rank_overall,
  ROW_NUMBER() over (partition by fa.position order by evs.enhanced_value_score_v2 desc) as priority_rank_at_position,

  -- Metadata
  CURRENT_DATE as asof_date,
  (
    select MAX(week) from {{ ref('dim_schedule') }}
    where season = YEAR(CURRENT_DATE) and CAST(game_date as DATE) < CURRENT_DATE
  ) as current_week

from fa_pool fa
left join recent_stats rs on fa.player_id = rs.player_id
inner join projections proj on fa.player_id = proj.player_id  -- Only FAs with projections
left join opportunity opp on fa.player_id = opp.player_id
left join market_values ktc on fa.player_id = ktc.player_id
left join position_baselines pb on fa.position = pb.position
left join dynasty_valuation dv on fa.player_id = dv.player_id
left join market_signals ms on fa.player_id = ms.player_id
left join sustainability sus on fa.player_id = sus.player_id
left join league_vor lv on fa.player_id = lv.player_id
left join enhanced_value_score evs on fa.player_id = evs.player_id
left join market_adjusted_bids mab on fa.player_id = mab.player_id

where fa.position in ('QB', 'RB', 'WR', 'TE')  -- Focus on offensive skill positions for FASA
