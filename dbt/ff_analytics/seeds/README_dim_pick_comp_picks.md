# dim_pick: Compensatory Pick Handling

## Base Picks (Seeded)

- **Scope**: 2012-2030, 5 rounds, 12 teams = 1,140 base picks
- **pick_type**: `base`
- **Naming**: `{season}_R{round}_P{slot:02d}` (e.g., `2024_R1_P01`)

## Compensatory Picks (Added via TRANSACTIONS)

- **Source**: RFA compensation awards during FAAD (active through 2026 offseason)
- **Trigger**: Team loses RFA to another team
- **Award amounts**:
  - $10-14/year → 3rd round comp pick
  - $15-24/year → 2nd round comp pick
  - $25+/year → 1st round comp pick
- **Placement**: End of respective round
- **pick_type**: `compensatory`
- **Naming**: `{season}_R{round}_COMP_{slot:02d}` (e.g., `2024_R1_COMP_13`)

## Overall Pick Number (Derived)

**Cannot pre-calculate** because it depends on comp picks awarded:

```sql
-- Calculate overall pick number at query time
SELECT
  pick_id,
  season,
  round,
  round_slot,
  ROW_NUMBER() OVER (
    PARTITION BY season
    ORDER BY round, round_slot
  ) AS overall_pick_number
FROM {{ ref('dim_pick') }}
WHERE season = 2024
```

## Pick Value Calculation

- Use overall_pick_number (not round_slot) for value charts
- Example: "2024 R2 P1" value depends on R1 comp picks:
  - 12 R1 picks → overall #13
  - 16 R1 picks → overall #17

## Data Sources

1. **TRANSACTIONS** tab: Pick trades, comp awards (event history)
1. **Roster tabs**: Current pick holdings per franchise (snapshot)

- These should reconcile if commissioner tracking is accurate

## Implementation Notes

- Comp picks added to dim_pick when parsing TRANSACTIONS
- Transaction parser detects RFA awards → generates comp pick row
- Roster validation can check: computed holdings vs roster tabs
