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

# Analyze specific datasets with all features
PYTHONPATH=. uv run python tools/analyze_snapshot_coverage.py \
  --datasets weekly snap_counts \
  --report-deltas \
  --detect-gaps \
  --check-mappings

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
- Delta reporting: row count changes between snapshots
- Gap detection: missing weeks in historical data (baseline_plus_latest aware)
- Player mapping rates: coverage in dim_player_id_xref
- Helps identify stale data, missing snapshots, and coverage gaps

**When to use**:

- Auditing data freshness and completeness
- Understanding what data exists in snapshots
- Identifying which snapshots dbt models should use
- Debugging data coverage issues
- Monitoring ingestion quality (use --report-deltas)

______________________________________________________________________

### update_snapshot_registry.py

**Purpose**: Synchronize snapshot registry with actual data files (maintenance tool)

**Status**: Temporary - will be deprecated after Phase 4 (Prefect orchestration)

**Usage**:

```bash
# Update all sources
python tools/update_snapshot_registry.py

# Update specific source
python tools/update_snapshot_registry.py --source nflverse

# Dry run (show changes without applying)
python tools/update_snapshot_registry.py --dry-run

# Update specific datasets
python tools/update_snapshot_registry.py --source nflverse --datasets weekly snap_counts
```

**What it does**:

- Scans `data/raw/` for all parquet snapshots
- Reads row counts and coverage metadata from actual files
- Updates `snapshot_registry.csv` with accurate values
- Preserves status and description fields (only updates metrics)

**When to use**:

- After manual data ingestion (before Phase 4)
- When registry row_count column is NULL/stale
- To fix registry drift or data quality issues
- One-time fix for missing metadata

**When NOT to use**:

- After Phase 4 Prefect flows are implemented (automated)
- For routine operations (should be automated)
- If you're just reading data (this is for data writers)

**Deprecation notice**: This tool is a temporary bridge until Phase 4 orchestration. In the long-term architecture, Prefect flows will update the registry atomically with data writes, eliminating the need for manual maintenance.

______________________________________________________________________

### validate_manifests.py

**Purpose**: Validate snapshot integrity and freshness against the snapshot registry

**Usage**:

```bash
# Basic integrity validation (all sources)
uv run python tools/validate_manifests.py --sources all

# Validate specific sources
uv run python tools/validate_manifests.py --sources nflverse,sheets

# With freshness validation (global thresholds)
uv run python tools/validate_manifests.py \
  --sources all \
  --check-freshness \
  --freshness-warn-days 2 \
  --freshness-error-days 7

# With per-source freshness thresholds
uv run python tools/validate_manifests.py \
  --sources all \
  --check-freshness \
  --freshness-config config/snapshot_freshness_thresholds.yaml

# CI mode (fail on stale data)
uv run python tools/validate_manifests.py \
  --sources nflverse,sheets \
  --check-freshness \
  --freshness-config config/snapshot_freshness_thresholds.yaml \
  --fail-on-gaps

# JSON output for programmatic use
uv run python tools/validate_manifests.py \
  --sources all \
  --check-freshness \
  --freshness-config config/snapshot_freshness_thresholds.yaml \
  --output-format json > validation_report.json
```

**What it validates**:

**Integrity checks** (always enabled):

- Snapshot directory exists at `data/raw/{source}/{dataset}/dt={snapshot_date}`
- `_meta.json` manifest present and valid JSON
- Required manifest fields present (dataset, loader_path, source_version, asof_datetime)
- Parquet files exist and are readable
- Row counts match registry expectations (if specified)

**Freshness checks** (opt-in with `--check-freshness`):

- Snapshot age (current date - snapshot_date)
- Age within warn/error thresholds (per-source or global)
- Status: FRESH / STALE (WARN) / STALE (ERROR)

**When to use**:

- **Pre-dbt safety check**: Run before dbt to catch stale/missing snapshots
- **CI validation**: Ensure data freshness in automated pipelines
- **Data quality audits**: Verify snapshot integrity after ingestion
- **Troubleshooting**: Diagnose data age or missing manifest issues

**Freshness thresholds** (from `config/snapshot_freshness_thresholds.yaml`):

| Source      | Warn (days) | Error (days) | Rationale                                      |
| ----------- | ----------- | ------------ | ---------------------------------------------- |
| nflverse    | 2           | 7            | Weekly in-season, updates within 2 days        |
| sheets      | 1           | 7            | Daily roster/transaction updates during season |
| sleeper     | 1           | 7            | Daily league activity updates                  |
| ffanalytics | 2           | 7            | Weekly projection updates during season        |
| ktc         | 5           | 14           | Sporadic market valuations updates             |

**Output examples**:

Text output (with freshness):

```
Snapshot Manifest Validation (with Freshness)
======================================================================

Validated: 22/24 snapshots (integrity)
Fresh: 18/24 snapshots (within thresholds)

Freshness Issues (4):

  nflverse.weekly [2025-11-10] STALE (WARN):
    - Snapshot STALE (WARN): 10 days old (threshold: 2 days)

  ktc.assets [2025-10-01] STALE (ERROR):
    - Snapshot STALE (ERROR): 50 days old (threshold: 14 days)
```

**Troubleshooting stale data**:

1. **Check ingestion status**: Verify when data was last fetched
2. **Seasonal variation**: Some sources update weekly during season only
3. **Run manual ingestion**: Use `scripts/ingest/` to refresh stale snapshots
4. **Adjust thresholds**: Edit `config/snapshot_freshness_thresholds.yaml` for offseason

**Why not dbt source freshness?**

This project uses external Parquet files read via `read_parquet()`, not database tables. dbt's `dbt source freshness` requires queryable tables with timestamp columns, making it architecturally incompatible. See ADR-002 for details.

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
2. Add argparse CLI with `--help`
3. Use `src/` modules for logic
4. Document in this file
5. Add Makefile target if commonly used
