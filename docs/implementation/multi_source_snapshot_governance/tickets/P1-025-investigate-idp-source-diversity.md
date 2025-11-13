# Ticket P1-025: Investigate assert_idp_source_diversity Test Failures

**Status**: IN PROGRESS\
**Phase**: 1 - Foundation\
**Estimated Effort**: Medium (expanded to 3-4 hours due to critical bug discovery)\
**Dependencies**: None (independent data quality check)\
**Priority**: HIGH (upgraded from Low - critical data corruption bug discovered)

## Objective

Investigate and resolve 3 failures in the `assert_idp_source_diversity` test, which validates that IDP (Individual Defensive Player) statistics are sourced from multiple providers to ensure data coverage and reliability.

## Context

During comprehensive dbt test analysis (2025-11-10), the `assert_idp_source_diversity` test failed with 3 violations, indicating that some IDP players or position groups lack expected source diversity.

**Test Failure**:

```
assert_idp_source_diversity
Got 3 results, configured to fail if != 0
```

**Expected Behavior**:

IDP statistics should be available from multiple data providers to:

- Validate data accuracy through cross-referencing
- Ensure coverage if one provider is unavailable
- Provide redundancy for critical defensive stats

**Why This Matters**:

- Data reliability - multiple sources reduce single-point-of-failure risk
- IDP leagues require accurate defensive stats for scoring
- Source diversity enables data quality validation
- Low priority because it's a data quality warning, not a data corruption issue

## Tasks

### Phase 1: Investigation

- [ ] Run test query to identify which IDP players/positions lack source diversity:
  ```sql
  -- Example query structure (actual query in test file)
  SELECT player_id, player_name, position,
         COUNT(DISTINCT provider) as provider_count
  FROM main.fct_player_stats
  WHERE position IN ('DL', 'DE', 'DT', 'LB', 'DB', 'S', 'CB')
    AND stat_kind = 'actual'
  GROUP BY player_id, player_name, position
  HAVING COUNT(DISTINCT provider) < 2
  ORDER BY player_id;
  ```
- [ ] Check which providers are available for IDP:
  ```sql
  SELECT DISTINCT provider, COUNT(*) as stat_count
  FROM main.fct_player_stats
  WHERE position IN ('DL', 'DE', 'DT', 'LB', 'DB', 'S', 'CB')
  GROUP BY provider;
  ```
- [ ] Determine if failures are:
  - [ ] Specific players missing from secondary providers
  - [ ] Entire position groups missing from secondary providers
  - [ ] Seasonal gaps (e.g., rookies only in primary source)
- [ ] Review test expectations:
  - [ ] Is requiring 2+ sources realistic for all IDP players?
  - [ ] Should test allow exceptions for specific scenarios?
- [ ] Document root cause with SQL evidence

### Phase 2: Determine Fix Strategy

Based on investigation, choose approach:

**Option A: Accept Current State (Test Too Strict)**

- [ ] Test expectation of 2+ sources is unrealistic
- [ ] NFLverse is primary/only IDP source
- [ ] Update test to warn instead of fail
- [ ] Document known single-source IDP players

**Option B: Add Secondary IDP Source**

- [ ] Additional IDP data provider available but not integrated
- [ ] Integrate secondary source (e.g., Pro Football Reference, Sleeper)
- [ ] Update ingestion to include IDP from new source

**Option C: Fix Source Attribution**

- [ ] IDP data from multiple sources but incorrectly attributed
- [ ] Fix provider field in staging models
- [ ] Ensure proper source labeling

**Option D: Document Exceptions**

- [ ] 3 failures are legitimate exceptions (e.g., practice squad, recent signings)
- [ ] Update test to exclude these specific cases
- [ ] Add comments explaining exceptions

### Phase 3: Implementation

- [ ] Implement chosen fix strategy
- [ ] If test change: Update `tests/assert_idp_source_diversity.sql`
- [ ] If model change: Update IDP staging models
- [ ] If ingestion change: Add new IDP provider (out of P1 scope, defer to later)
- [ ] Test compilation if models changed

### Phase 4: Validation

- [ ] Run IDP diversity test:
  ```bash
  make dbt-test --select assert_idp_source_diversity
  # Expect: PASS (0 failures) or WARN (if downgraded)
  ```
- [ ] Verify IDP coverage:
  ```sql
  SELECT position,
         COUNT(DISTINCT player_id) as unique_players,
         COUNT(DISTINCT provider) as provider_count
  FROM main.fct_player_stats
  WHERE position IN ('DL', 'DE', 'DT', 'LB', 'DB', 'S', 'CB')
  GROUP BY position
  ORDER BY position;
  ```
- [ ] Spot-check that offensive players still have expected diversity

## Acceptance Criteria

- [ ] Root cause identified and documented
- [ ] Fix strategy chosen and implemented
- [ ] Test passes (0 failures) OR updated to warn instead of fail
- [ ] IDP coverage documented (single-source vs multi-source)
- [ ] Decision logged: accept single-source or add secondary source (future work)

## Implementation Notes

**Test File**: `dbt/ff_data_transform/tests/assert_idp_source_diversity.sql`

**Related Models**:

- `fct_player_stats` (primary fact table with provider field)
- `stg_nflverse__player_stats` (likely primary IDP source)
- Any other IDP staging models

**Investigation Query Template**:

```sql
-- Check current IDP source coverage
WITH idp_coverage AS (
  SELECT
    position,
    provider,
    COUNT(DISTINCT player_id) as player_count,
    COUNT(*) as stat_rows
  FROM main.fct_player_stats
  WHERE position IN ('DL', 'DE', 'DT', 'LB', 'DB', 'S', 'CB')
    AND season >= 2024
  GROUP BY position, provider
)
SELECT * FROM idp_coverage
ORDER BY position, provider;
```

## Testing

1. **Current state check**:

   ```bash
   EXTERNAL_ROOT="$PWD/data/raw" \
   duckdb "$PWD/dbt/ff_data_transform/target/dev.duckdb" -c \
     "SELECT position, COUNT(DISTINCT provider) as provider_count
      FROM main.fct_player_stats
      WHERE position IN ('DL', 'DE', 'DT', 'LB', 'DB', 'S', 'CB')
      GROUP BY position
      ORDER BY position;"
   ```

2. **Run test**:

   ```bash
   make dbt-test --select assert_idp_source_diversity
   ```

3. **After fix, verify**:

   ```bash
   # Should pass with 0 failures (or warn if downgraded)
   make dbt-test --select assert_idp_source_diversity
   ```

## Impact

**Before Fix**:

- 3 IDP players/positions with insufficient source diversity
- Potential single-point-of-failure for defensive stats
- Test failure (low severity)

**After Fix**:

- IDP source diversity validated or exceptions documented ✅
- Clear understanding of IDP data coverage ✅
- Test passes or appropriately warns ✅

**Downstream Impact**:

- IDP scoring in fantasy leagues
- Defensive player analysis
- Data quality monitoring

**Note**: This is a **low priority** ticket. If resolving requires significant effort (e.g., adding new data provider), consider deferring to post-Phase 1 work and downgrading test to warning.

## References

- Test: `dbt/ff_data_transform/tests/assert_idp_source_diversity.sql`
- Model: `dbt/ff_data_transform/models/core/fct_player_stats.sql`
- IDP positions: DL, DE, DT, LB, DB, S, CB
- Discovery: Comprehensive test analysis (2025-11-10)

## Notes

**Why This Ticket Exists**:

This test failure was discovered during comprehensive Phase 1 test analysis. It's a data quality check rather than a data integrity issue, making it lower priority than duplicates or orphan references.

**Sequencing**:

- Lowest priority among Phase 1 data quality tickets
- Can be done last or deferred to post-Phase 1
- No dependencies; completely independent

**IDP Context**:

IDP (Individual Defensive Player) leagues score defensive players individually rather than using team defenses (DST). This requires granular defensive statistics like tackles, sacks, interceptions, etc. Most fantasy platforms focus on offensive stats, so defensive stats may have less source diversity.

**Recommendation**:

If investigation shows that adding a secondary IDP source requires significant effort, consider:

1. Downgrading test from ERROR to WARN
2. Documenting NFLverse as authoritative IDP source
3. Deferring secondary source integration to future sprint

______________________________________________________________________

## Completion Notes

**Implemented**: 2025-11-13
**Strategy**: Option A - Accept Current State (Test Too Strict)

### Root Cause Analysis

**Configuration**: ✅ CORRECT

- We ARE scraping from ALL 9 sources: FantasyPros, NumberFire, FantasySharks, ESPN, FFToday, CBS, NFL, RTSports, Walterfootball
- We ARE requesting ALL positions including IDP: DL, LB, DB

**Source Limitation**: This is an INDUSTRY limitation, not a configuration issue

- FantasySharks is the ONLY source among those 9 that provides IDP stat projections
- Other sources provide IDP *rankings* (ordinal lists), not stat projections (tackles, sacks, INTs)
- FFAnalytics package scrapes stat projections, not rankings
- IDP leagues are ~10% of fantasy market, so most sites don't invest in IDP projections

### Test Results

**Before Fix**:

- Status: **FAIL 3** (Error severity)
- Message: "Got 3 results, configured to fail if != 0"

**Current Data**:

- **DB** (Defensive Backs): 100% single-source (1825/1825 from FantasySharks)
- **DL** (Defensive Line): 99.2% single-source (1672/1685 from FantasySharks)
- **LB** (Linebackers): 100% single-source (1018/1018 from FantasySharks)

**After Fix**:

- Status: **WARN 3** (Warning severity) ✅
- Message: "Got 3 results, configured to warn if != 0"
- Test passes with warning (not error)

### Changes Made

1. **Test SQL** (`dbt/ff_data_transform/tests/assert_idp_source_diversity.sql`):

   - Added `{{ config(severity='warn') }}` at top
   - Enhanced comments explaining industry limitation
   - Documented that we scrape ALL sources but only FantasySharks returns IDP

2. **R Script** (`scripts/R/ffanalytics_run.R`):

   - Added header comments documenting IDP limitation
   - Clarified this is industry-wide, not our configuration
   - References investigation document

3. **Documentation**: All changes reference `docs/findings/2025-10-29_idp_source_investigation.md` for details

### Decision

**Accept single-source IDP as expected behavior**:

- FantasySharks is authoritative IDP source (documented)
- Test downgraded to WARN (monitors situation without blocking)
- Alternative sources (Fantasy Nerds, IDP Guru) deferred to future sprint if needed
- Risk: Acknowledged and documented in test comments

______________________________________________________________________

## CRITICAL FOLLOW-UP: Player Name Collision Bug Discovered

**Date**: 2025-11-13 (same session as P1-025 completion)

### Discovery

While investigating `source_count=2` for IDP players (Jordan Phillips, Byron Young), discovered these were **NOT** legitimate multi-source data but rather **TWO DIFFERENT PLAYERS** being incorrectly merged by the FFAnalytics R script.

### The Bug

**File**: `scripts/R/ffanalytics_run.R` line 519 (before fix)

**Problem**: Consensus grouping excluded `team`, causing different players with same name to merge:

```r
group_by(player_normalized, pos, season, week) %>%  # team NOT included!
```

**Impact**:

- **Jordan Phillips (DT)**: Veteran (BUF, player_id=5505) + Rookie (MIA, player_id=9559) merged
  - Result: Rookie COMPLETELY MISSING, veteran has averaged/corrupted stats
- **Byron Young (DE)**: LAR player (ID 16276) + PHI player (ID 16273) merged
  - Result: PHI player COMPLETELY MISSING, LAR player has corrupted stats

### Fix Applied

**Line 521 (after fix)**:

```r
group_by(player_normalized, pos, season, week, team_normalized) %>%  # team INCLUDED!
```

**Test Validation**: ✅ Tested with existing raw data (see `scripts/R/test_name_collision_fix.R`)

- 4 separate rows maintained (each player-team combo preserved)
- source_count = 1 (correct for single-source IDP)
- No data averaging/corruption

### Next Steps

**IMMEDIATE** (before using projections data):

1. ✅ Fix implemented and tested (BOTH provider ID + team)
2. ✅ Re-run FFAnalytics ingestion (~15 min): `just ingest-ffanalytics` (COMPLETE)
3. ✅ Rebuild staging: `just dbt-run --select stg_ffanalytics__projections` (COMPLETE)
4. ✅ Verify both Jordan Phillips players appear separately in staging (VERIFIED: player_id 5505 BUF + 9559 MIA)
5. ✅ Verify Byron Young players appear separately (VERIFIED: player_id 8768 PHI + 8771 LAR)
6. ✅ Run new validation test: `just dbt-test --select assert_no_name_collision_merging` (PASSED)
7. ⏭️ Rebuild all downstream marts

**FOLLOW-UP** (audit other data sources):
7\. ✅ **Check other ingestion sources for similar team-based de-duplication errors** (COMPLETE):

**Audit Results** (2025-11-13):

✅ **NFLverse** (`src/ingest/nflverse/`): SAFE

- No grouping operations - data passes through from libraries as-is
- Primary keys include player_id or (season, week, player_id, team)

✅ **Sleeper** (`src/ingest/sleeper/`): SAFE

- Pure API fetching with filtering only, no aggregation
- Team field preserved in all outputs

✅ **Sheets** (`src/ingest/sheets/`): SAFE

- Pure parsing (CSV → DataFrames), no grouping
- Uses position-aware matching to handle same-name players

✅ **KTC** (`src/ingest/ktc/`): SAFE

- Web scraping with filtering only, no aggregation
- Team field preserved in player data

✅ **Staging Models**: SAFE

- `stg_nflverse__player_stats.sql`: Uses `player_key` (player_id or gsis_id)
- Other models: Limited grouping for ID deduplication or date ranges only

**Conclusion**: No additional team-based de-duplication bugs found. FFAnalytics was unique because it performs cross-provider consensus aggregation. All other sources fetch raw data or use unique IDs for deduplication.

**Full Report**: `docs/findings/2025-11-13_team_deduplication_audit.md`

**MONITORING**:
New dbt test created to catch future name collisions:

- **Test**: `tests/assert_no_name_collision_merging.sql`
- **Purpose**: Detect when same player_name + position has multiple teams but same player_id
- **Severity**: ERROR (will fail builds if name collision merging occurs)
- **Coverage**: All positions (IDP + offensive)

Quick manual check:

```sql
-- Should return 0 rows (no name collision merging)
SELECT * FROM stg_ffanalytics__projections
WHERE position IN ('DT', 'DE', 'DL', 'LB', 'DB', 'S', 'CB')
  AND source_count > 1;
```

### Documentation

**Full writeup**: `docs/findings/2025-11-13_ffanalytics_name_collision_bug.md`

### Severity

**CRITICAL** - This bug:

- Causes data loss (missing players)
- Corrupts projection stats (averaging different players)
- Affects IDP (confirmed) and potentially offensive players
- Has been active since FFAnalytics integration began
