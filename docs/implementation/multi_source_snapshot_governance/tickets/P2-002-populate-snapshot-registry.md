# Ticket P2-002: Populate Snapshot Registry with All 5 Sources

**Phase**: 2 - Governance\
**Estimated Effort**: Medium (2-3 hours)\
**Dependencies**: P2-001 (registry structure must exist)

## Objective

Populate the snapshot registry seed with current and historical snapshots for all 5 data sources (nflverse, sheets, ktc, ffanalytics, sleeper).

## Context

With the registry structure in place (P2-001), this ticket populates it with actual snapshot metadata by inspecting the `data/raw/` directory and associated `_meta.json` manifests. This creates the complete governance foundation for all sources.

## Tasks

### Inventory Existing Snapshots

- [ ] Scan `data/raw/nflverse/` for all snapshots (weekly, snap_counts, ff_opportunity, schedule, teams)
- [ ] Scan `data/raw/sheets/` for all snapshots (roster, transactions, picks)
- [ ] Scan `data/raw/ktc/` for all snapshots (players, picks)
- [ ] Scan `data/raw/ffanalytics/` for all snapshots (projections)
- [ ] Scan `data/raw/sleeper/` for all snapshots (league data)

### Extract Metadata

- [ ] Read `_meta.json` manifests for each snapshot
- [ ] Extract: row_count, coverage dates, source_version
- [ ] Determine status (current vs historical) based on dates

### Populate Registry

- [ ] Add entries for nflverse datasets (weekly, snap_counts, ff_opportunity, schedule, teams)
- [ ] Add entries for sheets datasets (roster, transactions, picks)
- [ ] Add entries for ktc datasets (players, picks)
- [ ] Add entries for ffanalytics datasets (projections)
- [ ] Add entries for sleeper datasets (league data)

### Document Snapshot Lifecycle

- [ ] Mark most recent snapshots as `current`
- [ ] Mark baseline snapshots (2025-10-01) as `historical`
- [ ] Add notes explaining each snapshot's purpose

### Validate Registry

- [ ] Load seed: `uv run dbt seed --select snapshot_registry --full-refresh`
- [ ] Run tests: `uv run dbt test --select snapshot_registry`
- [ ] Verify all expected snapshots represented

## Acceptance Criteria

- [ ] Registry contains entries for all 5 sources
- [ ] Each active snapshot has an entry with complete metadata
- [ ] Row counts match manifest files
- [ ] Status values correctly assigned (current vs historical)
- [ ] Coverage dates accurate for seasonal data
- [ ] Notes provide context for each snapshot

## Implementation Notes

**Expected Entries** (from plan and checklist):

### NFLverse

```csv
nflverse,weekly,2025-10-01,historical,2020,2024,89145,Baseline snapshot for historical continuity
nflverse,weekly,2025-10-27,current,2020,2024,89145,Current snapshot through Week 8
nflverse,snap_counts,2025-10-01,historical,2020,2024,136974,Baseline snapshot
nflverse,snap_counts,2025-10-28,current,2020,2024,136974,Current snapshot through Week 8
nflverse,ff_opportunity,2025-10-27,current,2020,2024,45000,Fantasy opportunity metrics
nflverse,schedule,2025-10-27,current,2020,2024,5000,NFL schedule data
nflverse,teams,2025-10-27,current,2020,2024,32,NFL team information
```

### Google Sheets

```csv
sheets,roster,2025-11-01,current,,,150,Commissioner league roster data
sheets,transactions,2025-11-01,current,,,500,Commissioner league transactions
sheets,picks,2025-11-01,current,,,200,Commissioner draft picks
```

### KTC

```csv
ktc,players,2025-11-01,current,,,5234,Dynasty valuations 1QB
ktc,picks,2025-11-01,current,,,100,Draft pick values
```

### FFAnalytics

```csv
ffanalytics,projections,2025-11-01,current,2024,2025,3000,Fantasy projections from R package
```

### Sleeper

```csv
sleeper,league_data,2025-11-01,current,,,200,Sleeper league platform data
```

**Metadata Extraction Script** (optional helper):

```python
# tools/extract_snapshot_metadata.py
import json
from pathlib import Path

def scan_snapshots(raw_dir='data/raw'):
    """Scan raw directory and extract snapshot metadata"""
    entries = []

    for source_dir in Path(raw_dir).iterdir():
        if source_dir.name == '_samples':
            continue

        source = source_dir.name

        for dataset_dir in source_dir.iterdir():
            if dataset_dir.name == '_samples':
                continue

            dataset = dataset_dir.name

            # Find all dt= partitions
            for dt_dir in dataset_dir.glob('dt=*'):
                snapshot_date = dt_dir.name.split('=')[1]

                # Read manifest if exists
                manifest_path = dt_dir / '_meta.json'
                if manifest_path.exists():
                    with open(manifest_path) as f:
                        manifest = json.load(f)

                    row_count = manifest.get('row_count', '')
                    # Extract coverage from manifest or estimate

                entries.append({
                    'source': source,
                    'dataset': dataset,
                    'snapshot_date': snapshot_date,
                    'status': 'pending',  # Manual review needed
                    'row_count': row_count,
                    'notes': ''
                })

    return entries
```

**Status Assignment Logic**:

- Most recent snapshot per dataset: `current`
- Baseline snapshots (2025-10-01): `historical`
- Older snapshots no longer referenced: `archived`
- Newly loaded but not validated: `pending`

## Testing

1. **Load populated seed**:

   ```bash
   cd dbt/ff_data_transform
   uv run dbt seed --select snapshot_registry --full-refresh
   ```

2. **Query registry**:

   ```sql
   -- Count by source
   SELECT source, COUNT(*) as snapshot_count
   FROM snapshot_registry
   GROUP BY source
   ORDER BY source;

   -- Current snapshots only
   SELECT source, dataset, snapshot_date, row_count
   FROM snapshot_registry
   WHERE status = 'current'
   ORDER BY source, dataset;
   ```

3. **Validate row counts**:

   ```bash
   # Compare registry row_count to actual Parquet files
   # For each entry, verify row count matches
   ```

4. **Run schema tests**:

   ```bash
   uv run dbt test --select snapshot_registry
   ```

## References

- Plan: `../2025-11-07_plan_v_2_0.md` - Design Decision #3 example entries (lines 125-131)
- Checklist: `../2025-11-07_tasks_checklist_v_2_0.md` - Phase 2 Registry (lines 99-105)
- Data directory: `data/raw/` (all sources)
- Manifests: `data/raw/<source>/<dataset>/dt=*/_meta.json`
