# Configuration

This directory contains configuration files for the FF Analytics project.

## Directory Structure

```text
config/
├── env_config.yaml        # Multi-environment path configuration
├── gcs/                   # GCS configuration
├── projections/           # Projection configuration
├── scoring/               # Scoring system configuration
└── secrets/               # Service account keys and secrets (gitignored)
```

## Environment Selection

The project supports multiple environments for flexible deployment:

- **`local`**: Development on local disk (default)
- **`ci`**: GitHub Actions (local disk)
- **`cloud`**: Prefect Cloud (GCS)

Set `FF_ENV` in your `.env` file to switch environments:

```bash
FF_ENV=local
```

## Configuration Priority

Configuration values are resolved in the following order (highest to lowest):

1. **Environment variables** (highest priority - explicit overrides)
2. **`.env` file** (user-specific local overrides)
3. **`config/env_config.yaml`** (environment-specific defaults based on `FF_ENV`)
4. **Defaults in dbt code** (lowest priority - fallback values)

This layered approach allows for:

- **Zero-config local development**: Works out of the box without any configuration
- **Environment-specific defaults**: Different paths for local/CI/cloud via `FF_ENV`
- **Selective overrides**: Override individual paths for testing without changing environment
- **Team consistency**: Shared defaults in `env_config.yaml` version controlled

## Zero-Config Local Development

The system works without any configuration. Defaults in dbt models use local paths (`data/raw/...`).

**Only override if you need**:

- Custom paths for testing
- Cloud storage (GCS)
- CI-specific configuration

## Example Usage

### Default Local Development (No Configuration Needed)

Simply run dbt commands - paths default to `data/raw/...`:

```bash
make dbt-run
make dbt-test
```

### Override Specific Paths for Testing

Add to your `.env` file:

```bash
# Test with a custom snapshot location
RAW_NFLVERSE_WEEKLY_GLOB="data/testing/nflverse/weekly/dt=*/*.parquet"
```

### Switch to Cloud Environment

Add to your `.env` file:

```bash
FF_ENV=cloud
GOOGLE_APPLICATION_CREDENTIALS=config/secrets/gcp-service-account-key.json
```

All paths will automatically resolve to `gs://ff-analytics/raw/...` based on `env_config.yaml`.

## Snapshot Governance

The `env_config.yaml` file defines path globs for all raw data sources across environments:

**Sources**:

- NFLverse (weekly stats, snap counts, ff_opportunity, ff_playerids, schedule, teams)
- Google Sheets (cap_space, contracts_active, contracts_cut, draft_pick_holdings, transactions)
- Sleeper (fa_pool, rosters)
- KTC (assets)
- FFAnalytics (projections)

Each source has environment-specific globs that dbt models can reference via `env_var()` with fallback defaults.

## Best Practices

1. **Never commit `.env`** - It's gitignored and contains user-specific values
2. **Use `.env.template`** - Copy to `.env` and fill in your values
3. **Document overrides** - If you add new path variables, update `env_config.yaml` and this README
4. **Test with defaults first** - Ensure zero-config works before adding overrides
5. **Keep secrets in `config/secrets/`** - This directory is gitignored

## Related Documentation

- `../.env.template` - Template for local environment variables
- `./env_config.yaml` - Multi-environment path configuration
- `../docs/implementation/multi_source_snapshot_governance/` - Snapshot governance implementation
