# Ticket P1-012: Update stg_sheets\_\_transactions Model

**Phase**: 1 - Foundation\
**Estimated Effort**: Small (1-2 hours)\
**Dependencies**: P1-001 (snapshot_selection_strategy macro must exist)\
**Status**: COMPLETE

## Objective

Replace `dt=*` wildcard pattern in `stg_sheets__transactions` with the new `snapshot_selection_strategy` macro using `latest_only` strategy.

## Context

The `stg_sheets__transactions` model currently reads all snapshots using `dt=*` pattern from the Commissioner Google Sheet exports. This model contains the complete league transaction history (trades, signings, cuts, draft picks).

Transaction history is append-only operational data where new transactions are added but historical records are never modified. Only the latest snapshot contains the complete transaction log.

## Tasks

- [x] Locate `stg_sheets__transactions.sql` model
- [x] Find the `read_parquet()` call with `dt=*` pattern
- [x] Replace with `snapshot_selection_strategy` macro call
- [x] Configure macro parameters:
  - [x] Use `latest_only` strategy
  - [x] Pass source glob path to macro
- [x] Test compilation: `make dbt-run --select stg_sheets__transactions`
- [x] Test execution and verify row counts
- [x] Verify downstream `fct_league_transactions` builds correctly

## Acceptance Criteria

- [x] `dt=*` pattern removed from model
- [x] `snapshot_selection_strategy` macro call added with `latest_only` strategy
- [x] Model compiles successfully
- [x] Model executes successfully
- [x] Row count matches expected transaction count (cumulative league history)

## Implementation Notes

**File**: `dbt/ff_data_transform/models/staging/stg_sheets__transactions.sql`

**Change Pattern**:

```sql
-- BEFORE:
with source as (
  select * from read_parquet(
    '{{ var("external_root", "data/raw") }}/sheets/transactions/dt=*/*.parquet',
    hive_partitioning = true
  )
)

-- AFTER:
with source as (
  select * from read_parquet(
    '{{ var("external_root", "data/raw") }}/sheets/transactions/dt=*/*.parquet',
    hive_partitioning = true
  )
  where 1=1
    {{ snapshot_selection_strategy(
        var("external_root", "data/raw") ~ '/sheets/transactions/dt=*/*.parquet',
        strategy='latest_only'
    ) }}
)
```

**Configuration**:

- Strategy: `latest_only` (transaction log is cumulative, latest contains all)
- No baseline needed (latest log supersedes all previous)

**Why `latest_only`**:

Transaction history is **append-only operational log** where:

- Latest snapshot contains complete transaction history
- New transactions added to end of log, historical records unchanged
- Downstream models expect single transaction record per transaction_id
- No time-series analysis on transaction log snapshots themselves

**Note on Append-Only Data**:

Even though transactions are append-only, we still use `latest_only` because:

- Each snapshot is a complete copy of the transaction log (not incremental)
- Reading multiple snapshots would create duplicates of historical transactions
- The `dt` partition represents "when we exported the sheet", not "when the transaction occurred"
- Transaction timestamps are captured in the `transaction_date` field

## Testing

1. **Compilation test**:

   ```bash
   make dbt-run --select stg_sheets__transactions
   ```

2. **Verify snapshot filtering**:

   ```bash
   EXTERNAL_ROOT="$PWD/data/raw" duckdb "$PWD/dbt/ff_data_transform/target/dev.duckdb" -c \
     "SELECT COUNT(DISTINCT dt) as snapshot_count, MAX(dt) as latest_snapshot
      FROM main.stg_sheets__transactions;"
   # Should show snapshot_count = 1
   ```

3. **Verify transaction counts**:

   ```bash
   EXTERNAL_ROOT="$PWD/data/raw" duckdb "$PWD/dbt/ff_data_transform/target/dev.duckdb" -c \
     "SELECT transaction_type, COUNT(*) as txn_count
      FROM main.stg_sheets__transactions
      GROUP BY transaction_type
      ORDER BY txn_count DESC;"
   # Should show reasonable distribution of trades, signings, cuts, etc.
   ```

4. **Verify downstream impact**:

   ```bash
   make dbt-run --select +fct_league_transactions
   # Should rebuild successfully
   ```

## References

- Plan: `../2025-11-07_plan_v_2_0.md` - Lines 39-43 (Sheets models)
- Checklist: `../2025-11-07_tasks_checklist_v_2_0.md` - Lines 73-75
- Model file: `dbt/ff_data_transform/models/staging/stg_sheets__transactions.sql`
- Downstream: `dbt/ff_data_transform/models/core/fct_league_transactions.sql`
- Related warning: `relationships_stg_sheets__transactions_pick_id` (41 orphan picks)

## Completion Notes

**Implemented**: 2025-11-09
**Tests**: Compilation and execution passing

**Implementation Details**:

- Replaced manual `latest_partition` CTE with `snapshot_selection_strategy` macro
- Used `latest_only` strategy as specified
- Removed `latest_partition` CTE and all `cross join latest_partition lp` references
- Removed `where rt.dt = lp.latest_dt` filters (replaced by macro WHERE clause)
- Path: `commissioner/transactions/dt=*/*.parquet` (note: source is `commissioner`, not `sheets`)

**Verification Results**:

- Compilation: PASS
- Execution: PASS (view model)
- Transaction counts by type show reasonable distribution (867 cuts, 826 rookie draft selections, 775 FASA signings, etc.)
- Model successfully filters to latest snapshot only

**Impact**:

- Eliminated hardcoded snapshot selection logic
- Simplified model by removing manual latest_partition CTE
- Ensured idempotent reads for transaction history
- Latest snapshot contains complete cumulative transaction log
