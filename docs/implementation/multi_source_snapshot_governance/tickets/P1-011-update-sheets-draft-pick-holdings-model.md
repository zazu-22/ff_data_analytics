# Ticket P1-011: Update stg_sheets\_\_draft_pick_holdings Model

**Phase**: 1 - Foundation\
**Estimated Effort**: Small (1-2 hours)\
**Dependencies**: P1-001 (snapshot_selection_strategy macro must exist)

## Objective

Replace `dt=*` wildcard pattern in `stg_sheets__draft_pick_holdings` with the new `snapshot_selection_strategy` macro using `latest_only` strategy.

## Context

The `stg_sheets__draft_pick_holdings` model currently reads all snapshots using `dt=*` pattern from the Commissioner Google Sheet exports. This model tracks current draft pick ownership across franchises and future draft years.

Pick holdings change frequently via trades and must reflect the most current ownership state for accurate dynasty asset valuation and trade analysis.

## Tasks

- [ ] Locate `stg_sheets__draft_pick_holdings.sql` model
- [ ] Find the `read_parquet()` call with `dt=*` pattern
- [ ] Replace with `snapshot_selection_strategy` macro call
- [ ] Configure macro parameters:
  - [ ] Use `latest_only` strategy
  - [ ] Pass source glob path to macro
- [ ] Test compilation: `make dbt-run --select stg_sheets__draft_pick_holdings`
- [ ] Test execution and verify row counts
- [ ] Verify downstream pick models build correctly (may help fix `dim_pick_lifecycle_control` duplicates)

## Acceptance Criteria

- [ ] `dt=*` pattern removed from model
- [ ] `snapshot_selection_strategy` macro call added with `latest_only` strategy
- [ ] Model compiles successfully
- [ ] Model executes successfully
- [ ] Row count reasonable (60 picks per season × future seasons tracked)

## Implementation Notes

**File**: `dbt/ff_data_transform/models/staging/stg_sheets__draft_pick_holdings.sql`

**Change Pattern**:

```sql
-- BEFORE:
with source as (
  select * from read_parquet(
    '{{ var("external_root", "data/raw") }}/sheets/draft_pick_holdings/dt=*/*.parquet',
    hive_partitioning = true
  )
)

-- AFTER:
with source as (
  select * from read_parquet(
    '{{ var("external_root", "data/raw") }}/sheets/draft_pick_holdings/dt=*/*.parquet',
    hive_partitioning = true
  )
  where 1=1
    {{ snapshot_selection_strategy(
        var("external_root", "data/raw") ~ '/sheets/draft_pick_holdings/dt=*/*.parquet',
        strategy='latest_only'
    ) }}
)
```

**Configuration**:

- Strategy: `latest_only` (pick holdings are current ownership state)
- No baseline needed (latest ownership supersedes all previous)

**Why `latest_only`**:

Draft pick holdings are **current asset ownership** where:

- Latest snapshot reflects current pick ownership after recent trades
- Historical ownership tracked via transaction history
- Downstream models expect single ownership record per pick per season
- Pick ownership changes frequently during trade seasons

**Potential Impact**:

This fix may contribute to resolving the `dim_pick_lifecycle_control` duplicate issue (22 duplicates). If multiple snapshots are being read for pick holdings, this could cascade to duplicate pick records in the lifecycle control model.

## Testing

1. **Compilation test**:

   ```bash
   make dbt-run --select stg_sheets__draft_pick_holdings
   ```

2. **Verify snapshot filtering**:

   ```bash
   EXTERNAL_ROOT="$PWD/data/raw" duckdb "$PWD/dbt/ff_data_transform/target/dev.duckdb" -c \
     "SELECT COUNT(DISTINCT dt) as snapshot_count, MAX(dt) as latest_snapshot
      FROM main.stg_sheets__draft_pick_holdings;"
   # Should show snapshot_count = 1
   ```

3. **Verify pick counts by season**:

   ```bash
   EXTERNAL_ROOT="$PWD/data/raw" duckdb "$PWD/dbt/ff_data_transform/target/dev.duckdb" -c \
     "SELECT season, COUNT(*) as picks_count
      FROM main.stg_sheets__draft_pick_holdings
      GROUP BY season
      ORDER BY season;"
   # Should show 60 picks (5 rounds × 12 franchises) per future season
   ```

4. **Check for duplicate impact**:

   ```bash
   make dbt-test --select dim_pick_lifecycle_control
   # May help reduce duplicates (currently 22)
   ```

## References

- Plan: `../2025-11-07_plan_v_2_0.md` - Lines 39-43 (Sheets models)
- Checklist: `../2025-11-07_tasks_checklist_v_2_0.md` - Lines 70-72
- Model file: `dbt/ff_data_transform/models/staging/stg_sheets__draft_pick_holdings.sql`
- Downstream: `dbt/ff_data_transform/models/core/dim_pick.sql`
- Related test failure: `unique_dim_pick_lifecycle_control_pick_id` (22 duplicates)
