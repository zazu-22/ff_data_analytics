# TRANSACTIONS Kimball Modeling Strategy

**Date**: 2025-10-01
**Process**: League Transaction History (Commissioner Sheet TRANSACTIONS tab)
**Related Documents**:

- Profiling: `TRANSACTIONS_profiling_20251001.md`
- ADR-008: `docs/adr/ADR-008-league-transaction-history-integration.md`
- Kimball Guide: `docs/architecture/kimball_modeling_guidance/kimbal_modeling.md`

______________________________________________________________________

## Four-Step Kimball Design Process

### Step 1: Select Business Process

**Business Process**: League Transaction History

**Description**: Captures all asset movements (players, draft picks, cap space) between franchises, including trades, cuts, signings, waivers, draft selections, and contract actions.

**Source**: Commissioner Google Sheet TRANSACTIONS tab (authoritative source of truth for dynasty league)

**Business Value**:

- Historical audit trail for all league transactions
- Trade analysis (who won/lost based on market values)
- Roster reconstruction at any point in time
- Contract management and cap space tracking
- Multi-asset trade analysis

______________________________________________________________________

### Step 2: Declare the Grain

**Grain Statement**:

> **One row per asset per transaction per direction**

**Example**: A trade where Chip sends 2 players + 1 pick to James in exchange for 1 player + 2 picks creates **6 rows**:

- 3 rows: Chip → James (2 players, 1 pick)
- 3 rows: James → Chip (1 player, 2 picks)

**Grain Components**:

1. `transaction_id` — Unique identifier for each asset movement (from Sort column, cleaned)
1. `asset_type` — Player, pick, or cap_space
1. `player_id` — Nullable, populated only when asset_type='player'
1. `pick_id` — Nullable, populated only when asset_type='pick'

**Grain Validation**:

```sql
-- dbt test: unique combination
SELECT transaction_id, asset_type, player_id, pick_id
FROM fact_league_transactions
GROUP BY 1,2,3,4
HAVING COUNT(*) > 1;
-- Should return 0 rows
```

**Grain Type**: **Transaction Fact Table** (per Kimball guide p. 243-248)

- Event-driven (not periodic)
- Sparse (transactions happen irregularly)
- Immutable once recorded

______________________________________________________________________

### Step 3: Identify the Dimensions

#### Conformed Dimensions (Existing)

| Dimension       | Surrogate Key      | Type       | Cardinality   | Source                     |
| --------------- | ------------------ | ---------- | ------------- | -------------------------- |
| `dim_player`    | player_id (mfl_id) | SCD Type 1 | ~12,000       | nflverse ff_playerids      |
| `dim_pick`      | pick_id            | Static     | ~1,140        | Seed (2012-2030)           |
| `dim_franchise` | franchise_id       | SCD Type 2 | 12 franchises | Seed (ownership history)   |
| `dim_asset`     | asset_id           | Static     | ~13,000       | UNION of players + picks   |
| `dim_date`      | date_key           | Static     | ~10,950       | Generated (2009-2039)      |
| `dim_timeframe` | timeframe          | Static     | ~138          | Seed (season/week mapping) |

#### Role-Playing Dimensions

**dim_franchise** plays 2 roles:

- `from_franchise_id` → Franchise sending the asset
- `to_franchise_id` → Franchise receiving the asset

**Special handling**:

- "Waiver Wire" is represented as NULL franchise_id (not a dimension member)
- Cuts: from_franchise_id IS NOT NULL, to_franchise_id IS NULL
- Signings: from_franchise_id IS NULL, to_franchise_id IS NOT NULL
- Trades: Both IS NOT NULL

#### Degenerate Dimensions

Per Kimball guide (p. 408-422), transaction identifiers with no other attributes should be stored directly in fact table:

**Degenerate Dimensions**:

- `transaction_id` — No separate dim_transaction table
- `transaction_type` — Low-cardinality enum (9 values)
- `asset_type` — Low-cardinality enum (3 values: player, pick, cap_space)

**Rationale**: These have no descriptive attributes beyond their ID/code, so a separate dimension table adds no value.

#### Junk Dimension (Optional)

**Option A: Junk Dimension** `dim_transaction_profile`

```sql
CREATE TABLE dim_transaction_profile (
    transaction_profile_key INTEGER PRIMARY KEY,
    transaction_type VARCHAR,  -- Trade, Cut, Signing, etc.
    asset_type VARCHAR,        -- player, pick, cap_space
    -- All 27 valid combinations pre-populated
);
```

**Option B: Degenerate Dimensions** (RECOMMENDED)
Store `transaction_type` and `asset_type` directly in fact table as VARCHAR columns.

**Recommendation**: **Option B** (degenerate)

- Only 27 combinations (9 transaction types × 3 asset types)
- No history tracking needed
- Simpler queries (no extra join)
- More intuitive for analysts

______________________________________________________________________

### Step 4: Identify the Facts

#### Measure Classification

| Measure           | Type          | Additive Across Transactions? | Additive Across Time? | Storage |
| ----------------- | ------------- | ----------------------------- | --------------------- | ------- |
| contract_total    | Semi-additive | ✅ Yes (trade value sums)     | ❌ No (restate)       | INTEGER |
| contract_years    | Semi-additive | ✅ Yes (total years)          | ❌ No                 | INTEGER |
| faad_compensation | Additive      | ✅ Yes                        | ✅ Yes                | INTEGER |
| cap_space_amount  | Semi-additive | ✅ Yes (net cap transfer)     | ❌ No                 | INTEGER |

**No Fully Additive Measures**: All measures are semi-additive because they represent point-in-time values, not accumulating totals.

#### Complex Attributes

**contract_split** (yearly cap hits):

- Format: JSON array `[4, 4, 4]` or `[40, 40, 37, 24, 24]`
- Length must equal `contract_years`
- Sum must equal `contract_total`
- Storage: TEXT as JSON (DuckDB supports JSON functions)

**Rationale for JSON**:

- Variable-length arrays (1-7 years observed)
- Schema flexibility (league rules may change)
- DuckDB native JSON support for aggregation
- Avoids bridge table complexity

**Data Quality Validation**:

```sql
-- dbt test: contract split integrity
SELECT transaction_id
FROM fact_league_transactions
WHERE contract_total IS NOT NULL
  AND contract_split IS NOT NULL
  AND len(json_extract(contract_split, '$')) != contract_years;
-- Should return 0 rows

-- dbt test: contract split sum
SELECT transaction_id
FROM fact_league_transactions
WHERE contract_total IS NOT NULL
  AND contract_split IS NOT NULL
  AND list_sum(json_extract(contract_split, '$')) != contract_total;
-- Should return 0 rows
```

#### Flags and Indicators

| Flag        | Type    | Values     | Nullability            |
| ----------- | ------- | ---------- | ---------------------- |
| rfa_matched | BOOLEAN | TRUE/FALSE | Nullable (mostly NULL) |

**Note**: `franchise_tag` and `faad_compensation` are derived from `transaction_type`, not separate flags.

______________________________________________________________________

## Fact Table Schema

### DDL

```sql
{{
  config(
    materialized='table',
    partition_by=['transaction_year'],
    external=true,
    location="{{ var('external_root') }}/core/fact_league_transactions"
  )
}}

CREATE TABLE fact_league_transactions (
    -- Degenerate Dimensions
    transaction_id VARCHAR NOT NULL,
    transaction_type VARCHAR NOT NULL,  -- Enum: Trade, Cut, Signing, Draft, FA, Waivers, Extension, Franchise, Amnesty
    asset_type VARCHAR NOT NULL,        -- Enum: player, pick, cap_space

    -- Time Dimensions
    transaction_date DATE NOT NULL,
    transaction_year INTEGER NOT NULL,  -- Partition key: YEAR(transaction_date)
    time_frame VARCHAR,                  -- Original timeframe string (e.g., "2024 Offseason")

    -- Franchise Dimensions (Role-Playing)
    from_franchise_id VARCHAR,  -- NULL for waiver wire sources
    to_franchise_id VARCHAR,    -- NULL for waiver wire destinations

    -- Asset Dimensions (Nullable by asset_type)
    player_id VARCHAR,  -- FK to dim_player (when asset_type='player')
    pick_id VARCHAR,    -- FK to dim_pick (when asset_type='pick')

    -- Contract Measures (Semi-Additive)
    contract_years INTEGER,
    contract_total INTEGER,
    contract_split TEXT,  -- JSON array: [4, 4, 4]

    -- Pick Attributes
    pick_original_owner VARCHAR,  -- Original franchise that owned the pick
    pick_round INTEGER,
    pick_slot INTEGER,

    -- Flags
    rfa_matched BOOLEAN,

    -- Special Transaction Measures
    faad_compensation INTEGER,  -- FAAD-specific

    -- Metadata
    source_row_hash VARCHAR,
    dt DATE,  -- Partition from raw load

    -- Primary Key (Grain Enforcement)
    PRIMARY KEY (transaction_id, asset_type, COALESCE(player_id, '-'), COALESCE(pick_id, '-'))
);
```

### Partitioning Strategy

**Partition Key**: `transaction_year`

**Analysis**:

- ~600 transactions/year × 13 seasons = ~7,800 total rows
- Partitions: 2012-2025 → 14 partitions
- Avg partition size: ~560 rows
- Max partition size: ~650 rows (2024)

**Query Patterns**:

```sql
-- Efficient: Single partition scan
SELECT * FROM fact_league_transactions
WHERE transaction_year = 2024;

-- Efficient: Range scan (3 partitions)
SELECT * FROM fact_league_transactions
WHERE transaction_year BETWEEN 2022 AND 2024;

-- Full scan (acceptable for 7,800 rows)
SELECT * FROM fact_league_transactions;
```

______________________________________________________________________

## Dimension Conformance

### dim_player Mapping Strategy

**Challenge**: Map 1,249 unique player names → `dim_player_id_xref.player_id`

**Mapping Sequence**:

1. **Exact match** on `name` column: `"Travis Kelce"` → match
1. **Fuzzy match** on `merge_name` column: `"travis kelce"` → match
1. **Unmapped**: player_id = -1, track in QA table

**Expected Coverage**:

- Exact match: ~85-90%
- Fuzzy match: ~5-8%
- Unmapped: ~2-5%

**QA View**:

```sql
-- stg_sheets__transactions_unmapped_players
SELECT DISTINCT
    player_name_raw,
    COUNT(*) AS occurrences,
    MIN(transaction_date) AS first_seen,
    MAX(transaction_date) AS last_seen
FROM stg_sheets__transactions
WHERE player_id = -1
  AND asset_type = 'player'
GROUP BY 1
ORDER BY 2 DESC;
```

**Follow-up**: If unmapped rate > 5%, populate `dim_name_alias` seed with manual mappings.

### dim_pick Mapping Strategy

**Challenge**: Map pick references like "2025 1st Round" → `dim_pick.pick_id`

**Pick ID Format**: `YYYY_R#_P##` (e.g., `2025_R1_P04`)

**Mapping Logic**:

```sql
CASE
    WHEN pick_slot IS NOT NULL AND pick_slot != 'TBD'
        THEN season || '_R' || round || '_P' || LPAD(pick_slot, 2, '0')
    ELSE
        season || '_R' || round || '_TBD'  -- Synthetic ID for unknown slots
END AS pick_id
```

**TBD Picks**:

- Cannot map to specific dim_pick row
- Create synthetic `pick_id` like `2025_R1_TBD`
- Update via backfill when pick is determined post-draft

### dim_franchise Mapping

**Simple**: GM name → franchise_id lookup

**Special Cases**:

- `"Waiver Wire"` → NULL (not a franchise)
- Historical ownership changes handled by dim_franchise SCD Type 2

**Validation**:

```sql
-- dbt test: all non-waiver transactions map to valid franchises
SELECT transaction_id
FROM fact_league_transactions
WHERE from_franchise_id IS NOT NULL
  AND from_franchise_id NOT IN (SELECT franchise_id FROM dim_franchise WHERE is_current_owner = TRUE);
```

______________________________________________________________________

## Multi-Asset Trade Reconstruction

### Business Requirement

Reconstruct complete trades showing all assets exchanged between parties.

**Example Query**:

```sql
-- "Show me the complete Chip vs James trade from 2024 Offseason"
WITH trade_window AS (
    SELECT
        time_frame,
        CASE
            WHEN from_franchise_id < to_franchise_id
            THEN from_franchise_id || '|' || to_franchise_id
            ELSE to_franchise_id || '|' || from_franchise_id
        END AS party_set,
        MIN(transaction_id) AS first_tid,
        MAX(transaction_id) AS last_tid
    FROM fact_league_transactions
    WHERE transaction_type = 'Trade'
      AND time_frame = '2024 Offseason'
      AND ('Chip' IN (from_franchise_id, to_franchise_id) AND 'James' IN (from_franchise_id, to_franchise_id))
    GROUP BY 1, 2
)
SELECT
    t.transaction_id,
    t.from_franchise_id,
    t.to_franchise_id,
    t.asset_type,
    COALESCE(p.name, pk.pick_id, 'Cap Space') AS asset_description,
    t.contract_total,
    t.contract_years
FROM fact_league_transactions t
JOIN trade_window tw
    ON t.transaction_id BETWEEN tw.first_tid AND tw.last_tid
LEFT JOIN dim_player p ON t.player_id = p.player_id
LEFT JOIN dim_pick pk ON t.pick_id = pk.pick_id
ORDER BY t.transaction_id DESC;
```

### Trade Summary Mart

**mart_trade_history** (aggregate by trade event):

```sql
-- One row per trade event (time_frame + party_set)
SELECT
    time_frame,
    party_set,
    COUNT(*) AS total_assets,
    SUM(CASE WHEN asset_type = 'player' THEN 1 ELSE 0 END) AS players_exchanged,
    SUM(CASE WHEN asset_type = 'pick' THEN 1 ELSE 0 END) AS picks_exchanged,
    SUM(CASE WHEN asset_type = 'cap_space' THEN contract_total ELSE 0 END) AS cap_space_exchanged,
    SUM(contract_total) AS total_contract_value
FROM fact_league_transactions
WHERE transaction_type = 'Trade'
GROUP BY 1, 2;
```

______________________________________________________________________

## Data Quality Framework

### Grain Tests

```yaml
# models/core/schema.yml
- name: fact_league_transactions
  tests:
    - dbt_utils.unique_combination_of_columns:
        combination_of_columns:
          - transaction_id
          - asset_type
          - player_id
          - pick_id
        config:
          where: "transaction_year >= 2012"  # Full history
```

### FK Tests

```yaml
tests:
  - relationships:
      to: ref('dim_player')
      field: player_id
      where: "asset_type = 'player' AND player_id != -1"

  - relationships:
      to: ref('dim_pick')
      field: pick_id
      where: "asset_type = 'pick' AND pick_id NOT LIKE '%TBD'"

  - relationships:
      to: ref('dim_franchise')
      field: from_franchise_id
      where: "from_franchise_id IS NOT NULL"

  - relationships:
      to: ref('dim_franchise')
      field: to_franchise_id
      where: "to_franchise_id IS NOT NULL"
```

### Enum Tests

```yaml
tests:
  - accepted_values:
      column_name: transaction_type
      values: ['Trade', 'Cut', 'Signing', 'Draft', 'FA', 'Waivers', 'Extension', 'Franchise', 'Amnesty']

  - accepted_values:
      column_name: asset_type
      values: ['player', 'pick', 'cap_space']
```

### Business Logic Tests

```yaml
tests:
  - dbt_expectations.expect_column_values_to_not_be_null:
      column_name: transaction_date

  - dbt_expectations.expect_column_pair_values_to_be_equal:
      column_A: contract_years
      column_B: "len(json_extract(contract_split, '$'))"
      where: "contract_split IS NOT NULL"

  - name: at_least_one_franchise_not_null
    test: "SELECT * FROM {{ ref('fact_league_transactions') }} WHERE from_franchise_id IS NULL AND to_franchise_id IS NULL"
    config:
      severity: error
```

______________________________________________________________________

## Implementation Checklist

### Prerequisites (✅ COMPLETE)

- ✅ dim_player_id_xref seed (12,133 players)
- ✅ dim_franchise seed (21 rows, SCD2)
- ✅ dim_pick seed (1,141 picks)
- ✅ dim_timeframe seed (138 timeframes)
- ⏭️ dim_asset seed/view (UNION of players + picks)

### Phase 2: Parser

- [ ] Implement `parse_transactions()` in `commissioner_parser.py`
- [ ] Timeframe parsing (regex patterns)
- [ ] Contract disaggregation (total/years → JSON split)
- [ ] Asset type inference
- [ ] Player name mapping (exact → fuzzy → unmapped tracking)
- [ ] Pick reference parsing
- [ ] Transaction ID cleaning (remove commas, handle duplicates)
- [ ] Unit tests with diverse fixtures

### Phase 3: Staging

- [ ] Create `stg_sheets__transactions.sql`
- [ ] Validate FK relationships
- [ ] Enum value validation
- [ ] Contract integrity tests
- [ ] QA view for unmapped players/picks
- [ ] Document mapping coverage metrics

### Phase 4: Fact

- [ ] Build `fact_league_transactions`
- [ ] Grain uniqueness test
- [ ] All FK relationship tests
- [ ] Partition by transaction_year
- [ ] Materialization strategy (table, full refresh)

### Phase 5: Marts

- [ ] `mart_trade_history` (trade event summaries)
- [ ] `mart_trade_valuations` (join to KTC market values)
- [ ] `mart_roster_timeline` (reconstruct rosters via transaction replay)

______________________________________________________________________

## Alignment with ADR-008

### What Changed

| ADR-008 Assumption                    | Reality (from Profiling)          | Resolution                                |
| ------------------------------------- | --------------------------------- | ----------------------------------------- |
| Sort column groups multi-asset trades | Each asset gets unique Sort value | Group by (time_frame, party_set) in marts |
| ~1,000 rows                           | 3,912 rows (13 seasons)           | Confirmed scale is manageable             |
| dim_asset required                    | Optional convenience view         | Create as simple UNION view               |
| dim_name_alias required               | Only if fuzzy matching fails      | Add iteratively based on QA               |

### ADR-008 Addendum (to be written)

**Title**: Resolved - TRANSACTIONS Prerequisites

**Changes**:

1. ✅ dim_player_id_xref created from nflverse ff_playerids
1. ✅ dim_pick created (2012-2030 base picks)
1. ✅ dim_franchise created (SCD2 ownership history)
1. ✅ dim_timeframe created (season/week/period mapping)
1. ⏭️ dim_asset to be created as UNION view (5 min task)
1. ⏭️ dim_name_alias deferred pending mapping QA results

**Trade Grouping**:

- Sort column does NOT group multi-asset trades
- Use `(time_frame, party_set)` tuple for trade reconstruction
- Preserve asset-level grain in fact table
- Aggregate in marts for trade-level analysis

______________________________________________________________________

## Next Steps

1. ✅ Phase 0: Data profiling complete
1. ✅ Phase 1: Kimball modeling strategy complete
1. ⏭️ Create dim_asset view
1. ⏭️ Implement parse_transactions()
1. ⏭️ Build staging model
1. ⏭️ Build fact table
1. ⏭️ Build trade analysis marts

______________________________________________________________________

## References

- Kimball Modeling Guide: `docs/architecture/kimball_modeling_guidance/kimbal_modeling.md`
- Data Profiling: `docs/analysis/TRANSACTIONS_profiling_20251001.md`
- ADR-008: `docs/adr/ADR-008-league-transaction-history-integration.md`
- SPEC-1 v2.2: `docs/spec/SPEC-1_v_2.2.md`
