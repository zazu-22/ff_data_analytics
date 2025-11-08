# Ticket P3-003: Create ingestion_triggers_current_state Doc

**Phase**: 3 - Documentation\
**Estimated Effort**: Small (1-2 hours)\
**Dependencies**: P3-001 (SPEC checklist should be updated first)

## Objective

Create `docs/ops/ingestion_triggers_current_state.md` documenting how data loads are triggered today (GitHub Actions, manual commands, Prefect status).

## Context

This doc answers "how do loads run?" and "when/how does each source update?" It should describe current orchestration mix and provide clear instructions for triggering loads manually when needed.

## Tasks

- [ ] Create `docs/ops/ingestion_triggers_current_state.md`
- [ ] Document how loads run today (GH Actions schedules, manual make commands)
- [ ] List trigger frequency per source
- [ ] Document credential storage patterns (env vars, service accounts)
- [ ] Explain when/how each source updates
- [ ] Note Prefect migration plan status

## Acceptance Criteria

- [ ] Document answers "how do I trigger a load?"
- [ ] Trigger frequency documented per source
- [ ] Credential requirements clear
- [ ] Manual and automated triggers both covered

## Implementation Notes

**File**: `docs/ops/ingestion_triggers_current_state.md`

**Document Structure**:

````markdown
# Ingestion Triggers — Current State

**Last Updated**: 2025-11-07
**Status**: Active (transitioning to Prefect)

## Overview

This document describes how data ingestion is triggered as of November 2025.

## Current Orchestration Mix

### GitHub Actions (Primary - for now)

**Active workflows**:
- `.github/workflows/data-pipeline.yml` — nflverse, ffanalytics
- `.github/workflows/ingest_google_sheets.yml` — Commissioner sheets

**Schedule**:
- nflverse: Tuesday/Wednesday mornings (weekly during season)
- sheets: Daily at 6 AM ET
- ffanalytics: Weekly Wednesdays

### Manual Commands (Developer use)

```bash
# NFLverse load
uv run python -c "from ingest.nflverse.shim import load_nflverse; load_nflverse('weekly', seasons=[2024])"

# Sheets load
make ingest-sheets

# Projections
make run-projections
````

### Prefect Flows (In Development)

**Status**: Phase 4 implementation in progress

- Local flows implemented for all 5 sources
- Not yet deployed or scheduled
- See: `src/flows/` directory

## Trigger Frequency by Source

| Source          | Frequency | Trigger              | Rationale                          |
| --------------- | --------- | -------------------- | ---------------------------------- |
| **nflverse**    | Weekly    | GH Actions (Tue/Wed) | Updates 1-2 days post-games        |
| **sheets**      | Daily     | GH Actions (6 AM)    | Roster changes daily during season |
| **ktc**         | Manual    | On-demand            | Valuations update sporadically     |
| **ffanalytics** | Weekly    | GH Actions (Wed)     | Weekly projections                 |
| **sleeper**     | Manual    | On-demand            | League platform integration        |

## Credential Storage

### Environment Variables

```bash
# Google Sheets
export GOOGLE_APPLICATION_CREDENTIALS="path/to/service-account-key.json"

# Or via JSON string
export GCS_SERVICE_ACCOUNT_JSON='{"type": "service_account", ...}'

# Sleeper (if API key required)
export SLEEPER_API_KEY="..."
```

### Repository Secrets (GitHub Actions)

- `GCS_SERVICE_ACCOUNT_JSON` — Google Sheets access
- Stored in GitHub repo settings → Secrets

### Local Development

- Store credentials in `.env` file (gitignored)
- Use `uv run` to ensure env vars loaded

## Manual Load Instructions

### NFLverse

```bash
cd /Users/jason/code/ff_analytics
uv run python -c "
from ingest.nflverse.shim import load_nflverse
load_nflverse('weekly', seasons=[2024, 2025], out_dir='data/raw/nflverse')
"
```

### Google Sheets

```bash
make ingest-sheets
# Or directly:
uv run python src/ingest/sheets/commissioner_parser.py
```

### KTC

```bash
# When KTC loader is implemented
uv run python src/ingest/ktc/fetch.py
```

### FFAnalytics Projections

```bash
make run-projections
# Or directly:
Rscript scripts/R/run_projections.R
```

### Sleeper

```bash
# When Sleeper loader is implemented
uv run python src/ingest/sleeper/fetch.py
```

## Prefect Migration Status

**Current State**:

- GitHub Actions remain primary orchestrator
- Prefect flows exist but not deployed

**Next Steps** (Phase 4 completion):

- Local testing complete
- Parallel run period (2 weeks)
- Cut-over validation
- See: `docs/ops/ci_transition_plan.md`

## Troubleshooting

### Load Failed in GitHub Actions

1. Check workflow run logs in GitHub UI
2. Verify credentials still valid (service account keys expire)
3. Run load manually to reproduce issue
4. Check freshness tests: `cd dbt/ff_data_transform && uv run dbt source freshness`

### Manual Load Not Working

1. Verify PYTHONPATH: `export PYTHONPATH=.`
2. Check credentials: `echo $GOOGLE_APPLICATION_CREDENTIALS`
3. Test with sample flag: `... --samples=true`
4. Check logs in terminal output

## References

- GitHub Actions workflows: `.github/workflows/`
- Prefect flows: `src/flows/`
- Ingestion modules: `src/ingest/`
- CI transition plan: `docs/ops/ci_transition_plan.md`

```

## Testing

1. **Verify all commands work**: Test each manual load command
2. **Check GH Actions schedules**: Confirm cron expressions match description
3. **Link validation**: Ensure file paths correct

## References

- Plan: `../2025-11-07_plan_v_2_0.md` - Phase 3 Activity (lines 389-396)
- Checklist: `../2025-11-07_tasks_checklist_v_2_0.md` - Phase 3 Ops Docs (lines 217-223)
- Workflows: `.github/workflows/data-pipeline.yml`, `.github/workflows/ingest_google_sheets.yml`

```
