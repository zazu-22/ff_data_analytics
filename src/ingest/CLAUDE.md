# Ingest Package Context

**Location**: `src/ingest/`
**Purpose**: Packaged provider integrations (importable Python modules)

## Structure

```text
src/ingest/
├── __init__.py
├── common/          # Storage helpers, metadata patterns
├── nflverse/        # NFL data (Python-first with R fallback)
├── sheets/          # Google Sheets parsers
├── ffanalytics/     # Fantasy projections (R-based via subprocess)
└── ktc/             # Keep/Trade/Cut (stub, minimal client only)
```

Each provider package is self-contained with:

- `registry.py` - Dataset → loader function mapping
- Loader modules - Actual data fetch logic
- Tests in `tests/test_<provider>_*.py`

## Key Patterns

### Registry Pattern

Map logical dataset names to loader functions:

```python
# src/ingest/nflverse/registry.py
DATASETS = {
    'players': {
        'loader': 'load_players',
        'python_available': True,
        'r_available': True,
    },
    'weekly': {
        'loader': 'load_player_stats',
        'python_available': True,
        'r_available': True,
    },
}
```

### Storage Helper

All loaders use common storage pattern:

```python
from ingest.common.storage import write_partitioned_parquet

write_partitioned_parquet(
    df=data,
    base_path='data/raw/nflverse/players',
    partition_by='dt',
    partition_value='2024-09-29',
    metadata={
        'dataset': 'players',
        'loader_path': 'src.ingest.nflverse.shim',
        'source_name': 'nflreadpy',
        'source_version': nflreadpy.__version__,
        'asof_datetime': datetime.now(UTC).isoformat(),
    }
)
```

### Metadata Structure

Every load writes `_meta.json`:

```json
{
  "dataset": "players",
  "asof_datetime": "2024-09-29T12:00:00+00:00",
  "loader_path": "src.ingest.nflverse.shim",
  "source_name": "nflreadpy",
  "source_version": "0.1.3",
  "output_parquet": ["players_a1b2c3d4.parquet"],
  "row_count": 5432
}
```

### Output Path Convention

```text
data/raw/<provider>/<dataset>/dt=YYYY-MM-DD/
├── <dataset>_<uuid8>.parquet
└── _meta.json
```

### Utility Helpers: DuckDB-First with Fallback

For reference data needed during ingestion (player crosswalks, name aliases, team mappings):

**Pattern**: Query DuckDB first, fall back to source files

```python
from ff_analytics_utils.player_xref import get_player_xref
from ff_analytics_utils.name_alias import get_name_alias

# Default: Try DuckDB, fall back to Parquet/CSV
player_xref = get_player_xref()  # source='auto'
name_aliases = get_name_alias()  # source='auto'

# Force file fallback (for first run, testing)
player_xref = get_player_xref(source='parquet')
name_aliases = get_name_alias(source='csv')
```

**Why?**

- **Performance**: DuckDB queries faster than file parsing
- **Robustness**: File fallback ensures first-run works without `dbt seed`/`dbt run`
- **No hard dependency**: Ingestion can operate independently of dbt

**Available helpers**:

- `get_player_xref()` - DuckDB → Parquet (NFLverse ff_playerids)
- `get_name_alias()` - DuckDB → CSV (manual seed)
- `get_defense_xref()` - DuckDB → CSV (manual seed, planned in P1-028)

See `docs/dev/repo_conventions_and_structure.md` for full pattern documentation.

## Adding a New Provider

### 1. Create provider package

```bash
mkdir src/ingest/<provider>
touch src/ingest/<provider>/__init__.py
touch src/ingest/<provider>/registry.py
```

### 2. Define registry

```python
# src/ingest/<provider>/registry.py
DATASETS = {
    'dataset_name': {
        'loader': 'load_dataset_name',
        'description': 'Brief description',
    }
}
```

### 3. Implement loader

```python
# src/ingest/<provider>/loader.py
def load_dataset_name(
    out_dir: str = "data/raw/<provider>",
    **kwargs
) -> dict:
    """
    Load dataset from provider.

    Returns:
        dict: Manifest with output_path, row_count, etc.
    """
    # Fetch data
    df = fetch_from_api(**kwargs)

    # Write using storage helper
    from ingest.common.storage import write_partitioned_parquet
    result = write_partitioned_parquet(
        df=df,
        base_path=f"{out_dir}/dataset_name",
        partition_by='dt',
        partition_value=datetime.now(UTC).strftime('%Y-%m-%d'),
        metadata={...}
    )

    return result
```

### 4. Add to make_samples.py

Update `tools/make_samples.py` to support sampling from your provider.

### 5. Add tests

```python
# tests/test_<provider>_samples_pk.py
def test_provider_dataset_primary_keys():
    # Test PK uniqueness using sample data
    ...
```

### 6. Document

Add entry to this file and update root CLAUDE.md if needed.

## Provider-Specific Notes

### nflverse

- **Shim pattern**: Python-first with R fallback
- **Registry**: `src/ingest/nflverse/registry.py`
- **Loader**: `src/ingest/nflverse/shim.py::load_nflverse()`
- **R fallback**: `scripts/R/nflverse_load.R`

### sheets

- **Parser**: `src/ingest/sheets/commissioner_parser.py`
- **Normalization**: Transforms wide GM tabs → long-form tables
- **Auth**: Requires `GOOGLE_APPLICATION_CREDENTIALS`

### ffanalytics

- **Implementation**: R-based projections via subprocess
- **Registry**: `src/ingest/ffanalytics/registry.py`
- **Loader**: `src/ingest/ffanalytics/loader.py` (calls R runner)
- **R script**: `scripts/R/ffanalytics_run.R`
- **Features**: Weighted consensus from 8+ sources, player ID mapping
- **Status**: ✅ Production-ready (Track D: 100% complete)
- **Output**: Parquet with consensus projections and metadata

### ktc

- **Status**: Stub implementation (Track C: 0%)
- **Current**: Minimal client.py only, no registry.py
- **TODO**: Implement real fetcher with rate limiting and ToS compliance

## Testing Ingestion

```bash
# 1. Generate samples
uv run python tools/make_samples.py <provider> --datasets <list> --out ./samples

# 2. Verify PKs
pytest tests/test_<provider>_samples_pk.py

# 3. Check metadata
cat samples/<provider>/<dataset>/dt=*/\_meta.json | jq .
```

## Common Issues

**Import errors**: Ensure `PYTHONPATH=.` when running from repo root

**GCS auth**: Set `GOOGLE_APPLICATION_CREDENTIALS` or `GOOGLE_APPLICATION_CREDENTIALS_JSON`

**Missing datasets**: Check registry and ensure loader is implemented
