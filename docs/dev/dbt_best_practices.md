# dbt Best Practices Guide

## Overview

This project enforces dbt best practices using **dbt-opiner**, a linter that validates dbt projects against common conventions and patterns. All models must comply with these standards before merge.

**Automated Enforcement**: dbt-opiner runs automatically as a pre-commit hook on every commit.

**Manual Check**: `make dbt-opiner-check`

## The Five Key Rules (O001-O007)

dbt-opiner enforces five categories of rules. Understanding these rules helps you write compliant models from the start.

______________________________________________________________________

### O001: Model Descriptions

**Rule**: Every model must have a description in its YAML file.

**Purpose**: Ensures all models are documented with their purpose and grain.

**Format**: "[Grain statement]. [Purpose]."

**Example**:

```yaml
models:
  - name: mrt_fantasy_actuals_weekly
    description: |
      Fantasy actuals mart - weekly player performance with fantasy scoring applied.

      Grain: One row per player per season per week
      Source: mrt_real_world_actuals_weekly (with scoring rules applied)
```

**Quick Fix**:

1. Open or create `_<model_name>.yml` in same directory as SQL file
2. Add `description:` field with grain and purpose
3. Template: "One row per [grain]. [Purpose]."

______________________________________________________________________

### O003: Column Descriptions

**Rule**: Every column must have a description in the YAML file.

**Purpose**: Ensures all columns are documented, making the data model self-documenting.

**Example**:

```yaml
columns:
  - name: fantasy_points
    description: Total fantasy points calculated from real-world stats using league scoring rules
    data_tests:
      - not_null
  - name: player_id
    description: Canonical player identifier from dim_player (FK)
    data_tests:
      - not_null
      - relationships:
          arguments:
            to: ref('dim_player')
            field: player_id
```

**Tips**:

- Document WHY, not just WHAT: "Player identifier" → "Canonical player identifier for grain uniqueness"
- Include calculation logic for derived columns
- Copy from upstream models and adjust as needed
- ALL columns must be documented, even obvious ones

______________________________________________________________________

### O005: unique_key Declaration

**Rule**: All materialized tables must declare a `unique_key` in config.

**Purpose**: Declares the grain explicitly, enabling incremental models and data quality validation.

**Example**:

```sql
-- Single column unique key
{{ config(
    materialized='table',
    unique_key='player_id'
) }}
```

```sql
-- Composite unique key (most common for facts)
{{ config(
    materialized='table',
    unique_key=['player_id', 'season', 'week']
) }}
```

**YAML config must match**:

```yaml
models:
  - name: mrt_fantasy_actuals_weekly
    config:
      unique_key: ['player_id', 'season', 'week']
```

**Notes**:

- Views don't need `unique_key` (only materialized tables)
- Should match your grain uniqueness test
- Use array syntax for composite keys

______________________________________________________________________

### O006: Naming Conventions

**Rule**: Models must use standard prefixes that indicate their layer.

**Standard Prefixes**:

- `stg_<provider>__<dataset>` - Staging models (from sources)
- `fct_<name>` - Fact tables (**NOT** `fact_*`)
- `dim_<name>` - Dimension tables
- `mrt_<name>` - Analytics marts (**NOT** `mart_*`)
- `int_<name>` - Intermediate models

**Example**:

```text
✅ CORRECT:
- stg_nflverse__player_stats
- fct_player_stats
- dim_player
- mrt_fantasy_actuals_weekly
- int_pick_base

❌ WRONG:
- player_stats_staging
- fact_player_stats
- mart_fantasy_actuals_weekly
```

**Fixing**:

Renaming models is a breaking change. Follow this process:

1. Search for all references: `grep -r "ref('old_name')" models/`
2. Rename SQL file: `git mv old_name.sql new_name.sql`
3. Rename YAML file: `git mv _old_name.yml _new_name.yml`
4. Update model name in YAML: `- name: new_name`
5. Update all downstream `{{ ref() }}` calls
6. Update any notebook/test references
7. Commit with descriptive message: `refactor: rename old_name to new_name (O006)`

______________________________________________________________________

### O007: YAML/SQL Column Alignment

**Rule**: Columns documented in YAML must exist in the final SQL SELECT output.

**Purpose**: Ensures documentation stays synchronized with actual SQL output.

**Common Cause**: Using `SELECT *` in the final SELECT statement.

**Fix**: Use explicit columns in final SELECT:

```sql
-- ❌ BAD - causes O007 violations
with base as (
    select * from {{ ref('upstream') }}
)
select base.*, calculated_col from base

-- ✅ GOOD - explicit columns
with base as (
    select * from {{ ref('upstream') }}  -- OK in CTEs
)
select
    player_id,
    season,
    week,
    fantasy_points,
    calculated_col
from base
```

**Why explicit columns?**

1. dbt-opiner can validate YAML matches SQL
2. Upstream schema changes don't silently break documentation
3. Makes dependencies explicit and reviewable
4. Easier to debug column issues

**SELECT * Policy**:

- ✅ Acceptable in CTEs (for readability)
- ❌ Not allowed in final SELECT statement

______________________________________________________________________

## Model Creation Workflow

Follow this workflow to create compliant models from the start:

### 1. Before Writing SQL

- [ ] Identify the grain: "One row per \_\_\_?"
- [ ] Determine materialization (table/view)
- [ ] Identify upstream dependencies
- [ ] Choose unique_key (single column or composite)

### 2. Write SQL File

Create `models/<layer>/<model_name>.sql`:

```sql
{{ config(
    materialized='table',
    unique_key=['player_id', 'season', 'week'],  -- O005 requirement
    external=true,
    partition_by=['season', 'week']
) }}

/*
Model description: One row per player per season per week.

Grain: player_id + season + week
Source: mrt_real_world_actuals_weekly + dim_scoring_rule
*/

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

-- Final SELECT: explicit columns (O007 requirement)
select
    player_id,
    season,
    week,
    fantasy_points
from transformed
```

**Key Requirements**:

- Config block with `unique_key`
- Header comment with grain
- Explicit columns in final SELECT (not `SELECT *`)

### 3. Write YAML File

Create `models/<layer>/_<model_name>.yml` (note underscore prefix):

```yaml
version: 2

models:
  - name: <model_name>
    description: |
      One row per [grain]. [Purpose and key logic].

      Grain: [Detailed grain explanation]
      Source: [Upstream models]

    config:
      unique_key: ['player_id', 'season', 'week']  # Must match SQL

    columns:
      - name: player_id
        description: Canonical player identifier
        data_tests:
          - not_null

      - name: season
        description: NFL season year
        data_tests:
          - not_null

      # Document ALL columns

    data_tests:
      - dbt_utils.unique_combination_of_columns:
          arguments:
            combination_of_columns:
              - player_id
              - season
              - week
          config:
            severity: error
```

**Key Requirements**:

- Model description (O001)
- All columns documented (O003)
- unique_key in config (O005)
- Grain uniqueness test
- FK relationship tests

### 4. Validate

Run checks before committing:

```bash
# Run the model
make dbt-run --select <model_name>

# Test the model
make dbt-test --select <model_name>

# Check all quality standards
make sql-all
```

### 5. Commit

Pre-commit hooks will automatically run:

1. sqlfmt (auto-formats)
2. sqlfluff-lint (style checks)
3. dbt-compile (syntax validation)
4. dbt-opiner (best practices)

If hooks fail, fix the issues and retry.

______________________________________________________________________

## Troubleshooting

### "Model has no description" (O001)

**Symptom**: `Model <model_name> must have a description`

**Fix**: Add `description:` to YAML file

### "Column has no description" (O003)

**Symptom**: `Column(s): ['col1'] must have a description`

**Fix**: Document the column in YAML

### "Missing unique_key" (O005)

**Symptom**: `Model should have a unique key defined`

**Fix**: Add to both SQL config and YAML config

### "Wrong model prefix" (O006)

**Symptom**: `Model should use fct_ prefix not fact_`

**Fix**: Rename model file and update all refs

### "Column in YAML not in SQL" (O007)

**Symptom**: `Unnecessary column(s) defined in YAML`

**Fix**: Use explicit columns in final SELECT or remove from YAML

______________________________________________________________________

## Quick Reference

| Rule | Requirement            | Location                 |
| ---- | ---------------------- | ------------------------ |
| O001 | Model description      | YAML `description:`      |
| O003 | Column descriptions    | YAML `columns:`          |
| O005 | unique_key declaration | SQL config + YAML config |
| O006 | Standard model prefix  | File name                |
| O007 | YAML columns match SQL | Final SELECT (explicit)  |

## See Also

- **Main dbt guide**: `dbt/ff_data_transform/CLAUDE.md`
- **Model creation checklist**: `dbt/ff_data_transform/CLAUDE.md#creating-a-new-model`
- **Common pitfalls**: `dbt/ff_data_transform/CLAUDE.md#common-pitfalls`
- **Pre-commit hooks**: `.pre-commit-config.yaml`
- **dbt-opiner config**: `.dbt-opiner.yaml` (uses defaults if not present)
