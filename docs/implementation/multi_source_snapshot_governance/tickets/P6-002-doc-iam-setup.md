# Ticket P6-002: Document IAM Requirements and Service Account Setup

**Phase**: 6 - Cloud Blueprint\
**Estimated Effort**: Small (1 hour)\
**Dependencies**: None

## Objective

Document IAM permissions required for GCS access and provide service account setup guide with gcloud commands.

## Context

**Current State**: Service account already exists and key is downloaded. Check `.env` file for `GOOGLE_APPLICATION_CREDENTIALS` variable to see current key location (typically `config/secrets/gcp-service-account-key.json`).

This ticket documents the existing setup rather than creating new resources. Partially complete from P3-007. Validate IAM section completeness and ensure all gcloud commands are correct and tested (if GCP project available).

## Tasks

- [ ] Verify current service account setup:
  - [ ] Check `.env` for `GOOGLE_APPLICATION_CREDENTIALS` path
  - [ ] Verify key file exists at documented location
  - [ ] Document current service account name and permissions
- [ ] Review IAM requirements documentation
- [ ] Document existing service account setup (not creation)
- [ ] Document key management and rotation policy
- [ ] Add security best practices
- [ ] Note: Service account creation commands are for reference only (already done)

## Acceptance Criteria

- [ ] Required permissions documented
- [ ] Service account setup guide complete with commands
- [ ] Key rotation policy documented
- [ ] Security notes included

## Implementation Notes

**Current Service Account Location**:

Check `.env` file for `GOOGLE_APPLICATION_CREDENTIALS` variable. Typical location:

- `config/secrets/gcp-service-account-key.json`

**Verification Steps**:

```bash
# Check .env for current path
grep GOOGLE_APPLICATION_CREDENTIALS .env

# Verify key file exists
ls -lh config/secrets/gcp-service-account-key.json

# Verify key is valid JSON
cat config/secrets/gcp-service-account-key.json | jq .type
# Should output: "service_account"
```

**Documentation to Update**:

Already documented in `docs/ops/cloud_storage_migration.md` (P3-007), but update to note:

- **Service account already exists** (no creation needed)
- **Key already downloaded** (verify location from `.env`)
- Required permissions (storage.objects.\*)
- Key rotation policy (90 days) - document when last rotated
- Security best practices (key storage, access control)

## Testing

If GCP project available, test commands in dry-run mode

## References

- Plan: `../2025-11-07_plan_v_2_0.md` - Phase 6 IAM (lines 603-617)
- Doc: `docs/ops/cloud_storage_migration.md` (IAM section)
