# IDP Opportunity Data: Snap Counts Investigation

**Date:** 2025-10-29
**Context:** Addendum to IDP Historical Data Investigation - FASA notebook requires opportunity metrics for IDP valuation
**Related:** `docs/findings/2025-10-29_idp_historical_data_investigation.md`

______________________________________________________________________

## Executive Summary

**Finding:** `snap_counts` dataset provides IDP "opportunity" metrics (defense_snaps, defense_pct) - equivalent to targets/carries for offensive players.

**Coverage:** 5 years of history (2020-2025), 950+ IDP players per season

**Current State:** Raw data exists but staging model has path issue + same `latest_snapshot_only()` limitation as player_stats

**Solution:** Fix `snap_counts` alongside `player_stats` using identical multi-snapshot loading pattern

______________________________________________________________________

## IDP Opportunity Metrics

### ff_opportunity: ❌ NOT APPLICABLE

**Coverage:** Only 1 defensive player (DB with trick play rushing stats)

**Reason:** Measures offensive opportunities (targets, carries, pass attempts) which defensive players don't generate

**Verdict:** Cannot use for IDP - dataset is offense-only by design

### snap_counts: ✅ IDEAL IDP OPPORTUNITY METRIC

**Concept:** Defensive snaps = IDP opportunity (more snaps → more chances for tackles/sacks/INTs)

**Analogous to:**

- WR targets = offensive opportunity
- RB carries = offensive opportunity
- Defense snaps = **defensive opportunity**

**Metrics Available:**

- `defense_snaps` - Count of defensive snaps played per game
- `defense_pct` - % of team's total defensive snaps
- Also: `offense_snaps`, `st_snaps` (for versatile players)

**IDP Coverage (2025 season):**

| Position Group   | Players | Total Records | Avg Snaps/Game | Avg Snap % |
| ---------------- | ------- | ------------- | -------------- | ---------- |
| DB (CB/S/FS/SS)  | 376     | 2,219         | 33.5           | 52%        |
| DL (DE/DT/NT)    | 304     | 1,708         | 29.0           | 45%        |
| LB (MLB/ILB/OLB) | 274     | 1,635         | 28.8           | 45%        |

**Historical Coverage:**

| Season    | Weeks          | IDP Players   | Total Records |
| --------- | -------------- | ------------- | ------------- |
| 2020      | 1-21           | 1,073         | ~10,000       |
| 2021      | 1-22           | 1,119         | ~11,000       |
| 2022      | 1-22           | 1,075         | ~10,500       |
| 2023      | 1-22           | 1,047         | ~10,200       |
| 2024      | 1-22           | 1,076         | ~10,500       |
| 2025      | 1-8 (YTD)      | 951           | ~5,500        |
| **Total** | **~115 weeks** | **~1,000/yr** | **~58,000**   |

______________________________________________________________________

## Use Case: FASA Value Scoring for IDP

### Offensive Player Value Framework

**Current FASA Components:**

1. **Opportunity** - ff_opportunity metrics (targets, carries)
2. **Production** - fact_player_stats (yards, TDs, receptions)
3. **Efficiency** - Production per opportunity
4. **Trend** - Multi-season history

### IDP Player Value Framework (Proposed)

**Components:**

1. **Opportunity** - snap_counts (defense_snaps, defense_pct)
2. **Production** - fact_player_stats (tackles, sacks, INTs, passes defended)
3. **Efficiency** - Production per snap
4. **Trend** - Multi-season history

**Efficiency Metrics (calculated in FASA):**

- Tackles per snap
- Sacks per snap
- Fantasy points per snap
- Snap share trend (increasing/decreasing role)

**Example IDP Value Score:**

```sql
-- Simplified FASA-style IDP value calculation
WITH player_metrics AS (
  SELECT
    player_id,
    -- Recent production (last 4 weeks)
    SUM(tackles) as recent_tackles,
    SUM(sacks) as recent_sacks,
    -- Recent opportunity (last 4 weeks)
    AVG(defense_snaps) as recent_snaps,
    AVG(defense_pct) as recent_snap_pct,
    -- Historical baseline (prior season)
    AVG(tackles_per_snap) as historical_efficiency
  FROM combined_idp_data
  WHERE ...
)
SELECT
  player_id,
  -- Volume score (opportunity)
  recent_snaps * recent_snap_pct * 100 as opportunity_score,
  -- Production score
  (recent_tackles * 1.0 + recent_sacks * 4.0) as production_score,
  -- Efficiency vs. baseline
  (current_efficiency / historical_efficiency) as efficiency_trend,
  -- TOTAL VALUE SCORE
  opportunity_score * production_score * efficiency_trend as idp_value
FROM player_metrics;
```

______________________________________________________________________

## Current State & Issues

### snap_counts Staging Model

**File:** `models/staging/stg_nflverse__snap_counts.sql`

**Issue 1: Path Resolution**

```sql
read_parquet(
  '{{ env_var("RAW_NFLVERSE_SNAP_COUNTS_GLOB",
    "data/raw/nflverse/snap_counts/dt=*/*.parquet") }}',
  hive_partitioning = true
)
```

Uses relative path which may not resolve correctly depending on execution context.

**Issue 2: Same `latest_snapshot_only()` Problem**
Model likely has same issue as `player_stats` - only loading latest snapshot (2025) instead of historical data.

**Raw Data Available:**

- `dt=2025-10-01`: Historical + partial 2025
- `dt=2025-10-28`: Latest 2025 only

**Same root cause:** Need to load multiple snapshots with deduplication.

______________________________________________________________________

## Unified Implementation Plan

### Goal

Enable full FASA valuation for IDP players by loading 5 years of:

1. IDP stats (tackles, sacks, INTs) - `player_stats`
2. IDP opportunity (defensive snaps) - `snap_counts`

### Why Fix Both Together

**Same Problem:**

- Both use `latest_snapshot_only()` excluding historical data
- Both have multiple snapshots available with 2020-2025 coverage
- Both need identical deduplication logic

**Same Solution:**

- Load historical snapshot (dt=2024-01-01 or dt=2025-10-01)
- Load latest snapshot (dt=2025-10-28)
- Deduplicate overlapping seasons

**Efficiency:**

- Single code pattern applied to both models
- Single rebuild/test cycle
- Atomic release (both ready for FASA simultaneously)

### Implementation Steps

#### Step 1: Fix stg_nflverse\_\_player_stats

**File:** `models/staging/stg_nflverse__player_stats.sql`

**Change (around line 135):**

```sql
-- BEFORE:
where
  w.player_id is not null
  and w.season is not null
  and w.week is not null
  and {{ latest_snapshot_only(...) }}

-- AFTER:
where
  w.player_id is not null
  and w.season is not null
  and w.week is not null
  -- Load historical baseline + current season
  and (
    w.dt = '2024-01-01'  -- Historical: 2020-2023
    or w.dt = {{ latest_snapshot() }}  -- Current: 2024-2025
  )
```

**Add deduplication (at end of unpivoted CTE, before final SELECT):**

```sql
-- Deduplicate overlapping seasons (2024 appears in both snapshots)
qualify row_number() over (
  partition by player_id, game_id, season, week, season_type, stat_name
  order by dt desc  -- Prefer latest snapshot for overlaps
) = 1
```

#### Step 2: Fix stg_nflverse\_\_snap_counts

**File:** `models/staging/stg_nflverse__snap_counts.sql`

**Same pattern as player_stats:**

1. Find the WHERE clause with snapshot filter
2. Replace with multi-snapshot loading
3. Add QUALIFY deduplication

**Expected location:** Near end of base CTE, similar structure to player_stats

**Same snapshots:**

- Historical: `dt='2024-01-01'` or `dt='2025-10-01'`
- Latest: `{{ latest_snapshot() }}`

**Deduplication key:**

```sql
qualify row_number() over (
  partition by pfr_player_id, game_id, season, week
  order by dt desc
) = 1
```

#### Step 3: Rebuild Models

```bash
# Rebuild both staging models
cd dbt/ff_analytics
EXTERNAL_ROOT="../../data/raw" dbt run --select stg_nflverse__player_stats stg_nflverse__snap_counts --full-refresh

# Rebuild downstream fact table
EXTERNAL_ROOT="../../data/raw" dbt run --select fact_player_stats --full-refresh
```

#### Step 4: Validate Results

**player_stats validation:**

```sql
-- Should show 2020-2025
SELECT
  MIN(season) as first_season,  -- Expect: 2020
  MAX(season) as last_season,   -- Expect: 2025
  COUNT(DISTINCT player_id) as idp_players,  -- Expect: 4,500+
  COUNT(*) as stat_records      -- Expect: ~50,000
FROM fact_player_stats
WHERE stat_name LIKE 'def_%'
  AND position IN ('DE', 'DT', 'LB', 'CB', 'S');
```

**snap_counts validation:**

```sql
-- Should show 2020-2025
SELECT
  MIN(season) as first_season,  -- Expect: 2020
  MAX(season) as last_season,   -- Expect: 2025
  COUNT(DISTINCT pfr_player_id) as idp_players,  -- Expect: 4,500+
  COUNT(*) as snap_records      -- Expect: ~58,000
FROM stg_nflverse__snap_counts
WHERE position IN ('CB', 'DB', 'FS', 'SS', 'S', 'DE', 'DL', 'DT', 'NT', 'LB', 'MLB', 'ILB', 'OLB');
```

**Cross-dataset join test:**

```sql
-- Verify most IDP players have both stats AND snap counts
SELECT
  COUNT(DISTINCT s.player_id) as players_with_stats,
  COUNT(DISTINCT sc.pfr_player_id) as players_with_snaps,
  COUNT(DISTINCT
    CASE WHEN sc.pfr_player_id IS NOT NULL THEN s.player_id END
  ) as players_with_both
FROM fact_player_stats s
LEFT JOIN stg_nflverse__snap_counts sc
  ON s.player_id = sc.player_id  -- May need crosswalk mapping
WHERE s.stat_name LIKE 'def_%'
  AND s.position IN ('DE', 'DT', 'LB', 'CB', 'S');
-- Expect high overlap (>80%)
```

#### Step 5: Create IDP FASA Mart (Optional Enhancement)

**File:** `models/marts/mart_idp_value_score.sql` (new)

Combine player_stats + snap_counts into IDP-specific value scoring mart:

```sql
-- Simplified structure
with recent_stats as (
  select player_id, position,
    sum(tackles) as tackles,
    sum(sacks) as sacks
  from fact_player_stats
  where season = 2025 and stat_name like 'def_%'
  group by player_id, position
),
recent_snaps as (
  select player_id, position,
    avg(defense_snaps) as avg_snaps,
    avg(defense_pct) as avg_snap_pct
  from stg_nflverse__snap_counts
  where season = 2025
  group by player_id, position
)
select
  s.player_id,
  s.position,
  s.tackles,
  s.sacks,
  sc.avg_snaps as opportunity_volume,
  sc.avg_snap_pct as opportunity_share,
  s.tackles / nullif(sc.avg_snaps, 0) as tackles_per_snap,
  s.sacks / nullif(sc.avg_snaps, 0) as sacks_per_snap
from recent_stats s
left join recent_snaps sc using (player_id, position);
```

______________________________________________________________________

## Data Quality Considerations

### Player ID Mapping

**Challenge:** snap_counts uses `pfr_player_id`, player_stats uses `gsis_id` → `player_id` (mfl_id)

**Current crosswalk:** dim_player_id_xref has `pfr_id` column ✅

**Join pattern:**

```sql
-- Method 1: Join via crosswalk
FROM fact_player_stats s
JOIN dim_player_id_xref x ON s.player_id = x.player_id
JOIN stg_nflverse__snap_counts sc ON x.pfr_id = sc.pfr_player_id

-- Method 2: If snap_counts staging already maps to player_id
FROM fact_player_stats s
JOIN stg_nflverse__snap_counts sc ON s.player_id = sc.player_id
```

**Action:** Verify snap_counts staging model maps pfr_player_id → player_id via crosswalk

### Position Consistency

**snap_counts positions:** More granular (CB, FS, SS vs. DB)

**Solution:** Use position groups in queries:

```sql
CASE
  WHEN position IN ('CB', 'FS', 'SS', 'S', 'DB') THEN 'DB'
  WHEN position IN ('DE', 'DT', 'NT', 'DL') THEN 'DL'
  WHEN position IN ('LB', 'MLB', 'ILB', 'OLB') THEN 'LB'
END as position_group
```

### Expected Data Gaps

**Normal:**

- Rookies have no prior history
- Injured players have incomplete seasons
- Backup players have low snap counts (expected)

**Red Flags:**

- Starter with suddenly 0 snaps (data quality issue)
- Snap % > 100% (data error)
- Defensive snaps > team total snaps (impossible)

**Recommendation:** Add data quality tests for snap count validity

______________________________________________________________________

## Timeline & Effort

**Estimated Effort:** 2-3 hours total

**Breakdown:**

1. Modify stg_nflverse\_\_player_stats: 30 min
2. Modify stg_nflverse\_\_snap_counts: 30 min
3. Rebuild models: 15 min
4. Validation queries: 30 min
5. Test FASA integration: 30 min
6. Documentation: 30 min

**Critical Path:** Both fixes required before FASA can properly value IDP players

**Dependencies:** None (can implement immediately after Phase 3 completion)

______________________________________________________________________

## Success Criteria

1. ✅ **Historical Coverage:** Both datasets show 2020-2025 seasons
2. ✅ **IDP Player Count:** 4,500+ unique IDP players across all seasons
3. ✅ **Record Volume:**
   - player_stats: ~50,000 IDP stat records
   - snap_counts: ~58,000 snap count records
4. ✅ **Data Quality:** No duplicate grain violations
5. ✅ **Cross-dataset Join:** >80% of IDP players have both stats and snaps
6. ✅ **FASA Integration:** Notebook can calculate IDP value scores using:
   - Historical performance trends
   - Current season production
   - Snap count opportunity metrics

______________________________________________________________________

## References

- **Main investigation:** `docs/findings/2025-10-29_idp_historical_data_investigation.md`
- **Staging models:**
  - `models/staging/stg_nflverse__player_stats.sql`
  - `models/staging/stg_nflverse__snap_counts.sql`
- **Fact table:** `models/core/fact_player_stats.sql`
- **Crosswalk:** `seeds/dim_player_id_xref.csv`

______________________________________________________________________

## Next Session Action Items

1. **Implement fixes** for both stg_nflverse\_\_player_stats and stg_nflverse\_\_snap_counts
2. **Rebuild models** with 5 years of historical data
3. **Validate** data quality and coverage
4. **Test FASA integration** with IDP players
5. **Create ADR** documenting multi-snapshot loading pattern (if not already covered)
6. **Update FASA notebook** to leverage IDP opportunity metrics

**Start with:** Review this document + main investigation, then implement Step 1 (player_stats fix)
