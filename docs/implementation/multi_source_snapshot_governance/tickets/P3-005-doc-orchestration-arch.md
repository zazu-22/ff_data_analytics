# Ticket P3-005: Create orchestration_architecture Doc

**Phase**: 3 - Documentation\
**Estimated Effort**: Small (2 hours)\
**Dependencies**: P3-001

## Objective

Create `docs/ops/orchestration_architecture.md` documenting current orchestration architecture, Prefect plan status, local vs cloud execution state, and dependencies between ingestion jobs.

## Context

This doc provides architectural overview of how data ingestion is orchestrated, explaining the transition from GitHub Actions to Prefect and the current state of that migration.

## Tasks

- [ ] Create `docs/ops/orchestration_architecture.md`
- [ ] Document current orchestration mix (GH Actions + manual + Prefect status)
- [ ] Explain Prefect plan status (Phases 1+2 implementation)
- [ ] Describe local vs cloud execution state
- [ ] Document dependencies between ingestion jobs
- [ ] Add architecture diagram if helpful

## Acceptance Criteria

- [ ] Document answers "how is orchestration structured?"
- [ ] Current state vs planned state clearly differentiated
- [ ] Dependencies between jobs documented
- [ ] Transition plan referenced

## Implementation Notes

**File**: `docs/ops/orchestration_architecture.md`

**Document Structure**:

```markdown
# Orchestration Architecture

**Last Updated**: 2025-11-07
**Status**: Transitioning (GH Actions → Prefect)

## Overview

This document describes the orchestration architecture for data ingestion as of November 2025.

## Current Architecture (Nov 2025)

### Three-Layer Approach

1. **GitHub Actions** (Primary - for now)
   - Scheduled workflows for nflverse, sheets, ffanalytics
   - Simple, no infrastructure required
   - Limited orchestration capabilities

2. **Manual Commands** (Developer use)
   - Make targets and direct Python/R calls
   - Used for ad-hoc loads and debugging

3. **Prefect Flows** (In development)
   - Local execution only (no cloud deployment yet)
   - All 5 sources implemented
   - Governance integration complete

## Orchestration by Source

| Source | Current Method | Prefect Status | Dependencies |
|--------|---------------|----------------|--------------|
| **nflverse** | GH Actions | Implemented, local only | None |
| **sheets** | GH Actions | Two flows: copy (every 2-4h) + parse (15-30min after copy) | copy_league_sheet_flow → parse_league_sheet_flow |
| **ktc** | Manual | Implemented, local only | None |
| **ffanalytics** | GH Actions + R | Implemented, local only | None |
| **sleeper** | Manual | Implemented, local only | None |

## Prefect Implementation Status

### Phase 1+2: Local Flows (COMPLETE)

**Implemented**:
- [x] Flow directory structure (`src/flows/`)
- [x] Shared utilities (validation, notifications)
- [x] copy_league_sheet_flow (Google Sheets copy operation)
- [x] parse_league_sheet_flow (Google Sheets parse operation, depends on copy flow)
- [x] nfl_data_pipeline flow
- [x] ktc_pipeline flow
- [x] ffanalytics_pipeline flow
- [x] sleeper_pipeline flow
- [x] Governance task integration (copy completeness validation, row counts, required columns)
- [x] Local testing complete

**Out of Scope** (Phases 3-4):
- [ ] Cloud deployment (Prefect Cloud or self-hosted)
- [ ] Advanced monitoring dashboards
- [ ] Backfill orchestration
- [ ] Production scheduling

### Governance Integration

Each Prefect flow includes:

1. **Pre-load validation**: Check for blockers (API status, credentials)
2. **Post-load validation**: Run `validate_manifests.py`
3. **Anomaly detection**: Flag unusual row count deltas
4. **Freshness checks**: Verify snapshot currency
5. **Notifications**: Log warnings, fail on critical errors

See: `src/flows/` for implementation details

## Job Dependencies

### Current Dependencies

```

┌─────────────┐
│ nflverse │ Independent (can run anytime)
└─────────────┘

┌─────────────┐
│ sheets │ Independent (can run anytime)
└─────────────┘

┌─────────────┐
│ ktc │ Independent (can run anytime)
└─────────────┘

┌─────────────┐
│ ffanalytics │ Independent (can run anytime)
└─────────────┘

┌─────────────┐
│ sleeper │ Independent (can run anytime)
└─────────────┘

┌──────────────────────────────────┐
│ dbt run (all staging models) │ Depends on: All sources loaded
└──────────────────────────────────┘

```

**Notes**:
- Source loads are independent of each other
- dbt models depend on source data but not on each other (within staging layer)
- Prefect can parallelize source loads for faster execution

### Future Dependencies (when orchestrated)

```

Start
├─> nflverse_pipeline ──┐
├─> sheets_pipeline ────┤
├─> ktc_pipeline ────────┼─> dbt_run ─> dbt_test ─> End
├─> ffanalytics_pipeline ┤
└─> sleeper_pipeline ────┘

````

## Local vs Cloud Execution

### Local Execution (Current)

**Environment**: Developer laptop or GitHub Actions runner

**Characteristics**:
- Data stored locally (`data/raw/`)
- DuckDB database local (`dbt/ff_data_transform/target/dev.duckdb`)
- No persistent Prefect server
- Manual flow execution

**Usage**:
```bash
# Run Prefect flow locally
uv run python src/flows/nfl_data_pipeline.py

# Or with Prefect UI
prefect server start
# Then trigger flow via UI
````

### Cloud Execution (Future - Phase 3+)

**Planned Environment**: GCS + Cloud Run/Compute Engine + Prefect Cloud

**Characteristics**:

- Data stored in GCS (`gs://ff-analytics/raw/`)
- DuckDB connects to GCS via httpfs
- Persistent Prefect Cloud server
- Scheduled deployments

**Status**: Deferred to future work (see Phase 6 cloud blueprint)

## CI Integration

### Current (GitHub Actions)

```yaml
# .github/workflows/data-pipeline.yml
name: Data Pipeline

on:
  schedule:
    - cron: '0 12 * * 2,3'  # Tue/Wed at 7am ET

jobs:
  ingest:
    runs-on: ubuntu-latest
    steps:
      - name: Load nflverse data
        run: uv run python -c "..."

      - name: Validate manifests
        run: uv run python tools/validate_manifests.py

      - name: Run dbt models
        run: cd dbt/ff_data_transform && uv run dbt run
```

### Future (Prefect Cloud)

- Prefect deployments triggered by schedule or event
- GitHub Actions remains as backup/failover
- Parallel run period before full cut-over

See: `docs/ops/ci_transition_plan.md`

## Architecture Decisions

### Why Prefect?

1. **Better orchestration**: DAG-based dependencies, retries, monitoring
2. **Governance integration**: Validation tasks as first-class citizens
3. **Scalability**: Can run locally or in cloud
4. **Developer experience**: Python-native, easy testing

### Why Keep GitHub Actions Initially?

1. **Risk mitigation**: Proven, working solution
2. **Zero infrastructure**: No servers to manage
3. **Fallback option**: If Prefect fails, GH Actions can take over
4. **Parallel run**: Validate Prefect outputs match GH Actions

## Transition Timeline

1. **Phase 1+2** (Complete): Implement local Prefect flows
2. **Phase 5** (Planning): Document parallel run strategy
3. **Phase 3-4** (Future): Deploy Prefect Cloud, backfill orchestration
4. **Cut-over** (TBD): Switch to Prefect as primary, archive GH Actions

## References

- Prefect flows: `src/flows/`
- GitHub Actions: `.github/workflows/`
- CI transition plan: `docs/ops/ci_transition_plan.md`
- Prefect detailed spec: `docs/spec/prefect_dbt_sources_migration_20251026.md`

```

## Testing

1. **Verify architecture accuracy**: Check claims against actual implementation
2. **Test flow execution**: Run each Prefect flow locally to confirm status
3. **Validate dependency graph**: Ensure dependency descriptions match code

## References

- Plan: `../2025-11-07_plan_v_2_0.md` - Phase 3 Activity (lines 409-416), Phase 4 (lines 442-515)
- Checklist: `../2025-11-07_tasks_checklist_v_2_0.md` - Phase 3 Ops Docs (lines 233-239)
- Flows: `src/flows/`

```
