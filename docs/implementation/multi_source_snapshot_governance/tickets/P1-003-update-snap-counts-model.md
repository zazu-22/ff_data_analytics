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

- [ ] Locate `stg_nflverse__snap_counts.sql` model
- [ ] Replace hardcoded `dt IN ('2025-10-01', '2025-10-28')` with macro call
- [ ] Configure macro parameters:
  - [ ] Use `baseline_plus_latest` strategy
  - [ ] Set baseline_dt using fallback pattern: `var('NFLVERSE_SNAP_BASELINE_DT', var('NFLVERSE_BASELINE_DT', '2025-10-01'))`
  - [ ] Pass RAW_NFLVERSE_SNAP_COUNTS_GLOB env var for source_glob
  - [ ] Document baseline date choice and rationale
- [ ] Test compilation: `uv run dbt compile --select stg_nflverse__snap_counts`
- [ ] Test execution: `uv run dbt run --select stg_nflverse__snap_counts`
- [ ] Verify row counts match pre-change baseline

## Acceptance Criteria

- [ ] Hardcoded `dt IN (...)` filter removed from model
- [ ] `snapshot_selection_strategy` macro call added with correct parameters
- [ ] Model compiles successfully
- [ ] Model executes successfully
- [ ] Row counts match baseline (comparison test passes)

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

## References

- Plan: `../2025-11-07_plan_v_2_0.md` - dbt Models section (lines 30-34)
- Checklist: `../2025-11-07_tasks_checklist_v_2_0.md` - Phase 1 Staging Updates (lines 46-49)
- Model file: `dbt/ff_data_transform/models/staging/nflverse/stg_nflverse__snap_counts.sql`
