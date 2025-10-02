# Refined Data Model Plan v4.0

**Date:** 2025-09-29
**Status:** Approved with Addenda
**Incorporates:** All items from `refined_data_model_plan_v2_feedback.md` and fixes to v3 blockers/mismatches/polishes
**Scope:** Single 12-team dynasty fantasy football league

**Addenda:**

- **v4.1** - Projections Integration (FFanalytics; separate fact table for 2×2 model alignment)
- **v4.2** - League Transaction History (Commissioner TRANSACTIONS tab; trade analysis)
- **v4.3** - Expanded NFL Stats + mfl_id Identity (snap counts, ff_opportunity; mfl_id as canonical player_id)

All addenda are blocked by seeds completion (Phase 1) and are parallel tracks after that.

## What Changed From v3 (Fixes Applied)

- Blocker 1 — Incremental logic: Replaced non-portable tuple/aggregate usage with 2-step CTE to compute `max_season` and `max_week` in DuckDB-safe form.
- Blocker 2 — Horizon mismatch: Removed `horizon` column from base fact (per-game grain). If needed later, define in marts.
- Mismatch — Per-game grain vs weekly source: Introduced `resolved_game_id` using schedule join, with a deterministic synthetic fallback when `game_id` is missing.
- Minor polishes:
  - Replaced `any_value()` with DuckDB-safe `arbitrary()` in marts.
  - Corrected `dim_date` date spine to use `DATEADD` and `range()`.
  - Clarified seeds booleans handling and provider scope.
  - Ensured tests and ranges allow PRE/REG/POST with postseason week ranges.

______________________________________________________________________

## Corrected SQL Snippets (Drop-In Replacements)

### 1) `models/core/dim_date.sql` (DuckDB-safe)

```sql
{{ config(materialized='table') }}

WITH date_spine AS (
    SELECT DATEADD('day', n, DATE '2009-01-01') AS calendar_date
    FROM range(0, 365 * 30) AS t(n)
)

SELECT
    CAST(strftime(calendar_date, '%Y%m%d') AS INTEGER) AS date_key,
    calendar_date,
    CAST(strftime(calendar_date, '%Y') AS INTEGER) AS year,
    CAST(strftime(calendar_date, '%m') AS INTEGER) AS month,
    CAST(strftime(calendar_date, '%d') AS INTEGER) AS day,
    strftime(calendar_date, '%A') AS day_of_week,
    CAST(strftime(calendar_date, '%w') IN ('0','6') AS BOOLEAN) AS is_weekend,
    CASE WHEN CAST(strftime(calendar_date, '%m') AS INTEGER) >= 3
         THEN CAST(strftime(calendar_date, '%Y') AS INTEGER)
         ELSE CAST(strftime(calendar_date, '%Y') AS INTEGER) - 1
    END AS fiscal_year
FROM date_spine
```

### 2) `models/core/fact_player_stats.sql` (Incremental + per-game alignment)

```sql
{{
  config(
    materialized='incremental',
    unique_key=['player_id','game_id','stat_name','provider','stat_kind','measure_domain'],
    partition_by=['season','week'],
    external=true,
    location="{{ var('external_root') }}/core/fact_player_stats"
  )
}}

-- Compute max built season/week in a portable way
WITH max_season AS (
  SELECT COALESCE(MAX(season), 0) AS max_season FROM {{ this }}
), max_week AS (
  SELECT COALESCE(MAX(week), 0) AS max_week
  FROM {{ this }}, max_season
  WHERE {{ this }}.season = max_season.max_season
), max_built AS (
  SELECT max_season.max_season, max_week.max_week FROM max_season, max_week
),

base AS (
  SELECT
    -- Canonical player id via crosswalk
    COALESCE(xref.player_id, -1) AS player_id,

    -- Join schedule for real game_id if available
    COALESCE(s.game_id,
      -- Deterministic synthetic fallback when game_id missing
      {{ dbt_utils.generate_surrogate_key([
        'w.season','w.week','w.team','w.opponent_team','w.player_id'
      ]) }}
    ) AS game_id,

    w.season,
    w.week,
    w.season_type,

    -- Additive stat columns (subset shown)
    w.completions,
    w.attempts,
    w.passing_yards,
    w.passing_tds,
    w.rushing_attempts,
    w.rushing_yards,
    w.rushing_tds,
    w.targets,
    w.receptions,
    w.receiving_yards,
    w.receiving_tds

  FROM {{ ref('stg_nflverse__weekly') }} w
  LEFT JOIN {{ ref('dim_player_id_xref') }} xref ON w.player_id = xref.gsis_id
  LEFT JOIN {{ ref('dim_schedule') }} s
    ON s.season = w.season AND s.week = w.week
    AND (s.home_team_id = w.team OR s.away_team_id = w.team)

  {% if is_incremental() %}
  WHERE (
    w.season > (SELECT max_season FROM max_built)
    OR (
      w.season = (SELECT max_season FROM max_built)
      AND w.week > (SELECT max_week FROM max_built)
    )
  )
  {% endif %}
),

unpivoted AS (
  -- Unpivot additive-only stats into long form; no 'horizon' column here.
  SELECT player_id, game_id, season, week, season_type,
         'completions' AS stat_name, completions AS stat_value,
         'real_world' AS measure_domain, 'actual' AS stat_kind, 'nflverse' AS provider
  FROM base WHERE completions IS NOT NULL
  UNION ALL
  SELECT player_id, game_id, season, week, season_type,
         'attempts', attempts, 'real_world', 'actual', 'nflverse'
  FROM base WHERE attempts IS NOT NULL
  UNION ALL
  SELECT player_id, game_id, season, week, season_type,
         'passing_yards', passing_yards, 'real_world', 'actual', 'nflverse'
  FROM base WHERE passing_yards IS NOT NULL
  UNION ALL
  SELECT player_id, game_id, season, week, season_type,
         'rushing_yards', rushing_yards, 'real_world', 'actual', 'nflverse'
  FROM base WHERE rushing_yards IS NOT NULL
  UNION ALL
  SELECT player_id, game_id, season, week, season_type,
         'receptions', receptions, 'real_world', 'actual', 'nflverse'
  FROM base WHERE receptions IS NOT NULL
  UNION ALL
  SELECT player_id, game_id, season, week, season_type,
         'receiving_yards', receiving_yards, 'real_world', 'actual', 'nflverse'
  FROM base WHERE receiving_yards IS NOT NULL
)

SELECT * FROM unpivoted
```

Notes:

- Incremental comparison now uses a two-step `max_season`/`max_week` derivation.
- `horizon` column removed; unique key unchanged.
- `resolved_game_id` via schedule join; synthetic surrogate when missing.

### 3) `models/marts/mart_real_world_actuals_weekly.sql` (grouping + attributes)

```sql
{{ config(materialized='table', partition_by=['season'], external=true) }}

SELECT
  f.player_id,
  f.season,
  f.week,
  f.season_type,
  arbitrary(p.display_name) AS display_name,
  arbitrary(p.position) AS position,
  arbitrary(p.current_team) AS current_team,
  SUM(CASE WHEN f.stat_name = 'completions' THEN f.stat_value ELSE 0 END) AS completions,
  SUM(CASE WHEN f.stat_name = 'passing_yards' THEN f.stat_value ELSE 0 END) AS passing_yards,
  SUM(CASE WHEN f.stat_name = 'passing_tds' THEN f.stat_value ELSE 0 END) AS passing_tds,
  SUM(CASE WHEN f.stat_name = 'rushing_yards' THEN f.stat_value ELSE 0 END) AS rushing_yards,
  SUM(CASE WHEN f.stat_name = 'rushing_tds' THEN f.stat_value ELSE 0 END) AS rushing_tds,
  SUM(CASE WHEN f.stat_name = 'receptions' THEN f.stat_value ELSE 0 END) AS receptions,
  SUM(CASE WHEN f.stat_name = 'receiving_yards' THEN f.stat_value ELSE 0 END) AS receiving_yards,
  SUM(CASE WHEN f.stat_name = 'receiving_tds' THEN f.stat_value ELSE 0 END) AS receiving_tds,
  COUNT(DISTINCT f.game_id) AS games_played
FROM {{ ref('fact_player_stats') }} f
JOIN {{ ref('dim_player') }} p USING (player_id)
WHERE f.measure_domain = 'real_world' AND f.stat_kind = 'actual' AND f.provider = 'nflverse'
GROUP BY 1,2,3,4
```

______________________________________________________________________

## Mismatch Resolution (Per-Game vs Weekly Source)

- Source alignment:
  - Primary source here is NFLverse weekly stats. It may not always include a reliable `game_id` for every row.
  - v4 resolves this by:
    - Attempting to map to `dim_schedule` to obtain `game_id` when possible.
    - Falling back to a deterministic synthetic `game_id` for uniqueness and consistent grain.
- Acceptance: This maintains the per-game unique key semantics even when the underlying source is week-aggregated. Downstream marts aggregate by `(player_id, season, week, season_type)` and remain correct.
- Future improvement: If per-game event data is added, replace synthetic `game_id` with true IDs and retain uniqueness.

______________________________________________________________________

## Minor Polishes Finalized

- `any_value()` → `arbitrary()` for DuckDB compatibility in marts.
- Seeds booleans: prefer `0/1` or cast in models; ensure schema.yml documents expected types.
- Provider scope: `fact_player_stats.provider` limited to `['nflverse','ffanalytics']`; document that projections populate the same fact with `stat_kind='projection'`.
- Tests: PRE/REG/POST all allowed; week ranges up to 22 for postseason; no stray 1–18 assertions.

______________________________________________________________________

## Ready-for-Approval Checklist

- Incremental logic is DuckDB-safe and handles season rollover.
- Base fact has no horizon mismatch and enforces additive-only stats.
- Per-game grain statement is consistent with implementation via `resolved_game_id`.
- Marts group by keys only; dimensional attributes selected via `arbitrary()`.
- Date spine and functions are DuckDB-safe.
- Provider enums narrowed; seeds and tests align with repo guidance.

______________________________________________________________________

## Addendum: Projections Integration (v4.1)

**Added:** 2025-09-29
**Scope:** FFanalytics projections and the 2×2 stat model

### Design Decision: Separate Facts for Actuals vs Projections

**Rationale:**

- `fact_player_stats` (v4) enforces **per-game grain** with `game_id` as part of unique key
- Projections are inherently **weekly or season-long** with no specific game association
- Separate tables avoid nullable `game_id` in primary key and maintain clean grain semantics
- Aligns with **2×2 model** where actuals and projections are distinct axes

### The 2×2 Stat Model (Actual vs Projected × Real-world vs Fantasy)

```
                 Real-World Stats          Fantasy Points
                 ----------------          --------------
Actuals          fact_player_stats         mart_fantasy_actuals_weekly
                 (provider=nflverse,       (apply scoring rules to
                  stat_kind=actual)         real-world actuals)

Projections      fact_player_projections   mart_fantasy_projections
                 (provider=ffanalytics,    (apply scoring rules to
                  stat_kind=projection)     real-world projections)
```

**Key principle:** Base facts store **real-world measures only**. Fantasy scoring is derived in marts via `dim_scoring_rule` seeds.

### Proposed Schema: `fact_player_projections`

**Grain:** One row per player per stat per projection horizon per as-of date

```sql
{{
  config(
    materialized='incremental',
    unique_key=['player_id','season','week','horizon','stat_name','provider','measure_domain','asof_date'],
    partition_by=['season'],
    external=true,
    location="{{ var('external_root') }}/core/fact_player_projections"
  )
}}

WITH base AS (
  SELECT
    -- Canonical player id via crosswalk
    COALESCE(xref.player_id, -1) AS player_id,

    p.season,
    p.week,              -- nullable for season-long projections
    p.horizon,           -- enum: 'weekly', 'rest_of_season', 'full_season'
    p.asof_date,         -- when projection was made (UTC)
    p.provider,          -- 'ffanalytics_consensus' or individual source
    p.source_site,       -- CBS, ESPN, FantasyPros, etc. (nullable for consensus)

    -- Real-world stat columns (weighted/aggregated from raw sources)
    p.completions,
    p.attempts,
    p.passing_yards,
    p.passing_tds,
    p.interceptions,
    p.rushing_attempts,
    p.rushing_yards,
    p.rushing_tds,
    p.targets,
    p.receptions,
    p.receiving_yards,
    p.receiving_tds,
    p.fumbles_lost

  FROM {{ ref('stg_ffanalytics__projections') }} p
  LEFT JOIN {{ ref('dim_player_id_xref') }} xref ON p.player_name = xref.display_name

  {% if is_incremental() %}
  WHERE p.asof_date > (SELECT COALESCE(MAX(asof_date), '1900-01-01') FROM {{ this }})
  {% endif %}
),

unpivoted AS (
  -- Unpivot to long form (measure_domain='real_world' only)
  SELECT player_id, season, week, horizon, asof_date, provider, source_site,
         'completions' AS stat_name, completions AS stat_value,
         'real_world' AS measure_domain, 'projection' AS stat_kind
  FROM base WHERE completions IS NOT NULL
  UNION ALL
  SELECT player_id, season, week, horizon, asof_date, provider, source_site,
         'passing_yards', passing_yards, 'real_world', 'projection'
  FROM base WHERE passing_yards IS NOT NULL
  UNION ALL
  SELECT player_id, season, week, horizon, asof_date, provider, source_site,
         'passing_tds', passing_tds, 'real_world', 'projection'
  FROM base WHERE passing_tds IS NOT NULL
  UNION ALL
  SELECT player_id, season, week, horizon, asof_date, provider, source_site,
         'rushing_yards', rushing_yards, 'real_world', 'projection'
  FROM base WHERE rushing_yards IS NOT NULL
  UNION ALL
  SELECT player_id, season, week, horizon, asof_date, provider, source_site,
         'receptions', receptions, 'real_world', 'projection'
  FROM base WHERE receptions IS NOT NULL
  UNION ALL
  SELECT player_id, season, week, horizon, asof_date, provider, source_site,
         'receiving_yards', receiving_yards, 'real_world', 'projection'
  FROM base WHERE receiving_yards IS NOT NULL
  -- ... additional stats
)

SELECT * FROM unpivoted
```

**Notes:**

- `horizon` column captures projection timeframe explicitly
- `week` is nullable for season-long projections (horizon='full_season')
- No `game_id` (projections are not game-specific)
- `asof_date` enables time-travel queries ("what were projections as of week 3?")
- `provider` can be 'ffanalytics_consensus' (weighted) or individual sources
- Incremental on `asof_date` (append-only by projection run date)

### Integration with Existing Marts

**Real-world projections mart:**

```sql
-- models/marts/mart_real_world_projections.sql
SELECT
  f.player_id,
  f.season,
  f.week,
  f.horizon,
  f.asof_date,
  arbitrary(p.display_name) AS display_name,
  arbitrary(p.position) AS position,
  arbitrary(p.current_team) AS current_team,
  SUM(CASE WHEN f.stat_name = 'passing_yards' THEN f.stat_value ELSE 0 END) AS passing_yards,
  SUM(CASE WHEN f.stat_name = 'rushing_yards' THEN f.stat_value ELSE 0 END) AS rushing_yards,
  SUM(CASE WHEN f.stat_name = 'receiving_yards' THEN f.stat_value ELSE 0 END) AS receiving_yards
  -- ... additional stats
FROM {{ ref('fact_player_projections') }} f
JOIN {{ ref('dim_player') }} p USING (player_id)
WHERE f.measure_domain = 'real_world' AND f.stat_kind = 'projection'
  AND f.provider = 'ffanalytics_consensus'
  AND f.horizon = 'weekly'  -- filter to weekly projections
GROUP BY 1,2,3,4,5
```

**Fantasy projections mart (apply scoring):**

```sql
-- models/marts/mart_fantasy_projections.sql
WITH real_world AS (
  SELECT * FROM {{ ref('mart_real_world_projections') }}
  WHERE horizon = 'weekly'
),
scoring AS (
  SELECT * FROM {{ ref('dim_scoring_rule') }}
  WHERE is_current = true  -- latest scoring rules
)
SELECT
  rw.*,
  (rw.passing_yards * s.passing_yards_points) +
  (rw.passing_tds * s.passing_td_points) +
  (rw.rushing_yards * s.rushing_yards_points) +
  (rw.rushing_tds * s.rushing_td_points) +
  (rw.receptions * s.reception_points) +  -- Half-PPR
  (rw.receiving_yards * s.receiving_yards_points) +
  (rw.receiving_tds * s.receiving_td_points)
  AS projected_fantasy_points
FROM real_world rw
CROSS JOIN scoring s
```

**Variance analysis mart (actuals vs projections):**

```sql
-- models/marts/mart_projection_variance.sql
SELECT
  a.player_id,
  a.season,
  a.week,
  a.display_name,
  a.position,
  p.asof_date AS projection_date,
  a.rushing_yards AS actual_rushing_yards,
  p.rushing_yards AS projected_rushing_yards,
  a.rushing_yards - p.rushing_yards AS rushing_yards_variance,
  -- ... additional stat comparisons
FROM {{ ref('mart_real_world_actuals_weekly') }} a
JOIN {{ ref('mart_real_world_projections') }} p
  ON a.player_id = p.player_id
  AND a.season = p.season
  AND a.week = p.week
  AND p.horizon = 'weekly'
WHERE p.provider = 'ffanalytics_consensus'
  AND p.asof_date <= a.game_date  -- only compare to projections made before the game
```

### Implementation Sequence (v4.1)

Per updated implementation checklist:

1. **Phase 1**: Complete Section 7 seeds (BLOCKER - especially `dim_player_id_xref` for name mapping)
1. **Section 6 completion**:
   - Weighted aggregation across 8 FFanalytics sources
   - Output real-world projections in long form (no fantasy scoring yet)
1. **Staging**: Create `stg_ffanalytics__projections.sql`
   - Map player names to canonical `player_id`
   - Normalize horizon values
   - Validate stat ranges
1. **Core fact**: Build `fact_player_projections` with incremental on `asof_date`
1. **Marts**: Real-world projections → fantasy projections (apply scoring) → variance analysis

**Parallel Track**: This is independent of NFL actuals (Track A) and can proceed after seeds.

**Status:** Added to implementation checklist Section 6 and Section 7.

______________________________________________________________________

## Addendum: League Transaction History (v4.2)

**Added:** 2025-09-29
**Scope:** Commissioner TRANSACTIONS tab integration

### Gap Identified

The TRANSACTIONS tab contains ~4,000 rows of detailed league transaction history (trades, cuts, waivers, signings, FAAD) that is not captured by the current v4 plan. Roster snapshots show current state only; transaction history provides:

- Multi-asset trades (players, picks, cap space) with parties
- Historical audit trail
- Contract terms at signing time
- Trade valuation context (actual trades vs KTC market)

### Proposed Addition: `fact_league_transactions`

**Grain:** One row per asset per transaction (matches raw TRANSACTIONS tab structure)

**Schema:**

```sql
{{ config(materialized='table', partition_by=['transaction_year'], external=true) }}

SELECT
  transaction_id,  -- from Sort column; groups multi-asset trades
  transaction_date,
  CAST(strftime(transaction_date, '%Y') AS INTEGER) AS transaction_year,
  transaction_type,  -- enum: trade, cut, waivers, signing, faad
  from_franchise_id,  -- nullable; 'Waiver Wire' for FA signings
  to_franchise_id,    -- nullable; 'Waiver Wire' for cuts
  asset_type,  -- enum: player, pick, cap_space

  -- Asset references (nullable based on asset_type)
  player_id,  -- FK to dim_player (when asset_type=player)
  pick_id,    -- FK to dim_pick (when asset_type=pick)

  -- Contract details (when applicable)
  contract_years,
  contract_total,
  contract_split,  -- JSON array of year splits
  rfa_matched,
  franchise_tag,
  faad_compensation,

  -- Metadata
  source_row_hash,
  dt  -- partition from raw load
FROM {{ ref('stg_sheets__transactions') }}
```

**Key Dependencies:**

- **Seeds required first**: `dim_player_id_xref` (player name → canonical ID), `dim_pick`, `dim_asset`
- **Staging**: `stg_sheets__transactions` maps raw TRANSACTIONS columns to normalized schema
- **New dimension**: `dim_franchise` (league team/owner dimension)

**Integration with Existing Plan:**

- Does not block v4 approval (NFL stats are independent)
- Enables trade analysis marts that join to `fact_asset_market_values` (KTC)
- Supports roster reconstruction via transaction replay

### New Marts Enabled

1. **`mart_trade_history`** - Aggregated trade summaries by franchise

   - Total trades, players/picks acquired/sent, cap transfers
   - Window functions to show trade patterns over time

1. **`mart_trade_valuations`** - Actual trades vs KTC market comparison

   - Join `fact_league_transactions` (asset_type=player) to `fact_asset_market_values`
   - Calculate trade value differential (market vs actual)
   - Identify value wins/losses per franchise

1. **`mart_roster_timeline`** - Reconstruct roster state at any point in time

   - Window functions over transaction history ordered by transaction_date
   - Current roster = initial state + cumulative transactions
   - Enables "what was my roster on 2024-10-15?" queries

### Implementation Sequence (v4.2)

Per updated implementation checklist:

1. **Phase 1**: Complete Section 7 seeds (BLOCKER)
1. **Phase 2 - Track B**: Parse TRANSACTIONS → staging → fact_league_transactions
1. **Phase 3**: Trade analysis marts (depends on KTC integration for valuations)

**Status:** Added to implementation checklist Section 4 and Section 7.

______________________________________________________________________

## Addendum: Expanded NFL Stats + mfl_id Identity (v4.3)

**Added:** 2025-09-30
**Scope:** Comprehensive nflverse stats integration and player identity architecture
**Related ADRs:** ADR-009, ADR-010

### Decisions Made

#### 1. Single Consolidated Fact Table for All NFL Stats (ADR-009)

**Problem:** nflverse provides multiple stat datasets with identical grain:

- `load_player_stats`: Base stats (passing, rushing, receiving, defense, kicking) - ~50 stat types
- `load_snap_counts`: Snap participation (offense, defense, ST) - 6 stat types
- `load_ff_opportunity`: Expected stats, variances, team shares - ~40 stat types

**Decision:** Integrate all three sources into single `fact_player_stats` table.

**Rationale:**

- **Same grain:** player-game-stat across all sources
- **Manageable scale:** 12-15M rows (5 years), well within DuckDB's 10M-1B row sweet spot
- **Avoids fact-to-fact joins:** Kimball anti-pattern (guidance p. 724-759)
- **Simpler queries:** Single table scan vs complex multi-table joins
- **Better compression:** Parquet columnar storage benefits from unified schema

Scale Analysis:

```text
Active players: 2,000
Games per player per season: 15 (avg with injuries/backups)
Seasons: 5
Stat types: 96 (50 base + 6 snap + 40 opportunity)
Sparsity: 0.4 (position-specific stats)

Total: 2,000 × 15 × 5 × 96 × 0.4 = 28.8M worst case
Realistic after sparsity: 12-15M rows
Storage: 900 MB - 1.8 GB (Parquet compressed)
Partitions: 115 (5 seasons × 23 weeks), ~130K rows each
```

#### 2. mfl_id as Canonical Player Identity (ADR-010)

**Problem:** Original plan used `gsis_id` as canonical `player_id`, but:

- `gsis_id` is NFL-specific (couples architecture to NFL systems)
- Fantasy platforms use different IDs (Sleeper, ESPN, Yahoo, KTC, etc.)
- `load_ff_playerids` provides 19 provider IDs with platform-neutral crosswalk

**Decision:** Use nflverse's `mfl_id` as canonical `player_id`.

**Rationale:**

- **Platform agnostic:** Created by nflverse specifically as neutral crosswalk ID
- **Separates concerns:** Canonical ID distinct from provider IDs
- **Comprehensive:** Maps to 19 fantasy platforms/stat providers
- **Stable:** Doesn't change with team/platform migrations
- **Future-proof:** Can add new platforms without schema changes

**Provider Coverage (from ff_playerids):**

```text
mfl_id (canonical), gsis_id, sleeper_id, espn_id, yahoo_id, pfr_id,
fantasypros_id, pff_id, cbs_id, ktc_id, sportradar_id, fleaflicker_id,
rotowire_id, rotoworld_id, stats_id, stats_global_id, fantasy_data_id,
swish_id, cfbref_id, nfl_id
```

### Updated Schemas

#### dim_player_id_xref (Seed Table)

**Source:** `samples/nflverse/ff_playerids/`

```sql
CREATE TABLE dim_player_id_xref (
    player_id VARCHAR PRIMARY KEY,  -- mfl_id (canonical)

    -- All 19 provider IDs from ff_playerids
    mfl_id VARCHAR,
    gsis_id VARCHAR,
    sleeper_id INTEGER,
    espn_id INTEGER,
    yahoo_id VARCHAR,
    pfr_id VARCHAR,
    fantasypros_id INTEGER,
    pff_id INTEGER,
    cbs_id INTEGER,
    ktc_id INTEGER,
    sportradar_id VARCHAR,
    fleaflicker_id VARCHAR,
    rotowire_id INTEGER,
    rotoworld_id VARCHAR,
    stats_id INTEGER,
    stats_global_id INTEGER,
    fantasy_data_id VARCHAR,
    swish_id VARCHAR,
    cfbref_id VARCHAR,
    nfl_id INTEGER,

    -- Attributes for name-based matching
    name VARCHAR,
    merge_name VARCHAR,  -- Normalized for TRANSACTIONS fuzzy matching
    position VARCHAR,
    team VARCHAR,
    birthdate DATE,
    draft_year INTEGER
);
```

#### fact_player_stats (Expanded)

**Grain:** One row per player per game per stat per provider

```sql
{{
  config(
    materialized='incremental',
    unique_key=['player_id','game_id','stat_name','provider','measure_domain','stat_kind'],
    partition_by=['season','week'],
    external=true,
    location="{{ var('external_root') }}/core/fact_player_stats"
  )
}}

-- Incremental logic (unchanged)
WITH max_season AS (
  SELECT COALESCE(MAX(season), 0) AS max_season FROM {{ this }}
), max_week AS (
  SELECT COALESCE(MAX(week), 0) AS max_week
  FROM {{ this }}, max_season
  WHERE {{ this }}.season = max_season.max_season
), max_built AS (
  SELECT max_season.max_season, max_week.max_week FROM max_season, max_week
)

-- Union all three stat sources
SELECT * FROM {{ ref('stg_nflverse__player_stats') }}  -- Base stats (~50 types)
{% if is_incremental() %}
WHERE (season > (SELECT max_season FROM max_built)
    OR (season = (SELECT max_season FROM max_built) AND week > (SELECT max_week FROM max_built)))
{% endif %}

UNION ALL

SELECT * FROM {{ ref('stg_nflverse__snap_counts') }}  -- Snap stats (6 types)
{% if is_incremental() %}
WHERE (season > (SELECT max_season FROM max_built)
    OR (season = (SELECT max_season FROM max_built) AND week > (SELECT max_week FROM max_built)))
{% endif %}

UNION ALL

SELECT * FROM {{ ref('stg_nflverse__ff_opportunity') }}  -- Expected stats (~40 types)
{% if is_incremental() %}
WHERE (season > (SELECT max_season FROM max_built)
    OR (season = (SELECT max_season FROM max_built) AND week > (SELECT max_week FROM max_built)))
{% endif %}
```

### Updated Staging Models

#### stg_nflverse\_\_player_stats.sql

**Updated to use mfl_id:**

```sql
{{ config(materialized='view') }}

WITH base AS (
  SELECT
    -- Map gsis_id → mfl_id via crosswalk
    COALESCE(xref.player_id, -1) AS player_id,  -- mfl_id

    -- Game identifiers
    COALESCE(s.game_id,
      {{ dbt_utils.generate_surrogate_key([
        'w.season','w.week','w.team','w.opponent_team','w.player_id'
      ]) }}
    ) AS game_id,

    w.season,
    w.week,
    w.season_type,

    -- Base stats (existing - ~50 columns)
    w.completions,
    w.attempts,
    w.passing_yards,
    w.passing_tds,
    -- ... (all other base stats)

  FROM {{ source('raw_nflverse', 'player_stats') }} w
  LEFT JOIN {{ ref('dim_player_id_xref') }} xref
    ON w.player_id = xref.gsis_id  -- Explicit mapping
  LEFT JOIN {{ ref('dim_schedule') }} s
    ON s.season = w.season AND s.week = w.week
    AND (s.home_team_id = w.team OR s.away_team_id = w.team)
),

unpivoted AS (
  -- Unpivot to long form (existing logic)
  SELECT player_id, game_id, season, week, season_type,
         'completions' AS stat_name, completions AS stat_value,
         'real_world' AS measure_domain, 'actual' AS stat_kind, 'nflverse' AS provider
  FROM base WHERE completions IS NOT NULL
  UNION ALL
  -- ... (all other stats)
)

SELECT * FROM unpivoted
```

#### stg_nflverse\_\_snap_counts.sql (NEW)

```sql
{{ config(materialized='view') }}

WITH base AS (
  SELECT
    COALESCE(xref.player_id, -1) AS player_id,  -- mfl_id
    s.game_id,
    s.season,
    s.week,
    s.game_type AS season_type,

    -- Snap stats
    s.offense_snaps,
    s.offense_pct,
    s.defense_snaps,
    s.defense_pct,
    s.st_snaps,
    s.st_pct

  FROM {{ source('raw_nflverse', 'snap_counts') }} s
  LEFT JOIN {{ ref('dim_player_id_xref') }} xref
    ON s.pfr_player_id = xref.pfr_id  -- Map via PFR ID
),

unpivoted AS (
  SELECT player_id, game_id, season, week, season_type,
         'offense_snaps' AS stat_name, offense_snaps AS stat_value,
         'real_world' AS measure_domain, 'actual' AS stat_kind, 'nflverse' AS provider
  FROM base WHERE offense_snaps IS NOT NULL
  UNION ALL
  SELECT player_id, game_id, season, week, season_type,
         'offense_pct' AS stat_name, offense_pct AS stat_value,
         'real_world' AS measure_domain, 'actual' AS stat_kind, 'nflverse' AS provider
  FROM base WHERE offense_pct IS NOT NULL
  UNION ALL
  SELECT player_id, game_id, season, week, season_type,
         'defense_snaps' AS stat_name, defense_snaps AS stat_value,
         'real_world' AS measure_domain, 'actual' AS stat_kind, 'nflverse' AS provider
  FROM base WHERE defense_snaps IS NOT NULL
  UNION ALL
  SELECT player_id, game_id, season, week, season_type,
         'defense_pct' AS stat_name, defense_pct AS stat_value,
         'real_world' AS measure_domain, 'actual' AS stat_kind, 'nflverse' AS provider
  FROM base WHERE defense_pct IS NOT NULL
  UNION ALL
  SELECT player_id, game_id, season, week, season_type,
         'st_snaps' AS stat_name, st_snaps AS stat_value,
         'real_world' AS measure_domain, 'actual' AS stat_kind, 'nflverse' AS provider
  FROM base WHERE st_snaps IS NOT NULL
  UNION ALL
  SELECT player_id, game_id, season, week, season_type,
         'st_pct' AS stat_name, st_pct AS stat_value,
         'real_world' AS measure_domain, 'actual' AS stat_kind, 'nflverse' AS provider
  FROM base WHERE st_pct IS NOT NULL
)

SELECT * FROM unpivoted
```

#### stg_nflverse\_\_ff_opportunity.sql (NEW)

```sql
{{ config(materialized='view') }}

-- Note: ff_opportunity has 170+ columns
-- Unpivot key metrics: expected stats, variances, team shares

WITH base AS (
  SELECT
    COALESCE(xref.player_id, -1) AS player_id,  -- mfl_id
    o.game_id,
    CAST(o.season AS INTEGER) AS season,
    CAST(o.week AS INTEGER) AS week,
    'REG' AS season_type,  -- ff_opportunity doesn't have season_type

    -- Expected stats
    o.pass_yards_gained_exp,
    o.rush_yards_gained_exp,
    o.rec_yards_gained_exp,
    o.receptions_exp,
    o.pass_touchdown_exp,
    o.rec_touchdown_exp,
    o.rush_touchdown_exp,

    -- Variances (actual - expected)
    o.pass_yards_gained_diff,
    o.rush_yards_gained_diff,
    o.rec_yards_gained_diff,
    o.receptions_diff,

    -- Team shares
    o.pass_air_yards,
    o.rec_air_yards,
    o.pass_attempt,
    o.rec_attempt,
    o.rush_attempt

  FROM {{ source('raw_nflverse', 'ff_opportunity') }} o
  LEFT JOIN {{ ref('dim_player_id_xref') }} xref
    ON o.player_id = xref.gsis_id  -- ff_opportunity uses gsis_id
),

unpivoted AS (
  -- Expected stats
  SELECT player_id, game_id, season, week, season_type,
         'pass_yards_gained_exp' AS stat_name, pass_yards_gained_exp AS stat_value,
         'real_world' AS measure_domain, 'actual' AS stat_kind, 'nflverse' AS provider
  FROM base WHERE pass_yards_gained_exp IS NOT NULL
  UNION ALL
  SELECT player_id, game_id, season, week, season_type,
         'rush_yards_gained_exp', rush_yards_gained_exp,
         'real_world', 'actual', 'nflverse'
  FROM base WHERE rush_yards_gained_exp IS NOT NULL
  UNION ALL
  SELECT player_id, game_id, season, week, season_type,
         'rec_yards_gained_exp', rec_yards_gained_exp,
         'real_world', 'actual', 'nflverse'
  FROM base WHERE rec_yards_gained_exp IS NOT NULL
  UNION ALL
  SELECT player_id, game_id, season, week, season_type,
         'receptions_exp', receptions_exp,
         'real_world', 'actual', 'nflverse'
  FROM base WHERE receptions_exp IS NOT NULL

  -- Variances
  UNION ALL
  SELECT player_id, game_id, season, week, season_type,
         'pass_yards_gained_diff', pass_yards_gained_diff,
         'real_world', 'actual', 'nflverse'
  FROM base WHERE pass_yards_gained_diff IS NOT NULL
  UNION ALL
  SELECT player_id, game_id, season, week, season_type,
         'rec_yards_gained_diff', rec_yards_gained_diff,
         'real_world', 'actual', 'nflverse'
  FROM base WHERE rec_yards_gained_diff IS NOT NULL

  -- Team shares (sample - add more as needed)
  UNION ALL
  SELECT player_id, game_id, season, week, season_type,
         'pass_air_yards', pass_air_yards,
         'real_world', 'actual', 'nflverse'
  FROM base WHERE pass_air_yards IS NOT NULL
  UNION ALL
  SELECT player_id, game_id, season, week, season_type,
         'rec_air_yards', rec_air_yards,
         'real_world', 'actual', 'nflverse'
  FROM base WHERE rec_air_yards IS NOT NULL
  -- ... (add remaining key metrics)
)

SELECT * FROM unpivoted
```

### Implementation Sequence

Per updated implementation checklist:

1. **Phase 1 (BLOCKER)**: Generate ff_playerids sample and create dim_player_id_xref seed

   - Add ff_playerids to nflverse registry
   - Run `make samples-nflverse DATASETS=ff_playerids`
   - Generate seed CSV with all 19 provider IDs

1. **Phase 2**: Add snap_counts and ff_opportunity datasets

   - Add to nflverse registry
   - Run `make samples-nflverse DATASETS=snap_counts,ff_opportunity`

1. **Phase 2**: Create new staging models

   - `stg_nflverse__snap_counts.sql`
   - `stg_nflverse__ff_opportunity.sql`

1. **Phase 2**: Update existing staging models

   - Replace `player_id` with crosswalk join to get mfl_id
   - Update `stg_nflverse__player_stats.sql`

1. **Phase 2**: Expand fact_player_stats with UNION ALL

1. **Phase 3**: Update marts to leverage new stats

   - Snap efficiency analysis: rushing yards per offensive snap
   - Variance analysis: actual vs expected (using ff_opportunity built-in xStats)
   - Target/opportunity share analysis

### Query Examples

**Snap efficiency:**

```sql
SELECT
    p.display_name,
    f.season,
    f.week,
    MAX(CASE WHEN f.stat_name = 'rushing_yards' THEN f.stat_value END) AS rushing_yards,
    MAX(CASE WHEN f.stat_name = 'offense_snaps' THEN f.stat_value END) AS offense_snaps,
    rushing_yards / NULLIF(offense_snaps, 0) AS yards_per_snap
FROM {{ ref('fact_player_stats') }} f
JOIN {{ ref('dim_player') }} p ON f.player_id = p.player_id
WHERE f.season = 2024 AND f.week = 5
GROUP BY 1,2,3
HAVING offense_snaps > 0
ORDER BY yards_per_snap DESC
LIMIT 20;
```

**Built-in variance analysis:**

```sql
SELECT
    p.display_name,
    f.season,
    SUM(CASE WHEN f.stat_name = 'receptions' THEN f.stat_value END) AS receptions_actual,
    SUM(CASE WHEN f.stat_name = 'receptions_exp' THEN f.stat_value END) AS receptions_expected,
    SUM(CASE WHEN f.stat_name = 'receptions_diff' THEN f.stat_value END) AS receptions_variance
FROM {{ ref('fact_player_stats') }} f
JOIN {{ ref('dim_player') }} p ON f.player_id = p.player_id
WHERE f.season = 2024 AND p.position = 'WR'
GROUP BY 1,2
ORDER BY receptions_variance DESC
LIMIT 20;
-- Top overperformers vs expected receptions
```

### Benefits

1. **Comprehensive stats:** 96 stat types per player-game vs previous 50
1. **Built-in variance:** ff_opportunity provides expected stats + variances (no need to calculate)
1. **Opportunity metrics:** Team shares, air yards, target rates for advanced analysis
1. **Snap context:** Correlate production with playing time
1. **Platform-agnostic identity:** Support all 19 fantasy platforms via single crosswalk
1. **Future-proof:** Can add new providers without schema changes

**Status:** Approved; implementation blocked by Phase 1 seeds (ff_playerids required first).

______________________________________________________________________

If approved, these addenda can be implemented following the phased approach in the updated implementation checklist.
