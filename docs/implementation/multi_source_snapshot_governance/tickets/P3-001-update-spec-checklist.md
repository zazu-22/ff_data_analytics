# Ticket P3-001: Update SPEC v2.3 Checklist

**Phase**: 3 - Documentation\
**Estimated Effort**: Medium (2-3 hours)\
**Dependencies**: Should be done after Phase 1 and Phase 2 implementation tickets

## Objective

Update the authoritative SPEC v2.3 checklist to reflect current implementation state of snapshot selection, freshness tests, and snapshot registry governance.

## Context

The SPEC checklist (`docs/spec/SPEC-1_v_2.3_implementation_checklist_v_0.md`) is the source of truth for implementation status. It must be updated FIRST before creating ops docs, so that all documentation references the correct current state.

This ticket ensures the checklist accurately reflects:

- Snapshot selection macro implementation
- Staging model updates
- Registry governance model
- Freshness test coverage

## Tasks

### Update Snapshot Selection Status

- [ ] Document current snapshot selection state (hardcoded dates → macro)
- [ ] Note which models updated (player_stats, snap_counts) vs pending
- [ ] Link to snapshot_selection_strategy macro
- [ ] Update Phase 1 completion status

### Document Freshness Test Implementation

- [ ] Add freshness test implementation status section
- [ ] List sources with freshness tests configured
- [ ] Document thresholds per source
- [ ] Link to source YAML files

### Add Snapshot Registry Section

- [ ] Document snapshot registry governance model
- [ ] Explain lifecycle states (pending, current, historical, archived)
- [ ] Link to registry seed file
- [ ] Note validation tooling (validate_manifests.py)

### Link to New Ops Docs

- [ ] Add references to ops docs (will be created in P3-002 through P3-007)
- [ ] Update table of contents if needed
- [ ] Add cross-references to related sections

### Update Prefect Implementation Status

- [ ] Note Prefect Phases 1+2 progress (local flows for all 5 sources)
- [ ] Link to flow implementations (will be created in Phase 4)
- [ ] Document orchestration approach

## Acceptance Criteria

- [ ] SPEC checklist reflects actual implementation state
- [ ] No outdated or incorrect status markers
- [ ] Links to new artifacts (macros, seeds, tools) included
- [ ] Ops docs references added (even if not yet created)
- [ ] Accuracy review passed

## Implementation Notes

**File**: `docs/spec/SPEC-1_v_2.3_implementation_checklist_v_0.md`

**Sections to Update**:

1. **Phase 2 Track A (NFL Actuals)** - Add snapshot governance status:

   ```markdown
   ### Snapshot Governance (NEW)

   - [x] snapshot_selection_strategy macro implemented (calls existing latest_snapshot_only helper)
   - [x] stg_nflverse__player_stats uses macro (baseline_plus_latest, fallback baseline_dt pattern)
   - [x] stg_nflverse__snap_counts uses macro (baseline_plus_latest, fallback baseline_dt pattern)
   - [x] stg_nflverse__ff_opportunity uses macro (latest_only, consistency with other models)
   - [x] Legacy sample artifacts archived (data/_archived_samples/2025-11-07/)
   - [x] Performance baseline documented (all three NFLverse models profiled)

   See: `dbt/ff_analytics/macros/snapshot_selection.sql`
   See: `docs/implementation/multi_source_snapshot_governance/`
   ```

2. **Data Quality & Governance** (new section):

   ```markdown
   ## Data Quality & Governance

   ### Snapshot Registry

   - [x] Registry seed created (`dbt/ff_analytics/seeds/snapshot_registry.csv`)
   - [x] Populated with all 5 sources (nflverse, sheets, ktc, ffanalytics, sleeper)
   - [x] Lifecycle states defined (pending, current, historical, archived)
   - [x] Validation tooling implemented (`tools/validate_manifests.py`)

   ### Freshness Tests

   **Frequently Updated Sources** (daily/near-daily):
   - [x] nflverse: warn 2 days, error 7 days
   - [x] sheets: warn 1 day, error 7 days (multiple times per day during season)
   - [x] sleeper: warn 1 day, error 7 days

   **Weekly/Sporadic Sources**:
   - [x] ktc: warn 5 days, error 14 days
   - [x] ffanalytics: warn 2 days, error 7 days

   See: `dbt/ff_analytics/models/sources/src_*.yml`

   ### Coverage Analysis

   - [x] analyze_snapshot_coverage.py extended with row deltas
   - [x] Gap detection added (missing weeks, unmapped players)
   - [x] CI integration ready

   See: `tools/analyze_snapshot_coverage.py`
   See: `tools/validate_manifests.py`
   ```

3. **Orchestration Status** - Update Prefect section:

   ```markdown
   ## Prefect Orchestration (Phases 1+2)

   - [x] Flow structure created (`src/flows/`)
   - [x] copy_league_sheet_flow implemented (Google Sheets copy operation)
   - [x] parse_league_sheet_flow implemented (Google Sheets parse operation)
   - [x] nfl_data_pipeline implemented
   - [x] ktc_pipeline implemented
   - [x] ffanalytics_pipeline implemented
   - [x] sleeper_pipeline implemented
   - [x] Governance integration (validation tasks, copy completeness checks)
   - [x] Local testing completed
   - [ ] Cloud deployment (Phase 3 - deferred)
   - [ ] Advanced monitoring (Phase 4 - deferred)

   See: `src/flows/`
   See: `docs/ops/orchestration_architecture.md`
   ```

4. **Operations Documentation** (new section):

   ```markdown
   ## Operations Documentation

   - [x] snapshot_management_current_state.md
   - [x] ingestion_triggers_current_state.md
   - [x] data_freshness_current_state.md
   - [x] orchestration_architecture.md
   - [x] ci_transition_plan.md
   - [x] cloud_storage_migration.md

   See: `docs/ops/` directory
   ```

**Update Principles** (from plan line 369):

- Reflect current implementation state
- Link to new ops docs
- Update Phase 2 Track A status
- Add governance model section

## Testing

1. **Accuracy review**:

   ```bash
   # Read through SPEC checklist
   # For each checkmark:
   #   - Verify artifact exists
   #   - Verify implementation matches description
   #   - Check links are valid
   ```

2. **Cross-reference validation**:

   ```bash
   # Verify all links resolve
   # Check that referenced files exist
   # Ensure no broken internal links
   ```

3. **Stakeholder review**:

   - Share updated checklist with team
   - Confirm status markers are accurate
   - Get approval before proceeding to ops docs

## References

- Plan: `../2025-11-07_plan_v_2_0.md` - Phase 3 Activities (lines 363-440)
- Checklist: `../2025-11-07_tasks_checklist_v_2_0.md` - Phase 3 SPEC Update (lines 197-205)
- Current SPEC: `docs/spec/SPEC-1_v_2.3_implementation_checklist_v_0.md`
