# Ticket P1-024: Fix int_pick_comp_registry Duplicate Transaction IDs

**Status**: COMPLETE\
**Phase**: 1 - Foundation\
**Estimated Effort**: Small-Medium (2-3 hours)\
**Dependencies**: None (independent data integrity issue)\
**Priority**: Medium - 19 duplicate comp_faad_transaction_ids

## Objective

Investigate and fix the root cause of 19 duplicate `comp_faad_transaction_id` values in the `int_pick_comp_registry` intermediate model, which serves as the registry for compensatory pick assignments.

## Context

During comprehensive dbt test analysis (2025-11-10), the `unique_int_pick_comp_registry_comp_faad_transaction_id` test failed with 19 duplicates, indicating that some compensatory pick transaction IDs appear multiple times in the registry.

**Test Failure**:

```
unique_int_pick_comp_registry_comp_faad_transaction_id
Got 19 results, configured to fail if != 0
```

**Expected Behavior**:

The `int_pick_comp_registry` model maps compensatory picks to their originating free agent transactions. Each `comp_faad_transaction_id` should appear exactly once in the registry - one compensatory pick awarded per qualifying FA transaction.

**Why This Matters**:

- Registry integrity - each comp pick should map to exactly one FA transaction
- Compensatory pick calculation accuracy
- Downstream pick valuation and draft analysis
- Prevents double-counting of comp picks in trade scenarios

## Tasks

### Phase 1: Investigation

- [x] Query to identify duplicate transaction IDs: ✅ 0 duplicates found
- [x] Examine full records for duplicates: ✅ No duplicates to examine
- [x] Check if duplicates have different pick_ids: ✅ No duplicates present
- [x] Review model logic in `int_pick_comp_registry.sql`:
  - [x] Check for missing DISTINCT or QUALIFY
  - [x] Identify any Cartesian products in joins ✅ Found: SCD Type 2 join issue
  - [x] Review window functions and partitioning
- [x] Document root cause with SQL evidence ✅ See Completion Notes

### Phase 2: Determine Fix Strategy

Based on investigation, choose approach:

**Option B: Fix Join Logic** ✅ SELECTED AND IMPLEMENTED

- [x] Model has incorrect join creating Cartesian product ✅ SCD Type 2 temporal issue
- [x] Fix join conditions to prevent duplicates ✅ Added temporal filter
- [x] Add missing join keys ✅ Added season_start/season_end conditions

### Phase 3: Implementation

- [x] Implement chosen fix strategy ✅ Temporal join filter added
- [x] Update `int_pick_comp_registry.sql` if model fix needed ✅ Lines 120, 148-152 modified
- [x] Update `_int_pick_comp_registry.yml` if test/grain clarification needed ✅ No changes needed
- [x] Test compilation: `make dbt-run --select int_pick_comp_registry` ✅ PASS
- [x] Verify row counts and unique transaction counts ✅ 56 entries, 56 unique, 0 duplicates

### Phase 4: Validation

- [x] Run uniqueness test: ✅ PASS (unique_int_pick_comp_registry_comp_faad_transaction_id)
- [x] Verify registry integrity: ✅ Perfect 1:1 mapping confirmed
- [x] Spot-check a few comp picks map to correct FA transactions ✅ Validated

## Acceptance Criteria

- [x] Root cause identified and documented ✅ SCD Type 2 join without temporal filter
- [x] Fix implemented in model or test ✅ Temporal join condition added
- [x] Model compiles and executes successfully ✅ PASS
- [x] **Critical**: Uniqueness test passes (0 duplicate transaction IDs) ✅ PASS
- [x] Registry has clear one-to-one or documented one-to-many relationship ✅ 1:1 mapping confirmed
- [x] Downstream comp pick queries unaffected ✅ All 17 downstream models build successfully

## Implementation Notes

**Model File**: `dbt/ff_data_transform/models/core/intermediate/int_pick_comp_registry.sql`

**YAML File**: `dbt/ff_data_transform/models/core/intermediate/_int_pick_comp_registry.yml`

**Related Models**:

- `fct_league_transactions` (source of FA transactions)
- `dim_pick` (comp picks defined here)
- `int_pick_comp_reconciliation` (uses registry for validation)

**Investigation Query Template**:

```sql
-- Find duplicate patterns
WITH dup_details AS (
  SELECT
    comp_faad_transaction_id,
    pick_id,
    season,
    round,
    player_id,
    franchise_id,
    ROW_NUMBER() OVER (
      PARTITION BY comp_faad_transaction_id
      ORDER BY season, round, pick_id
    ) as rn
  FROM main.int_pick_comp_registry
  WHERE comp_faad_transaction_id IN (
    SELECT comp_faad_transaction_id
    FROM main.int_pick_comp_registry
    GROUP BY comp_faad_transaction_id
    HAVING COUNT(*) > 1
  )
)
SELECT * FROM dup_details ORDER BY comp_faad_transaction_id, rn;
```

## Testing

1. **Current state check**:

   ```bash
   EXTERNAL_ROOT="$PWD/data/raw" \
   duckdb "$PWD/dbt/ff_data_transform/target/dev.duckdb" -c \
     "SELECT comp_faad_transaction_id, COUNT(*) as dup_count
      FROM main.int_pick_comp_registry
      GROUP BY comp_faad_transaction_id
      HAVING COUNT(*) > 1
      ORDER BY dup_count DESC
      LIMIT 10;"
   ```

2. **Run test**:

   ```bash
   make dbt-test --select int_pick_comp_registry
   ```

3. **After fix, verify**:

   ```bash
   # Should pass with 0 duplicates
   make dbt-test --select int_pick_comp_registry
   ```

## Impact

**Before Fix**:

- 19 duplicate `comp_faad_transaction_id` values
- Registry integrity compromised
- Potential for incorrect comp pick assignments
- Test failure blocking Phase 1 completion

**After Fix**:

- 0 duplicate transaction IDs ✅
- Clean one-to-one (or documented one-to-many) mapping ✅
- Registry integrity validated ✅
- Accurate comp pick tracking ✅

**Downstream Impact**:

- Comp pick reconciliation tests rely on registry accuracy
- Trade analysis uses comp picks from registry
- Draft order calculations depend on comp pick assignments

## References

- Model: `dbt/ff_data_transform/models/core/intermediate/int_pick_comp_registry.sql`
- YAML: `dbt/ff_data_transform/models/core/intermediate/_int_pick_comp_registry.yml`
- Related test: `unique_int_pick_comp_registry_comp_faad_transaction_id`
- Discovery: Comprehensive test analysis (2025-11-10)

## Notes

**Why This Ticket Exists**:

This test failure was discovered during comprehensive Phase 1 test analysis. The compensatory pick registry is a critical intermediate model that maps free agent transactions to awarded compensatory picks. Ensuring registry integrity is essential for accurate draft capital tracking.

**Sequencing**:

- Can run in parallel with P1-020, P1-023, or other Phase 1 tickets
- Should complete before Phase 2 (governance)
- No dependencies on other P1 tickets

**Compensatory Pick Background**:

In dynasty fantasy football leagues, teams that lose valuable free agents may be awarded compensatory draft picks. The registry tracks:

- Which FA transaction triggered the comp pick
- Which pick was awarded (season, round, franchise)
- Player lost and expected contract value (AAV)

Each qualifying FA loss should award exactly one comp pick (or zero if threshold not met).

## Completion Notes

**Implemented**: 2025-11-10 (commit d6eb65c)\
**Completed By**: Earlier session (referenced in commit message)

### Root Cause

The issue was caused by a **many-to-many join** between `parsed_comps` and `dim_franchise`. The `dim_franchise` dimension is an **SCD Type 2** table that tracks franchise ownership changes over time. Without a temporal filter, each comp pick transaction was matching multiple franchise records (one for each ownership period of that franchise).

**Example scenario causing duplicates**:

- Transaction date: 2023-03-15 (FAAD for 2023 season)
- Franchise ID: 5 (has 2 ownership periods: 2018-2021, 2022-present)
- Without temporal filter: Both franchise records matched → 2 rows
- With temporal filter: Only 2022-present record matches → 1 row

### Fix Strategy

**Option B: Fix Join Logic** was implemented.

Added temporal join condition to `validated_comps` CTE:

```sql
left join
    franchise_mapping fm
    on pc.comp_awarded_to_franchise_id = fm.franchise_id
    -- Temporal join: match owner in season of FAAD transaction
    and year(pc.transaction_date) between fm.season_start and coalesce(fm.season_end, 9999)
```

This ensures each comp pick transaction joins to exactly one franchise record - the one active at the time of the transaction.

### Implementation Details

**File Modified**: `dbt/ff_data_transform/models/core/intermediate/int_pick_comp_registry.sql`

**Changes**:

1. Added `season_start` and `season_end` columns to `franchise_mapping` CTE
2. Added temporal join condition using `year(transaction_date)` and `BETWEEN` clause
3. Used `COALESCE(season_end, 9999)` to handle current franchises (NULL end date)

**Lines Modified**: int_pick_comp_registry.sql:120, 148-152

### Testing Results

**Before Fix**:

- Total registry entries: 75 (estimated)
- Unique transactions: 56
- Duplicates: 19 ❌

**After Fix**:

- Total registry entries: 56
- Unique transactions: 56
- Duplicates: 0 ✅

**Test Results** (2025-11-12 verification):

```bash
make dbt-test --select int_pick_comp_registry
# Result: 7 of 7 tests PASS (including unique_int_pick_comp_registry_comp_faad_transaction_id)
```

**Registry Integrity Verification**:

```sql
SELECT
    COUNT(*) as total_registry_entries,        -- 56
    COUNT(DISTINCT comp_faad_transaction_id),  -- 56
    COUNT(DISTINCT pick_id)                     -- 56
FROM int_pick_comp_registry;
```

Result: Perfect 1:1 mapping ✅

### Impact

**Data Quality**:

- ✅ Zero duplicate transaction IDs (was 19)
- ✅ Clean one-to-one mapping (registry integrity restored)
- ✅ Accurate comp pick tracking
- ✅ All uniqueness tests passing

**Downstream Models**:

- `int_pick_comp_reconciliation` - now operates on clean data
- `int_pick_comp_sequenced` - no longer affected by duplicate sequences
- `dim_pick` - comp picks correctly identified
- `fct_league_transactions` - transaction-to-pick mapping accurate

**Related Tickets**:

- Part of the same fix session that addressed P1-020, P1-022, and P1-023
- Documented in: `docs/investigations/P1-020-through-P1-024_root_cause_analysis_2025-11-10.md`

### Lessons Learned

1. **SCD Type 2 joins require temporal filters** - Always add date range conditions when joining to slowly changing dimensions
2. **Ephemeral models need investigation via downstream tables** - Use `dbt compile` and inline SQL for debugging
3. **Test failures reveal join issues** - Uniqueness test failures often indicate Cartesian product problems
4. **Franchise ownership changes** - The league has had multiple ownership transitions, making temporal accuracy critical
