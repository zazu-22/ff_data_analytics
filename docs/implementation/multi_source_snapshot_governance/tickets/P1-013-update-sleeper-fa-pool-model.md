# Ticket P1-013: Update stg_sleeper\_\_fa_pool Model

**Phase**: 1 - Foundation\
**Estimated Effort**: Small (1-2 hours)\
**Dependencies**: P1-001 (snapshot_selection_strategy macro must exist)\
**Priority**: ⚠️ **HIGH** - Fixes 1,893 duplicates in `mrt_fasa_targets`

## Objective

Replace `dt=*` wildcard pattern in `stg_sleeper__fa_pool` with the new `snapshot_selection_strategy` macro using `latest_only` strategy.

## Context

The `stg_sleeper__fa_pool` model currently reads all snapshots using `dt=*` pattern, causing **1,893 duplicate rows** in the downstream `mrt_fasa_targets` mart due to multiple snapshot dates being read for the same player.

**Test Failure**:

```
dbt_utils_unique_combination_of_columns_mrt_fasa_targets_player_id__asof_date
Got 1893 results, configured to fail if != 0
```

**Root Cause**: Line in `stg_sleeper__fa_pool.sql` reading from `dt=*/` without filtering to latest snapshot.

This is the **highest impact fix** in Phase 1, affecting a critical analytics mart used for free agent acquisition analysis.

## Tasks

- [ ] Locate `stg_sleeper__fa_pool.sql` model
- [ ] Find the `read_parquet()` call with `dt=*` pattern
- [ ] Replace with `snapshot_selection_strategy` macro call
- [ ] Configure macro parameters:
  - [ ] Use `latest_only` strategy (Sleeper data is daily, only latest needed)
  - [ ] Pass source glob path to macro
- [ ] Test compilation: `make dbt-run --select stg_sleeper__fa_pool`
- [ ] Test execution and verify row counts
- [ ] **Verify duplicate fix**: Run `make dbt-test --select mrt_fasa_targets` (expect 1,893 duplicates → 0)

## Acceptance Criteria

- [ ] `dt=*` pattern removed from model
- [ ] `snapshot_selection_strategy` macro call added with `latest_only` strategy
- [ ] Model compiles successfully
- [ ] Model executes successfully
- [ ] **Critical**: `mrt_fasa_targets` grain test passes (0 duplicates)

## Implementation Notes

**File**: `dbt/ff_data_transform/models/staging/stg_sleeper__fa_pool.sql`

**Change Pattern**:

```sql
-- BEFORE:
with source as (
  select * from read_parquet(
    'data/raw/sleeper/fa_pool/dt=*/*.parquet',
    hive_partitioning = true
  )
)

-- AFTER:
with source as (
  select * from read_parquet(
    'data/raw/sleeper/fa_pool/dt=*/*.parquet',
    hive_partitioning = true
  )
  where 1=1
    {{ snapshot_selection_strategy(
        'data/raw/sleeper/fa_pool/dt=*/*.parquet',
        strategy='latest_only'
    ) }}
)
```

**Configuration**:

- Strategy: `latest_only` (Sleeper FA pool is daily snapshot, only latest relevant)
- No baseline needed (latest is sufficient for current FA analysis)

**Why `latest_only`**:

Sleeper free agent pool is a **point-in-time snapshot** of available players. Historical snapshots are not needed for:

- Current FASA target scoring
- Bid recommendations
- League context analysis

All downstream marts (`mrt_fasa_targets`) expect a single snapshot date per analysis run.

## Testing

1. **Compilation test**:

   ```bash
   make dbt-run --select stg_sleeper__fa_pool
   ```

2. **Verify snapshot filtering**:

   ```bash
   EXTERNAL_ROOT="$PWD/data/raw" duckdb "$PWD/dbt/ff_data_transform/target/dev.duckdb" -c \
     "SELECT DISTINCT dt FROM main.stg_sleeper__fa_pool ORDER BY dt DESC;"
   # Should show only 1 date (latest)
   ```

3. **Verify duplicate fix**:

   ```bash
   make dbt-test --select mrt_fasa_targets
   # Expect: dbt_utils_unique_combination_of_columns test PASS (was 1,893 failures)
   ```

4. **Row count validation**:

   ```bash
   EXTERNAL_ROOT="$PWD/data/raw" duckdb "$PWD/dbt/ff_data_transform/target/dev.duckdb" -c \
     "SELECT COUNT(*) as total_players FROM main.stg_sleeper__fa_pool;"
   # Should match expected FA pool size for latest snapshot (typically 200-500 players)
   ```

## Impact

**Before Fix**:

- `stg_sleeper__fa_pool`: Reading N snapshots → N × player_count rows
- `mrt_fasa_targets`: 1,893 duplicate (player_id, asof_date) combinations

**After Fix**:

- `stg_sleeper__fa_pool`: Reading 1 snapshot → player_count rows
- `mrt_fasa_targets`: 0 duplicates ✅

**Downstream Models Fixed**:

- `mrt_fasa_targets` - Free agent acquisition targets mart

## References

- Plan: `../2025-11-07_plan_v_2_0.md` - Lines 46-47 (Sleeper models)
- Checklist: `../2025-11-07_tasks_checklist_v_2_0.md` - Lines 77-81 (Sleeper priority)
- Model file: `dbt/ff_data_transform/models/staging/stg_sleeper__fa_pool.sql`
- Downstream test: `dbt/ff_data_transform/models/marts/_mrt_fasa_targets.yml`
