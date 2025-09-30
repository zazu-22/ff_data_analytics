# ADR-007: Separate Fact Tables for Actuals vs Projections

**Status:** Accepted
**Date:** 2025-09-29
**Decision Makers:** Jason Shaffer, Development Team

## Context

The Fantasy Football Analytics data model follows a **2×2 stat model** (Actual vs Projected × Real-world vs Fantasy) as defined in SPEC-1 v2.2. The refined data model plan v4.0 specified a per-game grain for `fact_player_stats` to handle NFL actuals. However, projections from FFanalytics are inherently **weekly or season-long** and have no specific game association.

### Problem Statement

- `fact_player_stats` (v4.0) enforces **per-game grain** with `game_id` as part of the unique key
- FFanalytics projections are **weekly** (horizon='weekly') or **season-long** (horizon='full_season', 'rest_of_season')
- Projections have no meaningful `game_id` to populate
- The original SPEC-1 v2.2 proposed a single fact table with a `horizon` column, but v4.0 removed it to fix a grain mismatch for actuals

### Constraints

- Must maintain per-game grain for actuals (required for NFL game-level analysis)
- Must support weekly and season-long projections (required for FFanalytics integration)
- Must avoid nullable keys in primary/unique keys (data quality best practice)
- Must align with 2×2 model where actuals and projections are distinct axes
- Must enable joins between actuals and projections for variance analysis
- Must support incremental loading with different cadences (actuals: weekly; projections: weekly or pre-season)

## Decision

Implement **separate fact tables** for actuals and projections:

1. **`fact_player_stats`** - Per-game actuals from nflverse

   - Grain: one row per player per game per stat
   - Required columns: `player_id`, `game_id`, `season`, `week`, `stat_name`
   - `stat_kind='actual'`, `measure_domain='real_world'`
   - No `horizon` column needed

1. **`fact_player_projections`** - Weekly/season-long projections from FFanalytics

   - Grain: one row per player per stat per horizon per asof_date
   - Required columns: `player_id`, `season`, `week` (nullable for season-long), `horizon`, `stat_name`, `asof_date`
   - `stat_kind='projection'`, `measure_domain='real_world'`
   - Includes `horizon` column: 'weekly', 'rest_of_season', 'full_season'
   - No `game_id` (projections are not game-specific)

### Architecture

```
2×2 Model Implementation:

                 Real-World Stats              Fantasy Points
                 ----------------              --------------
Actuals          fact_player_stats        →    mart_fantasy_actuals_weekly
                 (per-game grain)              (apply scoring rules)

Projections      fact_player_projections  →    mart_fantasy_projections
                 (weekly/season grain)         (apply scoring rules)
```

**Key principle:** Base facts store **real-world measures only**. Fantasy scoring is derived in marts via `dim_scoring_rule` seeds.

### Integration Pattern

Marts join actuals to projections on `(player_id, season, week)` for variance analysis:

```sql
-- Variance analysis
SELECT
  a.player_id, a.season, a.week,
  a.rushing_yards AS actual_rushing_yards,
  p.rushing_yards AS projected_rushing_yards,
  a.rushing_yards - p.rushing_yards AS variance
FROM mart_real_world_actuals_weekly a
JOIN mart_real_world_projections p
  ON a.player_id = p.player_id
  AND a.season = p.season
  AND a.week = p.week
  AND p.horizon = 'weekly'
```

## Consequences

### Positive

- **Clean grain semantics**: Each fact has a single, well-defined grain (per-game vs weekly/season)
- **No nullable keys**: Both facts have fully-populated primary/unique keys
- **Flexible incremental logic**: Each fact can have independent incremental strategies
- **Clear 2×2 alignment**: Actuals and projections are distinct along the "actual vs projected" axis
- **Time-travel queries**: `asof_date` in projections enables "what were projections as of week 3?" analysis
- **Horizon flexibility**: Supports multiple projection timeframes without schema changes
- **Maintainability**: Separate concerns make each fact simpler to understand and maintain

### Negative

- **Two facts instead of one**: Slightly more complex overall schema
- **Join required for comparison**: Actuals vs projections requires mart-level join
- **Separate tests**: Each fact needs its own data quality tests
- **Separate incremental logic**: Two sets of incremental configurations to manage

### Neutral

- **Storage overhead**: Similar total storage (one wide table vs two narrower tables)
- **Query patterns**: Some queries simpler (single fact), some more complex (joined)
- **Grain documentation**: Must clearly document grain differences in schema docs

## Alternatives Considered

### 1. Unified Fact with Nullable `game_id` and `horizon`

```sql
fact_player_stats(
  player_id,
  season,
  week,
  game_id,         -- nullable for projections
  horizon,         -- nullable for actuals
  stat_kind,       -- 'actual' or 'projection'
  ...
)
```

**Rejected because:**

- Nullable `game_id` in primary key violates data quality best practices
- Complex unique key: `[player_id, season, week, game_id, horizon, stat_name, ...]`
- Ambiguous grain: "sometimes per-game, sometimes weekly"
- Conditional logic required throughout: "if stat_kind='actual' then ignore horizon"

### 2. Weekly Aggregate Only (Force Projections to Weekly)

```sql
-- No season-long projections; convert all to weekly first
fact_player_stats(
  player_id, season, week,
  game_id,     -- nullable for projections
  stat_kind,
  ...
)
```

**Rejected because:**

- Loses season-long projection granularity (important for pre-season analysis)
- Still requires nullable `game_id`
- Forces artificial weekly breakdown of season-long projections (adds complexity upstream)

### 3. Separate Projection Horizon Facts

```sql
fact_player_stats              -- actuals
fact_player_projections_weekly -- weekly projections
fact_player_projections_season -- season projections
```

**Rejected because:**

- Overly granular (3+ facts for 1 logical entity)
- Difficult to query across horizon types
- Union queries required for complete projection picture

## Implementation Notes

### Unique Keys

- `fact_player_stats`: `[player_id, game_id, stat_name, provider, stat_kind, measure_domain]`
- `fact_player_projections`: `[player_id, season, week, horizon, stat_name, provider, measure_domain, asof_date]`

### Partitioning

- `fact_player_stats`: `partition_by=['season', 'week']`
- `fact_player_projections`: `partition_by=['season']` (incremental on `asof_date`)

### Incremental Logic

- Actuals: Incremental on `(max_season, max_week)` - weekly append
- Projections: Incremental on `max(asof_date)` - append each projection run

### Key Files

- `dbt/ff_analytics/models/core/fact_player_stats.sql` - Per-game actuals
- `dbt/ff_analytics/models/core/fact_player_projections.sql` - Weekly/season projections
- `dbt/ff_analytics/models/marts/mart_projection_variance.sql` - Variance analysis

## References

- **SPEC-1 v2.2**: Section "2×2 Stat Model" - [`docs/spec/SPEC-1_v_2.2.md`](../spec/SPEC-1_v_2.2.md)
- **Refined Data Model Plan v4.0**: Main plan and v4.1 addendum - [`docs/spec/refined_data_model_plan_v4.md`](../spec/refined_data_model_plan_v4.md)
- **Implementation Checklist**: Section 6 (FFanalytics) and Section 7 (dbt) - [`docs/spec/SPEC-1_v_2.2_implementation_checklist_v_1.md`](../spec/SPEC-1_v_2.2_implementation_checklist_v_1.md)
- **Kimball Modeling Guidance**: Fact table design patterns - [`docs/architecture/kimball_modeling_guidance/kimbal_modeling.md`](../architecture/kimball_modeling_guidance/kimbal_modeling.md)

## Decision Record

This decision was made during data model v4 review on 2025-09-29 when evaluating how to integrate FFanalytics projections. The separate fact table approach was approved as v4.1 addendum to the refined data model plan, maintaining v4.0's per-game actuals grain while adding proper projection support.

**Approval:** Documented in `refined_data_model_plan_v4.md` as Addendum v4.1 - Projections Integration.

**Implementation Status:** Phase 1 (seeds) required before implementation. Part of Phase 2, Track D (Projections parallel track).
