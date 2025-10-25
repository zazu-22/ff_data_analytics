# Handoff: player_key Composite Identifier Implementation - Grain Tests Resolved

**Date**: 2025-10-01
**Status**: Phase 2A Track A (NFL Actuals) - 85% Complete
**Test Results**: 19/19 passing (100%) ✅

## Phase 2B Update — 2025-10-02

Following additional review and fixes, Track A is architecturally correct and aligned with ADR-010 and the 2×2 model:

- ✅ Canonical Player ID: All models now use `mfl_id` as `player_id` (ADR-010)
- ✅ Fantasy Scoring: `mart_fantasy_actuals_weekly` reads coefficients from `dim_scoring_rule` (no hardcoded constants)
- ✅ Team Dimension: `dim_team` deduplicated by latest season per `team_abbr`

Remaining Follow-ups (non-blocking):

- Load nflverse `teams` and `schedule` parquet where missing so dims build consistently
- Consider adding kicking stats (FGM/FGA, XPM/XPA) and wire to existing `kicking` rules
- Resolve defensive tackles field semantics to avoid double-counting assists
- Optionally expose weekly team attribution in marts to complement `current_team`

## Executive Summary

Successfully resolved all grain test failures by implementing a composite `player_key` identifier that preserves unmapped player identity using raw provider IDs. All 19 fact_player_stats tests now passing.

**Key Achievement**: Eliminated 18 grain duplicate violations while maintaining data integrity and traceability for unmapped players.

______________________________________________________________________

## Problem Statement

**Issue**: 18 grain duplicate violations in fact_player_stats from unmapped TEs in 3 Pittsburgh games:

- 2021_16_PIT_KC (John Samuel Shenker, Rodney Williams)
- 2023_15_PIT_IND (2 unmapped TEs)
- 2024_06_PIT_LV (2 unmapped TEs)

**Root Cause**: When crosswalk mapping fails for multiple players in the same game, all become indistinguishable `player_id = -1` records, causing grain violations on composite key: `(player_id, game_id, stat_name, provider, measure_domain, stat_kind)`.

______________________________________________________________________

## Solution: Composite player_key Column

Implemented `player_key` as a composite identifier that uses raw provider IDs as fallback when crosswalk mapping fails:

```sql
case
  when coalesce(xref.player_id, -1) != -1
    then cast(xref.player_id as varchar)
  else coalesce(base.{raw_provider_id}, 'UNKNOWN_' || base.game_id)
end as player_key
```

**Behavior by mapping status**:

- **Mapped players**: `player_key = player_id` (canonical mfl_id as varchar)
- **Unmapped players**: `player_key = raw_provider_id` (gsis_id or pfr_id)
- **Unknown edge case**: `player_key = 'UNKNOWN_' || game_id` (defensive fail-safe)

______________________________________________________________________

## Implementation Details

### Files Modified

1. **stg_nflverse\_\_player_stats.sql** (50 unpivot statements)

   - Added player_key using `gsis_id_raw` fallback
   - Updated all UNION ALL statements to include player_key

1. **stg_nflverse\_\_snap_counts.sql** (6 unpivot statements)

   - Added player_key using `pfr_player_id` fallback
   - Updated all UNION ALL statements to include player_key

1. **stg_nflverse\_\_ff_opportunity.sql** (32 unpivot statements)

   - Added player_key using `gsis_id_raw` fallback
   - Updated all UNION ALL statements to include player_key

1. **schema.yml**

   - Updated grain test to use `player_key` instead of `player_id`
   - Added player_key column documentation
   - Added not_null test for player_key

**Total changes**: 88 unpivot statements updated across 3 models

### Documentation Added

All staging models now include comprehensive comments documenting:

**Data Quality Filters** (NULL provider ID filtering):

- `weekly`: ~0.12% filtered (113/97,415 rows with NULL player_id)
- `snap_counts`: 0.00% filtered (0/136,974 rows)
- `ff_opportunity`: ~6.75% filtered (2,115/31,339 rows with NULL player_id)

**Crosswalk Coverage** (mapping success rates):

- `weekly`: 99.9% of identifiable players map successfully
- `snap_counts`: 81.8% map (18.2% unmapped, mostly linemen)
- `ff_opportunity`: 99.86% of identifiable players map successfully

**player_key Logic**:

- Prevents duplicate grain violations when multiple unmapped players in same game
- Uses raw provider IDs to preserve identity
- Defensive fail-safe for edge cases

______________________________________________________________________

## Data Quality Analysis

### Complete Data Picture

**FF Opportunity** (most significant NULL filtering):

- **6.75%** unidentifiable (NULL player_id AND NULL position, filtered out)
- **93.12%** identifiable & successfully mapped to mfl_id
- **0.13%** identifiable but not in crosswalk (become player_id = -1)
- **Total: 100.00%**

NULL records characteristics:

- All have NULL position
- Small opportunity counts (1-4 targets/attempts)
- Consistent across all 6 seasons (~350-440 per year)
- Unattributable to specific players (nflverse data quality issue)

**Filtering rationale**: Records without player identification cannot support player-level analysis and would clutter fact table as UNKNOWN entries.

### Mapping Coverage by Source

| Source         | Raw Rows | NULL Filtered | Identifiable | Mapped | Unmapped |
| -------------- | -------- | ------------- | ------------ | ------ | -------- |
| weekly         | 97,415   | 0.12%         | 99.88%       | ~99.9% | ~0.1%    |
| snap_counts    | 136,974  | 0.00%         | 100.00%      | 81.8%  | 18.2%    |
| ff_opportunity | 31,339   | 6.75%         | 93.25%       | 99.86% | 0.14%    |

**Key insights**:

- Overall unmapped rate in fact table (~6%) driven by snap_counts linemen/specialists
- ff_opportunity has high NULL rate but excellent mapping coverage for identifiable players
- weekly data has nearly perfect coverage

______________________________________________________________________

## Test Results

### Before Implementation

- **17/18 tests passing** (94.4%)
- **1 failing test**: grain uniqueness (18 duplicate violations)

### After Implementation

- **19/19 tests passing** (100%) ✅
- **0 duplicate violations**
- All grain tests pass with fantasy-position filtering

### Test Suite Coverage

**Grain Test** (unique combination):

```yaml
- player_key  # Changed from player_id
- game_id
- stat_name
- provider
- measure_domain
- stat_kind
where: "position IN ('QB', 'RB', 'WR', 'TE', 'K', 'FB')"
```

**All 19 tests**:

- ✅ Grain uniqueness (player_key composite)
- ✅ Not null tests (all grain columns + player_key)
- ✅ Enum tests (season, season_type, measure_domain, stat_kind, provider)
- ✅ FK test (player_id → dim_player_id_xref, filtered for mapped players)

______________________________________________________________________

## Current Database State

### Fact Table Statistics

```
Total rows: 6,345,321 (rounded, ~6.3M)
Seasons: 2020-2025 (6 complete seasons)
Unique stat types: 88
Unique players: 12,133 (in crosswalk)
Build time: ~11 seconds
Database size: ~220MB
```

### Source Breakdown

| Source              | Rows      | Stat Types | Coverage      |
| ------------------- | --------- | ---------- | ------------- |
| player_stats (base) | 4,302,543 | 50         | All 6 seasons |
| snap_counts         | 1,224,282 | 6          | All 6 seasons |
| ff_opportunity      | 818,496   | 32         | All 6 seasons |

______________________________________________________________________

## Architecture Decisions

### ADR-009: Single Consolidated Fact Table

- Maintains single fact table design
- player_key enables grain enforcement without sacrificing unmapped player visibility

### ADR-010: mfl_id as Canonical Identity

- player_id remains canonical reference (mfl_id)
- player_key provides grain uniqueness while preserving raw IDs for traceability

### Design Principles

1. **Defensive data quality**: Filter NULL provider IDs before staging
1. **Preserve traceability**: Use raw IDs when crosswalk fails
1. **Fail-safe**: UNKNOWN fallback for edge cases (never reached in practice)
1. **Documentation**: Comprehensive comments explaining filtering and coverage

______________________________________________________________________

## Seeds Status - CORRECTED

**Previously thought**: Seeds incomplete and blocking

**Reality**: Seeds mostly complete, NOT blocking!

### Completed Seeds (5/8)

- ✅ **dim_player_id_xref**: 12,133 players, 19 provider IDs (from nflverse ff_playerids)
- ✅ **dim_franchise**: SCD2 ownership history (F001-F012)
- ✅ **dim_pick**: 2012-2030 base draft picks
- ✅ **dim_scoring_rule**: Half-PPR + IDP scoring with validity periods
- ✅ **dim_timeframe**: Season/week/period mapping

### Optional Seeds (3/8)

- ☐ **dim_asset**: Can generate on-demand via UNION of players + picks
- ☐ **stat_dictionary**: Only needed for multi-provider normalization (single provider currently)
- ☐ **dim_name_alias**: Only needed if fuzzy matching fails (add iteratively)

**Impact**: All Phase 2 tracks are UNBLOCKED! TRANSACTIONS parsing, FFanalytics projections, and KTC integration can all proceed.

______________________________________________________________________

## Phase 2 Track Status - UPDATED

| Track               | Progress | Status        | Next Task                             |
| ------------------- | -------- | ------------- | ------------------------------------- |
| **A (NFL Actuals)** | 85%      | Active        | Create dims (player/team/schedule)    |
| **B (League Data)** | 30%      | **UNBLOCKED** | Parse TRANSACTIONS tab                |
| **C (Market Data)** | 0%       | **UNBLOCKED** | Implement KTC fetcher                 |
| **D (Projections)** | 20%      | **UNBLOCKED** | Weighted aggregation + player mapping |

**Track A Remaining Work**:

1. Create dimensional tables:
   - `dim_player` (from dim_player_id_xref + player attributes)
   - `dim_team` (from nflverse teams)
   - `dim_schedule` (from nflverse schedule)
1. Build marts:
   - `mart_real_world_actuals_weekly` (aggregate to player-week grain)
   - `mart_fantasy_actuals_weekly` (apply dim_scoring_rule)

______________________________________________________________________

## Next Steps - Decision Point

### Option A: Complete Track A (NFL Actuals) ⚙️

**Rationale**: Finish current work stream, get one complete vertical slice

**Tasks** (~2-3 sessions):

- Create dim_player, dim_team, dim_schedule
- Build real-world and fantasy actuals marts
- Add comprehensive documentation

**Outcome**: One complete data pipeline (raw → staging → fact → dims → marts)

### Option B: Start Track B (TRANSACTIONS) ⭐ **RECOMMENDED**

**Rationale**: High business value, natural progression, seeds enable this

**Tasks** (~2-3 sessions):

- Update commissioner_parser.py to parse TRANSACTIONS tab
- Map player names → player_id via dim_player_id_xref (fuzzy matching)
- Map pick strings → pick_id via dim_pick
- Create stg_sheets\_\_transactions.sql
- Build fact_league_transactions
- Create trade analysis mart

**Outcome**: Unlock historical trade analysis, valuation comparisons

**Why now**:

- Commissioner sheet infrastructure exists
- Seeds enable name → ID mapping
- High user value (dynasty league core use case)
- Natural progression from existing commissioner sheet work

### Option C: Parallel Development 🔀

**Rationale**: Multiple tracks unblocked, maximize progress

**Session 1**: Create Track A dimensions
**Session 2**: Parse TRANSACTIONS
**Session 3**: FFanalytics weighted aggregation OR KTC fetcher

**Outcome**: Progress on multiple fronts simultaneously

______________________________________________________________________

## Technical Notes for Next Developer

### Working with player_key

- Always use player_key for grain tests and uniqueness checks
- Use player_id for business logic and FK relationships
- Filter `player_id != -1` when joining to dimensions

### Data Refresh Process

```bash
# Weekly update (after stats finalized)
PYTHONPATH=. uv run python -c "
from src.ingest.nflverse.shim import load_nflverse
load_nflverse('weekly', seasons=[2025], out_dir='data/raw/nflverse')
load_nflverse('snap_counts', seasons=[2025], out_dir='data/raw/nflverse')
load_nflverse('ff_opportunity', seasons=[2025], out_dir='data/raw/nflverse')
"

# Rebuild fact table
cd dbt/ff_analytics
uv run dbt run --select fact_player_stats
uv run dbt test --select fact_player_stats
```

### Investigating Unmapped Players

```python
import duckdb
conn = duckdb.connect('dbt/ff_analytics/target/dev.duckdb', read_only=True)

# Find unmapped players by position
conn.execute('''
    SELECT position, COUNT(DISTINCT player_key) as unmapped_count
    FROM fact_player_stats
    WHERE player_id = -1
    GROUP BY position
    ORDER BY unmapped_count DESC
''').fetchdf()
```

### Submitting to nflverse

Missing players identified (good candidates for ff_playerids PR):

- John Samuel Shenker (TE, LV) - gsis_id in snap_counts, not in ff_playerids
- Rodney Williams (TE, PIT) - gsis_id in snap_counts, not in ff_playerids

______________________________________________________________________

## Performance Metrics

| Metric            | Value             | Assessment                     |
| ----------------- | ----------------- | ------------------------------ |
| Total rows        | 6.3M              | ✅ 47% of 5-year target (13M)  |
| Build time        | ~11s              | ✅ Fast, scales linearly       |
| Database size     | ~220MB            | ✅ Reasonable                  |
| Stat consistency  | 88/88 all seasons | ✅ Perfect                     |
| Test success rate | 19/19 (100%)      | ✅ All passing                 |
| Unmapped rate     | ~6%               | ✅ Acceptable (mostly linemen) |

______________________________________________________________________

## Commit Reference

**Commit**: `3f5da23`
**Message**: "fix: add player_key composite identifier to resolve grain test duplicates"
**Files Changed**: 4 files, 157 insertions(+), 93 deletions(-)

______________________________________________________________________

## Success Criteria - ALL MET ✅

✅ **Grain test passing**: 0 duplicate violations
✅ **All tests passing**: 19/19 (100%)
✅ **Data quality documented**: NULL filtering explained with percentages
✅ **Mapping coverage documented**: Success rates per source
✅ **Architecture maintained**: Single fact table, mfl_id canonical
✅ **Traceability preserved**: Raw IDs available for unmapped players
✅ **Performance**: Build times excellent (\<15 seconds for 6.3M rows)

______________________________________________________________________

## Key Takeaways

1. **player_key solves grain violations**: Composite identifier preserves identity for unmapped players
1. **Documentation is critical**: Future maintainers need context on NULL filtering and mapping coverage
1. **Seeds are NOT blocking**: Implementation checklist was outdated, all tracks unblocked
1. **Data quality transparency**: 6.75% ff_opportunity NULL filtering is acceptable (unidentifiable records)
1. **Next phase ready**: TRANSACTIONS parsing or Track A completion, both viable paths

______________________________________________________________________

**Handoff Status**: Phase 2A Track A at 85%. All tests passing. Ready for next phase decision (Track A completion vs Track B TRANSACTIONS vs parallel development).

**Recommended next step**: Start Track B (TRANSACTIONS parsing) for high business value and natural progression.
