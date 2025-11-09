# Ticket P1-016: Update stg_ffanalytics\_\_projections Model

**Phase**: 1 - Foundation\
**Estimated Effort**: Small (1-2 hours)\
**Dependencies**: P1-001 (snapshot_selection_strategy macro must exist)\
**Priority**: ⚠️ **HIGH** - Fixes 195 duplicates (33 in staging + 162 in fact table)

## Objective

Replace `dt=*` wildcard pattern in `stg_ffanalytics__projections` with the new `snapshot_selection_strategy` macro using `latest_only` strategy.

## Context

The `stg_ffanalytics__projections` model currently reads all snapshots using `dt=*` pattern, causing:

- **33 duplicate rows** in `stg_ffanalytics__projections` (grain violation)
- **162 duplicate rows** in `fct_player_projections` (cascading from staging)

**Test Failures**:

```
1. stg_ffanalytics__projections grain test:
   dbt_utils_unique_combination_of_columns_player_id__season__week__horizon__asof_date__provider
   Got 33 results, configured to fail if != 0

2. fct_player_projections grain test (warning):
   dbt_utils_unique_combination_of_columns (8-column grain)
   Got 162 results, configured to warn if != 0
```

**Root Cause**: Line 79 in `stg_ffanalytics__projections.sql`:

```sql
from read_parquet(
  '{{ var("external_root", "data/raw") }}/ffanalytics/projections/dt=*/projections_consensus_*.parquet',
  hive_partitioning = true
)
```

This reads **all historical snapshots**, violating the 2×2 stat model assumption that projections have a single `asof_date` per player/season/week.

## Tasks

- [ ] Locate `stg_ffanalytics__projections.sql` model
- [ ] Find the `read_parquet()` call at line 79 with `dt=*` pattern
- [ ] Replace with `snapshot_selection_strategy` macro call
- [ ] Configure macro parameters:
  - [ ] Use `latest_only` strategy (projections are updated weekly, only latest relevant)
  - [ ] Use `var("external_root")` for path construction
- [ ] Test compilation: `make dbt-run --select stg_ffanalytics__projections`
- [ ] Test execution and verify row counts
- [ ] **Verify duplicate fix**: Run `make dbt-test --select stg_ffanalytics__projections fct_player_projections`
  - [ ] Expect staging test: 33 duplicates → 0
  - [ ] Expect fact test: 162 duplicates → 0

## Acceptance Criteria

- [ ] `dt=*` pattern removed from model
- [ ] `snapshot_selection_strategy` macro call added with `latest_only` strategy
- [ ] Model compiles successfully
- [ ] Model executes successfully
- [ ] **Critical**: Both grain tests pass (0 duplicates in staging and fact)

## Implementation Notes

**File**: `dbt/ff_data_transform/models/staging/stg_ffanalytics__projections.sql`

**Change Pattern**:

```sql
-- BEFORE (line 77-82):
from
    read_parquet(
        '{{ var("external_root", "data/raw") }}/ffanalytics/projections/dt=*/projections_consensus_*.parquet',
        hive_partitioning = true
    )

-- Filter out unmapped players (R runner sets player_id = -1 for unmapped)
where cast(player_id as integer) > 0

-- AFTER:
from
    read_parquet(
        '{{ var("external_root", "data/raw") }}/ffanalytics/projections/dt=*/projections_consensus_*.parquet',
        hive_partitioning = true
    )
where 1=1
    -- Filter to latest snapshot only
    {{ snapshot_selection_strategy(
        var("external_root", "data/raw") ~ '/ffanalytics/projections/dt=*/*.parquet',
        strategy='latest_only'
    ) }}
    -- Filter out unmapped players (R runner sets player_id = -1 for unmapped)
    and cast(player_id as integer) > 0
```

**Configuration**:

- Strategy: `latest_only` (projections updated weekly, only latest needed)
- No baseline needed (latest projections supersede previous)

**Why `latest_only`**:

FFanalytics projections are **forward-looking estimates** that are updated weekly:

- Each new snapshot supersedes the previous (refined estimates)
- Historical projections are not used in current analysis
- The `asof_date` column already captures when the projection was made

Using `latest_only`:

- Eliminates duplicate (player_id, season, week, horizon, asof_date, provider) combinations
- Ensures 2×2 stat model integrity (single projection per player/week/horizon)
- Maintains grain: one row per player per stat type per projection timeframe

## Testing

1. **Compilation test**:

   ```bash
   make dbt-run --select stg_ffanalytics__projections
   ```

2. **Verify snapshot filtering**:

   ```bash
   EXTERNAL_ROOT="$PWD/data/raw" duckdb "$PWD/dbt/ff_data_transform/target/dev.duckdb" -c \
     "SELECT DISTINCT asof_date FROM main.stg_ffanalytics__projections ORDER BY asof_date DESC;"
   # Should show only 1 date (latest)
   ```

3. **Verify duplicate fix in staging**:

   ```bash
   make dbt-test --select stg_ffanalytics__projections
   # Expect: unique_combination_of_columns test PASS (was 33 failures)
   ```

4. **Verify cascade fix in fact table**:

   ```bash
   make dbt-test --select fct_player_projections
   # Expect: unique_combination_of_columns test PASS (was 162 warnings)
   ```

5. **Query duplicate check**:

   ```bash
   EXTERNAL_ROOT="$PWD/data/raw" duckdb "$PWD/dbt/ff_data_transform/target/dev.duckdb" -c \
     "SELECT player_id, season, week, horizon, asof_date, provider, COUNT(*) as row_count
      FROM main.stg_ffanalytics__projections
      GROUP BY player_id, season, week, horizon, asof_date, provider
      HAVING COUNT(*) > 1;"
   # Should return 0 rows
   ```

## Impact

**Before Fix**:

- `stg_ffanalytics__projections`: Reading N snapshots → duplicates on grain
- `fct_player_projections`: Inheriting duplicates from staging
- 2×2 stat model integrity compromised

**After Fix**:

- `stg_ffanalytics__projections`: Reading 1 snapshot → clean grain ✅
- `fct_player_projections`: Single projection per player/stat/week ✅
- 2×2 stat model integrity restored ✅

**Downstream Models Fixed**:

- `fct_player_projections` - Player projection fact table
- `mrt_fantasy_projections` - Fantasy projections mart
- `mrt_projection_variance` - Actual vs projection variance analysis

## References

- Plan: `../2025-11-07_plan_v_2_0.md` - Lines 53-54 (FFAnalytics models)
- Checklist: `../2025-11-07_tasks_checklist_v_2_0.md` - Lines 91-96 (FFAnalytics priority)
- Model file: `dbt/ff_data_transform/models/staging/stg_ffanalytics__projections.sql`
- YAML: `dbt/ff_data_transform/models/staging/_stg_ffanalytics__projections.yml` (grain test)
- ADR-007: 2×2 Stat Model (separate actuals vs projections fact tables)
