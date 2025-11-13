# Multi-Source Snapshot Governance — Ticket Tracking Overview

**Version**: 2.1\
**Date**: 2025-11-12\
**Status**: Active

______________________________________________________________________

This document provides a concise checklist for tracking completion of all implementation tickets for the Multi-Source Snapshot Governance effort.

## Quick Reference

- **Total Tickets**: 58 (includes 13 staging models + 9 data quality fixes + 2 architectural refactors)
- **Total Phases**: 7 (Phase 0-6 + Cross-Cutting)
- **Estimated Total Effort**: ~176-218 hours (updated for expanded Phase 1 + P1-027)
- **Parent Plan**: `../2025-11-07_plan_v_2_0.md`
- **Task Checklist**: `../2025-11-07_tasks_checklist_v_2_0.md`

## Recent Accomplishments (2025-11-12)

🎉 **Major Breakthrough**: Streaming hypothesis VALIDATED and roster parity test fully resolved!

**Completed This Session**:

- ✅ **P1-019**: Roster parity investigation COMPLETE (30→0 failures, 100% success)
  - Discovered and fixed 4 critical player_id resolution bugs
  - Validated streaming hypothesis: weekly roster changes explain expected discrepancies
  - Quick fixes applied; full refactor tracked in new ticket P1-027
- ✅ **P1-026**: Fixed macro cartesian product regression (3,563 duplicates eliminated)
- ✅ **P1-020**: Resolved TBD pick duplicates (22 pick_ids → 0)
- ✅ **P1-022**: Resolved orphan pick references (46 orphans → 0)
- ✅ **P1-023**: Base picks per round validation COMPLETE (4→0 failures, 100% success)
- ✅ **P1-024**: Comp registry duplicates resolved (19→0 duplicates) - PREVIOUSLY COMPLETED (2025-11-10, commit d6eb65c)
- 📝 **P1-027**: NEW TICKET created for contracts model refactoring (technical debt cleanup)

**Impact**: Phase 1 now 22/27 tickets complete (81%); Overall project 22/58 tickets complete (38%)

______________________________________________________________________

## Ticket Status Legend

- `[ ]` Not Started
- `[-]` In Progress
- `[x]` Complete
- `[~]` Blocked (with blocker noted)

______________________________________________________________________

## Phase 0: Kickoff & Decision Ratification (1 ticket)

- [x] **P0-001** — Scope ratification and blocker identification

______________________________________________________________________

## Phase 1: Foundation (27 tickets - 13 staging models + 9 data quality fixes + 2 architectural refactors + 2 cleanup/validation)

### Macro & Infrastructure

- [x] **P1-001** — Create snapshot_selection_strategy macro

### NFLverse Models (4 tickets)

- [x] **P1-002** — Update stg_nflverse\_\_player_stats model (baseline_plus_latest)
- [x] **P1-003** — Update stg_nflverse\_\_snap_counts model (baseline_plus_latest)
- [x] **P1-004** — Update stg_nflverse\_\_ff_opportunity model (latest_only, consistency)
- [x] **P1-007** — Update stg_nflverse\_\_ff_playerids model (latest_only)

### Sheets Models (5 tickets)

- [x] **P1-008** — Update stg_sheets\_\_cap_space model (latest_only)
- [x] **P1-009** — Update stg_sheets\_\_contracts_active model (latest_only)
- [x] **P1-010** — Update stg_sheets\_\_contracts_cut model (latest_only)
- [x] **P1-011** — Update stg_sheets\_\_draft_pick_holdings model (latest_only)
- [x] **P1-012** — Update stg_sheets\_\_transactions model (latest_only)

### Sleeper Models (2 tickets) ⚠️ **Priority: Fixes 1,893 duplicates**

- [x] **P1-013** — Update stg_sleeper\_\_fa_pool model (latest_only) - ⚠️ See commit notes: duplicates persist, root cause in mart logic
- [x] **P1-014** — Update stg_sleeper\_\_rosters model (latest_only)

### KTC Models (2 tickets)

- [x] **P1-015** — Update stg_ktc_assets model (latest_only)
- [x] **P1-015b** — Refactor name alias loading to use DuckDB (architectural consistency)

### Architectural Refactors (1 ticket)

- [ ] **P1-027** — Refactor contracts models to use resolve_player_id_from_name macro (code deduplication, bug fixes)

### FFAnalytics Models (1 ticket) ⚠️ **Priority: Fixes 195 duplicates**

- [x] **P1-016** — Update stg_ffanalytics\_\_projections model (latest_only)

### Data Quality Follow-ups (9 tickets) ⚠️ **Discovered during comprehensive test analysis**

**Recent Achievements** (2025-11-12):

- ✅ **P1-026 COMPLETE**: Macro cartesian product regression fixed (3,563 transaction duplicates eliminated)
- ✅ **P1-019 COMPLETE**: Streaming hypothesis VALIDATED - All roster parity discrepancies resolved (30→0 failures)
  - Root cause: 4 player_id resolution bugs (K→PK mapping, dual-eligibility, multi-position notation, position-aware aliases)
  - Quick fixes applied to macro + inline logic; full refactor tracked in P1-027
- ✅ **P1-020 COMPLETE**: TBD pick duplicates fixed (22 pick_ids → 0)
- ✅ **P1-022 COMPLETE**: Orphan pick references resolved (46 orphans → 0)

**Recommended Execution Order** (remaining tickets):

1. [x] **P1-026** — 🚨 Fix resolve_player_id_from_name macro cartesian product ✅ **COMPLETE** (2025-11-11)
2. [x] **P1-020** — Fix dim_pick_lifecycle_control TBD pick duplicates ✅ **COMPLETE** (2025-11-11)
3. [x] **P1-023** — Fix assert_12_base_picks_per_round failures ✅ **COMPLETE** (2025-11-12) - **100% SUCCESS** (4→0 failures)
4. [x] **P1-024** — Fix int_pick_comp_registry duplicate transaction IDs ✅ **COMPLETE** (2025-11-10) - **100% SUCCESS** (19→0 duplicates)
5. [x] **P1-022** — Resolve orphan pick references ✅ **COMPLETE** (2025-11-11)
6. [x] **P1-019** — Investigate Sleeper-Commissioner roster parity failures ✅ **COMPLETE** (2025-11-12) - **100% SUCCESS** (30→0 failures)
7. [x] **P1-018** — Fix stg_ffanalytics\_\_projections source data duplicates ✅ **COMPLETE** (2025-11-13) - **100% SUCCESS** (34→0 duplicates, architectural fix)
8. [ ] **P1-017** — Fix mrt_fasa_targets duplicate rows (Medium: 4-6 hours - 1,893 mart duplicates)
9. [ ] **P1-025** — Investigate assert_idp_source_diversity failures (Small: 1-2 hours - 3 failures, LOW PRIORITY)

**Rationale**: Major progress on data quality! P1-026 regression fixed, roster parity fully resolved via player_id fixes (P1-019), and pick integrity issues resolved (P1-020, P1-022). Continue with remaining pick validation (P1-023, P1-024), then tackle projection/mart duplicates (P1-018, P1-017). P1-025 is lowest priority (data quality warning). P1-027 tracks technical debt cleanup.

### Sample Cleanup & Validation

- [ ] **P1-005** — Archive legacy sample artifacts from fully integrated sources
- [ ] **P1-006** — Performance profiling for all updated models

______________________________________________________________________

## Phase 2: Governance (7 tickets)

- [ ] **P2-001** — Create snapshot registry seed
- [ ] **P2-002** — Populate snapshot registry with all 5 sources
- [ ] **P2-003** — Extend analyze_snapshot_coverage - row deltas
- [ ] **P2-004** — Extend analyze_snapshot_coverage - gap detection
- [ ] **P2-005** — Create validate_manifests tool
- [ ] **P2-006** — Add freshness tests (frequently updated: nflverse, sheets, sleeper)
- [ ] **P2-007** — Add freshness tests (weekly/sporadic: ktc, ffanalytics)

______________________________________________________________________

## Phase 3: Documentation (8 tickets)

- [ ] **P3-001** — Update SPEC v2.3 checklist
- [ ] **P3-002** — Create snapshot_management_current_state doc
- [ ] **P3-003** — Create ingestion_triggers_current_state doc
- [ ] **P3-004** — Create data_freshness_current_state doc
- [ ] **P3-005** — Create orchestration_architecture doc
- [ ] **P3-006** — Create ci_transition_plan doc
- [ ] **P3-007** — Create cloud_storage_migration doc
- [ ] **P3-008** — Update dbt model documentation

______________________________________________________________________

## Phase 4: Orchestration (7 tickets)

- [ ] **P4-001** — Create flows directory and shared utilities
- [ ] **P4-002a** — Implement copy_league_sheet_flow (copy tabs from Commissioner sheet)
- [ ] **P4-002** — Implement parse_league_sheet_flow (parse copied sheet, depends on P4-002a)
- [ ] **P4-003** — Implement nfl_data_pipeline flow
- [ ] **P4-004** — Implement ktc_pipeline flow
- [ ] **P4-005** — Implement ffanalytics_pipeline flow
- [ ] **P4-006** — Implement sleeper_pipeline flow

______________________________________________________________________

## Phase 5: CI Planning (2 tickets)

- [ ] **P5-001** — Document parallel run and rollback strategy
- [ ] **P5-002** — Document validation criteria and comparison process

______________________________________________________________________

## Phase 6: Cloud Blueprint (4 tickets)

- [ ] **P6-001** — Document GCS bucket layout and lifecycle policies
- [ ] **P6-002** — Document IAM requirements and service account setup
- [ ] **P6-003** — Document DuckDB GCS configuration
- [ ] **P6-004** — Create migration checklist and optional sync utility

______________________________________________________________________

## Cross-Cutting Tasks (2 tickets)

- [ ] **CC-001** — Create comparison testing framework
- [ ] **CC-002** — Audit notebooks for hardcoded date filters

______________________________________________________________________

## Progress Summary

**Overall Project**: 23/58 tickets complete (40%)\
**Phase 1 Foundation**: 23/27 tickets complete (85%)\
**In Progress**: 0 tickets\
**Blocked**: 0 tickets

**Recent Progress** (2025-11-13):

- ✅ **P1-018 COMPLETE**: FFAnalytics source data duplicates ELIMINATED (34→0 duplicates)
  - Architectural fix: moved alias application BEFORE consensus aggregation
  - All 12 staging tests passing including grain test
  - Consensus rows reduced from 9,249 → 9,188 (61 duplicates deduplicated at source)
- ✅ **P1-023 COMPLETE**: Base picks per round validation 100% resolved (4→0 failures)

**Previous Progress** (2025-11-12):

- ✅ **P1-019 COMPLETE**: Streaming hypothesis validated - roster parity test PASSING (30→0 failures)
  - Discovered and fixed 4 critical player_id resolution bugs
  - K→PK mapping, dual-eligibility, multi-position notation, position-aware aliases all fixed
  - Created P1-027 to track full refactor (remove inline logic from contracts models)
- ✅ **P1-026 COMPLETE**: Macro cartesian product regression fixed (3,563 duplicates → 0)
- ✅ **P1-020 COMPLETE**: TBD pick duplicates resolved (22 pick_ids → 0)
- ✅ **P1-022 COMPLETE**: Orphan pick references resolved (46 orphans → 0)

**Historical Notes**:

- **2025-11-13**: P1-018 architectural fix complete - moved alias application before consensus aggregation, eliminating all 34 source data duplicates; P1-023 validation complete (100% success)
- **2025-11-12**: P1-019 streaming hypothesis validated with 4 critical player_id bugs fixed; P1-027 created to track full refactor of contracts models
- **2025-11-11**: P1-026 cartesian product regression fixed; P1-020 and P1-022 resolved (TBD picks and orphan references)
- **2025-11-10**: Comprehensive test analysis revealed 3 new data quality issues requiring tickets (P1-023, P1-024, P1-025); P1-021 now passing and removed
- P1-009: Snapshot governance fix complete; pre-existing roster parity test failure (30 discrepancies - separate ticket P1-019 created)
- P1-011: Snapshot governance fix complete; downstream testing revealed TBD pick duplicates (22 pick_ids - separate ticket P1-020 created)
- P1-012: Snapshot governance fix complete; reduced orphan picks from 41→5 in fact table (87% improvement - separate ticket P1-022 created for remaining 5 + 41 staging orphans)
- P1-013: Staging model fix complete, but downstream mart duplicates persist (separate ticket P1-017 created)
- P1-016: Snapshot governance fix complete; reduced cross-snapshot duplicates from 33→17 (staging) and 162→101 (fact table). Remaining 17 duplicates are source data quality issues (player name variations: "DJ Moore" vs "Moore, D.J." - separate ticket P1-018 created)

______________________________________________________________________

## Critical Path

The following tickets represent the critical path for achieving minimum viable governance:

01. **P0-001** → Scope confirmation ✅
02. **P1-001** → Macro foundation ✅
03. **P1-013, P1-016** → High-priority staging model updates ✅
04. **P1-002, P1-003, P1-004** → NFLverse baseline models ✅
05. **P1-007 through P1-015** → Remaining staging models ✅
06. **Data Quality Fixes** (9 tickets):
    - **P1-026** → Macro cartesian product fix ✅ **COMPLETE**
    - **P1-020** → TBD pick duplicates ✅ **COMPLETE**
    - **P1-022** → Orphan pick references ✅ **COMPLETE**
    - **P1-019** → Roster parity investigation ✅ **COMPLETE** - Streaming hypothesis validated
    - **P1-023** → Base picks per round validation ✅ **COMPLETE** (100% resolved)
    - **P1-024** → Comp registry duplicates ✅ **COMPLETE** (2025-11-10)
    - **P1-018** → Source data duplicates (pending)
    - **P1-017** → Mart duplicates (pending)
    - **P1-025** → IDP source diversity (low priority)
07. **P1-027** → Refactor contracts models (architectural cleanup)
08. **P2-001, P2-002** → Registry creation
09. **P2-005** → Validation tooling
10. **P2-006, P2-007** → Freshness tests
11. **P3-001** → SPEC update

______________________________________________________________________

## Dependencies Map

### Must Complete First

- **P1-001** must be done before all other P1 tickets (macro foundation)
- **P2-001** must be done before P2-002
- **P2-003** must be done before P2-004
- **P4-001** must be done before P4-002a through P4-006
- **P4-002a** must be done before P4-002 (copy flow before parse flow)

### Can Be Done in Parallel

- After P1-001, all staging model updates (P1-002 through P1-016) can be done in parallel
  - **Suggested priority**: P1-013 and P1-016 first (standardize high-impact models)
  - **Then**: P1-002, P1-003, P1-004 (NFLverse baseline models)
  - **Finally**: Remaining 7 models (P1-007 through P1-012, P1-014, P1-015)
- **P1-017** (mart fix) can run in parallel with late staging models or P1-005/P1-006
  - Dependency: P1-013 must be complete (to rule out staging as root cause)
  - Should be resolved before Phase 2 (governance) begins
- **P1-018** (FFAnalytics source deduplication) can run in parallel with other staging models
  - Dependency: P1-016 must be complete (to rule out snapshot selection as root cause)
  - Can be addressed after Phase 1 staging updates complete
- **P1-019** (roster parity investigation) can run in parallel with other staging models
  - Dependency: P1-009 must be complete (to rule out snapshot selection as root cause)
  - Not blocking other work; can be addressed after Phase 1 staging updates complete
- **P1-020** (TBD pick duplicates) can run in parallel with P1-015
  - Dependency: P1-011 must be complete (to rule out staging as root cause)
  - Not blocking other work; data modeling issue separate from snapshot governance
- **P1-023, P1-024, P1-025** (new data quality tickets) can run in parallel with each other
  - No dependencies; data validation and integrity issues
  - Can be sequenced for efficiency (pick-related issues first)
- **P1-022** (orphan pick references) can run in parallel with other Phase 1 tickets ✅ **COMPLETE**
  - Dependency: P1-012 must be complete (snapshot governance already reduced issue 87%)
  - Not blocking other work; low priority since only 5 orphans remain
- **P1-027** (refactor contracts models) should wait for P1-026 to be complete
  - Dependency: P1-026 must be complete (macro with cartesian product fix)
  - Technical debt cleanup - removes inline logic duplication
  - Can be done in parallel with other Phase 1 tickets once P1-026 is done
- All Phase 3 documentation tickets (P3-001 through P3-008) are independent
- Phase 4 flow tickets (P4-003 through P4-006) can be done in parallel after P4-001
- **Note**: P4-002a and P4-002 are sequential (copy flow before parse flow)
- Phase 5 and Phase 6 tickets are all documentation and can be done in parallel

______________________________________________________________________

## Success Metrics

Implementation is complete when:

- [x] Zero hardcoded snapshot dates in all 13 staging models (P1-002 through P1-016) ✅
- [x] All staging models use snapshot_selection_strategy macro (P1-001 through P1-016) ✅
- [-] All current test failures resolved:
  - [x] Snapshot governance duplicates eliminated (P1-016: 33→17 staging, 162→101 fact) ✅ **COMPLETE**
  - [x] Source data duplicates eliminated (P1-018: 34→0 duplicates, architectural fix) ✅ **100% SUCCESS**
  - [ ] Mart duplicates eliminated (P1-017: 1,893→0)
  - [x] Roster parity discrepancies resolved (P1-019: 30→0) ✅ **100% SUCCESS** - Streaming hypothesis validated
  - [x] TBD pick duplicates eliminated (P1-020: 22 pick_ids→0) ✅ **COMPLETE**
  - [x] Orphan pick references resolved (P1-022: 46 orphans→0) ✅ **COMPLETE**
  - [x] Base picks per round validated (P1-023: 21→0 violations) ✅ **100% SUCCESS**
  - [x] Comp registry duplicates eliminated (P1-024: 19 duplicates→0) ✅ **COMPLETE** (2025-11-10)
  - [ ] IDP source diversity validated (P1-025: 3 failures→0 or test downgraded to warning)
  - [ ] Player ID resolution refactored (P1-027: contracts models use macro consistently)
- [ ] Snapshot registry tracking current/historical snapshots (P2-001, P2-002)
- [ ] Working Prefect flows for all 5 sources (P4-002 through P4-006)
- [ ] Freshness tests providing pre-dbt safety net (P2-006, P2-007)
- [ ] CI transition plan documented (P5-001, P5-002)
- [ ] Cloud migration blueprint complete (P6-001 through P6-004)

______________________________________________________________________

## Notes

- Update ticket status in this file as work progresses
- Link individual ticket files for detailed context and implementation notes
- Each ticket is designed to be completable in one developer session (2-4 hours)
- All tickets follow the standard template defined in the implementation plan
