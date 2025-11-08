# Task 2.6: Enhance FASA Targets with Market Intelligence

**Sprint:** Sprint 1 (Post-FASA Enhancement)
**Phase:** Phase 2 Extension
**Estimated Duration:** 8-12 hours
**Priority:** HIGH (transforms FASA into dynasty intelligence tool)

______________________________________________________________________

## Objective

Transform `mart_fasa_targets` from tactical FAAB tool into comprehensive dynasty market intelligence platform by integrating:

1. **Dynasty Valuation** - Multi-year value with position-specific aging curves
2. **Market Efficiency Scoring** - Model vs. market pricing gaps (buy/sell signals)
3. **Sustainability Analysis** - Distinguish signal from noise (sticky vs. fluky metrics)
4. **Strategic Fit** - Competitive window alignment for roster construction
5. **League Context** - True VoR vs. rostered players, hypothetical rankings

**Research Foundation:** All enhancements based on comprehensive research compiled in `docs/analytics_references/fasa_targets_research.md` (25,000 words, 50+ citations from industry experts).

______________________________________________________________________

## Context

### Current State (Task 1.3 Baseline)

**Strengths:**

- ✅ Recent performance tracking (L3/L4/L8 games)
- ✅ Rest-of-season projections
- ✅ Opportunity metrics (target share, rush share)
- ✅ Basic bid heuristics (`projected_total_ros / 10`)
- ✅ Value score composite (0-100)

**Limitations:**

- ❌ No aging curve adjustments (treats 24yo RB = 28yo RB)
- ❌ No market efficiency signals (can't identify undervalued targets)
- ❌ No sustainability analysis (can't detect TD regression candidates)
- ❌ No dynasty timeline context (1-year ROS focus only)
- ❌ Replacement level = FA pool 25th %ile (not true league VoR)

### Enhanced State (Post-Task 2.6)

**Dynasty Intelligence:**

- ✅ 3-year discounted value with position-specific aging curves
- ✅ Model vs. market gap % (identify 25%+ inefficiencies)
- ✅ TDOE regression flags (86% of +3.0 TDOE decline next year)
- ✅ Opportunity > efficiency scoring (sticky metrics prioritized)
- ✅ Peak window flags (RB 23-26, WR 26-30, etc.)
- ✅ True league VoR (vs. median rostered player, not just FAs)
- ✅ Competitive window fit scores (contender vs. rebuilder lens)

______________________________________________________________________

## Dependencies

### Completed Tasks

- ✅ Task 1.3: `mart_fasa_targets` baseline exists
- ✅ Task 2.4: `mart_fa_acquisition_history` (market context)
- ✅ Task 2.5: `mart_league_roster_depth` (league VoR)

### Research Documentation

- ✅ `docs/analytics_references/fasa_targets_research.md` - Comprehensive strategy frameworks
- ✅ `docs/analytics_references/player_valuation_frameworks.md` - VoR, VBD, WAR formulas
- ✅ `docs/analytics_references/player_aging_curves_positional_value_research.md` - Position-specific aging
- ✅ `docs/analytics_references/dynasty_trade_value_methodologies.md` - Market pricing
- ✅ `docs/analytics_references/dynasty_strategy_frameworks_2025.md` - Strategic frameworks

### Data Sources Required

- `mart_fantasy_projections` - Multi-year projections (if available, else use decay model)
- `fact_asset_market_values` - KTC values (model vs. market)
- `fact_player_stats` - Calculate TDOE, TPRR, YPRR, WOPR
- `mart_league_roster_depth` - True replacement level
- `dim_player` - Age data (birth_date)

______________________________________________________________________

## Implementation Approach

### Phase 1: Aging Curve Adjustments (High Impact, Low Effort)

**New columns to add:**

```sql
-- Aging curve context
, age_at_snapshot INTEGER  -- Current age
, position_peak_age_min INTEGER  -- Position-specific (RB:23, WR:26, QB:28, TE:25)
, position_peak_age_max INTEGER  -- Position-specific (RB:26, WR:30, QB:33, TE:27)
, age_peak_window_flag BOOLEAN  -- Within peak age range
, years_to_peak INTEGER  -- Negative if past peak
, age_decline_risk_score DECIMAL(4,2)  -- 0.0-1.0, higher = more risk

-- Dynasty multi-year value (3-year discounted)
, projected_points_year1 DECIMAL(6,2)  -- Current ROS projection
, projected_points_year2 DECIMAL(6,2)  -- Year 2 (discounted by aging curve)
, projected_points_year3 DECIMAL(6,2)  -- Year 3 (discounted by aging curve)
, dynasty_3yr_value DECIMAL(8,2)  -- Sum of discounted future points
, dynasty_discount_rate DECIMAL(4,3)  -- Position-specific (RB:0.15, WR:0.10, QB:0.07)
```

**Aging curve parameters (from research):**

| Position | Peak Ages | Decline Rate/Year | Sell Before | Avoid After |
| -------- | --------- | ----------------- | ----------- | ----------- |
| **RB**   | 23-26     | 15-20%            | Age 27      | Age 28      |
| **WR**   | 26-30     | 8-12%             | Age 30      | Age 33      |
| **QB**   | 28-33     | 5-8%              | Age 35      | Age 37      |
| **TE**   | 25-27     | 10-15%            | Age 30      | Age 32      |

**Implementation (SQL CTE):**

```sql
-- Add after opportunity CTE in mart_fasa_targets.sql

aging_context AS (
  SELECT
    fa.player_key,
    dp.birth_date,
    YEAR(CURRENT_DATE) - YEAR(dp.birth_date) AS age_at_snapshot,

    -- Position-specific peak windows (from research)
    CASE fa.position
      WHEN 'RB' THEN 23
      WHEN 'WR' THEN 26
      WHEN 'QB' THEN 28
      WHEN 'TE' THEN 25
    END AS position_peak_age_min,

    CASE fa.position
      WHEN 'RB' THEN 26
      WHEN 'WR' THEN 30
      WHEN 'QB' THEN 33
      WHEN 'TE' THEN 27
    END AS position_peak_age_max,

    -- Position-specific annual decline rates
    CASE fa.position
      WHEN 'RB' THEN 0.175  -- 17.5% average (research: 15-20%)
      WHEN 'WR' THEN 0.100  -- 10% average (research: 8-12%)
      WHEN 'QB' THEN 0.065  -- 6.5% average (research: 5-8%)
      WHEN 'TE' THEN 0.125  -- 12.5% average (research: 10-15%)
    END AS dynasty_discount_rate

  FROM fa_pool fa
  LEFT JOIN {{ ref('dim_player') }} dp ON fa.player_key = dp.player_key
),

dynasty_valuation AS (
  SELECT
    ac.player_key,
    ac.age_at_snapshot,
    ac.position_peak_age_min,
    ac.position_peak_age_max,
    ac.dynasty_discount_rate,

    -- Peak window flag
    ac.age_at_snapshot BETWEEN ac.position_peak_age_min AND ac.position_peak_age_max
      AS age_peak_window_flag,

    -- Years to/from peak
    CASE
      WHEN ac.age_at_snapshot < ac.position_peak_age_min
        THEN ac.position_peak_age_min - ac.age_at_snapshot
      WHEN ac.age_at_snapshot > ac.position_peak_age_max
        THEN ac.position_peak_age_max - ac.age_at_snapshot  -- Negative
      ELSE 0  -- In peak window
    END AS years_to_peak,

    -- Age decline risk (0.0 = no risk, 1.0 = extreme risk)
    CASE
      WHEN ac.age_at_snapshot <= ac.position_peak_age_max THEN 0.0
      WHEN ac.age_at_snapshot = ac.position_peak_age_max + 1 THEN 0.25
      WHEN ac.age_at_snapshot = ac.position_peak_age_max + 2 THEN 0.50
      WHEN ac.age_at_snapshot = ac.position_peak_age_max + 3 THEN 0.75
      ELSE 1.0  -- 4+ years past peak
    END AS age_decline_risk_score,

    -- 3-year dynasty value (discounted cash flow model)
    proj.projected_ppg_ros * proj.weeks_remaining AS projected_points_year1,

    -- Year 2: Apply aging curve decline
    (proj.projected_ppg_ros * 17 * (1 - ac.dynasty_discount_rate))
      AS projected_points_year2,

    -- Year 3: Compound aging decline
    (proj.projected_ppg_ros * 17 * POWER(1 - ac.dynasty_discount_rate, 2))
      AS projected_points_year3,

    -- Sum to get 3-year dynasty value
    (proj.projected_ppg_ros * proj.weeks_remaining) +
    (proj.projected_ppg_ros * 17 * (1 - ac.dynasty_discount_rate)) +
    (proj.projected_ppg_ros * 17 * POWER(1 - ac.dynasty_discount_rate, 2))
      AS dynasty_3yr_value

  FROM aging_context ac
  LEFT JOIN projections proj ON ac.player_key = proj.player_key
)
```

______________________________________________________________________

### Phase 2: Market Efficiency Scoring (High Impact, Medium Effort)

**New columns to add:**

```sql
-- Market intelligence
, model_value DECIMAL(8,2)  -- Our dynasty_3yr_value (internal model)
, market_value DECIMAL(8,2)  -- KTC consensus (external market)
, value_gap_pct DECIMAL(6,2)  -- (model - market) / market * 100
, market_efficiency_signal VARCHAR(12)  -- 'STRONG_BUY', 'BUY', 'HOLD', 'SELL', 'STRONG_SELL'
, market_inefficiency_flag BOOLEAN  -- |gap| > 25% (actionable arbitrage)
```

**Trading signals (from research):**

| Value Gap    | Signal      | Action                  | Rationale                        |
| ------------ | ----------- | ----------------------- | -------------------------------- |
| > +25%       | STRONG_BUY  | Acquire aggressively    | Market significantly undervalues |
| +10% to +25% | BUY         | Target in trades        | Modest market inefficiency       |
| -10% to +10% | HOLD        | Fair value              | Efficient pricing                |
| -10% to -25% | SELL        | Liquidate to contenders | Market overvalues                |
| < -25%       | STRONG_SELL | Dump immediately        | Extreme overvaluation            |

**Implementation (SQL CTE):**

```sql
market_context AS (
  SELECT
    fa.player_key,

    -- Model value (our internal valuation)
    dv.dynasty_3yr_value AS model_value,

    -- Market value (KTC or ADP consensus)
    -- NOTE: KTC values are 0-10,000 scale, normalize to points if needed
    mv.asset_value AS market_value,

    -- Value gap percentage
    CASE
      WHEN mv.asset_value > 0 THEN
        ((dv.dynasty_3yr_value - mv.asset_value) / mv.asset_value * 100)
      ELSE NULL
    END AS value_gap_pct

  FROM fa_pool fa
  LEFT JOIN dynasty_valuation dv ON fa.player_key = dv.player_key
  LEFT JOIN (
    -- Get most recent KTC value
    SELECT player_key, asset_value
    FROM {{ ref('fact_asset_market_values') }}
    WHERE provider = 'ktc'
      AND asset_value_date = (SELECT MAX(asset_value_date)
                              FROM {{ ref('fact_asset_market_values') }})
  ) mv ON fa.player_key = mv.player_key
),

market_signals AS (
  SELECT
    mc.player_key,
    mc.model_value,
    mc.market_value,
    mc.value_gap_pct,

    -- Market efficiency signal
    CASE
      WHEN mc.value_gap_pct > 25 THEN 'STRONG_BUY'
      WHEN mc.value_gap_pct BETWEEN 10 AND 25 THEN 'BUY'
      WHEN mc.value_gap_pct BETWEEN -10 AND 10 THEN 'HOLD'
      WHEN mc.value_gap_pct BETWEEN -25 AND -10 THEN 'SELL'
      WHEN mc.value_gap_pct < -25 THEN 'STRONG_SELL'
      ELSE 'UNKNOWN'
    END AS market_efficiency_signal,

    -- Inefficiency flag (actionable arbitrage)
    ABS(mc.value_gap_pct) > 25 AS market_inefficiency_flag

  FROM market_context mc
)
```

______________________________________________________________________

### Phase 3: Sustainability Analysis (High Impact, Medium Effort)

**New columns to add:**

```sql
-- Sustainable vs fluky performance
, expected_tds_season DECIMAL(5,2)  -- Based on opportunity + team context
, actual_tds_season INTEGER  -- From recent_stats
, tdoe DECIMAL(5,2)  -- TD Over/Under Expected (actual - expected)
, td_regression_risk_flag BOOLEAN  -- |TDOE| >= 3.0 (strong regression signal)
, td_regression_direction VARCHAR(10)  -- 'POSITIVE' (decline expected), 'NEGATIVE' (increase expected)

-- Opportunity vs efficiency (sticky metrics prioritized)
, target_share_pct DECIMAL(5,2)  -- Receiving opportunity (r² = 0.60, sticky)
, opportunity_share_pct DECIMAL(5,2)  -- Combined touches (r² = 0.55, sticky)
, tprr DECIMAL(5,3)  -- Targets per route run (r² = 0.65, very sticky)
, yprr DECIMAL(5,2)  -- Yards per route run (r² = 0.58, moderately sticky)
, td_rate_pct DECIMAL(5,2)  -- TD per target/touch (r² = 0.25, fluky!)
, sustainability_score DECIMAL(4,2)  -- 0.0-1.0, higher = more sustainable

-- Advanced metrics (if route data available)
, wopr DECIMAL(5,3)  -- Weighted Opportunity Rating (best WR predictor)
```

**Metric stickiness (from research):**

| Metric           | Year-to-Year r² | Classification    | Trading Weight                  |
| ---------------- | --------------- | ----------------- | ------------------------------- |
| **Targets**      | 0.65            | Sticky            | HIGH (trust projections)        |
| **Target Share** | 0.60            | Sticky            | HIGH (opportunity > efficiency) |
| **TPRR**         | 0.65            | Sticky            | HIGHEST (best WR predictor)     |
| **YPRR**         | 0.58            | Moderately Sticky | MEDIUM (reliable efficiency)    |
| **Touchdowns**   | 0.30            | Fluky             | LOW (regress to mean)           |
| **TD Rate**      | 0.25            | Fluky             | LOWEST (luck-driven)            |

**TDOE Regression (from research):**

- **Positive TDOE (+3.0+):** 86% decline next year, avg -52% fewer TDs → SELL signal
- **Negative TDOE (-3.0+):** 93% improve next year, avg +93% more TDs → BUY signal

**Implementation (SQL CTE):**

```sql
sustainability AS (
  SELECT
    fa.player_key,
    fa.position,

    -- Calculate expected TDs based on opportunity
    -- Formula: (Target_Share × Team_Pass_TDs × 0.8) + (Rush_Share × Team_Rush_TDs)
    CASE fa.position
      WHEN 'WR' THEN
        (opp.target_share_l4 * 35 * 0.8)  -- Assume 35 pass TDs/team/year
      WHEN 'RB' THEN
        (opp.target_share_l4 * 35 * 0.8 * 0.5) +  -- RBs get fewer passing TDs
        (opp.rush_share_l4 * 15)  -- Assume 15 rush TDs/team/year
      WHEN 'TE' THEN
        (opp.target_share_l4 * 35 * 0.8 * 0.6)  -- TEs get moderate passing TDs
      ELSE NULL
    END AS expected_tds_season,

    -- Actual TDs (from stats)
    rs.touchdowns_season AS actual_tds_season,

    -- TDOE calculation
    rs.touchdowns_season - expected_tds_season AS tdoe,

    -- Regression risk flag
    ABS(rs.touchdowns_season - expected_tds_season) >= 3.0
      AS td_regression_risk_flag,

    -- Regression direction
    CASE
      WHEN (rs.touchdowns_season - expected_tds_season) >= 3.0 THEN 'POSITIVE'
      WHEN (rs.touchdowns_season - expected_tds_season) <= -3.0 THEN 'NEGATIVE'
      ELSE 'NEUTRAL'
    END AS td_regression_direction,

    -- Opportunity metrics (already in CTE, reference here)
    opp.target_share_l4 * 100 AS target_share_pct,
    opp.opportunity_share_l4 * 100 AS opportunity_share_pct,

    -- TD rate (fluky metric)
    CASE
      WHEN rs.targets_season > 0 THEN
        (rs.touchdowns_season / rs.targets_season * 100)
      ELSE NULL
    END AS td_rate_pct,

    -- Sustainability score (high opportunity + average efficiency = sustainable)
    CASE
      WHEN opp.target_share_l4 > 0.22  -- High target share (sticky)
        AND (rs.touchdowns_season / rs.targets_season) BETWEEN 0.08 AND 0.12  -- Normal TD rate
      THEN 0.90  -- Very sustainable
      WHEN opp.target_share_l4 > 0.18
        AND (rs.touchdowns_season / rs.targets_season) BETWEEN 0.08 AND 0.14
      THEN 0.70  -- Sustainable
      WHEN opp.target_share_l4 < 0.15
        OR (rs.touchdowns_season / rs.targets_season) > 0.16  -- High TD rate (fluky)
      THEN 0.30  -- Unsustainable
      ELSE 0.50  -- Average
    END AS sustainability_score

  FROM fa_pool fa
  LEFT JOIN opportunity opp ON fa.player_key = opp.player_key
  LEFT JOIN recent_stats rs ON fa.player_key = rs.player_key
)
```

______________________________________________________________________

### Phase 4: League Context & VoR (Medium Impact, Low Effort)

**New columns to add:**

```sql
-- True league VoR (vs rostered players, not just FAs)
, league_replacement_level_ppg DECIMAL(5,2)  -- Median at position
, league_median_starter_ppg DECIMAL(5,2)  -- Median starter
, pts_above_league_replacement DECIMAL(6,2)  -- True VoR
, pts_vs_median_starter DECIMAL(6,2)  -- Starter comparison

-- Hypothetical league ranking
, hypothetical_league_rank INTEGER  -- If rostered, would rank Nth
, hypothetical_percentile DECIMAL(4,1)  -- Top X% at position
, total_league_rostered_at_pos INTEGER  -- Context for rank

-- Positional scarcity context
, position_scarcity_multiplier DECIMAL(3,2)  -- RB:1.5, WR:1.0, TE:1.2, QB:varies
```

**VoR baselines (from research):**

| Position     | Replacement Level | Typical in 12-team  |
| ------------ | ----------------- | ------------------- |
| **RB**       | RB24              | ~125 PPR pts/season |
| **WR**       | WR36              | ~140 PPR pts/season |
| **TE**       | TE12              | ~110 PPR pts/season |
| **QB (1QB)** | QB12              | ~280 pts/season     |
| **QB (SF)**  | QB24              | ~220 pts/season     |

**Implementation (SQL CTE):**

```sql
league_context AS (
  SELECT
    lrd.position,

    -- Replacement level (median RB2/WR3/etc)
    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY lrd.projected_ppg_ros)
      FILTER (WHERE lrd.roster_category = 'RB2' AND lrd.position = 'RB')
      AS rb_replacement_ppg,
    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY lrd.projected_ppg_ros)
      FILTER (WHERE lrd.roster_category = 'WR3' AND lrd.position = 'WR')
      AS wr_replacement_ppg,
    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY lrd.projected_ppg_ros)
      FILTER (WHERE lrd.roster_category = 'TE1' AND lrd.position = 'TE')
      AS te_replacement_ppg,

    -- Median starter (RB1/WR1/etc)
    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY lrd.projected_ppg_ros)
      FILTER (WHERE lrd.roster_category IN ('RB1', 'RB2') AND lrd.position = 'RB')
      AS rb_median_starter_ppg,
    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY lrd.projected_ppg_ros)
      FILTER (WHERE lrd.roster_category IN ('WR1', 'WR2', 'WR3') AND lrd.position = 'WR')
      AS wr_median_starter_ppg,

    -- Total rostered at position
    COUNT(*) FILTER (WHERE lrd.position = 'RB') AS rb_total_rostered,
    COUNT(*) FILTER (WHERE lrd.position = 'WR') AS wr_total_rostered,
    COUNT(*) FILTER (WHERE lrd.position = 'TE') AS te_total_rostered

  FROM {{ ref('mart_league_roster_depth') }} lrd
  GROUP BY lrd.position
),

league_vor AS (
  SELECT
    fa.player_key,
    fa.position,
    proj.projected_ppg_ros,

    -- League replacement level
    CASE fa.position
      WHEN 'RB' THEN lc.rb_replacement_ppg
      WHEN 'WR' THEN lc.wr_replacement_ppg
      WHEN 'TE' THEN lc.te_replacement_ppg
    END AS league_replacement_level_ppg,

    -- League median starter
    CASE fa.position
      WHEN 'RB' THEN lc.rb_median_starter_ppg
      WHEN 'WR' THEN lc.wr_median_starter_ppg
    END AS league_median_starter_ppg,

    -- True VoR (vs league replacement)
    proj.projected_ppg_ros -
      CASE fa.position
        WHEN 'RB' THEN lc.rb_replacement_ppg
        WHEN 'WR' THEN lc.wr_replacement_ppg
        WHEN 'TE' THEN lc.te_replacement_ppg
      END AS pts_above_league_replacement,

    -- Vs median starter
    proj.projected_ppg_ros -
      CASE fa.position
        WHEN 'RB' THEN lc.rb_median_starter_ppg
        WHEN 'WR' THEN lc.wr_median_starter_ppg
      END AS pts_vs_median_starter,

    -- Hypothetical league rank (if rostered)
    (SELECT COUNT(*) + 1
     FROM {{ ref('mart_league_roster_depth') }} lrd2
     WHERE lrd2.position = fa.position
       AND lrd2.projected_ppg_ros > proj.projected_ppg_ros
    ) AS hypothetical_league_rank,

    -- Total rostered for context
    CASE fa.position
      WHEN 'RB' THEN lc.rb_total_rostered
      WHEN 'WR' THEN lc.wr_total_rostered
      WHEN 'TE' THEN lc.te_total_rostered
    END AS total_league_rostered_at_pos,

    -- Percentile
    (1 - (hypothetical_league_rank / total_league_rostered_at_pos)) * 100
      AS hypothetical_percentile

  FROM fa_pool fa
  LEFT JOIN projections proj ON fa.player_key = proj.player_key
  CROSS JOIN league_context lc
)
```

______________________________________________________________________

### Phase 5: Enhanced Value Score & Bid Recommendations

**Updated composite score formula:**

```sql
enhanced_value_score AS (
  SELECT
    player_key,

    -- Weighted composite (0-100 scale)
    LEAST(100, GREATEST(0,
      -- Dynasty value (25% weight)
      (dv.dynasty_3yr_value / 500 * 25) +

      -- Aging curve context (20% weight)
      CASE
        WHEN dv.age_peak_window_flag THEN 20
        WHEN dv.age_decline_risk_score > 0.5 THEN 20 * (1 - dv.age_decline_risk_score)
        ELSE 20 * 0.5
      END +

      -- Market inefficiency (20% weight)
      CASE ms.market_efficiency_signal
        WHEN 'STRONG_BUY' THEN 20
        WHEN 'BUY' THEN 15
        WHEN 'HOLD' THEN 10
        WHEN 'SELL' THEN 5
        WHEN 'STRONG_SELL' THEN 0
        ELSE 10
      END +

      -- Sustainability (15% weight)
      (sus.sustainability_score * 15) +

      -- League VoR (10% weight)
      CASE
        WHEN lv.pts_above_league_replacement > 5 THEN 10
        WHEN lv.pts_above_league_replacement > 2 THEN 7
        WHEN lv.pts_above_league_replacement > 0 THEN 4
        ELSE 0
      END +

      -- Recent performance (10% weight)
      CASE
        WHEN rs.fantasy_ppg_last_4 > 12 THEN 10
        WHEN rs.fantasy_ppg_last_4 > 8 THEN 7
        WHEN rs.fantasy_ppg_last_4 > 5 THEN 4
        ELSE 0
      END
    )) AS enhanced_value_score,

    -- Bid confidence
    CASE
      WHEN ms.market_efficiency_signal IN ('STRONG_BUY', 'BUY')
        AND sus.sustainability_score > 0.6
        AND dv.age_peak_window_flag
        AND lv.pts_above_league_replacement > 2
      THEN 'VERY_HIGH'
      WHEN ms.market_efficiency_signal IN ('STRONG_BUY', 'BUY')
        AND sus.sustainability_score > 0.5
      THEN 'HIGH'
      WHEN ms.market_efficiency_signal = 'HOLD'
        AND sus.sustainability_score > 0.4
      THEN 'MEDIUM'
      ELSE 'LOW'
    END AS bid_confidence_v3

  FROM dynasty_valuation dv
  LEFT JOIN market_signals ms ON dv.player_key = ms.player_key
  LEFT JOIN sustainability sus ON dv.player_key = sus.player_key
  LEFT JOIN league_vor lv ON dv.player_key = lv.player_key
  LEFT JOIN recent_stats rs ON dv.player_key = rs.player_key
)
```

**Market-adjusted bids:**

```sql
market_adjusted_bids AS (
  SELECT
    fa.player_key,

    -- Dynasty bid (3-year value / 50 = years to amortize)
    ROUND(dv.dynasty_3yr_value / 50, 0) AS suggested_bid_dynasty_3yr,

    -- Market efficiency adjustment
    CASE ms.market_efficiency_signal
      WHEN 'STRONG_BUY' THEN ROUND(dv.dynasty_3yr_value / 50 * 1.3, 0)  -- Bid 30% more
      WHEN 'BUY' THEN ROUND(dv.dynasty_3yr_value / 50 * 1.1, 0)  -- Bid 10% more
      WHEN 'HOLD' THEN ROUND(dv.dynasty_3yr_value / 50, 0)
      WHEN 'SELL' THEN ROUND(dv.dynasty_3yr_value / 50 * 0.8, 0)  -- Bid 20% less
      WHEN 'STRONG_SELL' THEN 1  -- Minimum bid only
    END AS suggested_bid_market_adjusted,

    -- Competitive window adjustment (if user sets competitive state)
    -- TODO: Add dim_competitive_window with user's team state
    -- For now, assume contending
    CASE
      WHEN dv.age_peak_window_flag THEN suggested_bid_dynasty_3yr * 1.2
      WHEN dv.age_decline_risk_score > 0.5 THEN suggested_bid_dynasty_3yr * 0.7
      ELSE suggested_bid_dynasty_3yr
    END AS suggested_bid_contender,

    -- Rebuilder adjustment (defer aging players)
    CASE
      WHEN dv.age_at_snapshot < 25 THEN suggested_bid_dynasty_3yr * 1.3  -- Youth premium
      WHEN dv.age_at_snapshot > 27 THEN suggested_bid_dynasty_3yr * 0.5  -- Age discount
      ELSE suggested_bid_dynasty_3yr
    END AS suggested_bid_rebuilder

  FROM fa_pool fa
  LEFT JOIN dynasty_valuation dv ON fa.player_key = dv.player_key
  LEFT JOIN market_signals ms ON fa.player_key = ms.player_key
)
```

______________________________________________________________________

## Implementation Steps

### Step 1: Research Review (1 hour)

1. Read `docs/analytics_references/fasa_targets_research.md` Section 1 (valuation) and Section 2 (aging curves)
2. Review formulas and thresholds
3. Note any league-specific adjustments needed

### Step 2: Schema Design (1 hour)

1. Update `dbt/ff_data_transform/models/marts/_mart_fasa_targets.yml`
2. Add all new column definitions with descriptions
3. Add tests for new columns (not_null, ranges, accepted_values)
4. Document grain and dependencies

### Step 3: Phase 1 Implementation - Aging Curves (2 hours)

1. Add `aging_context` and `dynasty_valuation` CTEs to `mart_fasa_targets.sql`
2. Add new columns to final SELECT
3. Run: `make dbt-run MODELS=mart_fasa_targets`
4. Validate: Check age flags and 3yr values reasonable
5. Test: `make dbt-test MODELS=mart_fasa_targets`

### Step 4: Phase 2 Implementation - Market Efficiency (2 hours)

1. Add `market_context` and `market_signals` CTEs
2. Join to KTC values from `fact_asset_market_values`
3. Add market columns to final SELECT
4. Run and validate market gap calculations
5. Test buy/sell signals on known players

### Step 5: Phase 3 Implementation - Sustainability (2 hours)

1. Add `sustainability` CTE
2. Calculate TDOE and sticky metrics
3. Add sustainability columns to final SELECT
4. Validate TDOE calculations against known outliers
5. Test regression flags

### Step 6: Phase 4 Implementation - League VoR (1 hour)

1. Add `league_context` and `league_vor` CTEs
2. Join to `mart_league_roster_depth`
3. Add league VoR columns to final SELECT
4. Validate hypothetical rankings
5. Test true replacement level

### Step 7: Phase 5 Implementation - Enhanced Scoring (2 hours)

1. Add `enhanced_value_score` and `market_adjusted_bids` CTEs
2. Update composite score formula
3. Add new bid recommendation columns
4. Deprecate old `value_score` and `suggested_bid_1yr` (keep for comparison)
5. Run full model and validate

### Step 8: Documentation & Testing (1 hour)

1. Complete YAML documentation for all new columns
2. Add column-level tests
3. Update model description with new capabilities
4. Generate sample output for notebook

### Step 9: Notebook Integration (1 hour)

1. Update FASA notebook to display new columns
2. Add visualizations for market efficiency
3. Add aging curve warnings
4. Add sustainability flags
5. Export enhanced recommendations

______________________________________________________________________

## Success Criteria

### Functional Requirements

- ✅ All 40+ new columns added to `mart_fasa_targets`
- ✅ Aging curve adjustments applied (position-specific)
- ✅ Dynasty 3yr value calculated with discounting
- ✅ Market efficiency signals (buy/sell) working
- ✅ TDOE and sustainability scoring functional
- ✅ League VoR and hypothetical rankings correct
- ✅ Enhanced value score and market-adjusted bids calculated

### Quality Requirements

- ✅ All dbt tests passing
- ✅ Enhanced value scores 0-100 range
- ✅ Bid recommendations $1-100 range (reasonable)
- ✅ Age flags accurate (spot check 10 players)
- ✅ Market gaps sensible (compare to KTC)
- ✅ TDOE calculations validated against known regression cases

### Performance Requirements

- ✅ Model completes in < 2 minutes
- ✅ Grain maintained: `player_key, asof_date`
- ✅ 500-800 FAs scored (all eligible positions)

### Documentation Requirements

- ✅ YAML schema complete with all columns documented
- ✅ Formulas documented in column descriptions
- ✅ Research citations included in YAML `meta` fields
- ✅ Notebook updated with new visualizations

______________________________________________________________________

## Validation Commands

```bash
# Full rebuild
make dbt-run MODELS=mart_fasa_targets

# Run tests
make dbt-test MODELS=mart_fasa_targets

# Inspect aging curve adjustments
EXTERNAL_ROOT="$PWD/data/raw" duckdb dbt/ff_data_transform/target/dev.duckdb -c "
SELECT
  player_name,
  position,
  age_at_snapshot,
  age_peak_window_flag,
  age_decline_risk_score,
  dynasty_3yr_value,
  dynasty_discount_rate
FROM read_parquet('data/raw/marts/mart_fasa_targets/dt=*/data.parquet')
WHERE position = 'RB'
ORDER BY dynasty_3yr_value DESC
LIMIT 15;
"

# Check market efficiency signals
EXTERNAL_ROOT="$PWD/data/raw" duckdb dbt/ff_data_transform/target/dev.duckdb -c "
SELECT
  player_name,
  position,
  model_value,
  market_value,
  value_gap_pct,
  market_efficiency_signal,
  suggested_bid_market_adjusted
FROM read_parquet('data/raw/marts/mart_fasa_targets/dt=*/data.parquet')
WHERE market_inefficiency_flag = true
ORDER BY ABS(value_gap_pct) DESC
LIMIT 20;
"

# Validate TDOE and sustainability
EXTERNAL_ROOT="$PWD/data/raw" duckdb dbt/ff_data_transform/target/dev.duckdb -c "
SELECT
  player_name,
  position,
  actual_tds_season,
  expected_tds_season,
  tdoe,
  td_regression_direction,
  sustainability_score,
  target_share_pct
FROM read_parquet('data/raw/marts/mart_fasa_targets/dt=*/data.parquet')
WHERE td_regression_risk_flag = true
ORDER BY ABS(tdoe) DESC
LIMIT 20;
"

# Compare old vs new value scores
EXTERNAL_ROOT="$PWD/data/raw" duckdb dbt/ff_data_transform/target/dev.duckdb -c "
SELECT
  player_name,
  position,
  value_score AS old_score,
  enhanced_value_score AS new_score,
  (enhanced_value_score - value_score) AS score_diff,
  market_efficiency_signal,
  age_peak_window_flag
FROM read_parquet('data/raw/marts/mart_fasa_targets/dt=*/data.parquet')
WHERE position = 'RB'
ORDER BY enhanced_value_score DESC
LIMIT 20;
"

# Code quality
make sqlcheck
make sqlfix
```

______________________________________________________________________

## Expected Impact

### Before (Task 1.3 Baseline)

```
Isaiah Likely (TE, Age 24)
- Recent: 11.2 PPG last 4
- Projected: 9.8 PPG ROS
- Bid: $8 (projected_total_ros / 10)
- Value score: 67 (composite)
- Confidence: MEDIUM
```

**Limited context:**

- No aging curve insight (is 24 good for TE?)
- No market context (undervalued? overvalued?)
- No sustainability analysis (TD regression risk?)
- No dynasty timeline (1-year ROS only)

### After (Task 2.6 Enhanced)

```
Isaiah Likely (TE, Age 24)

DYNASTY VALUATION:
- Age: 24 (peak window: 25-27 for TE)
- Years to peak: 1 (entering prime)
- Age decline risk: 0.0 (no risk)
- Dynasty 3yr value: 412 pts (discounted)
  * Year 1 (ROS): 98 pts
  * Year 2: 167 pts (decline: 12.5%)
  * Year 3: 147 pts (decline: 12.5%)

MARKET INTELLIGENCE:
- Model value: 412 pts (our projection)
- Market value: 3,200 (KTC)
- Value gap: +28.8% (STRONG_BUY signal)
- Market inefficiency: TRUE (undervalued by market)

SUSTAINABILITY:
- Expected TDs: 4.2 (based on 14% target share)
- Actual TDs: 5 (season to date)
- TDOE: +0.8 (neutral, no regression risk)
- Target share: 14.2% (below sticky threshold)
- Sustainability score: 0.50 (average)

LEAGUE CONTEXT:
- Hypothetical rank: TE8 (if rostered)
- Percentile: Top 35% at TE
- Pts above league replacement: +2.3 PPG
- Pts vs median starter: -1.2 PPG (below TE1 median)

ENHANCED SCORING:
- Enhanced value score: 74 (↑7 from baseline)
- Bid confidence: HIGH (market inefficiency + age upside)
- Suggested bid (dynasty 3yr): $8
- Suggested bid (market adjusted): $10 (STRONG_BUY premium)
- Suggested bid (contender): $10 (age upside)
- Suggested bid (rebuilder): $11 (youth premium +30%)

STRATEGIC RECOMMENDATION:
✅ ACQUIRE - Undervalued by market, entering peak TE window,
   moderate opportunity with room for growth. Strong target
   for rebuilders (youth) and contenders (immediate TE2 value).

⚠️  CAUTION - Target share below 18% threshold for sustained
   WR/TE production. Monitor for increased role or target elsewhere.
```

**Transformative context:**

- ✅ Aging curve insight: Entering peak TE window (buy signal)
- ✅ Market inefficiency: 28.8% undervalued (strong buy)
- ✅ Sustainability: No TD regression risk, but opportunity limited
- ✅ Dynasty timeline: 3-year value projection
- ✅ Strategic fit: Adjustments for contender vs rebuilder
- ✅ League context: TE8 value with upside

**Decision confidence:** HIGH → User has full market intelligence to justify $10-11 FAAB bid with eyes wide open on upside (entering peak, undervalued) and risks (low target share, needs role growth).

______________________________________________________________________

## Commit Message

```
feat: transform FASA targets with dynasty market intelligence

Major enhancement to mart_fasa_targets integrating comprehensive
dynasty strategy frameworks:

1. AGING CURVE ADJUSTMENTS
   - Position-specific peak windows (RB:23-26, WR:26-30, etc)
   - 3-year discounted dynasty value with aging decline
   - Peak window flags and age decline risk scores

2. MARKET EFFICIENCY SCORING
   - Model vs market value gap percentage
   - Buy/sell signals (STRONG_BUY when gap > 25%)
   - Market inefficiency flags for arbitrage opportunities

3. SUSTAINABILITY ANALYSIS
   - TDOE (TD Over Expected) regression detection
   - Sticky vs fluky metric classification (TPRR r²=0.65)
   - Opportunity > efficiency prioritization

4. LEAGUE CONTEXT & VoR
   - True replacement level (vs rostered median, not FA pool)
   - Hypothetical league rankings if rostered
   - Positional scarcity multipliers

5. ENHANCED BID RECOMMENDATIONS
   - Dynasty 3yr bids (long-term value)
   - Market-adjusted bids (inefficiency premium/discount)
   - Contender vs rebuilder adjustments

Research foundation: 25,000 words, 50+ citations compiled in
docs/analytics_references/fasa_targets_research.md

Transforms FASA from tactical FAAB tool into comprehensive dynasty
market intelligence platform.

Part of Sprint 1 Phase 2 (Task 2.6)
Closes #XX
```

______________________________________________________________________

## Future Enhancements (Post-Sprint 1)

### Advanced Analytics

1. **WOPR calculation** - Requires route-level data (weighted opportunity rating)
2. **YPRR/TPRR** - Requires snap/route data from PFF or Sports Info Solutions
3. **WAR (Wins Above Replacement)** - Convert points to expected wins using probability
4. **Breakout prediction model** - ML model for Year 2-3 breakout candidates

### User Configuration

1. **Competitive window setting** - User declares "contending", "purgatory", or "rebuilding"
2. **Risk tolerance slider** - Adjust bid recommendations for conservative vs aggressive
3. **Position priorities** - User weights positions based on roster needs
4. **Cap space constraints** - Integrate with roster to show affordable targets

### Integration

1. **Trade value calculator** - Use dynasty valuations for trade evaluation
2. **Drop candidate optimizer** - Recommend drops to create cap space for targets
3. **Lineup optimizer** - Factor in bye weeks and matchups
4. **Draft pick equivalencies** - Convert player values to draft pick values

### Data Quality

1. **Projection ensembling** - Combine multiple projection sources (FFAnalytics, FantasyPros, etc)
2. **Historical backtest** - Validate aging curves against actual outcomes
3. **Calibration** - Tune discount rates and formulas to league history
4. **Uncertainty quantification** - Confidence intervals for projections

______________________________________________________________________

## References

### Research Documentation

- `docs/analytics_references/fasa_targets_research.md` - Master research compilation
- `docs/analytics_references/player_valuation_frameworks.md` - VoR, VBD, WAR formulas
- `docs/analytics_references/player_aging_curves_positional_value_research.md` - Aging curves
- `docs/analytics_references/dynasty_trade_value_methodologies.md` - KTC, DynastyProcess
- `docs/analytics_references/dynasty_strategy_frameworks_2025.md` - Strategic frameworks
- `docs/analytics_references/dynasty_roster_construction_strategies.md` - Roster construction
- `docs/analytics_references/dynasty_salary_cap_strategy_guide.md` - Cap management

### Industry Sources (Key Citations)

- **KeepTradeCut** - Crowdsourced market values (23M+ data points)
- **DynastyProcess** - Open-source valuation framework
- **PFF** - Aging curve research, advanced metrics
- **Fantasy Footballers** - TD regression analysis, draft capital research
- **Footballguys** - Adam Harstad mortality tables, VBD framework
- **Dynasty Nerds** - 2-3 year window strategy
- **PlayerProfiler** - Advanced metrics glossary (WOPR, YPRR, TPRR)

### dbt Model Dependencies

- `stg_sleeper__fa_pool` - FA player pool
- `mart_fantasy_projections` - ROS projections
- `fact_player_stats` - Recent performance, opportunity metrics
- `fact_asset_market_values` - KTC market values
- `mart_league_roster_depth` - League context, true VoR
- `mart_fa_acquisition_history` - Market behavior, bid history
- `dim_player` - Age data (birth_date)
- `dim_player_id_xref` - Identity resolution

______________________________________________________________________

**Status:** Ready for implementation
**Estimated Total Duration:** 8-12 hours
**Priority:** HIGH (transforms FASA into dynasty intelligence tool)
**Dependencies:** All prerequisites complete (Tasks 1.3, 2.4, 2.5 + research compilation)
