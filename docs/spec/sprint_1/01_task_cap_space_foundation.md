# Task 1.1: Cap Space Foundation

**Sprint:** Sprint 1 - FASA Optimization & Trade Intelligence
**Phase:** Phase 1 - Critical Path for Wednesday FASA
**Estimated Duration:** 4 hours
**Priority:** CRITICAL (blocks FASA notebook)

______________________________________________________________________

## Objective

Parse cap space data from Commissioner Sheet roster tabs to enable accurate FASA bid planning. The Commissioner Sheet tracks available cap space, dead cap, and traded cap space for each franchise across 5 years (2025-2029).

______________________________________________________________________

## Context

**Why this task matters:**

- FASA bids require knowing exactly how much cap space is available
- Drop decisions require calculating dead cap implications
- Commissioner Sheet is the source of truth for cap space (not calculated values)

**Current state:**

- Commissioner Sheet roster tabs exist (parsed in `.tmp_commissioner_extract/`)
- Row 3 of each GM's tab contains cap space data: Available, Dead, Traded
- Example from Jason's tab:
  ```
  Available Cap Space,,$80,$80,$158,$183,$250
  Dead Cap Space,,$26,$13,$6,$0,$0
  Traded Cap Space,$7,$0,$0,$0,$0
  ```

**Dependencies:**

- ✅ Commissioner Sheet parser exists (`src/ingest/sheets/commissioner_parser.py`)
- ✅ Sheet copy workflow works
- ✅ dbt project structure exists

______________________________________________________________________

## Files to Create/Modify

### 1. Modify: `src/ingest/sheets/commissioner_parser.py`

**Add new function:**

```python
def parse_cap_space(roster_df: pl.DataFrame, gm_name: str) -> pl.DataFrame:
    """
    Parse cap space section from roster tab (row 3).

    Input: Raw roster CSV with row 3 format:
        Available Cap Space,,$80,$80,$158,$183,$250
        Dead Cap Space,,$26,$13,$6,$0,$0
        Traded Cap Space,$7,$0,$0,$0,$0

    Output: Long-form DataFrame
        Columns: gm, season, available_cap_space, dead_cap_space, traded_cap_space
        Rows: One per (gm, season) - typically 5 rows (2025-2029)

    Logic:
        1. Locate row 3 in roster_df (contains "Available Cap Space")
        2. Extract columns _1 through _5 (years 2025-2029)
        3. Parse each of the 3 cap space rows
        4. Unpivot to long form
        5. Add gm column
        6. Return DataFrame
    """
    # Implementation here
```

**Update `parse_commissioner_dir()` to call this function:**

- After parsing roster/contracts/picks, also parse cap space
- Write to `data/raw/commissioner/cap_space/dt={today}/cap_space.parquet`
- Include in manifest

### 2. Create: `dbt/ff_analytics/models/staging/stg_sheets__cap_space.sql`

```sql
-- Grain: franchise_id, season
-- Source: data/raw/commissioner/cap_space/dt=*/cap_space.parquet
-- Purpose: Stage cap space data from Commissioner Sheet

{{ config(
    materialized='view'
) }}

WITH cap_raw AS (
    SELECT * FROM {{ source('sheets', 'cap_space') }}
),

franchise_xref AS (
    SELECT
        franchise_id,
        owner_name,
        season_start,
        COALESCE(season_end, 9999) AS season_end
    FROM {{ ref('dim_franchise') }}
)

SELECT
    fx.franchise_id,
    cr.season,
    cr.available_cap_space::int AS available_cap_space,
    cr.dead_cap_space::int AS dead_cap_space,
    cr.traded_cap_space::int AS traded_cap_space,
    250 AS base_cap,
    CURRENT_DATE AS asof_date

FROM cap_raw cr
INNER JOIN franchise_xref fx
    ON cr.gm = fx.owner_name
    AND cr.season BETWEEN fx.season_start AND fx.season_end
```

### 3. Create: `dbt/ff_analytics/models/staging/stg_sheets__cap_space.yml`

```yaml
version: 2

models:
  - name: stg_sheets__cap_space
    description: |
      Cap space data from Commissioner Sheet roster tabs.

      Grain: franchise_id, season
      Source: Commissioner Sheet (row 3 of each GM's roster tab)
      Refresh: Daily (via copy_league_sheet workflow)

    columns:
      - name: franchise_id
        description: Franchise identifier (F001-F012)
        tests:
          - not_null
          - relationships:
              to: ref('dim_franchise')
              field: franchise_id

      - name: season
        description: Fantasy season year
        tests:
          - not_null
          - accepted_values:
              values: [2025, 2026, 2027, 2028, 2029]

      - name: available_cap_space
        description: Cap space available for new contracts (reported by Commissioner)
        tests:
          - not_null

      - name: dead_cap_space
        description: Dead cap from cut contracts
        tests:
          - not_null

      - name: traded_cap_space
        description: Net cap space traded (positive = acquired, negative = sent)
        tests:
          - not_null

      - name: base_cap
        description: Starting cap space each season ($250)
        tests:
          - not_null
          - accepted_values:
              values: [250]

    tests:
      - dbt_utils.unique_combination_of_columns:
          combination_of_columns:
            - franchise_id
            - season
```

### 4. Create: `dbt/ff_analytics/models/core/mart_cap_situation.sql`

```sql
-- Grain: franchise_id, season
-- Purpose: Comprehensive cap space view with reconciliation

{{ config(
    materialized='table'
) }}

WITH cap_reported AS (
    SELECT * FROM {{ ref('stg_sheets__cap_space') }}
),

active_contracts AS (
    SELECT
        franchise_id,
        year AS season,
        SUM(amount) AS active_contracts_total
    FROM {{ ref('stg_sheets__contracts_active') }}
    GROUP BY franchise_id, year
),

dead_cap_calculated AS (
    SELECT
        franchise_id,
        year AS season,
        SUM(dead_cap_amount) AS dead_cap_total
    FROM {{ ref('stg_sheets__contracts_cut') }}
    GROUP BY franchise_id, year
),

franchise_dim AS (
    SELECT
        franchise_id,
        franchise_name,
        division
    FROM {{ ref('dim_franchise') }}
    WHERE is_current_owner
)

SELECT
    fd.franchise_id,
    fd.franchise_name,
    fd.division,
    cr.season,

    -- Base
    cr.base_cap,

    -- Reported (from sheets)
    cr.available_cap_space AS cap_space_available_reported,
    cr.dead_cap_space AS dead_cap_reported,
    cr.traded_cap_space AS traded_cap_net,

    -- Calculated (from contracts)
    COALESCE(ac.active_contracts_total, 0) AS active_contracts_total,
    COALESCE(dc.dead_cap_total, 0) AS dead_cap_calculated,

    -- Reconciliation
    (cr.base_cap + cr.traded_cap_space - COALESCE(ac.active_contracts_total, 0) - COALESCE(dc.dead_cap_total, 0)) AS cap_space_available_calculated,
    (cr.available_cap_space - (cr.base_cap + cr.traded_cap_space - COALESCE(ac.active_contracts_total, 0) - COALESCE(dc.dead_cap_total, 0))) AS reconciliation_difference,

    -- Final values (use reported per Commissioner)
    cr.available_cap_space AS cap_space_available,

    -- Metadata
    cr.asof_date

FROM cap_reported cr
INNER JOIN franchise_dim fd USING (franchise_id)
LEFT JOIN active_contracts ac USING (franchise_id, season)
LEFT JOIN dead_cap_calculated dc USING (franchise_id, season)

ORDER BY franchise_name, season
```

### 5. Create: `dbt/ff_analytics/models/core/mart_cap_situation.yml`

```yaml
version: 2

models:
  - name: mart_cap_situation
    description: |
      Comprehensive cap space analysis by franchise and season.

      Grain: franchise_id, season
      Purpose: Support FASA bid planning and roster decisions

      Key features:
      - Reported cap space (source of truth from Commissioner)
      - Calculated cap space (for reconciliation)
      - Active contracts and dead cap breakdowns
      - 5-year forward view (2025-2029)

    columns:
      - name: franchise_id
        description: Franchise identifier
        tests:
          - not_null
          - relationships:
              to: ref('dim_franchise')
              field: franchise_id

      - name: franchise_name
        description: Franchise name
        tests:
          - not_null

      - name: season
        description: Fantasy season year
        tests:
          - not_null

      - name: cap_space_available
        description: Cap space available for new contracts (use this for decisions)
        tests:
          - not_null

    tests:
      - dbt_utils.unique_combination_of_columns:
          combination_of_columns:
            - franchise_id
            - season
```

### 6. Update: `dbt/ff_analytics/models/sources/src_sheets.yml`

Add new source table:

```yaml
  - name: cap_space
    description: |
      Cap space data from roster tabs (row 3: Available, Dead, Traded)

      Refresh: Daily via copy_league_sheet workflow
      Path: data/raw/commissioner/cap_space/dt=*/cap_space.parquet

    columns:
      - name: gm
        description: GM name (owner_name)
      - name: season
        description: Fantasy season year
      - name: available_cap_space
        description: Available cap space
      - name: dead_cap_space
        description: Dead cap from cuts
      - name: traded_cap_space
        description: Net cap space traded
```

______________________________________________________________________

## Implementation Steps

1. **Modify `commissioner_parser.py`:**

   - Add `parse_cap_space()` function
   - Update `parse_commissioner_dir()` to parse cap space
   - Write output to `data/raw/commissioner/cap_space/dt={date}/cap_space.parquet`

1. **Update source definition:**

   - Add `cap_space` table to `src_sheets.yml`

1. **Create staging model:**

   - Write `stg_sheets__cap_space.sql`
   - Write `stg_sheets__cap_space.yml` with tests

1. **Create mart model:**

   - Write `mart_cap_situation.sql`
   - Write `mart_cap_situation.yml` with tests

1. **Test locally:**

   ```bash
   # Run parser
   uv run python scripts/ingest/parse_commissioner_sheet.py \
     --sheet-url [URL] --out data/raw/commissioner

   # Check output
   ls data/raw/commissioner/cap_space/dt=*/

   # Run dbt
   make dbt-run
   make dbt-test

   # Query result
   EXTERNAL_ROOT="$PWD/data/raw" dbt show --select mart_cap_situation
   ```

______________________________________________________________________

## Success Criteria

1. **Parser output:**

   - ✅ Cap space parquet files exist: `data/raw/commissioner/cap_space/dt=YYYY-MM-DD/cap_space.parquet`
   - ✅ Files contain 12 franchises × 5 years = 60 rows
   - ✅ Jason's row shows: `available_cap_space=80` for 2025

1. **dbt models:**

   - ✅ `stg_sheets__cap_space` builds successfully
   - ✅ All tests pass (6 column tests + 1 unique combination test)
   - ✅ `mart_cap_situation` builds successfully
   - ✅ All tests pass (4 column tests + 1 unique combination test)

1. **Data validation:**

   - ✅ Jason's cap space matches sheet: $80 (2025), $80 (2026), $158 (2027), $183 (2028), $250 (2029)
   - ✅ All 12 franchises have data for 5 years
   - ✅ Reconciliation differences documented (expected to be non-zero due to manual adjustments)

1. **Code quality:**

   - ✅ `make lint` passes
   - ✅ `make typecheck` passes (if applicable to Python changes)
   - ✅ No SQL linting errors: `make sqlcheck`

______________________________________________________________________

## Validation Commands

```bash
# 1. Run parser (creates parquet files)
uv run python scripts/ingest/parse_commissioner_sheet.py \
  --sheet-url [LEAGUE_SHEET_COPY_URL] \
  --out data/raw/commissioner

# 2. Verify parquet output
ls -lh data/raw/commissioner/cap_space/dt=*/cap_space.parquet

# 3. Inspect parquet contents
uv run python -c "
import polars as pl
df = pl.read_parquet('data/raw/commissioner/cap_space/dt=*/cap_space.parquet')
print(df.filter(pl.col('gm') == 'Jason Shaffer'))
"

# 4. Run dbt models
export EXTERNAL_ROOT="$PWD/data/raw"
make dbt-run --select stg_sheets__cap_space mart_cap_situation

# 5. Run dbt tests
make dbt-test --select stg_sheets__cap_space mart_cap_situation

# 6. Show results
dbt show --select mart_cap_situation --where "franchise_name = 'Jason Shaffer'"

# 7. Code quality checks
make lint
make sqlcheck
```

______________________________________________________________________

## Commit Message

```
feat: add cap space parsing and mart for FASA bid planning

Parse cap space data from Commissioner Sheet roster tabs (row 3) to
support FASA bidding decisions. Adds:

- parse_cap_space() function in commissioner_parser.py
- stg_sheets__cap_space staging model
- mart_cap_situation mart with reconciliation logic

Enables FASA notebook to calculate available cap space and drop
scenarios with accurate dead cap calculations.

Resolves: Sprint 1 Task 1.1
```

______________________________________________________________________

## Notes

- **Manual adjustments:** Commissioner has made some manual cap space adjustments, so `reconciliation_difference` will be non-zero. This is expected and documented in the mart.
- **Source of truth:** Always use `cap_space_available` (reported) for decisions, not calculated values.
- **Traded cap:** Positive values = acquired cap, negative = sent cap via trades.
