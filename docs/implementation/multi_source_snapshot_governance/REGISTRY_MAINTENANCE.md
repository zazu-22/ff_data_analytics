# Snapshot Registry Maintenance Strategy

**Version**: 1.0
**Date**: 2025-11-18
**Status**: Active (Transitional)

______________________________________________________________________

## Overview

The snapshot registry (`dbt/ff_data_transform/seeds/snapshot_registry.csv`) is the **catalog of record** for all data snapshots. It tracks metadata including row counts, coverage seasons, and snapshot status.

**Current state**: Manual/semi-automated maintenance
**Target state**: Fully automated via Prefect orchestration (Phase 4)

______________________________________________________________________

## Architecture Evolution

### Phase 2-3 (Current): Manual Maintenance

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ Ingestion    │     │ Parquet      │     │ Registry     │
│ Scripts      │ ──> │ Files        │     │ CSV          │
│ (manual)     │     │ (data/raw)   │     │ (manual)     │
└──────────────┘     └──────────────┘     └──────────────┘
                                                  │
                                                  └──> tools/update_snapshot_registry.py
                                                       (maintenance script)
```

**Problem**: Registry can drift from actual data on disk

**Solution**: `tools/update_snapshot_registry.py` - scans data/raw and syncs registry

______________________________________________________________________

### Phase 4 (Target): Automated Maintenance

```
┌────────────────────────────────────────┐
│ Prefect Flow                           │
│  ├─ Fetch data                        │
│  ├─ Write parquet ───────┐            │
│  └─ Update registry ─────┴─> ATOMIC   │
└────────────────────────────────────────┘
           │
           ├──> Parquet files (data/raw)
           └──> Registry CSV (always in sync)
```

**Benefit**: Registry updates atomic with data writes - no drift possible

______________________________________________________________________

## Tools & Usage

### Maintenance Script (Phase 2-3)

**Tool**: `tools/update_snapshot_registry.py`
**Purpose**: Sync registry with actual data files
**When**: After manual ingestion, when row_count is NULL/stale
**Deprecated**: After Phase 4 Prefect flows are complete

**Usage**:

```bash
# Fix missing row counts for nflverse
python tools/update_snapshot_registry.py --source nflverse --dry-run
python tools/update_snapshot_registry.py --source nflverse

# Reload into dbt
just dbt-seed
```

**What it does**:

1. Scans data/raw/ for all parquet snapshots
2. Reads row_count and coverage metadata from files
3. Updates snapshot_registry.csv (preserves status/description)
4. Outputs summary of changes

______________________________________________________________________

### Automated Updates (Phase 4)

**Implementation**: Each Prefect flow includes registry update task

**Example** (from P4-003):

```python
@flow
def nfl_data_pipeline():
    # 1. Fetch data
    df = fetch_nflverse_data(datasets=['weekly'])

    # 2. Write snapshot
    snapshot_dt = datetime.now().strftime('%Y-%m-%d')
    write_snapshot(df, path=f'data/raw/nflverse/weekly/dt={snapshot_dt}/')

    # 3. Update registry atomically
    update_snapshot_registry(
        source='nflverse',
        dataset='weekly',
        snapshot_date=snapshot_dt,
        row_count=len(df),  # ← Captured at write time
        coverage_start_season=df['season'].min(),
        coverage_end_season=df['season'].max(),
        status='current'
    )
```

**Phase 4 tickets with registry updates**:

- **P4-002**: Sheets pipeline (parse_league_sheet_flow)
- **P4-003**: NFL pipeline (nfl_data_pipeline) ✅ Documented
- **P4-004**: KTC pipeline (ktc_pipeline)
- **P4-005**: FFAnalytics pipeline (ffanalytics_pipeline)
- **P4-006**: Sleeper pipeline (sleeper_pipeline)

______________________________________________________________________

## Migration Checklist

### Phase 2-3 (Current)

- [x] Create `tools/update_snapshot_registry.py` maintenance script
- [ ] Populate missing row_count values for nflverse
- [ ] Run maintenance script after each manual ingestion
- [ ] Document in tools/CLAUDE.md

### Phase 4 (Orchestration)

- [ ] **P4-001**: Create flows directory structure
- [ ] **P4-002**: Add registry update to sheets flow
- [ ] **P4-003**: Add registry update to NFL flow
- [ ] **P4-004**: Add registry update to KTC flow
- [ ] **P4-005**: Add registry update to FFAnalytics flow
- [ ] **P4-006**: Add registry update to Sleeper flow
- [ ] Verify all flows update registry atomically
- [ ] **Deprecate** `tools/update_snapshot_registry.py`
- [ ] Remove maintenance script from documentation

### Verification

- [ ] Test each Prefect flow creates/updates registry entry
- [ ] Confirm row_count always populated
- [ ] Verify no manual maintenance needed
- [ ] Update tools/CLAUDE.md to remove deprecated script

______________________________________________________________________

## Current Known Issues

### Issue 1: Missing row_count for nflverse

**Symptom**: Delta calculations show 0% change even when rows differ
**Cause**: Registry has NULL row_count for nflverse snapshots
**Impact**: Anomaly detection doesn't work

**Example**:

```csv
nflverse,weekly,2025-11-10,current,2020,2025,,Player weekly statistics
                                            ^^
                                         empty row_count
```

**Fix**:

```bash
python tools/update_snapshot_registry.py --source nflverse
just dbt-seed
```

**Root cause**: P2-002 (registry population) didn't have \_meta.json files for nflverse
**Long-term fix**: Phase 4 flows will always populate row_count

______________________________________________________________________

## Best Practices

### Current (Phase 2-3)

1. **After ingestion**: Run maintenance script to sync registry
2. **Before dbt runs**: Ensure registry is current (`just dbt-seed`)
3. **Monitor**: Use `analyze_snapshot_coverage.py --report-deltas` to detect drift
4. **Validate**: Check for NULL row_count values periodically

### Future (Phase 4+)

1. **Let Prefect handle it**: Flows update registry automatically
2. **Monitor flows**: Watch for flow failures (indicates registry update failed)
3. **Trust the system**: No manual maintenance needed
4. **Validate**: Periodically verify registry matches data (for assurance)

______________________________________________________________________

## References

**Implementation**:

- Maintenance script: `tools/update_snapshot_registry.py`
- Documentation: `tools/CLAUDE.md`
- Registry seed: `dbt/ff_data_transform/seeds/snapshot_registry.csv`

**Phase 4 Tickets**:

- P4-001: Create flows structure
- P4-002 through P4-006: Implement flows with registry updates

**Related**:

- P2-001: Create snapshot registry seed
- P2-002: Populate snapshot registry
- P2-003: Extend coverage tool - delta reporting (discovered row_count issue)

______________________________________________________________________

## Questions?

**Q: Why not use dbt for registry maintenance?**
A: Registry must be updated by data writers (ingestion), not readers (dbt). Mixing concerns would couple ingestion to dbt.

**Q: Why CSV instead of database table?**
A: Git-tracked manifest ensures reproducibility. CSV is human-readable and version-controlled.

**Q: What if maintenance script fails?**
A: Registry stays as-is (no partial updates). Fix the issue and re-run. Script is idempotent.

**Q: When is maintenance script truly deprecated?**
A: After all Phase 4 flows are implemented and proven stable (likely several weeks of production use).
