# Multi-Source Snapshot Governance — Deferred Tasks Backlog

**Version**: 1.0
**Date**: 2025-11-13
**Status**: Active

______________________________________________________________________

This document tracks optional tasks that were deferred during Phase 1 implementation. These items are marked with `[defer]` in their source tickets and represent quality improvements that may be implemented in future work.

## Legend

- **Priority**: HIGH / MEDIUM / LOW
- **Effort**: SMALL (< 4 hours) / MEDIUM (4-8 hours) / LARGE (> 8 hours)
- **Status**: BACKLOG / PLANNED / IN_PROGRESS / COMPLETE

______________________________________________________________________

## Deferred Tasks

### DB-001: Add Unit Tests for Name Alias Utility

**Source Ticket**: P1-015b (Refactor Name Alias Loading to Use DuckDB)
**Priority**: MEDIUM
**Effort**: SMALL (1-2 hours)
**Status**: BACKLOG

**Description**:
Add unit tests for the `get_name_alias()` utility function in `src/ff_analytics_utils/name_alias.py` to improve code coverage and regression protection.

**Rationale for Deferral**:

- All functional requirements met via integration testing
- Ingestion validated successfully (31.1s run time)
- Player mapping verified (Zonovan Knight → Bam Knight → player_id 8284)
- Unit tests would be a quality enhancement but not blocking

**Recommended Test Coverage**:

1. DuckDB-first path (happy path)
2. CSV fallback when DuckDB unavailable
3. Source parameter validation (auto/duckdb/csv)
4. Column selection filtering
5. Error handling (missing files, malformed data)
6. Edge cases (empty results, duplicate aliases)

**Dependencies**: None

**References**:

- Function: `src/ff_analytics_utils/name_alias.py:get_name_alias()`
- Pattern reference: `src/ff_analytics_utils/player_xref.py:get_player_xref()`
- Ticket: `/Users/jason/code/ff_data_analytics/docs/implementation/multi_source_snapshot_governance/tickets/P1-015b-refactor-alias-to-use-duckdb.md` (line 46)

______________________________________________________________________

### DB-002: Extract Defense Handling to Macro

**Source Ticket**: P1-027 (Refactor Contracts Models to Use player_id Macro)
**Priority**: ~~LOW~~ → **PROMOTED**
**Effort**: SMALL (2-3 hours)
**Status**: ~~BACKLOG~~ → **PROMOTED TO P1-028b** (2025-11-13)

**Description**:
Extract defense/special teams player handling logic from `stg_sheets__contracts_active.sql` into a reusable `handle_defense_players` macro.

**Rationale for Deferral**:

- Defense handling currently only exists in one model (`contracts_active`)
- Inline logic is well-documented and tested
- Complexity vs. value trade-off: low value until duplicated across multiple models
- Ticket completion notes (line 536) document conscious decision to defer

**Scope**:

1. Create new macro: `macros/resolve_defense_players.sql`
2. Extract defense logic from `stg_sheets__contracts_active.sql` (lines ~140-155)
3. Update `contracts_active` to call macro
4. Update `contracts_cut` if defense handling needed there
5. Maintain roster parity test passing (critical validation)

**Current Defense Handling Logic**:

```sql
-- Defense/Special Teams: NULL player_id, synthetic player_key
when lower(pos) in ('def', 'dst', 'd', 'd/st') then struct_pack(
    player_id := null::integer,
    player_key := 'DEF_' || franchise_abbrev,
    match_status := 'DEFENSE',
    match_context := null::varchar
)
```

**Benefits if Implemented**:

- Consistency if defense handling needed in other models
- Single source of truth for defense logic
- Easier testing via macro unit tests

**Trigger for Priority Increase**:

- ✅ **TRIGGERED**: Defense player_id strategy changed in P1-028 (NULL → real IDs 10001-10032)

**Promotion Reason**:
P1-028 introduced `dim_team_defense_xref` seed with defense_ids 10001-10032 for FFAnalytics projections. To maintain consistency, contracts models must also use these IDs instead of NULL. This enables joining contracts to DST projections and creates the multi-model scenario that justifies macro extraction.

**Promoted To**: P1-028b (2025-11-13)

**Dependencies**: P1-028 (must complete first)

**References**:

- **New Ticket**: `P1-028b-refactor-contracts-to-use-defense-macro.md`
- Model: `dbt/ff_data_transform/models/staging/stg_sheets__contracts_active.sql`
- Macro pattern: `macros/resolve_player_id_from_name.sql`
- Original ticket: `P1-027-refactor-contracts-models-to-use-player-id-macro.md` (lines 187-189)
- Dependency: P1-028 (DST team defense seed)

______________________________________________________________________

## Backlog Statistics

**Total Items**: 1 active, 1 promoted
**By Priority**:

- HIGH: 0
- MEDIUM: 1 (DB-001)
- LOW: 0
- PROMOTED: 1 (DB-002 → P1-028b)

**By Effort**:

- SMALL: 1 active (DB-001)
- MEDIUM: 0
- LARGE: 0

**Total Estimated Effort**: 1-2 hours (active items only)

______________________________________________________________________

## Review Schedule

This backlog should be reviewed:

- After Phase 1 completion (before Phase 2)
- During Phase 3 (Documentation) planning
- Quarterly for priority reassessment
- When related features are being developed

______________________________________________________________________

## Adding New Deferred Items

When adding items to this backlog:

1. **Use next sequential ID**: DB-XXX
2. **Include all required fields**:
   - Source Ticket
   - Priority (HIGH/MEDIUM/LOW)
   - Effort (SMALL/MEDIUM/LARGE)
   - Status (default: BACKLOG)
   - Description (what needs to be done)
   - Rationale for Deferral (why not now)
   - Dependencies (if any)
   - References (files, tickets, line numbers)
3. **Update statistics** at bottom of document
4. **Mark source ticket** with `[defer]` symbol
5. **Update overview legend** if introducing new symbols

______________________________________________________________________

## Completion Process

When completing a deferred item:

1. Update status to IN_PROGRESS
2. Create implementation ticket or work directly
3. Upon completion:
   - Update status to COMPLETE
   - Add completion date
   - Link to completion commit/ticket
   - Update source ticket to mark as `[x]` complete
4. Update backlog statistics
