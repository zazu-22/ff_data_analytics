# Ticket P1-028b: Refactor Contracts Models to Use Defense Macro

**Phase**: 1 - Foundation
**Estimated Effort**: Small (2-3 hours)
**Dependencies**: P1-028 (DST team defense seed must exist)
**Priority**: MEDIUM (defense player_id strategy changed in P1-028)

## Objective

Apply P1-028's DST defense seed to contracts models by creating a `resolve_defense_id_from_franchise()` macro and updating contracts models to use real defense player_ids (10001-10032) instead of NULL.

## Context

**Current State** (after P1-027):

- Contracts models assign `player_id = NULL` for defenses
- Defense logic is inline in `stg_sheets__contracts_active.sql`
- Synthetic player_key: `'DEF_' || franchise_abbrev`

**After P1-028**:

- FFAnalytics projections use real defense_ids (10001-10032) from `dim_team_defense_xref`
- Contracts models still use NULL, preventing joins with DST projections

**This Ticket**:

- Extract defense handling to reusable macro
- Update contracts models to use real defense_ids from P1-028 seed
- Enable joining contracts to DST projections

**Triggered By**: P1-028 defense player_id strategy change (NULL → 10001-10032)

**Originally**: Deferred optional task (DB-002 in BACKLOG.md), promoted to P1-028b due to P1-028 dependency

## Tasks

### Phase 1: Create Defense Macro

- [ ] Create `dbt/ff_data_transform/macros/resolve_defense_id_from_franchise.sql`
- [ ] Implement macro logic:
  - [ ] Input: `franchise_abbrev` column reference
  - [ ] Query `dim_team_defense_xref` for matching `team_abbrev`
  - [ ] Return `defense_id` (10001-10032) for matches
  - [ ] Return NULL for non-matches or errors
- [ ] Add comprehensive macro documentation:
  - [ ] Purpose: Map franchise abbreviation to defense player_id
  - [ ] Usage examples
  - [ ] Return value documentation
  - [ ] Edge case handling

### Phase 2: Update stg_sheets\_\_contracts_active

- [ ] Locate inline defense handling logic (lines ~140-155)
- [ ] Replace with macro call:
  ```sql
  when lower(pos) in ('def', 'dst', 'd', 'd/st') then struct_pack(
      player_id := {{ resolve_defense_id_from_franchise('franchise_abbrev') }},
      player_key := 'DEF_' || franchise_abbrev,
      match_status := 'DEFENSE_MAPPED',
      match_context := 'dim_team_defense_xref'
  )
  ```
- [ ] Update match_status from 'DEFENSE' to 'DEFENSE_MAPPED'
- [ ] Test compilation: `just dbt-run --select stg_sheets__contracts_active`
- [ ] Verify defense_id values (10001-10032, not NULL)

### Phase 3: Update stg_sheets\_\_contracts_cut

- [ ] Check if defense handling exists in model
- [ ] If yes: Replace with macro call (same pattern as contracts_active)
- [ ] If no: Document that defenses not applicable to cut liabilities
- [ ] Test compilation: `just dbt-run --select stg_sheets__contracts_cut`

### Phase 4: Integration Testing

- [ ] Run both contracts models: `just dbt-run --select stg_sheets__contracts_active stg_sheets__contracts_cut`
- [ ] Verify all tests pass (grain uniqueness, referential integrity)
- [ ] Check defense player_ids:
  ```sql
  SELECT DISTINCT player_id, player_key, franchise_abbrev
  FROM stg_sheets__contracts_active
  WHERE player_key LIKE 'DEF_%'
  ORDER BY franchise_abbrev;
  -- Expect: 12 rows with defense_id 10001-10032 (not NULL)
  ```
- [ ] Run roster parity test: `just dbt-test --select assert_sleeper_commissioner_roster_parity`
  - [ ] Verify no new failures introduced
- [ ] Rebuild downstream models: `just dbt-run --select +mrt_contract_snapshot_current`

### Phase 5: Validation - Enable DST Projection Joins

- [ ] Verify you can join contracts to DST projections:
  ```sql
  -- Test join between contracts and FFAnalytics DST projections
  SELECT
      c.franchise_abbrev,
      c.player_key,
      c.player_id as contract_defense_id,
      p.player_id as projection_defense_id,
      p.player as projection_player_name,
      p.pos as projection_position
  FROM stg_sheets__contracts_active c
  INNER JOIN stg_ffanalytics__projections p
      ON c.player_id = p.player_id
  WHERE c.player_key LIKE 'DEF_%'
  ORDER BY c.franchise_abbrev;
  -- Expect: 12 rows with matching defense_ids (10001-10032)
  ```
- [ ] Document successful join capability in completion notes

### Phase 6: Documentation

- [ ] Update this ticket with completion notes
- [ ] Document defense_id mapping in macro comments
- [ ] Update BACKLOG.md to mark DB-002 as "Promoted to P1-028b"
- [ ] Add completion note to P1-028 referencing P1-028b

## Acceptance Criteria

- [ ] `resolve_defense_id_from_franchise()` macro created and documented
- [ ] `stg_sheets__contracts_active` uses macro (no inline defense logic)
- [ ] `stg_sheets__contracts_cut` updated if defense handling exists
- [ ] Both contracts models compile and execute successfully
- [ ] Defense player_ids are 10001-10032 (not NULL)
- [ ] All 17 contract model tests pass (grain, referential integrity, roster parity)
- [ ] Can successfully join contracts to DST projections on player_id
- [ ] No regressions in downstream models

## Implementation Notes

### Macro Signature (Proposed)

```sql
{% macro resolve_defense_id_from_franchise(franchise_abbrev_col) %}
    /*
    Map franchise abbreviation to defense player_id from dim_team_defense_xref.

    Args:
        franchise_abbrev_col: Column reference for franchise abbreviation (e.g., 'franchise_abbrev')

    Returns:
        defense_id (10001-10032) if franchise matches team_abbrev in seed
        NULL if no match found

    Example:
        player_id := {{ resolve_defense_id_from_franchise('franchise_abbrev') }}

    Dependencies:
        - Requires dim_team_defense_xref seed/model (created in P1-028)
        - Requires franchise_abbrev to match team_abbrev in seed
    */
    (
        SELECT defense_id
        FROM {{ ref('dim_team_defense_xref') }}
        WHERE team_abbrev = {{ franchise_abbrev_col }}
    )
{% endmacro %}
```

### Current Defense Handling Logic (contracts_active)

**Before P1-028b** (inline, NULL player_id):

```sql
when lower(pos) in ('def', 'dst', 'd', 'd/st') then struct_pack(
    player_id := null::integer,
    player_key := 'DEF_' || franchise_abbrev,
    match_status := 'DEFENSE',
    match_context := null::varchar
)
```

**After P1-028b** (macro, real defense_id):

```sql
when lower(pos) in ('def', 'dst', 'd', 'd/st') then struct_pack(
    player_id := {{ resolve_defense_id_from_franchise('franchise_abbrev') }},
    player_key := 'DEF_' || franchise_abbrev,
    match_status := 'DEFENSE_MAPPED',
    match_context := 'dim_team_defense_xref'
)
```

### Why This Matters

**Problem**: After P1-028, FFAnalytics DST projections have real player_ids (10001-10032), but contracts still use NULL.

**Impact Without P1-028b**:
❌ Cannot join contracts to DST projections (NULL ≠ 10001-10032)
❌ DST salary cap implications invisible in projections analysis
❌ Inconsistent player_id strategy across data sources

**Impact With P1-028b**:
✅ Contracts and projections use same defense_ids
✅ Can join to analyze DST value vs. cost
✅ Consistent player_id strategy across all sources
✅ Macro enables reuse if other models need defense mapping

### Architecture Consistency

This follows the same pattern as P1-027:

1. **P1-027**: Created `resolve_player_id_from_name()` macro for individual players
2. **P1-028b**: Creates `resolve_defense_id_from_franchise()` macro for team defenses

Both achieve:

- Single source of truth (macro)
- Code reuse across models
- Consistent resolution logic
- Testable via macro unit tests

### Testing Strategy

1. **Compilation Test**: Verify macro generates valid SQL
2. **Execution Test**: Verify models build successfully
3. **Data Validation**: Confirm defense_ids are 10001-10032 (not NULL)
4. **Grain Test**: Ensure uniqueness constraints still pass
5. **Roster Parity Test**: No new discrepancies introduced
6. **Join Test**: Successfully join contracts to DST projections

## Related Tickets

- **P1-028**: Add DST team defense seed for FFAnalytics mapping (dependency)
- **P1-027**: Refactor contracts models to use player_id macro (pattern reference)
- **DB-002**: Original backlog item (promoted to this ticket)

## References

- Model (before): `dbt/ff_data_transform/models/staging/stg_sheets__contracts_active.sql` (lines ~140-155)
- Macro pattern: `dbt/ff_data_transform/macros/resolve_player_id_from_name.sql`
- Seed: `dbt/ff_data_transform/seeds/seed_team_defense_xref.csv` (created in P1-028)
- Model: `dbt/ff_data_transform/models/core/dim_team_defense_xref.sql` (created in P1-028)
- Backlog: `BACKLOG.md` (DB-002 promoted to this ticket)

## Notes

**Why Promoted from Backlog**:

Originally deferred as DB-002 because defense handling was only in one model and complexity didn't justify extraction. However, P1-028 changed the defense player_id strategy from NULL to real IDs (10001-10032), triggering the backlog item's promotion criteria:

> **Trigger for Priority Increase**: If defense player_id strategy changes (e.g., using P1-028 DST seed)

**Sequencing**: This should be completed immediately after P1-028 to ensure data consistency across FFAnalytics projections and contracts models.
