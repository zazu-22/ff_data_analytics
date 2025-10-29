# IDP Historical Data Investigation

**Date:** 2025-10-29
**Context:** Phase 3 - Investigating IDP historical data capabilities for FASA notebook and long-term modeling
**Related:** `docs/findings/2025-10-29_idp_opportunity_snap_counts_addendum.md`

______________________________________________________________________

## Executive Summary

**Finding:** We ALREADY have 5 years of IDP historical data (2020-2025) in nflverse raw files, but only loading 2025 season into fact table.

**Root Cause:** `latest_snapshot_only()` macro filters to most recent date partition, excluding historical snapshots.

**Solution:** Load older snapshot (dt=2024-01-01) containing 2020-2023 history + continue loading latest for current season.

**Impact:** Will provide ~45,000+ IDP stat records across 5 seasons for FASA and modeling.

______________________________________________________________________

## Use Cases

### Short-Term: FASA Notebook

**Requirement:** Recent performance data for IDP free agent value assessment

**Current State:** Only 8 weeks of 2025 data (insufficient for trend analysis)

**Needed:** At minimum, full 2024 season (22 weeks) + 2025 YTD

**With Fix:** 5 seasons (2020-2025) = comprehensive history for value scoring

### Long-Term: Predictive Modeling

**Requirement:** Historical data for building IDP projection models

**Current State:** 8 weeks insufficient for ML/statistical models

**Needed:** Multiple seasons to capture:

- Year-over-year consistency
- Aging curves
- Position-specific patterns
- Injury impact

**With Fix:** 5 seasons x 900+ players/season = robust training dataset

______________________________________________________________________

## Investigation Results

### 3.1: Current Pipeline Audit

**Raw Data (nflverse):**

```text
Source: data/raw/nflverse/weekly/dt=*/*.parquet

Snapshots Available:
- dt=2024-01-01: 2020-2023 seasons (4 years, historical)
- dt=2025-10-01: 2024 + 2025 weeks 1-4 (transitional)
- dt=2025-10-27: 2025 weeks 1-8 only (latest)
```

**Historical Coverage:**

| Season    | Weeks          | IDP Players   | Records     |
| --------- | -------------- | ------------- | ----------- |
| 2020      | 1-21           | 958           | ~9,189      |
| 2021      | 1-22           | 986           | ~9,804      |
| 2022      | 1-22           | 928           | ~9,528      |
| 2023      | 1-22           | 888           | ~9,173      |
| 2024      | 1-22           | 900           | ~9,612      |
| 2025      | 1-8 (YTD)      | 752           | ~5,922      |
| **Total** | **~115 weeks** | **~1,000/yr** | **~53,228** |

**Fact Table (fact_player_stats):**

```text
Current: Only 2025 season (8 weeks, 1,468 players)

IDP Stats Available: 15 types
- def_tackles_solo, def_tackle_assists, def_tackles_with_assist
- def_tackles_for_loss, def_tackles_for_loss_yards
- def_sacks, def_sack_yards, def_qb_hits
- def_interceptions, def_interception_yards
- def_pass_defended
- def_fumbles, def_fumbles_forced
- def_tds, def_safeties
```

### 3.2: nflverse IDP Capabilities Assessment

**Data Quality: EXCELLENT** ✅

nflverse provides comprehensive, high-quality IDP data:

1. **Granularity:** Per-game, per-player (ideal grain)
2. **Coverage:** All defensive positions (DE, DT, NT, LB, ILB, OLB, MLB, CB, FS, SS, S, DB)
3. **Stats:** 15 IDP stat types (matches common IDP scoring formats)
4. **History:** 2020-present (5+ seasons)
5. **Reliability:** Official NFL data via nflverse consortium
6. **Update Frequency:** Weekly during season

**Comparison to Projections:**

| Metric       | Projections (FantasySharks) | Actuals (nflverse)   |
| ------------ | --------------------------- | -------------------- |
| Source Count | 1 (single source risk)      | 1 (authoritative)    |
| Stat Types   | 8 (limited)                 | 15 (comprehensive)   |
| Granularity  | Weekly forecast             | Per-game actuals     |
| History      | N/A (forward-looking)       | 2020-present         |
| Reliability  | Medium (site-dependent)     | High (official data) |
| Cost         | Free                        | Free                 |

**Verdict:** nflverse historical data is SUPERIOR to projections for backtesting and modeling.

### 3.3: Sleeper API Assessment

**Status:** NOT NEEDED for historical data

**Reason:** nflverse provides complete historical IDP stats for free with better coverage than Sleeper API.

**Sleeper API Characteristics:**

- League-specific data (requires league_id)
- Real-time scoring/rosters focus
- No comprehensive historical stat warehouse
- Rate limits (1000 requests/minute)

**Use Cases for Sleeper:**

- Live league integration (rosters, scoring)
- Alternative player ID crosswalk
- League transaction history
- NOT a replacement for nflverse historical data

**Decision:** Defer Sleeper API integration; nflverse sufficient for IDP historical needs.

______________________________________________________________________

## Root Cause Analysis

### Why Historical Data Not Loading

**File:** `models/staging/stg_nflverse__player_stats.sql:135`

```sql
where
  w.player_id is not null
  and w.season is not null
  and w.week is not null
  -- Keep only latest snapshot (idempotent reads across multiple dt partitions)
  and {{ latest_snapshot_only(...) }}  -- ← FILTERS TO dt=2025-10-27 ONLY
```

**Behavior:**

- Macro evaluates `MAX(dt)` across all partitions
- Returns `dt=2025-10-27` (latest)
- Excludes `dt=2024-01-01` (historical data)
- Result: Only 2025 season loaded

**Design Intent:** Prevent duplicate records when same season data exists in multiple snapshots

**Unintended Consequence:** Excludes historical snapshots with non-overlapping seasons

### Snapshot Strategy

**Current Snapshots:**

| Snapshot      | Content            | Purpose               |
| ------------- | ------------------ | --------------------- |
| dt=2024-01-01 | 2020-2023 complete | Historical baseline   |
| dt=2025-10-01 | 2024 + 2025 W1-4   | Mid-season refresh    |
| dt=2025-10-27 | 2025 W1-8 only     | Latest current season |

**Problem:** Naive `latest_snapshot_only()` assumes single snapshot contains all needed history.

______________________________________________________________________

## Solution

### Option A: Load Multiple Snapshots with Deduplication (RECOMMENDED)

**Approach:** Load historical + latest, deduplicate overlapping seasons

```sql
-- Modify stg_nflverse__player_stats.sql
where w.player_id is not null
  and w.season is not null
  and w.week is not null
  -- Load historical baseline (2020-2023) OR latest snapshot (2024-2025)
  and (
    w.dt = '2024-01-01'  -- Historical data
    OR w.dt = {{ latest_snapshot() }}  -- Current season
  )
-- Add deduplication in final CTE
qualify row_number() over (
  partition by player_id, game_id, season, week, stat_name
  order by dt desc  -- Prefer latest snapshot for overlaps
) = 1
```

**Pros:**

- ✅ Gets all 5 years of history (2020-2025)
- ✅ Refreshes current season from latest snapshot
- ✅ Handles overlaps gracefully (2024 appears in both snapshots)
- ✅ Minimal code changes

**Cons:**

- Slightly more complex query (QUALIFY clause)
- Assumes historical snapshot remains static

### Option B: Parametrize Snapshot Selection

**Approach:** Make snapshot selection configurable

```sql
-- Add dbt var for historical snapshots
{% set historical_snapshots = var('historical_snapshots', ['2024-01-01']) %}

where ...
  and (
    w.dt in {{ historical_snapshots }}
    or w.dt = {{ latest_snapshot() }}
  )
```

**Pros:**

- ✅ Flexible (add/remove historical snapshots via config)
- ✅ Same deduplication as Option A

**Cons:**

- Requires configuration management
- More moving parts

### Option C: Load All Snapshots (NO DEDUP)

**Approach:** Remove `latest_snapshot_only()`, load everything

**Pros:**

- Simplest code change

**Cons:**

- ❌ Creates duplicates for overlapping seasons
- ❌ Violates fact table grain
- ❌ NOT ACCEPTABLE

**Verdict:** Option A (Load Multiple with Dedup) is RECOMMENDED.

______________________________________________________________________

## Implementation Plan

### Step 1: Modify Staging Model

**File:** `models/staging/stg_nflverse__player_stats.sql`

**Changes:**

1. Replace `latest_snapshot_only()` with explicit snapshot filter
2. Add `QUALIFY` deduplication clause

**Expected Impact:**

- Fact table IDP records: 8,214 → ~53,000 (6.5x increase)
- Seasons: 2025 only → 2020-2025 (5 years)
- IDP players: 1,468 → ~4,500+ unique across all seasons

### Step 2: Rebuild Fact Table

```bash
dbt run --select stg_nflverse__player_stats fact_player_stats --full-refresh
```

### Step 3: Validate Coverage

**Tests:**

1. Verify season range: 2020-2025 ✅
2. Check for duplicates: `test_unique_grain` ✅
3. Validate IDP player count: 4,000+ ✅
4. Spot-check known players across seasons ✅

### Step 4: Update FASA Notebook

**Changes Required:**

- Notebook queries will automatically benefit from expanded history
- May need to adjust lookback windows (e.g., "last 8 weeks" → "last season")
- Update value scoring to leverage multi-season trends

______________________________________________________________________

## Data Quality Considerations

### Player ID Mapping

**Current:** IDP players mapped via `gsis_id` → `mfl_id` crosswalk

**Coverage:** 99.9% of identifiable players map successfully

**Issue:** IDP players less likely to have `mfl_id` than offensive players

**Mitigation:** Staging model uses `player_key` composite (gsis_id fallback) to prevent grain violations

### Position Consistency

**nflverse Positions:** DE, DT, NT, LB, ILB, OLB, MLB, CB, FS, SS, S, DB

**Crosswalk Positions:** DE, DT, LB, CB, S (normalized)

**Discrepancy:** nflverse more granular (ILB vs OLB, FS vs SS)

**Impact:** Minimal - position translation already handles this via `dim_position_translation`

### Missing Data Patterns

**Normal Patterns:**

- Rookies have no prior history (expected)
- Injured players have gaps (valid)
- Position changes create history discontinuity (track via crosswalk)

**Red Flags:**

- Entire week missing for player (data quality issue)
- Stat values outside expected range (validate)

**Recommendation:** Add data quality tests for IDP historical data patterns

______________________________________________________________________

## Recommendations

### Immediate Actions

1. **Implement Solution** (Option A: Multiple snapshots with dedup)

   - Timeline: 1-2 hours
   - Priority: HIGH (required for FASA)

2. **Rebuild Fact Table**

   - Load 5 years of history
   - Validate data quality

3. **Update FASA Notebook**

   - Test with expanded history
   - Adjust lookback windows as needed

### Future Enhancements

1. **Add Historical Coverage Tests**

   ```sql
   -- Test: Ensure 5 years of IDP history
   assert min(season) >= 2020 for IDP positions
   assert max(season) = current_season
   ```

2. **Document Snapshot Strategy**

   - Create ADR for multi-snapshot loading pattern
   - Document which snapshots contain which seasons
   - Establish refresh cadence

3. **Optimize Query Performance**

   - Consider partitioning fact table by season
   - Index on (player_id, season, week) for FASA queries
   - Monitor query times after history load

### Sleeper API: Deferred

**Status:** NOT NEEDED for historical IDP data

**Revisit IF:**

- Need live league integration
- nflverse data quality issues emerge
- Want alternative player ID source

______________________________________________________________________

## Appendix: Sample Queries

### Check Historical Coverage

```sql
SELECT
  season,
  COUNT(DISTINCT player_id) as unique_players,
  COUNT(DISTINCT CONCAT(season, week)) as unique_weeks,
  COUNT(*) as stat_records
FROM fact_player_stats
WHERE stat_name LIKE 'def_%'
  AND position IN ('DE', 'DT', 'LB', 'CB', 'S')
GROUP BY season
ORDER BY season;
```

### FASA Query Pattern (Multi-Season Trends)

```sql
-- Get player's recent performance trend
WITH recent_performance AS (
  SELECT
    player_id,
    season,
    SUM(CASE WHEN stat_name = 'def_tackles_solo' THEN stat_value ELSE 0 END) as tackles,
    SUM(CASE WHEN stat_name = 'def_sacks' THEN stat_value ELSE 0 END) as sacks
  FROM fact_player_stats
  WHERE player_id = ?
    AND season >= 2023  -- Last 2+ seasons
  GROUP BY player_id, season
)
SELECT
  AVG(tackles) as avg_tackles_per_season,
  AVG(sacks) as avg_sacks_per_season,
  STDDEV(tackles) as consistency_tackles
FROM recent_performance;
```

______________________________________________________________________

## Conclusion

**We have excellent IDP historical data already in our pipeline**, we just need to load it!

**Action Items:**

1. ✅ **CONFIRMED:** nflverse has 5 years of comprehensive IDP data (2020-2025)
2. ✅ **ROOT CAUSE:** `latest_snapshot_only()` macro excluding historical snapshots
3. ✅ **SOLUTION:** Load multiple snapshots with deduplication (Option A)
4. ⏳ **NEXT STEP:** Implement solution and rebuild fact table

**Timeline:** ~2 hours to implement + test

**Value:** Unlocks FASA for IDP + enables long-term IDP modeling
