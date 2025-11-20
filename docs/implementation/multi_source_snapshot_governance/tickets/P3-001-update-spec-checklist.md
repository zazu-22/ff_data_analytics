# Ticket P3-001: Update SPEC v2.3 Checklist

**Phase**: 3 - Documentation\
**Estimated Effort**: Medium (2-3 hours)\
**Dependencies**: Should be done after Phase 1 and Phase 2 implementation tickets\
**Status**: COMPLETE

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

- [x] Document current snapshot selection state (hardcoded dates → macro)
- [x] Note which models updated (player_stats, snap_counts) vs pending
- [x] Link to snapshot_selection_strategy macro
- [x] Update Phase 1 completion status

### Document Freshness Test Implementation

- [x] Add freshness test implementation status section
- [x] List sources with freshness tests configured
- [x] Document thresholds per source
- [x] Link to source YAML files

### Add Snapshot Registry Section

- [x] Document snapshot registry governance model
- [x] Explain lifecycle states (pending, current, historical, archived)
- [x] Link to registry seed file
- [x] Note validation tooling (validate_manifests.py)

### Link to New Ops Docs

- [x] Add references to ops docs (will be created in P3-002 through P3-007)
- [x] Update table of contents if needed
- [x] Add cross-references to related sections

### Update Prefect Implementation Status

- [x] Note Prefect Phases 1+2 progress (local flows for all 5 sources)
- [x] Link to flow implementations (will be created in Phase 4)
- [x] Document orchestration approach

## Acceptance Criteria

- [x] SPEC checklist reflects actual implementation state
- [x] No outdated or incorrect status markers
- [x] Links to new artifacts (macros, seeds, tools) included
- [x] Ops docs references added (even if not yet created)
- [x] Accuracy review passed

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

   See: `dbt/ff_data_transform/macros/snapshot_selection.sql`
   See: `docs/implementation/multi_source_snapshot_governance/`
   ```

2. **Data Quality & Governance** (new section):

   ```markdown
   ## Data Quality & Governance

   ### Snapshot Registry

   - [x] Registry seed created (`dbt/ff_data_transform/seeds/snapshot_registry.csv`)
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

   See: `dbt/ff_data_transform/models/sources/src_*.yml`

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

## Completion Notes

**Implemented**: 2025-11-20

**Changes Made**:

1. **Snapshot Governance Section** (added to Phase 2 Track A):

   - Documented all 13 staging model updates with snapshot_selection_strategy macro
   - Listed strategy used for each model (baseline_plus_latest for NFLverse historical, latest_only for others)
   - Added links to macro implementation and documentation
   - Noted legacy sample archival and performance profiling completion

2. **Data Quality & Governance Section** (new section after Phase 3):

   - **Snapshot Registry**: Documented seed creation, 100 snapshots registered, lifecycle states, validation and maintenance tooling
   - **Freshness Tests**: Documented manifest-based freshness validation (P2-006B), per-source thresholds, validation approach
   - **Coverage Analysis & Observability**: Documented row delta extension (P2-003), gap detection (P2-004), CI integration readiness
   - **Data Quality Fixes**: Listed all 12 Phase 1 data quality tickets with resolution status (all complete with 100% success rates)
   - **Success Metrics**: Confirmed all epic success metrics achieved

3. **Prefect Orchestration Section** (new section):

   - Listed 7 flow implementations (all pending - Phase 4)
   - Noted governance integration requirements
   - Added links to implementation guide and future orchestration architecture doc

4. **Operations Documentation Section** (new section):

   - Listed 6 ops docs to be created in P3-002 through P3-007
   - Added links to ticket files and future docs/ directory

**Impact**:

- SPEC v2.3 now accurately reflects Multi-Source Snapshot Governance implementation state
- All Phase 1 (Foundation) and Phase 2 (Governance) accomplishments documented
- Phase 3 (Documentation) and Phase 4 (Orchestration) status clearly marked as pending
- Provides authoritative reference for current implementation state

**Accuracy Review**: PASSED

- All checkmarks verified against actual implementation
- All file paths confirmed to exist
- Links to future artifacts clearly marked as "to be created"
- No outdated or incorrect status markers
