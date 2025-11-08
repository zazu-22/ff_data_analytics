# dim_pick Rebuild - Implementation Summary

**Date**: 2025-11-07
**Status**: Parser updated, ready for re-ingestion

______________________________________________________________________

## Problem Statement

The original `dim_pick` seed contained only base picks (P01-P12), missing **56+ compensatory picks** and **33 TBD picks**, causing **58 relationship test failures** in `fact_league_transactions`.

Investigation revealed the root cause:

- Commissioner Google Sheet "Pick" column contains **overall pick numbers** (1-60+)
- Parser was combining these with round numbers incorrectly
- Compensatory picks weren't being extracted from FAAD awards

______________________________________________________________________

## Solution Overview

### Three-Part Approach

1. **Preserve raw data in parser** (Python)

   - Extract `pick_season`, `pick_round`, `pick_overall_number` separately
   - Store `pick_id_raw` (uncorrected format like `2024_R2_P23`)
   - No logic - just parse what's there

2. **Build complete dim_pick** (dbt)

   - Generate base picks (P01-P12)
   - Extract compensatory picks from FAAD awards
   - Sequence by FAAD chronological order
   - Calculate correct `overall_pick` numbers accounting for all comps

3. **Match and canonicalize** (dbt)

   - Match transaction pick references to dim_pick by `overall_pick` number
   - Replace `pick_id_raw` with canonical `pick_id`
   - Full validation and audit trail

______________________________________________________________________

## Implementation Status

### ✅ Completed

#### Phase 1-5: dim_pick Model

- **int_pick_base.sql**: Generates 1,140 base picks (12 teams × 5 rounds × 19 years)
- **int_pick_comp_registry.sql**: Parses FAAD compensation awards (85 comp picks found)
- **int_pick_comp_sequenced.sql**: Sequences comp picks chronologically by transaction_id
- **int_pick_tbd.sql**: Extracts TBD picks from transactions (33 found)
- **dim_pick.sql**: Assembles all picks, calculates correct `overall_pick` numbers
- **\_dim_pick.yml**: Comprehensive tests and documentation

**Results:**

- Total picks: 1,258 (1,140 base + 85 comp + 33 TBD)
- Grain test: ✅ PASS (pick_id unique)
- Comp picks successfully extracted from `faad_ufa_signing` transactions

#### Phase 6: Parser Updates

- **commissioner_parser.py**: Updated `_parse_pick_id()` to return dict with:
  - `pick_season`: Draft year
  - `pick_round`: Round number from sheet
  - `pick_overall_number`: Overall pick number (1-60+) from sheet
  - `pick_id_raw`: Uncorrected combined format
- **stg_sheets\_\_transactions.sql**: Updated to expose new pick fields
- **Tested**: Parser correctly extracts all fields

### 🔄 Pending

#### Step 1: Re-ingest Commissioner Sheets

```bash
make ingest-sheets
```

This will regenerate transactions with the new pick fields (`pick_season`, `pick_round`, `pick_overall_number`, `pick_id_raw`).

#### Step 2: Create int_pick_transaction_xref Model

**File**: `dbt/ff_analytics/models/core/intermediate/int_pick_transaction_xref.sql`

```sql
-- Match transaction pick references to canonical dim_pick pick_ids
with transaction_picks as (
    select
        transaction_id_unique,
        asset_type,
        pick_season,
        pick_round,
        pick_overall_number,
        pick_id_raw,
        pick_id as pick_id_original  -- For backward compat
    from {{ ref('stg_sheets__transactions') }}
    where asset_type = 'pick'
),

canonical_picks as (
    select
        pick_id,
        season,
        round,
        overall_pick,
        slot_number,
        pick_type,
        is_compensatory
    from {{ ref('dim_pick') }}
    where pick_type != 'tbd'  -- Match on finalized picks only
),

matched as (
    select
        tp.transaction_id_unique,
        tp.pick_season,
        tp.pick_round,
        tp.pick_overall_number,
        tp.pick_id_raw,
        tp.pick_id_original,

        -- Canonical pick from dim_pick
        cp.pick_id as pick_id_canonical,
        cp.overall_pick as overall_pick_canonical,
        cp.slot_number,
        cp.pick_type,
        cp.is_compensatory,

        -- Validation flags
        tp.pick_overall_number = cp.overall_pick as is_overall_match,
        tp.pick_id_raw = cp.pick_id as is_raw_id_match,
        cp.pick_id is not null as has_canonical_match

    from transaction_picks tp
    left join canonical_picks cp
        on tp.pick_season = cp.season
        and tp.pick_round = cp.round
        and tp.pick_overall_number = cp.overall_pick
),

-- Handle TBD picks separately
tbd_picks as (
    select
        tp.transaction_id_unique,
        tp.pick_season,
        tp.pick_round,
        tp.pick_overall_number,
        tp.pick_id_raw,
        tp.pick_id_original,

        -- TBD picks match on season/round only
        tbd.pick_id as pick_id_canonical,
        tbd.overall_pick as overall_pick_canonical,
        tbd.slot_number,
        tbd.pick_type,
        tbd.is_compensatory,

        -- TBD picks always have NULL overall match
        cast(null as boolean) as is_overall_match,
        tp.pick_id_raw = tbd.pick_id as is_raw_id_match,
        tbd.pick_id is not null as has_canonical_match

    from transaction_picks tp
    inner join {{ ref('dim_pick') }} tbd
        on tp.pick_season = tbd.season
        and tp.pick_round = tbd.round
        and tbd.pick_type = 'tbd'
    where tp.pick_overall_number is null  -- Only for TBD transactions
)

select * from matched
where pick_overall_number is not null  -- Finalized picks

union all

select * from tbd_picks  -- TBD picks
```

#### Step 3: Add Validation Tests

**Test 1**: All transactions match (`tests/assert_all_transaction_picks_matched.sql`)

```sql
select
    transaction_id_unique,
    pick_id_raw,
    pick_overall_number,
    'No canonical match found' as issue
from {{ ref('int_pick_transaction_xref') }}
where not has_canonical_match
```

**Test 2**: Overall pick numbers align (`tests/assert_pick_overall_numbers_match.sql`)

```sql
select
    transaction_id_unique,
    pick_id_raw,
    pick_overall_number,
    overall_pick_canonical,
    'Overall pick mismatch' as issue
from {{ ref('int_pick_transaction_xref') }}
where not is_overall_match
    and pick_overall_number is not null  -- Exclude TBD
```

**Test 3**: Audit raw vs canonical differences (`tests/assert_pick_id_corrections_documented.sql`)

```sql
-- This test documents all pick_id corrections (WARN level)
select
    pick_id_raw,
    pick_id_canonical,
    count(*) as transaction_count,
    'Raw pick_id differs from canonical' as note
from {{ ref('int_pick_transaction_xref') }}
where not is_raw_id_match
group by 1, 2
order by 3 desc
```

#### Step 4: Update fact_league_transactions

**File**: `dbt/ff_analytics/models/core/fact_league_transactions.sql`

Add join to pick xref and use canonical pick_id:

```sql
with pick_xref as (
    select
        transaction_id_unique,
        pick_id_canonical
    from {{ ref('int_pick_transaction_xref') }}
),

base_transactions as (
    select
        t.*,
        px.pick_id_canonical
    from {{ ref('stg_sheets__transactions') }} t
    left join pick_xref px
        on t.transaction_id_unique = px.transaction_id_unique
        and t.asset_type = 'pick'
)

select
    -- Use canonical pick_id for pick assets
    case
        when asset_type = 'pick' then coalesce(pick_id_canonical, pick_id)
        else pick_id
    end as pick_id,

    -- ... rest of columns ...
from base_transactions
```

#### Step 5: Run Full Test Suite

```bash
# Rebuild all models
make dbt-run

# Run all tests
make dbt-test

# Expected results:
# - dim_pick grain test: PASS
# - All transaction picks matched: PASS
# - Overall pick alignment: PASS
# - Relationship tests: 0 failures (down from 58!)
```

______________________________________________________________________

## Key Insights from Investigation

### Compensatory Pick Mechanics

Per League Constitution Section XI.M-N:

1. **Trigger**: RFA signs with different team in FAAD
2. **Round assignment**: Based on contract AAV
   - $25+/year → R1 comp
   - $15-24/year → R2 comp
   - $10-14/year → R3 comp
3. **Sequencing**: Chronological FAAD transaction order
   - First RFA signing → P13 in that round
   - Second RFA signing → P14 in that round
4. **Placement**: All comp picks at END of round (after P12)

### Pick ID Format

**Canonical format**: `YYYY_R#_P##`

- `YYYY`: Draft year
- `R#`: Round (1-5)
- `P##`: Slot number within round (01-60+)

**Examples**:

- `2024_R1_P01`: First overall pick (worst team)
- `2024_R1_P13`: 13th pick in R1 (first comp pick)
- `2024_R2_P01`: 18th overall (first pick in R2, assuming 17 R1 picks)

### Overall Pick Calculation

With compensatory picks, rounds have variable lengths:

```
2024 Example:
- R1: 12 base + 5 comp = 17 picks (overall 1-17)
- R2: 12 base + 2 comp = 14 picks (overall 18-31)
- R3: 12 base + 4 comp = 16 picks (overall 32-47)
- etc.
```

**Critical**: Must count comp picks in prior rounds to calculate correct overall pick numbers!

______________________________________________________________________

## Data Quality Findings

### Known Issues Resolved

1. **✅ Missing comp picks**: Now extracted from FAAD awards (85 found vs 56 expected)
2. **✅ Missing TBD picks**: Now extracted from transactions (33 found)
3. **✅ Pick ID format**: Now preserves overall pick number for matching

### Known Issues Remaining (will be fixed after re-ingestion)

1. **JP Jessie Bates comp**: FAAD shows R3 ($10/yr), draft_picks shows R2
   - Will be flagged by AAV validation test
2. **2024 R2 extra comp**: Expected 1, found 2
   - Need to investigate contract values for 2023 FAAD R3 awards
3. **2021 R3/R4 swap**: One comp misclassified between adjacent rounds
   - Will be identified by overall pick matching

### Validation Strategy

All issues will be **validated and documented** via dbt tests:

- Mismatches flagged as WARN (not ERROR)
- Audit trail preserved (raw vs canonical pick_ids)
- Manual investigation for edge cases

______________________________________________________________________

## Success Metrics

### Before

- Relationship test failures: **58**
- dim_pick rows: 1,140 (base picks only)
- Compensatory picks: 0
- TBD picks: 0

### After (Expected)

- Relationship test failures: **0**
- dim_pick rows: 1,258 (base + comp + TBD)
- Compensatory picks: 85
- TBD picks: 33
- All transaction picks matched: ✅
- Overall pick alignment: ✅

______________________________________________________________________

## Next Steps for User

1. **Run re-ingestion**: `make ingest-sheets`
2. **Create xref model**: Implement `int_pick_transaction_xref.sql`
3. **Add validation tests**: Implement the 3 tests above
4. **Update fact table**: Modify `fact_league_transactions.sql`
5. **Run full suite**: `make dbt-run && make dbt-test`
6. **Review results**: Check audit trail for any remaining issues

______________________________________________________________________

## References

- **Investigation report**: `docs/investigations/comp_pick_investigation_2025-11-07.md`
- **Implementation plan**: `docs/investigations/dim_pick_rebuild_plan_2025-11-07.md`
- **2026 comp picks reference**: `docs/investigations/2026_comp_picks_reference.md`
- **League constitution**: `dbt/ff_analytics/seeds/league_constitution.csv`
- **Kimball modeling guide**: `docs/spec/kimball_modeling_guidance/kimbal_modeling.md`
