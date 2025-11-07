# Multi-Source Snapshot Governance Plans — Comparison & Harmonization Analysis

**Date**: 2025-11-06
**Purpose**: Identify disagreements and differences across three implementation plan versions to support team harmonization

______________________________________________________________________

## Executive Summary

Three plans propose similar foundations but diverge significantly on **Prefect orchestration scope** (Phase 1 vs Phases 1+2) and **level of prescription** (high-level vs detailed code snippets).

### **Team Decisions (Confirmed)**

1. ✅ **Prefect scope**: **All 5 sources** (nflverse, sheets, ktc, ffanalytics, sleeper) — standardize now to prevent drift
2. ✅ **Freshness coverage**: **Include Sleeper** — all sources get freshness checks
3. ✅ **Timeline**: Ignore hour estimates (irrelevant for AI coding assistants)
4. ⚠️ **Kickoff phase**: TBD - formalize decision gates or start directly with implementation?

**Implication**: **Adopt Plan 2's broader orchestration scope** with technical details from all three plans where they provide the most specificity.

______________________________________________________________________

## 1. MAJOR SCOPE DISAGREEMENTS

### 1.1 Prefect Orchestration Scope

| Plan       | Scope          | Sources                                                         | Rationale                                                                                                       |
| ---------- | -------------- | --------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| **Plan 1** | Phase 1 only   | Sheets + NFLverse (2 sources)                                   | "Prefect scope limited to Phase 1 from docs/spec/prefect\*dbt_sources_migration_20251026.md (local flows only)" |
| **Plan 2** | **Phases 1+2** | **All 5 sources** (nflverse, sheets, ktc, ffanalytics, sleeper) | "Complete ingestion automation for all sources (Phases 1-2 from existing Prefect plan)"                         |
| **Plan 3** | Phase 1 only   | Sheets + NFLverse (2 sources)                                   | "Prefect: Phase 1 only (local flows for Sheets + NFLverse, ~7–8h)"                                              |

**Impact**: Plan 2 requires broader orchestration implementation vs Plans 1/3. This affects testing burden and risk surface.

**✅ DECISION: Adopt Plan 2's all-5-sources approach** — standardizing now prevents future drift and inconsistencies. Earlier standardization would have prevented current problems.

______________________________________________________________________

### 1.2 Timeline & Effort Estimation

| Plan       | Total Duration    | Total Effort                          | Basis                                        |
| ---------- | ----------------- | ------------------------------------- | -------------------------------------------- |
| **Plan 1** | ~5 weeks          | 30-32 hours                           | Phase-by-phase hour estimates                |
| **Plan 2** | **60-90 minutes** | **210-270k tokens ≈ 2-3 AI sessions** | Token budget extrapolation                   |
| **Plan 3** | ~5 weeks          | ~36 hours                             | Phase-by-phase hour estimates (8+10+4+8+2+4) |

**✅ DECISION: Ignore timeline estimates** — not relevant for AI coding assistants. Focus on technical deliverables and scope, not effort prediction.

______________________________________________________________________

### 1.3 Phase 0 Kickoff Gate

| Plan       | Phase 0? | Content                                                                                                                          |
| ---------- | -------- | -------------------------------------------------------------------------------------------------------------------------------- |
| **Plan 1** | ✅ Yes   | Explicit "Kickoff Decisions" phase: confirm Prefect scope, approve registry creation, capture blockers (GCS auth, Prefect Cloud) |
| **Plan 2** | ❌ No    | Starts directly with Phase 1 foundation work                                                                                     |
| **Plan 3** | ❌ No    | Starts directly with Phase 1 foundation work                                                                                     |

**Impact**: Plan 1 forces upfront alignment on scope and prerequisites; Plans 2/3 assume these are already decided.

**Recommendation**: **Adopt Phase 0 concept** to prevent mid-implementation scope creep. Use it to ratify Prefect scope, registry approach, and cloud timeline.

______________________________________________________________________

## 2. TECHNICAL IMPLEMENTATION DIFFERENCES

### 2.1 Freshness Check Coverage

| Plan       | Sources Covered                                          |
| ---------- | -------------------------------------------------------- |
| **Plan 1** | "all providers" (unspecified)                            |
| **Plan 2** | nflverse, sheets, sleeper, ffanalytics, ktc (5 sources)  |
| **Plan 3** | nflverse, sheets, ktc, ffanalytics (**sleeper missing**) |

**Impact**: Plan 3 omits Sleeper freshness checks despite including it elsewhere.

**✅ DECISION: Include all 5 sources including Sleeper** — align with Plan 2's comprehensive coverage.

______________________________________________________________________

### 2.2 Sample Data Path Structure

| Plan       | Path Pattern                               | Example                   |
| ---------- | ------------------------------------------ | ------------------------- |
| **Plan 1** | `data/raw/<source>/_samples/`              | Generic pattern           |
| **Plan 2** | `data/raw/nflverse/_samples/weekly/`       | NFLverse-specific example |
| **Plan 3** | `data/raw/<source>/_samples/<dataset>/...` | Most specific pattern     |

**Impact**: Plan 3's structure is most explicit about preserving dataset hierarchy under `_samples/`.

**Recommendation**: **Adopt Plan 3 pattern** for consistency: `data/raw/<source>/_samples/<dataset>/dt=YYYY-MM-DD/`.

______________________________________________________________________

### 2.3 Validation Tooling Extensions

| Plan       | Tool Updates                                                                                                                         |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| **Plan 1** | Create `tools/validate_manifests.py` to cross-check manifests, `_meta.json`, and registry expectations                               |
| **Plan 2** | Create `tools/validate_manifests.py` **+ extend** `tools/analyze_snapshot_coverage.py` with row deltas, coverage gaps, mapping rates |
| **Plan 3** | Create `tools/validate_manifests.py` (row counts, season/week gaps, mapping coverage)                                                |

**Impact**: Plan 2 extends an existing tool while Plans 1/3 focus on net-new tooling. If `analyze_snapshot_coverage.py` already exists, Plan 2's approach avoids duplication.

**Recommendation**: **Check if** `tools/analyze_snapshot_coverage.py` **exists**. If yes, adopt Plan 2's extension approach; if no, consolidate all validation logic into `validate_manifests.py` per Plans 1/3.

______________________________________________________________________

### 2.4 Snapshot Selection Macro Strategies

All plans propose a `snapshot_selection_strategy` macro, but **Plan 2** provides the most detailed implementation:

```sql
-- Plan 2's detailed macro signature
{% macro snapshot_selection_strategy(source_glob, strategy='latest_only', baseline_dt=none) %}
  {% if strategy == 'latest_only' %}
    and {{ latest_snapshot_only(source_glob) }}
  {% elif strategy == 'baseline_plus_latest' %}
    and (dt = '{{ baseline_dt }}' or {{ latest_snapshot_only(source_glob) }})
  {% elif strategy == 'all' %}
    -- No filter (for backfills)
  {% endif %}
{% endmacro %}
```

**Impact**: Plan 2's code snippet provides clearest implementation guidance for developers.

**Recommendation**: **Use Plan 2's macro structure** as the implementation baseline. Plans 1/3 describe the same functionality more abstractly.

______________________________________________________________________

### 2.5 Staging Model Update Specifics

| Plan       | Models Mentioned                                                                          | Special Notes                                                                                      |
| ---------- | ----------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| **Plan 1** | `stg_nflverse__player_stats`, `stg_nflverse__snap_counts`, `stg_nflverse__ff_opportunity` | Update first two; third already uses macro                                                         |
| **Plan 2** | `stg_nflverse__player_stats`, `stg_nflverse__snap_counts`                                 | Hardcoded dates specified: `dt IN ('2025-10-01', '2025-10-27')` and `('2025-10-01', '2025-10-28')` |
| **Plan 3** | Same as Plan 1                                                                            | Adds "keep `union_by_name=true` where schema can drift"                                            |

**Impact**: Plan 2 documents current hardcoded values (useful for verification). Plan 3 emphasizes schema drift handling.

**Recommendation**: **Combine approaches** — verify current hardcoded dates per Plan 2, implement macro replacement per Plan 1, preserve `union_by_name=true` per Plan 3.

______________________________________________________________________

## 3. DOCUMENTATION DIFFERENCES

### 3.1 Documentation Priority & Approach

| Plan       | Priority Statement                                                        | First Doc to Update |
| ---------- | ------------------------------------------------------------------------- | ------------------- |
| **Plan 1** | "Update docs/spec/SPEC-1_v_2.3_implementation_checklist_v_0.md **first**" | SPEC checklist      |
| **Plan 2** | "**Priority order**: Update SPEC checklist first, then create new docs"   | SPEC checklist      |
| **Plan 3** | "Update docs/spec/SPEC-1_v_2.3_implementation_checklist_v_0.md **first**" | SPEC checklist      |

**Impact**: All three agree on updating SPEC checklist first — this is a consistent anchor.

**Recommendation**: **Confirm alignment** — SPEC checklist drives documentation structure.

______________________________________________________________________

### 3.2 New Documentation Files

All plans propose similar ops docs, with minor variations:

| Doc File                               | Plan 1           | Plan 2       | Plan 3                       |
| -------------------------------------- | ---------------- | ------------ | ---------------------------- |
| `snapshot_management_current_state.md` | ✅               | ✅           | ✅                           |
| `ingestion_triggers_current_state.md`  | ✅               | ✅           | ✅                           |
| `data_freshness_current_state.md`      | ✅               | ✅           | ✅                           |
| `orchestration_architecture.md`        | ✅ (consolidate) | ✅ (new)     | ✅ (current-state reference) |
| `ci_transition_plan.md`                | ✅ (Week 4)      | ✅ (Phase 3) | ✅ (Week 4)                  |
| `cloud_storage_migration.md`           | ✅ (Week 5)      | ✅ (Phase 4) | ✅ (Week 5)                  |

**Impact**: Agreement on doc set; minor timing differences.

**Recommendation**: **Adopt common doc set** across all plans. Timing aligns (Week 4-5 for CI/cloud docs).

______________________________________________________________________

## 4. PHASE STRUCTURE COMPARISON

### Phase Timing Summary

| Phase               | Plan 1                     | Plan 2                       | Plan 3                       | Consensus?          |
| ------------------- | -------------------------- | ---------------------------- | ---------------------------- | ------------------- |
| **Kickoff**         | Phase 0 (Day 0)            | —                            | —                            | ❌ (adopt?)         |
| **Foundation**      | Week 1, ~8h                | ~50-60k tokens               | Week 1, ~8h                  | ✅ ~8h              |
| **Governance**      | Week 2, ~10h               | ~60-80k tokens               | Week 2, ~10h                 | ✅ ~10h             |
| **Documentation**   | Week 2, ~6h                | (in Phase 2)                 | Week 2, ~4h                  | ⚠️ 4-6h             |
| **Orchestration**   | Week 3, ~8h (Phase 1 only) | ~80-100k tokens (Phases 1+2) | Week 3-4, ~8h (Phase 1 only) | ❌ **KEY DECISION** |
| **CI Planning**     | Week 4, ~4h                | (in Phase 3)                 | Week 4, ~2h                  | ⚠️ 2-4h             |
| **Cloud Blueprint** | Week 5, ~4h                | ~20-30k tokens               | Week 5, ~4h                  | ✅ ~4h              |

______________________________________________________________________

## 5. SUCCESS METRICS & ACCEPTANCE CRITERIA

| Plan       | Section Name              | Detail Level                                                                                                                         |
| ---------- | ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| **Plan 1** | "Cross-Cutting Practices" | General (regression comparison, rollback, weekly check-ins)                                                                          |
| **Plan 2** | "Success Metrics"         | **Most detailed** (6 explicit criteria: zero hardcoded dates, registry tracking, 5 flows, freshness tests, CI plan, cloud blueprint) |
| **Plan 3** | "Acceptance Criteria"     | Detailed (5 criteria similar to Plan 2)                                                                                              |

**Impact**: Plan 2 provides clearest definition of done.

**Recommendation**: **Adopt Plan 2's success metrics** as the acceptance test framework. Add to Phase 0 as exit criteria definition.

______________________________________________________________________

## 6. RISKS & OUT-OF-SCOPE

### Risks Identified

| Risk Category              | Plan 1                                                       | Plan 2                                                  | Plan 3                                              |
| -------------------------- | ------------------------------------------------------------ | ------------------------------------------------------- | --------------------------------------------------- |
| **Schema drift**           | Not explicit                                                 | ✅ "union_by_name=true, monitor null rates"             | ✅ "keep union_by_name=true"                        |
| **Breaking changes**       | Not explicit                                                 | ✅ "comparison tests validating row counts"             | Not explicit                                        |
| **Performance**            | ✅ "Profile query performance (DuckDB EXPLAIN)"              | ✅ "Profile UNION queries, consider materialized views" | ✅ "profile with EXPLAIN; consider materialization" |
| **Notebook compatibility** | ✅ "regression comparison queries/security rollback scripts" | ✅ "Audit notebooks for hardcoded dt= filters"          | ✅ "audit notebooks for hardcoded filters"          |

**Recommendation**: **Merge risk catalogs** — all three identify valid concerns. Adopt Plan 2's comparison test recommendation as concrete mitigation.

______________________________________________________________________

### Out-of-Scope Alignment

All plans agree on deferring:

- ✅ Prefect Phases 3-4 (backfill, monitoring, cloud deployment)
- ✅ Actual cloud migration (blueprint only)
- ✅ CI cut-over execution (planning only)

**Plan 2 uniquely defers**:

- Advanced monitoring dashboards
- Full GH Actions replacement

**Recommendation**: Formalize out-of-scope list in Phase 0 to prevent feature creep.

______________________________________________________________________

## 7. CRITICAL HARMONIZATION DECISIONS

### ✅ Decision 1: Prefect Orchestration Scope

**ADOPTED: All 5 sources (Plan 2 approach)**

- **Rationale**: Standardize now to prevent drift and inconsistencies. Earlier standardization would have solved current problems.
- **Sources**: nflverse, sheets, ktc, ffanalytics, sleeper
- **Implementation**: Prefect Phases 1+2 from existing plan

______________________________________________________________________

### ✅ Decision 2: Freshness Coverage

**ADOPTED: Include Sleeper (Plan 2 approach)**

- **Coverage**: All 5 sources get freshness checks
- **Pattern**: Use `loaded_at_field: dt` with per-source warn/error thresholds

______________________________________________________________________

### ✅ Decision 3: Timeline Estimates

**ADOPTED: Ignore hour/effort estimates**

- **Rationale**: Not relevant for AI coding assistants
- **Focus**: Technical deliverables and scope completion, not effort prediction

______________________________________________________________________

### ⚠️ Decision 4: Phase 0 Adoption (TBD)

**Options**:

- **Option A**: Add Phase 0 kickoff to formalize scope, registry approval, success metrics
- **Option B**: Start directly with Phase 1 foundation work

**Considerations**:

- Plan 1 includes explicit kickoff decisions
- Plans 2/3 assume these are pre-decided
- Phase 0 prevents mid-implementation scope creep

______________________________________________________________________

### ✅ Decision 5: Validation Tooling Strategy

**ADOPTED: Extend existing tool (Plan 2 approach)**

- ✅ `tools/analyze_snapshot_coverage.py` **exists**
- Extend with row deltas, coverage gaps, mapping rates per Plan 2
- Create complementary `tools/validate_manifests.py` for registry-driven validation

______________________________________________________________________

## 8. RECOMMENDED HARMONIZED PLAN

### Phase Structure (Based on Team Decisions)

| Phase                           | Key Deliverables                                                                                                                             |
| ------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| **Phase 0: Kickoff** (Optional) | Scope ratification (confirmed: all 5 sources, Sleeper freshness included), registry approval, success metrics                                |
| **Phase 1: Foundation**         | Macro (`snapshot_selection_strategy`), staging model updates (3 NFLverse models), samples relocation, performance profiling                  |
| **Phase 2: Governance**         | Registry seed, validation tooling (extend or create), freshness checks (**all 5 sources including Sleeper**)                                 |
| **Phase 3: Documentation**      | SPEC checklist first, then ops docs (snapshot mgmt, freshness, ingestion triggers, orchestration)                                            |
| **Phase 4: Orchestration**      | **Prefect Phases 1+2 flows for all 5 sources** (sheets, nflverse, ktc, ffanalytics, sleeper), local testing, snapshot governance integration |
| **Phase 5: CI Planning**        | Parallel run strategy, rollback procedures, GH Actions freshness baseline                                                                    |
| **Phase 6: Cloud Blueprint**    | GCS migration doc, optional sync tool outline (docs only, no infra changes)                                                                  |

______________________________________________________________________

### Key Technical Decisions

1. **Macro**: Adopt Plan 2's `snapshot_selection_strategy(source_glob, strategy, baseline_dt)` with `latest_only`, `baseline_plus_latest`, `all` strategies
2. **Sample paths**: `data/raw/<source>/_samples/<dataset>/dt=YYYY-MM-DD/` (Plan 3 pattern)
3. **Freshness**: ✅ **All 5 sources** (nflverse, sheets, ktc, ffanalytics, **sleeper**)
4. **Validation**: ✅ Extend existing `tools/analyze_snapshot_coverage.py` (Plan 2 approach) + create `tools/validate_manifests.py` for registry checks
5. **Staging updates**: Verify current hardcoded dates (Plan 2), preserve `union_by_name=true` (Plan 3), add comparison tests (Plan 2)
6. **Orchestration**: ✅ **All 5 sources** get Prefect flows (Phases 1+2 scope from Plan 2)

______________________________________________________________________

### Success Metrics (Updated for Team Decisions)

- [ ] Zero hardcoded snapshot dates in staging models
- [ ] Snapshot registry tracking current/historical snapshots for **all sources**
- [ ] Working Prefect flows for **all 5 sources** (sheets, nflverse, ktc, ffanalytics, sleeper) — local execution
- [ ] Freshness tests providing pre-dbt safety net (**all 5 sources including Sleeper**)
- [ ] CI transition plan documented with rollback procedures
- [ ] Cloud migration blueprint complete (docs only, no infra changes)

______________________________________________________________________

## 9. REMAINING OPEN QUESTIONS

### ✅ Resolved (Team Decisions)

1. ~~Prefect scope~~ → **All 5 sources (Phases 1+2)**
2. ~~Sleeper freshness~~ → **Include Sleeper**
3. ~~Timeline commitment~~ → **Ignore hour estimates**

### ⚠️ Still Open

1. **Phase 0 adoption**: Formalize kickoff decision gate (Plan 1 approach) or start directly with Phase 1 implementation?
2. ~~`analyze_snapshot_coverage.py` existence~~: ✅ **Tool exists at `tools/analyze_snapshot_coverage.py`** → Adopt Plan 2's extend strategy
3. **GCS prerequisites**: Are GCS auth and bucket access blockers for Phase 6 cloud blueprint, or can they be worked around initially?
4. **Validation tooling priority**: Should `validate_manifests.py` run in CI or remain local-only initially?

______________________________________________________________________

## 10. SUMMARY

### ✅ Team Decisions (Confirmed)

1. **Prefect scope**: **All 5 sources** (Phases 1+2) — standardize now to prevent drift
2. **Freshness coverage**: **Include Sleeper** — all 5 sources get freshness checks
3. **Timeline**: **Ignore hour estimates** — focus on deliverables, not effort prediction

### Major Differences Resolved

| Topic                  | Original Disagreement                              | Resolution                                     |
| ---------------------- | -------------------------------------------------- | ---------------------------------------------- |
| **Prefect scope**      | Phase 1 only (2 sources) vs Phases 1+2 (5 sources) | ✅ **All 5 sources** (Plan 2 approach)         |
| **Sleeper freshness**  | Include vs defer                                   | ✅ **Include**                                 |
| **Timeline estimates** | 30-36h vs 60-90 min                                | ✅ **Ignore** — not relevant for AI assistants |

### Still to Decide

- Phase 0 kickoff gate (formalize vs skip)
- Validation tooling strategy (depends on existing tool check)
- GCS prerequisites impact on Phase 6 cloud blueprint
- CI integration for validation tooling

### Consensus Areas (All Plans Agree)

- ✅ Macro structure and purpose (`snapshot_selection_strategy`)
- ✅ Sample relocation pattern (`data/raw/<source>/_samples/<dataset>/`)
- ✅ Documentation set (6 ops docs + SPEC checklist)
- ✅ Out-of-scope items (actual cloud migration, Prefect Phases 3-4)
- ✅ SPEC checklist-first documentation approach
- ✅ Registry-driven snapshot governance

### Implementation Path Forward

**Adopt harmonized plan with**:

- ✅ **Plan 2's broader orchestration scope** (all 5 sources)
- ✅ **Plan 2's technical implementation details** (most specific)
- ✅ **Plan 3's sample path structure** (most explicit)
- ✅ **Plan 2's success metrics** (most comprehensive)
- ⚠️ **Phase 0 decision TBD** (formalize scope gates vs start directly)
