# dbt Project Context

**Location**: `dbt/ff_analytics/`
**Purpose**: DuckDB + external Parquet dimensional models following Kimball patterns

## Configuration

**IMPORTANT**: `profiles.yml` is in `.gitignore` - you cannot see it with `ls` or `find`, but it exists at `dbt/ff_analytics/profiles.yml`.

**Profile Configuration** (`profiles.yml`):

- **Profile name**: `ff_duckdb`
- **Target**: `local` (default) or `ci`
- **Database path**: `$PWD/dbt/ff_analytics/target/dev.duckdb` (via `DBT_DUCKDB_PATH` env var)
- **External data root**: `$PWD/data/raw` (via `EXTERNAL_ROOT` env var)
- **Schema**: `main`
- **Extensions**: `[httpfs]`

**Environment Variables** (set by Makefile or manually):

- `EXTERNAL_ROOT` - Path to raw data (e.g., `$PWD/data/raw`)
- `DBT_DUCKDB_PATH` - Path to DuckDB database file (e.g., `$PWD/dbt/ff_analytics/target/dev.duckdb`)
- `DBT_TARGET` - Target name (default: `local`)
- `DBT_THREADS` - Thread count (default: 4)
- `DBT_SCHEMA` - Schema name (default: `main`)

## Quick Commands

```bash
# From repo root - use Makefile (handles env vars automatically)
make dbt-run    # dbt run with proper env setup
make dbt-test   # dbt test with proper env setup
make dbt-seed   # dbt seed with proper env setup
make sqlfix     # Auto-fix SQL style issues

# Run manually from repo root without make
mkdir -p .uv-cache
UV_CACHE_DIR="$(pwd)/.uv-cache" uv run env \
    EXTERNAL_ROOT="$(pwd)/data/raw" \
    DBT_DUCKDB_PATH="$(pwd)/dbt/ff_analytics/target/dev.duckdb" \
    dbt run --project-dir dbt/ff_analytics --profiles-dir dbt/ff_analytics

# Query database directly with DuckDB CLI (from repo root)
duckdb dbt/ff_analytics/target/dev.duckdb
# Within DuckDB: SELECT * FROM main.mart_contract_snapshot_current LIMIT 10;

# Run compiled dbt analysis SQL (from repo root)
EXTERNAL_ROOT="$(pwd)/data/raw" \
  dbt compile --select <analysis_name> --project-dir dbt/ff_analytics --profiles-dir dbt/ff_analytics
duckdb dbt/ff_analytics/target/dev.duckdb < dbt/ff_analytics/target/compiled/ff_analytics/analyses/<analysis_name>.sql
```

## Model Organization

Each subdirectory has a README.md with specific guidance:

| Directory | Purpose | Naming Pattern |
| ---------- | --------------------------- | ------------------------------- |
| `sources/` | Provider source definitions | `src_<provider>.yml` |
| `staging/` | Normalized from raw | `stg_<provider>__<dataset>.sql` |
| `core/` | Facts/dimensions (Kimball) | `fact_*`, `dim_*` |
| `marts/` | Analytics-ready marts | `mart_*` (2×2 model) |
| `markets/` | KTC trade values (stub) | Market-specific marts |
| `ops/` | Data quality/lineage | `ops.*` tables |
| `seeds/` | Reference data | `dim_*` crosswalks, rules |
| `macros/` | Reusable SQL functions | Freshness gates, helpers |

### Schema Documentation Pattern

This project follows **per-model YAML documentation** (dbt best practice):

- **One YAML file per model** (or small group of tightly related models)
- **Naming convention**: `_<model_name>.yml`
  - Underscore prefix groups docs with models in file listings
  - Makes it clear it's documentation, not a model
- **Location**: Same directory as the SQL model
- **Example**: `stg_ktc_assets.sql` + `_stg_ktc_assets.yml`

**Benefits**:

1. **Easier navigation** - Documentation lives next to the model SQL
2. **Reduced merge conflicts** - Multiple developers can work on different models
3. **Clearer ownership** - Each model's docs are self-contained
4. **Better code reviews** - Changes to model and its tests in same PR
5. **Scalability** - Works better as projects grow

**When creating new models**:

- ALWAYS create a corresponding `_<model_name>.yml` file
- At minimum, document: description, grain, key tests
- Follow existing YAML files as templates

## Key Patterns

### Grain Declaration

**CRITICAL**: Every fact table MUST explicitly declare and test its grain.

```yaml
# models/core/schema.yml (fact_player_stats)
tests:
  - dbt_utils.unique_combination_of_columns:
      arguments:
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

```text
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

| Test Type | Purpose | Location |
| ----------------------------------------- | ----------------------- | ------------- |
| `not_null` | Key fields populated | Column level |
| `unique` | Surrogate keys unique | Dimension PKs |
| `relationships` | Foreign keys valid | Fact FKs |
| `dbt_utils.unique_combination_of_columns` | Grain enforcement | Fact grain |
| `accepted_values` | Controlled vocabularies | Enums, flags |
| `freshness` | Data recency | Source level |

### Test Syntax (dbt 1.10+)

**IMPORTANT**: Follow these two critical rules to avoid deprecation warnings:

1. **Use `data_tests:` key** (not `tests:`): dbt 1.5+ introduced `data_tests:` to distinguish from `unit_tests:`
2. **Nest test arguments under `arguments:`**: dbt 1.10+ requires this for all generic tests with parameters

**Correct syntax** (use this):

```yaml
# Column-level tests
columns:
  - name: position
    description: "Player position"
    data_tests:  # Use data_tests:, not tests:
      - not_null
      - accepted_values:
          arguments:  # Arguments must be nested
            values: ['QB', 'RB', 'WR', 'TE']

  - name: franchise_id
    description: "FK to dim_franchise"
    data_tests:
      - not_null
      - relationships:
          arguments:
            to: ref('dim_franchise')
            field: franchise_id
          config:  # config: is a sibling to arguments:
            where: "franchise_id is not null"

# Model-level tests
data_tests:  # Use data_tests:, not tests:
  - dbt_utils.unique_combination_of_columns:
      arguments:
        combination_of_columns:
          - player_key
          - game_id
      config:
        severity: error
```

**Deprecated syntax** (don't use):

```yaml
# OLD - Will generate deprecation warnings
columns:
  - name: position
    tests:  # WRONG - should be data_tests:
      - accepted_values:
          values: ['QB', 'RB']  # WRONG - should be under arguments:

tests:  # WRONG - should be data_tests:
  - relationships:
      to: ref('other_model')  # WRONG - should be under arguments:
      field: id
```

**Key points**:

- Always use `data_tests:` for both column-level and model-level tests
- `arguments:` wraps all test parameters (to, field, values, combination_of_columns, etc.)
- `config:` remains a sibling to `arguments:` (not nested inside)
- `not_null` and `unique` tests have no arguments, so just use `- not_null` and `- unique` directly
- Legacy `tests:` key still works but is deprecated; use `data_tests:` for clarity

## References

- **Kimball guide**: `../../docs/architecture/kimball_modeling_guidance/kimbal_modeling.md`
- **Repo conventions**: `../../docs/dev/repo_conventions_and_structure.md`
- **SPEC**: `../../docs/spec/SPEC-1_v_2.2.md`
- **Implementation checklist**: `../../docs/spec/SPEC-1_v_2.3_implementation_checklist_v_0.md`
- **ADR-007**: `../../docs/adr/ADR-007-separate-fact-tables-actuals-vs-projections.md` (2×2 model rationale)
