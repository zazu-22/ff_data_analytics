# Ticket P1-024: Fix int_pick_comp_registry Duplicate Transaction IDs

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

- [ ] Query to identify duplicate transaction IDs:
  ```sql
  SELECT comp_faad_transaction_id, COUNT(*) as dup_count
  FROM main.int_pick_comp_registry
  GROUP BY comp_faad_transaction_id
  HAVING COUNT(*) > 1
  ORDER BY dup_count DESC;
  ```
- [ ] Examine full records for duplicates:
  ```sql
  WITH dups AS (
    SELECT comp_faad_transaction_id
    FROM main.int_pick_comp_registry
    GROUP BY comp_faad_transaction_id
    HAVING COUNT(*) > 1
  )
  SELECT pcr.*
  FROM main.int_pick_comp_registry pcr
  INNER JOIN dups d ON pcr.comp_faad_transaction_id = d.comp_faad_transaction_id
  ORDER BY pcr.comp_faad_transaction_id, pcr.pick_id;
  ```
- [ ] Check if duplicates have different pick_ids (same transaction → multiple picks):
  ```sql
  SELECT comp_faad_transaction_id,
         COUNT(DISTINCT pick_id) as unique_picks,
         COUNT(*) as total_rows
  FROM main.int_pick_comp_registry
  GROUP BY comp_faad_transaction_id
  HAVING COUNT(*) > 1;
  ```
- [ ] Review model logic in `int_pick_comp_registry.sql`:
  - [ ] Check for missing DISTINCT or QUALIFY
  - [ ] Identify any Cartesian products in joins
  - [ ] Review window functions and partitioning
- [ ] Document root cause with SQL evidence

### Phase 2: Determine Fix Strategy

Based on investigation, choose approach:

**Option A: Deduplication Logic**

- [ ] Model produces valid duplicates due to join logic
- [ ] Add QUALIFY ROW_NUMBER() to select correct record per transaction
- [ ] Determine correct ranking logic (e.g., by season, round, or creation date)

**Option B: Fix Join Logic**

- [ ] Model has incorrect join creating Cartesian product
- [ ] Fix join conditions to prevent duplicates
- [ ] Add missing join keys

**Option C: Grain Clarification**

- [ ] Model intentionally allows multiple picks per transaction
- [ ] Update test to reflect correct grain (e.g., include pick_id in uniqueness)
- [ ] Document grain in model YAML

**Option D: Source Data Quality**

- [ ] Source data has legitimate duplicate transactions
- [ ] Filter or consolidate source data before registry creation
- [ ] Document exceptions in model comments

### Phase 3: Implementation

- [ ] Implement chosen fix strategy
- [ ] Update `int_pick_comp_registry.sql` if model fix needed
- [ ] Update `_int_pick_comp_registry.yml` if test/grain clarification needed
- [ ] Test compilation: `make dbt-run --select int_pick_comp_registry`
- [ ] Verify row counts and unique transaction counts

### Phase 4: Validation

- [ ] Run uniqueness test:
  ```bash
  make dbt-test --select int_pick_comp_registry
  # Expect: unique test PASS (0 duplicates)
  ```
- [ ] Verify registry integrity:
  ```sql
  SELECT
    COUNT(*) as total_registry_entries,
    COUNT(DISTINCT comp_faad_transaction_id) as unique_transactions,
    COUNT(DISTINCT pick_id) as unique_picks
  FROM main.int_pick_comp_registry;
  ```
- [ ] Spot-check a few comp picks map to correct FA transactions

## Acceptance Criteria

- [ ] Root cause identified and documented
- [ ] Fix implemented in model or test
- [ ] Model compiles and executes successfully
- [ ] **Critical**: Uniqueness test passes (0 duplicate transaction IDs)
- [ ] Registry has clear one-to-one or documented one-to-many relationship
- [ ] Downstream comp pick queries unaffected

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
