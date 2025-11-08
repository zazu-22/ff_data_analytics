# dim_pick Rebuild Solution - Dual-Source Architecture

**Date**: 2025-11-07
**Status**: Design Complete - Ready for Implementation
**Context**: Continuation of dim_pick rebuild work from previous session

______________________________________________________________________

## Problem Summary

The original dim_pick rebuild attempted to reconstruct picks from FAAD Comp awards, but this approach had critical flaws:

### Issue 1: 10 Unmatched Transaction Picks

- Transactions referenced picks like "2024 R2 P21" that don't exist in dim_pick
- Example: Transaction 3170/3174 reference 2024_R2_P21, but R2 starts at overall pick 22
- Caused 10 relationship test warnings in fact_league_transactions

### Issue 2: FAAD Comp Column ≠ Actual Draft

Comparison for 2024 draft:

| Source               | R1 Comp | R2 Comp | R3 Comp | Total  |
| -------------------- | ------- | ------- | ------- | ------ |
| **Actual Draft**     | 5       | **2**   | 4       | **11** |
| **FAAD Comp Column** | 5       | **1**   | 4       | **10** |
| **AAV Calculation**  | 5       | **3**   | 2       | **10** |

**Key Finding**: The actual 2024 draft has **1 more R2 comp pick** than the FAAD Comp column accounts for.

### Issue 3: AAV Calculation Overcounts Massively

Historical analysis (2020-2023):

- FAAD Comp column: 33 total comp picks
- AAV calculation: 85 predicted (**+158% error**)

**Why AAV fails:**

1. Includes **extensions** (same team re-signings) - 52 high-value extensions didn't get comp picks
2. Includes **waiver signings** (released players) - No comp for cut players
3. Misses **commissioner discretion** - Thresholds are guidelines, not strict rules

### Root Cause Analysis

After extensive investigation, we discovered:

1. **Our dim_pick had wrong comp pick counts**:

   - 2024 R1: Had 21 picks (should be 17) → We had 9 comp picks (should be 5)
   - 2024 R2: Had 14 picks (correct) → We had 2 comp picks (correct)
   - 2024 R3: Had 17 picks (should be 16) → We had 5 comp picks(should be 4)

2. **We were using FAAD Comp column values incorrectly**:

   - Michael Pittman Jr: FAAD says "3rd" but $15.2/yr AAV → should be R2
   - Chris Godwin: FAAD says "3rd" but $17.0/yr AAV → should be R2
   - We used the FAAD column round (R3) instead of AAV-based correction (R2)

3. **We had a duplication bug**:

   - Chris Godwin appeared TWICE in dim_pick (2024_R3_P16 and P17)
   - Only 1 FAAD transaction exists
   - Bug in our sequencing logic created duplicates

4. **The actual rookie_draft_selection transactions are authoritative**:

   - They show what ACTUALLY happened in the draft
   - They reflect commissioner decisions, discretion, and corrections
   - FAAD Comp column has data entry errors and is incomplete

______________________________________________________________________

## Decision: Dual-Source Architecture

**Use actual draft as ground truth when available, with FAAD comp as fallback for future years.**

### Key Principles

1. **Historical Years (2012-2024)**: Extract picks from `rookie_draft_selection` transactions

   - This is what actually happened
   - Accounts for commissioner decisions and corrections
   - No reconstruction needed

2. **Prospective Years (2025+)**: Use FAAD Comp awards to project picks

   - Draft hasn't happened yet, so use FAAD projections
   - Transition to actual picks when draft occurs

3. **Reconciliation Layer**: Match FAAD awards to actual draft picks

   - Track both `faad_transaction_id` and `draft_transaction_id`
   - Flag mismatches for investigation
   - Maintain full lineage for comp picks

______________________________________________________________________

## Proposed Solution Architecture

### Data Flow

```text
┌─────────────────────────────────────────────────────────────────┐
│                    HISTORICAL (2012-2024)                       │
│                    Source: Actual Draft                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ↓
    rookie_draft_selection transactions
    (transaction_type_refined = 'rookie_draft_selection')
                              │
                              ↓
              int_pick_draft_actual.sql
              - Extract round, overall_pick from "Round", "Pick" columns
              - Calculate slot_number within round (ROW_NUMBER)
              - Classify as base (slot 1-12) or comp (slot 13+)
              - Track draft_transaction_id
                              │
                              ↓
                        dim_pick.sql
                        (with draft_transaction_id)

┌─────────────────────────────────────────────────────────────────┐
│                   PROSPECTIVE (2025+)                           │
│                   Source: FAAD Comp Awards                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ↓
              FAAD Comp column
              (from prior year's FAAD transactions)
                              │
                              ↓
              int_pick_comp_registry.sql
              - Parse "FAAD Comp" (e.g., "1st to Joe")
              - Extract season, round, recipient
              - Track faad_transaction_id
                              │
                              ↓
              int_pick_comp_sequenced.sql
              - Sequence by chronological FAAD order
              - Assign slot_number = 12 + sequence
              - Generate pick_id
                              │
                              ↓
              int_pick_base.sql
              (generate base picks P01-P12)
                              │
                              ↓
                        dim_pick.sql
                        (with faad_transaction_id)

┌─────────────────────────────────────────────────────────────────┐
│                   RECONCILIATION LAYER                          │
│              Match FAAD Awards → Draft Picks                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ↓
          int_pick_comp_reconciliation.sql
          - FULL OUTER JOIN faad awards with actual comp picks
          - Match by (season, round, chronological_sequence)
          - Flag: MATCHED, FAAD_AWARD_NOT_DRAFTED, DRAFTED_WITHOUT_FAAD_AWARD
          - Track both faad_transaction_id AND draft_transaction_id
                              │
                              ↓
                  Reconciliation Test
                  (assert mismatches < threshold)
```

### Model Breakdown

#### **New Model 1: `int_pick_draft_actual.sql`**

Extracts actual picks from completed drafts.

**Source**: `rookie_draft_selection` transactions (2012-2024)

**Key Logic**:

```sql
-- Extract from actual draft
SELECT
    transaction_id as draft_transaction_id,
    CAST("Round" AS INTEGER) as round,
    CAST("Pick" AS INTEGER) as overall_pick,
    "Player" as player_drafted
FROM transactions
WHERE transaction_type_refined = 'rookie_draft_selection'
    AND season <= 2024

-- Calculate slot within round
ROW_NUMBER() OVER (PARTITION BY season, round ORDER BY overall_pick) as slot_number

-- Classify pick type
CASE WHEN slot_number <= 12 THEN 'base' ELSE 'compensatory' END as pick_type
```

**Output Fields**:

- `pick_id`: Canonical format (e.g., `2024_R2_P06`)
- `season`, `round`, `overall_pick`, `slot_number`
- `pick_type`: 'base' or 'compensatory'
- `draft_transaction_id`: Link to transaction
- `player_drafted`: Who was selected
- `drafted_by_team`: Which team made the pick

#### **New Model 2: `int_pick_comp_reconciliation.sql`**

Matches FAAD comp awards to actual draft comp picks.

**Purpose**: Two-way reconciliation between FAAD projections and actual results

**Key Logic**:

```sql
-- Match by season, round, and chronological sequence
FROM faad_comp_awards fa
FULL OUTER JOIN actual_comp_picks ap
    ON fa.season = ap.season
    AND fa.round = ap.round
    AND fa.faad_chronological_seq = ap.comp_sequence_in_round

-- Reconciliation status
CASE
    WHEN both exist AND sequences match THEN 'MATCHED'
    WHEN FAAD exists but no draft pick THEN 'FAAD_AWARD_NOT_DRAFTED'
    WHEN draft pick exists but no FAAD award THEN 'DRAFTED_WITHOUT_FAAD_AWARD'
    WHEN both exist but sequences mismatch THEN 'SEQUENCE_MISMATCH'
END as reconciliation_status
```

**Output Fields**:

- `season`, `round`
- `faad_transaction_id`: FAAD award transaction
- `comp_source_player`: RFA that triggered comp pick
- `matched_pick_id`: Actual draft pick_id
- `matched_draft_transaction_id`: Draft selection transaction
- `matched_player_drafted`: Who was actually drafted with this comp pick
- `reconciliation_status`: Match quality flag

**Use Cases**:

1. **Populate comp metadata for historical picks** (who triggered the comp pick)
2. **Identify data quality issues** (like the missing 2024 R2 comp)
3. **Validate FAAD projections** against actual results
4. **Audit trail** for comp pick lifecycle

#### **Updated Model 3: `dim_pick.sql`**

Unified pick dimension combining all sources.

**Structure**:

```sql
-- Historical picks (2012-2024): Use actual draft
SELECT * FROM int_pick_draft_actual
LEFT JOIN int_pick_comp_reconciliation  -- Add FAAD metadata

UNION ALL

-- Prospective comp picks (2025+): Use FAAD projections
SELECT * FROM int_pick_comp_sequenced
WHERE season > 2024

UNION ALL

-- Prospective base picks (2025+): Generate standard picks
SELECT * FROM int_pick_base
WHERE season > 2024
```

**New Fields**:

- `is_prospective`: BOOLEAN - TRUE if pick hasn't been drafted yet
- `draft_transaction_id`: Link to rookie_draft_selection transaction
- `faad_transaction_id`: Link to FAAD award transaction
- `reconciliation_status`: For historical comps, match quality

______________________________________________________________________

## Expected Outcomes

### 1. **Resolve 10 Unmatched Transaction Picks**

**Current State** (using FAAD reconstruction):

- 10 picks referenced in transactions don't exist in dim_pick
- Examples: 2024_R2_P21, 2021_R3_P33, etc.
- Test shows: `relationships_fact_league_transactions_pick_id` → 10 warnings

**After Fix** (using actual draft):

- dim_pick will contain the ACTUAL picks that were drafted
- Transaction references will match real picks
- Test should show: `relationships_fact_league_transactions_pick_id` → **0-2 warnings** (only true data errors)

### 2. **Correct Pick Counts by Round**

**2024 Example - Before** (FAAD reconstruction):

| Round | dim_pick Count | Actual Draft Count | Delta        |
| ----- | -------------- | ------------------ | ------------ |
| R1    | 21             | 17                 | **+4 extra** |
| R2    | 14             | 14                 | ✅           |
| R3    | 17             | 16                 | **+1 extra** |
| R4    | 12             | 12                 | ✅           |

**2024 Example - After** (actual draft):

| Round | dim_pick Count | Actual Draft Count | Delta          |
| ----- | -------------- | ------------------ | -------------- |
| R1    | 17             | 17                 | ✅ **Perfect** |
| R2    | 14             | 14                 | ✅             |
| R3    | 16             | 16                 | ✅ **Perfect** |
| R4    | 12             | 12                 | ✅             |

### 3. **Identify FAAD Data Quality Issues**

The reconciliation model will flag:

- **2024 R2 mystery pick**: Draft has 2 comp picks, FAAD shows only 1
- **Michael Pittman/Chris Godwin**: FAAD says "3rd" but AAV suggests "2nd"
- **Missing FAAD entries**: Any comp picks drafted without FAAD awards
- **Phantom FAAD awards**: Any FAAD awards that never resulted in draft picks

### 4. **Support Prospective Years**

For 2025+ drafts:

- Use FAAD Comp projections to create TBD picks
- When draft happens, update to actual picks
- Reconciliation shows how accurate FAAD projections were

______________________________________________________________________

## Implementation Checklist

### Phase 1: Create New Models

- [ ] Create `int_pick_draft_actual.sql` (extract from rookie_draft_selection)
- [ ] Update `int_pick_comp_registry.sql` (ensure faad_transaction_id tracked)
- [ ] Create `int_pick_comp_reconciliation.sql` (match FAAD to actual)
- [ ] Update `int_pick_base.sql` (only for prospective years >2024)
- [ ] Update `int_pick_comp_sequenced.sql` (only for prospective years >2024)
- [ ] Update `int_pick_tbd.sql` (only for prospective years >2024)

### Phase 2: Rebuild dim_pick

- [ ] Update `dim_pick.sql` with dual-source logic
- [ ] Add `is_prospective`, `draft_transaction_id`, `faad_transaction_id` columns
- [ ] Update `_dim_pick.yml` with new column documentation
- [ ] Add `reconciliation_status` for historical comps

### Phase 3: Testing & Validation

- [ ] Create `assert_faad_comp_awards_reconciled.sql` test
- [ ] Run `dbt run --select dim_pick+`
- [ ] Verify pick counts match actual draft for each year 2012-2024
- [ ] Check reconciliation_status distribution (expect >95% MATCHED)
- [ ] Verify `int_pick_transaction_xref` now matches all picks
- [ ] Run full test suite: `dbt test`
- [ ] Confirm relationship test failures drop from 10 to 0-2

### Phase 4: Documentation

- [ ] Update ADR-008 with dual-source architecture decision
- [ ] Document reconciliation_status flags and meanings
- [ ] Create data quality report for FAAD vs actual mismatches
- [ ] Update dim_pick model documentation in `_dim_pick.yml`

______________________________________________________________________

## Key Design Decisions

### 1. **Why Not Use AAV Calculation?**

- ❌ Overcounts by 158% (includes extensions and waiver signings)
- ❌ Doesn't account for commissioner discretion
- ❌ Constitution thresholds are guidelines, not strict rules
- ✅ FAAD Comp column is 100% reliable for 2020-2023

### 2. **Why Not Trust FAAD Comp Column Alone?**

- ❌ 2024 has data entry error (missing 1 R2 comp pick)
- ❌ Some entries have wrong rounds (Pittman/Godwin show "3rd" should be "2nd")
- ❌ Incomplete metadata (doesn't track who was drafted with comp pick)
- ✅ Actual draft is what actually happened

### 3. **Why Full Outer Join in Reconciliation?**

- ✅ Catches FAAD awards that weren't drafted (data quality issue)
- ✅ Catches draft comp picks without FAAD awards (missing documentation)
- ✅ Provides complete audit trail
- ✅ Enables validation of FAAD projection accuracy over time

### 4. **Why Track Both Transaction IDs?**

- ✅ Full lineage: FAAD award → Draft selection
- ✅ Can trace comp pick lifecycle (awarded → traded → drafted)
- ✅ Supports analysis: "Who benefited from losing Player X?"
- ✅ Enables validation queries joining to source transactions

______________________________________________________________________

## Open Questions for Next Session

1. **Pick Numbering Edge Case**:

   - When a comp pick is traded before draft, does the pick_id change?
   - Example: 2026 R2 comp (Mahomes) traded as "2026_R2_P30" - is P30 tentative?

2. **TBD Transition Logic**:

   - How should TBD picks transition to actual picks when draft happens?
   - Update in place, or create new row and archive TBD?

3. **Historical Years with Missing Draft Data**:

   - Do we have complete rookie_draft_selection data for 2012-2019?
   - If not, fall back to FAAD for those years?

4. **Reconciliation Threshold**:

   - How many FAAD/actual mismatches are acceptable?
   - Current: 1 mismatch in 2024 (R2 mystery pick)
   - Should test WARN or ERROR on mismatches?

______________________________________________________________________

## Related Documents

- **Previous Session Status**: `docs/investigations/dim_pick_status_2025-11-07.md`
- **ADR-008**: `docs/adr/ADR-008-pick-identity-resolution-via-overall-pick-number.md`
- **Comp Pick Investigation**: `docs/investigations/comp_pick_investigation_2025-11-07.md`
- **League Constitution**: `docs/spec/league_constitution.csv` (Sections XI.M-N)
- **Implementation Summary**: `docs/investigations/dim_pick_implementation_summary_2025-11-07.md`

______________________________________________________________________

## Next Steps

1. **Start with int_pick_draft_actual.sql** - This is the foundation
2. **Test on 2024 draft** - Verify pick counts match before expanding to all years
3. **Build reconciliation model** - Identify all FAAD/actual mismatches
4. **Rebuild dim_pick** - Switch to dual-source architecture
5. **Run full test suite** - Confirm relationship test failures resolved

**Estimated Effort**: 2-3 hours to implement all models and tests
**Expected Impact**: Resolve all 10 unmatched pick warnings, establish reliable pick dimension for future years
