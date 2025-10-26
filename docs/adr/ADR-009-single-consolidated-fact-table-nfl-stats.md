# ADR-009: Single Consolidated Fact Table for NFL Player Stats

**Status:** Accepted
**Date:** 2025-09-30
**Decision Makers:** Jason Shaffer, Development Team
**Supersedes:** None
**Related:** ADR-007 (Separate Facts for Actuals vs Projections)

## Context

The Fantasy Football Analytics platform ingests multiple types of NFL player statistics from nflverse:

1. **Base player stats** (`load_player_stats`): Traditional passing, rushing, receiving, defense, kicking stats (~50 stat types)
1. **Snap counts** (`load_snap_counts`): Offensive, defensive, and special teams snap participation (~6 stat types)
1. **FF opportunity metrics** (`load_ff_opportunity`): Expected stats, variances, and team shares (~40 stat types)

All three datasets share the **same grain**: one row per player per game.

### Problem Statement

**Question:** Should these be integrated into a single `fact_player_stats` table, or should we create separate fact tables (`fact_player_stats`, `fact_player_snaps`, `fact_ff_opportunity`)?

### Constraints

- Must maintain per-game grain consistency across all NFL actuals
- Must support efficient queries correlating different stat types (e.g., rushing yards + offensive snaps)
- Must scale to 5+ years of historical data
- Must partition efficiently for incremental loads
- Must avoid Kimball anti-patterns (particularly fact-to-fact joins)
- DuckDB + external Parquet storage layer

## Decision

**Integrate all NFL player stats into a single `fact_player_stats` table** with expanded unpivot logic.

### Grain

One row per player, per game, per stat type, per provider:

```text
Unique key: (player_id, game_id, season, week, stat_name, provider, measure_domain, stat_kind)
```

### Schema

```sql
CREATE TABLE fact_player_stats (
    -- Grain keys
    player_id INTEGER NOT NULL,           -- FK to dim_player (mfl_id)
    game_id VARCHAR NOT NULL,             -- FK to dim_schedule
    season INTEGER NOT NULL,
    week INTEGER NOT NULL,
    stat_name VARCHAR NOT NULL,           -- 'rushing_yards', 'offense_snaps', 'receptions_exp', etc.
    provider VARCHAR NOT NULL,            -- 'nflverse'
    measure_domain VARCHAR NOT NULL,      -- 'real_world'
    stat_kind VARCHAR NOT NULL,           -- 'actual'

    -- Facts
    stat_value DECIMAL,

    -- Metadata
    asof_date DATE NOT NULL,

    UNIQUE(player_id, game_id, season, week, stat_name, provider, measure_domain, stat_kind)
);
```

### Stat Type Coverage

**Total:** ~96 stat types per player-game

| Source | Stat Count | Examples |
| -------------- | ---------- | ------------------------------------------------------------- |
| Base stats | ~50 | `passing_yards`, `rushing_tds`, `receptions`, `def_sacks` |
| Snap counts | 6 | `offense_snaps`, `offense_pct`, `defense_snaps`, `st_snaps` |
| FF opportunity | ~40 | `pass_yards_gained_exp`, `receptions_diff`, `air_yards_share` |

## Rationale

### 1. Scale Analysis

Projected row counts (5 years)

```text
Active NFL players: ~2,000
Games per player per season (avg): 15 (accounting for injuries, backups)
Seasons: 5
Stats per player-game: 96 (after unpivot)
Sparsity factor: 0.4 (not all positions have all stats)

Total rows = 2,000 × 15 × 5 × 96 × 0.4 = 28.8M rows (worst case)
Realistic: ~12-15M rows after sparsity
```

Storage estimate

```text
Columns: 12 (after unpivot)
Avg bytes per column: 50
Uncompressed: 15M rows × 12 cols × 50 bytes = 9 GB
Parquet compression (5-10x): 900 MB - 1.8 GB on disk
```

Partitioned by season/week

```text
Partitions: 5 seasons × 23 weeks = 115 partitions
Per partition: ~130K rows, ~8-15 MB
Query pattern: Most queries scan 1-2 partitions (200-300K rows)
```

### 2. DuckDB Performance Characteristics

- **Optimal range:** 10M-1B rows with columnar storage
- **Columnar execution:** Only reads columns in SELECT clause
- **Partition pruning:** WHERE season=2024 AND week=5 scans only 1 partition
- **Vectorized processing:** Processes row batches in parallel
- **15M rows well within comfort zone**

### 3. Kimball Anti-Pattern Avoidance

**With separate fact tables (ANTI-PATTERN):**

```sql
-- BAD: Fact-to-fact join (Kimball guidance p. 724-759)
SELECT
    s.player_id,
    s.rushing_yards,
    sn.offense_snaps,
    opp.rush_yards_gained_exp
FROM fact_player_stats s
JOIN fact_player_snaps sn
    ON s.player_id = sn.player_id
    AND s.game_id = sn.game_id
    AND s.season = sn.season
    AND s.week = sn.week
JOIN fact_ff_opportunity opp
    ON s.player_id = opp.player_id
    AND s.game_id = opp.game_id
    -- Cardinality issues, unpredictable performance
```

**With single fact table (CORRECT):**

```sql
-- GOOD: Single fact table scan
SELECT
    player_id,
    MAX(CASE WHEN stat_name = 'rushing_yards' THEN stat_value END) AS rushing_yards,
    MAX(CASE WHEN stat_name = 'offense_snaps' THEN stat_value END) AS offense_snaps,
    MAX(CASE WHEN stat_name = 'rush_yards_gained_exp' THEN stat_value END) AS rush_exp
FROM fact_player_stats
WHERE player_id = ? AND season = ? AND week = ?
GROUP BY player_id, game_id, season, week;
-- Single table scan, predictable cardinality, partition pruned
```

### 4. Same Grain = Same Table

Per Kimball methodology:

- All three sources share **identical grain**: player-game-stat
- All are **additive facts** (numeric measurements summed across time/players)
- All are **immutable** (historical game stats never change)
- All use **same dimensions** (player, game, date)
- All have **same update cadence** (weekly batch loads)

**When to split facts:**

- ❌ Different grain (e.g., weekly vs season-level) → **Not our case**
- ❌ Different update cadence (real-time vs batch) → **Not our case**
- ❌ >100M rows per fact type → **Not our case**
- ❌ Dramatically different access patterns → **Not our case**

## Consequences

### Positive

1. **Simpler queries:** No fact-to-fact joins required
1. **Single source of truth:** All NFL actuals in one place
1. **Better compression:** Parquet columnar format benefits from unified schema
1. **Easier maintenance:** One table to test, partition, compact
1. **Consistent grain enforcement:** Single unique key test in dbt
1. **Correlation queries:** Naturally express "rushing yards per offensive snap" queries

### Negative

1. **Sparse rows:** Not all players have all stats (mitigated by Parquet columnar storage)
1. **Larger unpivot logic:** More UNION ALL branches in staging (mitigated by code generation)
1. **Mixed stat semantics:** Absolute counts, percentages, expected values in same column (mitigated by stat_name prefix conventions)

### Mitigation Strategies

**Sparsity:**

- Parquet only stores non-null values efficiently
- Columnar format: queries only read relevant stat_name rows
- Impact on storage: minimal (~10% overhead vs separate tables)

**Unpivot complexity:**

- Generate staging SQL via dbt macros or Python scripts
- Template pattern for stat unpivot logic
- Document stat_name conventions (e.g., `_pct` suffix for percentages, `_exp` for expected values)

**Monitoring:**

- Track partition sizes (alert if >50 MB)
- Monitor query performance on 90th percentile latency
- Add compaction job if small files accumulate

## Implementation

### Phase 1: Staging Models

Create three staging models that normalize to common grain:

```sql
-- stg_nflverse__player_stats.sql (existing, expand)
-- stg_nflverse__snap_counts.sql (new)
-- stg_nflverse__ff_opportunity.sql (new)
```

### Phase 2: Core Fact

Expand `fact_player_stats` with UNION ALL:

```sql
-- fact_player_stats.sql
{{ config(
    materialized='incremental',
    unique_key=['player_id','game_id','stat_name','provider','measure_domain','stat_kind'],
    partition_by=['season','week'],
    external=true
) }}

SELECT * FROM {{ ref('stg_nflverse__player_stats') }}  -- Base stats
UNION ALL
SELECT * FROM {{ ref('stg_nflverse__snap_counts') }}   -- Snap participation
UNION ALL
SELECT * FROM {{ ref('stg_nflverse__ff_opportunity') }} -- Expected stats
```

### Phase 3: Testing

```yaml
# fact_player_stats.yml
tests:
  - dbt_utils.unique_combination_of_columns:
      combination_of_columns:
        - player_id
        - game_id
        - stat_name
        - provider
        - measure_domain
        - stat_kind
  - accepted_values:
      column_name: stat_name
      values: ['passing_yards', 'rushing_yards', ..., 'offense_snaps', ..., 'receptions_exp', ...]
```

## Alternatives Considered

### Alternative 1: Separate Fact Tables

**Rejected because:**

- Requires fact-to-fact joins (Kimball anti-pattern)
- Identical grain across all sources
- No performance benefit at 15M row scale
- More complex query patterns
- 3x the number of tables to maintain

### Alternative 2: Wide Fact Table (Columns per Stat)

**Rejected because:**

- Creates 96-column table (centipede fact table anti-pattern)
- Hard to add new stats dynamically
- Poor compression (many nulls for position-specific stats)
- Violates long-form pattern established in v4.0

### Alternative 3: Separate by Update Cadence

**Rejected because:**

- All three sources update on same weekly batch schedule
- No real-time vs batch split needed
- Doesn't reduce complexity

## References

- [Kimball Dimensional Modeling Guidance](../../architecture/kimball_modeling_guidance/kimbal_modeling.md) (lines 724-759: Fact-to-Fact Join Anti-Pattern)
- [SPEC-1 v2.2](../spec/SPEC-1_v_2.2.md) (2×2 Stat Model)
- [ADR-007](./ADR-007-separate-fact-tables-actuals-vs-projections.md) (Actuals vs Projections Separation)
- [Refined Data Model Plan v4.0](../spec/refined_data_model_plan_v4.md)
- DuckDB Documentation: [Optimal Dataset Sizes](https://duckdb.org/docs/guides/performance/overview)

## Revision History

- **2025-09-30:** Initial decision (v1.0)
