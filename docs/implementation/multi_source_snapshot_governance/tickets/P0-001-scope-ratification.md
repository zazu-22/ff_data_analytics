# Ticket P0-001: Scope Ratification and Blocker Identification

**Phase**: 0 - Kickoff & Decision Ratification\
**Estimated Effort**: Small (1-2 hours)\
**Dependencies**: None

## Objective

Formalize scope, approve governance approach, and define success criteria before implementation begins to ensure team alignment on the full Multi-Source Snapshot Governance effort.

## Context

Phase 0 serves as the formal kickoff to ratify all technical decisions, confirm orchestration scope, and identify any blockers that could derail implementation. This ensures the team is aligned on:

- Prefect orchestration for all 5 sources (nflverse, sheets, ktc, ffanalytics, sleeper)
- Snapshot registry seed as the governance foundation
- Tightened freshness thresholds per source
- CI-integrated validation tooling

Without this alignment, implementation could proceed on incorrect assumptions or encounter avoidable blockers.

## Tasks

- [ ] Confirm scope: All 5 sources for Prefect orchestration (nflverse, sheets, ktc, ffanalytics, sleeper)
- [ ] Confirm Prefect Phases 1+2 implementation (local flows, all sources)
- [ ] Approve snapshot registry seed creation and governance model
- [ ] Define success metrics and acceptance criteria
- [ ] Identify blockers:
  - [ ] GCS authentication status (service account key available?)
  - [ ] Prefect Cloud access or local Prefect server setup
  - [ ] Environment setup (Python 3.13.6, uv, dbt-fusion)
- [ ] Configure environment and path management:
  - [ ] Create `.env.template` with documented path overrides
  - [ ] Create `config/env_config.yaml` with multi-environment paths (local, ci, cloud)
  - [ ] Create `config/README.md` explaining environment switching
  - [ ] Verify default globs in dbt models work without configuration
  - [ ] Test that dbt works with zero configuration (defaults only)
- [ ] Document Phase 0 decisions and exit criteria in implementation README

## Acceptance Criteria

- [ ] Team alignment documented on full scope and approach
- [ ] All blockers identified with mitigation plans
- [ ] Success metrics agreed upon and documented
- [ ] Decision log captured (who approved what, when)

## Implementation Notes

**File to Update**: `docs/implementation/multi_source_snapshot_governance/2025-11-07_README_v_2_0.md`

Add a "Phase 0 Decisions" section documenting:

1. **Scope Confirmation**:

   - All 5 data sources in scope: nflverse, sheets, ktc, ffanalytics, sleeper
   - Prefect Phases 1+2: Local flows with governance integration
   - Out of scope: Cloud deployment (Prefect Phase 3-4), actual GCS migration

2. **Governance Model**:

   - Snapshot registry seed approved as single source of truth
   - Freshness thresholds confirmed per source (see table in plan)
   - Validation tooling approach approved (extend existing + create new)

3. **Success Metrics** (from plan):

   - Zero hardcoded snapshot dates in staging models
   - Snapshot registry tracking current/historical snapshots
   - Working Prefect flows for all 5 sources
   - Freshness tests providing pre-dbt safety net
   - CI transition plan documented with rollback procedures
   - Cloud migration blueprint complete

4. **Blocker Assessment**:

   - Document current state for each potential blocker
   - Assign owners for resolving any identified blockers
   - Set timeline for blocker resolution before Phase 1 begins

5. **Environment Configuration Setup**:

   Create `.env.template` (version controlled):

   ```bash
   # .env.template - Copy to .env for local development

   # Environment selector (local, ci, cloud)
   FF_ENV=local

   # Optional: Override specific paths for testing
   # RAW_NFLVERSE_WEEKLY_GLOB="custom/path/weekly/dt=*/*.parquet"
   # RAW_NFLVERSE_SNAP_COUNTS_GLOB="custom/path/snap_counts/dt=*/*.parquet"
   # RAW_NFLVERSE_FF_OPPORTUNITY_GLOB="custom/path/ff_opportunity/dt=*/*.parquet"

   # GCS credentials (required for cloud environment)
   # GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
   ```

   Create `config/env_config.yaml` (version controlled):

   ```yaml
   # Multi-environment configuration
   environments:
     local:
       RAW_NFLVERSE_WEEKLY_GLOB: "data/raw/nflverse/weekly/dt=*/*.parquet"
       RAW_NFLVERSE_SNAP_COUNTS_GLOB: "data/raw/nflverse/snap_counts/dt=*/*.parquet"
       RAW_NFLVERSE_FF_OPPORTUNITY_GLOB: "data/raw/nflverse/ff_opportunity/dt=*/*.parquet"

     cloud:
       RAW_NFLVERSE_WEEKLY_GLOB: "gs://ff-analytics/raw/nflverse/weekly/dt=*/*.parquet"
       RAW_NFLVERSE_SNAP_COUNTS_GLOB: "gs://ff-analytics/raw/nflverse/snap_counts/dt=*/*.parquet"
       RAW_NFLVERSE_FF_OPPORTUNITY_GLOB: "gs://ff-analytics/raw/nflverse/ff_opportunity/dt=*/*.parquet"

     ci:
       RAW_NFLVERSE_WEEKLY_GLOB: "data/raw/nflverse/weekly/dt=*/*.parquet"
       RAW_NFLVERSE_SNAP_COUNTS_GLOB: "data/raw/nflverse/snap_counts/dt=*/*.parquet"
       RAW_NFLVERSE_FF_OPPORTUNITY_GLOB: "data/raw/nflverse/ff_opportunity/dt=*/*.parquet"
   ```

   Create `config/README.md`:

   ```markdown
   # Configuration

   ## Environment Selection

   Set `FF_ENV` to switch environments:

   - `local`: Development on local disk (default)
   - `ci`: GitHub Actions (local disk)
   - `cloud`: Prefect Cloud (GCS)

   ## Configuration Priority

   1. Environment variables (highest)
   2. .env file
   3. config/env_config.yaml[FF_ENV]
   4. Defaults in dbt code (lowest)

   ## Zero-Config Local Development

   The system works without any configuration. Defaults in dbt models use local paths.
   Only override if you need custom paths or cloud storage.
   ```

## Testing

N/A - This is a planning/documentation ticket

## References

- Plan: `../2025-11-07_plan_v_2_0.md` - Phase 0 section (lines 240-260)
- Checklist: `../2025-11-07_tasks_checklist_v_2_0.md` - Phase 0 tasks (lines 13-26)
- README: `../2025-11-07_README_v_2_0.md` - Goals and approach sections
