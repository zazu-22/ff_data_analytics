# Refined Data Model Plan v4.0

**Date:** 2025-09-29
**Status:** Approval Candidate
**Incorporates:** All items from `refined_data_model_plan_v2_feedback.md` and fixes to v3 blockers/mismatches/polishes
**Scope:** Single 12-team dynasty fantasy football league

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

If approved, I can apply these snippets to the dbt project and wire schema tests accordingly.
