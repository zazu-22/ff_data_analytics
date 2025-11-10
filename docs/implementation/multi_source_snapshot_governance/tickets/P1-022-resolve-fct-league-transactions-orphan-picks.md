# Ticket P1-022: Resolve fct_league_transactions Orphan Pick References

**Phase**: 1 - Foundation\
**Estimated Effort**: Small-Medium (2-4 hours)\
**Dependencies**: P1-012 (transactions snapshot governance)\
**Priority**: Medium - 5 fact table orphans (down from 41) + 41 staging orphans

## Objective

Investigate and resolve orphan pick references where transaction records reference `pick_id` values that don't have matching records in `dim_pick`:

1. **5 orphan picks** in `fct_league_transactions` (fact table)
2. **41 orphan picks** in `stg_sheets__transactions` (staging table)

## Context

During comprehensive dbt test analysis (2025-11-10), two related orphan pick tests showed warnings:

**Test Warnings**:

```
WARN 5 relationships_fct_league_transactions_pick_id__pick_id__ref_dim_pick_
Got 5 results, configured to warn if != 0

WARN 41 relationships_stg_sheets__transactions_pick_id__pick_id__ref_dim_pick_
Got 41 results, configured to warn if != 0
```

**Good News**: The fact table improved significantly from **41 orphan picks** (pre-P1-012) to **5 orphan picks** (post-P1-012) after the snapshot governance fix. The P1-012 implementation reduced fact table orphan picks by **87%**.

**Gap Identified**: The staging table `stg_sheets__transactions` still has **41 orphan picks** - these are the upstream source of the issue and need investigation.

**Root Cause Hypothesis**:

Transaction records reference draft picks that either:

1. **Data lag**: Pick hasn't been created in `dim_pick` yet (timing issue)
2. **Naming mismatch**: Transaction uses different `pick_id` format than `dim_pick`
3. **Legacy picks**: Old transaction references using deprecated pick naming
4. **Invalid references**: Data entry errors in transaction records
5. **Compensatory picks**: Special pick types not properly tracked in `dim_pick`

**Why This Matters**:

- Foreign key integrity ensures reliable joins between transactions and picks
- Orphan picks prevent accurate trade analysis (can't resolve pick details)
- Pick valuation models need complete transaction history
- 5 remaining orphans are likely edge cases worth documenting

**Important**: The snapshot governance fix in P1-012 significantly improved this issue (41→5). The remaining 5 are likely legitimate data quality edge cases.

## Tasks

### Phase 1: Investigation

**Fact Table (5 orphans)**:

- [ ] Identify the 5 fact table orphan picks:
  ```bash
  EXTERNAL_ROOT="/Users/jason/code/ff_analytics/data/raw" \
  DBT_DUCKDB_PATH="/Users/jason/code/ff_analytics/dbt/ff_data_transform/target/dev.duckdb" \
  uv run dbt test --select relationships_fct_league_transactions_pick_id__pick_id__ref_dim_pick_ \
    --store-failures \
    --project-dir /Users/jason/code/ff_analytics/dbt/ff_data_transform \
    --profiles-dir /Users/jason/code/ff_analytics/dbt/ff_data_transform
  ```
- [ ] Query the orphan pick details:
  ```sql
  SELECT
    t.pick_id,
    t.transaction_type,
    t.season,
    t.transaction_date,
    t.from_franchise_name,
    t.to_franchise_name,
    t.pick_season,
    t.pick_round
  FROM main.fct_league_transactions t
  LEFT JOIN main.dim_pick p ON t.pick_id = p.pick_id
  WHERE t.pick_id IS NOT NULL
    AND p.pick_id IS NULL
  ORDER BY t.transaction_date;
  ```
- [ ] Categorize each orphan by root cause:
  - [ ] Check if pick exists in `stg_sheets__draft_pick_holdings`
  - [ ] Check if pick naming format matches `dim_pick` conventions
  - [ ] Check if transaction is old/legacy
  - [ ] Check if pick is compensatory or special type
- [ ] Document each orphan with explanation

**Staging Table (41 orphans)**:

- [ ] Identify the 41 staging table orphan picks:
  ```bash
  EXTERNAL_ROOT="/Users/jason/code/ff_analytics/data/raw" \
  DBT_DUCKDB_PATH="/Users/jason/code/ff_analytics/dbt/ff_data_transform/target/dev.duckdb" \
  uv run dbt test --select relationships_stg_sheets__transactions_pick_id__pick_id__ref_dim_pick_ \
    --store-failures \
    --project-dir /Users/jason/code/ff_analytics/dbt/ff_data_transform \
    --profiles-dir /Users/jason/code/ff_analytics/dbt/ff_data_transform
  ```
- [ ] Query the staging orphan pick details:
  ```sql
  SELECT
    t.pick_id,
    t.transaction_type,
    t.transaction_date,
    t.from_franchise_name,
    t.to_franchise_name,
    COUNT(*) as transaction_count
  FROM main.stg_sheets__transactions t
  LEFT JOIN main.dim_pick p ON t.pick_id = p.pick_id
  WHERE t.pick_id IS NOT NULL
    AND p.pick_id IS NULL
  GROUP BY 1,2,3,4,5
  ORDER BY t.transaction_date;
  ```
- [ ] Determine relationship between staging (41) and fact (5) orphans:
  - [ ] Are the 5 fact orphans a subset of the 41 staging orphans?
  - [ ] Why do 36 staging orphans not appear in fact table? (filtered out? aggregated?)
- [ ] Categorize staging orphans by root cause (same categories as fact table)
- [ ] Document overlap and differences

### Phase 2: Fix Strategy

Based on categorization, determine approach for each orphan:

**Option A: Create Missing Picks in dim_pick**

- [ ] Picks are legitimate but missing from `dim_pick`
- [ ] Add missing pick records to `dim_pick` source/seed
- [ ] Or: Fix `dim_pick` logic to include these pick types

**Option B: Fix pick_id References in Transactions**

- [ ] Transaction records use wrong `pick_id` format
- [ ] Update transaction data or add pick_id mapping logic
- [ ] Standardize pick naming conventions

**Option C: Document as Expected Exceptions**

- [ ] Orphans are legacy/invalid references that can't be resolved
- [ ] Update test to exclude these specific picks
- [ ] Document why these are expected failures

**Option D: Delete Invalid Transaction Records**

- [ ] Transaction records are erroneous data
- [ ] Remove from source or filter in staging model
- [ ] Document data quality issue

### Phase 3: Implementation

- [ ] Implement chosen fix strategy for each orphan
- [ ] Test changes don't break existing relationships
- [ ] Verify transaction grain still intact

### Phase 4: Validation

- [ ] Re-run relationship test:
  ```bash
  EXTERNAL_ROOT="/Users/jason/code/ff_analytics/data/raw" \
  DBT_DUCKDB_PATH="/Users/jason/code/ff_analytics/dbt/ff_data_transform/target/dev.duckdb" \
  uv run dbt test --select fct_league_transactions \
    --project-dir /Users/jason/code/ff_analytics/dbt/ff_data_transform \
    --profiles-dir /Users/jason/code/ff_analytics/dbt/ff_data_transform
  ```
- [ ] Verify orphan count: 5 → 0 (or documented exceptions)
- [ ] Spot-check that resolved picks now join correctly
- [ ] Verify no regression in other transaction tests

## Acceptance Criteria

- [ ] All 5 fact table orphan picks investigated and categorized
- [ ] All 41 staging table orphan picks investigated and categorized
- [ ] Relationship between staging and fact orphans documented
- [ ] Root cause documented for each orphan
- [ ] Fix strategy implemented (data fix, logic fix, or documented exception)
- [ ] Both relationship tests either PASS (0 orphans) or WARN with documented exceptions only
- [ ] No regression in transaction grain or other tests

## Implementation Notes

**Tests**:

1. Fact table: `dbt/ff_data_transform/models/core/_fct_league_transactions.yml`

   ```yaml
   relationships_fct_league_transactions_pick_id__pick_id__ref_dim_pick_
   ```

2. Staging table: `dbt/ff_data_transform/models/staging/_stg_sheets__transactions.yml`

   ```yaml
   relationships_stg_sheets__transactions_pick_id__pick_id__ref_dim_pick_
   ```

**Models**:

- Fact: `dbt/ff_data_transform/models/core/fct_league_transactions.sql`
- Staging: `dbt/ff_data_transform/models/staging/stg_sheets__transactions.sql` (P1-012)
- Dimension: `dbt/ff_data_transform/models/core/dim_pick.sql`

**Investigation Queries**:

```sql
-- Find orphan pick details with transaction context
SELECT
  t.pick_id,
  t.pick_season,
  t.pick_round,
  t.pick_original_owner,
  t.transaction_type,
  t.transaction_date,
  t.season,
  COUNT(*) as transaction_count
FROM main.fct_league_transactions t
LEFT JOIN main.dim_pick p ON t.pick_id = p.pick_id
WHERE t.asset_type = 'pick'
  AND t.pick_id IS NOT NULL
  AND p.pick_id IS NULL
GROUP BY 1,2,3,4,5,6,7
ORDER BY t.transaction_date;

-- Check if orphan picks exist in staging
SELECT DISTINCT pick_id
FROM main.stg_sheets__draft_pick_holdings
WHERE pick_id IN (
  SELECT DISTINCT t.pick_id
  FROM main.fct_league_transactions t
  LEFT JOIN main.dim_pick p ON t.pick_id = p.pick_id
  WHERE t.pick_id IS NOT NULL AND p.pick_id IS NULL
);

-- Check dim_pick for similar naming patterns
SELECT pick_id
FROM main.dim_pick
WHERE pick_id LIKE '%[orphan_year]%'
  OR pick_id LIKE '%R[orphan_round]%';
```

**Common Orphan Patterns**:

1. **Compensatory picks**: Format like `2023_R3_COMP_A` not in `dim_pick`
2. **Legacy format**: Old naming like `2019-3-14` vs new `2019_R3_14`
3. **TBD picks**: Transaction references `2023_R1_TBD` but `dim_pick` has different TBD handling
4. **Traded future picks**: Picks traded before they exist in pick inventory
5. **Data entry errors**: Typos in pick_id field

## Testing

1. **Run test with failure storage**:

   ```bash
   EXTERNAL_ROOT="/Users/jason/code/ff_analytics/data/raw" \
   DBT_DUCKDB_PATH="/Users/jason/code/ff_analytics/dbt/ff_data_transform/target/dev.duckdb" \
   uv run dbt test --select relationships_fct_league_transactions_pick_id__pick_id__ref_dim_pick_ \
     --store-failures \
     --project-dir /Users/jason/code/ff_analytics/dbt/ff_data_transform \
     --profiles-dir /Users/jason/code/ff_analytics/dbt/ff_data_transform
   ```

2. **Query stored failures**:

   ```bash
   EXTERNAL_ROOT="/Users/jason/code/ff_analytics/data/raw" \
   duckdb "/Users/jason/code/ff_analytics/dbt/ff_data_transform/target/dev.duckdb" -c \
     "SELECT * FROM main.relationships_fct_league_trans_[hash]_failures;"
   ```

3. **After fix, verify**:

   ```bash
   make dbt-test --select fct_league_transactions
   # Expect: relationship test PASS (0 orphans) or WARN with documented exceptions
   ```

## Impact

**Before Fix**:

- **Fact table**: 41 orphan picks (pre-P1-012) → 5 orphan picks (post-P1-012) ✅ 87% improvement!
- **Staging table**: 41 orphan picks (unchanged)
- Foreign key integrity warnings at both layers
- Incomplete trade analysis for affected picks

**After Fix**:

- **Fact table**: 0 orphan picks (or documented exceptions) ✅
- **Staging table**: 0 orphan picks (or documented exceptions) ✅
- Full foreign key integrity at both layers ✅
- Complete trade history for all picks ✅
- Pick valuation models have complete data ✅

**Downstream Impact**:

- Trade analysis relies on complete pick transaction history
- Pick valuation models need accurate trade context
- Draft capital analysis tracks pick movements via transactions

## References

- Test: `dbt/ff_data_transform/models/core/_fct_league_transactions.yml`
- Fact table: `dbt/ff_data_transform/models/core/fct_league_transactions.sql`
- Dimension: `dbt/ff_data_transform/models/core/dim_pick.sql`
- Staging: `dbt/ff_data_transform/models/staging/stg_sheets__transactions.sql` (P1-012)
- Discovery: During P1-012 downstream testing (2025-11-09)
- Related: P1-012 documentation noted "41 orphan picks" before fix

## Notes

**Why This Ticket Exists**:

P1-012 fixed the snapshot governance for transactions and reduced orphan picks from 41 to 5 (87% improvement). The remaining 5 orphans are likely legitimate edge cases (compensatory picks, legacy references, etc.) worth investigating and resolving.

**Sequencing**:

- AFTER P1-012 (snapshot governance fix already helped significantly) ✅
- Can be done in parallel with other Phase 1 tickets
- Not blocking Phase 2 (Governance)
- Low priority since count is small and test is warning-level

**Expected Outcome**:

Most likely, this will result in:

1. Adding a few missing picks to `dim_pick` (2-3 picks)
2. Documenting 1-2 legacy picks as expected exceptions
3. Fixing 1-2 data entry errors in transaction records
4. Test passes with 0 orphans or warns only on documented exceptions
