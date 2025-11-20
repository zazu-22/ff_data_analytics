# Ingestion Triggers — Current State

**Last Updated**: 2025-11-20
**Status**: Active

## Overview

This document describes how data ingestion is triggered in the FF Analytics pipeline as of November 2025. The project currently uses a mix of **manual commands** (via `just`) and **GitHub Actions workflows** for orchestration, with Prefect integration planned but not yet implemented.

## Current Orchestration Mix

### GitHub Actions (Partial Automation)

**Active Workflows**:

1. **`.github/workflows/ingest_google_sheets.yml`** — Commissioner League Sheets

   - **Schedule**: Twice daily at 07:30 and 15:30 UTC (2:30 AM and 10:30 AM ET)
   - **Purpose**: Copy tabs from Commissioner's master sheet to internal copy
   - **Trigger**: Automated (cron schedule) + manual (workflow_dispatch)
   - **Features**: Discord notifications, dry run mode, skip-if-unchanged logic

2. **`.github/workflows/data-pipeline.yml`** — NFLverse + dbt

   - **Schedule**: Manual only (workflow_dispatch)
   - **Purpose**: Load NFLverse players dataset and run dbt models
   - **Note**: Not scheduled; used for testing and ad-hoc runs

**Limitations**:

- Only Google Sheets ingestion is fully automated
- NFLverse, KTC, FFAnalytics, Sleeper require manual triggering
- No orchestration dependencies between jobs
- No error recovery or retry logic

### Manual Commands (Primary - via `just`)

All sources can be loaded manually using `just` commands from the repository root:

```bash
# Individual sources
just ingest-nflverse      # Load NFLverse datasets (ff_playerids, weekly, snap_counts)
just ingest-sheets        # Parse internal sheet copy to Parquet snapshots
just ingest-sleeper       # Load Sleeper player database
just ingest-ktc           # Load KeepTradeCut dynasty values (1QB)
just ingest-ffanalytics   # Load FFAnalytics projections (15-20 min runtime)

# Composite workflows
just ingest-quick         # Load all sources EXCEPT ffanalytics (fast)
just ingest-full          # Load ALL sources including ffanalytics (slow)
```

**Use Cases**:

- Local development
- Ad-hoc data refreshes
- Testing new ingestion logic
- Backfilling missing snapshots

### Prefect Flows (Not Yet Implemented)

**Status**: Phase 4 planned, not started

- **Directory**: `src/flows/` does not exist
- **Plan**: Implement Prefect flows for all 5 sources (see Phase 4 tickets P4-001 through P4-006)
- **Benefits**: Dependency management, retry logic, observability, scheduling

**Next Steps**:

- Create flows directory and shared utilities (P4-001)
- Implement per-source flows (P4-002 through P4-006)
- Parallel run period with GitHub Actions
- See `docs/ops/ci_transition_plan.md` (when created)

## Trigger Frequency by Source

| Source          | Current Trigger                         | Ideal Frequency | Update Cadence                   | Rationale                                |
| --------------- | --------------------------------------- | --------------- | -------------------------------- | ---------------------------------------- |
| **sheets**      | GH Actions (2x daily: 07:30, 15:30 UTC) | Twice daily     | Real-time (Commissioner updates) | Roster changes during season             |
| **nflverse**    | Manual (`just ingest-nflverse`)         | Weekly          | Weekly (Tue/Wed post-games)      | NFL stats finalized 1-2 days after games |
| **sleeper**     | Manual (`just ingest-sleeper`)          | Weekly          | Daily (platform updates)         | Sleeper player DB for league sync        |
| **ktc**         | Manual (`just ingest-ktc`)              | Weekly          | Weekly (trade value updates)     | Dynasty values updated sporadically      |
| **ffanalytics** | Manual (`just ingest-ffanalytics`)      | Weekly          | Weekly (projection updates)      | Projections scrape is slow (15-20 min)   |

**Notes**:

- **sheets** is the only fully automated source (via GH Actions)
- **nflverse** should run weekly during season, but currently manual
- **ffanalytics** is slow (15-20 min) due to scraping 9 sources
- **ktc** and **sleeper** update sporadically; weekly checks sufficient

## Credential Storage

### Environment Variables (Local Development)

Store credentials in `.env` file (gitignored, never commit):

```bash
# Google Sheets/GCS
GOOGLE_APPLICATION_CREDENTIALS=config/secrets/gcp-service-account-key.json
# Or via JSON string
GCS_SERVICE_ACCOUNT_JSON='{"type": "service_account", ...}'

# Commissioner Sheets
COMMISSIONER_SHEET_ID="1jYAGKzPmaQnmvomLzARw9mL6-JbguwkFQWlOfN7VGNY"
LEAGUE_SHEET_COPY_ID="1HktJj-VB5Rc35U6EXQJLwa_h4ytiur6A8QSJGN0tRy0"

# Sleeper
SLEEPER_LEAGUE_ID=1230330435511275520

# Discord notifications (optional)
DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."

# Prefect Cloud (for future use)
PREFECT_API_KEY=pnu_...
PREFECT_WORKSPACE_NAME=ff-analytics
```

**Credential Files**:

- `config/secrets/gcp-service-account-key.json` — Google Sheets/GCS access
- Never commit files in `config/secrets/` (gitignored)

### Repository Secrets (GitHub Actions)

Configured in GitHub repo settings → Secrets and variables → Actions:

- `GOOGLE_APPLICATION_CREDENTIALS_JSON` — Base64-encoded service account JSON
- `COMMISSIONER_SHEET_ID` — Commissioner's master sheet ID
- `LEAGUE_SHEET_COPY_ID` — Internal sheet copy ID
- `LOG_PARENT_ID` — Google Drive folder ID for logs
- `DISCORD_WEBHOOK_URL` — Discord webhook for notifications (optional)

**Encoding for GitHub Secrets**:

```bash
# Encode service account key for GitHub secret
base64 -i config/secrets/gcp-service-account-key.json

# Decode in workflow (GitHub Actions does this automatically)
echo "$GOOGLE_APPLICATION_CREDENTIALS_JSON" | base64 -d > /tmp/gcp.json
```

### Service Account Permissions

**Google Cloud IAM roles** required for service account:

- `roles/storage.objectAdmin` — Read/write GCS buckets
- Google Sheets API enabled
- Google Drive API enabled (for sheet copy operations)

**Sheet Sharing**:

- Share Commissioner Sheet with service account email (`<name>@<project>.iam.gserviceaccount.com`)
- Share League Sheet Copy with service account (for writes)
- Share Log Parent Drive folder with service account

## Manual Load Instructions

All manual commands assume you're in the repository root (`/Users/jason/code/personal/ff_data_analytics`).

### NFLverse

Load NFL statistics from nflverse/nflreadr:

```bash
# Load all NFLverse datasets (recommended)
just ingest-nflverse

# Or use Python directly for specific datasets
uv run python -c "
from src.ingest.nflverse.shim import load_nflverse

# Load specific dataset
load_nflverse('ff_playerids')    # Player ID crosswalk
load_nflverse('weekly')          # Weekly player stats
load_nflverse('snap_counts')     # Snap count data
load_nflverse('ff_opportunity')  # Fantasy opportunity metrics

# Load multiple seasons
load_nflverse('weekly', seasons=[2024, 2025])
"
```

**Output**: `data/raw/nflverse/<dataset>/dt=YYYY-MM-DD/*.parquet`

### Google Sheets

Parse Commissioner's league sheet to Parquet:

```bash
# Recommended: Use just command
just ingest-sheets

# Or run script directly
uv run python scripts/ingest/ingest_commissioner_sheet.py
```

**Prerequisites**:

- Sheet copy must be up to date (GH Actions runs 2x daily)
- Service account credentials configured

**Output**: `data/raw/commissioner/<dataset>/dt=YYYY-MM-DD/*.parquet`

**Datasets**:

- `cap_space` — Salary cap by franchise
- `contracts_active` — Active player contracts
- `contracts_cut` — Cut player history
- `draft_picks` — Draft pick inventory
- `draft_pick_conditions` — Pick conditions/protections
- `transactions` — Transaction history

### Sleeper

Load Sleeper player database:

```bash
# Recommended: Use just command
just ingest-sleeper

# Or run loader directly
uv run python -m src.ingest.sleeper.loader players
```

**Output**: `data/raw/sleeper/players/dt=YYYY-MM-DD/*.parquet`

**Note**: League-specific data (rosters, trades) requires league ID configuration.

### KeepTradeCut (KTC)

Load KTC dynasty values (1QB format):

```bash
# Recommended: Use just command
just ingest-ktc

# Or use Python directly
uv run python -c "
from ingest.ktc.registry import load_players
load_players()  # Loads 1QB dynasty values by default
"
```

**Output**: `data/raw/ktc/players/dt=YYYY-MM-DD/*.parquet`

**Note**: Uses web scraping; may be slow or rate-limited.

### FFAnalytics Projections

Scrape projections from 9 sources (slow: 15-20 minutes):

```bash
# Recommended: Use just command (includes progress indicator)
just ingest-ffanalytics

# Or run loader directly
uv run python -c "
from src.ingest.ffanalytics.loader import load_projections_ros
load_projections_ros()  # Rest-of-season projections
"
```

**Output**: `data/raw/ffanalytics/projections/dt=YYYY-MM-DD/*.parquet`

**Data Sources** (9 scraped sites):

- FantasyPros, FantasySharks, FFToday, NumberFire, FantasyFootballNerd, CBS, ESPN, RTSports, Walterfootball

**Performance**: 15-20 minutes due to sequential scraping + rate limiting

## Composite Workflows

For convenience, use composite workflows that run multiple sources:

```bash
# Fast workflow (excludes slow FFAnalytics)
just ingest-quick
# Runs: nflverse, sheets, sleeper, ktc

# Full workflow (includes FFAnalytics - takes 20+ minutes)
just ingest-full
# Runs: nflverse, sheets, sleeper, ktc, ffanalytics
```

**Use Cases**:

- `ingest-quick` — Daily refreshes during development
- `ingest-full` — Weekly comprehensive refresh (best run overnight)

## Automated Triggers (GitHub Actions)

### Google Sheets Copy Workflow

**Workflow**: `.github/workflows/ingest_google_sheets.yml`

**Schedule**: Twice daily (cron)

- `30 7 * * *` — 07:30 UTC (2:30 AM ET)
- `30 15 * * *` — 15:30 UTC (10:30 AM ET)

**Process**:

1. Copy tabs from Commissioner's master sheet
2. Write to internal League Sheet Copy
3. Log copy operations to separate log sheet
4. Send Discord notification on completion
5. Skip if source sheet unchanged (configurable)

**Manual Trigger**:

```bash
# Via GitHub UI: Actions → Ingest Raw Google Sheets → Run workflow
# Options:
#   - force_copy: true/false (ignore skip-if-unchanged)
#   - dry_run: true/false (check only, no copy)
```

**Monitoring**:

- Discord notifications on success/failure
- Logs uploaded as GitHub artifacts (7-day retention)
- View logs spreadsheet: [link in .env file]

### NFLverse + dbt Workflow

**Workflow**: `.github/workflows/data-pipeline.yml`

**Schedule**: Manual only (workflow_dispatch)

**Process**:

1. Load NFLverse players dataset (sample)
2. Run dbt models
3. Run dbt tests

**Manual Trigger**:

```bash
# Via GitHub UI: Actions → Data Pipeline (nflverse + dbt) → Run workflow
# Options:
#   - out_dir: Output directory (local path or gs:// bucket)
```

**Note**: Not scheduled; used for testing dbt integration in CI environment.

## Prefect Migration Plan

**Current Status**: Not started (Phase 4)

**Planned Architecture**:

- `src/flows/` — Prefect flow definitions
- Per-source flows:
  - `copy_league_sheet_flow.py` — Copy Commissioner sheet tabs
  - `parse_league_sheet_flow.py` — Parse sheet to Parquet (depends on copy flow)
  - `nfl_data_pipeline_flow.py` — NFLverse ingestion
  - `ktc_pipeline_flow.py` — KTC ingestion
  - `ffanalytics_pipeline_flow.py` — FFAnalytics ingestion
  - `sleeper_pipeline_flow.py` — Sleeper ingestion

**Migration Steps** (see Phase 4 tickets):

1. Create flows directory and shared utilities (P4-001)
2. Implement per-source flows (P4-002 through P4-006)
3. Local testing and validation
4. Parallel run period (2 weeks) — Prefect + GitHub Actions
5. Validation comparison (data checksums, row counts)
6. Cut-over: Disable GitHub Actions, enable Prefect schedules

**Benefits**:

- Dependency management (sheet copy → sheet parse)
- Retry logic and error recovery
- Observability dashboard (Prefect UI)
- Programmatic scheduling
- Parameter passing between flows

## Data Freshness Monitoring

After ingestion, validate data freshness using the manifest validation tool:

```bash
# Check all sources
uv run python tools/validate_manifests.py --sources all --check-freshness

# Check specific source with custom threshold (in hours)
uv run python tools/validate_manifests.py --sources sheets --max-age 24

# CI/CD mode (fails if stale)
uv run python tools/validate_manifests.py --sources all --check-freshness --fail-on-gaps
```

**Default Freshness Thresholds**:

- **sheets**: 24 hours (daily updates expected)
- **nflverse**: 72 hours (weekly updates during season)
- **sleeper**: 24 hours (daily platform updates)
- **ktc**: 72 hours (weekly value updates)
- **ffanalytics**: 168 hours (weekly projections)

See `docs/ops/snapshot_management_current_state.md` for detailed validation procedures.

## Troubleshooting

### GitHub Actions Failure

**Symptom**: Workflow run fails in GitHub UI

**Diagnosis**:

1. Check workflow run logs: Actions → Select workflow → View logs
2. Verify service account credentials still valid
3. Check if sheets are still shared with service account
4. Verify repository secrets are populated

**Common Issues**:

- Service account key expired (keys expire after 90 days)
- Sheet permissions revoked
- Discord webhook URL changed/invalid (non-critical)
- Sheet structure changed (tabs renamed, columns reordered)

**Fix**:

```bash
# Regenerate service account key
gcloud iam service-accounts keys create config/secrets/gcp-service-account-key.json \
    --iam-account=<service-account-email>

# Update GitHub secret (base64 encode)
base64 -i config/secrets/gcp-service-account-key.json
# Copy output to GitHub repo settings → Secrets → GOOGLE_APPLICATION_CREDENTIALS_JSON
```

### Manual Load Failure

**Symptom**: `just ingest-<source>` command fails

**Diagnosis Steps**:

1. **Check credentials**:

   ```bash
   echo $GOOGLE_APPLICATION_CREDENTIALS
   # Should print path to service account key file

   ls -l $GOOGLE_APPLICATION_CREDENTIALS
   # File should exist and be readable
   ```

2. **Check Python environment**:

   ```bash
   uv run python --version  # Should be 3.13.x
   uv sync                  # Ensure deps installed
   ```

3. **Check network connectivity**:

   ```bash
   # Test Google Sheets API
   curl -I https://sheets.googleapis.com/

   # Test nflverse data source
   curl -I https://github.com/nflverse/nflverse-data
   ```

4. **Check output directory permissions**:

   ```bash
   ls -ld data/raw/<source>
   # Directory should exist and be writable

   mkdir -p data/raw/<source>  # Create if missing
   ```

**Common Issues**:

- `.env` file not loaded (use `uv run` commands, not raw Python)
- Service account permissions insufficient
- Output directory doesn't exist or not writable
- Network firewall blocking API access
- Rate limiting (especially KTC, FFAnalytics)

**Fix Examples**:

```bash
# Reload .env file
source .env
export $(cat .env | xargs)

# Verify service account has correct permissions
gcloud projects get-iam-policy $GCP_PROJECT_ID \
    --flatten="bindings[].members" \
    --filter="bindings.members:serviceAccount:<service-account-email>"

# Create output directories
mkdir -p data/raw/{nflverse,commissioner,sleeper,ktc,ffanalytics}

# Test with verbose logging
DEBUG=true uv run python -c "from src.ingest.nflverse.shim import load_nflverse; load_nflverse('ff_playerids')"
```

### Data Not Appearing in dbt

**Symptom**: `just dbt-run` succeeds but tables are empty

**Diagnosis**:

1. **Check if data actually loaded**:

   ```bash
   ls -lh data/raw/<source>/<dataset>/dt=*/
   # Should see .parquet files with non-zero size
   ```

2. **Check snapshot selection**:

   ```bash
   # What snapshot is dbt using?
   just dbt-compile --select stg_<source>__<dataset>
   cat dbt/ff_data_transform/target/compiled/.../stg_<source>__<dataset>.sql | grep "dt ="
   ```

3. **Query DuckDB directly**:

   ```bash
   duckdb dbt/ff_data_transform/target/dev.duckdb

   # Within DuckDB:
   SELECT COUNT(*) FROM read_parquet('data/raw/<source>/<dataset>/dt=*/*.parquet');
   ```

**Common Issues**:

- Data loaded but snapshot date doesn't match dbt filter
- Snapshot registry not updated after new load
- `EXTERNAL_ROOT` env var pointing to wrong path
- Parquet files corrupted or zero-byte

**Fix**:

```bash
# Update snapshot registry after new load
just dbt-seed --select snapshot_registry --full-refresh

# Verify EXTERNAL_ROOT (should be absolute path)
echo $EXTERNAL_ROOT  # Should be /Users/jason/code/personal/ff_data_analytics/data/raw

# Check for corrupted files
find data/raw/<source> -name "*.parquet" -size 0

# Re-run ingestion if data missing
just ingest-<source>
```

## References

### GitHub Actions

- Sheets workflow: `.github/workflows/ingest_google_sheets.yml`
- NFLverse workflow: `.github/workflows/data-pipeline.yml`

### Scripts

- NFLverse loader: `scripts/ingest/load_nflverse.py`
- Sleeper loader: `scripts/ingest/load_sleeper.py`
- Sheet copy: `scripts/ingest/copy_league_sheet.py`
- Sheet parser: `scripts/ingest/ingest_commissioner_sheet.py`
- FFAnalytics runner: `scripts/R/ffanalytics_run.R`

### Ingestion Modules

- `src/ingest/nflverse/` — NFLverse datasets
- `src/ingest/sheets/` — Google Sheets parsing
- `src/ingest/sleeper/` — Sleeper API integration
- `src/ingest/ktc/` — KeepTradeCut scraping
- `src/ingest/ffanalytics/` — FFAnalytics projections

### Documentation

- Snapshot management: `docs/ops/snapshot_management_current_state.md`
- Ingestion patterns: `src/ingest/CLAUDE.md`
- Repository conventions: `docs/dev/repo_conventions_and_structure.md`
- Phase 4 Prefect tickets: `docs/implementation/multi_source_snapshot_governance/tickets/P4-*.md`

### Tools

- Manifest validation: `tools/validate_manifests.py`
- Snapshot coverage: `tools/analyze_snapshot_coverage.py`
- Registry maintenance: `tools/update_snapshot_registry.py`

## Future State

**Note**: This document describes the current state as of November 2025. Future automation plans include:

- **Phase 4**: Prefect flows for all 5 sources with dependency management
- **Phase 5**: CI transition plan (parallel run, validation, cut-over)
- **Phase 6**: Cloud migration (GCS bucket layout, IAM setup)

For future plans, see:

- Implementation plan: `docs/implementation/multi_source_snapshot_governance/2025-11-07_plan_v_2_0.md`
- CI transition: `docs/ops/ci_transition_plan.md` (when created)
- Cloud migration: `docs/ops/cloud_storage_migration.md` (when created)

## Changelog

**2025-11-20**: Initial version created (P3-003)

- Documented current orchestration mix (GH Actions + manual commands)
- All 5 sources covered (nflverse, sheets, sleeper, ktc, ffanalytics)
- Manual `just` commands documented with examples
- GitHub Actions workflows documented (schedules, triggers)
- Credential storage patterns (local .env, GH secrets, service accounts)
- Troubleshooting guide for common issues
- Prefect migration status (not yet implemented)
