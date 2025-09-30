# ADR-008: League Transaction History Integration

**Status:** Accepted
**Date:** 2025-09-29
**Decision Makers:** Jason Shaffer, Development Team

## Context

The Commissioner Google Sheet contains a **TRANSACTIONS tab** with approximately 1,000 rows documenting the complete history of league transactions since inception. This includes trades, cuts, waiver claims, free agent signings, and Free Agent Auction Draft (FAAD) signings.

### Problem Statement

The refined data model plan v4.0 included commissioner sheets ingestion for **roster snapshots** (active contracts, cut contracts, draft picks) but did not account for the TRANSACTIONS tab. Roster snapshots show current state only, missing:

- **Multi-asset trades**: Players, draft picks, and cap space exchanged between franchises
- **Transaction parties**: Who gave what to whom
- **Historical audit trail**: When each transaction occurred
- **Contract terms at signing**: What contracts were when players were acquired
- **Trade valuation context**: Actual trades to compare against KTC market values

### Transaction Types in Source Data

1. **Trade**: Multi-row transactions (grouped by Sort ID) involving players, picks, cap space
1. **Cut**: Player releases with dead cap implications
1. **Waivers**: GM-to-GM waiver claims
1. **Signing**: Free agent acquisitions from waiver wire
1. **FAAD**: Annual free agent auction draft signings

### Constraints

- Raw TRANSACTIONS tab matches the asset-per-row grain (same as trades are recorded)
- Player names must be mapped to canonical `player_id` (requires `dim_player_id_xref` seed)
- Draft picks must reference `dim_pick` (requires seed)
- Multi-asset trades must be grouped by transaction ID
- Must preserve historical fidelity (no summarization at ingestion)

## Decision

Implement a **league transaction history fact table** that captures the complete commissioner-recorded transaction log:

### `fact_league_transactions`

**Grain:** One row per asset per transaction (matches raw TRANSACTIONS tab structure)

**Schema:**

```sql
fact_league_transactions(
  transaction_id,        -- from Sort column; groups multi-asset trades
  transaction_date,
  transaction_year,      -- partition key
  transaction_type,      -- enum: trade, cut, waivers, signing, faad
  from_franchise_id,     -- nullable; 'Waiver Wire' for FA signings
  to_franchise_id,       -- nullable; 'Waiver Wire' for cuts
  asset_type,            -- enum: player, pick, cap_space

  -- Asset references (nullable based on asset_type)
  player_id,             -- FK to dim_player (when asset_type=player)
  pick_id,               -- FK to dim_pick (when asset_type=pick)

  -- Contract details (when applicable)
  contract_years,
  contract_total,
  contract_split,        -- JSON array of year splits
  rfa_matched,
  franchise_tag,
  faad_compensation,

  -- Metadata
  source_row_hash,
  dt                     -- partition from raw load
)
```

### Integration Architecture

```
Commissioner Sheet TRANSACTIONS tab
    ↓ [raw copy via ADR-005]
samples/sheets/TRANSACTIONS/TRANSACTIONS.csv
    ↓ [parser: commissioner_parser.py]
data/raw/commissioner/transactions/dt=YYYY-MM-DD/
    ↓ [staging: stg_sheets__transactions]
Normalized with player_id mapping
    ↓ [core: fact_league_transactions]
Partitioned fact table
    ↓
Trade analysis marts:
  - mart_trade_history (franchise-level summaries)
  - mart_trade_valuations (actual vs KTC market)
  - mart_roster_timeline (reconstruct rosters)
```

### New Marts Enabled

1. **`mart_trade_history`** - Aggregated trade summaries by franchise

   - Total trades, players/picks acquired/sent, cap transfers
   - Window functions to show trade patterns over time
   - "Who is the most active trader?"

1. **`mart_trade_valuations`** - Actual trades vs KTC market comparison

   - Join `fact_league_transactions` (asset_type=player) to `fact_asset_market_values`
   - Calculate trade value differential (market vs actual)
   - Identify value wins/losses per franchise
   - "Did I win or lose that trade based on market values?"

1. **`mart_roster_timeline`** - Reconstruct roster state at any point in time

   - Window functions over transaction history ordered by transaction_date
   - Current roster = initial state + cumulative transactions
   - "What was my roster on 2024-10-15?"

## Consequences

### Positive

- **Complete audit trail**: Full history of league transactions from inception
- **Multi-asset trades preserved**: Grouped by transaction_id; can reconstruct entire trades
- **Trade analysis enabled**: Compare actual trades to market values (KTC)
- **Roster reconstruction**: Can derive roster state at any historical point
- **Contract context**: Captures contract terms at time of signing/trade
- **Valuation accuracy**: Actual trade data improves understanding of player values in league context
- **Temporal analysis**: Track trading patterns, franchise strategies over time

### Negative

- **Additional parsing complexity**: TRANSACTIONS tab has more complex structure than roster tabs
- **Seed dependency**: Blocked by `dim_player_id_xref`, `dim_pick`, `dim_asset` seeds
- **Name mapping challenges**: Player names in TRANSACTIONS must map to canonical IDs
- **Data quality**: Historical data may have inconsistencies or name variations
- **Storage**: ~1,000 rows per snapshot; grows with league history

### Neutral

- **Parallel implementation**: Independent of NFL stats (Track A) and projections (Track D)
- **Complementary to roster snapshots**: Both provide different views of roster state
- **Asset-level grain**: Matches natural transaction recording pattern

## Alternatives Considered

### 1. Rely Solely on Roster Snapshots

**Description:** Only ingest current roster state from roster/contracts tabs; derive changes from snapshots.

**Rejected because:**

- Loses transaction context (who traded with whom)
- Cannot reconstruct historical rosters accurately
- Missing contract terms at signing (only shows current/cut contracts)
- No multi-asset trade grouping
- Cannot validate roster changes against actual transactions
- No audit trail for manual corrections

### 2. Store Only Trade Summaries

**Description:** Aggregate multi-asset trades into single rows with JSON arrays.

**Rejected because:**

- Complicates queries (unnesting JSON for analysis)
- Harder to join to player/pick dimensions
- Less flexible for different analysis patterns
- Raw grain is already asset-per-row; no benefit to aggregating

### 3. Separate Facts by Transaction Type

**Description:**

```sql
fact_trades
fact_cuts
fact_waivers
fact_signings
```

**Rejected because:**

- Overly granular (4+ facts for related data)
- Union queries required for complete history
- Shared schema would duplicate across tables
- Transaction type is a natural dimension, not a grain change

### 4. Derive from Sleeper API Transactions

**Description:** Use Sleeper's transaction API as source of truth instead of commissioner sheet.

**Rejected because:**

- Sleeper data is current season only (no historical backfill)
- Commissioner sheet is authoritative for dynasty league
- Contract details are not in Sleeper (sheet-specific)
- FAAD and some waivers are recorded differently
- Would require reconciliation between sources anyway

## Implementation Notes

### Key Dependencies

**BLOCKER - Phase 1 Seeds:**

- `dim_player_id_xref` - Maps player names to canonical `player_id`
- `dim_name_alias` - Handles alternate names/spelling variations
- `dim_pick` - Draft pick dimension for pick assets
- `dim_asset` - Unified player/pick/cap asset catalog
- `dim_franchise` - League team/owner dimension

### Parsing Strategy

```python
# src/ingest/sheets/commissioner_parser.py
def parse_transactions(csv_path: Path) -> pl.DataFrame:
    """
    Parse TRANSACTIONS tab to normalized format.

    Columns:
    - Time Frame → transaction_date (parse "2025 Week 4", "2024 Offseason")
    - From → from_franchise_id
    - To → to_franchise_id
    - Original Order, Round, Pick → pick details (when applicable)
    - Position, Player → player reference (when applicable)
    - Contract, Split → contract terms
    - RFA Matched, FAAD Comp → contract flags
    - Type → transaction_type
    - Sort → transaction_id (groups multi-asset trades)
    """
```

### Staging Model

```sql
-- models/staging/stg_sheets__transactions.sql
WITH base AS (
  SELECT * FROM {{ source('sheets_raw', 'transactions') }}
),
player_mapped AS (
  SELECT
    base.*,
    COALESCE(xref.player_id, -1) AS player_id
  FROM base
  LEFT JOIN {{ ref('dim_player_id_xref') }} xref
    ON base.player_name = xref.display_name
    OR base.player_name = xref.alias
  WHERE base.asset_type = 'player'
)
-- ... additional mapping for picks, validation
```

### Data Quality Tests

```yaml
# models/staging/schema.yml
- name: stg_sheets__transactions
  tests:
    - unique:
        column_name: (transaction_id, asset_type, player_id, pick_id)
    - not_null:
        column_name: transaction_date
    - not_null:
        column_name: transaction_id
    - accepted_values:
        column_name: transaction_type
        values: ['trade', 'cut', 'waivers', 'signing', 'faad']
    - accepted_values:
        column_name: asset_type
        values: ['player', 'pick', 'cap_space']
    - relationships:
        column_name: player_id
        to: ref('dim_player')
        field: player_id
        where: "asset_type = 'player'"
```

### Key Files

- `src/ingest/sheets/commissioner_parser.py` - Add `parse_transactions()` function
- `dbt/ff_analytics/models/staging/stg_sheets__transactions.sql` - Staging model
- `dbt/ff_analytics/models/core/fact_league_transactions.sql` - Core fact
- `dbt/ff_analytics/models/marts/mart_trade_history.sql` - Trade summaries
- `dbt/ff_analytics/models/marts/mart_trade_valuations.sql` - Actual vs market
- `dbt/ff_analytics/models/marts/mart_roster_timeline.sql` - Historical rosters

## References

- **SPEC-1 v2.2**: Trade Valuation section - [`docs/spec/SPEC-1_v_2.2.md`](../spec/SPEC-1_v_2.2.md)
- **Refined Data Model Plan v4.0**: v4.2 addendum - [`docs/spec/refined_data_model_plan_v4.md`](../spec/refined_data_model_plan_v4.md)
- **Implementation Checklist**: Section 4 (Sheets) and Section 7 (dbt) - [`docs/spec/SPEC-1_v_2.2_implementation_checklist_v_1.md`](../spec/SPEC-1_v_2.2_implementation_checklist_v_1.md)
- **Commissioner Parser**: Existing roster/contracts/picks parsing - [`src/ingest/sheets/commissioner_parser.py`](../../../src/ingest/sheets/commissioner_parser.py)
- **Kimball Modeling Guidance**: Fact table design patterns - [`docs/architecture/kimball_modeling_guidance/kimbal_modeling.md`](../architecture/kimball_modeling_guidance/kimbal_modeling.md)

## Decision Record

This decision was made during data model v4 review on 2025-09-29 when evaluating whether the TRANSACTIONS tab was adequately covered in the implementation plan. The gap was identified: roster snapshots alone cannot provide complete trade history or multi-asset transaction context.

**Approval:** Documented in `refined_data_model_plan_v4.md` as Addendum v4.2 - League Transaction History.

**Implementation Status:** Phase 1 (seeds) required before implementation. Part of Phase 2, Track B (League Data parallel track).

**Sample Data Available:** Raw TRANSACTIONS tab copied; ~1,000 rows at `samples/sheets/TRANSACTIONS/TRANSACTIONS.csv` (not yet parsed).
