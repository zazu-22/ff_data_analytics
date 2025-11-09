# Ticket P1-017: Fix mrt_fasa_targets Duplicate Rows

**Phase**: 1 - Foundation\
**Estimated Effort**: Medium (4-6 hours)\
**Dependencies**: P1-013 (to rule out staging model as root cause)\
**Priority**: ⚠️ **HIGH** - 1,893 duplicate rows in critical analytics mart

## Objective

Investigate and fix the root cause of 1,893 duplicate `(player_id, asof_date)` combinations in `mrt_fasa_targets`, which persist even after fixing the staging model snapshot selection.

## Context

During P1-013 implementation, we discovered that the 1,893 duplicates in `mrt_fasa_targets` are **NOT** caused by reading multiple snapshots from `stg_sleeper__fa_pool`. The staging model is clean (5,652 rows, no duplicates by `sleeper_player_id`).

**Evidence of Mart-Level Issue**:

```sql
-- Same player appears twice with DIFFERENT metric values
SELECT player_id, player_name, points_above_replacement, priority_rank_overall
FROM main.mrt_fasa_targets
WHERE player_id = 6695;

-- Results:
-- player_id | player_name   | points_above_replacement | priority_rank_overall
-- 6695      | Bradley Chubb | 0.0                      | 812
-- 6695      | Bradley Chubb | -0.25                    | 837
```

This indicates a Cartesian product or incorrect join logic in the mart's complex CTE structure.

**Grain Mismatch**:

- Model config: `unique_key=['sleeper_player_id', 'asof_date']`
- Failing test: `unique_combination_of_columns` on `['player_id', 'asof_date']`
- This mismatch suggests the model may have been designed for `sleeper_player_id` grain but is being tested for `player_id` grain

**Current Test Failure**:

```
dbt_utils_unique_combination_of_columns_mrt_fasa_targets_player_id__asof_date
Got 1893 results, configured to fail if != 0
```

## Tasks

### Phase 1: Investigation

- [ ] Identify which CTE(s) in `mrt_fasa_targets` are creating duplicates:
  - [ ] Test `fa_pool` CTE in isolation (should be clean after QUALIFY)
  - [ ] Test `recent_stats` CTE for duplicates
  - [ ] Test `projections` CTE for duplicates
  - [ ] Test `opportunity` CTE for duplicates
  - [ ] Test `position_baselines` UNION ALL logic (offense vs IDP)
  - [ ] Test final SELECT joins for Cartesian products
- [ ] Determine if grain should be `player_id` or `sleeper_player_id`:
  - [ ] Check if multiple `sleeper_player_id` values map to same `player_id`
  - [ ] Review model comments (lines 8-10) about duplicate entries in `dim_player_id_xref`
  - [ ] Decide correct grain and update config/tests accordingly
- [ ] Document root cause with SQL evidence

### Phase 2: Fix Implementation

- [ ] Implement fix based on root cause:
  - [ ] Option A: Add additional QUALIFY/DISTINCT to problematic CTE
  - [ ] Option B: Fix join conditions to prevent Cartesian product
  - [ ] Option C: Align grain (update config to `player_id` or update test to `sleeper_player_id`)
- [ ] Test compilation: `make dbt-run --select mrt_fasa_targets`
- [ ] Verify row counts match expected (should be ~3,380 unique combinations)

### Phase 3: Validation

- [ ] Run grain uniqueness test: `make dbt-test --select mrt_fasa_targets`
- [ ] Verify 0 duplicates (was 1,893)
- [ ] Check that IDP players (DE, DL, DT, LB, DB, S, CB) are not duplicated
- [ ] Spot-check a few `player_id` values to ensure only 1 row per `(player_id, asof_date)`
- [ ] Verify metrics are consistent (no different `points_above_replacement` for same player)

## Acceptance Criteria

- [ ] Root cause identified and documented in ticket comments/commit message
- [ ] Fix implemented in `mrt_fasa_targets.sql`
- [ ] Model compiles and executes successfully
- [ ] **Critical**: Grain uniqueness test passes (0 duplicates)
- [ ] Spot-check confirms consistent metrics per player

## Implementation Notes

**File**: `dbt/ff_data_transform/models/marts/mrt_fasa_targets.sql`

**Known Complex Areas**:

1. **fa_pool CTE** (lines 13-35): QUALIFY to dedup by `sleeper_player_id`

   - Already verified clean: 5,652 rows, 5,652 unique sleeper_player_ids

2. **position_baselines CTE** (lines 234-239): UNION ALL of offense + IDP

   - Could create duplicates if same position appears in both CTEs
   - IDP positions: 'DL', 'DE', 'DT', 'LB', 'DB', 'S', 'CB'

3. **Multiple window functions** (lines 972-973): `row_number()` for rankings

   - Could create different values for same player if joins are incorrect

4. **Final SELECT** (lines 798-1017): Many LEFT JOINs

   - Check for missing join keys that could cause Cartesian products

**Investigation Strategy**:

Start by querying each CTE in isolation to find where duplicates first appear:

```sql
-- Test fa_pool (should be 5,652 unique)
WITH fa_pool AS (...)
SELECT COUNT(*) as total, COUNT(DISTINCT sleeper_player_id) as unique_sleeper
FROM fa_pool;

-- Test after joining with recent_stats
WITH fa_pool AS (...), recent_stats AS (...)
SELECT fa.player_id, COUNT(*) as row_count
FROM fa_pool fa
LEFT JOIN recent_stats rs ON fa.player_id = rs.player_id
GROUP BY fa.player_id
HAVING COUNT(*) > 1;

-- Continue through each join...
```

## Testing

1. **Isolation testing** (query each CTE):

   ```bash
   # Copy CTEs into analysis file for testing
   # Or use inline WITH statements in DuckDB
   ```

2. **Compilation test**:

   ```bash
   make dbt-run --select mrt_fasa_targets
   ```

3. **Grain test**:

   ```bash
   make dbt-test --select mrt_fasa_targets
   # Expect: dbt_utils_unique_combination_of_columns test PASS (was 1,893 failures)
   ```

4. **Row count validation**:

   ```bash
   EXTERNAL_ROOT="$PWD/data/raw" duckdb "$PWD/dbt/ff_data_transform/target/dev.duckdb" -c \
     "SELECT COUNT(*) as total,
             COUNT(DISTINCT player_id) as unique_players,
             COUNT(DISTINCT (player_id, asof_date)) as unique_combinations
      FROM main.mrt_fasa_targets;"
   # Expect: total = unique_combinations (no duplicates)
   ```

## Impact

**Before Fix**:

- `mrt_fasa_targets`: 5,273 total rows, 3,380 unique `(player_id, asof_date)` combinations
- 1,893 duplicate rows causing analytics errors
- Grain uniqueness test fails

**After Fix**:

- `mrt_fasa_targets`: ~3,380 total rows = 3,380 unique combinations
- 0 duplicate rows ✅
- Grain uniqueness test passes ✅
- Correct bid recommendations and priority rankings for FASA analysis

**Downstream Impact**:

- FASA target analysis notebooks will have accurate data
- Bid recommendations will be reliable (no duplicate/conflicting values)
- Priority rankings will be consistent

## References

- Model file: `dbt/ff_data_transform/models/marts/mrt_fasa_targets.sql`
- Model YAML: `dbt/ff_data_transform/models/marts/_mrt_fasa_targets.yml`
- Related ticket: P1-013 (ruled out staging model as root cause)
- Investigation commit: dfe30f0 (P1-013 implementation with findings)

## Notes

**Why This Ticket Exists**:

P1-013 was originally expected to fix these duplicates by correcting `stg_sleeper__fa_pool` snapshot selection. However, investigation revealed:

1. The staging model already had correct snapshot filtering (via `latest_snapshot` CTE)
2. Replacing it with the macro was a good standardization but didn't fix duplicates
3. Root cause is in the mart model's join/CTE logic, requiring separate investigation

**Sequencing**:

This ticket should be completed AFTER the staging model updates (P1-002 through P1-016) but BEFORE moving to Phase 2 (Governance). It's a critical data quality issue in the foundation layer.

**Grain Decision**:

The model may need to choose between:

- `sleeper_player_id` grain (as configured) - simpler, avoids xref duplicates
- `player_id` grain (as tested) - aligns with other marts using canonical player_id

This decision should be made during investigation based on how the mart is actually used downstream.
