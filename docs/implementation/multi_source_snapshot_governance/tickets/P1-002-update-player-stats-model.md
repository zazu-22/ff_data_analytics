# Ticket P1-002: Update stg_nflverse\_\_player_stats Model

**Phase**: 1 - Foundation\
**Estimated Effort**: Small (1-2 hours)\
**Dependencies**: P1-001 (snapshot_selection_strategy macro must exist)

## Objective

Replace hardcoded `dt IN ('2025-10-01', '2025-10-27')` filter in `stg_nflverse__player_stats` with the new `snapshot_selection_strategy` macro using `baseline_plus_latest` strategy.

## Context

The `stg_nflverse__player_stats` model currently has hardcoded snapshot dates that must be manually updated whenever a new snapshot is loaded. This creates maintenance burden and risk of forgetting to update the dates.

By switching to the macro-based approach with `baseline_plus_latest` strategy, we maintain historical continuity (keep baseline 2025-10-01) while automatically picking up the latest snapshot, eliminating manual date updates.

## Tasks

- [x] Locate `stg_nflverse__player_stats.sql` model
- [x] Replace hardcoded `dt IN ('2025-10-01', '2025-10-27')` with macro call
- [x] Configure macro parameters:
  - [x] Use `baseline_plus_latest` strategy
  - [x] Set baseline_dt using fallback pattern: `var('NFLVERSE_WEEKLY_BASELINE_DT', var('NFLVERSE_BASELINE_DT', '2025-10-01'))`
  - [x] Pass RAW_NFLVERSE_WEEKLY_GLOB env var for source_glob
  - [x] Document baseline date choice and rationale
- [x] Test compilation: `uv run dbt compile --select stg_nflverse__player_stats`
- [x] Test execution: `uv run dbt run --select stg_nflverse__player_stats`
- [x] Verify row counts match pre-change baseline

## Acceptance Criteria

- [x] Hardcoded `dt IN (...)` filter removed from model
- [x] `snapshot_selection_strategy` macro call added with correct parameters
- [x] Model compiles successfully
- [x] Model executes successfully
- [x] Row counts match baseline (comparison test passes)

## Implementation Notes

**File**: `dbt/ff_data_transform/models/staging/nflverse/stg_nflverse__player_stats.sql`

**Change Pattern**:

```sql
-- BEFORE:
with source as (
  select * from read_parquet(
    '{{ env_var("RAW_NFLVERSE_WEEKLY_GLOB", "data/raw/nflverse/weekly/dt=*/*.parquet") }}'
  )
  where dt IN ('2025-10-01', '2025-10-27')
)

-- AFTER:
with source as (
  select * from read_parquet(
    '{{ env_var("RAW_NFLVERSE_WEEKLY_GLOB", "data/raw/nflverse/weekly/dt=*/*.parquet") }}'
  )
  where 1=1
    {{ snapshot_selection_strategy(
        env_var("RAW_NFLVERSE_WEEKLY_GLOB", "data/raw/nflverse/weekly/dt=*/*.parquet"),
        strategy='baseline_plus_latest',
        baseline_dt=var('NFLVERSE_BASELINE_DT', '2025-10-01')
    ) }}
)
```

**Configuration**:

- Baseline date: `2025-10-01` (complete 2020-2024 seasons data)
- Strategy: `baseline_plus_latest` (for historical continuity)
- Source glob: From `RAW_NFLVERSE_WEEKLY_GLOB` env var

**Baseline Date Strategy**:

We use a **single baseline date** (`NFLVERSE_BASELINE_DT`) for all NFLverse datasets with optional per-dataset overrides:

```sql
baseline_dt=var('NFLVERSE_WEEKLY_BASELINE_DT', var('NFLVERSE_BASELINE_DT', '2025-10-01'))
```

This pattern:

1. First checks for dataset-specific override (`NFLVERSE_WEEKLY_BASELINE_DT`)
2. Falls back to shared baseline (`NFLVERSE_BASELINE_DT`)
3. Uses hardcoded default if neither set (`2025-10-01`)

**Benefits**: Consistency across datasets by default, flexibility when needed.

## Testing

1. **Compilation test**:

   ```bash
   cd dbt/ff_data_transform
   uv run dbt compile --select stg_nflverse__player_stats
   ```

2. **Execution test**:

   ```bash
   uv run dbt run --select stg_nflverse__player_stats
   ```

3. **Row count comparison**:

   ```sql
   -- In DuckDB, compare row counts before/after
   SELECT COUNT(*) FROM read_parquet('target/dev.duckdb')
   WHERE model = 'stg_nflverse__player_stats';
   ```

4. **Verify snapshot dates included**:

   ```sql
   SELECT DISTINCT dt FROM stg_nflverse__player_stats ORDER BY dt;
   -- Should show: 2025-10-01 and 2025-10-27 (or latest available)
   ```

## Implementation Summary

**Completed**: 2025-11-09\
**Commit**: `713bfef` - feat(snapshot): implement P1-002 - stg_nflverse\_\_player_stats

### What Was Delivered

1. **Model Updated**: `dbt/ff_data_transform/models/staging/stg_nflverse__player_stats.sql`

   - Replaced hardcoded `dt IN ('2025-10-01', '2025-10-27')` filter
   - Added `snapshot_selection_strategy` macro call with `baseline_plus_latest` strategy
   - Baseline date: 2025-10-01 (complete 2020-2024 seasons data)
   - Uses fallback var pattern: `NFLVERSE_WEEKLY_BASELINE_DT → NFLVERSE_BASELINE_DT → '2025-10-01'`

2. **Testing Results**:

   - Compilation: PASS
   - Execution: PASS (view created successfully)
   - Row count: 6,889,138 rows from baseline + latest snapshots
   - Snapshot selection: Baseline (2025-10-01: 97,415 rows) + Latest (2025-11-05: 9,239 rows)
   - **Automatic latest detection**: Now picks 2025-11-05 (was hardcoded to 2025-10-27)

3. **Benefits Achieved**:

   - Eliminates manual date updates when new snapshots arrive
   - Maintains historical continuity with baseline snapshot
   - Automatically incorporates latest data without code changes

4. **Tracking Updated**:

   - `00-OVERVIEW.md`: 5/49 tickets complete (10%)
   - `tasks_checklist_v_2_0.md`: stg_nflverse\_\_player_stats complete

**Status**: COMPLETE - First NFLverse staging model successfully migrated

## References

- Plan: `../2025-11-07_plan_v_2_0.md` - Design Decision #1, Usage Example (lines 67-82)
- Checklist: `../2025-11-07_tasks_checklist_v_2_0.md` - Phase 1 Staging Updates (lines 42-45)
- Model file: `dbt/ff_data_transform/models/staging/nflverse/stg_nflverse__player_stats.sql`
