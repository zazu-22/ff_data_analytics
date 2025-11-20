# Orchestration Architecture

**Last Updated**: 2025-11-20
**Status**: GitHub Actions (Primary) + Manual Commands

## Overview

This document describes the orchestration architecture for data ingestion as of November 2025.

The project currently uses a two-layer orchestration approach: **GitHub Actions** for automated scheduled runs and **manual commands** (via `just` targets) for development and ad-hoc loads. A future migration to Prefect is planned but not yet implemented.

## Current Architecture (Nov 2025)

### Two-Layer Approach

1. **GitHub Actions** (Primary - Automated)

   - Scheduled workflows for nflverse and sheets
   - Simple, no infrastructure required
   - Limited orchestration capabilities
   - Production-ready for current scale

2. **Manual Commands** (Developer Use)

   - `just` targets for all sources
   - Used for development, testing, and ad-hoc loads
   - Direct Python/R script invocation
   - Full control over execution parameters

## Orchestration by Source

| Source          | Current Method                     | Schedule/Trigger            | Dependencies |
| --------------- | ---------------------------------- | --------------------------- | ------------ |
| **nflverse**    | GH Actions (workflow_dispatch)     | Manual trigger only         | None         |
| **sheets**      | GH Actions (scheduled)             | 2x daily (07:30, 15:30 UTC) | None         |
| **ktc**         | Manual (`just ingest-ktc`)         | On demand                   | None         |
| **ffanalytics** | Manual (`just ingest-ffanalytics`) | On demand                   | None         |
| **sleeper**     | Manual (`just ingest-sleeper`)     | On demand                   | None         |

### GitHub Actions Details

**File**: `.github/workflows/ingest_google_sheets.yml`

- **Trigger**: Scheduled at 07:30 and 15:30 UTC (twice daily)
- **Job**: `copy-league-sheet` - Copies commissioner Google Sheet to internal sheet
- **Runtime**: ~15 minutes
- **Features**:
  - Force copy option (manual trigger)
  - Dry run mode
  - Change detection (skip if unchanged)
  - Discord notifications
  - Log artifact upload

**File**: `.github/workflows/data-pipeline.yml`

- **Trigger**: Manual workflow_dispatch only
- **Jobs**:
  - Load nflverse (players sample)
  - Run dbt models
  - Run dbt tests
- **Runtime**: ~30 minutes
- **Features**:
  - Configurable output directory
  - GCS credentials support (optional)

### Manual Command Details

**Available via `justfile`**:

```bash
# Full ingestion (all sources)
just ingest-full

# Quick ingestion (nflverse + sheets only)
just ingest-quick

# Individual sources
just ingest-nflverse
just ingest-sheets
just ingest-sleeper
just ingest-ktc
just ingest-ffanalytics

# dbt operations
just dbt-compile
just dbt-run
just dbt-test
```

**Scripts** (called by `just` targets):

- `scripts/ingest/load_nflverse.py` - NFLverse data loader
- `scripts/ingest/copy_league_sheet.py` - Google Sheets copy operation
- `scripts/ingest/ingest_commissioner_sheet.py` - Google Sheets parse operation
- `scripts/ingest/load_sleeper.py` - Sleeper API loader
- R scripts for ffanalytics (via `Rscript`)

## Job Dependencies

### Current Dependencies

```
┌─────────────┐
│  nflverse   │  Independent (can run anytime)
└─────────────┘

┌─────────────┐
│   sheets    │  Independent (can run anytime)
└─────────────┘

┌─────────────┐
│     ktc     │  Independent (can run anytime)
└─────────────┘

┌─────────────┐
│ ffanalytics │  Independent (can run anytime)
└─────────────┘

┌─────────────┐
│   sleeper   │  Independent (can run anytime)
└─────────────┘

┌──────────────────────────────────┐
│  dbt run (all staging models)    │  Depends on: All sources loaded
└──────────────────────────────────┘

```

**Notes**:

- Source loads are independent of each other
- dbt models depend on source data but not on each other (within staging layer)
- All sources can be loaded in parallel (when using manual commands)
- GitHub Actions runs sources sequentially (sheets only currently scheduled)

### Sheets-Specific Dependency

The Google Sheets ingestion has a two-step process:

```
copy_league_sheet.py  →  ingest_commissioner_sheet.py
(Copy from source)        (Parse and extract data)
```

**Timing**: GitHub Actions schedule ensures 30-minute gap between workflows (if separate workflows exist for parse step).

## Local vs Cloud Execution

### Local Execution (Current)

**Environment**: Developer laptop or GitHub Actions runner

**Characteristics**:

- Data stored locally (`data/raw/`)
- DuckDB database local (`dbt/ff_data_transform/target/dev.duckdb`)
- No orchestration server
- Manual or cron-based execution

**Usage**:

```bash
# Run ingestion manually
just ingest-full

# Or individual sources
just ingest-nflverse
just ingest-sheets
```

**GitHub Actions Runner**:

- Ephemeral Ubuntu VM
- 30-minute timeout
- Secrets managed via GitHub Secrets
- Artifacts uploaded for logs

### Cloud Execution (Future - Not Implemented)

**Planned Environment**: GCS + Cloud Run/Compute Engine + Prefect Cloud

**Characteristics**:

- Data stored in GCS (`gs://ff-analytics/raw/`)
- DuckDB connects to GCS via httpfs
- Persistent Prefect Cloud server
- Scheduled deployments

**Status**: Deferred to future work (Phase 4+ of Multi-Source Snapshot Governance epic)

## Data Quality & Governance Integration

### Current Validation

**Post-Load Validation** (manual):

```bash
# Validate manifests after any load
uv run python tools/validate_manifests.py

# Analyze snapshot coverage
uv run python tools/analyze_snapshot_coverage.py
```

**dbt Tests** (automated in GH Actions):

```bash
just dbt-test
```

**Freshness Checks**:

- Implemented as dbt `freshness` tests in source YAML files
- Thresholds vary by source (1-7 days warn, 7-14 days error)
- See: `dbt/ff_data_transform/models/sources/src_*.yml`

### Governance Features

Each data load (whether GH Actions or manual) should include:

1. **Pre-load checks**: Credentials, API availability
2. **Post-load validation**: Run `validate_manifests.py`
3. **Freshness verification**: Check snapshot recency
4. **Row count anomaly detection**: Flag unusual deltas
5. **Required columns check**: Ensure schema compliance

**Status**:

- Pre-load checks: Implemented in scripts (credential validation)
- Post-load validation: Manual execution (not automated in GH Actions yet)
- Freshness tests: Implemented in dbt
- Anomaly detection: Available via `analyze_snapshot_coverage.py` (manual)
- Column checks: Implemented in `validate_manifests.py`

## CI Integration

### Current (GitHub Actions)

```yaml
# .github/workflows/ingest_google_sheets.yml
name: Ingest Raw Google Sheets

on:
  schedule:
    - cron: "30 7 * * *"   # 07:30 UTC daily
    - cron: "30 15 * * *"  # 15:30 UTC daily
  workflow_dispatch:       # Manual trigger

jobs:
  copy-league-sheet:
    runs-on: ubuntu-latest
    steps:
      - name: Run Copy League Sheet
        run: uv run python scripts/ingest/copy_league_sheet.py

      - name: Send Discord notification
        # (Discord webhook integration)
```

**Missing**:

- Post-load manifest validation (not yet in workflow)
- Parse step as separate job (currently only copy is scheduled)
- dbt run after sheets update

### Future (Prefect - Planned)

**Phase 4 Plan** (from epic):

- Prefect deployments triggered by schedule or event
- GitHub Actions remains as backup/failover
- Parallel run period before full cut-over
- Centralized orchestration for all 5 sources

**Directory Structure** (to be created):

```
src/flows/
├── copy_league_sheet_flow.py
├── parse_league_sheet_flow.py
├── nfl_data_pipeline.py
├── ktc_pipeline.py
├── ffanalytics_pipeline.py
├── sleeper_pipeline.py
└── shared/
    ├── validation.py
    ├── notifications.py
    └── governance.py
```

**Status**: Not yet implemented (Phase 4 of epic)

See: `docs/spec/prefect_dbt_sources_migration_20251026.md` for detailed Prefect plan

## Architecture Decisions

### Why GitHub Actions (for now)?

1. **Simplicity**: No infrastructure to manage
2. **Proven**: Working solution, low risk
3. **Zero cost**: Included in GitHub plan
4. **Good enough**: Current scale doesn't need complex orchestration
5. **Fast to implement**: Quicker than setting up Prefect Cloud

### Why Plan Prefect Migration?

1. **Better orchestration**: DAG-based dependencies, retries, monitoring
2. **Governance integration**: Validation tasks as first-class citizens
3. **Scalability**: Can run locally or in cloud
4. **Developer experience**: Python-native, easy testing
5. **Observability**: Built-in monitoring and alerting

### Why Keep GitHub Actions Initially?

1. **Risk mitigation**: Proven, working solution
2. **Fallback option**: If Prefect fails, GH Actions can take over
3. **Parallel run**: Validate Prefect outputs match GH Actions
4. **Incremental migration**: Test Prefect locally before cloud deployment

## Current Limitations

### Orchestration Gaps

1. **No automatic post-load validation**: `validate_manifests.py` not run after GH Actions loads
2. **No dependency management**: Sources run independently, no DAG
3. **Limited monitoring**: Relies on GH Actions logs and Discord notifications
4. **No retry logic**: Failed runs require manual intervention
5. **No backfill orchestration**: Historical loads are manual processes

### Scheduling Gaps

1. **Sheets only**: Only Google Sheets is scheduled
2. **NFLverse manual**: Requires manual trigger (workflow_dispatch)
3. **KTC/Sleeper/FFAnalytics**: No automation, purely manual
4. **No off-season adjustment**: Schedule doesn't change based on NFL season

### Data Quality Gaps

1. **No automated anomaly detection**: Row count checks are manual
2. **No automatic freshness alerts**: Rely on manual dbt test runs
3. **No cross-source validation**: Each source validated independently
4. **No data profiling**: No automatic stats collection

## Future Roadmap

### Phase 4: Prefect Implementation (Planned)

**Deliverables**:

- [ ] `src/flows/` directory structure
- [ ] 7 Prefect flows (5 source pipelines + 2 sheets flows)
- [ ] Shared utilities (validation, notifications, governance)
- [ ] Local testing complete
- [ ] Documentation updated

**Timeline**: TBD (see epic plan)

### Phase 5: CI Transition (Planned)

**Deliverables**:

- [ ] Parallel run strategy (Prefect + GH Actions)
- [ ] Validation comparison (outputs match)
- [ ] Cut-over plan
- [ ] Rollback procedures

**Timeline**: After Phase 4 complete

### Phase 6: Cloud Deployment (Future)

**Deliverables**:

- [ ] GCS storage migration
- [ ] Prefect Cloud setup
- [ ] Cloud Run deployment
- [ ] Monitoring dashboards
- [ ] Production scheduling

**Timeline**: Long-term (6+ months)

## References

- GitHub Actions: `.github/workflows/`
- Manual scripts: `scripts/ingest/`
- Justfile targets: `justfile`
- Prefect detailed spec: `docs/spec/prefect_dbt_sources_migration_20251026.md`
- Epic plan: `docs/implementation/multi_source_snapshot_governance/2025-11-07_plan_v_2_0.md`
- Validation tools: `tools/validate_manifests.py`, `tools/analyze_snapshot_coverage.py`
