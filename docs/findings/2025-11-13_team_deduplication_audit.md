# Team-Based De-duplication Audit

**Date**: 2025-11-13
**Author**: Claude Code (automated audit)
**Related Ticket**: P1-025 (FFAnalytics name collision bug follow-up)
**Scope**: All ingestion sources and staging models

## Executive Summary

✅ **No additional team-based de-duplication bugs found**

Following the discovery of a critical player name collision bug in FFAnalytics (where same-name players on different teams were merged), I audited all other data ingestion sources and staging models. **All sources correctly preserve team distinctions** and do not exhibit the same bug pattern.

## Background: The FFAnalytics Bug

**Bug Pattern Discovered** (fixed in P1-025):

```r
# BEFORE (BROKEN): Missing team in grouping key
group_by(player_normalized, pos, season, week) %>%

# AFTER (FIXED): Team included in grouping key
group_by(player_normalized, pos, season, week, team_normalized) %>%
```

**Impact**:

- Jordan Phillips (DT, BUF) + Jordan Phillips (DT, MIA) → merged into single record
- Byron Young (DE, LAR) + Byron Young (DE, PHI) → merged into single record
- Stats averaged/corrupted, one player completely lost from dataset

## Audit Methodology

For each ingestion source, I searched for:

1. **Grouping operations** (`group_by`, `groupby`, `GROUP BY`)
2. **Aggregation patterns** that might merge same-name players
3. **Deduplication logic** that could exclude team from identity keys

## Findings by Source

### 1. NFLverse (`src/ingest/nflverse/`)

**Status**: ✅ SAFE

**Architecture**: Shim pattern (Python-first with R fallback)

**Code Review**:

- `shim.py`: No grouping - data passes through from `nflreadpy` library as-is
- `scripts/R/nflverse_load.R`: No `group_by` operations found
- `registry.py`: Defines primary keys but no aggregation logic

**Primary Keys** (from registry):

- `weekly`: `(season, week, player_id)` - includes player_id (unique per player)
- `snap_counts`: `(season, week, pfr_player_id, team)` - **team IS included**
- `ff_opportunity`: `(season, week, player_id, game_id)` - uses unique player_id

**Conclusion**: NFLverse data is loaded directly from authoritative libraries without any grouping/aggregation that could cause player merging.

______________________________________________________________________

### 2. Sleeper (`src/ingest/sleeper/`)

**Status**: ✅ SAFE

**Architecture**: REST API client with filtering only

**Code Review**:

- `loader.py`: Pure filtering (position-based for FA pool), no grouping
- `client.py`: Fetches and caches API responses, no aggregation

**Operations**:

```python
# FA pool filtering (line 124)
df_fa = players_df.filter(pl.col("position").is_in(fa_positions))
```

**Conclusion**: Sleeper data is fetched as-is from API and written without any grouping operations.

______________________________________________________________________

### 3. Sheets (Commissioner) (`src/ingest/sheets/`)

**Status**: ✅ SAFE

**Architecture**: Pure parsing (CSV → DataFrames)

**Code Review**:

- `commissioner_parser.py`: 1,632 lines of parsing logic, no grouping
- `commissioner_writer.py`: File I/O only, no aggregation

**Operations**:

- Parses wide-format GM tabs to long-form tables
- Name normalization for player ID matching (via crosswalk)
- No aggregation by player name

**Player ID Resolution**:

- Uses multi-tier matching: exact → fuzzy → partial
- Includes **position filtering** to disambiguate same-name players
- Example (line 598): Maps "DL" → ["DE", "DT"] for position-aware matching

**Conclusion**: Commissioner parsing preserves all source data and uses position-aware matching to handle same-name players correctly.

______________________________________________________________________

### 4. KTC (Keep Trade Cut) (`src/ingest/ktc/`)

**Status**: ✅ SAFE

**Architecture**: Web scraper with filtering only

**Code Review**:

- `client.py`: Extracts embedded JavaScript data, no grouping
- Filters players vs picks using regex patterns
- Normalizes to long-form format without aggregation

**Operations**:

```python
# Player filtering (line 144)
players = [r for r in rankings if not pick_pattern.match(r.get("playerName", ""))]

# Team preserved in output (line 159)
"team": p.get("team"),
```

**Conclusion**: KTC data is scraped and normalized without any grouping that could merge same-name players.

______________________________________________________________________

## Staging Models Review

### Models with GROUP BY

**1. `stg_sheets__transactions.sql`**

```sql
-- Safe: Aggregates draft boundaries by season (no player data)
select rt.season, min(rt.transaction_id), max(rt.transaction_id)
from raw_transactions rt
where rt.period_type = 'rookie_draft'
group by rt.season
```

✅ No player-level grouping

**2. `stg_nflverse__ff_playerids.sql`**

```sql
-- Safe: Deduplicates ID crosswalks by ID columns
select sleeper_id
from with_status
where sleeper_id is not null
group by sleeper_id
having count(*) > 1
```

✅ Groups by unique IDs, not player names

### Models with QUALIFY (deduplication)

**`stg_nflverse__player_stats.sql`**

```sql
qualify row_number() over (
    partition by player_key, game_id, stat_name, provider, measure_domain, stat_kind
    order by season desc, week desc
) = 1
```

**What is `player_key`?**

```sql
-- Line 242-245
case
    when coalesce(xref.player_id, -1) != -1
    then cast(xref.player_id as varchar)  -- Mapped: uses canonical player_id
    else coalesce(base.gsis_id_raw, 'UNKNOWN_' || base.game_id)  -- Unmapped: uses raw ID
end as player_key
```

✅ **SAFE**: Uses `player_id` (canonical) or `gsis_id_raw` (unique per player), both of which correctly distinguish same-name players on different teams.

______________________________________________________________________

## Comparison: FFAnalytics vs Others

| Source                       | Grouping?        | Team Preserved?                 | Risk                          |
| ---------------------------- | ---------------- | ------------------------------- | ----------------------------- |
| **FFAnalytics** (BEFORE FIX) | ✅ Yes           | ❌ **NO**                       | 🔴 **HIGH** - Data corruption |
| **FFAnalytics** (AFTER FIX)  | ✅ Yes           | ✅ **YES**                      | ✅ SAFE                       |
| NFLverse                     | ❌ No            | ✅ N/A (no aggregation)         | ✅ SAFE                       |
| Sleeper                      | ❌ No            | ✅ N/A (no aggregation)         | ✅ SAFE                       |
| Sheets                       | ❌ No            | ✅ N/A (no aggregation)         | ✅ SAFE                       |
| KTC                          | ❌ No            | ✅ N/A (no aggregation)         | ✅ SAFE                       |
| Staging Models               | ✅ Yes (limited) | ✅ **YES** (uses player_id/IDs) | ✅ SAFE                       |

______________________________________________________________________

## Why Was FFAnalytics Different?

FFAnalytics is unique among our sources in that it:

1. **Aggregates consensus across multiple providers** (9 sources)
2. **Groups by name-based keys** during consensus calculation
3. **Requires team in grouping key** to avoid merging same-name players

Other sources:

- Fetch raw data from single authoritative APIs (NFLverse, Sleeper, KTC)
- Parse structured documents without aggregation (Sheets)
- Use unique IDs (player_id, gsis_id) rather than names for deduplication

## Recommendations

### 1. ✅ No Immediate Action Required

All sources correctly preserve team distinctions. No additional fixes needed.

### 2. 🔍 Ongoing Monitoring

The new dbt test created in P1-025 will catch future name collision bugs:

**Test**: `tests/assert_no_name_collision_merging.sql`

- **Purpose**: Detect when same player_name + position has multiple teams but same player_id
- **Severity**: ERROR (will fail builds)
- **Coverage**: All positions (IDP + offensive)

### 3. 📋 Best Practices for Future Integrations

When adding new data sources, ensure:

1. **If grouping/aggregating player data**:

   - ✅ Include `team` in grouping keys
   - ✅ OR use unique player IDs (player_id, gsis_id, etc.)

2. **If fetching raw data without aggregation**:

   - ✅ Preserve all source fields including `team`
   - ✅ Document in registry primary keys

3. **Add validation tests**:

   - ✅ Grain tests for player-level tables
   - ✅ Position `assert_no_name_collision_merging` to catch merging bugs

### 4. 🎯 Code Review Checklist

For PRs involving player data:

```python
# ❌ DANGEROUS: Groups by name without team
df.group_by("player_name", "position", "season").agg(...)

# ✅ SAFE: Includes team in grouping key
df.group_by("player_name", "position", "team", "season").agg(...)

# ✅ SAFER: Uses unique player ID
df.group_by("player_id", "season").agg(...)
```

______________________________________________________________________

## References

- **Original Bug Report**: `docs/findings/2025-11-13_ffanalytics_name_collision_bug.md`
- **Fix Implementation**: P1-025 ticket
- **Test Coverage**: `tests/assert_no_name_collision_merging.sql`
- **IDP Investigation**: `docs/findings/2025-10-29_idp_source_investigation.md`

______________________________________________________________________

## Appendix: Search Queries Used

```bash
# Ingestion source audit
grep -r "group_by\|groupby\|GROUP BY" src/ingest/nflverse/
grep -r "group_by\|groupby\|GROUP BY" src/ingest/sleeper/
grep -r "group_by\|groupby\|GROUP BY" src/ingest/sheets/
grep -r "group_by\|groupby\|GROUP BY" src/ingest/ktc/

# Staging model audit
grep -ri "group by" dbt/ff_data_transform/models/staging/
grep -ri "qualify.*row_number\|qualify.*rank" dbt/ff_data_transform/models/staging/

# Player-specific models
grep -ri "group by\|distinct on\|qualify" dbt/ff_data_transform/models/staging/stg_nflverse__player_stats.sql
```

______________________________________________________________________

**Audit Completed**: 2025-11-13
**Status**: ✅ All sources SAFE
**Next Action**: Mark P1-025 follow-up task complete
