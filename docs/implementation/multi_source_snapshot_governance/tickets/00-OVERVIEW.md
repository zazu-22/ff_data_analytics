# Multi-Source Snapshot Governance — Ticket Tracking Overview

**Version**: 2.0\
**Date**: 2025-11-07\
**Status**: Active

______________________________________________________________________

This document provides a concise checklist for tracking completion of all implementation tickets for the Multi-Source Snapshot Governance effort.

## Quick Reference

- **Total Tickets**: 57 (includes 13 staging models + 9 data quality fixes + 1 architectural refactor)
- **Total Phases**: 7 (Phase 0-6 + Cross-Cutting)
- **Estimated Total Effort**: ~172-212 hours (updated for expanded Phase 1 + data quality fixes)
- **Parent Plan**: `../2025-11-07_plan_v_2_0.md`
- **Task Checklist**: `../2025-11-07_tasks_checklist_v_2_0.md`

## Ticket Status Legend

- `[ ]` Not Started
- `[-]` In Progress
- `[x]` Complete
- `[~]` Blocked (with blocker noted)

______________________________________________________________________

## Phase 0: Kickoff & Decision Ratification (1 ticket)

- [x] **P0-001** — Scope ratification and blocker identification

______________________________________________________________________

## Phase 1: Foundation (25 tickets - 13 staging models + 9 data quality fixes + 1 architectural refactor)

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

### FFAnalytics Models (1 ticket) ⚠️ **Priority: Fixes 195 duplicates**

- [x] **P1-016** — Update stg_ffanalytics\_\_projections model (latest_only)

### Data Quality Follow-ups (9 tickets) ⚠️ **Discovered during comprehensive test analysis**

**🚨 CRITICAL BLOCKER**: P1-026 must be fixed IMMEDIATELY - it's a regression introduced in P1-019 that causes 6.8x row duplication.

**Recommended Execution Order** (sequential on main branch, no file conflicts):

1. [x] **P1-026** — 🚨 **CRITICAL: Fix resolve_player_id_from_name macro cartesian product** (Small: 1-2 hours - 3,563 transaction duplicates) ✅ **COMPLETE**
2. [x] **P1-020** — Fix dim_pick_lifecycle_control TBD pick duplicates (Medium: 3-5 hours - 22 pick_ids) ✅ **COMPLETE**
3. [-] **P1-023** — Fix assert_12_base_picks_per_round failures (Medium: 3-4 hours - 21 violations) ⚠️ **81% IMPROVED** (21→4)
4. [x] **P1-024** — Fix int_pick_comp_registry duplicate transaction IDs (Small-Medium: 2-3 hours - 19 duplicates) ✅ **COMPLETE**
5. [x] **P1-022** — Resolve orphan pick references (Small-Medium: 2-4 hours - 5 fact + 41 staging orphans) ✅ **COMPLETE**
6. [x] **P1-019** — Investigate Sleeper-Commissioner roster parity failures (Medium: 3-5 hours - 30 discrepancies) ✅ **COMPLETE** (2/3 fixed: 30→28 failures)
7. [ ] **P1-018** — Fix stg_ffanalytics\_\_projections source data duplicates (Medium: 3-5 hours - 17 staging duplicates)
8. [ ] **P1-017** — Fix mrt_fasa_targets duplicate rows (Medium: 4-6 hours - 1,893 mart duplicates)
9. [ ] **P1-025** — Investigate assert_idp_source_diversity failures (Small: 1-2 hours - 3 failures, LOW PRIORITY)

**Rationale**: P1-026 regression fixed (6.8x transaction duplication eliminated). Continue with pick-related data integrity issues (P1-020, P1-023, P1-024, P1-022) to ensure foundation, then tackle cross-source reconciliation (P1-019), followed by projection/mart duplicates (P1-018, P1-017). P1-025 is lowest priority (data quality warning). All can be done on main branch - zero file conflicts between tickets.

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

**Completed**: 16/56 (29%)\
**In Progress**: 0/56\
**Blocked**: 0/56\
**Remaining**: 40/56

**Notes**:

- **2025-11-10**: Comprehensive test analysis revealed 3 new data quality issues requiring tickets (P1-023, P1-024, P1-025); P1-021 now passing and removed
- P1-009: Snapshot governance fix complete; pre-existing roster parity test failure (30 discrepancies - separate ticket P1-019 created)
- P1-011: Snapshot governance fix complete; downstream testing revealed TBD pick duplicates (22 pick_ids - separate ticket P1-020 created)
- P1-012: Snapshot governance fix complete; reduced orphan picks from 41→5 in fact table (87% improvement - separate ticket P1-022 created for remaining 5 + 41 staging orphans)
- P1-013: Staging model fix complete, but downstream mart duplicates persist (separate ticket P1-017 created)
- P1-016: Snapshot governance fix complete; reduced cross-snapshot duplicates from 33→17 (staging) and 162→101 (fact table). Remaining 17 duplicates are source data quality issues (player name variations: "DJ Moore" vs "Moore, D.J." - separate ticket P1-018 created)

______________________________________________________________________

## Critical Path

The following tickets represent the critical path for achieving minimum viable governance:

01. **P0-001** → Scope confirmation
02. **P1-001** → Macro foundation
03. **P1-013, P1-016** → High-priority staging model updates
04. **P1-002, P1-003, P1-004** → NFLverse baseline models
05. **P1-007 through P1-015** → Remaining staging models (can be parallelized)
06. **P1-017, P1-018, P1-019, P1-020, P1-022, P1-023, P1-024, P1-025** → Data quality fixes (8 tickets addressing duplicates, orphan references, and data integrity issues discovered during comprehensive test analysis)
07. **P2-001, P2-002** → Registry creation
08. **P2-005** → Validation tooling
09. **P2-006, P2-007** → Freshness tests
10. **P3-001** → SPEC update

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
- **P1-022** (orphan pick references) can run in parallel with other Phase 1 tickets
  - Dependency: P1-012 must be complete (snapshot governance already reduced issue 87%)
  - Not blocking other work; low priority since only 5 orphans remain
- All Phase 3 documentation tickets (P3-001 through P3-008) are independent
- Phase 4 flow tickets (P4-003 through P4-006) can be done in parallel after P4-001
- **Note**: P4-002a and P4-002 are sequential (copy flow before parse flow)
- Phase 5 and Phase 6 tickets are all documentation and can be done in parallel

______________________________________________________________________

## Success Metrics

Implementation is complete when:

- [ ] Zero hardcoded snapshot dates in all 13 staging models (P1-002 through P1-016)
- [ ] All staging models use snapshot_selection_strategy macro (P1-001 through P1-016)
- [ ] All current test failures resolved:
  - [ ] Snapshot governance duplicates eliminated (P1-016: 33→17 staging, 162→101 fact)
  - [ ] Source data duplicates eliminated (P1-018: 17→0 staging, 101→0 fact)
  - [ ] Mart duplicates eliminated (P1-017: 1,893→0)
  - [ ] Roster parity discrepancies investigated and resolved (P1-019: 30→0 or documented)
  - [ ] TBD pick duplicates eliminated (P1-020: 22 pick_ids→0 or grain clarified)
  - [ ] Orphan pick references resolved (P1-022: 5 fact + 41 staging→0 or documented exceptions)
  - [ ] Base picks per round validated (P1-023: 21 violations→0)
  - [ ] Comp registry duplicates eliminated (P1-024: 19 duplicates→0)
  - [ ] IDP source diversity validated (P1-025: 3 failures→0 or test downgraded to warning)
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
