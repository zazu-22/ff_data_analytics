# Task 1.3: FASA Target Mart

**Sprint:** Sprint 1 - FASA Optimization & Trade Intelligence
**Phase:** Phase 1 - Critical Path for Wednesday FASA
**Estimated Duration:** 8 hours
**Priority:** CRITICAL (blocks FASA notebook)

______________________________________________________________________

## Objective

Create `mart_fasa_targets` and `mart_my_roster_droppable` dbt models to score every free agent and identify drop candidates for FASA bid planning.

______________________________________________________________________

## Context

**Why this task matters:**

- FASA notebook needs scored/ranked FAs to recommend bids
- Need to identify which rostered players to drop if cap space needed
- Combines performance, projections, opportunity, and market data

**Dependencies:**

- ✅ Task 1.2 complete (`stg_sleeper__fa_pool` exists)
- ✅ `fact_player_stats`, `mart_fantasy_actuals_weekly` exist
- ✅ `mart_fantasy_projections` exists
- ✅ `fact_asset_market_values` (KTC) exists
- ✅ `dim_player_id_xref` exists

______________________________________________________________________

## Files to Create

### 1. `dbt/ff_data_transform/models/marts/mart_fasa_targets.sql`

**Full SQL:** See `00_SPRINT_PLAN.md` lines 476-687 for complete implementation

**Key features:**

- Score every FA with `value_score` (0-100 composite)
- Calculate bid recommendations (1yr, 2yr, 3yr)
- Priority rankings overall and by position
- Recent performance (last 3/4/8 games)
- Rest of season projections
- Opportunity metrics (snap/target share)
- KTC market values

**Grain:** `player_key, asof_date, week`

### 2. `dbt/ff_data_transform/models/marts/mart_fasa_targets.yml`

Include tests:

- Unique: `player_key, asof_date`
- Not null: `player_key, position, value_score`
- Accepted values: `position IN ('QB', 'RB', 'WR', 'TE')`
- Accepted values: `bid_confidence IN ('HIGH', 'MEDIUM', 'LOW')`
- Range: `value_score BETWEEN 0 AND 100`

### 3. `dbt/ff_data_transform/models/marts/mart_my_roster_droppable.sql`

**Full SQL:** See `00_SPRINT_PLAN.md` lines 689-834 for complete implementation

**Key features:**

- Jason's 25 rostered players
- Dead cap if cut (using dim_cut_liability_schedule)
- Cap space freed calculations
- Droppable score (0-100)
- Drop recommendations

**Grain:** `player_key, asof_date`

### 4. `dbt/ff_data_transform/models/marts/mart_my_roster_droppable.yml`

Include tests:

- Unique: `player_key, asof_date`
- Not null: `player_key, position, droppable_score`
- Accepted values: `drop_recommendation IN ('KEEP', 'REVIEW', 'DROP_FOR_CAP', 'DROP_FOR_UPSIDE')`
- Range: `droppable_score BETWEEN 0 AND 100`

______________________________________________________________________

## Implementation Steps

1. Copy SQL from sprint plan (`00_SPRINT_PLAN.md`)
2. Create `mart_fasa_targets.sql` and `.yml`
3. Create `mart_my_roster_droppable.sql` and `.yml`
4. Run dbt: `make dbt-run --select mart_fasa_targets mart_my_roster_droppable`
5. Run tests: `make dbt-test --select mart_fasa_targets mart_my_roster_droppable`

______________________________________________________________________

## Success Criteria

- ✅ `mart_fasa_targets`: 500-800 FAs scored
- ✅ `mart_my_roster_droppable`: ~25 players (Jason's roster)
- ✅ All tests passing
- ✅ RB rankings sensible (known starters ranked higher)
- ✅ Bid recommendations reasonable ($1-50 range)

______________________________________________________________________

## Validation Commands

```bash
export EXTERNAL_ROOT="$PWD/data/raw"

# Run models
make dbt-run --select mart_fasa_targets mart_my_roster_droppable

# Run tests
make dbt-test --select mart_fasa_targets mart_my_roster_droppable

# Inspect results
dbt show --select mart_fasa_targets --where "position = 'RB'" --limit 10
dbt show --select mart_my_roster_droppable --where "droppable_score > 50"

# Check counts
duckdb data/ff_analytics.duckdb "SELECT COUNT(*) FROM mart_fasa_targets"
duckdb data/ff_analytics.duckdb "SELECT COUNT(*) FROM mart_my_roster_droppable"

# Code quality
make sqlcheck
```

______________________________________________________________________

## Commit Message

```
feat: add FASA target mart and droppable roster analysis

Create marts for FASA bid planning:
- mart_fasa_targets: Score 500-800 FAs with value_score, bid recommendations
- mart_my_roster_droppable: Jason's roster with drop candidates and cap impact

Enables Wednesday FASA notebook to recommend RB/WR/TE bids and drop scenarios.

Resolves: Sprint 1 Task 1.3
```
