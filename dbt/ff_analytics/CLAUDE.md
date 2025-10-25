# dbt Project Context

**Location**: `dbt/ff_analytics/`
**Purpose**: DuckDB + external Parquet dimensional models following Kimball patterns

## Quick Commands

```bash
# From repo root
make dbt-run    # dbt run --project-dir dbt/ff_analytics --profiles-dir dbt/ff_analytics
make dbt-test   # dbt test --project-dir dbt/ff_analytics --profiles-dir dbt/ff_analytics
make sqlfix     # Auto-fix SQL style issues

# From this directory
dbt run --profiles-dir .
dbt test --profiles-dir .
```

## Model Organization

Each subdirectory has a README.md with specific guidance:

| Directory  | Purpose                     | Naming Pattern                  |
| ---------- | --------------------------- | ------------------------------- |
| `sources/` | Provider source definitions | `src_<provider>.yml`            |
| `staging/` | Normalized from raw         | `stg_<provider>__<dataset>.sql` |
| `core/`    | Facts/dimensions (Kimball)  | `fact_*`, `dim_*`               |
| `marts/`   | Analytics-ready marts       | `mart_*` (2×2 model)            |
| `markets/` | KTC trade values (stub)     | Market-specific marts           |
| `ops/`     | Data quality/lineage        | `ops.*` tables                  |
| `seeds/`   | Reference data              | `dim_*` crosswalks, rules       |
| `macros/`  | Reusable SQL functions      | Freshness gates, helpers        |

## Key Patterns

### Grain Declaration

**CRITICAL**: Every fact table MUST explicitly declare and test its grain.

```yaml
# models/core/schema.yml (fact_player_stats)
tests:
  - dbt_utils.unique_combination_of_columns:
      combination_of_columns:
        - player_key  # Composite identifier (not player_id!)
        - game_id
        - stat_name
        - provider
        - measure_domain
        - stat_kind
      config:
        severity: error
        error_if: ">0"
        where: "position IN ('QB', 'RB', 'WR', 'TE', 'K', 'FB')"  # Fantasy-relevant only
```

**Why player_key instead of player_id?**
- Multiple unmapped players in same game would all have `player_id = -1`
- `player_key` uses raw provider IDs as fallback to preserve identity
- See `models/staging/README.md` for player identity resolution pattern

### Conformed Dimensions

- Reference `{{ ref('dim_player') }}` everywhere
- NEVER duplicate dimension logic
- Use crosswalk seeds (`dim_player_id_xref`) for identity resolution

### 2×2 Stat Model (ADR-007)

The project implements a **2×2 model** for player performance data:

```
                 Real-World Stats              Fantasy Points
                 ────────────────              ──────────────
Actuals          fact_player_stats        →    mart_fantasy_actuals_weekly
                 (per-game grain)              (apply dim_scoring_rule)

Projections      fact_player_projections  →    mart_fantasy_projections
                 (weekly/season grain)         (apply dim_scoring_rule)
```

**Key Decision (ADR-007)**: Actuals and projections use **separate fact tables** because:
- Actuals have per-game grain with `game_id` (required for NFL analysis)
- Projections have weekly/season grain with `horizon` (no meaningful game_id)
- Unified table would require nullable keys (anti-pattern)

**Fact Tables**:
- `fact_player_stats` - Per-game actuals (nflverse): 88 stat types, 6.3M rows
- `fact_player_projections` - Weekly/season projections (ffanalytics): 13 stat types

**Analytics Marts**:
- Real-world: `mart_real_world_actuals_weekly`, `mart_real_world_projections`
- Fantasy: `mart_fantasy_actuals_weekly`, `mart_fantasy_projections`
- Variance: `mart_projection_variance` (actuals vs projections)

### External Parquet

```yaml
{{ config(
    materialized='table',
    external=true,
    partition_by=['season', 'week']
) }}
```

All large models use external Parquet. DuckDB catalog is in-memory only.

### SQL Style

- **Staging models**: Allow raw provider column names (ignore `RF04`, `CV06`)
- **Core/marts**: Enforce strict style (lowercase, terminators)
- **Manual fix**: `make sqlfix` runs SQLFluff auto-fix

## Common Tasks

**Add new source**:

1. Define in `sources/src_<provider>.yml`
1. Create staging model `staging/stg_<provider>__<dataset>.sql`
1. Add tests to YAML file
1. Reference in downstream models

**Add conformed dimension**:

1. Create seed or base table
1. Model in `core/dim_<entity>.sql`
1. Add unique key test
1. Document grain and keys

**Add fact table**:

1. Model in `core/fact_<process>.sql`
1. Declare grain in docstring
1. Add grain uniqueness test
1. Add foreign key relationship tests

**Add analytics mart** (2×2 model pattern):

1. For real-world stats: Pivot fact table from long to wide format
1. For fantasy scoring: Join real-world mart with `dim_scoring_rule` and calculate points
1. For projections: Include `horizon` column ('weekly', 'full_season', 'rest_of_season')
1. Document grain and test uniqueness
1. Examples: `mart_real_world_projections.sql`, `mart_fantasy_actuals_weekly.sql`

## Testing Strategy

| Test Type                                 | Purpose                 | Location      |
| ----------------------------------------- | ----------------------- | ------------- |
| `not_null`                                | Key fields populated    | Column level  |
| `unique`                                  | Surrogate keys unique   | Dimension PKs |
| `relationships`                           | Foreign keys valid      | Fact FKs      |
| `dbt_utils.unique_combination_of_columns` | Grain enforcement       | Fact grain    |
| `accepted_values`                         | Controlled vocabularies | Enums, flags  |
| `freshness`                               | Data recency            | Source level  |

## References

- **Kimball guide**: `../../docs/architecture/kimball_modeling_guidance/kimbal_modeling.md`
- **Repo conventions**: `../../docs/dev/repo_conventions_and_structure.md`
- **SPEC**: `../../docs/spec/SPEC-1_v_2.2.md`
- **Implementation checklist**: `../../docs/spec/SPEC-1_v_2.3_implementation_checklist_v_0.md`
- **ADR-007**: `../../docs/adr/ADR-007-separate-fact-tables-actuals-vs-projections.md` (2×2 model rationale)
