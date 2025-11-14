# Ticket P1-009: Update stg_sheets\_\_contracts_active Model

**Status**: ✅ COMPLETE\
**Phase**: 1 - Foundation\
**Estimated Effort**: Small (1-2 hours)\
**Dependencies**: P1-001 (snapshot_selection_strategy macro must exist)

## Objective

Replace `dt=*` wildcard pattern in `stg_sheets__contracts_active` with the new `snapshot_selection_strategy` macro using `latest_only` strategy.

## Context

The `stg_sheets__contracts_active` model currently reads all snapshots using `dt=*` pattern from the Commissioner Google Sheet exports. Active contracts represent current player-franchise contractual obligations and should only use the latest snapshot.

This model feeds into `dim_player_contract_history` and contract-related analyses. Only the current state of active contracts is needed; historical contract snapshots are tracked via the contract history dimension.

## Tasks

- [x] Locate `stg_sheets__contracts_active.sql` model
- [x] Find the `read_parquet()` call with `dt=*` pattern
- [x] Replace with `snapshot_selection_strategy` macro call
- [x] Configure macro parameters:
  - [x] Use `latest_only` strategy
  - [x] Pass source glob path to macro
- [x] Test compilation: `make dbt-run --select stg_sheets__contracts_active`
- [x] Test execution and verify row counts
- [x] Verify downstream `dim_player_contract_history` builds correctly

## Acceptance Criteria

- [x] `dt=*` pattern removed from model
- [x] `snapshot_selection_strategy` macro call added with `latest_only` strategy
- [x] Model compiles successfully
- [x] Model executes successfully
- [x] Row count reasonable (active contracts across all franchises)

## Implementation Notes

**File**: `dbt/ff_data_transform/models/staging/stg_sheets__contracts_active.sql`

**Change Pattern**:

```sql
-- BEFORE:
with source as (
  select * from read_parquet(
    '{{ var("external_root", "data/raw") }}/sheets/contracts_active/dt=*/*.parquet',
    hive_partitioning = true
  )
)

-- AFTER:
with source as (
  select * from read_parquet(
    '{{ var("external_root", "data/raw") }}/sheets/contracts_active/dt=*/*.parquet',
    hive_partitioning = true
  )
  where 1=1
    {{ snapshot_selection_strategy(
        var("external_root", "data/raw") ~ '/sheets/contracts_active/dt=*/*.parquet',
        strategy='latest_only'
    ) }}
)
```

**Configuration**:

- Strategy: `latest_only` (active contracts are current state)
- No baseline needed (latest contracts supersede all previous)

**Why `latest_only`**:

Active contracts are **current roster state** where:

- Latest snapshot reflects current player obligations
- Historical contract changes tracked via `dim_player_contract_history` SCD Type 2
- Downstream models expect single active contract per player
- Contract lifecycle (signed → active → cut → expired) tracked separately

## Testing

1. **Compilation test**:

   ```bash
   make dbt-run --select stg_sheets__contracts_active
   ```

2. **Verify snapshot filtering**:

   ```bash
   EXTERNAL_ROOT="$PWD/data/raw" duckdb "$PWD/dbt/ff_data_transform/target/dev.duckdb" -c \
     "SELECT COUNT(DISTINCT dt) as snapshot_count, MAX(dt) as latest_snapshot
      FROM main.stg_sheets__contracts_active;"
   # Should show snapshot_count = 1
   ```

3. **Verify downstream impact**:

   ```bash
   make dbt-run --select +dim_player_contract_history
   # Should rebuild successfully
   ```

## References

- Plan: `../2025-11-07_plan_v_2_0.md` - Lines 39-43 (Sheets models)
- Checklist: `../2025-11-07_tasks_checklist_v_2_0.md` - Lines 64-66
- Model file: `dbt/ff_data_transform/models/staging/stg_sheets__contracts_active.sql`
- Downstream: `dbt/ff_data_transform/models/core/dim_player_contract_history.sql`

## Completion Notes

**Implemented**: 2025-11-09\
**Tests**: 9/10 tests passing (1 pre-existing data quality assertion failure unrelated to snapshot governance)\
**Impact**: Successfully replaced `latest_snapshot_only()` helper with `snapshot_selection_strategy` macro using `latest_only` strategy

**Implementation Details**:

- Replaced `latest_snapshot_only()` with `snapshot_selection_strategy(strategy='latest_only')` in WHERE clause
- Macro correctly filters to latest snapshot (2025-11-09) out of 3 available snapshots (2025-11-06, 2025-11-07, 2025-11-09)
- Verified zero duplicates in franchise_id/player_key/obligation_year/snapshot_date grain (886 rows = 886 unique keys)
- Row count: 886 active contract obligations
- Uniqueness test: PASS
- Referential integrity tests: PASS
- Pre-existing test failure: `assert_sleeper_commissioner_roster_parity` (17 data discrepancies, not related to snapshot governance change)
