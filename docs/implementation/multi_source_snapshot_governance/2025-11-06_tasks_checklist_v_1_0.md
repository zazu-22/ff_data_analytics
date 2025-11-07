______________________________________________________________________

## title: Snapshot Governance — Tasks Checklist version: 1.0 date: 2025-11-06

# Snapshot Governance — Tasks Checklist

Status legend: [ ] pending, [x] complete, [-] in progress

## Macro & Staging Updates

- [ ] Add macro `keep_latest_plus(source_glob, baseline_dt=None, min_dt=None)`
- [ ] Update `stg_nflverse__player_stats` to use env glob + baseline var
- [ ] Update `stg_nflverse__snap_counts` to use env glob + baseline var
- [ ] Ensure `union_by_name=true` where schema can drift

## Ops Metadata & Validation

- [ ] Create `ops_snapshot_metadata` view (reads `_meta.json` across sources)
- [ ] Add dbt freshness tests using ops view for latest `dt`
- [ ] Enhance `tools/analyze_snapshot_coverage.py` with row delta and mapping coverage checks

## Sample Guardrails & Storage

- [ ] Relocate legacy samples to `data/raw/<source>/_samples/<dataset>/...`
- [ ] Add `samples=True` routing to `load_nflverse` shim
- [ ] Draft `docs/ops/cloud_storage_migration.md` (layout, retention, IAM)
- [ ] Implement `tools/sync_snapshots.py` with `_samples` exclusion and safe overwrite policy

## Orchestration & CI

- [ ] Define Prefect flows in `src/flows/` (ingest, refs, sleeper, dbt)
- [ ] Embed snapshot currency/anomaly checks and notifications
- [ ] Add interim GitHub Actions steps for coverage checks + dbt run/test

## Documentation & Tracking

- [ ] Refresh dbt README and staging docs to reflect new macro usage
- [ ] Align `docs/spec/SPEC-1_v_2.3_implementation_checklist_v_0.md`
