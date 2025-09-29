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
uv run python tools/make_samples.py sheets --tabs <list> --sheet-url <url> --out ./samples
```

**Makefile shortcut**: `make samples-nflverse`

**Key Features**:

- Preserves raw provider schemas
- Small datasets for fast testing
- Used before dbt development

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

**Usage**: See implementation checklist (tool under development)

**Future**: Will integrate with `scripts/R/ffanalytics_run.R` output

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
uv run python tools/make_samples.py sheets --tabs <all-gm-tabs> --sheet-url <url> --out ./samples

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
