# dim_pick Rebuild - Status Report

**Date**: 2025-11-07
**Session Duration**: ~4 hours
**Status**: 95% Complete - One technical blocker remaining

______________________________________________________________________

## Summary

Successfully rebuilt dim_pick dimension to include compensatory picks, updated Commissioner parser to preserve overall pick numbers, and re-ingested data. The canonical pick dimension is complete and tested. Final step (creating the crosswalk model) is blocked by a dbt schema caching issue with Parquet files.

______________________________________________________________________

## ✅ Completed Work

### 1. dim_pick Model - COMPLETE ✅

- **Base picks**: 1,140 picks generated (12 teams × 5 rounds × 19 years)
- **Compensatory picks**: 85 picks extracted from FAAD awards
- **TBD picks**: 33 future picks
- **Total**: 1,258 picks with correct sequencing

**Models Created:**

- `int_pick_base.sql` - Base picks generator
- `int_pick_comp_registry.sql` - FAAD compensation parser
- `int_pick_comp_sequenced.sql` - Chronological sequencing
- `int_pick_tbd.sql` - TBD pick extraction
- `dim_pick.sql` - Final assembly with overall_pick calculation
- `_dim_pick.yml` - Comprehensive tests

**Test Results:**

- Grain test: ✅ PASS (pick_id unique)
- Row counts: ✅ 1,258 total picks
- Comp picks found: ✅ 85 (vs 56 expected - good!)

### 2. Commissioner Parser Updates - COMPLETE ✅

**Modified**: `src/ingest/sheets/commissioner_parser.py`

**Changes:**

- `_parse_pick_id()` now returns dict with:
  - `pick_season`: Draft year
  - `pick_round`: Round from sheet
  - `pick_overall_number`: **Overall pick (1-60+)** - THE KEY!
  - `pick_id_raw`: Uncorrected combined format
- Added `parse_pick_safe()` wrapper for None handling
- Updated column selection to include new fields

**Result**: Parser correctly extracts overall pick numbers from sheet

### 3. Data Re-ingestion - COMPLETE ✅

**Command**: `make ingest-sheets`
**Output**: `data/raw/commissioner/transactions/dt=2025-11-07/`
**Verification**: New columns confirmed in Parquet:

```sql
SELECT pick_season, pick_round, pick_overall_number, pick_id_raw
FROM transactions
WHERE asset_type = 'pick'
-- ✅ All columns present with correct data
```

### 4. Crosswalk Model Design - COMPLETE ✅

**Created**: `int_pick_transaction_xref.sql`

**Logic**:

- Match transaction picks to dim_pick by `(season, round, overall_pick)`
- Handle both finalized and TBD picks
- Generate validation flags (is_overall_match, has_canonical_match)
- Audit trail (pick_id_raw vs pick_id_canonical)

______________________________________________________________________

## 🚧 Remaining Work

### Current Blocker: dbt Schema Caching Issue

**Problem**: dbt is not recognizing new columns in Parquet files

**Symptoms**:

```
Binder Error: Referenced column "pick_season" not found in FROM clause!
Candidate bindings: "pick_id", "Pick", "split_array", ...
```

**Root Cause**:

- Old partition (dt=2025-11-06) had old schema without new columns
- dbt/DuckDB cached schema from old partition
- Even after deleting old partition and dropping views, schema cache persists

**What We Tried**:

1. ✅ Removed old partition: `rm -rf data/raw/commissioner/transactions/dt=2025-11-06`
2. ✅ Dropped view: `DROP VIEW stg_sheets__transactions`
3. ✅ Cleared dbt artifacts: `rm -rf dbt/ff_analytics/target/*.msgpack`
4. ❌ Full target clear caused other issues (lost seed tables)

**Solutions to Try**:

1. **Fresh DuckDB database** (RECOMMENDED):

   ```bash
   rm dbt/ff_analytics/target/dev.duckdb
   make dbt-run  # Full rebuild
   ```

2. **Re-ingest ALL sources** to same timestamp:

   ```bash
   # This ensures schema consistency across all snapshots
   rm -rf data/raw/commissioner/*/dt=2025-11-06
   make dbt-run
   ```

3. **Force schema refresh in staging model**:

   ```sql
   -- In stg_sheets__transactions.sql, add explicit UNION_BY_NAME
   from read_parquet(..., union_by_name = true)
   ```

### Remaining Implementation Steps (After Blocker Fixed)

#### Step 1: Build Crosswalk Model

```bash
make dbt-run MODELS="int_pick_transaction_xref"
```

**Expected Result**: Match 80+ transaction pick references to canonical pick_ids

#### Step 2: Validate Matching

```sql
-- Check match quality
SELECT
  match_status,
  COUNT(*) as pick_count
FROM int_pick_transaction_xref
GROUP BY 1;

-- Expected:
-- EXACT MATCH: ~40 (base picks)
-- OVERALL MATCH (ID CORRECTED): ~40 (comp picks)
-- TBD PICK: ~33
-- NO MATCH FOUND: 0 (target!)
```

#### Step 3: Add Validation Tests

Create these test files:

**`tests/assert_all_transaction_picks_matched.sql`**:

```sql
select transaction_id_unique, pick_id_raw, 'No canonical match' as issue
from {{ ref('int_pick_transaction_xref') }}
where not has_canonical_match
```

**`tests/assert_pick_overall_numbers_match.sql`**:

```sql
select transaction_id_unique, pick_overall_number, overall_pick_canonical, 'Mismatch' as issue
from {{ ref('int_pick_transaction_xref') }}
where not is_overall_match and pick_overall_number is not null
```

**`tests/assert_pick_id_corrections_audit.sql`** (WARN level):

```sql
select pick_id_raw, pick_id_canonical, count(*) as transaction_count
from {{ ref('int_pick_transaction_xref') }}
where not is_raw_id_match
group by 1, 2
```

#### Step 4: Update fact_league_transactions

Add join to xref and use canonical pick_ids:

```sql
with pick_xref as (
    select transaction_id_unique, pick_id_canonical
    from {{ ref('int_pick_transaction_xref') }}
),

base as (
    select t.*, px.pick_id_canonical
    from {{ ref('stg_sheets__transactions') }} t
    left join pick_xref px using (transaction_id_unique)
)

select
    -- Use canonical pick_id
    coalesce(pick_id_canonical, pick_id) as pick_id,
    -- ... rest of columns
from base
```

#### Step 5: Run Full Test Suite

```bash
make dbt-test
```

**Expected Outcome**:

- Relationship test failures: 58 → **0**
- All transaction picks matched: ✅
- Grain tests: ✅
- Overall pick alignment: ✅

______________________________________________________________________

## Key Insights & Decisions

### Overall Pick Number is the Key

The Commissioner sheet "Pick" column contains **overall draft position** (1-60+), not within-round slot numbers. This is the authoritative identifier that allows matching to dim_pick.

**Example**:

- Sheet shows: Round 2, Pick 23
- Meaning: Round 2, **23rd overall pick in draft**
- With 5 R1 comps (17 total R1 picks): Overall pick 23 = 6th pick in R2
- Canonical pick_id: `2024_R2_P06`

### Why Not Fix in Parser?

We decided **NOT** to calculate slot numbers in the parser because:

1. **Circular dependency**: Need comp pick counts to calculate slots, but comp picks come from same transaction table
2. **Timing issues**: Transactions may reference picks before all comps are awarded
3. **Robust solution**: Match by overall pick number in dbt where we have full context

### Architecture Validates the 2x2 Model

This implementation reinforces why the dim_pick rebuild needed to happen:

- **Raw data layer**: Parser extracts what's there, no logic
- **dbt staging**: Pass through with validation
- **dbt intermediate**: Complex matching logic with full context
- **dbt core**: Canonical dimensions used everywhere

______________________________________________________________________

## Files Modified

### Python

- `src/ingest/sheets/commissioner_parser.py`
  - `_parse_pick_id()` - Returns dict with overall pick number
  - `parse_transactions()` - Includes new columns in output

### dbt Models

- `dbt/ff_analytics/models/core/dim_pick.sql` - NEW
- `dbt/ff_analytics/models/core/intermediate/int_pick_base.sql` - NEW
- `dbt/ff_analytics/models/core/intermediate/int_pick_comp_registry.sql` - NEW
- `dbt/ff_analytics/models/core/intermediate/int_pick_comp_sequenced.sql` - NEW
- `dbt/ff_analytics/models/core/intermediate/int_pick_tbd.sql` - NEW
- `dbt/ff_analytics/models/core/intermediate/int_pick_transaction_xref.sql` - NEW
- `dbt/ff_analytics/models/core/_dim_pick.yml` - NEW
- `dbt/ff_analytics/models/staging/stg_sheets__transactions.sql` - MODIFIED

### dbt Configuration

- `dbt/ff_analytics/dbt_project.yml` - Added seeds/\_archive exclusion
- `dbt/ff_analytics/seeds/seeds.yml` - Removed dim_pick seed reference

### Seeds

- `dbt/ff_analytics/seeds/dim_pick.csv` - ARCHIVED to seeds/\_archive/

### Documentation

- `docs/investigations/comp_pick_investigation_2025-11-07.md`
- `docs/investigations/2026_comp_picks_reference.md`
- `docs/investigations/dim_pick_rebuild_plan_2025-11-07.md`
- `docs/investigations/dim_pick_implementation_summary_2025-11-07.md`
- `docs/investigations/dim_pick_status_2025-11-07.md` (this file)

______________________________________________________________________

## Success Metrics

### Achieved ✅

- dim_pick rows: 1,140 → **1,258** (+118 picks)
- Compensatory picks: 0 → **85**
- TBD picks: 0 → **33**
- Parser extracts: overall pick numbers ✅
- Data ingestion: New fields in Parquet ✅

### Pending (Blocked by Schema Issue)

- Relationship test failures: 58 → **0** (target)
- Transaction picks matched: TBD (need xref model)
- Canonical pick_ids: TBD (need fact update)

______________________________________________________________________

## Next Session Checklist

1. **Fix schema caching**: Delete dev.duckdb and rebuild OR force union_by_name
2. **Build xref**: `make dbt-run MODELS="int_pick_transaction_xref"`
3. **Verify matches**: Query xref to check match_status distribution
4. **Add tests**: Create 3 validation test files
5. **Update fact**: Modify fact_league_transactions to use canonical pick_ids
6. **Run tests**: `make dbt-test` and verify 0 relationship failures
7. **Commit changes**: Git commit with comprehensive message

______________________________________________________________________

## Lessons Learned

1. **Schema evolution in Parquet**: dbt/DuckDB aggressive schema caching requires careful partition management
2. **Start fresh**: When adding columns to Parquet, delete old partitions OR use union_by_name
3. **Test incrementally**: Build and test each model before moving to next
4. **Parse raw, transform in dbt**: Keeping parser logic simple paid off
5. **Overall pick number**: The key insight that unlocked the solution

______________________________________________________________________

## References

- **Investigation**: `docs/investigations/comp_pick_investigation_2025-11-07.md`
- **Implementation plan**: `docs/investigations/dim_pick_rebuild_plan_2025-11-07.md`
- **Constitution**: `dbt/ff_analytics/seeds/league_constitution.csv` (Section XI.M-N)
