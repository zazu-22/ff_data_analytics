# dim_pick Rebuild Architecture v2 - Production-Ready Design

**Date**: 2025-11-07
**Version**: 2.0 (incorporates senior architect feedback)
**Status**: Ready for Implementation

______________________________________________________________________

## Architectural Improvements from v1

This document addresses critical design gaps identified in the initial solution:

1. **Config-driven season boundaries** (not hard-coded `season <= 2024`)
2. **Explicit TBD pick lifecycle** (handoff from prospective → actual)
3. **Immutable FAAD sequence tracking** (prevent retroactive reordering)
4. **Base pick validation with fallback** (handle incomplete draft data)
5. **Comprehensive reconciliation tests** (quality gates before rebuild)

______________________________________________________________________

## 1. Config-Driven Season Boundary

### Problem (from v1)

Hard-coded filters like `WHERE season <= 2024` require SQL edits when 2025 draft completes:

```sql
-- BAD: Requires code change every year
WHERE season <= 2024  -- Historical
WHERE season > 2024   -- Prospective
```

### Solution: dbt Project Variable

**File**: `dbt/ff_analytics/dbt_project.yml`

```yaml
vars:
  # Latest completed rookie draft season
  # Update this ONCE when draft completes (no SQL changes needed)
  latest_completed_draft_season: 2024

  # Historical: seasons with actual draft data (2012-2024)
  # Prospective: seasons with only FAAD projections (2025+)
```

**Usage in models**:

```sql
-- int_pick_draft_actual.sql
WHERE season <= {{ var('latest_completed_draft_season') }}

-- int_pick_comp_sequenced.sql (prospective)
WHERE comp_season > {{ var('latest_completed_draft_season') }}

-- int_pick_base.sql (prospective)
WHERE season > {{ var('latest_completed_draft_season') }}
```

**Update workflow when 2025 draft completes**:

```bash
# 1. Update the config (one-time edit)
vim dbt/ff_analytics/dbt_project.yml
# Change: latest_completed_draft_season: 2024 → 2025

# 2. Rebuild dim_pick (no SQL changes needed!)
dbt run --select dim_pick+
```

**Benefits**:

- ✅ Single source of truth for season boundary
- ✅ No SQL edits required annually
- ✅ Clear documentation of what's historical vs prospective
- ✅ Easy to validate: `dbt run-operation print_vars`

______________________________________________________________________

## 2. TBD Pick Lifecycle & Handoff Logic

### Problem (from v1)

When 2025 draft completes, we have:

- **TBD picks** (`2025_R2_TBD`) in dim_pick from FAAD projections
- **Actual picks** (`2025_R2_P06`) from rookie_draft_selection

Without explicit handoff:

- ❌ Risk duplicate rows (both TBD and actual)
- ❌ Broken FKs if we delete TBD rows
- ❌ Transaction references to TBD picks become invalid

### Solution: Soft-Delete with Transition Tracking

**Design Decision**: TBD picks are **soft-deleted** (not hard-deleted) and **replaced** by actual picks.

#### Model: `dim_pick_lifecycle_control`

Track pick lifecycle states:

```sql
-- dim_pick_lifecycle_control.sql
-- Controls TBD → actual pick transitions

{{ config(materialized='table') }}

WITH tbd_picks_created AS (
    -- All TBD picks ever created (from FAAD projections)
    SELECT DISTINCT
        pick_id as tbd_pick_id,
        season,
        round,
        'TBD' as lifecycle_state,
        CURRENT_TIMESTAMP as created_at,
        NULL as superseded_at,
        NULL as superseded_by_pick_id
    FROM {{ ref('int_pick_tbd') }}
),

actual_picks_created AS (
    -- Actual picks from drafts that supersede TBDs
    SELECT
        season,
        round,
        pick_id as actual_pick_id,
        draft_transaction_id,
        CURRENT_TIMESTAMP as created_at
    FROM {{ ref('int_pick_draft_actual') }}
),

-- Match TBD picks to their actual pick replacements
tbd_to_actual_mapping AS (
    SELECT
        tbd.tbd_pick_id,
        tbd.season,
        tbd.round,
        act.actual_pick_id as superseded_by_pick_id,
        act.created_at as superseded_at,
        CASE
            WHEN act.actual_pick_id IS NOT NULL THEN 'SUPERSEDED'
            ELSE 'ACTIVE_TBD'
        END as lifecycle_state
    FROM tbd_picks_created tbd
    LEFT JOIN actual_picks_created act
        ON tbd.season = act.season
        AND tbd.round = act.round
)

SELECT
    tbd_pick_id as pick_id,
    season,
    round,
    lifecycle_state,
    created_at,
    superseded_at,
    superseded_by_pick_id,

    -- Audit flag for transactions still referencing TBD
    CASE
        WHEN lifecycle_state = 'SUPERSEDED'
        THEN 'WARN: Transactions should reference ' || superseded_by_pick_id
        ELSE NULL
    END as migration_note

FROM tbd_to_actual_mapping
```

#### Updated `dim_pick.sql` with Lifecycle

```sql
-- dim_pick.sql (with TBD lifecycle)

WITH lifecycle_control AS (
    SELECT * FROM {{ ref('dim_pick_lifecycle_control') }}
),

historical_picks AS (
    SELECT
        pick_id,
        season,
        round,
        overall_pick,
        slot_number,
        pick_type,
        'ACTUAL' as lifecycle_state,
        is_prospective = FALSE,
        draft_transaction_id,
        NULL as faad_transaction_id
    FROM {{ ref('int_pick_draft_actual') }}
),

prospective_picks AS (
    SELECT
        comp.pick_id,
        comp.season,
        comp.round,
        999 as overall_pick,  -- TBD
        comp.slot_number,
        'compensatory' as pick_type,
        lc.lifecycle_state,
        is_prospective = TRUE,
        NULL as draft_transaction_id,
        comp.comp_faad_transaction_id as faad_transaction_id
    FROM {{ ref('int_pick_comp_sequenced') }} comp
    LEFT JOIN lifecycle_control lc ON comp.pick_id = lc.pick_id
    WHERE comp.comp_season > {{ var('latest_completed_draft_season') }}
        AND (lc.lifecycle_state IS NULL OR lc.lifecycle_state = 'ACTIVE_TBD')
        -- Only include TBDs that haven't been superseded
)

-- Combine actual + active TBD picks
SELECT * FROM historical_picks
UNION ALL
SELECT * FROM prospective_picks
```

**Handoff Process When Draft Completes**:

```bash
# Step 1: 2025 draft happens, data ingested
make ingest-sheets  # Loads rookie_draft_selection transactions

# Step 2: Update season boundary
vim dbt_project.yml  # Set latest_completed_draft_season: 2025

# Step 3: Rebuild dim_pick
dbt run --select dim_pick+

# What happens:
# - int_pick_draft_actual now includes 2025 picks
# - dim_pick_lifecycle_control marks 2025 TBD picks as SUPERSEDED
# - dim_pick excludes SUPERSEDED TBD picks (filtered out)
# - Actual 2025 picks replace TBD picks seamlessly
```

**Transaction Migration**:

Transactions referencing TBD picks (`2025_R2_TBD`) need to update to actual picks:

```sql
-- int_pick_transaction_xref.sql (updated)
LEFT JOIN dim_pick_lifecycle_control lc
    ON raw.pick_id = lc.pick_id

SELECT
    raw.transaction_id_unique,
    raw.pick_id as pick_id_raw,
    COALESCE(lc.superseded_by_pick_id, raw.pick_id) as pick_id_canonical,
    lc.lifecycle_state,
    lc.migration_note
```

**Benefits**:

- ✅ No duplicate pick rows
- ✅ Audit trail of TBD → actual transitions
- ✅ Transactions auto-migrate to actual picks
- ✅ Can query historical "what TBDs existed before draft?"

______________________________________________________________________

## 3. Immutable FAAD Award Sequence

### Problem (from v1)

FAAD chronological sequence is calculated via `ROW_NUMBER() OVER (ORDER BY transaction_id)`.

**Risk**: If someone manually reorders transactions in Google Sheets (e.g., fixes a typo in transaction_id), the sequence changes retroactively, causing false `SEQUENCE_MISMATCH` flags.

### Solution: Persist Sequence at Ingestion Time

**Principle**: FAAD award sequence is determined **when the FAAD happens** and never changes.

#### Update Commissioner Parser

**File**: `src/ingest/sheets/commissioner_parser.py`

```python
def parse_transactions(sheet_data: pd.DataFrame) -> pd.DataFrame:
    """Parse transactions with stable FAAD sequence."""

    # Existing parsing logic...

    # NEW: Calculate and persist FAAD award sequence
    df['faad_award_sequence'] = None  # Initialize

    # For each FAAD season, assign sequence based on transaction_id order
    faad_mask = df['transaction_type_refined'] == 'faad_ufa_signing'
    faad_txns = df[faad_mask].copy()

    # Sequence by season and chronological transaction_id
    faad_txns['faad_award_sequence'] = (
        faad_txns
        .sort_values(['season', 'transaction_id'])
        .groupby('season')
        .cumcount() + 1  # 1-indexed sequence
    )

    # Merge back into main dataframe
    df.loc[faad_mask, 'faad_award_sequence'] = faad_txns['faad_award_sequence']

    return df
```

**Result**: New column in raw Parquet: `faad_award_sequence`

#### Use Persisted Sequence in dbt

**File**: `int_pick_comp_registry.sql`

```sql
WITH faad_transactions AS (
    SELECT
        transaction_id as comp_faad_transaction_id,
        faad_award_sequence,  -- Use persisted value, not ROW_NUMBER()
        player_name as comp_source_player,
        season,
        faad_compensation_text,
        contract_total,
        contract_years
    FROM {{ ref('stg_sheets__transactions') }}
    WHERE transaction_type = 'faad_ufa_signing'
        AND faad_compensation_text IS NOT NULL
)

-- Sequence comp picks within round using PERSISTED sequence
SELECT
    comp_faad_transaction_id,
    faad_award_sequence,  -- This never changes!
    comp_season,
    comp_round,

    -- Slot = 12 + sequence within this round
    ROW_NUMBER() OVER (
        PARTITION BY comp_season, comp_round
        ORDER BY faad_award_sequence  -- Use persisted sequence
    ) as faad_chronological_seq,

    12 + ROW_NUMBER() OVER (...) as slot_number
FROM parsed_comps
```

#### Immutability Test

**File**: `tests/assert_faad_sequence_immutable.sql`

```sql
-- Ensure FAAD award sequence never changes after ingestion
-- This test compares current sequence to a snapshot

{{ config(
    severity = 'error',
    tags = ['critical', 'data_integrity']
) }}

WITH current_faad_sequence AS (
    SELECT
        transaction_id,
        season,
        player_name,
        faad_award_sequence,
        faad_compensation_text
    FROM {{ ref('stg_sheets__transactions') }}
    WHERE transaction_type = 'faad_ufa_signing'
        AND season <= {{ var('latest_completed_draft_season') }}
),

-- Snapshot of last known good sequence
-- Updated manually when new FAAD completes
expected_sequence AS (
    SELECT
        transaction_id,
        season,
        expected_faad_award_sequence
    FROM {{ ref('seed_faad_award_sequence_snapshot') }}
)

SELECT
    cur.transaction_id,
    cur.season,
    cur.player_name,
    cur.faad_award_sequence as current_sequence,
    exp.expected_faad_award_sequence,
    'FAAD sequence changed retroactively!' as issue
FROM current_faad_sequence cur
INNER JOIN expected_sequence exp
    ON cur.transaction_id = exp.transaction_id
WHERE cur.faad_award_sequence != exp.expected_faad_award_sequence
```

**Seed File**: `seeds/seed_faad_award_sequence_snapshot.csv`

```csv
transaction_id,season,expected_faad_award_sequence
2762,2023,1
2763,2023,2
2796,2023,3
2801,2023,4
...
```

**Update workflow**:

```bash
# When 2025 FAAD completes:
# 1. Export current FAAD sequences
dbt run-operation export_faad_sequences --args '{season: 2025}'

# 2. Append to snapshot seed
cat faad_2025_sequences.csv >> seeds/seed_faad_award_sequence_snapshot.csv

# 3. Run immutability test
dbt test --select assert_faad_sequence_immutable
```

**Benefits**:

- ✅ FAAD sequence locked at ingestion time
- ✅ Manual sheet edits can't corrupt sequence
- ✅ Test alerts if sequence changes
- ✅ Historical reproducibility guaranteed

______________________________________________________________________

## 4. Base Pick Validation with Fallback

### Problem (from v1)

`ROW_NUMBER()` classification assumes every pick in the draft is captured:

```sql
-- Assumes slots 1-12 are base picks
CASE WHEN slot_number <= 12 THEN 'base' ELSE 'compensatory' END
```

**Risk**: If rookie_draft_selection is missing transaction #3214 (the 3rd pick in a round), the 13th pick gets `slot_number = 12` and is mislabeled as base instead of comp.

### Solution: Validate Base Count + Fallback to Seed

#### Validation Model

**File**: `int_pick_draft_validation.sql`

```sql
-- Validate draft data completeness before building dim_pick

{{ config(materialized='table') }}

WITH draft_picks_by_round AS (
    SELECT
        season,
        round,
        COUNT(*) as picks_in_draft,
        MIN(overall_pick) as first_pick,
        MAX(overall_pick) as last_pick,

        -- Expected: 12 base picks per round
        COUNT(*) FILTER (WHERE slot_number <= 12) as base_picks_count,
        COUNT(*) FILTER (WHERE slot_number > 12) as comp_picks_count
    FROM {{ ref('int_pick_draft_actual') }}
    GROUP BY season, round
),

validation_flags AS (
    SELECT
        *,

        -- Validation: Must have exactly 12 base picks
        base_picks_count = 12 as has_complete_base_picks,

        -- Flag incomplete rounds
        CASE
            WHEN base_picks_count < 12 THEN 'INCOMPLETE_BASE_PICKS'
            WHEN base_picks_count > 12 THEN 'TOO_MANY_BASE_PICKS'
            ELSE 'VALID'
        END as validation_status,

        -- Provide diagnostic info
        CASE
            WHEN base_picks_count < 12
            THEN 'Missing ' || (12 - base_picks_count)::VARCHAR || ' base picks'
            WHEN base_picks_count > 12
            THEN 'Extra ' || (base_picks_count - 12)::VARCHAR || ' picks in base range'
            ELSE NULL
        END as validation_message
    FROM draft_picks_by_round
)

SELECT * FROM validation_flags
```

#### Fallback Logic

**File**: `int_pick_draft_actual_with_fallback.sql`

```sql
-- Draft picks with fallback to seed for incomplete rounds

WITH draft_picks_raw AS (
    SELECT * FROM {{ ref('int_pick_draft_actual') }}
),

validation AS (
    SELECT * FROM {{ ref('int_pick_draft_validation') }}
),

-- Seed-based base picks (fallback for incomplete drafts)
seed_base_picks AS (
    SELECT
        season,
        round,
        slot_number,
        season || '_R' || round || '_P' || LPAD(slot_number::VARCHAR, 2, '0') as pick_id,
        'base' as pick_type,
        'SEED_FALLBACK' as source
    FROM {{ ref('int_pick_base') }}
    WHERE season <= {{ var('latest_completed_draft_season') }}
        AND slot_number <= 12  -- Only base picks
),

-- Use draft data for complete rounds, seed for incomplete
picks_with_fallback AS (
    SELECT
        dp.*,
        'DRAFT_ACTUAL' as source
    FROM draft_picks_raw dp
    INNER JOIN validation v
        ON dp.season = v.season
        AND dp.round = v.round
    WHERE v.has_complete_base_picks  -- Only use draft if complete

    UNION ALL

    -- Fallback: Use seed for incomplete rounds
    SELECT
        seed.pick_id,
        seed.season,
        seed.round,
        NULL as overall_pick,  -- Unknown (missing draft data)
        seed.slot_number,
        seed.pick_type,
        NULL as comp_sequence_in_round,
        NULL as draft_transaction_id,
        NULL as player_drafted,
        NULL as drafted_by_team,
        seed.source
    FROM seed_base_picks seed
    INNER JOIN validation v
        ON seed.season = v.season
        AND seed.round = v.round
    WHERE NOT v.has_complete_base_picks  -- Only for incomplete rounds
)

SELECT * FROM picks_with_fallback
```

#### Test for Base Pick Counts

**File**: `tests/assert_12_base_picks_per_round.sql`

```sql
-- Every historical round must have exactly 12 base picks

{{ config(severity = 'error') }}

SELECT
    season,
    round,
    base_picks_count,
    validation_status,
    validation_message,
    'Expected 12 base picks per round' as issue
FROM {{ ref('int_pick_draft_validation') }}
WHERE NOT has_complete_base_picks
    AND season >= 2012  -- Earliest reliable draft data
    AND season <= {{ var('latest_completed_draft_season') }}
```

**Benefits**:

- ✅ Detects missing draft transactions
- ✅ Fallback to seed prevents mislabeling
- ✅ Test alerts before dim_pick rebuild
- ✅ Audit trail shows which rounds used fallback

______________________________________________________________________

## 5. Reconciliation Quality Tests

### Test Suite for Reconciliation Outputs

#### Test 1: Base Pick Count per Round

**File**: `tests/assert_reconciliation_base_picks.sql`

```sql
-- Verify every historical round has exactly 12 base picks

SELECT
    season,
    round,
    COUNT(*) FILTER (WHERE pick_type = 'base') as base_count,
    '12 base picks required per round' as rule
FROM {{ ref('dim_pick') }}
WHERE season <= {{ var('latest_completed_draft_season') }}
    AND lifecycle_state = 'ACTUAL'
GROUP BY season, round
HAVING COUNT(*) FILTER (WHERE pick_type = 'base') != 12
```

#### Test 2: Comp Pick Count Matches FAAD

**File**: `tests/assert_reconciliation_comp_counts.sql`

```sql
-- Comp picks in dim_pick must match FAAD comp awards per round

WITH faad_comp_counts AS (
    SELECT
        comp_season as season,
        comp_round as round,
        COUNT(*) as faad_comp_count
    FROM {{ ref('int_pick_comp_registry') }}
    WHERE comp_season <= {{ var('latest_completed_draft_season') }}
    GROUP BY comp_season, comp_round
),

dim_comp_counts AS (
    SELECT
        season,
        round,
        COUNT(*) as dim_comp_count
    FROM {{ ref('dim_pick') }}
    WHERE pick_type = 'compensatory'
        AND lifecycle_state = 'ACTUAL'
        AND season <= {{ var('latest_completed_draft_season') }}
    GROUP BY season, round
)

SELECT
    COALESCE(f.season, d.season) as season,
    COALESCE(f.round, d.round) as round,
    f.faad_comp_count,
    d.dim_comp_count,
    ABS(COALESCE(f.faad_comp_count, 0) - COALESCE(d.dim_comp_count, 0)) as delta,
    'Comp pick count mismatch between FAAD and dim_pick' as issue
FROM faad_comp_counts f
FULL OUTER JOIN dim_comp_counts d
    ON f.season = d.season AND f.round = d.round
WHERE COALESCE(f.faad_comp_count, 0) != COALESCE(d.dim_comp_count, 0)
```

#### Test 3: Reconciliation Match Rate Threshold

**File**: `tests/assert_reconciliation_match_rate.sql`

```sql
-- At least 90% of comp picks should MATCH between FAAD and actual draft

{{ config(
    severity = 'warn',  -- WARN, not ERROR (some mismatches expected)
    tags = ['reconciliation', 'quality']
) }}

WITH reconciliation_stats AS (
    SELECT
        COUNT(*) as total_comps,
        COUNT(*) FILTER (WHERE reconciliation_status = 'MATCHED') as matched_comps,
        COUNT(*) FILTER (WHERE reconciliation_status = 'FAAD_AWARD_NOT_DRAFTED') as faad_not_drafted,
        COUNT(*) FILTER (WHERE reconciliation_status = 'DRAFTED_WITHOUT_FAAD_AWARD') as drafted_without_faad,
        COUNT(*) FILTER (WHERE reconciliation_status = 'SEQUENCE_MISMATCH') as sequence_mismatch,

        -- Match rate percentage
        ROUND(
            100.0 * COUNT(*) FILTER (WHERE reconciliation_status = 'MATCHED') /
            NULLIF(COUNT(*), 0),
            1
        ) as match_rate_pct
    FROM {{ ref('int_pick_comp_reconciliation') }}
),

threshold_check AS (
    SELECT
        *,
        90.0 as minimum_match_rate_pct,
        match_rate_pct >= 90.0 as meets_threshold
    FROM reconciliation_stats
)

SELECT
    total_comps,
    matched_comps,
    faad_not_drafted,
    drafted_without_faad,
    sequence_mismatch,
    match_rate_pct,
    minimum_match_rate_pct,
    'Reconciliation match rate below 90% threshold' as issue
FROM threshold_check
WHERE NOT meets_threshold
```

#### Test 4: Duplicate Pick Detection

**File**: `tests/assert_no_duplicate_picks.sql`

```sql
-- No pick_id should appear twice in dim_pick

SELECT
    pick_id,
    COUNT(*) as occurrence_count,
    STRING_AGG(DISTINCT lifecycle_state, ', ') as states,
    'Duplicate pick_id in dim_pick' as issue
FROM {{ ref('dim_pick') }}
GROUP BY pick_id
HAVING COUNT(*) > 1
```

#### Test 5: TBD Pick Migration Completeness

**File**: `tests/assert_tbd_migration_complete.sql`

```sql
-- When draft completes, all TBD picks should be SUPERSEDED

WITH completed_seasons AS (
    SELECT season
    FROM {{ ref('int_pick_draft_actual') }}
    GROUP BY season
),

tbd_picks_in_completed_seasons AS (
    SELECT
        lc.pick_id,
        lc.season,
        lc.round,
        lc.lifecycle_state,
        lc.superseded_by_pick_id
    FROM {{ ref('dim_pick_lifecycle_control') }} lc
    INNER JOIN completed_seasons cs
        ON lc.season = cs.season
    WHERE lc.pick_id LIKE '%_TBD'
)

SELECT
    pick_id,
    season,
    round,
    lifecycle_state,
    'TBD pick not superseded despite draft completing' as issue
FROM tbd_picks_in_completed_seasons
WHERE lifecycle_state != 'SUPERSEDED'
```

### Pre-Rebuild Quality Gate

**File**: `tests/schema.yml`

```yaml
# Tag all critical reconciliation tests
tests:
  - name: assert_reconciliation_base_picks
    config:
      tags: ['pre_rebuild', 'critical']
      severity: error

  - name: assert_reconciliation_comp_counts
    config:
      tags: ['pre_rebuild', 'critical']
      severity: warn  # Allow some variance

  - name: assert_reconciliation_match_rate
    config:
      tags: ['pre_rebuild', 'quality']
      severity: warn

  - name: assert_no_duplicate_picks
    config:
      tags: ['pre_rebuild', 'critical']
      severity: error
```

**Run before rebuild**:

```bash
# Must pass before rebuilding dim_pick
dbt test --select tag:pre_rebuild
```

______________________________________________________________________

## Implementation Sequence

### Phase 1: Foundation (Critical Path)

1. **Add `latest_completed_draft_season` to dbt_project.yml**

   - Set initial value: `2024`
   - Update all models to use `{{ var('latest_completed_draft_season') }}`

2. **Update commissioner parser**

   - Add `faad_award_sequence` calculation
   - Re-ingest data: `make ingest-sheets`

3. **Create snapshot seed**

   - `seeds/seed_faad_award_sequence_snapshot.csv`
   - Populate with current FAAD sequences (2012-2024)

4. **Build validation models**

   - `int_pick_draft_validation.sql`
   - `int_pick_draft_actual_with_fallback.sql`
   - Test: `assert_12_base_picks_per_round.sql`

### Phase 2: Reconciliation & Lifecycle

5. **Build reconciliation model**

   - `int_pick_comp_reconciliation.sql` (using persisted sequences)
   - Add all reconciliation tests

6. **Build lifecycle model**

   - `dim_pick_lifecycle_control.sql`
   - Test: `assert_tbd_migration_complete.sql`

7. **Update dim_pick with lifecycle**

   - Filter out SUPERSEDED TBDs
   - Add `lifecycle_state`, `source` columns

### Phase 3: Quality Gates

08. **Run pre-rebuild tests**

    ```bash
    dbt test --select tag:pre_rebuild
    ```

09. **Review reconciliation report**

    ```sql
    SELECT * FROM int_pick_comp_reconciliation
    WHERE reconciliation_status != 'MATCHED'
    ```

10. **Rebuild dim_pick**

    ```bash
    dbt run --select dim_pick+
    ```

11. **Validate results**

    ```bash
    dbt test --select dim_pick
    ```

______________________________________________________________________

## Annual Maintenance Workflow

**When 2025 rookie draft completes:**

```bash
# 1. Ingest draft data
make ingest-sheets

# 2. Snapshot FAAD sequences
dbt run-operation export_faad_sequences --args '{season: 2025}'
cat faad_2025.csv >> seeds/seed_faad_award_sequence_snapshot.csv
dbt seed --select seed_faad_award_sequence_snapshot

# 3. Update season boundary (ONLY edit needed!)
vim dbt/ff_analytics/dbt_project.yml
# Change: latest_completed_draft_season: 2024 → 2025

# 4. Run quality gates
dbt test --select tag:pre_rebuild

# 5. Rebuild dim_pick (no SQL changes!)
dbt run --select dim_pick+

# 6. Verify
dbt test --select dim_pick
```

**Benefits**: One config change, zero SQL edits.

______________________________________________________________________

## Success Metrics

### Before (Current State)

- ❌ Relationship test failures: 10
- ❌ Hard-coded season filters in 5+ models
- ❌ TBD picks remain after draft completes
- ❌ No protection against FAAD sequence changes
- ❌ No validation of base pick counts

### After (Target State)

- ✅ Relationship test failures: 0-2 (only true data errors)
- ✅ Config-driven season boundary (1 edit/year)
- ✅ TBD picks auto-superseded when draft completes
- ✅ FAAD sequence immutability enforced
- ✅ Base pick validation with seed fallback
- ✅ Reconciliation quality tests (>90% match rate)
- ✅ Zero SQL edits for annual draft updates

______________________________________________________________________

## Related Documents

- **v1 Solution**: `docs/investigations/dim_pick_rebuild_solution_2025-11-07.md`
- **League Constitution**: `docs/spec/league_constitution.csv`
- **ADR-008**: `docs/adr/ADR-008-pick-identity-resolution-via-overall-pick-number.md`
