# Tools Context

**Location**: `tools/`
**Purpose**: CLI utilities for development and operational tasks

All tools use `uv run` for execution. Set `PYTHONPATH=.` if importing from `src/`.

## Tools Overview

### make_samples.py

**Purpose**: Generate small test Parquet files from real providers

**Usage**:

```bash
# NFLverse samples
uv run python tools/make_samples.py nflverse --datasets players weekly --seasons 2024 --weeks 1 --out ./samples

# Sleeper samples
uv run python tools/make_samples.py sleeper --datasets league users rosters --league-id <id> --out ./samples

# Sheets samples (requires auth)
# GM roster tabs
uv run python tools/make_samples.py sheets --tabs Andy Gordon Joe --sheet-url <url> --out ./samples

# TRANSACTIONS tab
uv run python tools/make_samples.py sheets --tabs TRANSACTIONS --sheet-url <url> --out ./samples

# FFanalytics projections (requires R + ffanalytics package)
PYTHONPATH=. uv run python tools/make_samples.py ffanalytics \
  --config config/projections/ffanalytics_projections_config.yaml \
  --scoring config/scoring/sleeper_scoring_rules.yaml \
  --out ./samples
```

**Makefile shortcut**: `make samples-nflverse`

**Key Features**:

- Preserves raw provider schemas
- Small datasets for fast testing
- Used before dbt development
- **FFanalytics**: Calls R subprocess for weighted consensus projections (Track D: ✅ complete)

______________________________________________________________________

### commissioner_parse.py

**Purpose**: Parse commissioner sheets → normalized Parquet

**Usage**:

```bash
# From Google Sheets URL
uv run python tools/commissioner_parse.py \
  --sheet-url <url> \
  --out-raw data/raw/commissioner \
  --out-csv data/review/commissioner

# From local directory (after sampling)
uv run python tools/commissioner_parse.py \
  --local-dir ./samples/sheets \
  --out-raw data/raw/commissioner \
  --out-csv data/review/commissioner
```

**Outputs**:

- Parquet: `data/raw/commissioner/{roster,cut_contracts,draft_picks}/dt=YYYY-MM-DD/`
- CSV previews: `data/review/commissioner/*.csv` (for manual review)

**Requires**: `GOOGLE_APPLICATION_CREDENTIALS` or `GOOGLE_APPLICATION_CREDENTIALS_JSON`

______________________________________________________________________

### ffa_score_projections.py

**Purpose**: Apply scoring rules to FFAnalytics projections

**Status**: Experimental/superseded by R runner approach

**Note**: Fantasy scoring is now applied in dbt marts (`mart_fantasy_projections`) using `dim_scoring_rule`, following the 2×2 model pattern. This tool remains for potential standalone use cases.

______________________________________________________________________

### smoke_gcs_write.py

**Purpose**: Verify GCS write permissions and connectivity

**Usage**:

```bash
# Test write to GCS
uv run python tools/smoke_gcs_write.py --dest gs://<bucket>/test

# Test local write
uv run python tools/smoke_gcs_write.py --dest data/test
```

**Requires**: `GOOGLE_APPLICATION_CREDENTIALS` or `GOOGLE_APPLICATION_CREDENTIALS_JSON`

**When to use**:

- After setting up GCS credentials
- Before running production ingestion
- Debugging GCS connection issues

______________________________________________________________________

## Common Workflows

### Development Workflow

```bash
# 1. Generate samples
make samples-nflverse

# 2. Run dbt
make dbt-run

# 3. Test
make dbt-test
```

### Commissioner Data Workflow

```bash
# 1. Sample from sheets (or use copy_league_sheet.py)
# GM roster tabs
uv run python tools/make_samples.py sheets --tabs Andy Gordon Joe JP --sheet-url <url> --out ./samples

# TRANSACTIONS tab (separate sample for transaction history)
uv run python tools/make_samples.py sheets --tabs TRANSACTIONS --sheet-url <url> --out ./samples

# 2. Parse to Parquet
uv run python tools/commissioner_parse.py --local-dir ./samples/sheets --out-raw data/raw/commissioner

# 3. Run dbt staging
make dbt-run
```

## Adding New Tools

1. Create `tools/<tool_name>.py`
1. Add argparse CLI with `--help`
1. Use `src/` modules for logic
1. Document in this file
1. Add Makefile target if commonly used
