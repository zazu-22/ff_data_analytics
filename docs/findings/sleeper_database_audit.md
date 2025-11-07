# Sleeper Database Audit Findings

## Summary

The Sleeper database contains **11,368 unique NFL players** after deduplication by `dt` (latest snapshot). The initial count of 56,840 was due to multiple date partitions being read simultaneously.

## Key Findings

### Player Count

- **Total rows across all snapshots**: 56,840
- **Unique sleeper_player_ids**: 11,368
- **Unique players after dt deduplication**: 11,368
- **Snapshots**: Multiple dt partitions (2025-11-06, 2025-11-05, 2025-10-30, 2025-10-27)

**Conclusion**: The staging model correctly deduplicates by `dt` (keeps latest snapshot), so the unique count is accurate.

### Status Breakdown

- **Active**: 7,586 (66.7%)
- **Inactive**: 3,538 (31.1%)
- **Injured Reserve**: 227 (2.0%)
- **Other**: 17 (0.2%) - PUP, NFI, Practice Squad, NULL

**Conclusion**: Sleeper includes both active and inactive players, which is expected for a comprehensive NFL player database.

### Sport Analysis

- **NFL**: 11,368 (100%)
- **College/Other**: 0

**Conclusion**: All players are NFL players. No college or other sports included.

### Team Analysis

- **NULL (Free Agent/Retired)**: 8,621 (75.9%)
- **NFL Teams**: 2,746 (24.1%)
- **Non-NFL Teams**: 1 (0.01%)

**Conclusion**: Majority of players are free agents or retired, which is expected for a historical database.

### Data Quality Checks

#### Duplicate sleeper_player_ids

- **Result**: 0 duplicates
- **Conclusion**: Each sleeper_player_id is unique ✅

#### Duplicate name+position combinations

- **Data Quality Issues Found**:
  - "Player Invalid" entries: 52 total (multiple positions)
  - "Duplicate Player" entries: 31 total (multiple positions)
  - Legitimate duplicates: ~20 players with same name+position (different sleeper_player_ids)
    - Examples: Kyle Williams (WR, 3 IDs), Chris Jones (DT, 2 IDs), Matt Colburn (RB, 2 IDs)

**Conclusion**:

- Some placeholder/invalid entries exist ("Player Invalid", "Duplicate Player")
- Legitimate duplicate names exist (different players, same name+position)
- These are expected and handled correctly by birthdate matching

## Recommendations

### No Filtering Needed

The Sleeper database is correct and comprehensive. It includes:

- Active NFL players
- Inactive/retired players
- Players on IR/PUP
- Free agents

**Recommendation**: Continue using all players for fallback matching. The inactive/retired players may match historical players in nflverse that don't have sleeper_ids.

### Data Quality Notes

- "Player Invalid" and "Duplicate Player" entries should be filtered out during matching (they won't match real names anyway)
- Legitimate duplicate names are handled correctly by birthdate matching and deterministic tie-breaking

### Next Steps

Proceed with Phase 2: Bidirectional Position Normalization to improve matching for the 3,569 NULL sleeper_ids in xref.
