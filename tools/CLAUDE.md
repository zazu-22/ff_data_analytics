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

### parse_commissioner_local.py

**Purpose**: Parse commissioner sheets from local CSV → normalized Parquet (dev tool)

**Note**: For production ingestion, use `scripts/ingest/ingest_commissioner_sheet.py` instead.
This tool is for development/testing with local CSV files.

**Usage**:

```bash
# From Google Sheets URL
uv run python tools/parse_commissioner_local.py \
  --sheet-url <url> \
  --out-raw data/raw/commissioner \
  --out-csv data/review/commissioner

# From local directory (after sampling)
uv run python tools/parse_commissioner_local.py \
  --local-dir ./samples/sheets \
  --out-raw data/raw/commissioner \
  --out-csv data/review/commissioner
```

**Outputs**:

- Parquet: `data/raw/commissioner/{contracts_active,contracts_cut,draft_picks}/dt=YYYY-MM-DD/`
- CSV previews: `data/review/commissioner/*.csv` (for manual review)

**Requires**: `GOOGLE_APPLICATION_CREDENTIALS` or `GOOGLE_APPLICATION_CREDENTIALS_JSON`

______________________________________________________________________

### analyze_snapshot_coverage.py

**Purpose**: Analyze snapshot coverage for any data source to understand data freshness, coverage, and entity counts

**Usage**:

```bash
# Analyze nflverse (default)
PYTHONPATH=. uv run python tools/analyze_snapshot_coverage.py

# Analyze a different source
PYTHONPATH=. uv run python tools/analyze_snapshot_coverage.py --source data/raw/sleeper

# Analyze specific datasets only
PYTHONPATH=. uv run python tools/analyze_snapshot_coverage.py --datasets weekly snap_counts

# Custom output directory and filename
PYTHONPATH=. uv run python tools/analyze_snapshot_coverage.py \
  --out-dir data/review \
  --out-name custom_report
```

**Outputs**:

- JSON: `{out_dir}/{out_name}.json` - Detailed metrics per snapshot
- Markdown: `{out_dir}/{out_name}_report.md` - Human-readable coverage report

**Key Features**:

- Works with any data source (nflverse, sleeper, commissioner, etc.)
- Analyzes Parquet files in date-partitioned directories (`dt=YYYY-MM-DD`)
- Reports season/week coverage, entity counts, and snapshot overlaps
- Helps identify stale data, missing snapshots, and coverage gaps

**When to use**:

- Auditing data freshness and completeness
- Understanding what data exists in snapshots
- Identifying which snapshots dbt models should use
- Debugging data coverage issues

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
# Production: Unified atomic ingest (rosters + transactions)
uv run python scripts/ingest/ingest_commissioner_sheet.py

# Dev/testing: Parse from local samples
# 1. Sample from sheets
uv run python tools/make_samples.py sheets --tabs Andy Gordon Joe JP TRANSACTIONS --sheet-url <url> --out ./samples

# 2. Parse to Parquet
uv run python tools/parse_commissioner_local.py --local-dir ./samples/sheets --out-raw data/raw/commissioner

# 3. Run dbt staging
make dbt-run
```

## Adding New Tools

1. Create `tools/<tool_name>.py`
1. Add argparse CLI with `--help`
1. Use `src/` modules for logic
1. Document in this file
1. Add Makefile target if commonly used
