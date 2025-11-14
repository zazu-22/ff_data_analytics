# P1-028b Ticket Creation Summary

**Date**: 2025-11-13
**Action**: Created new Phase 1 ticket from promoted backlog item

## Overview

Created **P1-028b: Refactor Contracts Models to Use Defense Macro** by promoting backlog item DB-002 to a full Phase 1 ticket.

## Rationale

**Trigger Condition Met**:

> If defense player_id strategy changes (e.g., using P1-028 DST seed)

P1-028 introduces `dim_team_defense_xref` seed with real defense_ids (10001-10032) for FFAnalytics projections. Contracts models currently use `player_id = NULL` for defenses, preventing joins with DST projections.

**Promotion Criteria Satisfied**:

1. ✅ Defense player_id strategy changed (NULL → 10001-10032)
2. ✅ Multiple models need defense handling (contracts_active, contracts_cut)
3. ✅ Enables critical functionality (joining contracts to DST projections)
4. ✅ Follows established pattern (P1-027 player_id macro)

## Changes Made

### 1. Created P1-028b Ticket

**File**: `P1-028b-refactor-contracts-to-use-defense-macro.md`

**Content**:

- **Objective**: Apply P1-028 defense seed to contracts models
- **Dependencies**: P1-028 (must complete first)
- **Priority**: MEDIUM (defense strategy changed)
- **Effort**: SMALL (2-3 hours)
- **Phases**:
  1. Create `resolve_defense_id_from_franchise()` macro
  2. Update `stg_sheets__contracts_active`
  3. Update `stg_sheets__contracts_cut` (if applicable)
  4. Integration testing
  5. Validate DST projection joins
  6. Documentation

**Key Deliverable**: Enable joining contracts to DST projections on player_id

### 2. Updated BACKLOG.md

**Changes**:

- Marked DB-002 status: `BACKLOG` → `PROMOTED TO P1-028b`
- Updated priority: `LOW` → `PROMOTED`
- Added promotion reason and trigger explanation
- Added cross-reference to new ticket
- Updated statistics: 2 items → 1 active, 1 promoted
- Updated effort estimate: 3-5 hours → 1-2 hours (active only)

### 3. Updated 00-OVERVIEW.md

**Changes**:

- **Total tickets**: 60 → 61
- **Phase 1 tickets**: 29 → 30
- **Tech debt tickets**: 1 → 2
- **Overall progress**: 27/60 (45%) → 27/61 (44%)
- **Phase 1 progress**: 27/29 (93%) → 27/30 (90%)
- **Total estimated effort**: ~179-224 hours → ~182-229 hours
- Added P1-028b to FFAnalytics Models section
- Added creation note to Recent Progress (2025-11-13)
- Added historical note documenting promotion

## Sequencing

**Recommended order**:

1. **P1-028**: Add DST team defense seed (creates infrastructure)
2. **P1-028b**: Refactor contracts to use defense macro (applies infrastructure)
3. Both should complete before Phase 2 starts

**Dependencies**:

- P1-028b depends on P1-028 (requires `dim_team_defense_xref` seed)
- P1-028b is independent of P1-005/P1-006 (can run in parallel)

## Architectural Consistency

This follows the established pattern:

- **P1-015**: Updated KTC staging model
- **P1-015b**: Refactored name alias architecture
- **P1-028**: Add DST defense seed
- **P1-028b**: Refactor defense handling architecture

Both "b" tickets are architectural improvements that apply the "a" ticket's infrastructure more broadly.

## Benefits

**Without P1-028b** (after P1-028):

- ❌ Contracts: `player_id = NULL` for defenses
- ❌ FFAnalytics: `player_id = 10001-10032` for DST projections
- ❌ Cannot join contracts to DST projections (NULL ≠ 10001)
- ❌ DST salary cap impact invisible in projections analysis

**With P1-028b**:

- ✅ Contracts and projections use same defense_ids
- ✅ Can join to analyze DST value vs. cost
- ✅ Consistent player_id strategy across all sources
- ✅ Reusable macro for future models needing defense mapping

## Implementation Notes

**Macro Signature**:

```sql
{% macro resolve_defense_id_from_franchise(franchise_abbrev_col) %}
    -- Returns defense_id (10001-10032) from dim_team_defense_xref
    -- NULL if no match found
{% endmacro %}
```

**Usage Example**:

```sql
when lower(pos) in ('def', 'dst', 'd', 'd/st') then struct_pack(
    player_id := {{ resolve_defense_id_from_franchise('franchise_abbrev') }},
    player_key := 'DEF_' || franchise_abbrev,
    match_status := 'DEFENSE_MAPPED',
    match_context := 'dim_team_defense_xref'
)
```

## Validation

✅ P1-028b ticket created with comprehensive implementation plan
✅ BACKLOG.md updated to reflect promotion
✅ 00-OVERVIEW.md updated with new ticket and counts
✅ Dependencies clearly documented (P1-028 → P1-028b)
✅ Consistent with existing architectural patterns (P1-015b, P1-027)

## Files Modified

1. **Created**: `P1-028b-refactor-contracts-to-use-defense-macro.md`
2. **Updated**: `BACKLOG.md` (DB-002 promoted)
3. **Updated**: `00-OVERVIEW.md` (added P1-028b, updated counts)

## Next Steps

When implementing:

1. Complete P1-028 first (creates seed and defense_xref utility)
2. Then implement P1-028b (creates macro, updates contracts models)
3. Validate that contracts can join to DST projections on player_id

## References

- **New Ticket**: `P1-028b-refactor-contracts-to-use-defense-macro.md`
- **Dependency**: `P1-028-add-dst-team-defense-seed.md`
- **Pattern Reference**: `P1-027-refactor-contracts-models-to-use-player-id-macro.md`
- **Backlog Item**: `BACKLOG.md` (DB-002)
- **Overview**: `00-OVERVIEW.md` (lines 96, 200, 236)
