# Ticket P1-026: Fix resolve_player_id_from_name Macro Cartesian Product Bug

**Phase**: 1 - Foundation\
**Estimated Effort**: Small (1-2 hours)\
**Dependencies**: P1-019 (introduced by player_id resolution refactor)\
**Priority**: **CRITICAL** - Causes 6.8x row duplication in stg_sheets\_\_transactions (27,213 rows instead of 3,999)\
**Status**: COMPLETE

## Objective

Fix the `resolve_player_id_from_name` macro to prevent cartesian product joins that create massive row duplication in staging models.

## Context

During P1-019 implementation (Byron Young player_id resolution), the new `resolve_player_id_from_name` macro was created to centralize player ID resolution logic. However, the macro has a design flaw that causes many-to-many joins, resulting in severe data duplication.

**Critical Impact**:

```
stg_sheets__transactions:
- Expected rows: 3,999 (unique transaction_id_unique values)
- Actual rows: 27,213 (6.8x duplication)
- Test failure: unique_stg_sheets__transactions_transaction_id_unique (3,563 duplicates)
```

**Root Cause**:

The `with_player_id_lookup` CTE in the macro:

1. Selects `FROM` the source CTE (e.g., `with_alias`), which contains ALL transaction rows
2. Creates one lookup row per source transaction (not per unique player)
3. Joins back to the source CTE on `(player_name_canonical, position)`
4. Creates cartesian product: every transaction with "no selection" matches every other "no selection" transaction

**Example Duplication**:

```sql
-- 72 transactions with player_name = "no selection" and position = "-"
-- Each joins to all 72 lookup rows (72 × 72 = 5,184 duplicates for just these rows)
SELECT transaction_id_unique, COUNT(*) as duplicate_count
FROM main.stg_sheets__transactions
WHERE transaction_id_unique = '156_0'
GROUP BY transaction_id_unique;

-- Result: 72 duplicates (should be 1)
```

## Technical Details

**Current Macro Logic** (line 173-220 in `macros/resolve_player_id_from_name.sql`):

```sql
with_player_id_lookup as (
    -- This CTE pulls FROM the source, creating one row per source transaction
    select
      src.player_name_canonical,
      src.position,
      coalesce(cast(xwalk.player_id as bigint), cast(txn.player_id as bigint)) as player_id,
      cast(xwalk.mfl_id as bigint) as mfl_id,
      cast(xwalk.canonical_name as varchar) as canonical_name
    from {{ source_cte }} src  -- ❌ This pulls ALL source rows, not distinct players
    left join best_crosswalk_match xwalk
      on src.player_name_canonical = xwalk.player_name_canonical
      and src.position = xwalk.position
    left join transaction_player_ids txn
      on lower(trim(src.player_name_canonical)) = txn.player_name_lower
      -- position filtering...
)

-- Then the calling model joins back:
from {{ source_cte }} wa
left join with_player_id_lookup pid
    on wa.player_name_canonical = pid.player_name_canonical
    and wa.position = pid.position
-- ❌ Many-to-many join: every source row matches multiple lookup rows
```

**Problem**: `with_player_id_lookup` has N rows (one per source transaction), not M rows (one per unique player). The join creates N × N/M cartesian product.

## Solution

The `with_player_id_lookup` CTE must return **distinct player mappings only**, not tied to source transaction rows.

**Fixed Logic**:

```sql
distinct_players as (
    -- Get unique (player_name_canonical, position) combinations from source
    select distinct
        player_name_canonical,
        position
    from {{ source_cte }}
),

with_player_id_lookup as (
    -- Resolve player_id for unique players only (not per source row)
    select
      dp.player_name_canonical,
      dp.position,
      coalesce(cast(xwalk.player_id as bigint), cast(txn.player_id as bigint)) as player_id,
      cast(xwalk.mfl_id as bigint) as mfl_id,
      cast(xwalk.canonical_name as varchar) as canonical_name
    from distinct_players dp  -- ✅ Only unique players
    left join best_crosswalk_match xwalk
      on dp.player_name_canonical = xwalk.player_name_canonical
      and dp.position = xwalk.position
    left join transaction_player_ids txn
      on lower(trim(dp.player_name_canonical)) = txn.player_name_lower
      -- position filtering...
)

-- Then the calling model joins 1:1 (or N:1 for unmapped players):
from {{ source_cte }} wa
left join with_player_id_lookup pid
    on wa.player_name_canonical = pid.player_name_canonical
    and wa.position = pid.position
-- ✅ Clean join: each source row matches exactly one lookup row
```

## Tasks

- [x] Add `distinct_players` CTE to extract unique `(player_name_canonical, position)` combinations
- [x] Change `with_player_id_lookup` to select FROM `distinct_players` instead of `{{ source_cte }}`
- [x] Update all join logic to use the new CTE structure
- [x] Test with `stg_sheets__transactions` to verify row count drops from 27,213 to ~4,000
- [x] Run `dbt test --select stg_sheets__transactions` and verify `unique_transaction_id_unique` passes
- [x] Verify no regressions in other staging models that use the macro:
  - `stg_sheets__contracts_active`
  - `stg_sheets__contracts_cut`
- [x] Verify Byron Young resolution still works correctly (player_id 8771, not 8768)

## Acceptance Criteria

- [x] `stg_sheets__transactions` row count matches `COUNT(DISTINCT transaction_id_unique)` (~4,000 rows)
- [x] `unique_stg_sheets__transactions_transaction_id_unique` test passes (0 duplicates)
- [x] `assert_canonical_player_key_alignment` test still passes
- [x] No cartesian product warnings in compiled SQL
- [x] All staging models using the macro build successfully

## Testing

**Verification Query 1: Row Count Before/After**

```sql
-- Before fix: 27,213 rows
-- After fix: ~4,000 rows
SELECT
    COUNT(*) as total_rows,
    COUNT(DISTINCT transaction_id_unique) as unique_keys
FROM main.stg_sheets__transactions;
```

**Verification Query 2: Duplicate Analysis**

```sql
-- Before fix: 3,563 duplicates
-- After fix: 0 duplicates
SELECT
    transaction_id_unique,
    COUNT(*) as duplicate_count
FROM main.stg_sheets__transactions
GROUP BY transaction_id_unique
HAVING COUNT(*) > 1
ORDER BY duplicate_count DESC;
```

**Verification Query 3: Byron Young Resolution**

```sql
-- Should still resolve to player_id 8771 (DE/LAR), not 8768 (DT/PHI)
SELECT DISTINCT
    player_name,
    position,
    player_id
FROM main.stg_sheets__transactions
WHERE player_name ILIKE '%Byron Young%'
ORDER BY player_id;

-- Expected: 1 row with player_id = 8771
```

## Files Affected

- `dbt/ff_data_transform/macros/resolve_player_id_from_name.sql` - Macro definition (lines 173-220)
- `dbt/ff_data_transform/models/staging/stg_sheets__transactions.sql` - Consumer (uses macro)
- `dbt/ff_data_transform/models/staging/stg_sheets__contracts_active.sql` - Consumer
- `dbt/ff_data_transform/models/staging/stg_sheets__contracts_cut.sql` - Consumer

## References

- **Parent Ticket**: P1-019 (investigate-sleeper-commissioner-roster-parity)
- **Macro File**: `dbt/ff_data_transform/macros/resolve_player_id_from_name.sql`
- **Test File**: `dbt/ff_data_transform/models/staging/_stg_sheets__transactions.yml`
- **Root Cause Analysis**: Identified 2025-11-12 during P1-019 debugging

## Priority Justification

**CRITICAL Priority** because:

1. **Data Integrity**: Creates 6.8x row duplication in transaction history
2. **Blocking**: Prevents `stg_sheets__transactions` from passing tests
3. **Cascading Impact**: Corrupts all downstream models that depend on transactions
4. **Newly Introduced**: Bug was introduced in P1-019, not a pre-existing issue
5. **High Severity**: Unique key test failure (3,563 duplicates) is a data corruption signal

This should be fixed **immediately before** any other data quality tickets, as it's a regression that breaks previously working models.

## Implementation Notes

**Why This Happened**:

The macro was designed to be "flexible" by pulling from the source CTE directly, assuming it would handle any source structure. However, this created an accidental cartesian product because the macro author didn't realize the CTE would be joined back to the same source.

**Design Principle**:

Lookup/resolution CTEs should always work with **unique keys** (players, in this case), not source rows. The calling model is responsible for joining the lookup back to source rows.

**Testing Strategy**:

After fixing, run full test suite to catch any other models affected:

```bash
just dbt-run
just dbt-test
```

Focus on staging models that use `resolve_player_id_from_name`:

- `stg_sheets__transactions`
- `stg_sheets__contracts_active`
- `stg_sheets__contracts_cut`

## Completion Notes

**Implemented**: 2025-11-12

**Changes Made**:

- Added `distinct_players` CTE in `resolve_player_id_from_name` macro (line 173-180)
- Changed `with_player_id_lookup` to select FROM `distinct_players` instead of `{{ source_cte }}` (line 195)
- Updated all references from `src.` to `dp.` in position filtering logic (lines 207-227)

**Test Results**:

- **Row count reduction**: 27,213 → 3,999 rows (100% match to unique keys)
- **Duplicate elimination**: 0 duplicates (was 3,563)
- **Grain test**: `unique_stg_sheets__transactions_transaction_id_unique` - PASS
- **Player key alignment**: `assert_canonical_player_key_alignment` - PASS
- **Byron Young resolution**: Correctly resolves to player_id 8771 (DE/LAR)
- **Contracts models**: Both `stg_sheets__contracts_active` and `stg_sheets__contracts_cut` build and test successfully
- **All 18 tests for transactions**: PASS (17 PASS, 1 WARN on expected pick_id orphans)
- **All 17 tests for contracts**: PASS (16 PASS, 1 FAIL on known roster parity issue from P1-019)

**Impact**:

- Eliminated 6.8x row duplication caused by cartesian product joins
- Fixed data corruption in transaction history that was cascading to all downstream models
- All staging models using the macro now have clean 1:1 joins

**Files Modified**:

- `dbt/ff_data_transform/macros/resolve_player_id_from_name.sql` (lines 173-227)
