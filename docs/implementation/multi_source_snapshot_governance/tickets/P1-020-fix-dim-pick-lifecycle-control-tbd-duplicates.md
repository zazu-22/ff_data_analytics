# Ticket P1-020: Fix dim_pick_lifecycle_control TBD Pick Duplicates

**Phase**: 1 - Foundation\
**Estimated Effort**: Medium (3-5 hours)\
**Dependencies**: P1-011 (to rule out staging model as root cause)\
**Priority**: Medium - 22 duplicate pick_ids affecting 301 total rows

## Objective

Investigate and fix the root cause of 22 duplicate `pick_id` values in `dim_pick_lifecycle_control`, all affecting "TBD" (To Be Determined) picks - unassigned draft picks that haven't been traded to a specific franchise yet.

## Context

During P1-011 implementation (`stg_sheets__draft_pick_holdings`), we discovered that the `unique_dim_pick_lifecycle_control_pick_id` test fails with 22 duplicates. All duplicates are TBD picks with the pattern `YYYY_RX_TBD`.

**Test Failure**:

```
unique_dim_pick_lifecycle_control_pick_id
Got 22 results, configured to fail if != 0
```

**Evidence of TBD Pick Duplication**:

```sql
-- All duplicates are TBD picks
SELECT pick_id, COUNT(*) as dup_count
FROM main.dim_pick_lifecycle_control
GROUP BY pick_id
HAVING COUNT(*) > 1
ORDER BY dup_count DESC
LIMIT 10;

-- Results:
-- pick_id      | dup_count
-- 2023_R1_TBD  | 21
-- 2024_R1_TBD  | 17
-- 2021_R1_TBD  | 17
-- 2022_R1_TBD  | 16
-- 2021_R2_TBD  | 15
-- 2020_R1_TBD  | 14
-- 2022_R2_TBD  | 14
-- 2023_R2_TBD  | 14
-- 2025_R1_TBD  | 14
-- 2024_R2_TBD  | 14
```

**Total Impact**: 22 unique pick_ids with duplicates → 301 total rows affected

**Root Cause Hypothesis**:

The `dim_pick_lifecycle_control` model tracks pick lifecycle states (available, traded, drafted, etc.). TBD picks appear to be duplicated across lifecycle states or temporal snapshots, likely due to:

1. **Lifecycle state transitions**: Same TBD pick tracked in multiple states simultaneously
2. **Temporal tracking**: Historical lifecycle records not properly deduplicated
3. **Grain violation**: Model grain may include `lifecycle_state` or `effective_date` in addition to `pick_id`

The test expects `pick_id` to be unique, but the model may intentionally track multiple lifecycle records per pick.

**Why This Matters**:

- Test failure indicates grain mismatch between model design and test expectations
- TBD picks are used for trade valuations when pick ownership is uncertain
- Multiple lifecycle records may confuse downstream pick valuation analysis
- Only TBD picks are affected (known pick assignments work correctly)

**Important**: This is NOT caused by the snapshot governance changes in P1-011. The `stg_sheets__draft_pick_holdings` model correctly filters to latest snapshot (verified: 1 snapshot, 346 rows). Duplicates are introduced in the `dim_pick_lifecycle_control` transformation logic.

## Tasks

### Phase 1: Investigation

- [ ] Review model grain definition:
  - [ ] Check `dim_pick_lifecycle_control.sql` config and comments
  - [ ] Check YAML test definition for grain expectation
  - [ ] Determine intended grain: `pick_id` only, or `(pick_id, lifecycle_state, effective_date)`?
- [ ] Query TBD pick duplicates to identify pattern:
  ```sql
  SELECT pick_id, lifecycle_state, effective_date, COUNT(*) as row_count
  FROM main.dim_pick_lifecycle_control
  WHERE pick_id LIKE '%TBD%'
  GROUP BY pick_id, lifecycle_state, effective_date
  ORDER BY pick_id, effective_date;
  ```
- [ ] Check if duplicates have different `lifecycle_state` values
- [ ] Check if duplicates have different `effective_date` values
- [ ] Review model logic for TBD pick handling vs known pick assignments
- [ ] Document root cause with SQL evidence

### Phase 2: Determine Fix Strategy

Based on investigation, choose approach:

**Option A: Fix Test (if model grain is correct)**

- [ ] Model intentionally tracks multiple lifecycle records per pick
- [ ] Update test to use correct grain: `(pick_id, lifecycle_state, effective_date)`
- [ ] Update YAML documentation to clarify grain

**Option B: Fix Model (if model has logic error)**

- [ ] Add QUALIFY or DISTINCT to deduplicate TBD picks
- [ ] Fix lifecycle state logic to prevent duplicate records
- [ ] Ensure only one lifecycle record per pick at a time

**Option C: SCD Type 2 Temporal Logic**

- [ ] Model implements SCD Type 2 for pick lifecycle history
- [ ] Add `is_current` flag to filter to current state only
- [ ] Update test to filter `WHERE is_current = true`

### Phase 3: Implementation

- [ ] Implement chosen fix strategy
- [ ] Test compilation: `make dbt-run --select dim_pick_lifecycle_control`
- [ ] Verify row counts and grain logic

### Phase 4: Validation

- [ ] Run grain uniqueness test:
  ```bash
  make dbt-test --select dim_pick_lifecycle_control
  # Expect: unique test PASS (0 duplicates)
  ```
- [ ] Verify TBD picks are properly tracked:
  ```sql
  SELECT pick_id, lifecycle_state, COUNT(*) as state_count
  FROM main.dim_pick_lifecycle_control
  WHERE pick_id LIKE '%TBD%'
  GROUP BY pick_id, lifecycle_state
  ORDER BY pick_id;
  ```
- [ ] Spot-check known pick assignments still work correctly

## Acceptance Criteria

- [ ] Root cause identified and documented
- [ ] Fix strategy chosen and implemented
- [ ] Model compiles and executes successfully
- [ ] **Critical**: Grain uniqueness test passes (0 duplicates) OR test updated to reflect correct grain
- [ ] TBD picks tracked correctly without duplication
- [ ] Known pick assignments unaffected by fix

## Implementation Notes

**File**: `dbt/ff_data_transform/models/core/intermediate/dim_pick_lifecycle_control.sql`

**YAML**: `dbt/ff_data_transform/models/core/intermediate/_dim_pick_lifecycle_control.yml`

**Upstream Models**:

- `stg_sheets__draft_pick_holdings.sql` (P1-011 - verified clean, 1 snapshot)
- `int_pick_draft_actual.sql`
- Possibly other pick-related intermediate models

**Investigation Query**:

```sql
-- Check what makes TBD picks duplicate
SELECT
  pick_id,
  lifecycle_state,
  effective_date,
  valid_from,
  valid_to,
  is_current,
  COUNT(*) as row_count
FROM main.dim_pick_lifecycle_control
WHERE pick_id IN ('2023_R1_TBD', '2024_R1_TBD', '2021_R1_TBD')
GROUP BY ALL
ORDER BY pick_id, effective_date;
```

## Testing

1. **Run test in isolation**:

   ```bash
   EXTERNAL_ROOT="/Users/jason/code/ff_analytics/data/raw" \
   DBT_DUCKDB_PATH="/Users/jason/code/ff_analytics/dbt/ff_data_transform/target/dev.duckdb" \
   uv run dbt test --select dim_pick_lifecycle_control \
     --project-dir /Users/jason/code/ff_analytics/dbt/ff_data_transform \
     --profiles-dir /Users/jason/code/ff_analytics/dbt/ff_data_transform
   ```

2. **Check current state**:

   ```bash
   EXTERNAL_ROOT="/Users/jason/code/ff_analytics/data/raw" \
   duckdb "/Users/jason/code/ff_analytics/dbt/ff_data_transform/target/dev.duckdb" -c \
     "SELECT COUNT(*) as total_rows,
             COUNT(DISTINCT pick_id) as unique_picks,
             COUNT(*) FILTER (WHERE pick_id LIKE '%TBD%') as tbd_rows
      FROM main.dim_pick_lifecycle_control;"
   ```

3. **After fix, verify**:

   ```bash
   # Should pass with 0 duplicates
   make dbt-test --select dim_pick_lifecycle_control
   ```

## Impact

**Before Fix**:

- 22 duplicate `pick_id` values
- 301 total rows affected (all TBD picks)
- Grain test fails
- Unclear which lifecycle record is "current" for TBD picks

**After Fix**:

- 0 duplicate `pick_id` values (if Option B) OR grain test updated (if Option A) ✅
- TBD picks properly tracked ✅
- Clear grain definition documented ✅
- Downstream pick analysis uses correct data ✅

**Downstream Impact**:

- Trade analysis relies on pick lifecycle states
- Pick valuation models need accurate TBD pick tracking
- Draft capital analysis uses pick availability data

## References

- Model file: `dbt/ff_data_transform/models/core/intermediate/dim_pick_lifecycle_control.sql`
- YAML: `dbt/ff_data_transform/models/core/intermediate/_dim_pick_lifecycle_control.yml`
- Upstream: `stg_sheets__draft_pick_holdings.sql` (P1-011)
- Related test: `unique_dim_pick_lifecycle_control_pick_id`
- Discovery: During P1-011 downstream testing (2025-11-09)

## Notes

**Why This Ticket Exists**:

P1-011 fixed `stg_sheets__draft_pick_holdings` to use latest snapshot only (verified clean). However, downstream testing revealed that `dim_pick_lifecycle_control` has grain issues specific to TBD picks. This is a **data modeling issue**, not a snapshot governance issue, requiring separate investigation.

**Sequencing**:

- AFTER P1-011 (to rule out staging as root cause) ✅
- Can be done in parallel with P1-015 (last staging model)
- BEFORE Phase 2 (to ensure foundation data quality)

**TBD Pick Special Handling**:

TBD picks represent unassigned draft picks where ownership hasn't been determined (e.g., pick is "owed to whoever finishes in 3rd place"). These require special lifecycle tracking compared to picks with known ownership.
