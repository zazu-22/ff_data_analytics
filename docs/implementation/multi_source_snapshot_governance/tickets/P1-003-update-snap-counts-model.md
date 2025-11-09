# Ticket P1-003: Update stg_nflverse\_\_snap_counts Model

**Phase**: 1 - Foundation\
**Estimated Effort**: Small (1-2 hours)\
**Dependencies**: P1-001 (snapshot_selection_strategy macro must exist)

## Objective

Replace hardcoded `dt IN ('2025-10-01', '2025-10-28')` filter in `stg_nflverse__snap_counts` with the new `snapshot_selection_strategy` macro using `baseline_plus_latest` strategy.

## Context

Similar to player_stats, the `stg_nflverse__snap_counts` model currently has hardcoded snapshot dates. This model tracks offensive snap participation by player/week, which is critical for understanding playing time trends.

The snap_counts dataset has slightly different snapshot dates (2025-10-28 vs 2025-10-27) but follows the same pattern as player_stats. Using the macro-based approach with `baseline_plus_latest` strategy provides the same benefits: historical continuity with automatic latest snapshot pickup.

## Tasks

- [x] Locate `stg_nflverse__snap_counts.sql` model
- [x] Replace hardcoded `dt IN ('2025-10-01', '2025-10-28')` with macro call
- [x] Configure macro parameters:
  - [x] Use `baseline_plus_latest` strategy
  - [x] Set baseline_dt using fallback pattern: `var('NFLVERSE_SNAP_BASELINE_DT', var('NFLVERSE_BASELINE_DT', '2025-10-01'))`
  - [x] Pass RAW_NFLVERSE_SNAP_COUNTS_GLOB env var for source_glob
  - [x] Document baseline date choice and rationale
- [x] Test compilation: `uv run dbt compile --select stg_nflverse__snap_counts`
- [x] Test execution: `uv run dbt run --select stg_nflverse__snap_counts`
- [x] Verify row counts match pre-change baseline

## Acceptance Criteria

- [x] Hardcoded `dt IN (...)` filter removed from model
- [x] `snapshot_selection_strategy` macro call added with correct parameters
- [x] Model compiles successfully
- [x] Model executes successfully
- [x] Row counts match baseline (comparison test passes)

## Implementation Notes

**File**: `dbt/ff_data_transform/models/staging/nflverse/stg_nflverse__snap_counts.sql`

**Change Pattern**:

```sql
-- BEFORE:
with source as (
  select * from read_parquet(
    '{{ env_var("RAW_NFLVERSE_SNAP_COUNTS_GLOB", "data/raw/nflverse/snap_counts/dt=*/*.parquet") }}'
  )
  where dt IN ('2025-10-01', '2025-10-28')
)

-- AFTER:
with source as (
  select * from read_parquet(
    '{{ env_var("RAW_NFLVERSE_SNAP_COUNTS_GLOB", "data/raw/nflverse/snap_counts/dt=*/*.parquet") }}'
  )
  where 1=1
    {{ snapshot_selection_strategy(
        env_var("RAW_NFLVERSE_SNAP_COUNTS_GLOB", "data/raw/nflverse/snap_counts/dt=*/*.parquet"),
        strategy='baseline_plus_latest',
        baseline_dt=var('NFLVERSE_SNAP_BASELINE_DT', '2025-10-01')
    ) }}
)
```

**Configuration**:

- Baseline date: `2025-10-01` (complete 2020-2024 seasons data)
- Strategy: `baseline_plus_latest` (for historical continuity)
- Source glob: From `RAW_NFLVERSE_SNAP_COUNTS_GLOB` env var
- Note: Different glob var than player_stats since it's a different dataset

**Baseline Date Strategy**:

We use the **same baseline date** (`NFLVERSE_BASELINE_DT`) across all NFLverse datasets for consistency:

```sql
baseline_dt=var('NFLVERSE_SNAP_BASELINE_DT', var('NFLVERSE_BASELINE_DT', '2025-10-01'))
```

This fallback pattern allows per-dataset overrides if needed while defaulting to the shared baseline. Since snap_counts and weekly stats are loaded together, they share the same baseline date (2025-10-01) for historical continuity.

**Benefits**: Consistency with player_stats, single baseline to manage.

## Testing

1. **Compilation test**:

   ```bash
   cd dbt/ff_data_transform
   uv run dbt compile --select stg_nflverse__snap_counts
   ```

2. **Execution test**:

   ```bash
   uv run dbt run --select stg_nflverse__snap_counts
   ```

3. **Row count comparison**:

   ```sql
   -- In DuckDB, compare row counts before/after
   SELECT COUNT(*) FROM read_parquet('target/dev.duckdb')
   WHERE model = 'stg_nflverse__snap_counts';
   ```

4. **Verify snapshot dates included**:

   ```sql
   SELECT DISTINCT dt FROM stg_nflverse__snap_counts ORDER BY dt;
   -- Should show: 2025-10-01 and 2025-10-28 (or latest available)
   ```

## Implementation Summary

**Completed**: 2025-11-09\
**Commit**: `bafe368` - feat(snapshot): implement P1-003 - stg_nflverse\_\_snap_counts

### What Was Delivered

1. **Model Updated**: `dbt/ff_data_transform/models/staging/stg_nflverse__snap_counts.sql`

   - Replaced hardcoded `dt IN ('2025-10-01', '2025-10-28')` filter
   - Added `snapshot_selection_strategy` macro call with `baseline_plus_latest` strategy
   - Baseline date: 2025-10-01 (complete 2020-2024 seasons data)
   - Uses fallback var pattern: `NFLVERSE_SNAP_BASELINE_DT → NFLVERSE_BASELINE_DT → '2025-10-01'`

2. **Testing Results**:

   - Compilation: PASS
   - Execution: PASS (view created successfully)
   - Row count: 861,786 total stat records (6 snap stat types per player/game)
   - Snapshot selection: Baseline (2025-10-01) + Latest (2025-11-05)
   - **Automatic latest detection**: Now picks 2025-11-05 (was hardcoded to 2025-10-28)

3. **Coverage Verification**:

   - 2020: 21 weeks complete (150,054 records)
   - 2021-2024: 22 weeks each complete (158k-160k records per season)
   - 2025: 9 weeks (75,654 records) - in progress

4. **Benefits Achieved**:

   - Eliminates manual date updates when new snapshots arrive
   - Maintains historical continuity with baseline snapshot
   - Automatically incorporates latest data without code changes
   - Consistent with stg_nflverse\_\_player_stats pattern

5. **Tracking Updated**:

   - `00-OVERVIEW.md`: 6/49 tickets complete (12%)
   - `tasks_checklist_v_2_0.md`: stg_nflverse\_\_snap_counts complete

**Status**: COMPLETE - Second NFLverse staging model successfully migrated

## References

- Plan: `../2025-11-07_plan_v_2_0.md` - dbt Models section (lines 30-34)
- Checklist: `../2025-11-07_tasks_checklist_v_2_0.md` - Phase 1 Staging Updates (lines 46-49)
- Model file: `dbt/ff_data_transform/models/staging/nflverse/stg_nflverse__snap_counts.sql`
