# Snapshot Governance Implementation — Harmonization Decisions

**Date**: 2025-11-06
**Status**: Team decisions confirmed
**Full analysis**: `snapshot_governance_plan_comparison.md`

______________________________________________________________________

## Team Decisions (Confirmed)

### 1. ✅ Prefect Orchestration Scope

**Decision**: **All 5 sources** (nflverse, sheets, ktc, ffanalytics, sleeper)

- Implement Prefect Phases 1+2 upfront
- Standardize now to prevent drift and inconsistencies
- Earlier standardization would have solved current problems

**Adopts**: Plan 2's broader scope

______________________________________________________________________

### 2. ✅ Freshness Coverage

**Decision**: **Include Sleeper** with all other sources

- All 5 sources get freshness checks
- Use `loaded_at_field: dt` with per-source warn/error thresholds

**Adopts**: Plan 2's comprehensive coverage

______________________________________________________________________

### 3. ✅ Timeline Estimates

**Decision**: **Ignore hour/effort estimates**

- Not relevant for AI coding assistants
- Focus on technical deliverables and scope completion
- Let implementation drive timeline naturally

______________________________________________________________________

### 4. ✅ Validation Tooling

**Decision**: **Extend existing tool**

- `tools/analyze_snapshot_coverage.py` exists → extend it
- Add row deltas, coverage gaps, mapping rates per Plan 2
- Create complementary `tools/validate_manifests.py` for registry-driven checks

**Adopts**: Plan 2's extension approach

______________________________________________________________________

## Implementation Approach

### Phase Structure

| Phase                        | Key Deliverables                                                           |
| ---------------------------- | -------------------------------------------------------------------------- |
| **Phase 0** (Optional)       | Scope ratification, registry approval, success metrics definition          |
| **Phase 1: Foundation**      | Macro, staging updates, samples relocation, performance profiling          |
| **Phase 2: Governance**      | Registry seed, validation tooling, freshness checks (all 5 sources)        |
| **Phase 3: Documentation**   | SPEC checklist first, then 6 ops docs                                      |
| **Phase 4: Orchestration**   | **Prefect flows for all 5 sources**, local testing, governance integration |
| **Phase 5: CI Planning**     | Parallel run strategy, rollback procedures                                 |
| **Phase 6: Cloud Blueprint** | GCS migration doc (docs only, no infra)                                    |

______________________________________________________________________

### Key Technical Selections

1. **Macro**: Plan 2's `snapshot_selection_strategy(source_glob, strategy, baseline_dt)`

   - Strategies: `latest_only`, `baseline_plus_latest`, `all`

2. **Sample paths**: Plan 3's explicit structure

   - `data/raw/<source>/_samples/<dataset>/dt=YYYY-MM-DD/`

3. **Staging updates**: Combination approach

   - Verify hardcoded dates (Plan 2)
   - Preserve `union_by_name=true` (Plan 3)
   - Add comparison tests (Plan 2)

4. **Prefect flows**: Plan 2's comprehensive scope

   - All 5 sources: `google_sheets_pipeline.py`, `nfl_data_pipeline.py`, `ktc_pipeline.py`, `ffanalytics_pipeline.py`, `sleeper_pipeline.py`

______________________________________________________________________

### Success Metrics

- [ ] Zero hardcoded snapshot dates in staging models
- [ ] Snapshot registry tracking current/historical snapshots for all sources
- [ ] Working Prefect flows for all 5 sources (local execution)
- [ ] Freshness tests providing pre-dbt safety net (all 5 sources including Sleeper)
- [ ] CI transition plan documented with rollback procedures
- [ ] Cloud migration blueprint complete

______________________________________________________________________

## Still to Decide

1. **Phase 0 adoption**: Formalize kickoff decision gate or start directly with Phase 1?
2. **GCS prerequisites**: Blockers for Phase 6 cloud blueprint or work around initially?
3. **Validation tooling in CI**: Run `validate_manifests.py` in CI or local-only initially?

______________________________________________________________________

## What Each Plan Contributes

| Plan       | Key Contributions to Harmonized Approach                                                                                        |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------- |
| **Plan 1** | Phase 0 kickoff concept, regression comparison queries, weekly check-ins                                                        |
| **Plan 2** | ✅ **Orchestration scope** (all 5 sources), detailed macro implementation, success metrics framework, validation tool extension |
| **Plan 3** | ✅ **Sample path structure**, schema drift handling (`union_by_name=true`), explicit deliverables                               |

______________________________________________________________________

## Next Steps

1. **Decide on Phase 0**: Formalize scope or proceed directly to implementation?
2. **Begin Phase 1**: Implement `snapshot_selection_strategy` macro and update NFLverse staging models
3. **Track progress**: Update SPEC checklist and maintain ops documentation as implementation progresses
4. **Validate early**: Add comparison tests before rolling out changes to prevent regressions

______________________________________________________________________

## Out of Scope

- Prefect Phases 3-4 (backfill orchestration, advanced monitoring, cloud deployment)
- Actual cloud migration (blueprint only in Phase 6)
- CI cut-over execution (planning only in Phase 5)
- Full GH Actions replacement
