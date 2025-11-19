# Ticket P4-003: Implement nfl_data_pipeline Flow

**Phase**: 4 - Orchestration\
**Estimated Effort**: Medium (3-4 hours)\
**Dependencies**: P4-001

## Objective

Implement Prefect flow for NFLverse data ingestion with governance integration (freshness validation, row delta anomaly detection, snapshot registry updates).

## Context

The NFL data pipeline is the most complex, handling multiple datasets (weekly, snap_counts, ff_opportunity, schedule, teams) with row delta anomaly detection to catch data quality issues.

## Tasks

- [ ] Create `src/flows/nfl_data_pipeline.py`
- [ ] Define flow with tasks: Fetch nflverse → Write Parquet → Manifest → Registry update
- [ ] Add governance: Freshness validation, row delta anomaly detection, manifest validation
- [ ] Test locally with Prefect dev server

## Acceptance Criteria

- [ ] Flow executes successfully for all NFLverse datasets
- [ ] Anomaly detection catches unusual row count changes
- [ ] Snapshot registry updated atomically with data write (deprecates `tools/update_snapshot_registry.py`)
- [ ] Flow testable locally

## Implementation Notes

**File**: `src/flows/nfl_data_pipeline.py`

Key tasks:

1. `fetch_nflverse_data(datasets, seasons)` - Call `src/ingest/nflverse/shim.load_nflverse()`
2. `check_freshness(source, dataset, max_age_days)` - Use validation utility
3. `detect_anomalies(source, dataset, row_count)` - Use validation utility
4. `write_parquet_and_manifests()` - Write outputs
5. `update_snapshot_registry(source, dataset, snapshot_date, row_count)` - Mark new snapshot as current
6. `validate_manifests_task()` - Final validation

**Governance Integration**:

- Freshness check: Warn if latest snapshot > 2 days old
- Anomaly detection: Flag if row delta > 50% or < 0 (data loss)
- Manifest validation: Ensure all files have valid manifests

## Testing

```bash
uv run python src/flows/nfl_data_pipeline.py
```

## References

- Plan: `../2025-11-07_plan_v_2_0.md` - Phase 4 NFL Flow (lines 464-472)
- Checklist: `../2025-11-07_tasks_checklist_v_2_0.md` - Phase 4 NFL (lines 293-305)
- Shim: `src/ingest/nflverse/shim.py`
