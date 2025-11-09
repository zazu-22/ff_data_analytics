# Ticket P1-004: Update stg_nflverse\_\_ff_opportunity to Use New Macro

**Phase**: 1 - Foundation\
**Estimated Effort**: Small (1-2 hours)\
**Dependencies**: P1-001 (snapshot_selection_strategy macro must exist)

## Objective

Update `stg_nflverse__ff_opportunity` to use the new `snapshot_selection_strategy` macro for consistency with other NFLverse models, replacing the direct `latest_snapshot_only()` helper call.

## Context

The `stg_nflverse__ff_opportunity` model currently uses the `latest_snapshot_only()` helper directly. For **consistency** with player_stats and snap_counts models, we're updating it to use the new `snapshot_selection_strategy` macro with `latest_only` strategy.

**Why this change**:

1. **Consistency**: All NFLverse staging models should use the same snapshot selection pattern
2. **Clear intent**: Strategy explicitly named in code (`strategy='latest_only'`)
3. **Future-proof**: Easy to change strategy later if needed
4. **Easier to audit**: Searching for `snapshot_selection_strategy` finds all snapshot logic

This model tracks fantasy-relevant opportunities (targets, carries, red zone touches) and only needs the latest snapshot since it's purely for current-season analysis.

## Tasks

- [x] Locate `stg_nflverse__ff_opportunity.sql` model
- [x] Replace `{{ latest_snapshot_only(glob) }}` with `snapshot_selection_strategy` macro call
- [x] Configure macro parameters:
  - [x] Use `latest_only` strategy (no baseline needed)
  - [x] Pass RAW_NFLVERSE_FF_OPPORTUNITY_GLOB env var for source_glob
- [x] Test compilation: `uv run dbt compile --select stg_nflverse__ff_opportunity`
- [x] Test execution: `uv run dbt run --select stg_nflverse__ff_opportunity`
- [x] Verify row counts match pre-change baseline
- [x] Document that all three NFLverse models now use consistent pattern

## Acceptance Criteria

- [x] Hardcoded `latest_snapshot_only()` call replaced with `snapshot_selection_strategy` macro
- [x] Model compilation succeeds with no errors
- [x] Model execution succeeds with no errors
- [x] Row counts match pre-change baseline
- [x] Consistent pattern across all three NFLverse staging models documented

## Implementation Notes

**File**: `dbt/ff_data_transform/models/staging/nflverse/stg_nflverse__ff_opportunity.sql`

**Change Pattern**:

```sql
-- BEFORE:
with source as (
  select * from read_parquet(
    '{{ env_var("RAW_NFLVERSE_FF_OPPORTUNITY_GLOB", "data/raw/nflverse/ff_opportunity/dt=*/*.parquet") }}'
  )
  where {{ latest_snapshot_only(
    env_var("RAW_NFLVERSE_FF_OPPORTUNITY_GLOB", "data/raw/nflverse/ff_opportunity/dt=*/*.parquet")
  ) }}
)

-- AFTER:
with source as (
  select * from read_parquet(
    '{{ env_var("RAW_NFLVERSE_FF_OPPORTUNITY_GLOB", "data/raw/nflverse/ff_opportunity/dt=*/*.parquet") }}'
  )
  where 1=1
    {{ snapshot_selection_strategy(
        env_var("RAW_NFLVERSE_FF_OPPORTUNITY_GLOB", "data/raw/nflverse/ff_opportunity/dt=*/*.parquet"),
        strategy='latest_only'
    ) }}
)
```

**Configuration**:

- Strategy: `latest_only` (no baseline needed for current-season analysis)
- Source glob: From `RAW_NFLVERSE_FF_OPPORTUNITY_GLOB` env var

**Rationale for Change**:

While the existing `latest_snapshot_only()` helper works fine, updating to the new macro provides:

1. **Pattern consistency** across all three NFLverse models
2. **Explicit strategy naming** makes intent clear
3. **Uniform approach** for easier maintenance and auditing

## Testing

1. **Compilation test**:

   ```bash
   cd dbt/ff_data_transform
   uv run dbt compile --select stg_nflverse__ff_opportunity
   ```

2. **Execution test**:

   ```bash
   uv run dbt run --select stg_nflverse__ff_opportunity
   ```

3. **Row count comparison**:

   ```sql
   SELECT COUNT(*) FROM stg_nflverse__ff_opportunity;
   ```

4. **Verify snapshot date**:

   ```sql
   SELECT DISTINCT dt FROM stg_nflverse__ff_opportunity ORDER BY dt;
   -- Should show only the latest snapshot date
   ```

5. **Check macro resolution in compiled SQL**:

   ```bash
   cat target/compiled/ff_data_transform/models/staging/nflverse/stg_nflverse__ff_opportunity.sql
   # Verify the dt filter looks correct
   ```

## Implementation Summary

**Completed**: 2025-11-09\
**Commit**: `34eda40` - feat(snapshot): implement P1-004 - stg_nflverse\_\_ff_opportunity

### What Was Delivered

1. **Model Updated**: `dbt/ff_data_transform/models/staging/stg_nflverse__ff_opportunity.sql`

   - Replaced `latest_snapshot_only()` helper with `snapshot_selection_strategy` macro
   - Uses `latest_only` strategy for current-season analysis
   - Achieves consistency across all NFLverse staging models

2. **Testing Results**:

   - Compilation: PASS
   - Execution: PASS (view created successfully)
   - Row count: 84,576 stat records
   - Snapshot selection: Latest (2025-11-05) automatically detected
   - Season coverage: 2025 weeks 1-9 only (latest_only strategy confirmed)

3. **Coverage Verification**:

   - 2025: 9 weeks (492 unique players, 84,576 records)
   - ~38 stat types per player/game (expected, variance, air yards, team shares)

4. **Benefits Achieved**:

   - Consistent pattern with player_stats and snap_counts models
   - Explicit strategy naming makes intent clear ('latest_only')
   - Easier to audit (all models use snapshot_selection_strategy)
   - Future-proof (easy to change strategy if needed)

5. **Tracking Updated**:

   - `00-OVERVIEW.md`: 7/49 tickets complete (14%)
   - `tasks_checklist_v_2_0.md`: stg_nflverse\_\_ff_opportunity complete
   - All 3 NFLverse models (P1-002, P1-003, P1-004) now use consistent snapshot governance pattern

**Status**: COMPLETE - Third NFLverse staging model successfully migrated

## References

- Plan: `../2025-11-07_plan_v_2_0.md` - dbt Models section (lines 30-34)
- Checklist: `../2025-11-07_tasks_checklist_v_2_0.md` - Phase 1 Staging Updates (lines 50-52)
- Model file: `dbt/ff_data_transform/models/staging/nflverse/stg_nflverse__ff_opportunity.sql`
- Existing macro: `dbt/ff_data_transform/macros/get_latest_snapshot.sql`
