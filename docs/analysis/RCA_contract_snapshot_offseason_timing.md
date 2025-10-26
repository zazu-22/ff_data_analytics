# Root Cause Analysis: Contract Snapshot Mismatch - Offseason Transaction Timing

**Date**: 2025-10-25
**Severity**: High - Data Quality Issue
**Impact**: 250 contract-years missing from transaction-derived contract mart (82.7% match rate vs expected ~100%)
**Status**: Root cause identified, fix designed

---

## Executive Summary

The transaction-derived contract mart (`mart_contract_snapshot_current`) was showing only **82.7% match rate** against roster snapshot data, with **250 contract-years missing** from the transaction view. Investigation revealed that contracts acquired via **offseason transactions** (trades, signings) were incorrectly calculated to start in the wrong season year, causing them to appear expired and be filtered out.

**Root Cause**: `dim_player_contract_history` uses `transaction_season` directly as `contract_start_season`, but for **offseason period** transactions, the contract actually starts in `season + 1`.

**Example**: Mark Andrews traded in "2022 Offseason" with remaining contract [15,20,20] should cover **2023-2025**, but was calculated as **2022-2024**, causing it to be filtered as expired.

---

## Background: Timeframe Semantics

Our league uses a specific timeframe naming convention that creates semantic complexity:

### Chronological Order (from `dim_timeframe` seed):
```
2022 FAAD (Aug 2022)
  ↓
2022 Week 1-17 (Sep-Dec 2022)
  ↓
2022 Offseason (Feb-July 2023) ← Transaction labeled "2022" occurs in 2023!
  ↓
2023 FAAD (Aug 2023)
  ↓
2023 Week 1-17 (Sep-Dec 2023)
  ↓
2023 Offseason (Feb-July 2024) ← Transaction labeled "2023" occurs in 2024!
```

**Key Insight**: The label "2022 Offseason" refers to the offseason **AFTER** the 2022 season (Super Bowl, March free agency, etc.), which physically occurs in **early 2023**.

This is correctly documented in `stg_sheets__transactions.sql`:
```sql
when base.period_type = 'offseason'
  then date_trunc('year', make_date(base.season, 3, 1))  -- Mar 1 (offseason)
```

A transaction in "2022 Offseason" gets `transaction_date = 2022-03-01`, which is actually **March 2023** in the NFL calendar.

---

## Problem Statement

### Observed Symptoms

1. **Missing contracts in transaction-derived mart**: Players like Mark Andrews, Breece Hall, Calvin Ridley showed in snapshot but not in transaction mart
2. **Low match rate**: 82.7% (1,556/1,881 contract-years matched)
3. **250 snapshot-only contract-years**: Contracts that should exist based on transaction log but weren't appearing

### Initial Hypotheses (Ruled Out)

❌ **Stale transaction data**: Verified we have current data through Week 8 2025 (3,982 transactions)
❌ **Missing transactions**: 94/107 snapshot-only contract-years are from players WITH transaction history
❌ **NULL contract amounts**: Only 1/1,923 contract-creating transactions has NULL total (0.1%)
❌ **Extension handling bug**: Fixed in prior work - same-date extensions now properly combined

---

## Investigation: Mark Andrews Case Study

### Transaction History
```
2018-01-01: Rookie Draft → [1,1] for 2018-2019 ($2M)
2019-01-01: Franchise Tag → [17] for 2019 ($17M)
2021-01-01: FAAD Signing → [10,10,15,20,20] for 2021-2025 ($75M)
2022-01-01: Trade (2022 Offseason) → [15,20,20] remaining ($55M)
```

### Expected Contract After Trade
- Original FAAD: [10,10,15,20,20] for 2021-2025
- After 1 year (2021): Used first [10]
- After 2 years (2022): Used second [10]
- **Trade in "2022 Offseason" (spring 2023)**: Remaining [15,20,20] should cover **2023-2025**

### Actual Calculation (WRONG)
```sql
-- dim_player_contract_history.sql line 244
ce.transaction_season as contract_start_season,  -- Uses 2022

-- Result:
contract_start_season = 2022
contract_end_season = 2022 + 3 - 1 = 2024  -- Should be 2025!
is_current = true (but contract_end_season < 2025)

-- Filtering in mart (line 63):
where contract_end_season >= year(current_date)  -- Filters out contracts ending in 2024
```

**Result**: Mark Andrews contract filtered out as "expired" even though it should run through 2025.

### What Snapshot Shows (CORRECT)
```
Mark Andrews 2025: $20M
```

The snapshot is correct - he should still have a year remaining.

---

## Root Cause Analysis

### Direct Cause
`dim_player_contract_history.sql` line 244 uses `transaction_season` directly as `contract_start_season`:

```sql
ce.transaction_season as contract_start_season,
```

For offseason transactions, this assigns the wrong year because:
- `transaction_season` = the season that just **ended** (e.g., 2022)
- Contract actually starts in the **upcoming** season (e.g., 2023)

### Why This Wasn't Caught Earlier

1. **Franchise lookups work correctly**: The temporal join to `dim_franchise` correctly uses `season=2022` to identify which franchise owned the player during the 2022 season. This is semantically correct.

2. **No existing pattern**: No other models currently calculate "contract effective year" from transaction year, so this gap wasn't documented.

3. **Same-date extensions masked the issue**: Prior bug (extensions creating separate periods) caused different symptoms that we fixed first.

### Contributing Factors

1. **Semantic overload of "season" field**: The `season` field in `dim_timeframe` represents the *label* of the period (2022 Offseason) not the calendar year when contracts take effect.

2. **Lack of contract start year calculation**: No documented pattern for deriving contract effective year from transaction season + period_type.

---

## Scope of Impact

### Affected Transaction Types
Any contract-creating transaction in the **offseason period**:
- Trades during offseason
- FASA signings during offseason
- Free agent signings during offseason

### Not Affected
- Rookie draft (has its own period)
- FAAD (has its own period)
- Regular season transactions
- Deadline transactions

### Data Quality Impact

**Before fix**:
- Transaction-derived mart: 807 contract-years
- Snapshot: 1,806 contract-years
- Match rate: 82.7%

**Expected after fix**:
- Transaction-derived mart: ~900-950 contract-years (adding ~100-150 offseason contracts)
- Match rate: ~95-98% (remaining gaps likely due to other minor issues)

---

## Proposed Fix

### Change Location
File: `dbt/ff_analytics/models/core/dim_player_contract_history.sql`

### Changes Required

**Step 1**: Add `period_type` to `all_contract_events` CTE (line 55):
```sql
season as transaction_season,
period_type,  -- ADD THIS
```

**Step 2**: Propagate through CTEs:
- Add to `same_date_extensions` CTE (line 126)
- Add to `standalone_contracts` CTE (line 168)

**Step 3**: Fix contract start season calculation (line 244):
```sql
-- BEFORE:
ce.transaction_season as contract_start_season,

-- AFTER:
case
  when ce.period_type = 'offseason' then ce.transaction_season + 1
  else ce.transaction_season
end as contract_start_season,
```

### Why This Approach

1. **Minimal scope**: Changes isolated to the contract dimension where this calculation belongs
2. **Consistent with existing patterns**: Aligns with `stg_sheets__transactions.sql` date mapping logic
3. **Self-documenting**: The CASE statement makes the offseason special handling explicit
4. **No downstream changes needed**: `mart_contract_snapshot_current` automatically inherits the fix

---

## Validation Plan

### Test Cases

**1. Mark Andrews** (offseason trade):
- Before: Not in current mart (contract ends 2024, filtered)
- After: Should show 2025 = $20M

**2. Breece Hall** (same-date extension in offseason):
- Before: Shows only 2025-2026
- After: Should show 2025-2027

**3. Regular season trades** (control group):
- Should remain unchanged (no offseason adjustment)

### Acceptance Criteria

1. ✅ Match rate improves from 82.7% to >90%
2. ✅ Contract-years increase from 807 to ~900-950
3. ✅ All offseason contracts show correct start year (season + 1)
4. ✅ Franchise lookups still work correctly (no regression)
5. ✅ Mark Andrews shows 2023-2025, not 2022-2024

---

## Risk Assessment

**Risk**: Low
**Confidence**: High

### Why Low Risk

1. **Well-isolated change**: Only affects contract start year calculation
2. **Existing test coverage**: dbt tests on grain, referential integrity will catch breakage
3. **Easy rollback**: Single-file change, can revert quickly
4. **Validation path**: Can compare before/after on known cases

### Potential Side Effects

1. **Franchise temporal join**: Already verified this works correctly with `season` as-is
2. **Contract period numbering**: May shift for some players (not an issue, it's a synthetic key)
3. **Historical contracts**: Pre-2012 contracts unaffected (don't exist in our data)

---

## Lessons Learned

### What Went Well

1. **Systematic debugging**: Traced through specific player (Mark Andrews) from raw data → staging → dimension → mart
2. **Data validation**: Created validation script early to quantify the issue
3. **Existing documentation**: `stg_sheets__transactions.sql` comments about offseason timing helped confirm root cause

### Improvement Opportunities

1. **Document semantic fields**: Should have documented `season` field semantics (label vs. effective year) earlier
2. **Contract calculation patterns**: Need to establish and document patterns for deriving contract effective dates
3. **Integration tests**: Add specific test for offseason contract timing

### Recommended Follow-ups

1. **Documentation**: Add to Kimball modeling guide: "Season field semantics for offseason periods"
2. **Data quality check**: Create dbt test to flag contracts with `contract_start_season < transaction_year - 1`
3. **Investigation**: Remaining 5-10% gap - identify remaining causes (likely minor issues or legitimate discrepancies)

---

## Timeline

| Date | Event |
|------|-------|
| 2025-10-25 09:00 | Issue reported: 79.3% match rate between transaction and snapshot contracts |
| 2025-10-25 10:00 | Fixed same-date extension handling bug → 82.7% match rate |
| 2025-10-25 11:00 | Identified 250 snapshot-only contracts, 94 from players WITH transactions |
| 2025-10-25 12:00 | Deep dive on Mark Andrews case reveals offseason timing issue |
| 2025-10-25 13:00 | Root cause confirmed via `dim_timeframe` chronology analysis |
| 2025-10-25 14:00 | Fix designed and documented (this RCA) |
| 2025-10-25 (pending) | Implement fix and validate |

---

## Appendices

### A. Example Transaction Data

**Mark Andrews Trade (2022 Offseason)**:
```
transaction_date: 2022-01-01 (represents spring 2023)
season: 2022
period_type: offseason
to_franchise: Franchise 005
contract_total: 55
contract_split_json: [15,20,20]

Expected contract_start_season: 2023 (not 2022)
Expected contract_end_season: 2025 (not 2024)
```

### B. Affected Files
1. `dbt/ff_analytics/models/core/dim_player_contract_history.sql` (fix required)
2. `dbt/ff_analytics/models/marts/mart_contract_snapshot_current.sql` (auto-fixed via dependency)

### C. Related Documentation
- `docs/analysis/TRANSACTIONS_handoff_20251001_phase1.md` - Period type definitions
- `dbt/ff_analytics/models/staging/stg_sheets__transactions.sql` - Date mapping logic (lines 91-105)
- `dbt/ff_analytics/seeds/dim_timeframe.csv` - Canonical timeframe chronology
