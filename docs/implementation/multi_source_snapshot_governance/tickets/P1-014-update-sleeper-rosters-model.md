# Ticket P1-014: Update stg_sleeper\_\_rosters Model

**Phase**: 1 - Foundation\
**Status**: COMPLETE\
**Estimated Effort**: Small (1-2 hours)\
**Dependencies**: P1-001 (snapshot_selection_strategy macro must exist)

## Objective

Replace `dt=*` wildcard pattern in `stg_sleeper__rosters` with the new `snapshot_selection_strategy` macro using `latest_only` strategy.

## Context

The `stg_sleeper__rosters` model currently reads all snapshots using `dt=*` pattern from Sleeper API exports. This model contains current roster compositions (which players are on which franchise rosters) as reported by the Sleeper platform.

Sleeper roster data is used primarily for:

- Cross-validation against Commissioner sheet rosters
- Detecting roster discrepancies
- Verifying trades and waiver claims

Only the latest roster state is needed for validation and analysis purposes.

## Tasks

- [x] Locate `stg_sleeper__rosters.sql` model
- [x] Find the `read_parquet()` call with `dt=*` pattern
- [x] Replace with `snapshot_selection_strategy` macro call
- [x] Configure macro parameters:
  - [x] Use `latest_only` strategy
  - [x] Pass source glob path to macro
- [x] Test compilation: `make dbt-run --select stg_sleeper__rosters`
- [x] Test execution and verify row counts
- [x] Verify roster parity tests still run correctly

## Acceptance Criteria

- [x] `dt=*` pattern removed from model
- [x] `snapshot_selection_strategy` macro call added with `latest_only` strategy
- [x] Model compiles successfully
- [x] Model executes successfully
- [x] Row count reasonable (active rosters across franchises)

## Implementation Notes

**File**: `dbt/ff_data_transform/models/staging/stg_sleeper__rosters.sql`

**Change Pattern**:

```sql
-- BEFORE:
with source as (
  select * from read_parquet(
    'data/raw/sleeper/rosters/dt=*/*.parquet',
    hive_partitioning = true
  )
)

-- AFTER:
with source as (
  select * from read_parquet(
    'data/raw/sleeper/rosters/dt=*/*.parquet',
    hive_partitioning = true
  )
  where 1=1
    {{ snapshot_selection_strategy(
        'data/raw/sleeper/rosters/dt=*/*.parquet',
        strategy='latest_only'
    ) }}
)
```

**Configuration**:

- Strategy: `latest_only` (roster state is point-in-time, only latest relevant)
- No baseline needed (latest rosters supersede all previous)

**Why `latest_only`**:

Sleeper rosters are **current platform state** where:

- Latest snapshot reflects current roster composition
- Historical roster changes tracked via Commissioner sheet transactions
- Downstream validation expects single roster state per franchise
- Used primarily for cross-validation, not longitudinal analysis

## Testing

1. **Compilation test**:

   ```bash
   make dbt-run --select stg_sleeper__rosters
   ```

2. **Verify snapshot filtering**:

   ```bash
   EXTERNAL_ROOT="$PWD/data/raw" duckdb "$PWD/dbt/ff_data_transform/target/dev.duckdb" -c \
     "SELECT COUNT(DISTINCT dt) as snapshot_count, MAX(dt) as latest_snapshot
      FROM main.stg_sleeper__rosters;"
   # Should show snapshot_count = 1
   ```

3. **Verify roster counts**:

   ```bash
   EXTERNAL_ROOT="$PWD/data/raw" duckdb "$PWD/dbt/ff_data_transform/target/dev.duckdb" -c \
     "SELECT COUNT(DISTINCT franchise_id) as franchise_count,
             COUNT(*) as total_roster_slots
      FROM main.stg_sleeper__rosters;"
   # Should show 12 franchises with reasonable roster size
   ```

4. **Verify parity test**:

   ```bash
   make dbt-test --select assert_sleeper_commissioner_roster_parity
   # May still show 17 mismatches (roster parity issue is independent of snapshot selection)
   ```

## References

- Plan: `../2025-11-07_plan_v_2_0.md` - Lines 46-48 (Sleeper models)
- Checklist: `../2025-11-07_tasks_checklist_v_2_0.md` - Lines 82-84
- Model file: `dbt/ff_data_transform/models/staging/stg_sleeper__rosters.sql`
- Related test: `assert_sleeper_commissioner_roster_parity` (17 mismatches - not caused by snapshot issue)

## Completion Notes

**Implemented**: 2025-11-09

**Changes Made**:

- Replaced manual `latest_snapshot` CTE approach with `snapshot_selection_strategy` macro
- Removed `dt=*` wildcard pattern and manual `WHERE r.dt = (select max_dt from latest_snapshot)` filter
- Applied `latest_only` strategy for point-in-time roster state

**Test Results**:

- Compilation: PASS
- Execution: PASS
- Snapshot count: 1 (2025-11-05)
- Franchise count: 12 franchises
- Total roster slots: 321

**Impact**:

- Model now uses standardized snapshot selection approach
- Removed manual snapshot filtering logic
- Roster data correctly filtered to latest snapshot only
