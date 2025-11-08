# Task 2.5: League Roster Depth Analysis

**Sprint:** Sprint 1 (Post-FASA Enhancement)
**Phase:** Phase 2 Extension
**Estimated Duration:** 4 hours
**Priority:** MEDIUM (improves value assessment)

______________________________________________________________________

## Objective

Build `mart_league_roster_depth` to enable true **Value Over Replacement (VoR)** calculations by comparing FA targets to **all rostered players** across the league, not just other free agents.

______________________________________________________________________

## Context

**Problem:** Current `mart_fasa_targets` calculates replacement level as 25th percentile of FA pool only. This doesn't show how FA targets compare to starting lineups league-wide.

**Example:**

```
Current (FA-only baseline):
- Zonovan Knight: 11.1 PPG, value_score = 74
- Replacement (25th %ile FA RB): 2.5 PPG
- Points above replacement: +8.6 PPG

Enhanced (league-wide baseline):
- Zonovan Knight: 11.1 PPG
- League median RB2: 8.7 PPG  ← True benchmark
- Value over typical RB2: +2.4 PPG
- Would be RB8 if rostered (top 20%)
```

This shows Knight is an **upgrade** but not elite, providing better context for bidding decisions.

______________________________________________________________________

## Dependencies

- ✅ `stg_sheets__contracts_active` exists (my roster + all other teams)
- ✅ `mart_fantasy_projections` exists (ROS projections for all players)
- ✅ `dim_league_rules` exists (roster slot requirements)

______________________________________________________________________

## Files to Create

### 1. `dbt/ff_data_transform/models/marts/mart_league_roster_depth.sql`

**Purpose:** Rank all rostered players by position with league percentiles

**Grain:** `franchise_id, player_key, asof_date`

**SQL Spec:**

```sql
{{
  config(
    materialized='table'
  )
}}

/*
League Roster Depth - rank all rostered players for VoR analysis.

Grain: franchise_id, player_key, asof_date
Purpose: Provide league-wide context for FA target evaluation
*/

WITH current_rosters AS (
    SELECT
        c.franchise_id,
        c.player_id AS player_key,
        d.display_name AS player_name,
        d.position,
        c.current_year_cap_hit,
        c.years_remaining
    FROM {{ ref('stg_sheets__contracts_active') }} c
    INNER JOIN {{ ref('dim_player') }} d ON c.player_id = d.player_id
    WHERE c.obligation_year = YEAR(CURRENT_DATE)
        AND d.position IN ('QB', 'RB', 'WR', 'TE')
),

projections_ros AS (
    SELECT
        player_id AS player_key,
        AVG(projected_fantasy_points) AS projected_ppg_ros,
        SUM(projected_fantasy_points) AS projected_total_ros,
        COUNT(*) AS weeks_remaining
    FROM {{ ref('mart_fantasy_projections') }}
    WHERE season = YEAR(CURRENT_DATE)
        AND week > (
            SELECT MAX(week)
            FROM {{ ref('dim_schedule') }}
            WHERE season = YEAR(CURRENT_DATE)
                AND CAST(game_date AS DATE) < CURRENT_DATE
        )
        AND horizon = 'weekly'
    GROUP BY player_id
),

position_rankings AS (
    SELECT
        r.franchise_id,
        r.player_key,
        r.player_name,
        r.position,
        r.current_year_cap_hit,
        r.years_remaining,
        COALESCE(p.projected_ppg_ros, 0.0) AS projected_ppg_ros,
        COALESCE(p.projected_total_ros, 0.0) AS projected_total_ros,

        -- Rank within franchise (depth chart)
        ROW_NUMBER() OVER (
            PARTITION BY r.franchise_id, r.position
            ORDER BY COALESCE(p.projected_ppg_ros, 0.0) DESC
        ) AS team_depth_rank,

        -- Rank across entire league
        ROW_NUMBER() OVER (
            PARTITION BY r.position
            ORDER BY COALESCE(p.projected_ppg_ros, 0.0) DESC
        ) AS league_rank_at_position,

        -- Count of rostered players at position
        COUNT(*) OVER (PARTITION BY r.position) AS total_rostered_at_position,

        -- Percentile within position
        PERCENT_RANK() OVER (
            PARTITION BY r.position
            ORDER BY COALESCE(p.projected_ppg_ros, 0.0) DESC
        ) AS league_percentile_at_position

    FROM current_rosters r
    LEFT JOIN projections_ros p USING (player_key)
),

position_benchmarks AS (
    -- Calculate key benchmarks for each position
    SELECT
        position,

        -- Starter benchmarks (top players per league rules)
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY projected_ppg_ros DESC) FILTER (WHERE league_rank_at_position <= 12) AS median_starter_ppg,
        PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY projected_ppg_ros DESC) FILTER (WHERE league_rank_at_position <= 12) AS weak_starter_ppg,

        -- FLEX benchmarks (next tier of RB/WR/TE)
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY projected_ppg_ros DESC) FILTER (WHERE league_rank_at_position BETWEEN 13 AND 24) AS median_flex_ppg,

        -- Overall median
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY projected_ppg_ros) AS median_rostered_ppg,

        -- Replacement level (bottom quartile of rostered players)
        PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY projected_ppg_ros) AS replacement_level_ppg

    FROM position_rankings
    GROUP BY position
)

SELECT
    pr.*,

    -- Benchmark comparisons
    pb.median_starter_ppg,
    pb.weak_starter_ppg,
    pb.median_flex_ppg,
    pb.median_rostered_ppg,
    pb.replacement_level_ppg,

    -- Points above benchmarks
    pr.projected_ppg_ros - pb.median_starter_ppg AS pts_above_median_starter,
    pr.projected_ppg_ros - pb.median_flex_ppg AS pts_above_flex_median,
    pr.projected_ppg_ros - pb.replacement_level_ppg AS pts_above_replacement,

    -- Roster tier classification
    CASE
        WHEN pr.team_depth_rank = 1 THEN 'Starter'
        WHEN pr.team_depth_rank = 2 AND pr.position IN ('RB', 'WR') THEN 'Starter'
        WHEN pr.team_depth_rank = 3 AND pr.position = 'RB' THEN 'Flex'
        WHEN pr.team_depth_rank <= 5 THEN 'Bench'
        ELSE 'Deep Bench'
    END AS roster_tier,

    -- League tier (for comparison to FAs)
    CASE
        WHEN pr.league_percentile_at_position <= 0.25 THEN 'Elite'
        WHEN pr.league_percentile_at_position <= 0.50 THEN 'Strong'
        WHEN pr.league_percentile_at_position <= 0.75 THEN 'Viable'
        ELSE 'Weak'
    END AS league_tier,

    -- Metadata
    CURRENT_DATE AS asof_date

FROM position_rankings pr
LEFT JOIN position_benchmarks pb ON pr.position = pb.position
```

**Tests:**

```yaml
# dbt/ff_data_transform/models/marts/_mart_league_roster_depth.yml
models:
  - name: mart_league_roster_depth
    description: "All rostered players ranked by position with league benchmarks"

    data_tests:
      - dbt_utils.unique_combination_of_columns:
          arguments:
            combination_of_columns:
              - franchise_id
              - player_key
              - asof_date
          config:
            severity: error

    columns:
      - name: player_key
        description: "FK to dim_player"
        data_tests:
          - not_null

      - name: franchise_id
        description: "FK to dim_franchise"
        data_tests:
          - not_null

      - name: position
        description: "Player position"
        data_tests:
          - accepted_values:
              arguments:
                values: ['QB', 'RB', 'WR', 'TE']
```

______________________________________________________________________

## Implementation Steps

1. Create `mart_league_roster_depth.sql`
2. Create corresponding `_mart_league_roster_depth.yml` tests
3. Run: `make dbt-run MODELS=mart_league_roster_depth`
4. Run: `make dbt-test MODELS=mart_league_roster_depth`
5. Validate Jason's roster appears correctly ranked

______________________________________________________________________

## Success Criteria

- ✅ Mart builds without errors
- ✅ All tests pass
- ✅ Contains 300+ rostered players (12 teams × 25 roster spots)
- ✅ Benchmarks calculated for QB/RB/WR/TE
- ✅ Jason's roster correctly ranked

______________________________________________________________________

## Validation Commands

```bash
# Build mart
make dbt-run MODELS=mart_league_roster_depth

# Test
make dbt-test MODELS=mart_league_roster_depth

# Explore Jason's roster
EXTERNAL_ROOT="$PWD/data/raw" duckdb dbt/ff_data_transform/target/dev.duckdb -c "
SELECT player_name, position, team_depth_rank, league_rank_at_position,
       projected_ppg_ros, league_tier, roster_tier
FROM main.mart_league_roster_depth
WHERE franchise_id = (SELECT franchise_id FROM dim_franchise WHERE owner_name = 'Jason Shaffer' LIMIT 1)
ORDER BY position, team_depth_rank;
"

# Position benchmarks
EXTERNAL_ROOT="$PWD/data/raw" duckdb dbt/ff_data_transform/target/dev.duckdb -c "
SELECT DISTINCT position,
       median_starter_ppg,
       median_flex_ppg,
       replacement_level_ppg
FROM main.mart_league_roster_depth
ORDER BY position;
"
```

______________________________________________________________________

## Commit Message

```
feat: add league roster depth mart for true VoR analysis

Rank all 300+ rostered players by position with league-wide benchmarks:
- Team depth charts (RB1, RB2, FLEX, Bench)
- League percentiles (Elite/Strong/Viable/Weak tiers)
- Points above replacement vs league median starters

Enables comparison of FA targets to actual starting lineups,
not just other free agents.

Part of Sprint 1 Phase 2 enhancements.
```

______________________________________________________________________

## Next Steps

After this task completes:

- **Task 2.6**: Enhance `mart_fasa_targets` to include league VoR context
