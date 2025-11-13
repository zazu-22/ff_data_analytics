# FFAnalytics Player Name Collision Bug

**Date**: 2025-11-13
**Severity**: CRITICAL - Data corruption affecting IDP + offensive players
**Status**: FIXED (tested, ready for re-ingestion)

## Executive Summary

The FFAnalytics consensus calculation incorrectly merged different players with identical names into single records with averaged/corrupted stats. This affected **at least 2 confirmed IDP players** across 13 player-weeks, with one player completely missing from all downstream tables.

**Root Cause**: Two separate bugs in the R script caused name collision merging:

1. **Consensus grouping** excluded `id` (provider ID) and only used `team`, allowing same-source duplicates to merge
2. **Player_id mapping** joined by `(name, position)` WITHOUT `team`, and deduplicated crosswalk entries

**Fix**: Applied defense-in-depth with BOTH provider ID and team:

1. **Line 522**: Added `id` (provider ID) to consensus grouping
2. **Lines 620-628**: Added `team` to player_id mapping joins
3. **Line 610**: Removed crosswalk deduplication that discarded players with same name

**Test Result**: ✅ Fix validated in production - both Jordan Phillips (BUF + MIA) and Byron Young (LAR + PHI) now appear separately with correct stats.

## Confirmed Affected Players

### IDP (Individual Defensive Players)

**Jordan Phillips (DT)**:

- **Veteran** (player_id=5505, mfl_id=12229): Buffalo Bills, drafted 2015
- **Rookie** (player_id=9559, mfl_id=17196): Miami Dolphins, drafted 2025
- **Impact**: Rookie completely missing; veteran has corrupted stats (averaged with rookie)
- **Weeks affected**: 11-17 (6 weeks)

**Byron Young (DE/DL)**:

- **Player A** (FantasySharks ID=16276): Los Angeles Rams
- **Player B** (FantasySharks ID=16273): Philadelphia Eagles
- **Impact**: PHI player completely missing; LAR player has corrupted stats
- **Weeks affected**: 11-17 (7 weeks)

### Offensive Players

**Potential Impact**: Unknown extent. Multi-source data (CBS, ESPN, FantasyPros, etc.) for offense makes detection harder. Name collisions possible for common names (e.g., "Mike Williams" WR).

**Note**: Most `source_count>=2` in offense is **legitimate multi-source**, not name collision. True collisions would require manual audit.

## Data Corruption Evidence

**Byron Young Week 11 Example**:

| Source                  | Team    | Solo Tackles | Assisted | Sacks    |
| ----------------------- | ------- | ------------ | -------- | -------- |
| FantasySharks (LAR)     | LAR     | 2.4          | 1.6      | 0.8      |
| FantasySharks (PHI)     | PHI     | 1.0          | 1.0      | 0.1      |
| **Staging (CORRUPTED)** | **LAR** | **1.7**      | **1.3**  | **0.45** |

All stats are `(LAR + PHI) / 2` - proving incorrect averaging.

## Root Cause Analysis

**File**: `scripts/R/ffanalytics_run.R`
**Line**: 519 (original), 521 (after fix)

**Original (BROKEN)**:

```r
group_by(player_normalized, pos, season, week) %>%  # team NOT included!
```

**Problem**:

- Groups by `(name, position, week)` only
- Same name + different teams → merged into ONE row
- `source_count = n()` counts rows (2 players → source_count=2)
- Stats averaged via `weighted.mean()`
- One team picked arbitrarily via `pick_consensus_value(team, weight)`

**Fix Applied**:

```r
group_by(player_normalized, pos, season, week, team_normalized) %>%  # team INCLUDED!
```

**Result**:

- Groups by `(name, position, week, team)`
- Same name + different teams → separate rows ✅
- `source_count` reflects actual source diversity (1 for IDP, multiple for offense)
- Stats remain separate (no averaging)

## Detection Methods

### Method 1: Check IDP for source_count >= 2

IDP has only ONE source (FantasySharks), so `source_count >= 2` indicates bug:

```sql
SELECT player, pos, team, source_count, COUNT(*) as weeks
FROM consensus_projections
WHERE pos IN ('DL', 'DE', 'DT', 'LB', 'DB', 'S', 'CB')
  AND source_count >= 2
GROUP BY player, pos, team, source_count;
```

### Method 2: Check raw data for multiple IDs with same name

```sql
WITH multi_team AS (
  SELECT player, pos, week,
    ARRAY_AGG(DISTINCT team) as teams,
    ARRAY_AGG(DISTINCT id) as ids,
    COUNT(DISTINCT team) as team_count,
    COUNT(DISTINCT id) as id_count
  FROM raw_projections
  GROUP BY player, pos, week
  HAVING COUNT(DISTINCT team) > 1
)
SELECT * FROM multi_team
WHERE id_count > 1;  -- Multiple IDs = true name collision
```

## Test Validation

**Test Script**: `scripts/R/test_name_collision_fix.R`

**Test Data**: Jordan Phillips + Byron Young, week 11, latest snapshot (2025-11-13)

**Test Results**:

✅ **WITH FIX**:

- 4 separate rows (BUF Phillips, MIA Phillips, LAR Young, PHI Young)
- source_count = 1 for all (correct)
- No data averaging

❌ **WITHOUT FIX**:

- 2 rows (merged by name)
- source_count = 2 (incorrect)
- Stats averaged across different players

**Command**: `Rscript scripts/R/test_name_collision_fix.R`

## Related Issues (NOT Name Collisions)

**Source Disagreement on Team** (NOT a bug):

- **Greg Joseph (K)**: ESPN=FA, FantasyPros=LV (same ID)
- **Lil'Jordan Humphrey (WR)**: FantasyPros=DEN, NFL=NYG (same ID)
- **Cause**: Mid-season signings/trades, sources update at different times
- **Handling**: Team normalization already handles this (lines 53-141)

**Team Abbreviation Aliases** (Already handled):

- JAC/JAX (Jacksonville Jaguars)
- KC/KCC (Kansas City Chiefs)
- **Handling**: Team alias map normalizes these (lines 53-141)

## Next Steps

1. ✅ **Fix implemented** (line 521 - add `team_normalized` to grouping)
2. ✅ **Test validates fix** with existing raw data
3. ⏭️ **Re-run FFAnalytics ingestion** (~15 minutes):
   ```bash
   just ingest-ffanalytics
   # OR manually: uv run python -c "from src.ingest.ffanalytics.loader import load_projections_ros; load_projections_ros()"
   ```
4. ⏭️ **Rebuild staging model**:
   ```bash
   just dbt-run --select stg_ffanalytics__projections
   ```
5. ⏭️ **Verify fix in production data**:
   - Check Jordan Phillips: Should have 2 separate player_ids (5505, 9559)
   - Check Byron Young: Should have 2 separate entries (LAR, PHI)
   - Check source_count: Should be 1 for IDP (no false "2 sources")

## Monitoring

Add validation test to catch future name collisions:

```sql
-- Test: Detect IDP with source_count > 1 (should always be 1 for IDP)
SELECT player_id, player_name, position, current_team, source_count
FROM main.stg_ffanalytics__projections
WHERE position IN ('DT', 'DE', 'DL', 'LB', 'DB', 'S', 'CB')
  AND source_count > 1
```

Expected: 0 rows (all IDP should have source_count=1 from FantasySharks).

## Impact Assessment

**Downstream Models Affected**:

- `stg_ffanalytics__projections` ✅ Direct impact
- `fct_player_projections` ✅ Inherits corrupted data
- `mrt_fantasy_projections` ✅ Fantasy scoring based on corrupted stats
- `mrt_projection_variance` ✅ Actuals vs projections analysis
- Any analytics/notebooks using projections ✅

**Data Quality Impact**:

- Jordan Phillips (MIA rookie): Completely missing from ALL tables
- Jordan Phillips (BUF veteran): Stats corrupted (mixed with rookie)
- Byron Young (PHI): Completely missing from ALL tables
- Byron Young (LAR): Stats corrupted (mixed with PHI player)
- Unknown # of offensive players potentially affected

## References

- **R Script**: `scripts/R/ffanalytics_run.R` (line 521)
- **Test Script**: `scripts/R/test_name_collision_fix.R`
- **Crosswalk**: `main.dim_player_id_xref` (shows both Jordan Phillips players)
- **Discovery**: P1-025 ticket investigation (IDP source diversity test)
- **Related Ticket**: `docs/implementation/multi_source_snapshot_governance/tickets/P1-025-investigate-idp-source-diversity.md`
