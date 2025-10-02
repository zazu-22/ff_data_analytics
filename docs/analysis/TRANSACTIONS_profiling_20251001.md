# TRANSACTIONS Tab Data Profiling

**Date**: 2025-10-01
**Sample Size**: 3,912 rows (2012-2025, ~13 seasons)
**Source**: Commissioner Sheet TRANSACTIONS tab

## Executive Summary

Successfully profiled 3,912 transaction records spanning 13 seasons. Discovered **critical deviation from ADR-008 assumptions**: multi-asset trades are NOT grouped by Sort column—instead, they must be identified by `(Time Frame, Party Set)` tuples. Largest trade contained 18 assets.

---

## Transaction Type Distribution

| Type | Count | % | Description |
|------|-------|---|-------------|
| Signing | 1,101 | 28.1% | Free agent signings from waiver wire |
| Cut | 853 | 21.8% | Player releases to waiver wire |
| Draft | 826 | 21.1% | Rookie draft selections |
| Trade | 732 | 18.7% | Multi-asset trades between franchises |
| FA | 246 | 6.3% | Free agent acquisitions |
| Waivers | 80 | 2.0% | Waiver wire claims |
| Extension | 40 | 1.0% | Contract extensions |
| Franchise | 24 | 0.6% | Franchise tag designations |
| Amnesty | 10 | 0.3% | Amnesty cuts |

---

## Asset Type Breakdown

| Asset Type | Count | % | Identification Logic |
|-----------|-------|---|----------------------|
| Player | 3,528 | 90.2% | `Player` column filled, not containing "Round" or "Cap Space" |
| Pick | 214 | 5.5% | `Player` column contains "Round" (e.g., "2025 1st Round") |
| Cap Space | 170 | 4.3% | `Player` column contains "Cap Space" (e.g., "2025 Cap Space") |

---

## Multi-Asset Trade Analysis

### Key Finding: **Sort Column Does NOT Group Multi-Asset Trades**

**ADR-008 Assumption (INCORRECT)**:
> "transaction_id from Sort column groups multi-asset trades"

**Reality**:
- Each asset in a trade gets a **unique Sort value** (consecutive descending integers)
- Multi-asset trades must be grouped by `(Time Frame, Party Set)` where Party Set = sorted({From, To})

### Trade Event Distribution

| Assets Per Trade | Number of Trade Events | Example |
|------------------|----------------------|---------|
| 1 asset | 4 | Simple 1-for-1 swaps (rare) |
| 2 assets | 27 | Player for pick |
| 3 assets | 24 | 2 players + pick |
| 4 assets | 27 | Multi-player deals |
| 5-10 assets | ~80 | Complex trades |
| 11-15 assets | ~40 | Blockbuster trades |
| 16+ assets | 3 | Mega-trades |

**Total Trade Events**: ~210 (from 732 individual asset rows)
**Largest Trade**: 18 assets (Chip ↔ James, 2024 Offseason)

### Example: 18-Asset Mega-Trade

**Time Frame**: 2024 Offseason
**Parties**: Chip ↔ James
**Transaction IDs**: 3622-3837 (consecutive descending)

**Chip → James**:
- DB Antoine Winfield Jr. (12/3, 4-4-4)
- DL Nick Bosa (34/2, 17-17)
- 2025 Cap Space (10)
- 2026 Cap Space (6)
- 7 more assets...

**James → Chip**:
- RB Isaac Guernedo (6/3, 1-1-4)
- RB Nick Chubb (no contract)
- 2025 1st Round (Chip's original pick)
- 2025 3rd, 5th Round
- 2026 1st, 2nd Round
- 3 more assets...

---

## Data Structure Details

### Columns

| Column | Type | Format | Examples | Nullability |
|--------|------|--------|----------|-------------|
| Time Frame | String | Various | "2025 Week 4", "2024 Offseason", "2025 FAAD", "2025 Rookie Draft" | Not Null |
| From | String | GM name or "Waiver Wire" | "Jason", "Waiver Wire" | Nullable (Draft) |
| To | String | GM name or "Waiver Wire" | "Chip", "Waiver Wire" | Nullable (Draft) |
| Original Order | String | GM name | "Chip" | Picks only |
| Round | String | "1"-"5" | "1", "2" | Picks only |
| Pick | String | Slot number or "TBD" | "4", "TBD" | Picks only |
| Position | String | Position code or "-" | "QB", "RB", "WR", "TE", "K", "DB", "DL", "LB", "D/ST", "-" | Players only |
| Player | String | Player name or asset description | "Travis Kelce", "2025 1st Round", "2025 Cap Space" | Not Null |
| Contract | String | "total/years" or "-" | "12/3", "152/4", "-" | Mixed |
| Split | String | Hyphen-delimited yearly amounts | "4-4-4", "40-40-37-24-24", "10" | Mixed |
| RFA Matched | String | "yes" or "-" | "yes", "-" | Sparse |
| FAAD Comp | String | Compensation amount or "-" | "5", "-" | FAAD only |
| Type | String | Transaction type | "Trade", "Cut", "Signing", "Draft" | Not Null |
| Sort | String | Transaction ID with commas | "3,910", "1,234" | Not Null |

### Time Frame Patterns

| Pattern | Count | Examples |
|---------|-------|----------|
| Week | 1,875 | "2025 Week 4", "2023 Week 12 Deadline" |
| Offseason | 696 | "2024 Offseason", "2019 Offseason" |
| FAAD | 515 | "2025 FAAD", "2020 FAAD" |
| Rookie Draft | 826 | "2025 Rookie Draft", "2015 Rookie Draft" |

**Total Unique Timeframes**: 138

### Contract Format Complexity

**Format**: `"total/years"` where total is sum of all yearly amounts

**Examples**:
- `"12/3"` = $12M over 3 years
- `"152/4"` = $152M over 4 years
- `"-"` = no contract (cut players, picks, cap space)

**Distribution**:
- Rows with contracts: 3,426 (87.6%)
- Rows without contracts: 486 (12.4%)

### Split Format Complexity

**Format**: Hyphen-delimited yearly cap hits (must sum to contract total, span contract years)

**Patterns**:
- Equal split: `"4-4-4"` for 12/3 contract
- Front-loaded: `"40-40-37-24-24"` for 165/5 contract
- Back-loaded: `"1-1-4"` for 6/3 contract
- Single year: `"50"` for 50/1 contract

**Edge Cases**:
- Cap space rows use Split for amount: Split="10" means $10M
- Pick rows typically have Split="-"
- Some players have Contract but Split="-" (legacy data?)

**Distribution**:
- Rows with splits: 3,596 (91.9%)
- Rows without splits: 316 (8.1%)

### Player Name Variations

- **Total player asset rows**: 3,528
- **Unique player names**: 1,249
- **Mapping challenge**: Must map to `dim_player_id_xref.player_id` (mfl_id)

**Sample Names**:
```
Travis Kelce
Antoine Winfield Jr.
D.K. Metcalf
T.J. Hockenson
...
```

**Mapping Strategy**:
1. Exact match on `dim_player_id_xref.name`
2. Fuzzy match on `dim_player_id_xref.merge_name` (normalized)
3. Unmapped → track for manual review, populate `dim_name_alias` if needed

---

## Critical Implementation Findings

### 1. Trade Grouping Logic (CORRECTED)

**WRONG (per ADR-008)**:
```sql
-- DON'T USE THIS
GROUP BY transaction_id  -- Sort column
```

**CORRECT**:
```sql
-- Use this pattern
WITH party_normalized AS (
  SELECT
    *,
    CASE
      WHEN from_franchise < to_franchise
      THEN from_franchise || '|' || to_franchise
      ELSE to_franchise || '|' || from_franchise
    END AS party_set
  FROM transactions
  WHERE type = 'Trade'
)
SELECT
  time_frame,
  party_set,
  COUNT(*) AS asset_count,
  MIN(transaction_id) AS first_tid,
  MAX(transaction_id) AS last_tid
FROM party_normalized
GROUP BY time_frame, party_set
```

### 2. Asset Type Inference

```python
def infer_asset_type(row):
    player = row['Player']
    position = row['Position']

    if pd.isna(player) or player == '-':
        return 'unknown'
    elif 'Round' in player:
        return 'pick'
    elif 'Cap Space' in player:
        return 'cap_space'
    elif position and position != '-':
        return 'player'
    else:
        return 'unknown'
```

### 3. Contract Parsing Logic

```python
def parse_contract(contract_str, split_str):
    """Parse contract total/years and validate against split."""
    if not contract_str or contract_str == '-':
        return None, None, None

    # Parse "total/years"
    total, years = contract_str.split('/')
    total = int(total)
    years = int(years)

    # Parse split (hyphen-delimited)
    if split_str and split_str != '-':
        split_values = [int(x) for x in split_str.split('-')]

        # Validation
        assert len(split_values) == years, f"Split length mismatch: {len(split_values)} != {years}"
        assert sum(split_values) == total, f"Split sum mismatch: {sum(split_values)} != {total}"

        return total, years, split_values
    else:
        # No split provided, assume even distribution
        return total, years, [total // years] * years
```

### 4. Timeframe Parsing

**Complexity**: Multiple formats require pattern matching

```python
import re
from datetime import datetime

def parse_timeframe(timeframe_str):
    """Parse Time Frame into structured date/period."""

    # Pattern 1: "YYYY Week N" or "YYYY Week N Deadline"
    week_match = re.match(r'(\d{4}) Week (\d+)', timeframe_str)
    if week_match:
        season = int(week_match.group(1))
        week = int(week_match.group(2))
        return {'season': season, 'week': week, 'period': 'regular'}

    # Pattern 2: "YYYY Offseason"
    offseason_match = re.match(r'(\d{4}) Offseason', timeframe_str)
    if offseason_match:
        season = int(offseason_match.group(1))
        return {'season': season, 'week': None, 'period': 'offseason'}

    # Pattern 3: "YYYY FAAD"
    faad_match = re.match(r'(\d{4}) FAAD', timeframe_str)
    if faad_match:
        season = int(faad_match.group(1))
        return {'season': season, 'week': None, 'period': 'faad'}

    # Pattern 4: "YYYY Rookie Draft"
    draft_match = re.match(r'(\d{4}) Rookie Draft', timeframe_str)
    if draft_match:
        season = int(draft_match.group(1))
        return {'season': season, 'week': None, 'period': 'rookie_draft'}

    raise ValueError(f"Unknown timeframe format: {timeframe_str}")
```

### 5. Pick Parsing

**Format**: `"YYYY Rth Round"` in Player column

```python
def parse_pick_reference(player_str, original_order, round_col, pick_col):
    """Parse pick reference and map to dim_pick.pick_id."""

    # Extract season and round from Player column
    pick_match = re.match(r'(\d{4}) (\d)(?:st|nd|rd|th) Round', player_str)
    if not pick_match:
        return None

    season = int(pick_match.group(1))
    round_num = int(pick_match.group(2))

    # Determine pick slot
    if pick_col and pick_col != 'TBD':
        slot = int(pick_col)
    else:
        # TBD picks: use original_order to estimate
        slot = None  # Will need manual resolution or update later

    # Construct pick_id matching dim_pick format
    if slot:
        pick_id = f"{season}_R{round_num}_P{slot:02d}"
    else:
        pick_id = f"{season}_R{round_num}_TBD"

    return pick_id
```

---

## Kimball Modeling Considerations

### Grain Validation

**Proposed Grain** (from ADR-008):
> "One row per asset per transaction"

**Validation**: ✅ **CORRECT**

**Unique Key**:
- ✅ `transaction_id` (Sort column, cleaned)
- ✅ `asset_type`
- ✅ `player_id` (nullable, for player assets)
- ✅ `pick_id` (nullable, for pick assets)

**Rationale**: Each row represents one asset moving in one direction. Multi-asset trades create multiple rows.

### Fact vs Dimension Attributes

**Fact Attributes** (measures, FKs):
- `transaction_id` (degenerate dimension)
- `transaction_date` (derived from time_frame)
- `from_franchise_id` (FK to dim_franchise)
- `to_franchise_id` (FK to dim_franchise)
- `player_id` (FK to dim_player, nullable)
- `pick_id` (FK to dim_pick, nullable)
- `contract_years` (semi-additive)
- `contract_total` (semi-additive)
- `rfa_matched` (flag)
- `faad_compensation` (measure)

**Dimension Attributes** (should be in dimensions, not fact):
- Player name → dim_player
- Pick description → dim_pick
- Franchise/GM name → dim_franchise

**Degenerate Dimensions** (low-cardinality, stored in fact):
- `transaction_type`
- `asset_type`

**Complex Attributes** (requires disaggregation):
- `contract_split` → Store as JSON array in fact for flexibility

### Partitioning Strategy

**Partition Key**: `transaction_year` (extracted from transaction_date)

**Rationale**:
- ~600 transactions/year → ~600 rows/partition
- Enables efficient temporal queries
- Matches natural data collection boundary

### Additive vs Semi-Additive Measures

| Measure | Type | Reason |
|---------|------|--------|
| contract_total | Semi-additive | Can sum across assets in a trade, NOT across time |
| contract_years | Semi-additive | Can sum across assets in a trade, NOT across time |
| faad_compensation | Semi-additive | Meaningful only in FAAD context |

**Note**: No truly additive measures (transaction counts are derived, not stored).

---

## Data Quality Issues

### 1. Missing Contracts

- Some player assets have Position but Contract="-" and Split="-"
- Likely free agents or legacy data
- **Resolution**: Allow nullable contract fields

### 2. TBD Picks

- 214 pick assets, many with Pick="TBD"
- Cannot map to specific pick_id in dim_pick
- **Resolution**: Create synthetic pick_id format like "2025_R1_TBD", update when pick is determined

### 3. Player Name Variations

- Need to map 1,249 unique names → dim_player_id_xref.player_id
- **Expected unmapped rate**: ~5-10% (based on nflverse crosswalk coverage)
- **Resolution**:
  1. Exact match on name
  2. Fuzzy match on merge_name
  3. Track unmapped for manual review
  4. Populate dim_name_alias if patterns emerge

### 4. Cut Transactions with Same Sort ID

- Found 2 instances where multiple cuts share same Sort ID (3898, 3881)
- Violates assumption that Sort is unique per row
- **Resolution**: Use Sort + row number as composite transaction_id

---

## Implementation Recommendations

### Phase 2: Parser Implementation

1. **Timeframe normalization**: Use dim_timeframe seed for structured mapping
2. **Contract disaggregation**: Parse Contract and Split into separate columns, validate sum
3. **Asset type inference**: Use Player/Position/Round columns to determine asset_type
4. **Pick mapping**: Map pick descriptions to dim_pick.pick_id (handle TBD)
5. **Player mapping**: Map player names to dim_player_id_xref.player_id (exact → fuzzy → unmapped)
6. **Transaction ID**: Clean Sort column (remove commas, handle duplicates with row_number)
7. **Trade grouping**: Group by (Time Frame, Party Set) for analytics, but preserve row-level grain

### Phase 3: Staging Model

1. **Source validation**: Test all column types match expectations
2. **FK validation**: Ensure all player_id/pick_id/franchise_id map to dimensions
3. **Enum validation**: transaction_type, asset_type use controlled vocabularies
4. **Contract validation**: contract_total = sum(contract_split), len(contract_split) = contract_years
5. **QA view**: Create stg_sheets__transactions_unmapped for review

### Phase 4: Fact Table

1. **Grain test**: `dbt_utils.unique_combination_of_columns` on (transaction_id, asset_type, player_id, pick_id)
2. **FK tests**: Relationships to all dimension tables
3. **Partition by**: transaction_year (extracted from transaction_date)
4. **Materialization**: Table (not incremental—full refresh on each run)

---

## Next Steps

1. ✅ **Phase 0 Complete**: Data profiling complete
2. ⏭️ **Phase 1**: Apply Kimball modeling lens, document disaggregation strategy
3. ⏭️ **Phase 2**: Implement parse_transactions() with all complexity
4. ⏭️ **Phase 3**: Build staging model with QA
5. ⏭️ **Phase 4**: Build fact table and marts

---

## Appendix: Sample Data

### Multi-Asset Trade Example (6 assets)

```
Transaction: Chip ↔ James, 2024 Offseason (TID 3832-3837)

3837: Chip → James | DB Antoine Winfield Jr. | 12/3 (4-4-4)
3836: James → Chip | RB Isaac Guernedo | 6/3 (1-1-4)
3835: Chip → James | DL Nick Bosa | 34/2 (17-17)
3834: Chip → James | 2025 Cap Space | (10)
3833: Chip → James | 2026 Cap Space | (6)
3832: James → Chip | 2027 2nd Round | -
```

### Transaction Type Examples

```csv
# Cut
2025 Week 4,Waiver Wire,Gordon,-,-,-,WR,Tre Tucker,12/4,3-3-3-3,-,-,Cut,"3,910"

# Signing
2025 Week 2,Waiver Wire,Eric,-,-,-,TE,Juwan Johnson,1/1,1,-,-,Signing,"3,879"

# Draft
2025 Rookie Draft,-,Andy,Andy,1,1,RB,Ashton Jeanty,18/3,6-6-6,-,-,Draft,"3,707"

# Trade
2024 Offseason,Chip,James,-,-,-,DB,Antoine Winfield Jr.,12/3,4-4-4,-,-,Trade,"3,837"

# FA
2023 Offseason,Waiver Wire,Andy,-,-,-,DL,Calais Campbell,2/1,2,-,-,FA,"3,275"

# Waivers
2024 Offseason,Chip,Piper,-,-,-,QB,Jared Goff,2/2,1-1,-,-,Waivers,"3,845"

# Extension
2021 Offseason,Andy,Andy,-,-,-,WR,A.J. Brown,24/2,12-12,-,-,Extension,"1,764"

# Franchise
2024 Offseason,Jason,Jason,-,-,-,WR,Justin Jefferson,20/1,20,-,-,Franchise,"3,573"
```
