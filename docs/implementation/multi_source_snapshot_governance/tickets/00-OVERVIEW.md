# Multi-Source Snapshot Governance — Ticket Tracking Overview

**Version**: 2.0\
**Date**: 2025-11-07\
**Status**: Active

______________________________________________________________________

This document provides a concise checklist for tracking completion of all implementation tickets for the Multi-Source Snapshot Governance effort.

## Quick Reference

- **Total Tickets**: 37
- **Total Phases**: 7 (Phase 0-6 + Cross-Cutting)
- **Estimated Total Effort**: ~120-150 hours
- **Parent Plan**: `../2025-11-07_plan_v_2_0.md`
- **Task Checklist**: `../2025-11-07_tasks_checklist_v_2_0.md`

## Ticket Status Legend

- `[ ]` Not Started
- `[-]` In Progress
- `[x]` Complete
- `[~]` Blocked (with blocker noted)

______________________________________________________________________

## Phase 0: Kickoff & Decision Ratification (1 ticket)

- [ ] **P0-001** — Scope ratification and blocker identification

______________________________________________________________________

## Phase 1: Foundation (6 tickets)

- [ ] **P1-001** — Create snapshot_selection_strategy macro
- [ ] **P1-002** — Update stg_nflverse\_\_player_stats model (baseline_plus_latest)
- [ ] **P1-003** — Update stg_nflverse\_\_snap_counts model (baseline_plus_latest)
- [ ] **P1-004** — Update stg_nflverse\_\_ff_opportunity model (latest_only, consistency)
- [ ] **P1-005** — Archive legacy sample artifacts from fully integrated sources
- [ ] **P1-006** — Performance profiling for all three models

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

**Completed**: 0/37 (0%)\
**In Progress**: 0/37\
**Blocked**: 0/37\
**Remaining**: 37/37

______________________________________________________________________

## Critical Path

The following tickets represent the critical path for achieving minimum viable governance:

1. **P0-001** → Scope confirmation
2. **P1-001** → Macro foundation
3. **P1-002, P1-003** → Staging model updates
4. **P2-001, P2-002** → Registry creation
5. **P2-005** → Validation tooling
6. **P2-006, P2-007** → Freshness tests
7. **P3-001** → SPEC update

______________________________________________________________________

## Dependencies Map

### Must Complete First

- **P1-001** must be done before P1-002, P1-003
- **P2-001** must be done before P2-002
- **P2-003** must be done before P2-004
- **P4-001** must be done before P4-002a through P4-006
- **P4-002a** must be done before P4-002 (copy flow before parse flow)

### Can Be Done in Parallel

- All Phase 3 documentation tickets (P3-001 through P3-008) are independent
- Phase 4 flow tickets (P4-003 through P4-006) can be done in parallel after P4-001
- **Note**: P4-002a and P4-002 are sequential (copy before parse)
- Phase 5 and Phase 6 tickets are all documentation and can be done in parallel

______________________________________________________________________

## Success Metrics

Implementation is complete when:

- [ ] Zero hardcoded snapshot dates in staging models (P1-002, P1-003)
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
