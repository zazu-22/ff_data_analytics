# Unified Implementation Plan: Prefect + dbt Sources+ GCS/BigQuery Migration

## Overview

**Goal**: Transform from manual execution to fully
orchestrated data pipeline with monitoring,
scheduling, and cloud-ready architecture.

**Timeline**: 4 weeks to production-ready
Effort: ~20-30 hours (spread across 4 weeks for a
solo operator)

### Architecture Evolution

#### Current State (Week 0)

```text
Manual Execution:
    └─ GH Action (2x/day) → Copy Google Sheets
    └─ Manual: make ingest-sheets
    └─ Manual: make samples-nflverse
    └─ Manual: make dbt-run
    └─ Local: DuckDB + Parquet files
```

#### Target State (Week 4)

```text
Prefect Cloud (Orchestration):
    ├─ Flow: Google Sheets Pipeline (2x/day)
    │   ├─ Task: Copy sheets (GH Action webhook OR
native)
    │   ├─ Task: Ingest to Parquet
    │   └─ Task: Run dbt (seeds + models)
    │
    ├─ Flow: NFL Data Pipeline (Event-driven
schedule)
    │   ├─ Task: Load nflverse (Fri AM, Sun PM, Mon
AM, Tue AM, Wed noon, Thu AM)
    │   ├─ Task: Load FFanalytics (3x/week)
    │   ├─ Task: Load KTC (daily)
    │   ├─ Task: Load Sleeper (daily)
    │   └─ Task: Run dbt (incremental models)
    │
    └─ Flow: Backfill Pipeline (On-demand)
        ├─ Task: Backfill nflverse (2020-2024)
        ├─ Task: Backfill FFanalytics
        └─ Task: Run dbt (full refresh)
```

**Storage:** Local Parquet → Ready for GCS migration
**Warehouse:** DuckDB → Ready for BigQuery migration
**Sources:** dbt sources document data contracts
\*\*Monitoring: \*\*Prefect UI + Slack alerts

______________________________________________________________________

## Phases

### Phase 1: Foundation (Week 1)

**Goal**: Set up Prefect infrastructure and wrap
existing scripts

#### 1.1 Prefect Installation & Setup (Day 1: 2 hours)

```bash
# Install Prefect
uv add prefect

# Initialize Prefect (creates ~/.prefect/)
prefect config view

# Sign up for Prefect Cloud (free tier)
# https://app.prefect.cloud/
prefect cloud login

# Create workspace blocks for config
prefect block register -m prefect_shell
```

\*\*Deliverable: \*\*Working Prefect installation with Cloud connection

#### 1.2 Project Structure Setup

```text
ff_analytics/
├── flows/                         # NEW: Prefect flows
│   ├── __init__.py
│   ├── google_sheets_pipeline.py   # Flow 1
│   ├── nfl_data_pipeline.py        # Flow 2
│   ├── backfill_pipeline.py        # Flow 3
│   └── utils/                      # Shared utilities
│       ├── __init__.py
│       ├── dbt_runner.py           # dbt execution helpers
│       └── notifications.py        # Slack/email alerts
├── scripts/                        # EXISTING: Keep as-is
│   ├── ingest/                    # Your existing scripts
│   └── ...
└── dbt/ff_data_transform/
      └── models/sources/    # EXISTING: Will enhance incrementally
```

Deliverable: Directory structure for Prefect flows

#### 1.3 Convert First Script to Prefect Task (Day 2: 3

hours)

Start with Google Sheets (most critical, already
partially automated):

```python
	# flows/google_sheets_pipeline.py
	from prefect import flow, task
	from prefect.blocks.system import Secret
	import subprocess
	import logging
	from pathlib import Path
	from datetime import datetime

	logger = logging.getLogger(__name__)

	@task(name="Copy Google Sheets", retries=3, retry_delay_seconds=60, tags=["sheets", "ingestion"])

	def copy_google_sheets():
      """
      Copy Google Sheets to avoid rate limits.

      Currently triggered via GH Action.
      Future: Can call Sheets API directly here.
      """

      # For now, trigger GH Action via webhook
      # OR: Implement direct Sheets API call
      logger.info("Triggering sheet copy via GH Action")

      # Option A: Webhook to GH Action
      # gh_token = Secret.load("github-token").get()
      # requests.post(f"https://api.github.com/repos/{owner}/{repo}/dispatches", ...)

      # Option B: Wait for GH Action (check file timestamp)
      # Wait for copied sheet to appear in expected location

      # For Week 1: Keep GH Action as-is, just add monitoring
      logger.info("Sheet copy completed (via existing GH Action)")
      return True

	@task(name="Ingest Sheets to Parquet",
        retries=2,
        retry_delay_seconds=30,
        tags=["sheets", "ingestion"])

	def ingest_sheets_to_parquet(snapshot_date: str = None):
      """
      Run sheets ingestion script.

      Idempotent: Safe to run multiple times for same date.
      """

      if snapshot_date is None:
          snapshot_date = datetime.now().strftime("%Y-%m-%d")

      logger.info(f"Ingesting sheets data for {snapshot_date}")

      # Run existing script
      result = subprocess.run(
          ["make", "ingest-sheets"],
          cwd=Path(__file__).parent.parent,# repo root
          capture_output=True,
          text=True,
          timeout=300# 5 min timeout
      )

      if result.returncode != 0:
          logger.error(f"Sheets ingestion failed: {result.stderr}")
          raise Exception(f"Ingestion failed: {result.stderr}")

      logger.info(f"Sheets ingestion completed: {result.stdout}")
      return snapshot_date

	@task(name = "Run dbt Seeds", retries=1, tags=["dbt", "seeds"])

	def run_dbt_seeds():
      """Load dimension seeds (player xref, franchise, etc.)"""
      logger.info("Running dbt seeds")

      result = subprocess.run(
          ["make", "dbt-seed"],
          cwd=Path(__file__).parent.parent,
          capture_output=True,
          text=True,
          timeout=300
      )

      if result.returncode != 0:
          raise Exception(f"dbt seed failed: {result.stderr}")

      logger.info("dbt seeds completed")
      return True
	@task(name="Run dbt Models",
        retries=1,
        tags=["dbt", "transform"])

	def run_dbt_models(select: str = None):
      """
      Run dbt models.

      Args:
          select: Optional dbt selector (e.g., 'tag:sheets' or 'stg_sheets+')
      """

      logger.info(f"Running dbt models (select={select})")

      cmd = ["make", "dbt-run"]
      # TODO: Add select logic if needed

      result = subprocess.run(
          cmd,
          cwd=Path(__file__).parent.parent,
          capture_output=True,
          text=True,
          timeout=600# 10 min timeout
      )

      if result.returncode != 0:
          raise Exception(f"dbt run failed: {result.stderr}")

      logger.info("dbt run completed")
      return True

	@task(name="Run dbt Tests",
        retries=0,# Don't retry tests
        tags=["dbt", "quality"])
	def run_dbt_tests():
      """Run dbt tests for data quality validation"""
      logger.info("Running dbt tests")

      result = subprocess.run(
          ["make", "dbt-test"],
          cwd=Path__file__).parent.parent,
          capture_output=True,
          text=True,
          timeout=300
      )

      # Log but don't fail flow on test failures (depends on your preference)
      if result.returncode != 0:
          logger.warning(f"dbt tests had failures: {result.stderr}")
          # Optionally raise or just log
      else:
          logger.info("All dbt tests passed")

      return result.returncode == 0

	@flow(name="Google Sheets Pipeline",
        description="Copy sheets → Ingest → dbt transform",
        log_prints=True)
	def google_sheets_pipeline(run_tests: bool = True):
      """
      Complete Google Sheets data pipeline.

      Runs 2x per day to capture league updates.
      """
      logger.info("Starting Google Sheets pipeline")

      # Step 1: Copy sheets (via GH Action or direct API)
      copy_google_sheets()

      # Step 2: Ingest to Parquet
      snapshot_date = ingest_sheets_to_parquet()

      # Step 3: Run dbt seeds (player xref, franchise, etc.)
      run_dbt_seeds()

      # Step 4: Run dbt models (staging → core → marts)
      run_dbt_models()

      # Step 5: Run dbt tests (optional)
      if run_tests:
          tests_passed = run_dbt_tests()
          if not tests_passed:
              logger.warning("Pipeline completed but some tests failed")

      logger.info(f"Google Sheets pipeline completed for {snapshot_date}")
      return {"snapshot_date": snapshot_date,"tests_passed": tests_passed}

	# Deployment configuration
	if __name__ == "__main__":
      # For local testing:
      google_sheets_pipeline()

      # For deployment (run this once to deploy to Prefect Cloud):
      # google_sheets_pipeline.serve(
      #     name="sheets-pipeline-deployment",
      #     cron="0 6,18 * * *",# 6am and 6pm daily
      #     tags=["production", "sheets"]
      # )

```

Test it locally:

```bash
	# Run the flow locally
	python flows/google_sheets_pipeline.py

	# View in Prefect UI
	prefect server start# OR use Prefect Cloud UI
```

Deliverable: Working Google Sheets pipeline in
Prefect

####1.4 Deploy to Prefect Cloud (Day 2: 1 hour)

```
	# Deploy the flow with schedule
	python -c "
	from flows.google_sheets_pipeline import
	google_sheets_pipeline
	google_sheets_pipeline.serve(
      name='sheets-pipeline-prod',
      cron='0 6,18 * * *',# 6am and 6pm daily
      tags=['production', 'sheets']
	)"
```

# Verify in Prefect Cloud UI

# https://app.prefect.cloud/

Deliverable: Automated Google Sheets pipeline
running 2x/day

______________________________________________________________________

### Phase 2: NFL Data Sources (Week 2)

Goal: Add NFLverse, FFanalytics, KTC, Sleeper
ingestion flows

2.1 Create dbt Sources (Day 1: 2 hours)

Build source definitions incrementally as you add
flows:

```
	# dbt/ff_data_transform/models/sources/src_nflverse.yml
	version: 2

sources:
    - name: nflverse
      description: |
        NFLverse datasets loaded via Prefect.

        Schedule: Event-driven based on NFL week
        - Friday AM (TNF recap)
        - Sunday PM (early games)
        - Monday AM (SNF/MNF recap)
        - Tuesday AM (final stats)
        - Wednesday noon (pre-FAAD update)
        - Thursday AM (pre-lineup lock)

        Future: Will migrate to BigQuery external
tables pointing to GCS.

      # Commented out for local dev, uncomment for
BigQuery:
      # database: ff-analytics-project
      # schema: raw

      # Enable for production monitoring:
      # freshness:
      #   warn_after: {count: 24, period: hour}
      #   error_after: {count: 48, period: hour}

      tables:
        - name: weekly
          description: "Weekly player stats (71 stat
types)"
          # loaded_at_field: _ingestion_timestamp#
For freshness monitoring
          columns:
            - name: player_id
              description: "GSIS player ID (raw)"
            - name: season
              description: "NFL season year"
            - name: week
              description: "Week number (1-22)"
            - name: season_type
              description: "REG, POST, WC, DIV, CON,
SB, PRE"
            - name: team
              description: "Player's team"
            - name: position
              description: "Player position"
            # Key stats (document top 10-15, skip 71
stat columns for now)
            - name: completions
            - name: passing_yards
            - name: passing_tds
            - name: rushing_yards
            - name: rushing_tds
            - name: receptions
            - name: receiving_yards
            - name: receiving_tds

        - name: snap_counts
          description: "Player snap counts (6 stat
types)"
          columns:
            - name: pfr_player_id
              description: "Pro Football Reference ID
   (raw)"
            - name: game_id
              description: "nflverse game ID"
            - name: season
            - name: week
            - name: team
            - name: position
            - name: offense_snaps
            - name: defense_snaps
            - name: st_snaps

        - name: ff_opportunity
          description: "Fantasy opportunity metrics
(38 stat types)"
          columns:
            - name: player_id
              description: "GSIS player ID (raw)"
            - name: game_id
            - name: season
            - name: week
            - name: position
            # Key opportunity stats
            - name: pass_attempt
            - name: rec_attempt
            - name: rush_attempt
            - name: pass_air_yards
            - name: rec_air_yards
```

Similar files:

- src_ffanalytics.yml - Projections data
- src_ktc.yml - Market values
- src_sleeper.yml - League/roster data

Deliverable: Source definitions for all 6 data
sources

2.2 Build NFLverse Flow (Day 2-3: 4 hours)

```
# flows/nfl_data_pipeline.py
from prefect import flow, task
from datetime import datetime, timedelta
import subprocess
from pathlib import Path

@task(name="Load NFLverse Data",
        retries=3,
        retry_delay_seconds=[60, 120, 300],#
Exponential backoff
        tags=["nflverse", "ingestion"])
def load_nflverse(
      dataset: str,# 'weekly', 'snap_counts',
'ff_opportunity'
      season: int = None,
      week: int = None
):
      """
      Load NFLverse data for specific
dataset/season/week.

      Idempotent: Safe to run multiple times.
      """
      if season is None:
          season = datetime.now().year

      logger.info(f"Loading nflverse {dataset} for
{season} week {week}")

      # Call your existing load script
      # Assuming you have:
scripts/ingest/load_nflverse.py
      cmd = [
          "uv", "run", "python",
          "scripts/ingest/load_nflverse.py",
          "--dataset", dataset,
          "--season", str(season)
      ]
      if week:
          cmd.extend(["--week", str(week)])

      result = subprocess.run(
          cmd,
          cwd=Path(__file__).parent.parent,
          capture_output=True,
          text=True,
          timeout=600
      )

      if result.returncode != 0:
          raise Exception(f"NFLverse load failed:
{result.stderr}")

      logger.info(f"NFLverse {dataset} loaded
successfully")
      return {"dataset": dataset, "season": season,
"week": week}

@flow(name="NFL Weekly Data Update",
        description="Load all NFL data sources for
current week")
def nfl_weekly_update(season: int = None, week: int
   = None):
      """
      Load all NFL data for specific week.

      Runs after each slate of NFL games.
      """
      if season is None:
          season = datetime.now().year

      logger.info(f"Starting NFL data update for
{season} week {week}")

      # Load all nflverse datasets
      load_nflverse("weekly", season, week)
      load_nflverse("snap_counts", season, week)
      load_nflverse("ff_opportunity", season, week)

      # Load supplementary data
      load_ffanalytics(season, week)# Task defined
elsewhere
      load_ktc()# Always load latest
      load_sleeper()# Load league data

      # Run dbt incrementally
      run_dbt_models(select="tag:nfl_actuals")
      run_dbt_tests()

      logger.info(f"NFL data update completed for
{season} week {week}")
      return {"season": season, "week": week}

# Deployment with NFL-aware scheduling
if __name__ == "__main__":
      # Deploy with multiple schedules for different
update points
      nfl_weekly_update.serve(
          name="nfl-data-friday-am",
          cron="0 6 * * 5",# Friday 6am (TNF recap)
          tags=["production", "nfl", "tnf"]
      )

      # Add other schedules (Sunday PM, Monday AM,
Tuesday AM, etc.)
      # Or use Prefect Automations to trigger based
on events
```

Deliverable: Automated NFL data ingestion with
smart scheduling

2.3 Build FFanalytics, KTC, Sleeper Flows (Day 4-5:
4 hours)

Similar pattern to NFLverse. Create flows for:

- load_ffanalytics() - 3x/week
- load_ktc() - Daily
- load_sleeper() - Daily

Deliverable: All 6 data sources automated

______________________________________________________________________

### Phase 3: Backfill & Monitoring (Week 3)

Goal: Historical data backfill + comprehensive
monitoring

3.1 Backfill Flow (Day 1-2: 4 hours)

```
# flows/backfill_pipeline.py
from prefect import flow, task
from prefect.task_runners import
ConcurrentTaskRunner

@flow(name="Backfill NFLverse",
        description="Load historical nflverse data",
        task_runner=ConcurrentTaskRunner())
def backfill_nflverse(
      start_season: int = 2020,
      end_season: int = 2024,
      datasets: list = None
):
      """
      Backfill nflverse data for multiple seasons.

      Uses concurrent task runner for parallel loads.
      """
      if datasets is None:
          datasets = ["weekly", "snap_counts",
"ff_opportunity"]

      logger.info(f"Backfilling nflverse
{start_season}-{end_season}")

      # Load all seasons in parallel (or sequential
if you prefer)
      for season in range(start_season, end_season +
1):
          for dataset in datasets:
              # Load full season (week=None loads all
   weeks)
              load_nflverse.submit(dataset, season,
week=None)

      # After all loads complete, run dbt full
refresh
      run_dbt_models(full_refresh=True)

      logger.info(f"Backfill completed for
{start_season}-{end_season}")

# Run manually or on-demand
if __name__ == "__main__":
      backfill_nflverse(start_season=2020,
end_season=2024)
```

Usage:

```
# Run backfill on-demand
python flows/backfill_pipeline.py
```

Deliverable: Historical data loaded (2020-2024)

3.2 Monitoring & Alerting (Day 3-4: 4 hours)

```
# flows/utils/notifications.py
from prefect import get_run_logger
from prefect.blocks.notifications import
SlackWebhook

def notify_failure(flow_name: str, error: str):
      """Send Slack notification on flow failure"""
      slack =
SlackWebhook.load("ff-analytics-alerts")
      slack.notify(
          subject=f"🚨 {flow_name} Failed",
          body=f"Error: {error}\n\nCheck Prefect UI
for details."
      )

def notify_success(flow_name: str, metrics: dict):
      """Send Slack notification on success with
metrics"""
      slack =
SlackWebhook.load("ff-analytics-alerts")
      slack.notify(
          subject=f"✅ {flow_name} Completed",
          body=f"Metrics: {metrics}"
      )
```

Add to flows:

```
@flow(on_failure=[notify_failure],
        on_completion=[notify_success])
def google_sheets_pipeline():
      # ...flow logic...
```

Setup Slack webhook:

```
# In Prefect Cloud UI, create Slack webhook block
# Name: ff-analytics-alerts
# Webhook URL:
https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

Deliverable: Slack notifications for all flows

3.3 Data Freshness Monitoring (Day 5: 2 hours)

```
# flows/data_quality_checks.py
from prefect import flow, task
from datetime import datetime, timedelta

@task(name="Check Data Freshness")
def check_freshness(source: str, max_age_hours: int
   = 24):
      """
      Check if data source has been updated recently.

      Raises alert if data is stale.
      """
      # Check last file modification time in
data/raw/<source>/
      source_path = Path(f"data/raw/{source}")

      if not source_path.exists():
          raise Exception(f"Source {source} has no
data")

      # Find most recent file
      files = list(source_path.rglob("*.parquet"))
      if not files:
          raise Exception(f"Source {source} has no
parquet files")

      latest_file = max(files, key=lambda f:
f.stat().st_mtime)
      age_hours = (datetime.now().timestamp() -
latest_file.stat().st_mtime) / 3600

      if age_hours > max_age_hours:
          raise Exception(
              f"Source {source} is stale:
{age_hours:.1f} hours old "
              f"(max {max_age_hours})"
          )

      logger.info(f"Source {source} is fresh
({age_hours:.1f} hours old)")
      return {"source": source, "age_hours":
age_hours}

@flow(name="Data Freshness Check",
        description="Monitor data staleness across
all sources")
def freshness_check():
      """
      Run freshness checks for all data sources.

      Schedule: Hourly
      """
      sources = {
          "nflverse": 24,      # Alert if >24h old
          "ffanalytics": 48,   # Alert if >48h old
          "ktc": 24,           # Alert if >24h old
          "sleeper": 24,       # Alert if >24h old
          "commissioner": 12,# Alert if >12h old
      }

      for source, max_age in sources.items():
          check_freshness(source, max_age)

      logger.info("All sources are fresh")

# Deploy with hourly schedule
if __name__ == "__main__":
      freshness_check.serve(
          name="freshness-check-prod",
          cron="0 * * * *",# Every hour
          tags=["monitoring", "freshness"]
      )
```

Deliverable: Automated freshness monitoring

______________________________________________________________________

### Phase 4: GitHub Actions Integration & Documentation

(Week 4)

Goal: Integrate with existing GH Actions, document
for LLMs

#### 4.1 GH Actions ↔ Prefect Integration (Day 1-2: 3

hours)

Option A: Keep GH Action, trigger Prefect via
webhook

```
# .github/workflows/copy_sheets.yml (UPDATED)
name: Copy Google Sheets

on:
    schedule:
      - cron: '0 6,18 * * *'# 6am, 6pm
    workflow_dispatch:

jobs:
    copy-sheets:
      runs-on: ubuntu-latest
      steps:
        - name: Copy sheets
          # ... existing copy logic ...

        - name: Trigger Prefect Flow
          run: |
            curl -X POST \
              -H "Authorization: Bearer ${{
secrets.PREFECT_API_KEY }}" \
              -H "Content-Type: application/json" \
              https://api.prefect.cloud/api/accounts/
$ACCOUNT_ID/workspaces/$WORKSPACE_ID/deployments/$D
EPLOYMENT_ID/create_flow_run
```

Option B: Replace GH Action with Prefect entirely

```
# flows/google_sheets_pipeline.py (UPDATED)
@task
def copy_google_sheets():
      """Copy sheets using Google Sheets API
directly"""
      from google.oauth2 import service_account
      from googleapiclient.discovery import build

      credentials = service_account.Credentials.from_
service_account_file(
          'path/to/credentials.json',
          scopes=['https://www.googleapis.com/auth/sp
readsheets']
      )

      service = build('sheets', 'v4',
credentials=credentials)

      # Copy sheet logic here
      # ...
```

My recommendation: Start with Option A (keep GH
Action), migrate to Option B later

Deliverable: GH Actions integrated with Prefect

4.2 Documentation for LLMs (Day 3-4: 4 hours)

Create comprehensive docs optimized for LLM
context:

````
# docs/orchestration/PREFECT_ARCHITECTURE.md

# Prefect Orchestration Architecture

## Overview
This document describes the data orchestration
architecture for the FF Analytics project.
It is optimized for LLM coding assistants to
quickly understand the system.

## Data Flow

[Data Sources] → [Prefect Flows] → [dbt
Transformations] → [Analytics Marts]

## Flows

### 1. Google Sheets Pipeline
**Schedule**: 2x daily (6am, 6pm)
**Trigger**: Cron schedule
**Dependencies**: None (first in chain)
**Duration**: ~5 minutes

**Tasks**:
1. `copy_google_sheets()` - Copy commissioner sheet
2. `ingest_sheets_to_parquet()` - Parse to Parquet
3. `run_dbt_seeds()` - Load dimension seeds
4. `run_dbt_models()` - Transform data
5. `run_dbt_tests()` - Validate quality

**Outputs**:
- `data/raw/commissioner/transactions/dt=YYYY-MM-DD
/*.parquet`
- `data/raw/commissioner/contracts_active/dt=YYYY-M
M-DD/*.parquet`
- `data/raw/commissioner/contracts_cut/dt=YYYY-MM-D
D/*.parquet`

**dbt Sources Used**:
- `source('sheets', 'transactions')`
- `source('sheets', 'contracts_active')`
- `source('sheets', 'contracts_cut')`

### 2. NFL Data Pipeline
**Schedule**: Event-driven (6x per week)
**Triggers**:
- Friday 6am (TNF recap)
- Sunday 9pm (early games)
- Monday 6am (SNF/MNF)
- Tuesday 6am (final stats)
- Wednesday 12pm (FAAD prep)
- Thursday 6am (lineup lock prep)

**Tasks**:
1. `load_nflverse('weekly')` - Player stats
2. `load_nflverse('snap_counts')` - Snap data
3. `load_nflverse('ff_opportunity')` - Opportunity
metrics
4. `load_ffanalytics()` - Projections (3x/week
only)
5. `load_ktc()` - Market values (daily)
6. `load_sleeper()` - League data (daily)
7. `run_dbt_models(select='tag:nfl_actuals')` -
Transform
8. `run_dbt_tests()` - Validate

**Outputs**:
-
`data/raw/nflverse/weekly/dt=YYYY-MM-DD/*.parquet`
- `data/raw/nflverse/snap_counts/dt=YYYY-MM-DD/*.pa
rquet`
- `data/raw/nflverse/ff_opportunity/dt=YYYY-MM-DD/*
.parquet`
- `data/raw/ffanalytics/projections/dt=YYYY-MM-DD/*
.parquet`
- `data/raw/ktc/players/dt=YYYY-MM-DD/*.parquet`
- `data/raw/ktc/picks/dt=YYYY-MM-DD/*.parquet`
-
`data/raw/sleeper/rosters/dt=YYYY-MM-DD/*.parquet`

**dbt Sources Used**:
- `source('nflverse', 'weekly')`
- `source('nflverse', 'snap_counts')`
- `source('nflverse', 'ff_opportunity')`
- `source('ffanalytics', 'projections')`
- `source('ktc', 'players')`
- `source('ktc', 'picks')`
- `source('sleeper', 'rosters')`

### 3. Backfill Pipeline
**Schedule**: On-demand
**Trigger**: Manual execution
**Dependencies**: None

**Tasks**:
1. `backfill_nflverse(2020, 2024)` - Historical
data
2. `backfill_ffanalytics(2020, 2024)`
3. `run_dbt_models(full_refresh=True)`

## Dependencies Between Flows

```mermaid
graph TD
      A[Google Sheets Pipeline] --> C[dbt Transform]
      B[NFL Data Pipeline] --> C
      C --> D[Data Quality Checks]

Error Handling

All flows implement:
- Retries: 2-3 attempts with exponential backoff
- Timeouts: 5-10 minute limits per task
- Notifications: Slack alerts on failure
- Logging: Comprehensive logs in Prefect UI

Critical Sequences

Tuesday Morning (Post-MNF)

1. NFL Data Pipeline runs at 6am
2. Loads complete MNF stats
3. dbt builds updated marts
4. Freshness check validates all sources

Wednesday Midday (Pre-FAAD)

1. NFL Data Pipeline runs at 12pm
2. Updates projections for FAAD prep
3. Market values refreshed
4. Contract data synced

For LLM Assistants

When modifying flows:
1. Check flows/<flow_name>.py for flow definition
2. Check dbt/ff_data_transform/models/sources/ for data
contracts
3. Update both if schema changes
4. Test locally: python flows/<flow_name>.py
5. Deploy: Add .serve() call with schedule

Common patterns:
- All tasks are idempotent (safe to retry)
- All tasks have timeouts (prevent hangs)
- All tasks log verbosely (debugging)
- All flows notify on failure (monitoring)

File conventions:
- Flows: flows/<domain>_pipeline.py
- Tasks: Defined inline with flows
- Utils: flows/utils/<utility>.py
- Tests: tests/flows/test_<flow>.py

**Similar docs to create**:
- `docs/orchestration/DBT_SOURCES_GUIDE.md` - dbt
source contracts
- `docs/orchestration/MIGRATION_TO_GCS.md` - GCS
migration plan
- `docs/orchestration/ADDING_NEW_SOURCES.md` -
Template for new sources
````

**Deliverable**: Comprehensive LLM-optimized
documentation

### 4.3 Migration Readiness for GCS/BigQuery (Day

5: 2 hours)

**Document migration path**:

````markdown
# docs/orchestration/MIGRATION_TO_GCS.md

# Migration Path: Local → GCS → BigQuery

## Phase A: GCS Storage (No code changes)

**Change**: Store Parquet files in GCS instead of
local disk

**Steps**:

1. Create GCS bucket: `gs://ff-analytics/`
2. Update env var:
   `EXTERNAL_ROOT=gs://ff-analytics/raw/`
3. DuckDB reads directly from GCS (same code!)

**Prefect changes**: None (flows write to
EXTERNAL_ROOT)
**dbt changes**: None (reads from EXTERNAL_ROOT)
**Timeline**: 1 day

## Phase B: BigQuery Warehouse (Code changes

required)

**Change**: Load data into BigQuery tables

**Steps**:

1. Create BigQuery dataset: `ff-analytics.raw`
2. Update Prefect flows to load BigQuery instead of
   Parquet
3. Switch dbt adapter: `dbt-duckdb` →
   `dbt-bigquery`
4. Activate dbt sources: Uncomment
   `database`/`schema` in source YAMLs
5. Update staging models: `read_parquet()` → `{{
source() }}`

**Prefect changes**:

    ```python
    # OLD: Write Parquet
    df.to_parquet(f"{EXTERNAL_ROOT}/nflverse/weekly/...")

    # NEW: Load BigQuery
    from google.cloud import bigquery
    client = bigquery.Client()
    job = client.load_table_from_dataframe(df,"ff-analytics.raw.nflverse_weekly")
    ```

dbt changes:

    ```sql
    -- OLD: Read Parquet
    select * from
    read_parquet('data/raw/nflverse/weekly/...')

    -- NEW: Use source
    select * from {{ source('nflverse', 'weekly') }}
    ```
````

Timeline: 1-2 weeks

### Phase C: BigQuery External Tables (Hybrid approach)

Change: Keep Parquet in GCS, query via BigQuery
external tables

Best of both worlds:

- Parquet storage (cost-effective, portable)
- BigQuery compute (powerful querying)
- dbt sources (monitoring, freshness)

Steps:

1. Files stay in GCS as Parquet
2. Create BigQuery external tables pointing to GCS
3. dbt queries external tables via sources

Timeline: 3-5 days

Recommendation

Start with Phase A (GCS storage) immediately after
Prefect setup.
This is a simple env var change with zero code
changes.

Evaluate Phase B vs C in 3-6 months based on:

- Query performance needs
- Cost considerations
- Team BigQuery experience

**Deliverable**: Clear migration path documented

______________________________________________________________________

## Week 4 Deliverables Summary

✅ **Prefect Cloud deployed** with 3 main flows +
monitoring
✅ **dbt sources documented** for all 6 data
sources
✅ **Automated scheduling** for all ingestion
pipelines
✅ **Slack notifications** for failures and
successes
✅ **Freshness monitoring** for data staleness
✅ **Backfill capability** for historical data
✅ **GH Actions integrated** with Prefect
✅ **LLM-optimized documentation** for AI
assistants
✅ **GCS/BigQuery migration plan** documented

______________________________________________________________________

## Next Steps (Post-Week 4)

### Month 2: Optimization

- Add more granular dbt tags for selective runs
- Implement incremental models in dbt
- Fine-tune schedules based on actual NFL calendar
- Add data quality tests (Great Expectations)

### Month 3-4: GCS Migration

- Migrate storage to GCS (Phase A)
- Test DuckDB performance with GCS
- Prepare for BigQuery switch

### Month 5-6: BigQuery Migration

- Switch to BigQuery warehouse (Phase B or C)
- Activate dbt sources for freshness monitoring
- Optimize BigQuery partitioning/clustering

______________________________________________________________________

## Resource Requirements

### Infrastructure

- **Prefect Cloud**: Free tier (up to 20,000 task
  runs/month) - Sufficient
- **Google Sheets API**: Free tier (sufficient for
  2x/day)
- **Slack**: Free tier (webhook notifications)
- **GCS** (future): ~$20/month for 100GB Parquet
  files
- **BigQuery** (future): ~$50-100/month for queries
  - storage

### Time Investment

- **Week 1**: 7 hours (setup + first flow)
- **Week 2**: 10 hours (add all data sources)
- **Week 3**: 10 hours (backfill + monitoring)
- **Week 4**: 9 hours (integration + docs)
- **Total**: ~36 hours over 4 weeks

### Ongoing Maintenance

- **Weekly**: ~30 min (check dashboards, respond to
  alerts)
- **Monthly**: ~2 hours (update schedules, add
  sources)

______________________________________________________________________

## Success Criteria

After 4 weeks, you should have:

✅ **Zero manual data loads** - Everything
automated
✅ **Fresh data always** - NFL data within 6 hours
of games
✅ **Clear visibility** - Prefect UI shows all
pipeline status
✅ **Fast alerts** - Slack notification within 5
min of failures
✅ **Easy debugging** - Comprehensive logs for
troubleshooting
✅ **LLM-ready** - AI assistants can understand and
modify flows
✅ **Cloud-ready** - One env var change to switch
to GCS
✅ **Backfill complete** - 2020-2024 historical
data loaded

______________________________________________________________________

## Decision Points

### Day 3 Decision: GH Actions vs Prefect for

Sheets
**Options**:

- A: Keep GH Action, trigger Prefect after
- B: Move sheet copy to Prefect entirely

**Recommendation**: Start with A, migrate to B in
Month 2

### Week 2 Decision: Prefect Scheduling vs dbt-cron

**Options**:

- A: All scheduling in Prefect
- B: Some schedules in dbt (via cron)

**Recommendation**: All in Prefect (single source
of truth)

### Week 3 Decision: Freshness monitoring location

**Options**:

- A: Prefect flow (this plan)
- B: dbt source freshness
- C: Both (redundant)

**Recommendation**:

- Now: A (Prefect) - works with Parquet files
- After BigQuery: B (dbt) - native support

______________________________________________________________________

## Implementation Tracking

### Phase 4 Implementation Status

**P4-007: Production Hardening (Retry & Timeout Configuration)** - ✅ COMPLETE (2025-11-23)

- All external API tasks have retry configuration with appropriate delays
- All long-running tasks have timeout configuration
- Task configurations implemented:
  - Google Sheets: `create_gspread_client` (3 retries, 60s delay), `download_sheet_tabs_to_csv` (2 retries, 30s delay)
  - Sleeper: `fetch_sleeper_data` (3 retries, 60s delay, 180s timeout)
  - KTC: `fetch_ktc_data` (2 retries, 30s delay)
  - NFLverse: `fetch_nflverse_data` (2 retries, 60s delay, 300s timeout)
  - FFAnalytics: `run_projections_scraper` (900s timeout for multi-week scrapes)
- Flow docstrings updated with production hardening documentation
- All flows ready for production deployment

______________________________________________________________________

## Questions?

Before starting, clarify:

1. Do you have Prefect Cloud account created?
2. Do you have Slack webhook for notifications?
3. Are existing ingestion scripts parameterized
   (season/week args)?
4. Do you want to keep GH Action for sheets or
   migrate to Prefect?

Once these are answered, you're ready to start
