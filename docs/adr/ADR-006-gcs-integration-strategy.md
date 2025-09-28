# ADR-006: GCS Integration Strategy

## Status

Accepted

## Context

The data pipeline needs to write to Google Cloud Storage (GCS) in production while supporting local filesystem development. We need a strategy that:

- Minimizes code changes between environments
- Avoids accidental GCS writes (and costs) during development
- Maintains the same directory structure locally and in cloud
- Enables gradual migration to cloud storage

## Decision

### Current State (Local Development)

All data loaders currently write to local filesystem paths that mirror the eventual GCS structure:

- Default: `data/raw/{provider}/{dataset}/dt=YYYY-MM-DD/`
- Example: `data/raw/nflverse/players/dt=2024-09-28/`

This allows us to:

1. Develop and test the pipeline locally without GCS costs
1. Validate the partitioning structure before deployment
1. Use the same code paths for local and cloud environments

## Future State (Production via GitHub Actions)

### Option 1: Environment-based Configuration (Recommended)

- GitHub Actions sets environment variable: `DATA_ROOT=gs://ff-analytics`

- Scripts read this variable and construct paths accordingly

- Example:

  ```python
  import os
  data_root = os.getenv('DATA_ROOT', 'data')  # defaults to local
  out_dir = f"{data_root}/raw/nflverse"
  load_nflverse("players", out_dir=out_dir)
  ```

### Option 2: Explicit GCS Wrapper Script

- Create `scripts/ingest/upload_to_gcs.py` that:
  1. Runs the local loader
  1. Uploads results to GCS using `google-cloud-storage` library
  1. Cleans up local files
- GitHub Actions calls this wrapper script

### Option 3: Direct GCS Support in Loaders

- Enhance loaders to detect `gs://` prefixes

- Use `gcsfs` or `google-cloud-storage` for GCS paths

- Use `Path` for local paths

- Example:

  ```python
  if out_dir.startswith('gs://'):
      # Use GCS client
      fs = gcsfs.GCSFileSystem()
      fs.write_parquet(...)
  else:
      # Use local Path
      Path(out_dir).write_parquet(...)
  ```

## Implementation Timeline

1. **Phase 1 (Current)**: Local development with GCS-like structure
1. **Phase 2**: Add environment variable support (Option 1)
1. **Phase 3**: Add GCS libraries to requirements when CI/CD is set up
1. **Phase 4**: Test in GitHub Actions with actual GCS writes

## Configuration in GitHub Actions

```yaml
env:
  DATA_ROOT: gs://ff-analytics
  GOOGLE_APPLICATION_CREDENTIALS_JSON: ${{ secrets.GCP_SERVICE_ACCOUNT_JSON }}

steps:
  - name: Run nflverse ingestion
    run: |
      python -c "
      import os
      from ingest.nflverse.shim import load_nflverse
      out_dir = f\"{os.getenv('DATA_ROOT')}/raw/nflverse\"
      load_nflverse('players', out_dir=out_dir)
      "
```

## Consequences

### Positive

1. **No code changes needed** when moving from local to cloud
1. **Same testing locally and in CI** - just different output paths
1. **Cost control** - only write to GCS when explicitly configured
1. **Gradual migration** - can test GCS writes selectively

### Negative

1. **Additional configuration** - GitHub Actions needs environment variables
1. **Deferred complexity** - GCS client libraries added later
1. **Path handling** - Must ensure consistent path separators across platforms

## References

- SPEC-1 v2.2: Data Architecture Specification
- GitHub Actions documentation for environment variables
- Google Cloud Storage Python client documentation
