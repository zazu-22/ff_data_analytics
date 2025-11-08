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

- [ ] Locate `stg_nflverse__player_stats.sql` model
- [ ] Replace hardcoded `dt IN ('2025-10-01', '2025-10-27')` with macro call
- [ ] Configure macro parameters:
  - [ ] Use `baseline_plus_latest` strategy
  - [ ] Set baseline_dt using fallback pattern: `var('NFLVERSE_WEEKLY_BASELINE_DT', var('NFLVERSE_BASELINE_DT', '2025-10-01'))`
  - [ ] Pass RAW_NFLVERSE_WEEKLY_GLOB env var for source_glob
  - [ ] Document baseline date choice and rationale
- [ ] Test compilation: `uv run dbt compile --select stg_nflverse__player_stats`
- [ ] Test execution: `uv run dbt run --select stg_nflverse__player_stats`
- [ ] Verify row counts match pre-change baseline

## Acceptance Criteria

- [ ] Hardcoded `dt IN (...)` filter removed from model
- [ ] `snapshot_selection_strategy` macro call added with correct parameters
- [ ] Model compiles successfully
- [ ] Model executes successfully
- [ ] Row counts match baseline (comparison test passes)

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

## References

- Plan: `../2025-11-07_plan_v_2_0.md` - Design Decision #1, Usage Example (lines 67-82)
- Checklist: `../2025-11-07_tasks_checklist_v_2_0.md` - Phase 1 Staging Updates (lines 42-45)
- Model file: `dbt/ff_data_transform/models/staging/nflverse/stg_nflverse__player_stats.sql`
