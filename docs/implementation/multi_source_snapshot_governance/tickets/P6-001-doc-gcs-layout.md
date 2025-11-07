# Ticket P6-001: Document GCS Bucket Layout and Lifecycle Policies

**Phase**: 6 - Cloud Blueprint\
**Estimated Effort**: Small (1-2 hours)\
**Dependencies**: None (pure documentation)

## Objective

Document GCS bucket structure, retention policies, and lifecycle rules for future cloud migration.

## Context

This is partially complete from P3-007 (`cloud_storage_migration.md`). Validate the GCS bucket layout section and create the `config/gcs/lifecycle.json` file if missing.

## Tasks

- [ ] Review GCS bucket layout documentation in `docs/ops/cloud_storage_migration.md`
- [ ] Create `config/gcs/lifecycle.json` with lifecycle rules
- [ ] Document partition patterns
- [ ] Document retention policies by layer (raw, stage, mart, ops)

## Acceptance Criteria

- [ ] Bucket layout fully documented
- [ ] Lifecycle JSON file created and valid
- [ ] Retention policies defined per layer
- [ ] Cost optimization considerations documented

## Implementation Notes

**Bucket Structure**:

```
gs://ff-analytics/
├── raw/     # 90 days, Standard → Nearline → Coldline
├── stage/   # 30 days, delete after
├── mart/    # 365 days, Standard → Archive
└── ops/     # 180 days, Standard → Nearline
```

**File**: `config/gcs/lifecycle.json` (create if missing, already specified in P3-007)

## Testing

Validate JSON syntax:

```bash
cat config/gcs/lifecycle.json | jq .
```

## References

- Plan: `../2025-11-07_plan_v_2_0.md` - Phase 6 GCS Layout (lines 580-601)
- Doc: `docs/ops/cloud_storage_migration.md` (created in P3-007)
