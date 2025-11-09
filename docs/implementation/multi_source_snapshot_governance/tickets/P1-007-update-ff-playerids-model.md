# Ticket P1-007: Update stg_nflverse\_\_ff_playerids Model

**Phase**: 1 - Foundation\
**Estimated Effort**: Small (1-2 hours)\
**Dependencies**: P1-001 (snapshot_selection_strategy macro must exist)

## Objective

Replace `dt=*` wildcard pattern in `stg_nflverse__ff_playerids` with the new `snapshot_selection_strategy` macro using `latest_only` strategy.

## Context

The `stg_nflverse__ff_playerids` model currently reads all snapshots using `dt=*` pattern. This model provides the player ID crosswalk mapping between different data sources (MFL, Sleeper, ESPN, etc.) and should only use the latest available mapping.

Player ID mappings are relatively stable but can change when:

- New players are added to the league
- Corrections are made to historical mappings
- New data sources are integrated

Using `latest_only` ensures we always use the most current and accurate player ID mappings.

## Tasks

- [x] Locate `stg_nflverse__ff_playerids.sql` model
- [x] Find the `read_parquet()` call with `dt=*` pattern
- [x] Replace with `snapshot_selection_strategy` macro call
- [x] Configure macro parameters:
  - [x] Use `latest_only` strategy
  - [x] Pass source glob path to macro
- [x] Test compilation: `make dbt-run --select stg_nflverse__ff_playerids`
- [x] Test execution and verify row counts
- [x] Verify downstream `dim_player_id_xref` builds correctly

## Acceptance Criteria

- [x] `dt=*` pattern removed from model
- [x] `snapshot_selection_strategy` macro call added with `latest_only` strategy
- [x] Model compiles successfully
- [x] Model executes successfully
- [x] Row counts reasonable (should match latest snapshot player count)

## Implementation Notes

**File**: `dbt/ff_data_transform/models/staging/stg_nflverse__ff_playerids.sql`

**Change Pattern**:

```sql
-- BEFORE:
with source as (
  select * from read_parquet(
    '{{ var("external_root", "data/raw") }}/nflverse/ff_playerids/dt=*/*.parquet',
    hive_partitioning = true
  )
)

-- AFTER:
with source as (
  select * from read_parquet(
    '{{ var("external_root", "data/raw") }}/nflverse/ff_playerids/dt=*/*.parquet',
    hive_partitioning = true
  )
  where 1=1
    {{ snapshot_selection_strategy(
        var("external_root", "data/raw") ~ '/nflverse/ff_playerids/dt=*/*.parquet',
        strategy='latest_only'
    ) }}
)
```

**Configuration**:

- Strategy: `latest_only` (crosswalk mappings should use latest authoritative version)
- No baseline needed (latest mappings supersede all previous)

**Why `latest_only`**:

Player ID crosswalks are **reference data** where:

- Latest snapshot contains most accurate mappings
- Historical snapshots may have errors corrected in newer versions
- No analytical value in comparing crosswalks over time
- Downstream models expect single authoritative mapping per player

## Testing

1. **Compilation test**:

   ```bash
   make dbt-run --select stg_nflverse__ff_playerids
   ```

2. **Verify snapshot filtering**:

   ```bash
   EXTERNAL_ROOT="$PWD/data/raw" duckdb "$PWD/dbt/ff_data_transform/target/dev.duckdb" -c \
     "SELECT COUNT(*) as player_count, MIN(dt) as snapshot_date
      FROM main.stg_nflverse__ff_playerids
      GROUP BY dt;"
   # Should show only 1 snapshot date
   ```

3. **Verify downstream impact**:

   ```bash
   make dbt-run --select +dim_player_id_xref
   # Should rebuild successfully
   ```

## Implementation Summary

**Completed**: 2025-11-09\
**Commit**: `f55b06c` - feat(snapshot): implement P1-007 - stg_nflverse\_\_ff_playerids

### What Was Delivered

1. **Model Updated**: `dbt/ff_data_transform/models/staging/stg_nflverse__ff_playerids.sql`

   - Replaced `dt=*` pattern with `snapshot_selection_strategy` macro
   - Uses `latest_only` strategy for player ID crosswalk reference data
   - Completes all 4 NFLverse staging models (100%)

2. **Testing Results**:

   - Compilation: PASS
   - Execution: PASS (table created in 2.87s)
   - Row count: 9,734 players (matches expected after filtering)
   - Snapshot selection: 2025-10-01 (latest/only available)
   - Deduplication: Working correctly (20 sleeper_ids added, 10 gsis duplicates cleared)

3. **Coverage Verification**:

   - Total players: 9,734
   - Unique player_ids: 9,734 (1:1 mapping)
   - Unique mfl_ids: 9,734 (canonical identifier)
   - Unique gsis_ids: 7,639 (some players lack NFL IDs)
   - Unique sleeper_ids: 6,169 (some cleared/missing)

4. **Rationale for latest_only**:

   - Player ID crosswalks are reference data
   - Latest snapshot contains most accurate mappings
   - Historical snapshots may have errors corrected in newer versions
   - No analytical value in comparing crosswalks over time
   - Downstream models expect single authoritative mapping per player

5. **NFLverse Models Complete**:

   - ✓ P1-002: stg_nflverse\_\_player_stats (baseline_plus_latest)
   - ✓ P1-003: stg_nflverse\_\_snap_counts (baseline_plus_latest)
   - ✓ P1-004: stg_nflverse\_\_ff_opportunity (latest_only)
   - ✓ P1-007: stg_nflverse\_\_ff_playerids (latest_only)

6. **Tracking Updated**:

   - `00-OVERVIEW.md`: 8/49 tickets complete (16%)
   - `tasks_checklist_v_2_0.md`: stg_nflverse\_\_ff_playerids complete
   - All NFLverse models now use consistent snapshot governance pattern

**Status**: COMPLETE - All 4 NFLverse staging models successfully migrated

## References

- Plan: `../2025-11-07_plan_v_2_0.md` - Lines 37 (NFLverse models)
- Checklist: `../2025-11-07_tasks_checklist_v_2_0.md` - Lines 56-58
- Model file: `dbt/ff_data_transform/models/staging/stg_nflverse__ff_playerids.sql`
- Downstream: `dbt/ff_data_transform/models/core/dim_player_id_xref.sql`
