# Root Cause Analysis: P1-020 through P1-024

**Date**: 2025-11-10
**Investigator**: Claude (AI Assistant)
**User**: Jason

## Executive Summary

Investigated 4 related dbt test failures (P1-020, P1-022, P1-023, P1-024). Implemented 3 fixes resulting in significant improvements:

| Ticket     | Issue                    | Before | After  | Status               |
| ---------- | ------------------------ | ------ | ------ | -------------------- |
| **P1-024** | Comp registry duplicates | 19     | **0**  | ✅ **FIXED**         |
| **P1-023** | Incomplete base picks    | 21     | **4**  | ⚠️ 81% improved      |
| **P1-022** | Orphan pick references   | 5      | **4**  | ⚠️ 20% improved      |
| **P1-020** | TBD pick duplicates      | 22     | **22** | ❌ Not addressed yet |

______________________________________________________________________

## Root Causes Identified

### 1. P1-024: SCD Type 2 Join Without Temporal Filter ✅ FIXED

**File**: `int_pick_comp_registry.sql:147`

**Problem**:

```sql
-- BEFORE: Joined to ALL historical owners for franchise
left join franchise_mapping fm on pc.comp_awarded_to_franchise_id = fm.franchise_id
```

**Result**: Transaction 1766 matched 4 owner records for F002 (Eric → Schnese → Blaise → McCrystal), creating 4 duplicate rows.

**Fix**:

```sql
-- AFTER: Temporal join to owner at time of transaction
left join franchise_mapping fm
    on pc.comp_awarded_to_franchise_id = fm.franchise_id
    and year(pc.transaction_date) between fm.season_start and coalesce(fm.season_end, 9999)
```

**Impact**: 19 duplicates → 0 ✅

______________________________________________________________________

### 2. P1-023: Phantom R5 Picks + Missing "No Selection" Picks ⚠️ PARTIALLY FIXED

**Two Sub-Problems**:

#### 2a. Phantom R5 Picks for 2018-2024 ✅ FIXED

**File**: `int_pick_base.sql`

**Problem**: Model generated R5 picks for ALL years, but league only had 5 rounds in 2012-2017 and 2025+. Years 2018-2024 used 4-round format.

**Fix**:

```sql
-- Added filter to base_picks CTE
where not (round = 5 and season between 2018 and 2024)
```

**Impact**: Removed 84 phantom picks (7 years × 12 picks)

#### 2b. "No Selection" Picks Excluded ✅ FIXED

**File**: `int_pick_draft_actual.sql:42`

**Problem**: Model filtered to only `asset_type = 'player'`, excluding picks where franchise chose not to draft (asset_type = 'unknown').

**Context**: "No selection" picks are legitimate draft positions where franchise passed due to roster constraints or lack of trade partners. They occupy a slot in draft order.

**Fix**:

```sql
-- BEFORE
and asset_type = 'player'

-- AFTER
and asset_type in ('player', 'unknown')  -- Include "no selection" picks
```

**Example**: 2017 R4 had 3 "no selection" picks (transactions 317, 325, 327)

- Before: 9 picks counted
- After: 12 picks counted ✅

**Combined Impact**: 21 failures → 4 failures (81% improvement)

**Remaining 4 Failures**:

```
2014 R2: 11 picks (missing 1)
2015 R2: 11 picks (missing 1)
2017 R5: 11 picks (missing 1)
2025 R5: 8 picks (missing 4)
```

**Next Steps**: Investigate if these are additional "no selection" picks with different classification, or genuine data gaps.

______________________________________________________________________

### 3. P1-022: Incorrect Round Labels in Source Data ⚠️ NOT FIXED YET

**Root Cause**: Trade transactions have mismatched round labels.

**Example**:

- Transaction 1596: Player column says "2021 3rd Round", Pick column = 54
- But overall pick #54 in 2021 is actually in Round 4 (48 base picks before R4 starts)
- Parser faithfully creates `pick_id='2021_R3_P54'` but this doesn't exist in dim_pick

**Evidence**:

```sql
-- Source CSV (transaction 1638 - actual rookie draft):
2021 Rookie Draft, Round 4, Pick 54, Player: Odafe Oweh

-- Parsed data (transaction 1596 - trade):
Round 3, Pick 54, Player: "2021 3rd Round"  -- Wrong round label!
```

**Current Status**:

- Before fixes: 5 orphan picks (including TBD picks)
- After fixes: 4 orphan picks
- Improvement came from fixing dim_pick overall_pick calculations (removed phantom R5)

**Ready Solution**: Enhance `int_pick_transaction_xref` to match ONLY on `(season, overall_pick)`, ignoring round since overall_pick is authoritative per ADR-014.

**Affected Picks**:

- 2021_R3_P54 (should be 2021_R4_P??)
- 2022_R4_P54 (should be 2022_R5_P??)
- 2025_R2_P33, 2025_R3_P26, 2026_R2_P30 (similar round mismatches)

______________________________________________________________________

### 4. P1-020: Cartesian Product from Season/Round Join ❌ NOT FIXED YET

**File**: `dim_pick_lifecycle_control.sql:68`

**Problem**:

```sql
left join actual_picks_created act on tbd.season = act.season and tbd.round = act.round
```

**Result**: `2023_R1_TBD` joins to ALL 21 actual picks in 2023 R1 (12 base + 9 comp), creating 21 duplicate rows per TBD pick.

**Model Intent**: The model should be a canonical registry with ONE row per pick (per line 19: "Grain: One row per pick").

**Note in Code** (line 57): "Currently no matches since actual_picks_created is empty" - suggesting the join may serve no current purpose.

**Ready Solution**: Either remove the join entirely OR add proper matching logic (e.g., match on franchise ownership, not just season/round).

**Impact**: 22 pick_ids with 301 total duplicate rows

______________________________________________________________________

## Implementation Timeline

### Session 1: Investigation

1. Read tickets P1-020, P1-022, P1-023, P1-024
2. Queried data to understand patterns
3. Identified common theme: one-to-many problems
4. Initial hypothesis: Deduplication failures

### Session 2: Corrections After User Input

User provided critical corrections:

- Overall pick numbers are authoritative (not slot numbers) - per ADR-014
- 2025 rookie draft HAS happened
- 2026 comp picks have been awarded
- Pick numbers like P54 refer to overall position, not impossible slot numbers

### Session 3: Deep Investigation

Discovered actual root causes:

- P1-024: SCD Type 2 join missing temporal filter
- P1-023: Phantom R5 picks + excluded "no selection" picks
- P1-022: Source data has incorrect round labels
- P1-020: Cartesian product join

### Session 4: Implementation

**Fix 1**: Added R5 filter to `int_pick_base.sql`
**Fix 2**: Included "no selection" picks in `int_pick_draft_actual.sql`
**Fix 3**: Added temporal filter to `int_pick_comp_registry.sql`

### Session 5: Completing P1-020 and P1-022 (2025-11-10)

**Context**: User correctly identified that P1-020 "fix" was inadequate - it just disabled functionality via SQL comments rather than properly addressing the issue.

**P1-020 Proper Fix** (Option A: Remove dead code, document requirements):

- Removed unused `actual_picks_created` CTE entirely
- Simplified `tbd_to_actual_mapping` → `tbd_picks` CTE
- Updated SQL comments to document current state and implementation requirements
- Updated YAML to reflect that TBD → Actual matching NOT YET IMPLEMENTED
- Documented that proper matching requires franchise ownership tracking
- All 17 downstream models still work correctly
- Result: 22 duplicates → 0 duplicates ✅

**P1-022 Fix** (Match on overall_pick only, per ADR-014):

- Root cause: Transaction source data has incorrect round labels
- Example: "2021 3rd Round, Pick 54" → actually R4 P09 (overall pick 54 is in R4, not R3)
- Fix: Removed `tp.pick_round = cp.round` from join conditions in `int_pick_transaction_xref.sql`
- Now matches ONLY on `(season, overall_pick)` - per ADR-014, overall pick is authoritative
- Added new match_status: 'ROUND CORRECTED (OVERALL MATCH)' for these cases
- Applied fix to both `matched_by_overall` and `matched_by_slot` CTEs
- Result: 4 orphan picks → 0 orphan picks ✅

**Verification**:

- All 4 orphaned picks now correctly matched with round corrections:
  - 2021_R3_P54 → 2021_R4_P09 (round corrected R3→R4)
  - 2025_R3_P26 → 2025_R2_P12 (round corrected R3→R2)
  - 2025_R2_P33 → 2025_R3_P05 (round corrected R2→R3)
  - 2026_R2_P30 → 2026_R3_P06 (round corrected R2→R3)
- All downstream tests pass
- Foreign key integrity fully restored

______________________________________________________________________

## Key Learnings

### 1. Phantom Data Can Cascade

Phantom R5 picks (84 generated but non-existent) caused:

- Wrong overall_pick calculations (duplicates)
- Test failures across multiple tickets
- Crosswalk matching issues

### 2. "No Selection" Picks Are Real Picks

Teams strategically passing on picks (due to roster limits) is valid gameplay. These must be counted as base picks to maintain correct draft order sequencing.

### 3. Overall Pick Number Is Authoritative

Per ADR-014, overall pick number is the canonical identifier. Round labels in trade transactions are unreliable (human entry errors).

### 4. SCD Type 2 Dimensions Need Temporal Joins

When joining to franchise dimension with ownership history, must filter to owner at time of transaction to avoid Cartesian products.

______________________________________________________________________

## Files Modified

### ✅ Completed Fixes

1. `dbt/ff_data_transform/models/core/intermediate/int_pick_base.sql`

   - Added: `where not (round = 5 and season between 2018 and 2024)`

2. `dbt/ff_data_transform/models/core/intermediate/int_pick_draft_actual.sql`

   - Changed: `asset_type = 'player'` → `asset_type in ('player', 'unknown')`
   - Added: Documentation comment explaining "no selection" picks

3. `dbt/ff_data_transform/models/core/intermediate/int_pick_comp_registry.sql`

   - Added: `and year(pc.transaction_date) between fm.season_start and coalesce(fm.season_end, 9999)`

### ✅ Session 5 Fixes (P1-020, P1-022)

4. `dbt/ff_data_transform/models/core/intermediate/dim_pick_lifecycle_control.sql`

   - Removed: Dead `actual_picks_created` CTE and Cartesian product join
   - Simplified: `tbd_to_actual_mapping` → `tbd_picks`
   - Updated: SQL comments and YAML to document current state and requirements
   - Result: TBD picks no longer create duplicates (22 → 0)

5. `dbt/ff_data_transform/models/core/intermediate/int_pick_transaction_xref.sql`

   - Removed: `tp.pick_round = cp.round` from both `matched_by_overall` and `matched_by_slot` joins
   - Changed: Match ONLY on `(season, overall_pick)` per ADR-014
   - Added: New match_status 'ROUND CORRECTED (OVERALL MATCH)'
   - Result: Orphan picks resolved via round correction (4 → 0)

6. `dbt/ff_data_transform/models/core/intermediate/_dim_pick_lifecycle_control.yml`

   - Updated: Model and column descriptions to reflect current implementation state

______________________________________________________________________

## Remaining Work

### Completed ✅

1. **P1-020**: TBD pick duplicates resolved (dead code removed, documentation updated)
2. **P1-022**: Orphan pick references resolved (match on overall_pick only per ADR-014)
3. **P1-024**: Comp registry duplicates resolved (temporal join fixed)

### Investigation Needed

1. **P1-023 Remaining 4 Failures**: Investigate why these specific rounds have \<12 picks:
   - Check if more "no selection" picks with different asset_type
   - Check if genuine data gaps in source
   - May need to check with commissioner

______________________________________________________________________

## Test Results Summary

### Before Any Fixes

```
P1-020: 22 duplicates (TBD picks)
P1-022: 5 orphan picks
P1-023: 21 incomplete rounds
P1-024: 19 duplicate transactions
```

### After 3 Fixes (Session 4)

```
P1-020: 22 duplicates (unchanged - not addressed)
P1-022: 4 orphan picks (20% improvement)
P1-023: 4 incomplete rounds (81% improvement)
P1-024: 0 duplicates (100% FIXED ✅)
```

### After Session 5 (Final - 2025-11-10)

```
P1-020: 0 duplicates (100% FIXED ✅)
P1-022: 0 orphan picks (100% FIXED ✅)
P1-023: 4 incomplete rounds (81% improvement - stable)
P1-024: 0 duplicates (100% FIXED ✅) - remains fixed
```

**Total Impact**:

- **3 tickets completely resolved** ✅ (P1-020, P1-022, P1-024)
- **1 ticket significantly improved** ⚠️ (P1-023: 81% improvement)
- Remaining work: Investigate 4 specific rounds with \<12 picks

______________________________________________________________________

## References

- **Tickets**: `docs/implementation/multi_source_snapshot_governance/tickets/P1-0{20,22,23,24}*.md`
- **ADR-014**: `docs/adr/ADR-014-pick-identity-resolution-via-overall-pick-number.md`
- **Source Data**: `/Users/jason/Desktop/{rookie.csv,faad.csv}` (provided during investigation)
- **League Rules**: Rookie draft had 5 rounds (2012-2017, 2025+), 4 rounds (2018-2024)
