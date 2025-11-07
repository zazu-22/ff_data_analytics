# Ticket P3-007: Create cloud_storage_migration Doc

**Phase**: 3 - Documentation\
**Estimated Effort**: Medium (3 hours)\
**Dependencies**: None (pure documentation)

## Objective

Create `docs/ops/cloud_storage_migration.md` documenting GCS bucket layout, retention policies, IAM requirements, DuckDB GCS configuration, and migration checklist.

## Context

This doc provides a blueprint for future cloud migration (GCS). It's planning documentation only — no actual migration occurs in this ticket. The goal is to document requirements so the team can execute migration independently later.

## Tasks

- [ ] Create `docs/ops/cloud_storage_migration.md`
- [ ] Document GCS bucket layout (`gs://ff-analytics/{raw,stage,mart,ops}/`)
- [ ] Explain retention policies and lifecycle rules
- [ ] Document IAM requirements (`storage.objects.*` permissions)
- [ ] Provide service account setup guide with gcloud commands
- [ ] Document DuckDB GCS configuration (httpfs extension)
- [ ] Create migration checklist
- [ ] Note: Blueprint only, no actual migration

## Acceptance Criteria

- [ ] Document provides complete migration blueprint
- [ ] IAM requirements clearly specified
- [ ] GCS bucket layout documented with retention policies
- [ ] DuckDB configuration steps provided
- [ ] Migration checklist actionable

## Implementation Notes

**File**: `docs/ops/cloud_storage_migration.md`

**Document Structure** (from plan Phase 6):

```markdown
# Cloud Storage Migration — GCS Blueprint

**Last Updated**: 2025-11-07
**Status**: Planning Only (No Migration)

## Overview

This document provides a blueprint for migrating from local storage to Google Cloud Storage (GCS).

**Important**: This is planning documentation. No actual migration should occur without team approval and preparation.

## GCS Bucket Layout

### Bucket Structure

```

gs://ff-analytics/
├── raw/ # Immutable source snapshots
│ ├── nflverse/
│ │ ├── weekly/dt=2025-10-27/
│ │ ├── snap_counts/dt=2025-10-28/
│ │ └── ...
│ ├── sheets/
│ ├── ktc/
│ ├── ffanalytics/
│ └── sleeper/
├── stage/ # Intermediate staging artifacts
├── mart/ # Published dimensional models
└── ops/ # Metadata, logs, monitoring

````

### Partition Patterns

All snapshots follow: `<source>/<dataset>/dt=YYYY-MM-DD/`

Example:
- `gs://ff-analytics/raw/nflverse/weekly/dt=2025-10-27/weekly.parquet`
- `gs://ff-analytics/raw/nflverse/weekly/dt=2025-10-27/_meta.json`

## Retention Policies

### By Layer

| Layer | Retention Period | Storage Class Transitions | Rationale |
|-------|-----------------|---------------------------|-----------|
| **raw** | 90 days | Standard → Nearline (30d) → Coldline (60d) | Immutable snapshots, kept for reprocessing |
| **stage** | 30 days | Standard only, then delete | Intermediate artifacts, can be regenerated |
| **mart** | 365 days | Standard → Nearline (90d) → Archive (180d) | Published models, kept for historical analysis |
| **ops** | 180 days | Standard → Nearline (60d) | Logs and metadata for troubleshooting |

### Lifecycle Rules

Create `config/gcs/lifecycle.json`:

```json
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "SetStorageClass", "storageClass": "NEARLINE"},
        "condition": {
          "age": 30,
          "matchesPrefix": ["raw/"]
        }
      },
      {
        "action": {"type": "SetStorageClass", "storageClass": "COLDLINE"},
        "condition": {
          "age": 60,
          "matchesPrefix": ["raw/"]
        }
      },
      {
        "action": {"type": "Delete"},
        "condition": {
          "age": 90,
          "matchesPrefix": ["raw/"]
        }
      },
      {
        "action": {"type": "Delete"},
        "condition": {
          "age": 30,
          "matchesPrefix": ["stage/"]
        }
      },
      {
        "action": {"type": "SetStorageClass", "storageClass": "ARCHIVE"},
        "condition": {
          "age": 180,
          "matchesPrefix": ["mart/"]
        }
      },
      {
        "action": {"type": "Delete"},
        "condition": {
          "age": 365,
          "matchesPrefix": ["mart/"]
        }
      }
    ]
  }
}
````

**Apply lifecycle rules**:

```bash
gsutil lifecycle set config/gcs/lifecycle.json gs://ff-analytics
```

### Cost Optimization

**Storage Class Pricing** (approximate, as of 2025):

- Standard: $0.020/GB/month
- Nearline: $0.010/GB/month (30-day minimum)
- Coldline: $0.004/GB/month (90-day minimum)
- Archive: $0.0012/GB/month (365-day minimum)

**Example Savings** (100 GB raw data):

- All Standard: $2.00/month
- With lifecycle (Standard → Nearline → Coldline): ~$1.00/month (50% savings)

## IAM Requirements

### Required Permissions

Service account needs these GCS permissions:

- `storage.objects.create` — Write Parquet files and manifests
- `storage.objects.get` — Read files (DuckDB queries)
- `storage.objects.list` — Glob patterns (`dt=*/*.parquet`)
- `storage.objects.delete` — Lifecycle cleanup (optional, can use lifecycle rules instead)

### Recommended Role

**Option 1**: Use predefined role `roles/storage.objectAdmin`

```bash
gcloud projects add-iam-policy-binding PROJECT_ID \
    --member="serviceAccount:ff-analytics-ingestion@PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/storage.objectAdmin"
```

**Option 2**: Create custom role (least privilege)

```bash
gcloud iam roles create ffAnalyticsStorageRole \
    --project=PROJECT_ID \
    --title="FF Analytics Storage Access" \
    --description="Read/write access to ff-analytics bucket" \
    --permissions=storage.objects.create,storage.objects.get,storage.objects.list
```

## Service Account Setup

**Current State**: Service account already exists and key is downloaded. Check `.env` file for `GOOGLE_APPLICATION_CREDENTIALS` variable to see current key location (typically `config/secrets/gcp-service-account-key.json`).

**Verify Existing Setup**:

```bash
# Check .env for current path
grep GOOGLE_APPLICATION_CREDENTIALS .env

# Verify key file exists
ls -lh config/secrets/gcp-service-account-key.json

# Verify key is valid JSON
cat config/secrets/gcp-service-account-key.json | jq .type
# Should output: "service_account"
```

**Reference: Service Account Creation** (already done, for documentation only):

### Step 1: Create Service Account

```bash
gcloud iam service-accounts create ff-analytics-ingestion \
    --display-name="FF Analytics Ingestion" \
    --description="Service account for data pipeline ingestion"
```

**Note**: This step is already complete. Service account exists.

### Step 2: Grant GCS Permissions

```bash
gcloud projects add-iam-policy-binding PROJECT_ID \
    --member="serviceAccount:ff-analytics-ingestion@PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/storage.objectAdmin"
```

**Note**: Permissions already granted. Verify if needed.

### Step 3: Create and Download Key

```bash
gcloud iam service-accounts keys create gcp-service-account-key.json \
    --iam-account=ff-analytics-ingestion@PROJECT_ID.iam.gserviceaccount.com
```

**Note**: Key already downloaded. Current location documented in `.env` as `GOOGLE_APPLICATION_CREDENTIALS`.

**Security Note**: Key is stored securely in `config/secrets/` (gitignored), never committed to git

```bash
# Current setup (already done):
# Key location: config/secrets/gcp-service-account-key.json
# Environment variable: GOOGLE_APPLICATION_CREDENTIALS (set in .env)
# Permissions: 600 (read/write for owner only)
```

### Step 4: Key Rotation Policy

- Rotate keys every 90 days
- Delete old keys after rotation
- Update environment variables/secrets

```bash
# List keys
gcloud iam service-accounts keys list \
    --iam-account=ff-analytics-ingestion@PROJECT_ID.iam.gserviceaccount.com

# Delete old key
gcloud iam service-accounts keys delete KEY_ID \
    --iam-account=ff-analytics-ingestion@PROJECT_ID.iam.gserviceaccount.com
```

## DuckDB GCS Configuration

### Install httpfs Extension

```sql
INSTALL httpfs;
LOAD httpfs;
```

### Configure GCS Access

```sql
-- Using service account key file
SET gcs_access_key_id = 'YOUR_ACCESS_KEY';
SET gcs_secret_access_key = 'YOUR_SECRET_KEY';

-- Or using default application credentials
SET gcs_use_default_credentials = true;
```

### Test GCS Read

```sql
-- Test query
SELECT * FROM read_parquet('gs://ff-analytics/raw/nflverse/weekly/dt=*/weekly.parquet')
LIMIT 10;

-- Should return 10 rows if working correctly
```

### Performance Considerations

- **Network latency**: GCS reads slower than local disk (~50-100ms per request)
- **Query pushdown**: DuckDB pushes filters to reduce data transferred
- **Caching**: Consider caching frequently accessed data locally

## Migration Checklist

### Pre-Migration (Preparation)

- [ ] Create GCS bucket: `gsutil mb gs://ff-analytics`
- [ ] Verify service account setup (already exists):
  - [ ] Check `.env` for `GOOGLE_APPLICATION_CREDENTIALS` path
  - [ ] Verify key file exists at documented location
  - [ ] Verify service account has required GCS permissions
- [ ] Grant IAM permissions (if not already granted)
- [ ] Apply lifecycle rules: `gsutil lifecycle set config/gcs/lifecycle.json gs://ff-analytics`
- [ ] Test DuckDB GCS connection locally (using existing credentials)
- [ ] Back up critical local snapshots

### Migration Execution

- [ ] **Initial data copy** (use gsutil rsync for efficiency):

  ```bash
  gsutil -m rsync -r -x ".*_samples/.*" data/raw/ gs://ff-analytics/raw/
  ```

- [ ] **Validate file counts**:

  ```bash
  # Local count
  find data/raw -type f -name "*.parquet" | wc -l

  # GCS count
  gsutil ls -r gs://ff-analytics/raw/**/*.parquet | wc -l
  ```

- [ ] **Validate file sizes**:

  ```bash
  # Compare du output
  du -sh data/raw/*
  gsutil du -sh gs://ff-analytics/raw/*
  ```

- [ ] **Test DuckDB reads from GCS**:

  ```sql
  SELECT COUNT(*) FROM read_parquet('gs://ff-analytics/raw/nflverse/weekly/dt=*/weekly.parquet');
  -- Compare to local count
  ```

- [ ] **Update Prefect flow env vars**:

  ```bash
  export EXTERNAL_ROOT="gs://ff-analytics/raw"
  export GOOGLE_APPLICATION_CREDENTIALS="path/to/key.json"
  ```

- [ ] **Test Prefect flows with GCS**:

  ```bash
  uv run python src/flows/nfl_data_pipeline.py
  # Verify writes to GCS
  ```

- [ ] **Validate cloud reads work in dbt**:

  ```bash
  cd dbt/ff_analytics
  # Update dbt_project.yml with GCS paths
  uv run dbt compile
  uv run dbt run --select stg_nflverse__player_stats
  ```

### Post-Migration

- [ ] Monitor query performance (compare to local baseline)
- [ ] Verify lifecycle rules trigger correctly (check after 30 days)
- [ ] Run full dbt test suite: `uv run dbt test`
- [ ] Keep local data for 2+ weeks as backup
- [ ] Document any issues encountered

### Rollback Plan

If migration issues arise:

1. [ ] Revert `EXTERNAL_ROOT` to local paths in env vars
2. [ ] Restart Prefect flows (will write to local)
3. [ ] Restart dbt (will read from local)
4. [ ] Investigate GCS issues before retrying
5. [ ] Do not delete local data until cloud validated (2+ weeks stable)

## Optional: Sync Utility

Create `tools/sync_snapshots.py` for manual sync operations:

```python
#!/usr/bin/env python3
"""Sync snapshots between local and GCS."""

import subprocess
import click

@click.command()
@click.option('--direction', type=click.Choice(['up', 'down']), required=True)
@click.option('--dry-run', is_flag=True, help='Preview operations without executing')
@click.option('--force', is_flag=True, help='Overwrite existing files')
def sync(direction, dry_run, force):
    """Sync snapshots between local and GCS."""

    if direction == 'up':
        source = 'data/raw/'
        dest = 'gs://ff-analytics/raw/'
    else:
        source = 'gs://ff-analytics/raw/'
        dest = 'data/raw/'

    cmd = ['gsutil', '-m', 'rsync', '-r']

    if dry_run:
        cmd.append('-n')

    if not force:
        cmd.append('-x')  # Don't overwrite

    # Exclude _samples
    cmd.extend(['-x', '.*_samples/.*'])

    cmd.extend([source, dest])

    print(f"Running: {' '.join(cmd)}")
    subprocess.run(cmd)

if __name__ == '__main__':
    sync()
```

**Usage**:

```bash
# Preview upload
uv run python tools/sync_snapshots.py --direction up --dry-run

# Execute upload
uv run python tools/sync_snapshots.py --direction up

# Download from GCS
uv run python tools/sync_snapshots.py --direction down
```

## References

- GCS documentation: https://cloud.google.com/storage/docs
- DuckDB httpfs extension: https://duckdb.org/docs/extensions/httpfs
- Bucket lifecycle: https://cloud.google.com/storage/docs/lifecycle

```

## Testing

1. **Verify all commands are valid**: Test gcloud commands in docs (requires GCP project)
2. **Check lifecycle JSON**: Validate JSON syntax
3. **Link checking**: Ensure external references are current

## References

- Plan: `../2025-11-07_plan_v_2_0.md` - Phase 6 (lines 575-665)
- Checklist: `../2025-11-07_tasks_checklist_v_2_0.md` - Phase 6 (lines 448-567)

```
