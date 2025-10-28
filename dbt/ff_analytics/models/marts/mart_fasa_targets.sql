-- Grain: player_key, asof_date, week
-- Purpose: Score every FA for FASA with bid recommendations

WITH fa_pool AS (
    SELECT * FROM {{ ref('stg_sleeper__fa_pool') }}
),

recent_stats AS (
    -- Aggregate recent performance from fantasy actuals
    SELECT
        player_key,

        -- Last 3/4/8 games
        AVG(CASE WHEN game_recency <= 3 THEN fantasy_points END) AS fantasy_ppg_last_3,
        AVG(CASE WHEN game_recency <= 4 THEN fantasy_points END) AS fantasy_ppg_last_4,
        AVG(CASE WHEN game_recency <= 8 THEN fantasy_points END) AS fantasy_ppg_last_8,
        AVG(fantasy_points) AS fantasy_ppg_season,

        -- Real-world volume (last 4 weeks)
        AVG(CASE WHEN game_recency <= 4 THEN attempts END) AS attempts_per_game_l4,
        AVG(CASE WHEN game_recency <= 4 THEN targets END) AS targets_per_game_l4,

        -- Efficiency
        SUM(rushing_yards) / NULLIF(SUM(carries), 0) AS ypc,
        SUM(receiving_yards) / NULLIF(SUM(receptions), 0) AS ypr,
        SUM(receptions) / NULLIF(SUM(targets), 0) AS catch_rate

    FROM (
        SELECT
            player_key,
            fantasy_points,
            attempts,
            targets,
            carries,
            rushing_yards,
            receiving_yards,
            receptions,
            ROW_NUMBER() OVER (PARTITION BY player_key ORDER BY season DESC, week DESC) AS game_recency
        FROM {{ ref('mart_fantasy_actuals_weekly') }}
        WHERE season = YEAR(CURRENT_DATE)
            AND week <= (SELECT MAX(week) FROM {{ ref('dim_schedule') }} WHERE season = YEAR(CURRENT_DATE) AND CAST(game_date AS DATE) < CURRENT_DATE)
    )
    GROUP BY player_key
),

projections AS (
    -- Rest of season projections (join through dim_player to get mfl_id)
    SELECT
        dp.mfl_id,
        SUM(proj.projected_fantasy_points) AS projected_total_ros,
        AVG(proj.projected_fantasy_points) AS projected_ppg_ros,
        COUNT(*) AS weeks_remaining
    FROM {{ ref('mart_fantasy_projections') }} proj
    INNER JOIN {{ ref('dim_player') }} dp ON proj.player_id = dp.player_id
    WHERE proj.season = YEAR(CURRENT_DATE)
        AND proj.week > (SELECT MAX(week) FROM {{ ref('dim_schedule') }} WHERE season = YEAR(CURRENT_DATE) AND CAST(game_date AS DATE) < CURRENT_DATE)
        AND proj.horizon = 'weekly'  -- Changed from 'full_season'
        AND dp.mfl_id IS NOT NULL
    GROUP BY dp.mfl_id
),

opportunity AS (
    -- Calculate opportunity shares from ff_opportunity attempt metrics
    -- rec_attempt / rec_attempt_team = target share
    -- rush_attempt / rush_attempt_team = rush share
    SELECT
        player_key,
        AVG(CASE WHEN game_recency <= 4 THEN target_share END) AS target_share_l4,
        AVG(CASE WHEN game_recency <= 4 THEN rush_share END) AS rush_share_l4,
        -- Combined opportunity share (weighted average for RB/WR/TE)
        AVG(CASE WHEN game_recency <= 4 THEN
            COALESCE(target_share, 0) * 0.6 + COALESCE(rush_share, 0) * 0.4
        END) AS opportunity_share_l4
    FROM (
        SELECT
            player_key,
            season,
            week,
            -- Calculate target share (receiving opportunity)
            MAX(CASE WHEN stat_name = 'rec_attempt' THEN stat_value END) /
                NULLIF(MAX(CASE WHEN stat_name = 'rec_attempt_team' THEN stat_value END), 0) AS target_share,
            -- Calculate rush share (rushing opportunity)
            MAX(CASE WHEN stat_name = 'rush_attempt' THEN stat_value END) /
                NULLIF(MAX(CASE WHEN stat_name = 'rush_attempt_team' THEN stat_value END), 0) AS rush_share,
            ROW_NUMBER() OVER (PARTITION BY player_key ORDER BY season DESC, week DESC) AS game_recency
        FROM {{ ref('fact_player_stats') }}
        WHERE stat_kind = 'actual'
            AND measure_domain = 'real_world'
            AND season = YEAR(CURRENT_DATE)
            AND stat_name IN ('rec_attempt', 'rec_attempt_team', 'rush_attempt', 'rush_attempt_team')
        GROUP BY player_key, season, week
    )
    WHERE game_recency <= 4
    GROUP BY player_key
),

market_values AS (
    -- KTC valuations
    SELECT
        player_key,
        ktc_value,
        overall_rank AS ktc_rank_overall,
        positional_rank AS ktc_rank_at_position,
        ktc_value - LAG(ktc_value, 4) OVER (PARTITION BY player_key ORDER BY asof_date) AS ktc_trend_4wk
    FROM {{ ref('fact_asset_market_values') }}
    WHERE asset_type = 'player'
        AND market_scope = 'dynasty_1qb'
    QUALIFY ROW_NUMBER() OVER (PARTITION BY player_key ORDER BY asof_date DESC) = 1
),

position_baselines AS (
    -- Calculate replacement level (25th percentile at position)
    SELECT
        position,
        PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY projected_ppg_ros) AS replacement_ppg,
        MAX(projected_ppg_ros) AS max_projected_ppg
    FROM projections p
    INNER JOIN fa_pool fa ON p.mfl_id = fa.mfl_id
    GROUP BY position
)

SELECT
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
        0.40 * COALESCE(proj.projected_ppg_ros / NULLIF(pb.max_projected_ppg, 0), 0) +

        -- Opportunity: Normalize by capping at 25% team share (0-1 scale)
        -- A player getting 25%+ of team opportunities = full 25 points
        0.25 * LEAST(COALESCE(opp.opportunity_share_l4, 0) / 0.25, 1.0) +

        -- Efficiency: Binary scoring based on thresholds (0-1 scale)
        0.20 * (CASE
            WHEN rs.ypc > 4.5 THEN 1.0
            WHEN rs.ypr > 11.0 THEN 1.0
            WHEN rs.catch_rate > 0.70 THEN 0.8
            ELSE 0.3
        END) +

        -- Market: Invert rank so lower rank = higher score (0-1 scale)
        -- Top 20 at position = full 15 points, rank 100+ = 0 points
        0.15 * GREATEST(1.0 - (COALESCE(ktc.ktc_rank_at_position, 100) / 100.0), 0)
    ) * 100 AS value_score,

    -- Points above replacement
    proj.projected_ppg_ros - pb.replacement_ppg AS points_above_replacement,

    -- Breakout indicator (high opportunity share + trending performance + efficiency)
    CASE
        WHEN opp.opportunity_share_l4 > 0.20  -- Getting 20%+ of team's opportunities
            AND rs.fantasy_ppg_last_4 > COALESCE(rs.fantasy_ppg_last_8, 0)
            AND (rs.ypc > 4.5 OR rs.ypr > 10.0)
        THEN TRUE
        ELSE FALSE
    END AS breakout_indicator,

    -- Regression risk (overperforming)
    CASE
        WHEN rs.fantasy_ppg_last_4 > proj.projected_ppg_ros * 1.3
        THEN TRUE
        ELSE FALSE
    END AS regression_risk_flag,

    -- Bid Recommendations (business logic)
    CASE
        WHEN fa.position = 'RB' THEN ROUND(proj.projected_total_ros / 10, 0)  -- $1 per 10 projected points
        WHEN fa.position = 'WR' THEN ROUND(proj.projected_total_ros / 12, 0)
        WHEN fa.position = 'TE' THEN ROUND(proj.projected_total_ros / 15, 0)
        WHEN fa.position = 'QB' THEN ROUND(proj.projected_total_ros / 20, 0)
        ELSE 1
    END AS suggested_bid_1yr,

    CASE
        WHEN proj.projected_total_ros > 100 THEN ROUND(proj.projected_total_ros / 8, 0)  -- Discount for multi-year
        ELSE NULL
    END AS suggested_bid_2yr,

    -- Bid confidence (based on recent performance + opportunity + projections)
    CASE
        WHEN rs.fantasy_ppg_last_4 IS NOT NULL
            AND opp.opportunity_share_l4 > 0.15  -- Getting 15%+ of team opportunities
            AND proj.projected_ppg_ros > pb.replacement_ppg
        THEN 'HIGH'
        WHEN proj.projected_ppg_ros > pb.replacement_ppg
        THEN 'MEDIUM'
        ELSE 'LOW'
    END AS bid_confidence,

    -- Priority ranking
    ROW_NUMBER() OVER (ORDER BY value_score DESC) AS priority_rank_overall,
    ROW_NUMBER() OVER (PARTITION BY fa.position ORDER BY value_score DESC) AS priority_rank_at_position,

    -- Metadata
    CURRENT_DATE AS asof_date,
    (SELECT MAX(week) FROM {{ ref('dim_schedule') }} WHERE season = YEAR(CURRENT_DATE) AND CAST(game_date AS DATE) < CURRENT_DATE) AS current_week

FROM fa_pool fa
LEFT JOIN recent_stats rs USING (player_key)
INNER JOIN projections proj ON fa.mfl_id = proj.mfl_id  -- Only FAs with projections
LEFT JOIN opportunity opp USING (player_key)
LEFT JOIN market_values ktc USING (player_key)
LEFT JOIN position_baselines pb ON fa.position = pb.position

WHERE fa.position IN ('QB', 'RB', 'WR', 'TE')  -- Focus on offensive skill positions for FASA
