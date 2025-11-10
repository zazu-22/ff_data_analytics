# Task 2.1: Historical Backfill

**Sprint:** Sprint 1
**Phase:** Phase 2
**Duration:** 8h
**Priority:** HIGH (blocks valuation model)

## Objective

Backfill nflverse data 2012-2024 for model training and aging curve analysis. This is required before Task 2.2 (Baseline Valuation Model) to ensure sufficient training data.

## Command

```bash
# Run in tmux/screen (takes hours)
for year in {2012..2024}; do
  uv run python scripts/ingest/load_nflverse.py \
    --seasons $year \
    --datasets weekly,snap_counts,ff_opportunity \
    --out data/raw/nflverse
done

# After complete, refresh dbt
export EXTERNAL_ROOT="$PWD/data/raw"
make dbt-run --full-refresh
```

## Success Criteria

- ✅ 2012-2024 data loaded
- ✅ `fact_player_stats` contains historical data

## Post-Backfill Validation

After completing this task, validate data coverage improvements in dependent marts:

**Expected Improvement: `mart_fa_acquisition_history`**
- Current coverage: 76.2% of FASA transactions have performance context
- Gap: 72/84 missing transactions (85%) are from 2019 signings (data starts 2020)
- After backfill: Coverage should improve to ~90% with 2012-2019 data
- Validation query:
  ```sql
  SELECT
      COUNT(*) as total,
      COUNT(fantasy_ppg_l4_games) as with_performance,
      ROUND(100.0 * COUNT(fantasy_ppg_l4_games) / COUNT(*), 1) as pct_coverage
  FROM main.mart_fa_acquisition_history;
  ```
- Target: >90% coverage (from current 76.2%)

## Commit

```
feat: backfill historical nflverse data (2012-2024)

Load 13 seasons of historical data required for valuation model training.
Enables aging curve analysis and improved predictions.

Resolves: Sprint 1 Task 2.1
```
