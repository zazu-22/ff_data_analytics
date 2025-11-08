# Task 2.2: Baseline Valuation Model

**Sprint:** Sprint 1 - FASA Optimization & Trade Intelligence
**Phase:** Phase 2 - Trade Intelligence
**Estimated Duration:** 8 hours
**Priority:** HIGH (blocks trade marts)

______________________________________________________________________

## Objective

Train linear regression model to predict player fair value, enabling buy-low/sell-high identification by comparing model_value to KTC market value.

______________________________________________________________________

## Context

**Why this task matters:**

- Identifies players undervalued by market (buy-low targets)
- Identifies players overvalued by market (sell-high opportunities)
- Data-driven trade negotiations

**Dependencies:**

- ✅ Task 2.1 complete: Historical backfill (2012-2024)
- ✅ `fact_player_stats` contains historical data (required for training)

______________________________________________________________________

## Files to Create

### 1. `dbt/ff_data_transform/models/marts/mart_player_features_historical.sql`

**Full SQL:** See `00_SPRINT_PLAN.md` lines 1087-1183

**Features:**

- Demographics: age, nfl_experience
- Performance: fantasy_ppg_rolling_3, fantasy_ppg_rolling_8
- Usage: carries, targets, snaps, touches
- Efficiency: ypc, ypr
- Team context: team_offense_rank
- Career stats: career_points_cumulative, career_games_played

**Grain:** `player_key, season, week`

### 2. `src/ff_analytics_utils/models/__init__.py`

```python
"""Machine learning models for player valuation."""
```

### 3. `src/ff_analytics_utils/models/player_valuation.py`

**Full implementation:** See `00_SPRINT_PLAN.md` lines 1187-1393

**Key functions:**

- `load_training_data()` - Load historical features
- `train_model()` - Train linear/ridge/lasso regression
- `save_model()` - Pickle model to disk
- `load_model()` - Load pickled model
- `predict_player_values()` - Generate predictions

**Target metric:**

- MAE < 5.0 points per week
- R² > 0.50

______________________________________________________________________

## Implementation Steps

1. Create feature mart SQL
2. Create Python model training script
3. Train model: `python -m src.ff_analytics_utils.models.player_valuation --train --save models/player_valuation_v1.pkl`
4. Validate metrics (MAE, R², RMSE)
5. Test predictions

______________________________________________________________________

## Success Criteria

- ✅ Feature mart builds successfully
- ✅ Model trains without errors
- ✅ MAE < 5.0
- ✅ R² > 0.50
- ✅ Model saved: `models/player_valuation_v1.pkl`
- ✅ Predictions reasonable (no negatives)

______________________________________________________________________

## Validation Commands

```bash
# Build feature mart
export EXTERNAL_ROOT="$PWD/data/raw"
make dbt-run --select mart_player_features_historical

# Train model
uv run python -m src.ff_analytics_utils.models.player_valuation \
  --train --save models/player_valuation_v1.pkl

# Test predictions
uv run python -m src.ff_analytics_utils.models.player_valuation \
  --predict --model models/player_valuation_v1.pkl

# Code quality
make lint
make typecheck
```

______________________________________________________________________

## Commit Message

```
feat: add baseline player valuation model

Train linear regression model to predict player fair value using:
- Historical performance features
- Usage and efficiency metrics
- Demographics and team context

Model achieves MAE < 5.0 and R² > 0.50, enabling buy-low/sell-high
identification by comparing model predictions to KTC market values.

Resolves: Sprint 1 Task 2.2
```
