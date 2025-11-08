# Ticket P3-002: Create snapshot_management_current_state Doc

**Phase**: 3 - Documentation\
**Estimated Effort**: Small (2 hours)\
**Dependencies**: P3-001 (SPEC checklist should be updated first)

## Objective

Create `docs/ops/snapshot_management_current_state.md` documenting how snapshot selection works today across all sources.

## Context

This operational doc answers "how do snapshots work?" for contributors and LLMs. It should describe the current state (not future plans) and provide actionable guidance for working with snapshots.

## Tasks

- [ ] Create `docs/ops/snapshot_management_current_state.md`
- [ ] Document snapshot selection logic per source
- [ ] List models using hardcoded dates vs macros
- [ ] Explain sample storage patterns (`_samples/` directories)
- [ ] Document snapshot lifecycle policy
- [ ] Link to snapshot registry seed
- [ ] Add examples of common snapshot operations

## Acceptance Criteria

- [ ] Document answers "how are snapshots selected?"
- [ ] Current state accurately described (no future plans)
- [ ] Examples provided for common operations
- [ ] Links to related artifacts included

## Implementation Notes

**File**: `docs/ops/snapshot_management_current_state.md`

**Document Structure**:

````markdown
# Snapshot Management — Current State

**Last Updated**: 2025-11-07
**Status**: Active

## Overview

This document describes how snapshot selection works in the FF Analytics data pipeline as of November 2025.

## Snapshot Selection Strategies

### Macro-Based Selection (Current Standard)

Models using `snapshot_selection_strategy` macro:

- `stg_nflverse__player_stats` — baseline_plus_latest (2025-10-01 + latest, fallback baseline_dt pattern)
- `stg_nflverse__snap_counts` — baseline_plus_latest (2025-10-01 + latest, fallback baseline_dt pattern)
- `stg_nflverse__ff_opportunity` — latest_only (uses snapshot_selection_strategy macro for consistency)

**Benefits**:
- Eliminates hardcoded dates
- Automatic pickup of new snapshots
- Configurable via dbt vars

### Legacy Hardcoded Dates

The following models still use hardcoded dt filters and will be migrated in future work:
- [List any remaining models, or note "None - all migrated"]

## Snapshot Lifecycle

Snapshots progress through four states:

1. **pending** — Loaded but not yet validated
2. **current** — Active in production models
3. **historical** — Retained for continuity (e.g., baseline snapshots)
4. **archived** — Kept for audit but not used in models

See: `dbt/ff_data_transform/seeds/snapshot_registry.csv`

## Legacy Sample Data

Legacy sample artifacts from fully integrated sources have been archived:

**Production path**: `data/raw/<source>/<dataset>/dt=YYYY-MM-DD/`
**Archived samples**: `data/_archived_samples/2025-11-07/<source>/<dataset>/`

**Rationale**: Samples from fully integrated sources (nflverse, sheets) are no longer needed for active development. They have been archived to prevent accidental use while preserving the sample generation tool for new source exploration.

**Note**: The sample generation tool (`tools/make_samples.py`) is preserved for creating samples when exploring new sources.

## Common Operations

### Check Current Snapshots

```bash
# Query registry
cd dbt/ff_data_transform
uv run dbt seed --select snapshot_registry
duckdb target/dev.duckdb "SELECT * FROM snapshot_registry WHERE status='current' ORDER BY source, dataset"
````

### Add New Snapshot

1. Load data to `data/raw/<source>/<dataset>/dt=YYYY-MM-DD/`
2. Write `_meta.json` manifest
3. Update registry seed (add new entry as `pending`)
4. Validate: `uv run python tools/validate_manifests.py --sources <source>`
5. Promote to `current` status in registry

### Retire Old Snapshot

1. Update registry: change status from `current` to `archived`
2. Optionally move data to cold storage
3. Update baseline_dt var if retiring a baseline snapshot

## Configuration

### dbt Variables

Baseline dates use a fallback pattern for consistency:

```yaml
# dbt_project.yml or profiles.yml
vars:
  NFLVERSE_BASELINE_DT: '2025-10-01'  # Fallback for all NFLverse datasets
  NFLVERSE_WEEKLY_BASELINE_DT: '2025-10-01'  # Specific override for weekly
  NFLVERSE_SNAP_BASELINE_DT: '2025-10-01'  # Specific override for snap_counts
```

**Fallback Pattern**: Models use `var('NFLVERSE_WEEKLY_BASELINE_DT', var('NFLVERSE_BASELINE_DT', '2025-10-01'))` to allow dataset-specific overrides while maintaining a common default.

### Environment Variables

```bash
# Glob patterns for external sources
export RAW_NFLVERSE_WEEKLY_GLOB="data/raw/nflverse/weekly/dt=*/*.parquet"
export RAW_NFLVERSE_SNAP_COUNTS_GLOB="data/raw/nflverse/snap_counts/dt=*/*.parquet"
```

## References

- Snapshot registry: `dbt/ff_data_transform/seeds/snapshot_registry.csv`
- Selection macro: `dbt/ff_data_transform/macros/snapshot_selection.sql`
- Validation tool: `tools/validate_manifests.py`
- Coverage analysis: `tools/analyze_snapshot_coverage.py`

```

## Testing

1. **Accuracy review**: Verify all statements match actual implementation
2. **Example validation**: Test each command/query example
3. **Link checking**: Ensure all file references are correct
4. **LLM test**: Ask Claude to explain snapshot management using only this doc

## References

- Plan: `../2025-11-07_plan_v_2_0.md` - Phase 3 Activity (lines 378-387)
- Checklist: `../2025-11-07_tasks_checklist_v_2_0.md` - Phase 3 Ops Docs (lines 208-215)

```
