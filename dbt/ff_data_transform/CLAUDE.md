# dbt Project Context

**Location**: `dbt/ff_data_transform/`
**Purpose**: DuckDB + external Parquet dimensional models following Kimball patterns

## Configuration

**IMPORTANT**: `profiles.yml` is in `.gitignore` - you cannot see it with `ls` or `find`, but it exists at `dbt/ff_data_transform/profiles.yml`.

**Profile Configuration** (`profiles.yml`):

- **Profile name**: `ff_duckdb`
- **Target**: `local` (default) or `ci`
- **Database path**: `$PWD/dbt/ff_data_transform/target/dev.duckdb` (via `DBT_DUCKDB_PATH` env var)
- **External data root**: `$PWD/data/raw` (via `EXTERNAL_ROOT` env var)
- **Schema**: `main`
- **Extensions**: `[httpfs]`

**Environment Variables** (set by Makefile or manually):

- `EXTERNAL_ROOT` - Path to raw data (e.g., `$PWD/data/raw`)
- `DBT_DUCKDB_PATH` - Path to DuckDB database file (e.g., `$PWD/dbt/ff_data_transform/target/dev.duckdb`)
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
# NOTE: No UV_CACHE_DIR needed - uv uses ~/.cache/uv by default (shared across projects)
uv run env \
    EXTERNAL_ROOT="$(pwd)/data/raw" \
    DBT_DUCKDB_PATH="$(pwd)/dbt/ff_data_transform/target/dev.duckdb" \
    dbt run --project-dir dbt/ff_data_transform --profiles-dir dbt/ff_data_transform

# IMPORTANT: When running dbt commands in Bash tool, use $(pwd) NOT $PWD
# $PWD doesn't expand correctly in the Bash tool environment, causing "/.uv-cache" errors

# Query database directly with DuckDB CLI (from repo root)
duckdb dbt/ff_data_transform/target/dev.duckdb
# Within DuckDB: SELECT * FROM main.mrt_contract_snapshot_current LIMIT 10;

# Run compiled dbt analysis SQL (from repo root)
EXTERNAL_ROOT="$(pwd)/data/raw" \
  dbt compile --select <analysis_name> --project-dir dbt/ff_data_transform --profiles-dir dbt/ff_data_transform
duckdb dbt/ff_data_transform/target/dev.duckdb < dbt/ff_data_transform/target/compiled/ff_data_transform/analyses/<analysis_name>.sql
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
# models/core/schema.yml (fct_player_stats)
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

### SELECT * Policy

**CRITICAL for dbt-opiner O007 compliance**: Using `SELECT *` in the final SELECT statement breaks YAML column validation.

**Rule**:

- ✅ **In CTEs**: `SELECT *` is acceptable for readability
- ❌ **In final SELECT**: MUST use explicit columns

**Why?**
dbt-opiner validates that YAML column documentation matches the actual SQL output. When you use `SELECT *` in the final statement:

1. Linter cannot determine which columns are in the output
2. Upstream schema changes silently break YAML documentation
3. Creates maintenance burden when debugging O007 violations

**Good Example**:

```sql
with real_world as (
    select * from {{ ref('mrt_real_world_actuals_weekly') }}  -- OK in CTE
),

scoring as (
    select * from {{ ref('dim_scoring_rule') }}  -- OK in CTE
)

-- Final SELECT: Explicit columns (dbt-opiner can validate)
select
    rw.player_id,
    rw.season,
    rw.week,
    rw.passing_yards,
    rw.rushing_yards,
    rw.receiving_yards,
    s.fantasy_points
from real_world rw
cross join scoring s
```

**Bad Example**:

```sql
with real_world as (
    select * from {{ ref('mrt_real_world_actuals_weekly') }}
)

-- BAD: SELECT * in final output
select rw.*,  -- ❌ Fails O007 validation
    fantasy_points
from real_world rw
```

**If you must use `SELECT *`**:

- Document EVERY column from the upstream model in your YAML
- When upstream schema changes, update your YAML immediately
- Consider using explicit columns instead for better maintainability

### 2×2 Stat Model (ADR-007)

The project implements a **2×2 model** for player performance data:

```text
                 Real-World Stats              Fantasy Points
                 ────────────────              ──────────────
Actuals          fct_player_stats        →    mrt_fantasy_actuals_weekly
                 (per-game grain)              (apply dim_scoring_rule)

Projections      fct_player_projections  →    mrt_fantasy_projections
                 (weekly/season grain)         (apply dim_scoring_rule)
```

**Key Decision (ADR-007)**: Actuals and projections use **separate fact tables** because:

- Actuals have per-game grain with `game_id` (required for NFL analysis)
- Projections have weekly/season grain with `horizon` (no meaningful game_id)
- Unified table would require nullable keys (anti-pattern)

**Fact Tables**:

- `fct_player_stats` - Per-game actuals (nflverse): 88 stat types, 6.3M rows
- `fct_player_projections` - Weekly/season projections (ffanalytics): 13 stat types

**Analytics Marts**:

- Real-world: `mrt_real_world_actuals_weekly`, `mrt_real_world_projections`
- Fantasy: `mrt_fantasy_actuals_weekly`, `mrt_fantasy_projections`
- Variance: `mrt_projection_variance` (actuals vs projections)

### External Parquet

```yaml
{{ config(
    materialized='table',
    external=true,
    partition_by=['season', 'week']
) }}
```

All large models use external Parquet. DuckDB catalog is in-memory only.

### SQL Style & Linting Strategy

This project uses a **multi-tool approach** for SQL quality:

1. **sqlfmt** (formatting) - Formats all SQL files for consistent indentation/spacing

   - Handles DuckDB syntax correctly (polyglot mode)
   - Fast and opinionated (minimal configuration)
   - Uses 4-space indentation (default, non-configurable)
   - Run: `make sqlfmt` (format) or `make sqlfmt-check` (check only)

2. **SQLFluff** (selective linting) - Style/quality checks on standard SQL models

   - Configuration: `.sqlfluff`, `pyproject.toml`, and `.sqlfluffignore`
   - Uses 4-space indentation (configured to match sqlfmt)
   - Excludes files with DuckDB-specific syntax that SQLFluff cannot parse (via `.sqlfluffignore`)
   - Excluded patterns:
     - Staging models (`stg_*.sql`) - use `read_parquet()` with named parameters
     - Core models with DuckDB functions (`dim_player_contract_history.sql`, `fct_league_transactions.sql`, `int_pick_*.sql`)
     - Mart models with DuckDB functions (`mrt_contract_snapshot_current.sql`, `mrt_real_world_actuals_weekly.sql`)
   - Run: `make sqlcheck` (lint) or `make sqlfix` (auto-fix)

3. **dbt compile** (syntax validation) - Validates SQL syntax using actual DuckDB parser

   - Catches real syntax errors regardless of linting exclusions
   - Uses dbt's compilation process (validates after Jinja templating)
   - Run: `make dbt-compile-check`

4. **dbt-opiner** (dbt best practices) - Enforces dbt project conventions

   - Checks naming, structure, and dbt-specific patterns
   - **Configuration**: `.dbt-opiner.yaml` (optional - uses defaults if not present)
   - **Exclusions**: Test files (`tests/*.sql`) are excluded via pre-commit hook - they're not dbt project nodes
   - Separate from SQL syntax/style concerns
   - Run: `make dbt-opiner-check`
   - **Note**: When using `--all-files`, dbt-opiner will report errors for test files (expected - they're excluded from linting)

**All-in-one**: `make sql-all` runs all four checks in sequence.

**Pre-commit hooks**: All tools run automatically on commit (format → lint → validate → dbt practices).

#### Pre-commit Hook Workflow

When you commit SQL/YAML changes, hooks run in this **specific order**:

1. **sqlfmt** - Formats SQL (auto-fixes, modifies files)
2. **sqlfluff-lint** - Style checks (fails on violations)
3. **dbt-compile** - Syntax validation (fails on SQL errors)
4. **dbt-opiner** - Best practices (fails on O001-O007 violations)

**If pre-commit fails**:

1. Check the specific hook that failed in the error output
2. Fix the reported issue (see "Common Pitfalls" section below)
3. Stage the changes: `git add .`
4. Retry the commit

**Run manually before committing** (recommended):

```bash
make sql-all  # Runs all 4 checks at once - faster than waiting for pre-commit
```

**Emergency override** (NOT recommended - use sparingly):

```bash
git commit --no-verify  # Skips ALL pre-commit hooks
```

**Tip**: Hooks only run on files you've changed, so commits are usually fast. For full validation, use `pre-commit run --all-files`.

**Why multiple tools?**

- SQLFluff's DuckDB dialect has incomplete support for DuckDB-specific syntax
- sqlfmt handles formatting correctly for all DuckDB syntax
- dbt compile provides authoritative syntax validation
- dbt-opiner focuses on dbt project structure (not SQL syntax)

### Excluded Files Reference

**SQLFluff Exclusions** (via `.sqlfluffignore` file):

- **Staging models** (`stg_*.sql`): Use `read_parquet()` with named parameters
- **Core models**: `dim_player_contract_history.sql` (list functions), `fct_league_transactions.sql` (interval arithmetic), `int_pick_*.sql` (regexp/date functions)
- **Mart models**: `mrt_contract_snapshot_current.sql` (JSON/unnest), `mrt_real_world_actuals_weekly.sql` (arbitrary)
- **Test files**: `tests/*.sql` (not dbt project nodes)

**dbt-opiner Exclusions** (via pre-commit hook):

- **Test files**: `tests/*.sql` (not dbt project nodes in manifest)

**Note**: Excluded files are still validated via `dbt compile` and `dbt test`. Only style linting is excluded.

## Creating a New Model: Step-by-Step Checklist

Follow this checklist when creating any new dbt model to ensure dbt-opiner compliance.

### Before You Write SQL

- [ ] **Identify the grain**: One row per \_\_\_?
- [ ] **Determine materialization**: table, view, or incremental?
- [ ] **Check upstream dependencies**: Do required models exist?
- [ ] **Choose unique_key**: Single column or composite key?

### SQL File (`models/<layer>/<model_name>.sql`)

```sql
{{ config(
    materialized='table',
    unique_key='player_id',  -- REQUIRED for dbt-opiner O005
    external=true,
    partition_by=['season', 'week']
) }}

/*
Model description: One row per [grain]. [Purpose].

Grain: [Detailed grain explanation]
Source: [Upstream models or sources]
*/

-- Use CTEs for readability
with base as (
    select * from {{ ref('upstream_model') }}  -- SELECT * OK in CTEs
),

transformed as (
    select
        col1,
        col2,
        -- calculations
    from base
)

-- FINAL SELECT: Must use explicit columns (not SELECT *)
select
    player_id,        -- List all columns explicitly
    season,
    week,
    fantasy_points
from transformed
```

**Key Requirements**:

- [ ] Add config block with `materialized` and `unique_key`
- [ ] Include descriptive header comment with grain
- [ ] Use **explicit columns in final SELECT** (not `SELECT *`)
- [ ] Format with sqlfmt (runs automatically via pre-commit)

### YAML File (`models/<layer>/_<model_name>.yml`)

Create `_<model_name>.yml` in the same directory:

```yaml
version: 2

models:
  - name: <model_name>
    description: |
      [One sentence grain statement]. [Purpose and key logic].

      Grain: One row per [detailed grain]
      Source: [Upstream models]
    config:
      unique_key: player_id  # Must match SQL config
    columns:
      - name: player_id
        description: Canonical player identifier
        data_tests:
          - not_null
          - unique

      - name: season
        description: NFL season year
        data_tests:
          - not_null

      # Document ALL columns, even calculated ones

    data_tests:
      - dbt_utils.unique_combination_of_columns:
          arguments:
            combination_of_columns:
              - player_id
              - season
          config:
            severity: error
```

**Key Requirements**:

- [ ] File named `_<model_name>.yml` (underscore prefix)
- [ ] Model description with grain declaration
- [ ] `unique_key` in config block (must match SQL)
- [ ] **All columns documented** (dbt-opiner O003)
- [ ] Grain uniqueness test
- [ ] FK relationship tests for foreign keys
- [ ] `not_null` tests on key columns
- [ ] Use `data_tests:` and `arguments:` (dbt 1.10+ syntax)

### Validation Workflow

Run these commands **in order** before committing:

```bash
# 1. Compile (validates Jinja and SQL syntax)
make dbt-run --select <model_name>

# 2. Test (validates data quality)
make dbt-test --select <model_name>

# 3. Check best practices (runs all quality checks)
make sql-all
```

**Pre-commit hooks will automatically run**:

1. sqlfmt (formats SQL)
2. sqlfluff-lint (style checks)
3. dbt-compile (syntax validation)
4. dbt-opiner (best practices validation)

If pre-commit fails, fix the reported issues and retry the commit.

### Common Validation Errors

| Error                           | Fix                                    |
| ------------------------------- | -------------------------------------- |
| O001: Model has no description  | Add `description:` to YAML             |
| O003: Column has no description | Document all columns in YAML           |
| O005: Missing unique_key        | Add to both SQL config and YAML config |
| O007: Column in YAML not in SQL | Use explicit columns in final SELECT   |

## Common Tasks

**Add new source**:

1. Define in `sources/src_<provider>.yml`
2. Create staging model `staging/stg_<provider>__<dataset>.sql`
3. Add tests to YAML file
4. Reference in downstream models

**Add conformed dimension**:

1. Create seed or base table
2. Model in `core/dim_<entity>.sql`
3. Add unique key test
4. Document grain and keys

**Add fact table**:

1. Model in `core/fact_<process>.sql`
2. Declare grain in docstring
3. Add grain uniqueness test
4. Add foreign key relationship tests

**Add analytics mart** (2×2 model pattern):

1. For real-world stats: Pivot fact table from long to wide format
2. For fantasy scoring: Join real-world mart with `dim_scoring_rule` and calculate points
3. For projections: Include `horizon` column ('weekly', 'full_season', 'rest_of_season')
4. Document grain and test uniqueness
5. Examples: `mrt_real_world_projections.sql`, `mrt_fantasy_actuals_weekly.sql`

## Testing Strategy

| Test Type                                 | Purpose                 | Location      |
| ----------------------------------------- | ----------------------- | ------------- |
| `not_null`                                | Key fields populated    | Column level  |
| `unique`                                  | Surrogate keys unique   | Dimension PKs |
| `relationships`                           | Foreign keys valid      | Fact FKs      |
| `dbt_utils.unique_combination_of_columns` | Grain enforcement       | Fact grain    |
| `accepted_values`                         | Controlled vocabularies | Enums, flags  |
| `freshness`                               | Data recency            | Source level  |

**Known Issue**: dbt 1.10 has a [false positive bug](https://github.com/dbt-labs/dbt-fusion/issues/507) that incorrectly flags `dbt_utils.unique_combination_of_columns` tests as missing `arguments:` even when syntax is correct. These deprecation warnings can be safely ignored until dbt patches the bug.

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

## Common Pitfalls and How to Avoid Them

This section covers common dbt-opiner violations (O001-O007) and how to fix them.

### O001: Missing Model Description

**Symptom**: `Model <model_name> must have a description`

**Cause**: YAML file missing or has no `description:` field

**Fix**:

```yaml
models:
  - name: <model_name>
    description: |
      One row per [grain]. [Purpose statement].

      Grain: [Detailed grain explanation]
      Source: [Upstream dependencies]
```

**Template**: "[Grain statement]. [Purpose]."

______________________________________________________________________

### O003: Missing Column Descriptions

**Symptom**: `Column(s): ['col1', 'col2'] in model <model_name> must have a description`

**Cause**: Columns exist in SQL but not documented in YAML

**Fix**: Document ALL columns in YAML, even calculated/derived columns

```yaml
columns:
  - name: fantasy_points
    description: Total fantasy points calculated from scoring rules
  - name: player_id
    description: Canonical player identifier from dim_player
```

**Tips**:

- Copy column list from upstream model and adjust
- Use meaningful descriptions (WHY, not just WHAT)
- Include calculation logic for derived columns

______________________________________________________________________

### O005: Missing unique_key

**Symptom**: `Model should have a unique key defined in the config block`

**Cause**: Materialized table without `unique_key` declaration

**Fix**: Add to BOTH SQL config AND YAML config

```sql
-- In SQL file
{{ config(
    materialized='table',
    unique_key='player_id'  -- Single column
) }}

-- OR for composite key:
{{ config(
    materialized='table',
    unique_key=['player_id', 'season', 'week']  -- Array for composite
) }}
```

```yaml
# In YAML file
models:
  - name: <model_name>
    config:
      unique_key: player_id  # Must match SQL config
```

**Note**: Views don't need unique_key, only materialized tables

______________________________________________________________________

### O006: Model Naming Convention

**Symptom**: `Model must start with a prefix that specifies the layer`

**Standard Prefixes**:

- `stg_<provider>__<dataset>` - Staging models (from sources)
- `fct_<name>` - Fact tables (NOT `fact_*`)
- `dim_<name>` - Dimensions
- `mrt_<name>` - Analytics marts (NOT `mart_*`)
- `int_<name>` - Intermediate models

**Fix**: Rename the model file and update all `{{ ref() }}` calls

**IMPORTANT**: This is a breaking change! Before renaming:

1. Search for all refs: `grep -r "ref('old_name')" models/`
2. Update all references in downstream models
3. Update tests and documentation
4. Commit in a dedicated commit for easy rollback

______________________________________________________________________

### O007: YAML/SQL Column Mismatch

**Symptom**: `Unnecessary column(s) defined in YAML: {'col1', 'col2'}`

**Cause**: Columns documented in YAML but not in final SQL SELECT

**Common Causes**:

1. **Using `SELECT *` in final statement** (most common)
2. Renamed columns in SQL but not updated in YAML
3. Removed columns from SQL but forgot to update YAML

**Fix Option 1** (Recommended): Use explicit columns in final SELECT

```sql
-- BAD
select rw.*, fantasy_points from real_world rw

-- GOOD
select
    rw.player_id,
    rw.season,
    rw.week,
    fantasy_points
from real_world rw
```

**Fix Option 2**: Remove columns from YAML that don't exist in SQL

**Prevention**: Always use explicit columns in the final SELECT statement (see SELECT * Policy above)

______________________________________________________________________

### Pre-commit Hook Failures

**Symptom**: Commit rejected with hook errors

**Hooks run in this order**:

1. **sqlfmt** - SQL formatting (auto-fixes)
2. **sqlfluff-lint** - Style checks
3. **dbt-compile** - Syntax validation
4. **dbt-opiner** - Best practices validation

**What to do**:

1. Read the specific hook error message
2. Fix the issue (see violation guides above)
3. Stage changes: `git add .`
4. Retry commit

**Run manually before committing**:

```bash
make sql-all  # Runs all 4 checks at once
```

**Emergency only** (NOT recommended):

```bash
git commit --no-verify  # Skips ALL hooks
```

______________________________________________________________________

### Debugging Tips

**Check which files are affected**:

```bash
make dbt-opiner-check  # Shows all violations
```

**Validate a specific model**:

```bash
make dbt-run --select <model_name>
make dbt-test --select <model_name>
```

**Common workflow**:

1. Make changes to SQL/YAML
2. Run `make sql-all` to check everything
3. Fix any violations
4. Commit (pre-commit will validate again)

## References

- **Kimball guide**: `../../docs/architecture/kimball_modeling_guidance/kimbal_modeling.md`
- **Repo conventions**: `../../docs/dev/repo_conventions_and_structure.md`
- **SPEC**: `../../docs/spec/SPEC-1_v_2.2.md`
- **Implementation checklist**: `../../docs/spec/SPEC-1_v_2.3_implementation_checklist_v_0.md`
- **ADR-007**: `../../docs/adr/ADR-007-separate-fact-tables-actuals-vs-projections.md` (2×2 model rationale)
