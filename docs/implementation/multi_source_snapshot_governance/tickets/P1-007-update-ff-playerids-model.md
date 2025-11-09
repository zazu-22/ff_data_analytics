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

- [ ] Locate `stg_nflverse__ff_playerids.sql` model
- [ ] Find the `read_parquet()` call with `dt=*` pattern
- [ ] Replace with `snapshot_selection_strategy` macro call
- [ ] Configure macro parameters:
  - [ ] Use `latest_only` strategy
  - [ ] Pass source glob path to macro
- [ ] Test compilation: `make dbt-run --select stg_nflverse__ff_playerids`
- [ ] Test execution and verify row counts
- [ ] Verify downstream `dim_player_id_xref` builds correctly

## Acceptance Criteria

- [ ] `dt=*` pattern removed from model
- [ ] `snapshot_selection_strategy` macro call added with `latest_only` strategy
- [ ] Model compiles successfully
- [ ] Model executes successfully
- [ ] Row counts reasonable (should match latest snapshot player count)

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

## References

- Plan: `../2025-11-07_plan_v_2_0.md` - Lines 37 (NFLverse models)
- Checklist: `../2025-11-07_tasks_checklist_v_2_0.md` - Lines 56-58
- Model file: `dbt/ff_data_transform/models/staging/stg_nflverse__ff_playerids.sql`
- Downstream: `dbt/ff_data_transform/models/core/dim_player_id_xref.sql`
