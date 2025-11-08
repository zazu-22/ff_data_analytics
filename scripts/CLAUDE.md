# Scripts Context

**Location**: `scripts/`
**Purpose**: Operational runners and utilities (not importable libraries)

Difference from `tools/`: Scripts are typically invoked by CI/CD or for one-off operations, while tools are for iterative development.

## Directory Structure

| Directory          | Purpose                   | When to Use                          |
| ------------------ | ------------------------- | ------------------------------------ |
| `ingest/`          | Production data ingestion | CI workflows, scheduled runs         |
| `R/`               | R-based loaders           | When Python alternatives unavailable |
| `setup/`           | One-time initialization   | Environment setup, bucket creation   |
| `troubleshooting/` | Debugging utilities       | Investigating issues                 |
| `debug/`           | Development helpers       | Local debugging only                 |

## Key Scripts

### ingest/copy_league_sheet.py

**Purpose**: Server-side Google Sheets copier implementing ADR-005

**Why**: Commissioner sheet is too complex for direct API reads (formulas, external connections)

**Strategy**:

1. Use Google Sheets API `copyTo()` to duplicate tabs
2. Freeze formulas to values via batch operations
3. Atomic rename/swap for consistency
4. Log to Shared Drive (avoids service account quota)

**Usage**: Invoked by GitHub Actions workflow

**Requires**:

- `COMMISSIONER_SHEET_ID` (source)
- `LEAGUE_SHEET_COPY_ID` (destination)
- `LOG_PARENT_ID` (Shared Drive folder for logs)

**Skip Logic**: Checks source `modifiedTime` to avoid unnecessary copies

______________________________________________________________________

### ingest/ingest_league_sheet_to_gcs.py

**Purpose**: Legacy sheet ingestion to GCS

**Status**: Being replaced by copy_league_sheet.py + commissioner_parse.py workflow

______________________________________________________________________

### R/ffanalytics_run.R

**Purpose**: Scrape weekly fantasy projections from multiple sources with weighted consensus

**Status**: ✅ Production-ready (Track D: 100% complete)

**Config**: `config/projections/ffanalytics_projections_config.yaml`

**Invoked by**: Python via `subprocess` from `src/ingest/ffanalytics/loader.py`

**Features**:

- Weighted consensus from 8+ sources (CBS, ESPN, FantasyPros, etc.)
- Site weights from `config/projections/ffanalytics_projection_weights_mapped.csv`
- Player name → ID mapping via `dim_player_id_xref` seed
- Both raw projections and consensus output

**Outputs**:

- `projections_raw_*.parquet` - Individual source projections
- `projections_consensus_*.parquet` - Weighted aggregation
- Metadata with player mapping stats, source success/failure

**Usage**:

```bash
Rscript scripts/R/ffanalytics_run.R \
  --config config/projections/ffanalytics_projections_config.yaml \
  --scoring config/scoring/sleeper_scoring_rules.yaml
```

**Integration**: Parquet output → `stg_ffanalytics__projections` → `fact_player_projections` → projection marts

______________________________________________________________________

### R/nflverse_load.R

**Purpose**: Fallback loader when `nflreadpy` unavailable

**Called by**: `src/ingest/nflverse/shim.py`

**Usage**: Automatic fallback, not invoked directly

**Outputs**: Parquet + `_meta.json` (same format as Python loader)

______________________________________________________________________

## Credentials & Environment

All ingest scripts require authentication via:

- **Local**: `.env` file (see `.env.template`)
- **CI**: GitHub repo secrets

**Common variables**:

```bash
GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json
# OR
GOOGLE_APPLICATION_CREDENTIALS_JSON=<base64-encoded-json>

COMMISSIONER_SHEET_ID=<sheet-id>
LEAGUE_SHEET_COPY_ID=<copy-sheet-id>
LOG_PARENT_ID=<shared-drive-folder-id>
GCS_BUCKET=ff-analytics
```

## Adding New Scripts

**Operational script** (production use):

1. Create in appropriate subdirectory (`ingest/`, `setup/`, etc.)
2. Add argparse CLI
3. Document required environment variables
4. Add to GitHub Actions workflow if needed
5. Update this file

**One-off utility**:

1. Create in `troubleshooting/` or `debug/`
2. Add usage docstring
3. Not required to be production-ready

## CI Integration

Scripts are orchestrated by GitHub Actions:

- `.github/workflows/data-pipeline.yml` - nflverse ingestion
- `.github/workflows/ingest_google_sheets.yml` - commissioner sheets

See workflow files for scheduling and triggering.
