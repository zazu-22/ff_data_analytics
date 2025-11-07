# Ticket P6-004: Create Migration Checklist and Optional Sync Utility

**Phase**: 6 - Cloud Blueprint\
**Estimated Effort**: Medium (2 hours)\
**Dependencies**: P6-001, P6-002, P6-003

## Objective

Create comprehensive migration checklist and optional `tools/sync_snapshots.py` utility for manual sync operations.

## Context

Partially complete from P3-007. Validate migration checklist completeness and create the sync utility if it would be useful.

## Tasks

- [ ] Review migration checklist in `docs/ops/cloud_storage_migration.md`
- [ ] Validate pre-migration, execution, and post-migration steps
- [ ] Document rollback plan
- [ ] Create `tools/sync_snapshots.py` (optional but recommended)
- [ ] Test sync utility in dry-run mode

## Acceptance Criteria

- [ ] Migration checklist complete with all phases
- [ ] Rollback plan documented
- [ ] Optional sync utility created
- [ ] Sync utility tested in dry-run mode

## Implementation Notes

**Migration Checklist** (already in P3-007 doc):

- Pre-migration (preparation)
- Migration execution (gsutil rsync)
- Post-migration (validation)
- Rollback plan

**Sync Utility**: `tools/sync_snapshots.py` (specification in P3-007)

- Bidirectional sync (local ↔ GCS)
- Exclude `_samples/` directories
- Dry-run mode
- Force option

## Testing

```bash
# Dry run test (no GCS required)
uv run python tools/sync_snapshots.py --direction up --dry-run
```

## References

- Plan: `../2025-11-07_plan_v_2_0.md` - Phase 6 Migration (lines 635-651)
- Doc: `docs/ops/cloud_storage_migration.md` (migration section)
