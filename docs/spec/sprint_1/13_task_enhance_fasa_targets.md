# Task 2.6: Enhance FASA Targets with Predictive Bids & League VoR

**Sprint:** Sprint 1 (Post-FASA Enhancement)
**Phase:** Phase 2 Extension
**Estimated Duration:** 4 hours
**Priority:** MEDIUM (final integration)

______________________________________________________________________

## Objective

Enhance `mart_fasa_targets` to replace heuristic bid calculations with:
1. **Predictive bid model** trained on `mart_fa_acquisition_history`
2. **League-wide VoR** from `mart_league_roster_depth`

______________________________________________________________________

## Context

**Current state:**
- Bid formula: `projected_total_ros / 10` for RBs (simple heuristic)
- Replacement level: 25th percentile of FA pool
- No market intelligence

**Enhanced state:**
- Bid prediction: Regression model using performance tier, scarcity, season phase
- Replacement level: League median at position (true VoR)
- Market context: "Would be RB8 if rostered (top 20%)"

______________________________________________________________________

## Dependencies

- ✅ Task 2.4 complete: `mart_fa_acquisition_history` exists
- ✅ Task 2.5 complete: `mart_league_roster_depth` exists
- ✅ `mart_fasa_targets` exists (baseline from Task 1.3)

______________________________________________________________________

## Implementation Approach

### Option A: SQL-Based Bid Adjustment (Quick Win)

Enhance existing `mart_fasa_targets` with league context and market-adjusted bids:

```sql
-- Add to mart_fasa_targets.sql after line 186 (value_score calculation)

-- League context (compare to rostered players)
league_context AS (
    SELECT
        position,
        median_starter_ppg,
        median_flex_ppg,
        replacement_level_ppg,
        COUNT(*) as total_rostered
    FROM {{ ref('mart_league_roster_depth') }}
    GROUP BY 1, 2, 3, 4
),

-- Market intelligence (recent FA acquisitions)
recent_market AS (
    SELECT
        position,
        season_phase,
        AVG(bid_amount) as avg_recent_bid,
        AVG(dollars_per_ppg) as market_efficiency
    FROM {{ ref('mart_fa_acquisition_history') }}
    WHERE transaction_date >= CURRENT_DATE - INTERVAL '60 days'
    GROUP BY 1, 2
)

-- Then in final SELECT, add:
LEFT JOIN league_context lc ON fa.position = lc.position
LEFT JOIN recent_market rm ON fa.position = rm.position
    AND CASE
        WHEN current_week <= 4 THEN 'Early Season'
        WHEN current_week BETWEEN 5 AND 12 THEN 'Mid Season'
        ELSE 'Late Season'
    END = rm.season_phase

-- Add columns:
    -- League VoR (true replacement level)
    proj.projected_ppg_ros - lc.replacement_level_ppg AS pts_above_league_replacement,
    proj.projected_ppg_ros - lc.median_starter_ppg AS pts_vs_median_starter,

    -- Hypothetical league rank if rostered
    (SELECT COUNT(*) + 1
     FROM {{ ref('mart_league_roster_depth') }} lrd
     WHERE lrd.position = fa.position
       AND lrd.projected_ppg_ros > proj.projected_ppg_ros
    ) AS hypothetical_league_rank,

    -- Market-adjusted bid (combine heuristic with market data)
    CASE
        WHEN rm.market_efficiency IS NOT NULL
            THEN ROUND(proj.projected_ppg_ros * rm.market_efficiency, 0)
        ELSE
            -- Fallback to heuristic
            CASE
                WHEN fa.position = 'RB' THEN ROUND(proj.projected_total_ros / 10, 0)
                WHEN fa.position = 'WR' THEN ROUND(proj.projected_total_ros / 12, 0)
                WHEN fa.position = 'TE' THEN ROUND(proj.projected_total_ros / 15, 0)
                ELSE 1
            END
    END AS suggested_bid_1yr_v2,

    -- Bid confidence (enhanced with market data)
    CASE
        WHEN rs.fantasy_ppg_last_4 IS NOT NULL
            AND opp.opportunity_share_l4 > 0.15
            AND proj.projected_ppg_ros > lc.median_flex_ppg  -- League context
            AND rm.avg_recent_bid IS NOT NULL  -- Market data available
        THEN 'HIGH'
        WHEN proj.projected_ppg_ros > lc.replacement_level_ppg
            AND rm.avg_recent_bid IS NOT NULL
        THEN 'MEDIUM'
        ELSE 'LOW'
    END AS bid_confidence_v2,
```

### Option B: Python Regression Model (Advanced)

If time permits after Option A:

**File:** `src/ff_analytics_utils/models/fa_bid_predictor.py`

```python
"""FA bid prediction model using sklearn."""

import duckdb
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
import pickle

def train_bid_model(duckdb_path: str) -> RandomForestRegressor:
    """Train model on historical FA acquisitions."""

    conn = duckdb.connect(duckdb_path, read_only=True)

    # Load training data
    df = conn.execute("""
        SELECT
            position,
            fantasy_ppg_l4_before_signing,
            fantasy_ppg_season_before_signing,
            touches_per_game_l4,
            quality_fas_available,
            market_depth_ratio,
            season_phase,
            bid_amount  -- target variable
        FROM main.mart_fa_acquisition_history
        WHERE bid_amount IS NOT NULL
          AND fantasy_ppg_l4_before_signing IS NOT NULL
    """).df()

    conn.close()

    # One-hot encode categoricals
    df = pd.get_dummies(df, columns=['position', 'season_phase'])

    # Split
    X = df.drop('bid_amount', axis=1)
    y = df['bid_amount']
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Train
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)

    # Evaluate
    score = model.score(X_test, y_test)
    print(f"Model R²: {score:.3f}")

    return model

def save_model(model, path='models/fa_bid_predictor.pkl'):
    """Save trained model to disk."""
    with open(path, 'wb') as f:
        pickle.dump(model, f)

if __name__ == '__main__':
    import sys
    duckdb_path = sys.argv[1] if len(sys.argv) > 1 else 'dbt/ff_analytics/target/dev.duckdb'

    model = train_bid_model(duckdb_path)
    save_model(model)
    print("✅ Model saved to models/fa_bid_predictor.pkl")
```

______________________________________________________________________

## Implementation Steps

### Phase 1: SQL Enhancement (Required)

1. Update `mart_fasa_targets.sql` with league context CTEs
2. Add new columns: `pts_above_league_replacement`, `hypothetical_league_rank`, `suggested_bid_1yr_v2`
3. Update `_mart_fasa_targets.yml` documentation
4. Run: `make dbt-run MODELS=mart_fasa_targets`
5. Run: `make dbt-test MODELS=mart_fasa_targets`
6. Regenerate notebook to verify new columns

### Phase 2: Python Model (Optional)

1. Create `src/ff_analytics_utils/models/fa_bid_predictor.py`
2. Train model: `uv run python -m src.ff_analytics_utils.models.fa_bid_predictor dbt/ff_analytics/target/dev.duckdb`
3. Use model predictions in notebook (Python layer)

______________________________________________________________________

## Success Criteria

- ✅ `mart_fasa_targets` includes league VoR columns
- ✅ Bid recommendations adjusted for market efficiency
- ✅ Hypothetical league rank calculated for all FAs
- ✅ Tests pass
- ✅ Notebook displays enhanced metrics

**Optional (Python model):**
- ✅ Model trains with R² > 0.6
- ✅ Predictions reasonable (no negative bids)
- ✅ Model saved to `models/fa_bid_predictor.pkl`

______________________________________________________________________

## Validation Commands

```bash
# Rebuild enhanced mart
make dbt-run MODELS=mart_fasa_targets

# Test
make dbt-test MODELS=mart_fasa_targets

# Inspect new columns
EXTERNAL_ROOT="$PWD/data/raw" duckdb dbt/ff_analytics/target/dev.duckdb -c "
SELECT player_name, position,
       projected_ppg_ros,
       pts_above_league_replacement,
       hypothetical_league_rank,
       suggested_bid_1yr AS old_bid,
       suggested_bid_1yr_v2 AS market_bid
FROM read_parquet('data/raw/marts/mart_fasa_targets/dt=*/data.parquet')
WHERE position = 'RB'
ORDER BY value_score DESC
LIMIT 10;
"
```

______________________________________________________________________

## Commit Message

```
feat: enhance FASA targets with league VoR and market bids

Improvements to mart_fasa_targets:
1. True value over replacement (vs league median, not just FAs)
2. Hypothetical league ranking if rostered
3. Market-adjusted bid suggestions using recent acquisition history
4. Enhanced bid confidence with market context

Replaces simple heuristics with data-driven intelligence.

Part of Sprint 1 Phase 2 enhancements.
Closes #XX
```

______________________________________________________________________

## Expected Impact

**Before (Heuristic):**
```
Zonovan Knight (RB)
- Projected: 11.1 PPG ROS
- Suggested bid: $11 (total/10)
- Replacement: 2.5 PPG (FA pool 25th %ile)
- Value above replacement: +8.6 PPG
```

**After (Enhanced):**
```
Zonovan Knight (RB)
- Projected: 11.1 PPG ROS
- League context: Would rank RB8 (top 20%)
- Points above league replacement: +2.6 PPG (vs median RB2: 8.5 PPG)
- Market bid: $14 (based on recent RB signings 8-12 PPG tier)
- Confidence: HIGH (market data + performance + opportunity)
```

More accurate bid guidance grounded in league reality and market behavior.
