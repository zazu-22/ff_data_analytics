-- Grain: player_key, asof_date
-- Purpose: Identify drop candidates on Jason's roster

WITH my_roster AS (
    SELECT DISTINCT
        c.player_id AS player_key,
        d.position
    FROM {{ ref('stg_sheets__contracts_active') }} c
    INNER JOIN {{ ref('dim_player') }} d ON c.player_id = d.player_id
    WHERE c.gm_full_name = 'Jason Shaffer'
        AND c.obligation_year = YEAR(CURRENT_DATE)
),

contracts AS (
    SELECT
        player_id AS player_key,
        COUNT(DISTINCT obligation_year) AS years_remaining,
        SUM(CASE WHEN obligation_year = YEAR(CURRENT_DATE) THEN cap_hit END) AS current_year_cap_hit,
        SUM(CASE WHEN obligation_year > YEAR(CURRENT_DATE) THEN cap_hit END) AS future_years_cap_hit,
        SUM(cap_hit) AS total_remaining
    FROM {{ ref('stg_sheets__contracts_active') }}
    WHERE gm_full_name = 'Jason Shaffer'
    GROUP BY player_id
),

dead_cap AS (
    -- Calculate dead cap if cut now using dim_cut_liability_schedule
    SELECT
        c.player_key,
        c.total_remaining * dl.dead_cap_pct AS dead_cap_if_cut_now
    FROM contracts c
    INNER JOIN {{ ref('dim_cut_liability_schedule') }} dl
        ON c.years_remaining = dl.contract_year
),

performance AS (
    SELECT
        player_id AS player_key,
        AVG(CASE WHEN game_recency <= 8 THEN fantasy_points END) AS fantasy_ppg_last_8
    FROM (
        SELECT
            player_id,
            fantasy_points,
            ROW_NUMBER() OVER (PARTITION BY player_id ORDER BY season DESC, week DESC) AS game_recency
        FROM {{ ref('mart_fantasy_actuals_weekly') }}
        WHERE season = YEAR(CURRENT_DATE)
    )
    WHERE game_recency <= 8
    GROUP BY player_id
),

projections AS (
    SELECT
        player_id,
        AVG(projected_fantasy_points) AS projected_ppg_ros,
        SUM(projected_fantasy_points) AS projected_total_ros,
        COUNT(*) AS weeks_remaining
    FROM {{ ref('mart_fantasy_projections') }}
    WHERE season = YEAR(CURRENT_DATE)
        AND week > (SELECT MAX(week) FROM {{ ref('dim_schedule') }} WHERE season = YEAR(CURRENT_DATE) AND CAST(game_date AS DATE) < CURRENT_DATE)
        AND horizon = 'weekly'
    GROUP BY player_id
),

position_depth AS (
    -- Rank players at each position on my roster
    SELECT
        player_key,
        ROW_NUMBER() OVER (PARTITION BY position ORDER BY projected_ppg_ros DESC) AS position_depth_rank
    FROM my_roster
    LEFT JOIN projections ON my_roster.player_key = projections.player_id
)

SELECT
    -- Identity
    r.player_key,
    dim.display_name AS player_name,
    r.position,

    -- Contract
    c.years_remaining,
    c.current_year_cap_hit,
    c.future_years_cap_hit,
    c.total_remaining,
    dc.dead_cap_if_cut_now,
    c.current_year_cap_hit - dc.dead_cap_if_cut_now AS cap_space_freed,

    -- Performance
    perf.fantasy_ppg_last_8,
    proj.projected_ppg_ros,

    -- Value Assessment
    proj.projected_ppg_ros / NULLIF(c.current_year_cap_hit, 0) AS points_per_dollar,
    proj.projected_ppg_ros - (
        SELECT PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY projected_ppg_ros)
        FROM {{ ref('mart_fasa_targets') }}
        WHERE position = r.position
    ) AS replacement_surplus,

    -- Droppable score (0-100, higher = more droppable)
    (
        CASE WHEN proj.projected_ppg_ros < 5 THEN 30 ELSE 0 END +  -- Low production
        CASE WHEN c.current_year_cap_hit > 10 THEN 30 ELSE 0 END +  -- High cap hit
        CASE WHEN dc.dead_cap_if_cut_now < 5 THEN 20 ELSE 0 END +   -- Low dead cap
        CASE WHEN pd.position_depth_rank > 3 THEN 20 ELSE 0 END     -- Roster depth
    ) AS droppable_score,

    -- Opportunity cost
    (c.current_year_cap_hit - dc.dead_cap_if_cut_now) - (proj.projected_ppg_ros / 10) AS opportunity_cost,

    -- Roster Context
    pd.position_depth_rank,
    CASE
        WHEN pd.position_depth_rank <= 2 THEN 'STARTER'
        WHEN pd.position_depth_rank = 3 THEN 'FLEX'
        ELSE 'BENCH'
    END AS roster_tier,
    c.years_remaining AS weeks_until_contract_expires,

    -- Recommendation
    CASE
        WHEN droppable_score >= 80 THEN 'DROP_FOR_CAP'
        WHEN droppable_score >= 60 AND proj.projected_ppg_ros < 8 THEN 'CONSIDER'
        WHEN droppable_score >= 40 THEN 'DROP_FOR_UPSIDE'
        ELSE 'KEEP'
    END AS drop_recommendation,

    -- Metadata
    CURRENT_DATE AS asof_date

FROM my_roster r
LEFT JOIN contracts c USING (player_key)
LEFT JOIN dead_cap dc USING (player_key)
LEFT JOIN performance perf USING (player_key)
LEFT JOIN projections proj ON r.player_key = proj.player_id
LEFT JOIN position_depth pd USING (player_key)
LEFT JOIN {{ ref('dim_player') }} dim ON r.player_key = dim.player_id

ORDER BY droppable_score DESC
