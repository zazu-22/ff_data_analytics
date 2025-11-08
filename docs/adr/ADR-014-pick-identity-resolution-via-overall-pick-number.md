# ADR-014: Pick Identity Resolution via Overall Pick Number

**Status**: Accepted
**Date**: 2025-11-07
**Deciders**: Jason (User), Claude (AI Assistant)
**Related**: ADR-005 (Server-Side Sheet Operations), SPEC-1 (Data Architecture)

______________________________________________________________________

## Context

The Commissioner Google Sheet tracks draft picks using two separate fields:

- **Round**: Draft round (1-5) parsed from "Player" column (e.g., "2024 2nd Round")
- **Pick**: Overall draft position (1-60+) in the "Pick" column (e.g., "23")

With compensatory picks awarded via FAAD (Free Agent Auction Draft), rounds have variable lengths:

- **Base picks**: P01-P12 per round (12-team league)
- **Comp picks**: P13+ per round (awarded for RFA losses, sequenced chronologically by FAAD transaction order)

**Example Draft Structure**:

```text
2024 Draft:
- R1: Picks 1-17  (12 base + 5 comp)
- R2: Picks 18-33 (12 base + 4 comp)
- R3: Picks 34-49 (12 base + 4 comp)
...
```

**The Problem**:

When transactions reference picks, the raw data shows:

- Round 2, Pick 23

This creates ambiguity:

1. Does "Pick 23" mean the 23rd pick in Round 2? (Impossible - only 12-16 picks per round)
2. Does "Pick 23" mean the 23rd overall pick in the draft? (Correct!)

The original parser (`commissioner_parser.py`) combined these incorrectly:

```python
pick_id = f"{season}_R{round}_P{pick_number}"  # "2024_R2_P23"
```

This created **phantom picks** that don't exist in the actual draft structure, causing 58 relationship test failures in `fact_league_transactions`.

**Investigation Revealed**:

- 56+ compensatory picks missing from `dim_pick` seed
- Pick numbering uses **overall draft position**, not within-round slots
- Parser had no way to calculate correct within-round slot numbers (circular dependency: need comp pick counts, but comp picks come from same transaction table)

______________________________________________________________________

## Decision

### Architecture: Parse Raw, Transform in dbt

We separate **data extraction** from **identity resolution**:

#### 1. Parser Layer (Python) - Raw Data Extraction

**Purpose**: Extract what's in the sheet, no transformation logic

**Implementation** (`commissioner_parser.py::_parse_pick_id()`):

```python
def _parse_pick_id(player_str: str | None, pick_col: str) -> dict | None:
    """Parse pick reference to structured pick information.

    Returns:
        dict with:
          - pick_season: Draft year (int)
          - pick_round: Round number from sheet (int)
          - pick_overall_number: Overall pick number (1-60+) from sheet (int)
          - pick_id_raw: Uncorrected combined format YYYY_R#_P## (str)
    """
    # Extract season and round from "YYYY Rnd Round" format
    # Extract overall pick number from Pick column AS-IS
    # Store pick_id_raw using overall number (will be corrected in dbt)
```

**Key Decision**: Store `pick_overall_number` separately as authoritative identifier

#### 2. dim_pick Layer (dbt) - Canonical Pick Dimension

**Purpose**: Generate complete pick inventory with correct sequencing

**Components**:

- `int_pick_base.sql` - Base picks (P01-P12) for all years/rounds
- `int_pick_comp_registry.sql` - Extract comp picks from FAAD Comp column
- `int_pick_comp_sequenced.sql` - Sequence comp picks by FAAD transaction order
- `int_pick_tbd.sql` - Extract TBD picks (future picks with unknown slot)
- `dim_pick.sql` - Assemble all picks, calculate overall_pick via ROW_NUMBER()

**Critical Calculation**:

```sql
ROW_NUMBER() OVER (
    PARTITION BY season
    ORDER BY round, slot_number
) AS overall_pick
```

This accounts for compensatory picks in prior rounds when calculating overall position.

#### 3. Crosswalk Layer (dbt) - Identity Resolution

**Purpose**: Match transaction pick references to canonical pick_ids

**Implementation** (`int_pick_transaction_xref.sql`):

```sql
-- Match on (season, round, overall_pick) - the authoritative triple
SELECT
    tp.transaction_id_unique,
    tp.pick_id_raw,              -- "2024_R2_P23"
    tp.pick_overall_number,      -- 23
    cp.pick_id AS pick_id_canonical,  -- "2024_R2_P06" (correct!)
    cp.overall_pick,             -- 23 (verified match)
    tp.pick_overall_number = cp.overall_pick AS is_overall_match
FROM transaction_picks tp
LEFT JOIN dim_pick cp
    ON tp.pick_season = cp.season
    AND tp.pick_round = cp.round
    AND tp.pick_overall_number = cp.overall_pick  -- THE KEY MATCH
```

**Key Decision**: Match on `overall_pick` number, which accounts for all comp picks

#### 4. Fact Layer (dbt) - Use Canonical IDs

**Purpose**: Replace raw pick_ids with canonical pick_ids from xref

**Implementation** (`fact_league_transactions.sql`):

```sql
SELECT
    -- Use canonical pick_id
    COALESCE(xref.pick_id_canonical, raw.pick_id) AS pick_id,
    ...
FROM stg_sheets__transactions raw
LEFT JOIN int_pick_transaction_xref xref USING (transaction_id_unique)
```

______________________________________________________________________

## Consequences

### Positive ✅

1. **Preserves Source Truth**

   - Raw sheet data unchanged in parser
   - Full audit trail (pick_id_raw vs pick_id_canonical)
   - Can trace every transformation

2. **Robust Identity Resolution**

   - Handles comp picks correctly (match by overall position)
   - No circular dependencies (comp counts known before matching)
   - Self-documenting (match_status flag shows quality)

3. **Fully Testable**

   - Validation at every layer (parse → dim → xref → fact)
   - Data quality flags (is_overall_match, has_canonical_match)
   - Mismatch audit trail for investigation

4. **Flexible & Maintainable**

   - Parser logic simple (just extraction)
   - All business logic in SQL (inspectable, testable)
   - Easy to fix issues (rebuild xref, not re-ingest)

5. **Self-Healing**

   - If dim_pick updated (new comp picks), xref automatically picks up changes
   - No re-parsing of historical data needed

### Negative ⚠️

1. **Additional Model Layer**

   - Adds `int_pick_transaction_xref` intermediate model
   - Increases model count (5 intermediate + 1 xref + 1 final)
   - Slightly more complex lineage

2. **Two Pick IDs in Flight**

   - `pick_id_raw` (from parser) and `pick_id_canonical` (from xref)
   - Must remember to use canonical in downstream models
   - Potential confusion for new developers

3. **Schema Evolution Challenges**

   - Adding new columns to Parquet requires careful partition management
   - dbt/DuckDB aggressive schema caching can cause issues
   - Best practice: Delete old partitions or use `union_by_name`

______________________________________________________________________

## Alternatives Considered

### Alternative 1: Calculate Slot in Parser

**Approach**: Parser calculates within-round slot from overall pick number

**Rejected Because**:

- **Circular dependency**: Need comp pick counts to calculate slots, but comp picks come from same transaction table being parsed
- **Timing issues**: Transactions may reference picks before all comps awarded (FAAD in progress)
- **Fragile**: Parser would need to know league rules, comp pick counts by year, etc.

**Code would look like**:

```python
# BAD: Parser needs to know comp pick counts
def calculate_slot(overall_pick, round, comp_counts):
    base_offset = sum(12 + comp_counts[r] for r in range(1, round))
    return overall_pick - base_offset
```

### Alternative 2: Unified Pick ID Format with Overall Number

**Approach**: Use pick_id format `YYYY_O##` (overall position only, no round)

**Rejected Because**:

- **Loses round information**: Round is meaningful for draft analysis
- **Breaks convention**: Existing pick_ids use `YYYY_R#_P##` format everywhere
- **Migration pain**: Would require updating all downstream code/queries

### Alternative 3: TBD-Only Approach (Don't Fix Comp Picks)

**Approach**: Only extract TBD picks, leave comp picks as "known data quality issue"

**Rejected Because**:

- **58 test failures**: Unacceptable technical debt
- **Incorrect analysis**: Queries joining on pick_id would fail for comp picks
- **No audit trail**: Couldn't trace which picks are comp picks vs base picks

______________________________________________________________________

## Implementation Notes

### Compensatory Pick Rules

Per League Constitution Section XI.M-N:

**Award Conditions**:

- RFA signs with different team in FAAD
- Original team receives comp pick in next draft

**Round Assignment** (by contract AAV):

- $25+/year → R1 comp
- $15-24/year → R2 comp
- $10-14/year → R3 comp

**Sequencing**:

- All comp picks at END of round (after P12)
- Ordered chronologically by FAAD transaction_id
- First RFA signing → P13, second → P14, etc.

**Example**:

```text
2024 FAAD RFA Signings:
1. D'Andre Swift → $30M/4yr → R1 comp to Alec
2. J.K. Dobbins → $28M/4yr → R1 comp to Gordon
3. Aaron Jones → $26M/4yr → R1 comp to Kevin

2024 Draft R1 Structure:
P01-P12: Base picks (standings order)
P13: Alec's comp (first RFA, transaction_id 2801)
P14: Gordon's comp (second RFA, transaction_id 2806)
P15: Kevin's comp (third RFA, transaction_id 2809)
```

### Data Quality Flags

The xref model provides comprehensive validation:

```sql
-- Validation columns
is_overall_match        BOOLEAN   -- Overall pick numbers align
is_raw_id_match         BOOLEAN   -- Raw and canonical pick_ids match
has_canonical_match     BOOLEAN   -- Found match in dim_pick
match_status            VARCHAR   -- Human-readable status

-- Status values
'EXACT MATCH'                    -- Base pick, no correction needed
'OVERALL MATCH (ID CORRECTED)'   -- Comp pick, ID fixed via matching
'TBD PICK'                       -- Future pick, no slot yet
'NO MATCH FOUND'                 -- ERROR - investigate!
```

### Testing Strategy

**Level 1:** Raw Data Tests

- Parser extracts all fields correctly
- pick_overall_number populated for finalized picks
- pick_id_raw combines season/round/overall

**Level 2:** dim_pick Tests

- Grain: pick_id unique
- Counts: 1,140 base + 85 comp + 33 TBD = 1,258
- Sequencing: overall_pick sequential within season
- Comp pick AAV: Round matches contract value threshold

**Level 3:** Crosswalk Tests

- All transactions match: has_canonical_match = TRUE for all
- Overall numbers align: is_overall_match = TRUE for finalized
- Mismatch audit: Count and document ID corrections

**Level 4:** Fact Tests

- Relationship: All pick_ids exist in dim_pick (0 failures, was 58)
- Grain: transaction_id_unique still unique
- Completeness: Row count unchanged

______________________________________________________________________

## Related Decisions

### ADR-005: Server-Side Sheet Operations

This ADR builds on ADR-005's principle of **preserving source fidelity**. The parser extracts raw data without transformation, deferring business logic to dbt where it's testable and transparent.

### SPEC-1: Data Architecture

This implementation follows SPEC-1's **medallion architecture**:

- **Bronze (Raw)**: Parser output with pick_overall_number
- **Silver (Staging)**: stg_sheets\_\_transactions passes through
- **Gold (Core)**: dim_pick + int_pick_transaction_xref resolve identity
- **Platinum (Marts)**: Facts use canonical pick_ids

### ADR-007: Separate Fact Tables for Actuals vs Projections

Similar reasoning: Don't force-fit incompatible grains. Here, we don't force the parser to calculate slots (wrong layer). Instead, we match in dbt where we have full context.

______________________________________________________________________

## Success Metrics

### Before

- dim_pick rows: 1,140 (base picks only)
- Relationship test failures: **58**
- Compensatory picks: 0
- Audit trail: None

### After

- dim_pick rows: **1,258** (base + comp + TBD)
- Relationship test failures: **0** (target)
- Compensatory picks: **85** extracted and sequenced
- Audit trail: Complete (raw → canonical mapping)

______________________________________________________________________

## References

- **Investigation**: `docs/investigations/comp_pick_investigation_2025-11-07.md`
- **Implementation**: `docs/investigations/dim_pick_implementation_summary_2025-11-07.md`
- **Status**: `docs/investigations/dim_pick_status_2025-11-07.md`
- **League Constitution**: `dbt/ff_data_transform/seeds/league_constitution.csv` (Section XI)
- **Code**:
  - `src/ingest/sheets/commissioner_parser.py::_parse_pick_id()`
  - `dbt/ff_data_transform/models/core/dim_pick.sql`
  - `dbt/ff_data_transform/models/core/intermediate/int_pick_transaction_xref.sql`

______________________________________________________________________

## Future Considerations

### When RFA Comp System Ends (2027+)

Per constitution, RFA comp picks end after 2026. When this happens:

- `int_pick_comp_registry` will return 0 rows for 2027+
- `dim_pick` will only have base + TBD picks for future years
- No code changes needed - system gracefully handles 0 comp picks

### If Sheet Format Changes

If the "Pick" column changes meaning (e.g., becomes within-round slot):

- Update parser to document new meaning
- Adjust xref matching logic to account for change
- Add version/timestamp flag to detect format transitions

### If League Size Changes

If league expands/contracts (e.g., 10 teams or 14 teams):

- Update `int_pick_base` to generate correct base pick count
- Matching logic remains unchanged (still based on overall_pick)
- May need year-specific team counts if change mid-history

______________________________________________________________________

## Lessons Learned

1. **Overall pick number is authoritative** - Don't try to derive it; match on it
2. **Parse raw, transform in dbt** - Keeps parser simple, dbt testable
3. **Circular dependencies are real** - Can't calculate slots without comp counts
4. **Schema evolution needs care** - Parquet schema caching can bite you
5. **Audit trails are essential** - Being able to see raw → canonical mapping is invaluable
6. **Trust the user's domain knowledge** - "It's overall pick number, not slot" unlocked the solution
