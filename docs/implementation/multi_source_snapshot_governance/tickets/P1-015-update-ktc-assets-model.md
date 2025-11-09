# Ticket P1-015: Update stg_ktc_assets Model

**Phase**: 1 - Foundation\
**Estimated Effort**: Small (1-2 hours)\
**Dependencies**: P1-001 (snapshot_selection_strategy macro must exist)

## Objective

Replace `dt=*` wildcard pattern in `stg_ktc_assets` with the new `snapshot_selection_strategy` macro using `latest_only` strategy.

## Context

The `stg_ktc_assets` model currently reads all snapshots using `dt=*` pattern from Keep Trade Cut (KTC) API exports. This model contains dynasty player and pick valuations (0-10,000 scale) for 1QB league format.

KTC valuations are updated approximately weekly and reflect current dynasty market consensus. Only the latest valuations are used for:

- Trade analysis and recommendations
- FASA target scoring (market efficiency signals)
- Dynasty asset portfolio valuation

Historical KTC values could be used for trend analysis, but current implementation uses only latest values.

## Tasks

- [ ] Locate `stg_ktc_assets.sql` model
- [ ] Find the `read_parquet()` call with `dt=*` pattern
- [ ] Replace with `snapshot_selection_strategy` macro call
- [ ] Configure macro parameters:
  - [ ] Use `latest_only` strategy
  - [ ] Pass source glob path to macro
- [ ] Test compilation: `make dbt-run --select stg_ktc_assets`
- [ ] Test execution and verify row counts
- [ ] Verify downstream `fct_asset_market_values` builds correctly

## Acceptance Criteria

- [ ] `dt=*` pattern removed from model
- [ ] `snapshot_selection_strategy` macro call added with `latest_only` strategy
- [ ] Model compiles successfully
- [ ] Model executes successfully
- [ ] Row count matches expected asset count (players + picks in KTC database)

## Implementation Notes

**File**: `dbt/ff_data_transform/models/staging/stg_ktc_assets.sql`

**Change Pattern**:

```sql
-- BEFORE:
with source as (
  select * from read_parquet(
    '{{ var("external_root", "data/raw") }}/ktc/players/dt=*/*.parquet',
    hive_partitioning = true
  )
)

-- AFTER:
with source as (
  select * from read_parquet(
    '{{ var("external_root", "data/raw") }}/ktc/players/dt=*/*.parquet',
    hive_partitioning = true
  )
  where 1=1
    {{ snapshot_selection_strategy(
        var("external_root", "data/raw") ~ '/ktc/players/dt=*/*.parquet',
        strategy='latest_only'
    ) }}
)
```

**Configuration**:

- Strategy: `latest_only` (market values are current consensus, only latest relevant)
- No baseline needed (latest valuations supersede all previous)

**Why `latest_only`**:

KTC valuations are **market consensus snapshots** where:

- Latest snapshot reflects current dynasty trade market
- Historical values not currently used (could enable trend analysis in future)
- Downstream models expect single valuation per asset
- Values updated weekly but only latest used for decision-making

**Future Enhancement**:

If trend analysis is desired (e.g., 4-week value change), could switch to `baseline_plus_latest` strategy with 4-week baseline. Current implementation uses only latest for simplicity.

## Testing

1. **Compilation test**:

   ```bash
   make dbt-run --select stg_ktc_assets
   ```

2. **Verify snapshot filtering**:

   ```bash
   EXTERNAL_ROOT="$PWD/data/raw" duckdb "$PWD/dbt/ff_data_transform/target/dev.duckdb" -c \
     "SELECT COUNT(DISTINCT dt) as snapshot_count, MAX(dt) as latest_snapshot
      FROM main.stg_ktc_assets;"
   # Should show snapshot_count = 1
   ```

3. **Verify asset counts by type**:

   ```bash
   EXTERNAL_ROOT="$PWD/data/raw" duckdb "$PWD/dbt/ff_data_transform/target/dev.duckdb" -c \
     "SELECT asset_type, COUNT(*) as asset_count
      FROM main.stg_ktc_assets
      GROUP BY asset_type
      ORDER BY asset_type;"
   # Should show counts for 'player' and 'pick' assets
   ```

4. **Verify downstream impact**:

   ```bash
   make dbt-run --select +fct_asset_market_values
   # Should rebuild successfully
   ```

5. **Check value ranges**:

   ```bash
   EXTERNAL_ROOT="$PWD/data/raw" duckdb "$PWD/dbt/ff_data_transform/target/dev.duckdb" -c \
     "SELECT
        MIN(ktc_value) as min_value,
        MAX(ktc_value) as max_value,
        AVG(ktc_value) as avg_value
      FROM main.stg_ktc_assets
      WHERE asset_type = 'player';"
   # Should show values in 0-10,000 range
   ```

## References

- Plan: `../2025-11-07_plan_v_2_0.md` - Lines 50-51 (KTC models)
- Checklist: `../2025-11-07_tasks_checklist_v_2_0.md` - Lines 86-88
- Model file: `dbt/ff_data_transform/models/staging/stg_ktc_assets.sql`
- Downstream: `dbt/ff_data_transform/models/core/fct_asset_market_values.sql`
- Usage: `dbt/ff_data_transform/models/marts/mrt_fasa_targets.sql` (market efficiency signals)
