# dim_pick Rebuild Implementation Plan

**Date**: 2025-11-07
**Author**: Claude Code
**Purpose**: Replace seed-based dim_pick with complete dbt model including compensatory picks

______________________________________________________________________

## Executive Summary

The current `dim_pick` seed contains only "base" picks (P01-P12 per round, 2012-2030). Investigation revealed **56 compensatory picks** awarded 2020-2026 that are missing from the dimension, causing 51 relationship test failures.

This plan rebuilds `dim_pick` as a **dbt model** (not seed) that:

1. Generates base picks (P01-P12) for all years/rounds
2. Extracts compensatory picks from FAAD Comp column in transactions
3. Sequences picks chronologically per league rules
4. Implements comprehensive data quality checks

______________________________________________________________________

## Current State Analysis

### Existing dim_pick Seed

- **Location**: `dbt/ff_analytics/seeds/dim_pick.csv`
- **Structure**: 1,140 rows (19 years × 5 rounds × 12 picks)
- **Schema**: `pick_id, season, round, overall_pick, pick_type, notes`
- **Coverage**: 2012-2030 base picks only
- **Missing**: All compensatory picks (P13+)

### Downstream Dependencies

1. **dim_pick_valuation** - Calculates overall pick numbers, KTC values
2. **dim_asset** - UNIONs players + picks for unified asset dimension
3. **fact_league_transactions** - References pick_id (58 failures due to missing comps)

### Known Data Quality Issues

1. JP's Jessie Bates comp: FAAD shows R3, draft_picks shows R2 (FAAD is correct)
2. 2024 R2: 14 actual picks vs 13 expected (one unreported comp)
3. 2021 R3/R4: Net-zero swap (-1/+1) suggests misclassification

______________________________________________________________________

## Design Specifications

### Schema (Enhanced from Current)

```sql
-- dim_pick (dbt model, not seed)
CREATE TABLE dim_pick AS (
  pick_id VARCHAR PRIMARY KEY,            -- YYYY_R#_P## (e.g., "2024_R1_P14")
  season INTEGER NOT NULL,                -- Draft year (2012-2030+)
  round INTEGER NOT NULL,                 -- 1-5
  overall_pick INTEGER NOT NULL,          -- Overall position (1-60+ with comps)
  pick_type VARCHAR NOT NULL,             -- 'base', 'compensatory', 'tbd'

  -- NEW: Comp pick metadata
  slot_number INTEGER NOT NULL,           -- Within-round position (P01-P60+)
  is_compensatory BOOLEAN NOT NULL,       -- TRUE for P13+
  comp_source_player VARCHAR,             -- Player name that triggered comp (if applicable)
  comp_awarded_to_franchise VARCHAR,      -- Original franchise awarded (before trades)
  comp_faad_transaction_id INTEGER,       -- Transaction ID from FAAD award
  comp_round_threshold VARCHAR,           -- Contract AAV threshold (e.g., "$15-24/yr → R2")
  faad_chronological_seq INTEGER,         -- Sequence within round (1=first comp, 2=second, etc.)

  -- Existing
  notes VARCHAR                           -- Freeform notes
);
```

### Grain

- **Primary key**: `pick_id` (unique)
- **One row per**: Draft pick (base or compensatory)
- **Scope**: All picks referenced in transactions OR expected for future drafts

### Pick ID Format

- **Base picks**: `YYYY_R#_P##` where `##` is 01-12
- **Comp picks**: `YYYY_R#_P##` where `##` is 13-60+
- **TBD picks**: `YYYY_R#_TBD` (future picks with unknown slot)

______________________________________________________________________

## Implementation Architecture

### Model Structure (dbt)

```
models/core/
├── dim_pick.sql                    # Final dimension (UNION of base + comp + tbd)
├── _dim_pick.yml                   # Tests and documentation
└── intermediate/
    ├── int_pick_base.sql           # Base picks generator (P01-P12)
    ├── int_pick_comp_registry.sql  # Comp picks from FAAD Comp column
    ├── int_pick_comp_sequenced.sql # Comp picks with chronological ordering
    └── int_pick_tbd.sql            # TBD picks from transactions
```

### Model Lineage

```
stg_sheets__transactions
         ↓
    ┌────┴─────────────┬──────────────┬──────────────┐
    ↓                  ↓              ↓              ↓
int_pick_base  int_pick_comp_registry  int_pick_tbd  dim_franchise
    │                  ↓                    │
    │         int_pick_comp_sequenced       │
    │                  │                    │
    └──────────────────┴────────────────────┘
                       ↓
                  dim_pick
                       ↓
          ┌────────────┴────────────┐
          ↓                         ↓
   dim_pick_valuation          dim_asset
          ↓
   fact_league_transactions
```

______________________________________________________________________

## Phase 1: Base Picks Generation

### int_pick_base.sql

Generates standard P01-P12 picks for all years and rounds.

**Logic**:

```sql
-- Generate 12 picks × 5 rounds × (2012-2030) = 1,140 base picks
WITH years AS (
  SELECT UNNEST(generate_series(2012, 2030)) AS season
),
rounds AS (
  SELECT UNNEST([1, 2, 3, 4, 5]) AS round
),
slots AS (
  SELECT UNNEST(generate_series(1, 12)) AS slot_number
),
base_picks AS (
  SELECT
    season || '_R' || round || '_P' || LPAD(slot_number::VARCHAR, 2, '0') AS pick_id,
    season,
    round,
    ((round - 1) * 12) + slot_number AS overall_pick,  -- Provisional (ignores comps in prior rounds)
    slot_number,
    'base' AS pick_type,
    FALSE AS is_compensatory,
    CAST(NULL AS VARCHAR) AS comp_source_player,
    CAST(NULL AS VARCHAR) AS comp_awarded_to_franchise,
    CAST(NULL AS INTEGER) AS comp_faad_transaction_id,
    CAST(NULL AS VARCHAR) AS comp_round_threshold,
    CAST(NULL AS INTEGER) AS faad_chronological_seq,
    '' AS notes
  FROM years
  CROSS JOIN rounds
  CROSS JOIN slots
)
SELECT * FROM base_picks
```

**Tests**:

- Grain: `unique` on `pick_id`
- Count: Exactly 1,140 rows (19 years × 5 rounds × 12 picks)
- Range: `season BETWEEN 2012 AND 2030`
- Completeness: All rounds 1-5 present for each year

______________________________________________________________________

## Phase 2: Compensatory Picks Extraction

### int_pick_comp_registry.sql

Parses FAAD Comp column to extract all compensatory pick awards.

**Logic**:

```sql
WITH faad_transactions AS (
  SELECT
    transaction_id,
    transaction_date,
    from_franchise_id,  -- Team that signed the RFA
    to_franchise_id,    -- Team that lost the RFA (receives comp)
    player_display_name AS comp_source_player,
    faad_comp,
    contract_apy
  FROM {{ ref('stg_sheets__transactions') }}
  WHERE transaction_type = 'free_agent_signing'
    AND faad_comp IS NOT NULL
    AND faad_comp != '-'
),

parsed_comps AS (
  SELECT
    transaction_id AS comp_faad_transaction_id,
    transaction_date,
    comp_source_player,
    faad_comp,
    contract_apy,

    -- Parse FAAD Comp format
    -- Historical: "YYYY Rnd" (e.g., "2024 1st", "2023 3rd")
    -- Prospective: "Rnd to Owner" (e.g., "1st to Joe", "2nd to Piper")

    CASE
      -- Historical format: "YYYY Rnd"
      WHEN REGEXP_MATCHES(faad_comp, '^\d{4} \d')
        THEN CAST(REGEXP_EXTRACT(faad_comp, '^(\d{4})', 1) AS INTEGER)
      -- Prospective format: "Rnd to Owner" - infer from transaction_date + 1 year
      WHEN REGEXP_MATCHES(faad_comp, '^\d(?:st|nd|rd|th) to')
        THEN YEAR(transaction_date) + 1
      ELSE NULL
    END AS comp_season,

    CASE
      WHEN REGEXP_MATCHES(faad_comp, '1st') THEN 1
      WHEN REGEXP_MATCHES(faad_comp, '2nd') THEN 2
      WHEN REGEXP_MATCHES(faad_comp, '3rd') THEN 3
      WHEN REGEXP_MATCHES(faad_comp, '4th') THEN 4
      WHEN REGEXP_MATCHES(faad_comp, '5th') THEN 5
      ELSE NULL
    END AS comp_round,

    -- Extract owner from prospective format "Rnd to Owner"
    CASE
      WHEN REGEXP_MATCHES(faad_comp, 'to (.+)$')
        THEN REGEXP_EXTRACT(faad_comp, 'to (.+)$', 1)
      ELSE NULL
    END AS comp_awarded_to_owner,

    -- Infer comp_awarded_to_franchise from owner name or to_franchise_id
    to_franchise_id AS comp_awarded_to_franchise_id,

    -- Contract AAV threshold validation
    CASE
      WHEN contract_apy >= 25 THEN 'R1: $25+/yr'
      WHEN contract_apy >= 15 THEN 'R2: $15-24/yr'
      WHEN contract_apy >= 10 THEN 'R3: $10-14/yr'
      ELSE 'Below R3 threshold (<$10/yr)'
    END AS comp_round_threshold_actual,

    CASE
      WHEN comp_round = 1 THEN 'R1: $25+/yr'
      WHEN comp_round = 2 THEN 'R2: $15-24/yr'
      WHEN comp_round = 3 THEN 'R3: $10-14/yr'
      ELSE 'Unknown'
    END AS comp_round_threshold_expected

  FROM faad_transactions
)

SELECT
  *,
  -- Data quality flag: Does contract AAV match comp round?
  comp_round_threshold_actual = comp_round_threshold_expected AS is_aav_valid
FROM parsed_comps
WHERE comp_season IS NOT NULL AND comp_round IS NOT NULL
```

**Tests**:

- Count: Should match investigation (56 total comps 2020-2026)
- Completeness: No NULL comp_season or comp_round
- **Data quality**: Flag AAV mismatches (JP Jessie Bates, 2024 R2 mystery)

______________________________________________________________________

## Phase 3: Compensatory Pick Sequencing

### int_pick_comp_sequenced.sql

Assigns pick numbers (P13+) to comp picks based on FAAD chronological order.

**Logic**:

```sql
WITH comp_registry AS (
  SELECT * FROM {{ ref('int_pick_comp_registry') }}
),

comp_sequenced AS (
  SELECT
    comp_season AS season,
    comp_round AS round,
    comp_faad_transaction_id,
    comp_source_player,
    comp_awarded_to_franchise_id,
    comp_round_threshold_expected,

    -- Chronological sequence within each round
    ROW_NUMBER() OVER (
      PARTITION BY comp_season, comp_round
      ORDER BY comp_faad_transaction_id  -- FAAD transaction order
    ) AS faad_chronological_seq,

    -- Slot number = 12 (base picks) + chronological sequence
    12 + ROW_NUMBER() OVER (
      PARTITION BY comp_season, comp_round
      ORDER BY comp_faad_transaction_id
    ) AS slot_number

  FROM comp_registry
),

comp_picks AS (
  SELECT
    season || '_R' || round || '_P' || LPAD(slot_number::VARCHAR, 2, '0') AS pick_id,
    season,
    round,
    999 AS overall_pick,  -- Placeholder, will be recalculated in final model
    slot_number,
    'compensatory' AS pick_type,
    TRUE AS is_compensatory,
    comp_source_player,
    comp_awarded_to_franchise_id AS comp_awarded_to_franchise,
    comp_faad_transaction_id,
    comp_round_threshold_expected AS comp_round_threshold,
    faad_chronological_seq,
    'Comp for ' || comp_source_player AS notes
  FROM comp_sequenced
)

SELECT * FROM comp_picks
```

**Tests**:

- Grain: `unique` on `pick_id`
- Sequencing: `faad_chronological_seq` matches transaction_id order
- Slot numbering: All comps have `slot_number > 12`

______________________________________________________________________

## Phase 4: TBD Picks Extraction

### int_pick_tbd.sql

Extracts TBD picks referenced in transactions but not yet finalized.

**Logic**:

```sql
WITH transaction_picks AS (
  SELECT DISTINCT
    pick_id
  FROM {{ ref('stg_sheets__transactions') }}
  WHERE asset_type = 'pick'
    AND pick_id LIKE '%_TBD'
),

tbd_parsed AS (
  SELECT
    pick_id,
    CAST(REGEXP_EXTRACT(pick_id, '^(\d{4})_R', 1) AS INTEGER) AS season,
    CAST(REGEXP_EXTRACT(pick_id, '_R(\d+)_', 1) AS INTEGER) AS round,
    99 AS overall_pick,  -- Placeholder
    99 AS slot_number,   -- Unknown until finalized
    'tbd' AS pick_type,
    FALSE AS is_compensatory,
    CAST(NULL AS VARCHAR) AS comp_source_player,
    CAST(NULL AS VARCHAR) AS comp_awarded_to_franchise,
    CAST(NULL AS INTEGER) AS comp_faad_transaction_id,
    CAST(NULL AS VARCHAR) AS comp_round_threshold,
    CAST(NULL AS INTEGER) AS faad_chronological_seq,
    'TBD - position unknown' AS notes
  FROM transaction_picks
)

SELECT * FROM tbd_parsed
```

**Tests**:

- All pick_ids end with `_TBD`
- Count: Should match investigation (~33 TBD picks)

______________________________________________________________________

## Phase 5: Final dim_pick Assembly

### dim_pick.sql

UNIONs base + comp + TBD picks, recalculates overall_pick accounting for comps.

**Logic**:

```sql
WITH base_picks AS (
  SELECT * FROM {{ ref('int_pick_base') }}
),

comp_picks AS (
  SELECT * FROM {{ ref('int_pick_comp_sequenced') }}
),

tbd_picks AS (
  SELECT * FROM {{ ref('int_pick_tbd') }}
),

all_picks AS (
  SELECT * FROM base_picks
  UNION ALL
  SELECT * FROM comp_picks
  UNION ALL
  SELECT * FROM tbd_picks
),

-- Recalculate overall_pick accounting for comps in prior rounds
overall_pick_final AS (
  SELECT
    *,
    ROW_NUMBER() OVER (
      PARTITION BY season
      ORDER BY round, slot_number
    ) AS overall_pick_recalculated
  FROM all_picks
  WHERE pick_type IN ('base', 'compensatory')  -- Exclude TBD from numbering
)

SELECT
  pick_id,
  season,
  round,
  overall_pick_recalculated AS overall_pick,
  slot_number,
  pick_type,
  is_compensatory,
  comp_source_player,
  comp_awarded_to_franchise,
  comp_faad_transaction_id,
  comp_round_threshold,
  faad_chronological_seq,
  notes
FROM overall_pick_final

UNION ALL

-- Add TBD picks with placeholder values
SELECT
  pick_id,
  season,
  round,
  overall_pick,  -- Keep placeholder 99
  slot_number,   -- Keep placeholder 99
  pick_type,
  is_compensatory,
  comp_source_player,
  comp_awarded_to_franchise,
  comp_faad_transaction_id,
  comp_round_threshold,
  faad_chronological_seq,
  notes
FROM all_picks
WHERE pick_type = 'tbd'
```

______________________________________________________________________

## Data Quality Tests

### Test Suite (\_dim_pick.yml)

```yaml
models:
  - name: dim_pick
    description: "Complete draft pick dimension including base and compensatory picks"

    config:
      tags: ['core', 'dimension']

    # Grain test
    data_tests:
      - dbt_utils.unique_combination_of_columns:
          arguments:
            combination_of_columns:
              - pick_id
          config:
            severity: error

      # Base picks count validation (12 per round per year, 2012-2030)
      - dbt_expectations.expect_table_row_count_to_equal:
          arguments:
            value: 1140
          config:
            where: "pick_type = 'base'"
            severity: error

      # Comp picks count validation (56 total, 2020-2026)
      - dbt_expectations.expect_table_row_count_to_be_between:
          arguments:
            min_value: 50
            max_value: 70
          config:
            where: "pick_type = 'compensatory'"
            severity: warn

      # AAV threshold validation
      - dbt_expectations.expect_column_values_to_be_in_set:
          arguments:
            column_name: comp_round_threshold
            value_set: ['R1: $25+/yr', 'R2: $15-24/yr', 'R3: $10-14/yr']
          config:
            where: "is_compensatory"
            severity: warn

    columns:
      - name: pick_id
        description: "Primary key: YYYY_R#_P## format"
        data_tests:
          - not_null
          - unique

      - name: season
        description: "Draft year (2012-2030+)"
        data_tests:
          - not_null
          - dbt_expectations.expect_column_values_to_be_between:
              arguments:
                min_value: 2012
                max_value: 2035

      - name: round
        description: "Draft round (1-5)"
        data_tests:
          - not_null
          - accepted_values:
              arguments:
                values: [1, 2, 3, 4, 5]

      - name: pick_type
        description: "Pick classification: base, compensatory, tbd"
        data_tests:
          - not_null
          - accepted_values:
              arguments:
                values: ['base', 'compensatory', 'tbd']

      - name: is_compensatory
        description: "TRUE for comp picks (P13+)"
        data_tests:
          - not_null

      - name: slot_number
        description: "Within-round position (1-60+)"
        data_tests:
          - not_null
          - dbt_expectations.expect_column_values_to_be_between:
              arguments:
                min_value: 1
                max_value: 100
              config:
                where: "pick_type != 'tbd'"
```

### Custom Data Quality Tests

```sql
-- tests/assert_comp_pick_aav_matches_round.sql
/*
Validates compensatory pick rounds match contract AAV thresholds.
Expected failures:
- JP Jessie Bates: FAAD shows R3, should be R3 (contract $10/yr)
- Investigate any other mismatches
*/

WITH comp_picks AS (
  SELECT
    pick_id,
    season,
    round,
    comp_source_player,
    comp_round_threshold,
    comp_faad_transaction_id
  FROM {{ ref('dim_pick') }}
  WHERE is_compensatory
),

faad_contracts AS (
  SELECT
    transaction_id,
    player_display_name,
    contract_apy,
    CASE
      WHEN contract_apy >= 25 THEN 1
      WHEN contract_apy >= 15 THEN 2
      WHEN contract_apy >= 10 THEN 3
      ELSE 4
    END AS expected_round
  FROM {{ ref('stg_sheets__transactions') }}
  WHERE transaction_type = 'free_agent_signing'
    AND faad_comp IS NOT NULL
    AND faad_comp != '-'
)

SELECT
  cp.pick_id,
  cp.comp_source_player,
  cp.round AS actual_round,
  fc.expected_round,
  fc.contract_apy,
  cp.comp_round_threshold
FROM comp_picks cp
JOIN faad_contracts fc
  ON cp.comp_faad_transaction_id = fc.transaction_id
WHERE cp.round != fc.expected_round
```

```sql
-- tests/assert_comp_pick_chronological_order.sql
/*
Validates comp picks are sequenced by FAAD transaction order.
*/

WITH comp_picks AS (
  SELECT
    pick_id,
    season,
    round,
    faad_chronological_seq,
    comp_faad_transaction_id
  FROM {{ ref('dim_pick') }}
  WHERE is_compensatory
),

expected_sequence AS (
  SELECT
    season,
    round,
    comp_faad_transaction_id,
    ROW_NUMBER() OVER (
      PARTITION BY season, round
      ORDER BY comp_faad_transaction_id
    ) AS expected_seq
  FROM comp_picks
)

SELECT
  cp.pick_id,
  cp.faad_chronological_seq AS actual_seq,
  es.expected_seq,
  cp.comp_faad_transaction_id
FROM comp_picks cp
JOIN expected_sequence es
  ON cp.season = es.season
  AND cp.round = es.round
  AND cp.comp_faad_transaction_id = es.comp_faad_transaction_id
WHERE cp.faad_chronological_seq != es.expected_seq
```

______________________________________________________________________

## Migration Strategy

### Step 1: Build New Models (Parallel to Seed)

1. Create intermediate models (int_pick\_\*)
2. Create new dim_pick model
3. Run tests - DO NOT drop seed yet

### Step 2: Validate New vs Old

```sql
-- Validation query: Compare new model to old seed
SELECT
  'Only in seed' AS source,
  COUNT(*) AS pick_count
FROM {{ ref('seed:dim_pick') }}
WHERE pick_id NOT IN (SELECT pick_id FROM {{ ref('dim_pick') }})

UNION ALL

SELECT
  'Only in model' AS source,
  COUNT(*) AS pick_count
FROM {{ ref('dim_pick') }}
WHERE pick_id NOT IN (SELECT pick_id FROM {{ ref('seed:dim_pick') }})

UNION ALL

SELECT
  'In both' AS source,
  COUNT(*) AS pick_count
FROM {{ ref('dim_pick') }}
WHERE pick_id IN (SELECT pick_id FROM {{ ref('seed:dim_pick') }})
```

### Step 3: Update Downstream Dependencies

1. Verify dim_pick_valuation still works
2. Verify dim_asset still works
3. Verify fact_league_transactions relationships pass

### Step 4: Deprecate Seed

1. Move `seeds/dim_pick.csv` to `seeds/_archive/`
2. Update dbt_project.yml to exclude archived seeds
3. Document migration in CHANGELOG

______________________________________________________________________

## Known Issues and Resolutions

### Issue 1: JP Jessie Bates Comp Round Mismatch

- **Problem**: FAAD shows "3rd to JP", draft_picks table shows R2
- **Root cause**: Data entry error in draft_picks table
- **Resolution**: Trust FAAD Comp column (R3 is correct per AAV threshold)
- **Action**: int_pick_comp_registry will use FAAD as source of truth

### Issue 2: 2024 R2 Extra Comp Pick

- **Problem**: 14 actual picks vs 13 expected (only 1 R2 comp in FAAD)
- **Root cause**: Likely one R3 comp was actually R2 based on contract AAV
- **Resolution**: AAV validation test will flag mismatches
- **Action**: Manual investigation of 2023 FAAD R3 comp contracts

### Issue 3: 2021 R3/R4 Swap

- **Problem**: R3 -1 pick, R4 +1 pick (net zero)
- **Root cause**: One comp pick misclassified between adjacent rounds
- **Resolution**: AAV validation test will identify the misclassified pick
- **Action**: Correct based on actual contract AAV

______________________________________________________________________

## Success Criteria

1. ✅ All base picks (1,140) present in final model
2. ✅ All comp picks (56) extracted from FAAD Comp column
3. ✅ All TBD picks (~33) extracted from transactions
4. ✅ Chronological ordering matches FAAD transaction sequence
5. ✅ AAV validation flags 3 known discrepancies
6. ✅ fact_league_transactions relationship tests pass (0 failures)
7. ✅ Grain test passes (pick_id unique)
8. ✅ Downstream models (dim_pick_valuation, dim_asset) unaffected

______________________________________________________________________

## Timeline

- **Phase 1**: 2 hours
- **Phase 2**: 3 hours
- **Phase 3**: 2 hours
- **Phase 4**: 1 hour
- **Phase 5**: 3 hours
- **Phase 6**: 2 hours
- **Total**: 13 hours

______________________________________________________________________

## Documentation Requirements

1. Update `_dim_pick.yml` with complete column documentation
2. Add CLAUDE.md section on comp pick maintenance
3. Create runbook for adding future comp picks
4. Document AAV threshold validation process

______________________________________________________________________

## References

- Investigation report: `docs/investigations/comp_pick_investigation_2025-11-07.md`
- 2026 comp picks reference: `docs/investigations/2026_comp_picks_reference.md`
- League constitution: `dbt/ff_analytics/seeds/league_constitution.csv`
- Kimball modeling guide: `docs/spec/kimball_modeling_guidance/kimbal_modeling.md`
