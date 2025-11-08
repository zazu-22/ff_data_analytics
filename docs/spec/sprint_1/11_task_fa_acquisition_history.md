# Task 2.4: FA Acquisition History Analysis

**Sprint:** Sprint 1 (Post-FASA Enhancement)
**Phase:** Phase 2 Extension
**Estimated Duration:** 6 hours
**Priority:** MEDIUM (enhances bid intelligence)

______________________________________________________________________

## Objective

Build `mart_fa_acquisition_history` to analyze historical free agent signings and train regression model to predict winning bids based on player performance tier, position scarcity, and time of season.

______________________________________________________________________

## Context

**Problem:** Current bid recommendations use simple heuristics ($1 per 10 projected points for RB), which don't reflect actual league bidding behavior.

**Solution:** Mine `fact_league_transactions` for FA signings and train model to predict winning bids.

**Example insights:**

- High-value RBs (>8 PPG) typically go for $10-15
- WR market more efficient: bids track projections closely
- Early-season FAAD bids 30% higher than in-season
- Position scarcity drives premiums (e.g., only 3 quality RBs available → bids spike)

______________________________________________________________________

## Dependencies

- ✅ `fact_league_transactions` exists (Task 1.2)
- ✅ Historical transaction data loaded

______________________________________________________________________

## Files to Create

### 1. `dbt/ff_data_transform/models/marts/mart_fa_acquisition_history.sql`

**Purpose:** Analytical mart of all FA acquisitions with context

**Grain:** `transaction_id_unique` (one row per FA acquisition)

**SQL Spec:**

```sql
{{
  config(
    materialized='table'
  )
}}

/*
FA Acquisition History - analyze winning bids for predictive modeling.

Grain: transaction_id_unique (one row per FA signing)
Purpose: Train bid prediction model for FASA
*/

WITH fa_acquisitions AS (
    SELECT
        t.transaction_id_unique,
        t.transaction_date,
        t.season,
        t.period_type,
        t.week,
        t.player_key,
        t.player_name,
        t.position,
        t.to_franchise_id,
        t.to_franchise_name,
        t.contract_total AS bid_amount,
        t.contract_years AS contract_length,
        t.contract_total / NULLIF(t.contract_years, 0) AS aav
    FROM {{ ref('fact_league_transactions') }} t
    WHERE t.transaction_type IN ('fa_acquisition', 'faad_acquisition')
        AND t.asset_type = 'player'
        AND t.contract_total IS NOT NULL
        AND t.position IN ('QB', 'RB', 'WR', 'TE')
),

-- Get player performance at time of signing
player_performance_context AS (
    SELECT
        fa.transaction_id_unique,
        fa.player_key,

        -- Recent performance (last 4 weeks before signing)
        AVG(CASE WHEN fps.week BETWEEN fa.week - 4 AND fa.week - 1
            THEN mfa.fantasy_points END) AS fantasy_ppg_l4_before_signing,

        -- Season average before signing
        AVG(CASE WHEN fps.week < fa.week
            THEN mfa.fantasy_points END) AS fantasy_ppg_season_before_signing,

        -- Usage metrics
        AVG(CASE WHEN fps.week BETWEEN fa.week - 4 AND fa.week - 1
            THEN mfa.rush_attempts + mfa.targets END) AS touches_per_game_l4

    FROM fa_acquisitions fa
    LEFT JOIN {{ ref('fact_player_stats') }} fps
        ON fa.player_key = fps.player_key
        AND fa.season = fps.season
        AND fps.stat_kind = 'actual'
    LEFT JOIN {{ ref('mart_fantasy_actuals_weekly') }} mfa
        ON fps.player_id = mfa.player_id
        AND fps.season = mfa.season
        AND fps.week = mfa.week
    GROUP BY 1, 2
),

-- Calculate position scarcity at time of signing
position_scarcity AS (
    SELECT
        fa.transaction_id_unique,
        fa.position,
        fa.season,
        fa.week,

        -- Count quality FAs available (projected > replacement level)
        COUNT(CASE WHEN proj.projected_ppg_ros > 5.0 THEN 1 END) AS quality_fas_available,

        -- Market depth indicator (0-1, lower = more scarce)
        COUNT(CASE WHEN proj.projected_ppg_ros > 5.0 THEN 1 END) /
            NULLIF(COUNT(*), 0.0) AS market_depth_ratio

    FROM fa_acquisitions fa
    LEFT JOIN {{ ref('mart_fantasy_projections') }} proj
        ON fa.season = proj.season
        AND fa.week = proj.week
        AND fa.position = proj.position
    GROUP BY 1, 2, 3, 4
)

SELECT
    fa.*,

    -- Performance context
    ppc.fantasy_ppg_l4_before_signing,
    ppc.fantasy_ppg_season_before_signing,
    ppc.touches_per_game_l4,

    -- Market context
    ps.quality_fas_available,
    ps.market_depth_ratio,

    -- Time context
    CASE
        WHEN fa.period_type = 'faad' THEN 'FAAD'
        WHEN fa.week <= 4 THEN 'Early Season'
        WHEN fa.week BETWEEN 5 AND 12 THEN 'Mid Season'
        ELSE 'Late Season'
    END AS season_phase,

    -- Performance tier at signing
    CASE
        WHEN ppc.fantasy_ppg_l4_before_signing >= 12.0 THEN 'Elite'
        WHEN ppc.fantasy_ppg_l4_before_signing >= 8.0 THEN 'Strong'
        WHEN ppc.fantasy_ppg_l4_before_signing >= 5.0 THEN 'Viable'
        ELSE 'Speculative'
    END AS performance_tier,

    -- Bid efficiency metrics
    fa.bid_amount / NULLIF(ppc.fantasy_ppg_l4_before_signing, 0) AS dollars_per_ppg,

    -- Metadata
    CURRENT_DATE AS asof_date

FROM fa_acquisitions fa
LEFT JOIN player_performance_context ppc USING (transaction_id_unique)
LEFT JOIN position_scarcity ps USING (transaction_id_unique)
```

**Tests:**

```yaml
# dbt/ff_data_transform/models/marts/_mart_fa_acquisition_history.yml
models:
  - name: mart_fa_acquisition_history
    description: "Historical FA acquisitions with performance/market context for bid modeling"

    data_tests:
      - dbt_utils.unique_combination_of_columns:
          arguments:
            combination_of_columns:
              - transaction_id_unique
          config:
            severity: error

    columns:
      - name: transaction_id_unique
        description: "Primary key"
        data_tests:
          - not_null

      - name: bid_amount
        description: "Total contract value (winning bid)"
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

1. Create `mart_fa_acquisition_history.sql`
2. Create corresponding `_mart_fa_acquisition_history.yml` tests
3. Run: `make dbt-run MODELS=mart_fa_acquisition_history`
4. Run: `make dbt-test MODELS=mart_fa_acquisition_history`
5. Validate data quality (spot check known transactions)

______________________________________________________________________

## Success Criteria

- ✅ Mart builds without errors
- ✅ All unique key tests pass
- ✅ Contains 50+ historical FA acquisitions (2023-2025)
- ✅ Performance context populated for 80%+ of transactions
- ✅ Position scarcity metrics calculated

______________________________________________________________________

## Validation Commands

```bash
# Build mart
make dbt-run MODELS=mart_fa_acquisition_history

# Test
make dbt-test MODELS=mart_fa_acquisition_history

# Explore
EXTERNAL_ROOT="$PWD/data/raw" duckdb dbt/ff_data_transform/target/dev.duckdb -c "
SELECT position, performance_tier, season_phase,
       COUNT(*) as acquisitions,
       AVG(bid_amount) as avg_bid,
       AVG(dollars_per_ppg) as avg_efficiency
FROM main.mart_fa_acquisition_history
GROUP BY 1, 2, 3
ORDER BY 1, 2, 3;
"
```

______________________________________________________________________

## Commit Message

```
feat: add FA acquisition history mart for bid intelligence

Analyze historical free agent signings from fact_league_transactions
to train predictive bidding model. Includes:
- Performance context at time of signing
- Position scarcity metrics
- Bid efficiency analysis ($/PPG)
- Season phase segmentation

Enables data-driven bid recommendations replacing simple heuristics.

Part of Sprint 1 Phase 2 enhancements.
```

______________________________________________________________________

## Next Steps

After this task completes:

- **Task 2.5**: Create league roster depth mart (value over replacement)
- **Task 2.6**: Enhance `mart_fasa_targets` with bid model predictions
