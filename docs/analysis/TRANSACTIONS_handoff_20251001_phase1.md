# TRANSACTIONS Implementation Handoff - Phase 1 Complete

**Date**: 2025-10-01
**Status**: Phase 0-1 Complete (Profiling + Kimball Design), Ready for Phase 2 (Parser Implementation)
**Next Session Start**: Phase 2 - Implement `parse_transactions()`

---

## Executive Summary

Successfully profiled 3,912 TRANSACTIONS records (2012-2025, 13 seasons) and designed complete Kimball dimensional model. **Critical discovery**: Transaction type classification requires joining to `dim_timeframe` seed - achieved **100% classification accuracy** using `period_type` + raw `Type` + contract patterns.

### Key Discoveries

1. **Multi-asset trades**: Sort column does NOT group trades - use `(Time Frame, Party Set)` tuple instead
2. **Transaction types**: Raw `Type` column is ambiguous - requires `dim_timeframe.period_type` for accurate classification
3. **Weekly contracts**: NOT in TRANSACTIONS tab (auto-expire, only in Sleeper API) - all TRANSACTIONS are yearly contracts
4. **Contract format**: 1/1 means "1 year for $1", NOT weekly
5. **Seeds ready**: All dependencies exist (dim_player_id_xref, dim_franchise, dim_pick, dim_timeframe)

---

## Phase 0-1 Deliverables ✅

### Documents Created

1. **`TRANSACTIONS_profiling_20251001.md`** - Complete data profiling
   - 3,912 rows, 14 columns, 138 unique timeframes
   - Transaction type distribution, contract complexity analysis
   - Multi-asset trade structure (up to 18 assets in single trade)
   - Player name mapping challenge (1,249 unique names)

2. **`TRANSACTIONS_kimball_strategy_20251001.md`** - Dimensional modeling design
   - Grain: One row per asset per transaction per direction
   - Fact schema with degenerate dimensions
   - Semi-additive measures, JSON contract splits
   - Partition strategy (transaction_year)

3. **`TRANSACTIONS_handoff_20251001_phase1.md`** (this document)

### Sample Data

- **Location**: `samples/sheets/TRANSACTIONS/TRANSACTIONS.csv` (3,912 rows)
- **Coverage**: 2012-2025 (13 complete seasons)
- **Quality**: 100% join to dim_timeframe

---

## Critical Transaction Type Classification

**Problem Solved**: Raw `Type` column is inconsistent - "Signing" can mean FAAD UFA, FAAD RFA match, FASA, or offseason signing depending on context.

**Solution**: Join to `dim_timeframe` seed and use `period_type` + additional fields:

### Classification Logic (100% Coverage)

```python
def derive_transaction_type_refined(row):
    """
    Derive precise transaction type using dim_timeframe.period_type.

    Returns one of 11 refined transaction types.
    """

    # Rookie draft selections
    if row['period_type'] == 'rookie_draft':
        return 'rookie_draft_selection'

    # Franchise tags (offseason only)
    if row['Type'] == 'Franchise':
        return 'franchise_tag'

    # FAAD signings (period_type='faad')
    if row['period_type'] == 'faad':
        if row['Type'] == 'Signing' and row['RFA Matched'] == 'yes':
            return 'faad_rfa_matched'
        elif row['Type'] in ['Signing', 'FA']:
            return 'faad_ufa_signing'

    # FASA signings (in-season, preseason, offseason, deadline)
    # CRITICAL: All Signing in TRANSACTIONS are yearly contracts via FASA
    # Weekly contracts ($1/week, auto-expire) are NOT in this tab
    if row['period_type'] in ['regular', 'deadline', 'preseason', 'offseason']:
        if row['Type'] == 'Signing':
            return 'fasa_signing'  # Includes 1/1 contracts (1 year for $1)

    # Offseason free agency (FA type outside FAAD)
    if row['period_type'] == 'offseason' and row['Type'] == 'FA':
        return 'offseason_ufa_signing'

    # Straightforward mappings
    if row['Type'] == 'Trade':
        return 'trade'
    if row['Type'] == 'Cut':
        return 'cut'
    if row['Type'] == 'Waivers':
        return 'waiver_claim'
    if row['Type'] == 'Extension':
        return 'contract_extension'
    if row['Type'] == 'Amnesty':
        return 'amnesty_cut'

    return 'unknown'
```

### Distribution of Refined Types

| Refined Type | Count | Source Logic |
|--------------|-------|--------------|
| cut | 853 | Type='Cut' |
| rookie_draft_selection | 826 | period_type='rookie_draft' |
| trade | 732 | Type='Trade' |
| fasa_signing | 718 | Signing in regular/deadline/preseason/offseason |
| faad_ufa_signing | 453 | Signing/FA in FAAD period (not RFA matched) |
| offseason_ufa_signing | 114 | FA in offseason (outside FAAD) |
| waiver_claim | 80 | Type='Waivers' |
| faad_rfa_matched | 62 | Signing in FAAD with RFA Matched='yes' |
| contract_extension | 40 | Type='Extension' (usually 4th year options) |
| franchise_tag | 24 | Type='Franchise' |
| amnesty_cut | 10 | Type='Amnesty' |
| **TOTAL** | **3,912** | **100% coverage** |

---

## dim_timeframe Integration (CRITICAL)

**Seed Location**: `dbt/ff_analytics/seeds/dim_timeframe.csv`

**Columns**:

- `timeframe_string` - Exact match to TRANSACTIONS `Time Frame` column
- `season` - Extracted season year
- `period_type` - **KEY FIELD**: rookie_draft, faad, regular, deadline, offseason, preseason
- `week` - NFL week number (nullable for non-week periods)
- `sort_sequence` - Chronological ordering

**Join Pattern**:

```sql
LEFT JOIN dim_timeframe tf
  ON raw.time_frame = tf.timeframe_string
```

**Coverage**: 100% - All 3,912 TRANSACTIONS rows match exactly to dim_timeframe

**period_type Values**:

- `rookie_draft` - Annual rookie draft (60 picks per year)
- `faad` - Free Agent Auction Draft (offseason, ~383 signings)
- `regular` - In-season weeks 1-17
- `deadline` - Trade deadline week (Week 12-15, varies by year)
- `preseason` - NFL preseason weeks (Weeks 3-4)
- `offseason` - Post-Super Bowl to FAAD (~187 cuts, 114 FA signings)

---

## Weekly vs Yearly Contracts (CRITICAL CORRECTION)

**Previous Assumption**: ❌ 1/1 contracts are weekly ($1/week, auto-expire)
**Actual Reality**: ✅ 1/1 contracts are yearly (1 year for $1)

### The Truth About Weekly Contracts

**Weekly contracts are NOT in TRANSACTIONS tab**:

- Format: $1/week, auto-expire after week's games
- Signed after FASA completes each week (first-come-first-serve)
- Automatically removed from Sleeper rosters on week rollover
- Only visible in Sleeper API roster data, NOT commissioner sheet

**All TRANSACTIONS are yearly contracts**:

- Signed via FAAD (offseason auction) or FASA (weekly sealed bid)
- Contract format: `total/years` (e.g., 1/1, 152/4, 550/5)
- 1/1 = 1 year for $1 (minimum yearly contract)
- Persist in commissioner sheet for cap tracking

---

## Data Structure Insights

### Multi-Asset Trade Grouping

**ADR-008 Assumption**: ❌ Sort column groups multi-asset trades
**Reality**: ✅ Sort column is unique per row; use `(Time Frame, Party Set)` to identify trade events

**Correct Grouping Logic**:

```sql
WITH party_normalized AS (
  SELECT
    *,
    CASE
      WHEN from_franchise < to_franchise
      THEN from_franchise || '|' || to_franchise
      ELSE to_franchise || '|' || from_franchise
    END AS party_set
  FROM transactions
  WHERE transaction_type_refined = 'trade'
)
SELECT
  time_frame,
  party_set,
  COUNT(*) AS asset_count
FROM party_normalized
GROUP BY 1, 2;
```

**Trade Complexity**:

- Largest trade: 18 assets (Chip ↔ James, 2024 Offseason)
- 17 different trade sizes observed (1-18 assets)
- Most trades: 2-6 assets (80% of trade events)

### Asset Types

**Inferred from columns**:

| Asset Type | Count | Identification Logic | FK Target |
|-----------|-------|----------------------|-----------|
| player | 3,528 | Player filled, Position != '-', not "Round/Cap Space" | dim_player_id_xref.player_id |
| pick | 214 | Player contains "Round" (e.g., "2025 1st Round") | dim_pick.pick_id |
| cap_space | 170 | Player contains "Cap Space" (e.g., "2025 Cap Space") | None (stored as amount in Split) |

### Contract Format Complexity

**Contract Column**: `total/years` format

- Examples: `1/1`, `152/4`, `550/5`
- Total = sum of all yearly amounts
- Years = contract length (1-5)

**Split Column**: Hyphen-delimited yearly cap hits

- Examples: `4-4-4` (equal), `40-40-37-24-24` (front-loaded), `1-1-4` (back-loaded)
- Must sum to Contract total
- Must have length equal to Contract years
- Cap space rows use Split for amount (e.g., Split="10" = $10M cap space)

**Validation Rules**:

```python
assert len(split_array) == contract_years
assert sum(split_array) == contract_total
```

### Special Fields

**RFA Matched**: 68 occurrences

- "yes" or "-" (blank/null)
- Only relevant for FAAD signings (RFA match process)
- Indicates owner matched another team's RFA offer

**FAAD Comp**: 56 occurrences

- Dollar amount (e.g., "5", "10")
- RFA compensation given to losing team
- Only for FAAD signings

---

## Seed Dependencies (ALL READY ✅)

### Required Seeds (Complete)

1. **dim_player_id_xref** ✅
   - 12,133 players with 19 provider IDs
   - `player_id` = mfl_id (canonical)
   - `name` for exact match, `merge_name` for fuzzy match
   - Coverage expected: ~95% exact/fuzzy, ~5% unmapped

2. **dim_franchise** ✅
   - 21 rows (F001-F012, SCD Type 2 ownership history)
   - Maps GM names → franchise_id
   - "Waiver Wire" → NULL (not a franchise)

3. **dim_pick** ✅
   - 1,141 picks (2012-2030, 5 rounds × 12 teams)
   - `pick_id` format: `YYYY_R#_P##` (e.g., `2025_R1_P04`)
   - Handles "TBD" picks with synthetic ID: `YYYY_R#_TBD`

4. **dim_timeframe** ✅
   - 139 timeframes (2012-2025)
   - **CRITICAL**: Enables transaction type classification
   - 100% join coverage to TRANSACTIONS

### Optional Seeds (Deferred)

5. **dim_asset** (create as simple UNION view)

   ```sql
   SELECT player_id AS asset_id, 'player' AS asset_type FROM dim_player_id_xref
   UNION ALL
   SELECT pick_id, 'pick' FROM dim_pick
   ```

6. **dim_name_alias** (add iteratively if fuzzy matching fails)
   - Only needed if unmapped rate > 5%
   - Populate based on parser QA results

---

## Phase 2 Implementation Plan

### Task 1: Implement parse_transactions()

**Location**: `src/ingest/sheets/commissioner_parser.py`

**Function Signature**:

```python
def parse_transactions(csv_path: Path) -> dict[str, pl.DataFrame]:
    """
    Parse TRANSACTIONS tab to normalized format.

    Returns:
        dict with keys:
            'transactions': Main transaction table (one row per asset)
            'unmapped_players': QA table for manual review
            'unmapped_picks': QA table for TBD picks
    """
```

**Key Parsing Tasks**:

1. **Load and join dim_timeframe**

   ```python
   timeframe_seed = pl.read_csv('dbt/ff_analytics/seeds/dim_timeframe.csv')
   df = df.join(timeframe_seed, left_on='Time Frame', right_on='timeframe_string')
   ```

2. **Derive transaction_type_refined** (use logic from this document)

3. **Parse contract fields**

   ```python
   def parse_contract(contract_str, split_str):
       if not contract_str or contract_str == '-':
           return None, None, None

       total, years = contract_str.split('/')
       total, years = int(total), int(years)

       if split_str and split_str != '-':
           split_array = [int(x) for x in split_str.split('-')]
           assert len(split_array) == years
           assert sum(split_array) == total
           return total, years, split_array
       else:
           # Even distribution
           return total, years, [total // years] * years
   ```

4. **Infer asset_type**

   ```python
   def infer_asset_type(player_str, position_str):
       if not player_str or player_str == '-':
           return 'unknown'
       elif 'Round' in player_str:
           return 'pick'
       elif 'Cap Space' in player_str:
           return 'cap_space'
       elif position_str and position_str != '-':
           return 'player'
       else:
           return 'unknown'
   ```

5. **Map player names → player_id**

   ```python
   # Load crosswalk
   xref = pl.read_csv('dbt/ff_analytics/seeds/dim_player_id_xref.csv')

   # Exact match
   df = df.join(xref.select(['name', 'player_id']),
                left_on='Player', right_on='name', how='left')

   # Fuzzy match for nulls
   unmapped = df.filter(pl.col('player_id').is_null() & (pl.col('asset_type') == 'player'))
   fuzzy_matches = unmapped.join(
       xref.select(['merge_name', 'player_id']),
       left_on=pl.col('Player').str.to_lowercase().str.strip(),
       right_on='merge_name',
       how='left'
   )

   # Track unmapped for QA
   still_unmapped = fuzzy_matches.filter(pl.col('player_id').is_null())
   ```

6. **Map pick references → pick_id**

   ```python
   def parse_pick_id(player_str, original_order, round_col, pick_col):
       match = re.match(r'(\d{4}) (\d)(?:st|nd|rd|th) Round', player_str)
       if not match:
           return None

       season, round_num = int(match.group(1)), int(match.group(2))

       if pick_col and pick_col != 'TBD':
           slot = int(pick_col)
           return f"{season}_R{round_num}_P{slot:02d}"
       else:
           return f"{season}_R{round_num}_TBD"  # Synthetic ID
   ```

7. **Clean transaction_id** (Sort column)

   ```python
   df = df.with_columns([
       pl.col('Sort').str.replace_all(',', '').str.replace_all('"', '').cast(pl.Int64).alias('transaction_id')
   ])

   # Handle duplicates (found 2 cases where same Sort used)
   df = df.with_columns([
       (pl.col('transaction_id').cast(pl.Str) + '_' +
        pl.arange(0, pl.count()).over('transaction_id').cast(pl.Str)).alias('transaction_id_unique')
   ])
   ```

8. **Write output**

   ```python
   from ingest.common.storage import write_parquet_any

   write_parquet_any(
       df=transactions_normalized,
       base_path='data/raw/commissioner/transactions',
       partition_by='dt',
       partition_value=datetime.now(UTC).strftime('%Y-%m-%d'),
       metadata={...}
   )
   ```

**Unit Test Fixtures Needed**:

- Multi-asset trade (6+ assets)
- FAAD RFA matched signing
- FASA 1/1 contract (1 year for $1)
- Draft selection with contract scale
- Cut with dead cap
- Waiver claim
- Franchise tag
- Contract extension (4th year option)
- Pick with TBD slot
- Cap space asset

### Task 2: Create dim_asset view

**Location**: `dbt/ff_analytics/models/core/dim_asset.sql`

```sql
{{ config(materialized='view') }}

SELECT
    player_id AS asset_id,
    'player' AS asset_type,
    name AS asset_name,
    position,
    team
FROM {{ ref('dim_player_id_xref') }}

UNION ALL

SELECT
    pick_id AS asset_id,
    'pick' AS asset_type,
    pick_id AS asset_name,  -- e.g., "2025_R1_P04"
    NULL AS position,
    NULL AS team
FROM {{ ref('dim_pick') }}
```

### Task 3: Build stg_sheets__transactions

**Location**: `dbt/ff_analytics/models/staging/stg_sheets__transactions.sql`

**Key Logic**:

```sql
{{ config(materialized='view') }}

WITH base AS (
  SELECT * FROM {{ source('sheets_raw', 'transactions') }}
),

with_timeframe AS (
  SELECT
    base.*,
    tf.season,
    tf.period_type,
    tf.week,
    tf.sort_sequence
  FROM base
  LEFT JOIN {{ ref('dim_timeframe') }} tf
    ON base.time_frame = tf.timeframe_string
),

classified AS (
  SELECT
    *,
    -- Apply transaction_type_refined logic here
    CASE
      WHEN period_type = 'rookie_draft' THEN 'rookie_draft_selection'
      WHEN type = 'Franchise' THEN 'franchise_tag'
      -- ... (full logic from this document)
    END AS transaction_type_refined
  FROM with_timeframe
)

SELECT * FROM classified
```

**Tests** (`models/staging/schema.yml`):

```yaml
- name: stg_sheets__transactions
  tests:
    - dbt_utils.unique_combination_of_columns:
        combination_of_columns:
          - transaction_id
          - asset_type
          - player_id
          - pick_id

    - accepted_values:
        column_name: transaction_type_refined
        values: ['rookie_draft_selection', 'faad_ufa_signing', 'faad_rfa_matched',
                 'fasa_signing', 'offseason_ufa_signing', 'trade', 'cut',
                 'waiver_claim', 'contract_extension', 'franchise_tag', 'amnesty_cut']

    - accepted_values:
        column_name: asset_type
        values: ['player', 'pick', 'cap_space']

    - relationships:
        to: ref('dim_player_id_xref')
        field: player_id
        where: "asset_type = 'player' AND player_id != -1"

    - relationships:
        to: ref('dim_pick')
        field: pick_id
        where: "asset_type = 'pick' AND pick_id NOT LIKE '%TBD'"
```

### Task 4: Build fact_league_transactions

**Location**: `dbt/ff_analytics/models/core/fact_league_transactions.sql`

**Schema** (from Kimball strategy doc):

```sql
{{ config(
    materialized='table',
    partition_by=['transaction_year'],
    external=true,
    location="{{ var('external_root') }}/core/fact_league_transactions"
) }}

SELECT
  -- Degenerate dimensions
  transaction_id,
  transaction_type_refined AS transaction_type,
  asset_type,

  -- Time dimensions
  transaction_date,
  transaction_year,
  time_frame,
  season,
  week,
  period_type,

  -- Franchise dimensions (role-playing)
  from_franchise_id,
  to_franchise_id,

  -- Asset dimensions
  player_id,
  pick_id,

  -- Contract measures
  contract_years,
  contract_total,
  contract_split,  -- JSON array

  -- Pick attributes
  pick_original_owner,
  pick_round,
  pick_slot,

  -- Flags
  rfa_matched,
  faad_compensation,

  -- Metadata
  source_row_hash,
  dt
FROM {{ ref('stg_sheets__transactions') }}
```

---

## Known Issues & Edge Cases

### 1. Duplicate Sort IDs

- Found 2 cases: TID 3898, 3881
- Multiple cuts share same Sort value
- **Solution**: Append row_number to create unique transaction_id

### 2. TBD Picks

- 214 pick assets, many with Pick="TBD"
- Cannot map to specific dim_pick row
- **Solution**: Create synthetic pick_id like `2025_R1_TBD`, backfill when determined

### 3. Player Name Variations

- 1,249 unique player names to map to 12,133 in crosswalk
- Expected ~5% unmapped after exact + fuzzy matching
- **Solution**: Track unmapped in QA view, populate dim_name_alias if needed

### 4. Contract Extensions vs 4th Year Options

- Type='Extension' in offseason
- Often rookie 4th year option exercises
- Contract format: typically high $/1 year (e.g., 24/1, 20/1)
- **No special handling needed**: Extension type captures intent

### 5. Cap Space in Split Column

- Cap space assets use Split column for amount (not Contract)
- Example: Player="2025 Cap Space", Contract="-", Split="10"
- **Parse logic**: When asset_type='cap_space', contract_total = int(Split)

---

## Success Criteria for Phase 2

**Parser Implementation**:

- ✅ 100% transaction type classification using dim_timeframe
- ✅ Player name mapping: ≥95% coverage (exact + fuzzy)
- ✅ Pick mapping: All valid picks mapped, TBD handled with synthetic ID
- ✅ Contract parsing: All splits validate (sum = total, length = years)
- ✅ Multi-asset trades: Correctly preserve asset-level grain
- ✅ QA tables: Unmapped players/picks tracked for review

**Staging Model**:

- ✅ All grain uniqueness tests pass
- ✅ All FK relationship tests pass
- ✅ All enum/accepted_values tests pass
- ✅ Contract integrity tests pass

**Fact Table**:

- ✅ Builds successfully with partition by transaction_year
- ✅ Grain test passes (transaction_id, asset_type, player_id, pick_id)
- ✅ All FK tests pass
- ✅ Enables trade reconstruction queries

---

## Files to Update in Phase 2

### Create New

- [ ] `src/ingest/sheets/commissioner_parser.py::parse_transactions()`
- [ ] `tests/test_sheets_commissioner_parser.py::test_parse_transactions_*` (unit tests)
- [ ] `dbt/ff_analytics/models/core/dim_asset.sql`
- [ ] `dbt/ff_analytics/models/staging/stg_sheets__transactions.sql`
- [ ] `dbt/ff_analytics/models/core/fact_league_transactions.sql`

### Update Existing

- [ ] `tools/make_samples.py` - Add TRANSACTIONS tab to sheets sampler
- [ ] `dbt/ff_analytics/models/staging/schema.yml` - Add stg_sheets__transactions tests
- [ ] `dbt/ff_analytics/models/core/schema.yml` - Add fact_league_transactions tests
- [ ] `docs/adr/ADR-008-league-transaction-history-integration.md` - Add resolution addendum
- [ ] `docs/spec/SPEC-1_v_2.2_implementation_checklist_v_1.md` - Update checkboxes

---

## Key References

- **Profiling**: `docs/analysis/TRANSACTIONS_profiling_20251001.md`
- **Kimball Strategy**: `docs/analysis/TRANSACTIONS_kimball_strategy_20251001.md`
- **ADR-008**: `docs/adr/ADR-008-league-transaction-history-integration.md`
- **League Rules**: `docs/spec/league_constitution.csv`
- **Rules Constants**: `docs/spec/rules_constants.json`
- **Sample Data**: `samples/sheets/TRANSACTIONS/TRANSACTIONS.csv`
- **Seeds**: `dbt/ff_analytics/seeds/`

---

## Quick Start for Next Session

```bash
# 1. Review this handoff
cat docs/analysis/TRANSACTIONS_handoff_20251001_phase1.md

# 2. Validate sample data still accessible
head samples/sheets/TRANSACTIONS/TRANSACTIONS.csv

# 3. Check seed availability
ls -la dbt/ff_analytics/seeds/dim_*.csv

# 4. Start Phase 2 implementation
# Begin with: src/ingest/sheets/commissioner_parser.py::parse_transactions()
```

---

**Handoff Complete** ✅
**Next Task**: Implement `parse_transactions()` with full transaction type classification logic
