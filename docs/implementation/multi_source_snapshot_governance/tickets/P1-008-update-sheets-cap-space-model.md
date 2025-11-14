# Ticket P1-008: Update stg_sheets\_\_cap_space Model

**Status**: ✅ COMPLETE\
**Phase**: 1 - Foundation\
**Estimated Effort**: Small (1-2 hours)\
**Dependencies**: P1-001 (snapshot_selection_strategy macro must exist)

## Objective

Replace `dt=*` wildcard pattern in `stg_sheets__cap_space` with the new `snapshot_selection_strategy` macro using `latest_only` strategy.

## Context

The `stg_sheets__cap_space` model currently reads all snapshots using `dt=*` pattern from the Commissioner Google Sheet exports. Cap space data represents point-in-time franchise salary cap positions and should only use the latest snapshot.

Commissioner sheets are updated manually multiple times per day during the season with roster moves, contract adjustments, and cap space changes. Only the most recent data is relevant for current league operations.

## Tasks

- [x] Locate `stg_sheets__cap_space.sql` model
- [x] Find the `read_parquet()` call with `dt=*` pattern
- [x] Replace with `snapshot_selection_strategy` macro call
- [x] Configure macro parameters:
  - [x] Use `latest_only` strategy
  - [x] Pass source glob path to macro
- [x] Test compilation: `make dbt-run --select stg_sheets__cap_space`
- [x] Test execution and verify row counts
- [x] Verify one row per franchise in output

## Acceptance Criteria

- [x] `dt=*` pattern removed from model
- [x] `snapshot_selection_strategy` macro call added with `latest_only` strategy
- [x] Model compiles successfully
- [x] Model executes successfully
- [x] Row count matches franchise count (typically 12 franchises)

## Implementation Notes

**File**: `dbt/ff_data_transform/models/staging/stg_sheets__cap_space.sql`

**Change Pattern**:

```sql
-- BEFORE:
with source as (
  select * from read_parquet(
    '{{ var("external_root", "data/raw") }}/sheets/cap_space/dt=*/*.parquet',
    hive_partitioning = true
  )
)

-- AFTER:
with source as (
  select * from read_parquet(
    '{{ var("external_root", "data/raw") }}/sheets/cap_space/dt=*/*.parquet',
    hive_partitioning = true
  )
  where 1=1
    {{ snapshot_selection_strategy(
        var("external_root", "data/raw") ~ '/sheets/cap_space/dt=*/*.parquet',
        strategy='latest_only'
    ) }}
)
```

**Configuration**:

- Strategy: `latest_only` (cap space is current state, only latest relevant)
- No baseline needed (latest cap space supersedes all previous)

**Why `latest_only`**:

Cap space data is **operational state** where:

- Latest snapshot reflects current league cap positions
- Historical snapshots are not used for analysis (cap space changes are tracked via contract history)
- Downstream models expect single snapshot per franchise
- No time-series analysis performed on cap space directly

## Testing

1. **Compilation test**:

   ```bash
   make dbt-run --select stg_sheets__cap_space
   ```

2. **Verify snapshot filtering**:

   ```bash
   EXTERNAL_ROOT="$PWD/data/raw" duckdb "$PWD/dbt/ff_data_transform/target/dev.duckdb" -c \
     "SELECT COUNT(DISTINCT dt) as snapshot_count, MAX(dt) as latest_snapshot
      FROM main.stg_sheets__cap_space;"
   # Should show snapshot_count = 1
   ```

3. **Verify franchise count**:

   ```bash
   EXTERNAL_ROOT="$PWD/data/raw" duckdb "$PWD/dbt/ff_data_transform/target/dev.duckdb" -c \
     "SELECT COUNT(*) as franchise_count FROM main.stg_sheets__cap_space;"
   # Should show 12 (one per franchise)
   ```

## References

- Plan: `../2025-11-07_plan_v_2_0.md` - Lines 39-43 (Sheets models)
- Checklist: `../2025-11-07_tasks_checklist_v_2_0.md` - Lines 61-63
- Model file: `dbt/ff_data_transform/models/staging/stg_sheets__cap_space.sql`

## Completion Notes

**Implemented**: 2025-11-09\
**Tests**: All 10 tests passing\
**Impact**: Successfully replaced source reference with direct `read_parquet()` and `snapshot_selection_strategy` macro using `latest_only` strategy

**Implementation Details**:

- Converted from `{{ source("sheets_raw", "cap_space") }}` to direct `read_parquet()` with macro
- Macro correctly filters to latest snapshot (2025-11-09) out of 3 available snapshots (2025-11-06, 2025-11-07, 2025-11-09)
- Verified zero duplicates in franchise_id/season grain
- Row count: 60 (12 franchises × 5 seasons)
- All data quality tests passing (uniqueness, referential integrity, accepted values)
