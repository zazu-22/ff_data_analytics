# Ticket P1-008: Update stg_sheets\_\_cap_space Model

**Phase**: 1 - Foundation\
**Estimated Effort**: Small (1-2 hours)\
**Dependencies**: P1-001 (snapshot_selection_strategy macro must exist)

## Objective

Replace `dt=*` wildcard pattern in `stg_sheets__cap_space` with the new `snapshot_selection_strategy` macro using `latest_only` strategy.

## Context

The `stg_sheets__cap_space` model currently reads all snapshots using `dt=*` pattern from the Commissioner Google Sheet exports. Cap space data represents point-in-time franchise salary cap positions and should only use the latest snapshot.

Commissioner sheets are updated manually multiple times per day during the season with roster moves, contract adjustments, and cap space changes. Only the most recent data is relevant for current league operations.

## Tasks

- [ ] Locate `stg_sheets__cap_space.sql` model
- [ ] Find the `read_parquet()` call with `dt=*` pattern
- [ ] Replace with `snapshot_selection_strategy` macro call
- [ ] Configure macro parameters:
  - [ ] Use `latest_only` strategy
  - [ ] Pass source glob path to macro
- [ ] Test compilation: `make dbt-run --select stg_sheets__cap_space`
- [ ] Test execution and verify row counts
- [ ] Verify one row per franchise in output

## Acceptance Criteria

- [ ] `dt=*` pattern removed from model
- [ ] `snapshot_selection_strategy` macro call added with `latest_only` strategy
- [ ] Model compiles successfully
- [ ] Model executes successfully
- [ ] Row count matches franchise count (typically 12 franchises)

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
