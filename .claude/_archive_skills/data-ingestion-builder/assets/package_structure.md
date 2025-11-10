# Provider Package Structure Template

When creating a new data ingestion provider, follow this directory structure:

```
src/ingest/{provider}/
├── __init__.py                  # Empty or package exports
├── registry.py                  # Dataset registry (REQUIRED)
├── loader.py                    # Loader functions (REQUIRED)
└── README.md                    # Provider documentation (optional)

tests/
└── test_{provider}_samples_pk.py    # Primary key tests (REQUIRED)

samples/{provider}/              # Sample data for testing
└── {dataset}/
    └── dt=YYYY-MM-DD/
        ├── {dataset}_{uuid}.parquet
        └── _meta.json
```

## File Purposes

### `__init__.py`
Empty file or exports for package:
```python
"""ingest/{provider} package."""
```

### `registry.py` (REQUIRED)
Maps dataset names to loader functions and metadata:
- Dataset specifications with primary keys
- Loader function mappings
- Documentation and notes

See: `assets/registry_template.py`

### `loader.py` (REQUIRED)
Implements data fetching and storage:
- One function per dataset
- Uses `ingest.common.storage` helpers
- Writes Parquet with metadata sidecars
- Returns manifest dict

See: `assets/loader_template.py`

### `test_{provider}_samples_pk.py` (REQUIRED)
Validates sample data quality:
- Primary key uniqueness tests
- Metadata sidecar validation
- Sample data completeness checks

See: `assets/test_template.py`

### Sample Data Structure
Each dataset follows:
```
samples/{provider}/{dataset}/dt=YYYY-MM-DD/
├── {dataset}_{uuid8}.parquet
└── _meta.json
```

Metadata JSON structure:
```json
{
  "dataset": "dataset_name",
  "asof_datetime": "2024-10-27T12:00:00+00:00",
  "loader_path": "src.ingest.{provider}.loader.load_{dataset}",
  "source_name": "{PROVIDER}",
  "source_version": "1.0.0",
  "output_parquet": "path/to/file.parquet",
  "row_count": 1234
}
```

## Integration Points

### Update `tools/make_samples.py`
Add provider-specific sampling logic:
```python
elif args.provider == "{provider}":
    from ingest.{provider}.loader import load_{dataset}
    result = load_{dataset}(out_dir=args.out, **provider_args)
```

### Update Project Documentation
Add entries to:
- `src/ingest/CLAUDE.md` - Provider-specific notes
- Root `CLAUDE.md` - If architecturally significant
- `README.md` - If user-facing

## Naming Conventions

- **Provider name**: lowercase, underscore-separated (e.g., `nflverse`, `my_provider`)
- **Dataset names**: lowercase, descriptive (e.g., `players`, `weekly_stats`)
- **Loader functions**: `load_{dataset_name}` (e.g., `load_players`)
- **Test file**: `test_{provider}_samples_pk.py`
- **Parquet files**: `{dataset}_{uuid8}.parquet`

## Output Path Convention

Raw data follows:
```
data/raw/{provider}/{dataset}/dt=YYYY-MM-DD/
├── {dataset}_{uuid}.parquet
└── _meta.json
```

Or for cloud:
```
gs://ff-analytics/raw/{provider}/{dataset}/dt=YYYY-MM-DD/
├── {dataset}_{uuid}.parquet
└── _meta.json
```
