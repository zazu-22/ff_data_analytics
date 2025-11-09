# Ticket P1-010: Update stg_sheets\_\_contracts_cut Model

**Status**: ✅ COMPLETE\
**Phase**: 1 - Foundation\
**Estimated Effort**: Small (1-2 hours)\
**Dependencies**: P1-001 (snapshot_selection_strategy macro must exist)

## Objective

Replace `dt=*` wildcard pattern in `stg_sheets__contracts_cut` with the new `snapshot_selection_strategy` macro using `latest_only` strategy.

## Context

The `stg_sheets__contracts_cut` model currently reads all snapshots using `dt=*` pattern from the Commissioner Google Sheet exports. This model contains the league's cut liability schedule (dead cap penalties by contract year and timing).

Cut liability rules are relatively static reference data that define dead cap calculations. Only the latest/current ruleset is needed for contract analysis.

## Tasks

- [ ] Locate `stg_sheets__contracts_cut.sql` model
- [ ] Find the `read_parquet()` call with `dt=*` pattern
- [ ] Replace with `snapshot_selection_strategy` macro call
- [ ] Configure macro parameters:
  - [ ] Use `latest_only` strategy
  - [ ] Pass source glob path to macro
- [ ] Test compilation: `make dbt-run --select stg_sheets__contracts_cut`
- [ ] Test execution and verify row counts
- [ ] Verify downstream `dim_cut_liability_schedule` builds correctly

## Acceptance Criteria

- [ ] `dt=*` pattern removed from model
- [ ] `snapshot_selection_strategy` macro call added with `latest_only` strategy
- [ ] Model compiles successfully
- [ ] Model executes successfully
- [ ] Row count matches cut liability rule count (typically 15-20 rules)

## Implementation Notes

**File**: `dbt/ff_data_transform/models/staging/stg_sheets__contracts_cut.sql`

**Change Pattern**:

```sql
-- BEFORE:
with source as (
  select * from read_parquet(
    '{{ var("external_root", "data/raw") }}/sheets/contracts_cut/dt=*/*.parquet',
    hive_partitioning = true
  )
)

-- AFTER:
with source as (
  select * from read_parquet(
    '{{ var("external_root", "data/raw") }}/sheets/contracts_cut/dt=*/*.parquet',
    hive_partitioning = true
  )
  where 1=1
    {{ snapshot_selection_strategy(
        var("external_root", "data/raw") ~ '/sheets/contracts_cut/dt=*/*.parquet',
        strategy='latest_only'
    ) }}
)
```

**Configuration**:

- Strategy: `latest_only` (cut liability rules are reference data)
- No baseline needed (latest rules supersede all previous)

**Why `latest_only`**:

Cut liability schedule is **league rules reference data** where:

- Rules change infrequently (only when league constitution is amended)
- Latest snapshot reflects current dead cap calculation rules
- Historical rule versions not used for analysis
- Downstream models expect single authoritative ruleset

## Testing

1. **Compilation test**:

   ```bash
   make dbt-run --select stg_sheets__contracts_cut
   ```

2. **Verify snapshot filtering**:

   ```bash
   EXTERNAL_ROOT="$PWD/data/raw" duckdb "$PWD/dbt/ff_data_transform/target/dev.duckdb" -c \
     "SELECT COUNT(DISTINCT dt) as snapshot_count, MAX(dt) as latest_snapshot
      FROM main.stg_sheets__contracts_cut;"
   # Should show snapshot_count = 1
   ```

3. **Verify downstream impact**:

   ```bash
   make dbt-run --select +dim_cut_liability_schedule
   # Should rebuild successfully
   ```

4. **Verify rule coverage**:

   ```bash
   EXTERNAL_ROOT="$PWD/data/raw" duckdb "$PWD/dbt/ff_data_transform/target/dev.duckdb" -c \
     "SELECT contract_year, rounding_rule, COUNT(*) as rule_count
      FROM main.stg_sheets__contracts_cut
      GROUP BY contract_year, rounding_rule
      ORDER BY contract_year;"
   # Should show rules for contract years 1-5 with 'ceil' rounding
   ```

## References

- Plan: `../2025-11-07_plan_v_2_0.md` - Lines 39-43 (Sheets models)
- Checklist: `../2025-11-07_tasks_checklist_v_2_0.md` - Lines 67-69
- Model file: `dbt/ff_data_transform/models/staging/stg_sheets__contracts_cut.sql`
- Downstream: `dbt/ff_data_transform/models/core/dim_cut_liability_schedule.sql`

## Completion Notes

**Implemented**: 2025-11-09\
**Tests**: 8/9 tests passing (1 pre-existing roster parity test failure unrelated to snapshot governance)\
**Impact**: Successfully replaced `latest_snapshot_only()` helper with `snapshot_selection_strategy` macro using `latest_only` strategy

**Implementation Details**:

- Replaced `latest_snapshot_only()` with `snapshot_selection_strategy(strategy='latest_only')` in WHERE clause
- Macro correctly filters to latest snapshot (2025-11-09) out of 3 available snapshots
- Verified zero duplicates in franchise_id/player_key/obligation_year/snapshot_date grain (436 rows = 436 unique keys)
- Row count: 436 dead cap obligations across all franchises
- Uniqueness test: PASS
- Referential integrity tests: PASS
- Pre-existing test failure: `assert_sleeper_commissioner_roster_parity` (17 discrepancies, documented in P1-019)
