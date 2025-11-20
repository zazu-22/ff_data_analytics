# Epic Technical Specification: Prefect Foundation Setup

Date: 2025-11-19
Author: Jason
Epic ID: 0
Status: Draft

______________________________________________________________________

## Overview

This epic establishes the Prefect orchestration foundation required for all subsequent analytics development (Epics 1-5). Building Prefect infrastructure FIRST avoids 20-30 hours of retrofit work and enables analytics code to be Prefect-native from Day 1. The epic delivers a configured Prefect Cloud workspace, Discord notification infrastructure, reusable task/flow templates, and documented integration patterns from existing snapshot governance flows. Success means analytics tasks can be written as `@task`-decorated functions immediately, with monitoring, retry logic, and alerting built-in from the start.

## Objectives and Scope

**In Scope:**

- Prefect Cloud workspace creation and authentication configuration
- Discord webhook block registration (`ff-analytics-alerts`)
- Reusable `@task` and `@flow` decorator templates for analytics patterns
- Local development environment validation (flows execute on Mac)
- Documentation of integration patterns from existing snapshot governance flows
- Error handling, retry logic, and Discord notification patterns
- Directory structure setup (`flows/`, `flows/tasks/`, `data/analytics/`)

**Out of Scope:**

- Actual analytics computation logic (deferred to Epics 1-4)
- dbt model creation (deferred to Epic-specific stories)
- Production deployment infrastructure (local execution only for MVP)
- Automated scheduling (manual triggers during development)
- Cloud compute resources (Prefect Cloud SaaS only, execution remains local)

## System Architecture Alignment

This epic implements **ADR-001: Prefect-First Development** from the architecture document. The foundation aligns with the existing brownfield infrastructure by:

- **Extending existing orchestration**: Builds upon proven snapshot governance Prefect flows (error handling, Discord alerts already established)
- **Preserving dbt patterns**: Analytics outputs will integrate via external Parquet sources (ADR-002), matching existing staging model patterns
- **Cloud-first storage alignment**: Mirrors GCS integration strategy already in use for `data/raw/` provider ingestion
- **Task runner compatibility**: Integrates with existing `justfile` commands for dbt operations (`just dbt-run`, `just dbt-test`)

The Prefect infrastructure serves as the orchestration layer between Python analytics modules (`src/ff_analytics_utils/`) and dbt transformation models, enabling the complete data flow: Prefect tasks → Parquet → dbt sources → dbt marts → notebooks.

## Detailed Design

### Services and Modules

| Module/Service                | Responsibility                                                              | Inputs                                     | Outputs                                                          | Owner           |
| ----------------------------- | --------------------------------------------------------------------------- | ------------------------------------------ | ---------------------------------------------------------------- | --------------- |
| **Prefect Cloud Workspace**   | Managed orchestration platform, flow scheduling, monitoring UI              | API keys, workspace configuration          | Workspace URL, deployment endpoints                              | Platform (SaaS) |
| **Discord Webhook Block**     | Alert delivery infrastructure for pipeline failures and validation warnings | Webhook URL, message content               | Discord channel notifications                                    | Configuration   |
| **Task Templates**            | Reusable Prefect task decorators for analytics patterns                     | Template specifications                    | Python module files in `flows/tasks/`                            | Development     |
| **Flow Templates**            | Orchestration patterns for chaining analytics tasks                         | Task dependencies, execution order         | Python flow files in `flows/`                                    | Development     |
| **Integration Documentation** | Patterns extracted from snapshot governance flows                           | Existing flow code, architectural diagrams | Markdown documentation, sequence diagrams                        | Documentation   |
| **Directory Structure**       | File organization for Prefect flows and analytics outputs                   | Architecture requirements                  | Created directories: `flows/`, `flows/tasks/`, `data/analytics/` | Setup           |

### Data Models and Contracts

**Configuration Models:**

```python
# Prefect Cloud Workspace Config
workspace_config = {
    "workspace_name": "ff-analytics",
    "api_url": "https://api.prefect.cloud/api/accounts/[account_id]/workspaces/[workspace_id]",
    "api_key": "${PREFECT_API_KEY}",  # Environment variable
}

# Discord Webhook Block Schema
discord_block_schema = {
    "block_name": "ff-analytics-alerts",
    "webhook_url": "${DISCORD_WEBHOOK_URL}",  # Environment variable
    "username": "FF Analytics Bot",
    "avatar_url": None,  # Optional
}
```

**Task Template Signatures:**

```python
from prefect import task, flow
import polars as pl
from pydantic import BaseModel

# Template 1: Data Loading Task
@task(name="load-dbt-mart", retries=3, retry_delay_seconds=60)
def load_dbt_mart(mart_name: str, db_path: str) -> pl.DataFrame:
    """Load dbt mart as Polars DataFrame."""
    pass

# Template 2: Analytics Computation Task
@task(name="compute-analytics", retries=2, retry_delay_seconds=30)
def compute_analytics(input_df: pl.DataFrame, schema: type[BaseModel]) -> list[BaseModel]:
    """Compute analytics with Pydantic validation."""
    pass

# Template 3: Parquet Writer Task
@task(name="write-parquet")
def write_parquet(data: list[BaseModel], output_path: str) -> None:
    """Write validated data to Parquet."""
    pass

# Template 4: dbt Runner Task
@task(name="run-dbt-models")
def run_dbt_models(selector: str) -> None:
    """Execute dbt via justfile."""
    pass
```

**Flow Template Pattern:**

```python
@flow(name="analytics-template", on_failure=[send_discord_alert])
def analytics_template_flow():
    """Template orchestration flow."""
    # Load data
    df = load_dbt_mart(mart_name="mrt_fantasy_actuals_weekly")

    # Compute analytics
    results = compute_analytics(df, schema=PlayerValuationOutput)

    # Write Parquet
    write_parquet(results, output_path="data/analytics/player_valuation/latest.parquet")

    # Materialize dbt marts
    run_dbt_models(selector="mrt_player_valuation")
```

### APIs and Interfaces

**Prefect Cloud API:**

- **Authentication**: `prefect cloud login` (interactive) or `PREFECT_API_KEY` environment variable
- **Workspace Management**: `prefect workspace create <name>`
- **Block Registration**: `prefect block register --file <path>` or Python API via `Block.save()`
- **Flow Deployment**: `prefect deploy` or `flow.serve()` for local execution
- **Flow Triggers**: Manual via UI, programmatic via `prefect deployment run`, or scheduled via cron

**Discord Webhook API:**

```python
# Via Prefect Block (recommended)
from prefect.blocks.discord import DiscordWebhook

discord_webhook = DiscordWebhook.load("ff-analytics-alerts")
discord_webhook.notify("Pipeline completed successfully")

# Direct API (alternative)
import requests
requests.post(
    webhook_url,
    json={"content": "⚠️ Pipeline failure detected"}
)
```

**Justfile Integration (dbt Runner):**

```python
import subprocess

def run_dbt_models(selector: str) -> None:
    """Execute dbt via justfile."""
    result = subprocess.run(
        ["just", "dbt-run", "--select", selector],
        cwd="/Users/jason/code/ff_data_analytics",
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"dbt run failed: {result.stderr}")
```

**Error Response Codes:**

| Error Type                  | Prefect State | Discord Alert | Action                    |
| --------------------------- | ------------- | ------------- | ------------------------- |
| Task failure (no retries)   | `Failed`      | Yes (🚨)      | Investigate immediately   |
| Task failure (with retries) | `Retrying`    | No            | Automatic retry           |
| Flow failure                | `Failed`      | Yes (⚠️)      | Check Prefect UI logs     |
| Validation error (Pydantic) | `Failed`      | Yes (🔴)      | Schema mismatch, fix code |

### Workflows and Sequencing

**Epic 0 Execution Sequence:**

```
Story 1: Prefect Cloud Workspace Setup
  ├─> Install Prefect: uv add prefect
  ├─> Login: prefect cloud login
  ├─> Create workspace: prefect workspace create ff-analytics
  ├─> Verify: Deploy simple test flow
  └─> Output: Workspace URL, API key in .env

Story 2: Discord Notification Block
  ├─> Get webhook URL from Discord channel settings
  ├─> Create block Python script: blocks/discord_webhook.py
  ├─> Register block: prefect block register --file blocks/discord_webhook.py
  ├─> Test: discord_webhook.notify("Test alert")
  └─> Output: Block saved in Prefect Cloud

Story 3: Analytics Flow Templates
  ├─> Create flows/tasks/ directory structure
  ├─> Implement template_data_loader.py
  ├─> Implement template_analytics_compute.py
  ├─> Implement template_parquet_writer.py
  ├─> Implement template_dbt_runner.py
  ├─> Create flows/analytics_template_flow.py
  ├─> Test: python flows/analytics_template_flow.py
  └─> Output: Working templates validated with hello world examples

Story 4: Integration Review
  ├─> Review existing snapshot governance flows
  ├─> Document error handling patterns
  ├─> Document retry logic configurations
  ├─> Document Discord alert usage
  ├─> Create sequence diagram: Snapshot → dbt → Analytics → Marts
  └─> Output: Integration patterns documentation
```

**Data Flow (Post-Epic 0):**

```
Provider APIs (nflverse, ffanalytics, KTC, Sheets, Sleeper)
  ↓
Python Ingestion (src/ingest/) [Existing - No Change]
  ↓
Raw Parquet (data/raw/) [Existing - No Change]
  ↓
dbt Staging Models (stg_*) [Existing - No Change]
  ↓
dbt Core Models (fct_*, dim_*) [Existing - No Change]
  ↓
dbt Marts (mrt_*) [Existing - Consumed by Analytics]
  ↓
Prefect Analytics Tasks (@task-decorated) [NEW - Epic 0 Foundation]
  ├─> Load mart data (Polars)
  ├─> Compute analytics (Pydantic validation)
  └─> Write Parquet (data/analytics/)
  ↓
dbt Analytics Sources (source('analytics', ...)) [NEW - Epic 1-4]
  ↓
dbt Analytics Marts (mrt_player_valuation, mrt_multi_year_projections, ...) [NEW - Epic 1-4]
  ↓
Jupyter Notebooks [Existing - No Change]
```

## Non-Functional Requirements

### Performance

**Targets (Epic 0 Specific):**

- **Workspace setup**: \<5 minutes total (interactive login + workspace creation)
- **Discord block registration**: \<1 minute
- **Template validation**: Each hello world example executes in \<30 seconds
- **Prefect UI responsiveness**: Flow runs visible in UI within 5 seconds of execution

**No Performance Concerns:**

Epic 0 is infrastructure setup with minimal compute requirements. Templates validate with trivial "hello world" examples (e.g., load 10 rows, compute sum, write small Parquet). Actual performance targets apply to Epic 1-4 analytics computations, not foundation setup.

### Security

**Authentication:**

- Prefect API key stored in environment variable `PREFECT_API_KEY` (never committed to git)
- Discord webhook URL stored in `DISCORD_WEBHOOK_URL` (never committed to git)
- `.env` file added to `.gitignore` to prevent accidental commit of secrets

**Authorization:**

- Prefect Cloud workspace access controlled via account permissions (Jason as owner)
- Discord webhook limited to single channel (`#analytics-alerts`)

**Data Handling:**

- No PII or sensitive data involved in Epic 0 (infrastructure only)
- Template examples use synthetic test data (no real player data)
- Prefect logs may contain task names and file paths (acceptable, no secrets)

**Threat Mitigation:**

- **Webhook URL Exposure**: If Discord webhook URL leaked, attacker can send spam alerts (low severity). Mitigation: Regenerate webhook URL, update block.
- **API Key Exposure**: If Prefect API key leaked, attacker can trigger flows or read logs (medium severity). Mitigation: Rotate API key immediately, review Prefect audit logs.

**Security Testing:**

- Verify `.env` file excluded from git: `git status` should not show `.env`
- Verify secrets not in Prefect UI: Flow run logs should not display API keys or webhook URLs
- Verify environment variable loading: Template tasks fail gracefully if secrets missing

### Reliability/Availability

**Prefect Cloud SLA:**

- Prefect Cloud (SaaS) provides 99.9% uptime SLA
- Managed service eliminates need for self-hosted orchestration infrastructure
- Automatic failover and redundancy handled by Prefect Cloud platform

**Local Execution Reliability:**

- Flows run locally on Mac (no remote compute dependencies during MVP)
- If Prefect Cloud UI unavailable, flows still execute (API degradation graceful)
- Flow state persisted to Prefect Cloud asynchronously (local execution not blocked)

**Error Handling Patterns (From Templates):**

```python
@task(retries=3, retry_delay_seconds=60, retry_jitter_factor=0.5)
def resilient_task():
    """Task with automatic retry on transient failures."""
    pass

@flow(on_failure=[send_discord_alert])
def monitored_flow():
    """Flow with automatic failure alerting."""
    pass
```

**Degradation Behavior:**

- **Prefect Cloud API unavailable**: Flows fail to start (acceptable - manual retry when service restored)
- **Discord webhook unavailable**: Alerts fail silently (logged in Prefect UI, not critical)
- **dbt command fails**: Task raises exception, triggers Discord alert, flow marked as Failed

**Recovery Procedures:**

- Flow failures: Review Prefect UI logs → Fix code/data → Retry flow manually
- Webhook delivery failures: Check Discord channel permissions, verify webhook URL in block
- API authentication failures: Verify `PREFECT_API_KEY` environment variable set correctly

### Observability

**Logging Strategy:**

- **Python logging module**: All tasks use `logger = logging.getLogger(__name__)`
  - `INFO`: Task start/completion, row counts, file paths
  - `DEBUG`: Intermediate calculations, configuration values
  - `ERROR`: Exceptions with full stack traces
- **Prefect structured logs**: Automatically captured in Prefect Cloud UI with timestamps, task context

**Metrics Tracked (Prefect UI):**

- Task execution duration (wall-clock time per task)
- Task state transitions (Pending → Running → Success/Failed)
- Flow run history (success rate, failure patterns)
- Retry attempts (count, delay between retries)

**Alerting:**

- **Discord notifications** for critical events:
  - Flow failures (unhandled exceptions)
  - Pydantic validation errors (schema mismatches)
  - dbt test failures (data quality issues)
- **Prefect UI alerts**: Built-in notification for flow state changes (optional, not configured in Epic 0)

**Monitoring Dashboards:**

- **Prefect Cloud UI**: Primary monitoring interface
  - Flow run timeline (visualize task dependencies, execution order)
  - Task run details (logs, duration, state history)
  - Artifact viewer (intermediate DataFrames, validation results)
- **Discord Channel**: `#analytics-alerts` for team visibility

**Debugging Workflow:**

1. Check Discord alerts for failure notifications
2. Open Prefect UI → Flow Runs → Select failed run
3. Review task logs (identify failed task, exception message)
4. Check task inputs/outputs via artifacts (if available)
5. Reproduce locally: `python flows/analytics_pipeline.py`
6. Fix code, commit, retry flow

## Dependencies and Integrations

**Python Dependencies (New):**

```toml
# pyproject.toml additions
[project]
dependencies = [
    "prefect>=3.6.2",  # Orchestration framework (verified 2025-11-18)
]
```

**External Services:**

| Service           | Version       | Purpose                        | Integration Point                        |
| ----------------- | ------------- | ------------------------------ | ---------------------------------------- |
| **Prefect Cloud** | SaaS (latest) | Managed orchestration platform | API authentication via `PREFECT_API_KEY` |
| **Discord**       | Webhook API   | Alert notifications            | Webhook URL via `DISCORD_WEBHOOK_URL`    |

**Existing Project Dependencies (No Changes):**

- Python 3.13.6 (existing .python-version)
- uv 0.8.8 (package manager)
- dbt-core 1.10.13 + dbt-duckdb 1.10.0 (transformation engine)
- DuckDB >=1.4.0 (OLAP database)
- just (task runner, used by dbt runner template)

**Integration Points:**

1. **Prefect → dbt Integration**:

   - Prefect task wraps `subprocess.run(["just", "dbt-run", "--select", selector])`
   - Error codes propagated: dbt exit code != 0 → Prefect task fails
   - Logs captured: dbt stdout/stderr visible in Prefect UI

2. **Prefect → Discord Integration**:

   - DiscordWebhook block registered in Prefect Cloud
   - Flow-level hook: `@flow(on_failure=[send_discord_alert])`
   - Manual alerts: `discord_webhook.notify(message)`

3. **Prefect → Existing Snapshot Governance Flows**:

   - Patterns extracted (not direct integration)
   - Error handling: `@task(retries=N)` pattern reused
   - Discord alert format: Emoji prefix (🚨/⚠️/ℹ️) + message content

**Directory Structure Created:**

```
ff_data_analytics/
├── flows/                    # NEW
│   ├── __init__.py
│   ├── analytics_template_flow.py
│   └── tasks/                # NEW
│       ├── __init__.py
│       ├── template_data_loader.py
│       ├── template_analytics_compute.py
│       ├── template_parquet_writer.py
│       └── template_dbt_runner.py
├── blocks/                   # NEW
│   └── discord_webhook.py
├── data/
│   └── analytics/            # NEW (created, empty until Epic 1)
└── .prefect/                 # NEW (gitignored, local config)
```

## Acceptance Criteria (Authoritative)

**AC-1: Prefect Cloud Workspace Operational**

- Workspace `ff-analytics` created and accessible via Prefect Cloud UI
- API key stored in `.env` file as `PREFECT_API_KEY`
- Simple test flow deploys and executes successfully from local Mac environment
- Flow run visible in Prefect Cloud UI with state transitions logged

**AC-2: Discord Notification Infrastructure Functional**

- Discord webhook block `ff-analytics-alerts` registered in Prefect Cloud
- Test alert successfully received in Discord channel `#analytics-alerts`
- Alert message formatted with emoji prefix and readable content
- Block loadable via `DiscordWebhook.load("ff-analytics-alerts")` in Python

**AC-3: Analytics Flow Templates Validated**

- Four template task modules created in `flows/tasks/`:
  - `template_data_loader.py` (loads dbt mart as Polars DataFrame)
  - `template_analytics_compute.py` (validates with Pydantic schema)
  - `template_parquet_writer.py` (writes to `data/analytics/`)
  - `template_dbt_runner.py` (executes `just dbt-run --select <model>`)
- Template flow `flows/analytics_template_flow.py` chains all four tasks
- All templates execute successfully with "hello world" test data
- Prefect UI shows task dependencies and execution timeline

**AC-4: Local Development Environment Proven**

- Flows execute on Mac without errors
- Prefect Cloud connection verified (API reachable, flow state synced)
- Environment variables loaded correctly (`.env` file read by workflows)
- Directory structure created: `flows/`, `flows/tasks/`, `blocks/`, `data/analytics/`

**AC-5: Integration Patterns Documented**

- Snapshot governance flows reviewed for reusable patterns
- Documentation covers:
  - Error handling: `@task(retries=N, retry_delay_seconds=M)` pattern
  - Retry logic: Exponential backoff via `retry_jitter_factor`
  - Discord notifications: `@flow(on_failure=[send_discord_alert])` hook
  - Artifact tracking: `create_table_artifact()` usage examples
- Sequence diagram created showing: Snapshot ingest → dbt staging → analytics → dbt analytics marts

**AC-6: Prerequisites Established for Epics 1-4**

- Python package `prefect>=3.6.2` installed via `uv add prefect`
- Templates ready for analytics logic insertion (placeholders replaced in Epics 1-4)
- Monitoring infrastructure operational (Discord alerts working)
- Development workflow validated (write task → run flow → check Prefect UI → verify Discord alert)

## Traceability Mapping

| AC       | PRD Section                                                                                     | Spec Section                                                                          | Component/API                                          | Test Idea                                                                             |
| -------- | ----------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- | ------------------------------------------------------ | ------------------------------------------------------------------------------------- |
| **AC-1** | Epic 0 Success Criteria: "Prefect Cloud workspace configured and tested"                        | System Architecture Alignment, APIs and Interfaces                                    | Prefect Cloud API (`prefect workspace create`)         | Integration test: Deploy simple flow, verify in Prefect UI                            |
| **AC-2** | Epic 0 Success Criteria: "Discord webhook block created for analytics alerts"                   | Services and Modules (Discord Webhook Block), APIs and Interfaces                     | DiscordWebhook block, Discord API                      | Integration test: `discord_webhook.notify("Test")`, verify message in Discord channel |
| **AC-3** | Epic 0 Success Criteria: "Task/flow decorator templates validated with working examples"        | Data Models and Contracts (Task Template Signatures), Workflows and Sequencing        | `flows/tasks/*.py`, `flows/analytics_template_flow.py` | Unit tests: Each template executes hello world successfully, returns expected types   |
| **AC-4** | Epic 0 Success Criteria: "Local development environment proven (flows run successfully on Mac)" | Reliability/Availability (Local Execution Reliability)                                | Local Prefect execution, environment variable loading  | Integration test: Flow runs end-to-end, Prefect UI shows completed state              |
| **AC-5** | Epic 0 Success Criteria: "Integration patterns documented from snapshot governance flows"       | Workflows and Sequencing (Data Flow diagram), Observability (Error handling patterns) | Documentation files, sequence diagram                  | Manual review: Documentation covers error handling, retry logic, Discord alerts       |
| **AC-6** | Architecture ADR-001: "Prefect-First Development"                                               | Dependencies and Integrations (Python Dependencies), System Architecture Alignment    | `prefect>=3.6.2` package, template modules             | Verification: \`uv pip list                                                           |

## Risks, Assumptions, Open Questions

**Risks:**

| Risk                                                               | Severity | Mitigation                                                                                                 |
| ------------------------------------------------------------------ | -------- | ---------------------------------------------------------------------------------------------------------- |
| **Prefect Cloud service outage during development**                | Low      | Flows execute locally (degraded observability acceptable), retry when service restored                     |
| **Discord webhook URL leaked in public repo**                      | Low      | Webhook URL in `.env` (gitignored), code review checks prevent accidental commit                           |
| **Template patterns insufficient for Epic 1-4 complexity**         | Medium   | Templates are starting points (not rigid contracts), refine as analytics requirements emerge               |
| **Learning curve for Prefect decorators slows Epic 1 development** | Medium   | Mitigated by intermediate user skill level, templates provide working examples, Prefect docs comprehensive |

**Assumptions:**

| Assumption                                                 | Validation                                                                                 | Fallback                                                      |
| ---------------------------------------------------------- | ------------------------------------------------------------------------------------------ | ------------------------------------------------------------- |
| **Prefect Cloud free tier sufficient for MVP**             | Verify workspace limits (10 concurrent flows, 1000 flow runs/month) against Epic 1-5 usage | Upgrade to paid tier if needed (~$20/month for standard plan) |
| **Existing Discord channel `#analytics-alerts` available** | Confirm channel exists, webhook permissions granted                                        | Create new channel if needed (trivial, \<5 min setup)         |
| **Mac local execution acceptable for MVP**                 | Architecture decision: local dev validated (no cloud compute required)                     | Migrate to cloud compute in Phase 2 if needed                 |
| **Snapshot governance flows provide sufficient patterns**  | Review existing flows for error handling, retry logic, Discord alerts                      | Supplement with Prefect docs if patterns incomplete           |

**Open Questions:**

| Question                                                        | Decision Owner  | Resolution Target              | Impact if Unresolved                                                                  |
| --------------------------------------------------------------- | --------------- | ------------------------------ | ------------------------------------------------------------------------------------- |
| **Should templates include example Pydantic schemas?**          | Developer       | Story 3 implementation         | Minor - schemas simple to add later, but example would clarify contract-first pattern |
| **Prefect artifact usage for intermediate DataFrames?**         | Developer       | Story 3 implementation         | Minor - artifacts helpful for debugging but not required for templates                |
| **Separate Discord channels for alerts vs info notifications?** | User preference | Story 2 implementation         | Minor - single channel acceptable, separate channels reduce noise                     |
| **Pre-commit hooks for Prefect flow validation?**               | Developer       | Post-Epic 0 (Epic 5 extension) | Low - manual testing sufficient for MVP, automation deferred                          |

## Test Strategy Summary

**Test Levels:**

| Level           | Scope                                                                                  | Tools                                   | Coverage Target            |
| --------------- | -------------------------------------------------------------------------------------- | --------------------------------------- | -------------------------- |
| **Unit**        | Individual template tasks (data loader, analytics compute, Parquet writer, dbt runner) | pytest                                  | 80%+ for template modules  |
| **Integration** | End-to-end flow execution (template flow chains tasks correctly)                       | pytest + manual Prefect UI verification | Complete flow success path |
| **Manual**      | Workspace setup, Discord alerts, Prefect UI validation                                 | Interactive testing                     | All acceptance criteria    |

**Test Cases:**

**Unit Tests (pytest):**

```python
# tests/unit/test_template_data_loader.py
def test_load_dbt_mart_returns_polars_dataframe():
    """Data loader returns Polars DataFrame with expected schema."""
    df = load_dbt_mart(mart_name="test_mart", db_path="test.duckdb")
    assert isinstance(df, pl.DataFrame)
    assert len(df) > 0

# tests/unit/test_template_parquet_writer.py
def test_write_parquet_creates_file():
    """Parquet writer creates file at expected path."""
    test_data = [TestSchema(player_id="1", value=100)]
    write_parquet(test_data, output_path="/tmp/test.parquet")
    assert Path("/tmp/test.parquet").exists()

# tests/unit/test_template_dbt_runner.py
def test_dbt_runner_executes_justfile_command(mocker):
    """dbt runner calls justfile with correct arguments."""
    mock_run = mocker.patch("subprocess.run")
    run_dbt_models(selector="mrt_player_valuation")
    mock_run.assert_called_with(
        ["just", "dbt-run", "--select", "mrt_player_valuation"],
        cwd=ANY,
        capture_output=True,
        text=True
    )
```

**Integration Tests:**

```python
# tests/integration/test_analytics_template_flow.py
def test_template_flow_executes_successfully():
    """Template flow runs all tasks without errors."""
    state = analytics_template_flow()
    assert state.is_successful()

    # Verify Parquet output created
    assert Path("data/analytics/test_output/latest.parquet").exists()
```

**Manual Test Checklist:**

- [ ] **AC-1**: Workspace visible in Prefect Cloud UI
- [ ] **AC-1**: Test flow run shows in UI with success state
- [ ] **AC-2**: Discord alert received in `#analytics-alerts` channel
- [ ] **AC-2**: Alert formatted with emoji and readable content
- [ ] **AC-3**: All four template tasks execute successfully
- [ ] **AC-3**: Template flow shows task dependencies in Prefect UI timeline
- [ ] **AC-4**: `.env` file not committed to git (check `git status`)
- [ ] **AC-5**: Integration documentation complete (error handling, retry logic, Discord alerts)
- [ ] **AC-6**: `uv pip list` shows `prefect>=3.6.2`

**Edge Case Coverage:**

- **Missing environment variables**: Template tasks fail gracefully with clear error message
- **dbt command failure**: dbt runner raises exception, Prefect task marked as Failed, Discord alert sent
- **Pydantic validation error**: Analytics compute task logs validation error, fails task, triggers alert
- **Prefect Cloud API unavailable**: Flow fails to start, logged locally, retry manually when service restored

**Test Execution Order:**

1. Unit tests (fast, run frequently during development)
2. Integration tests (slower, run before story completion)
3. Manual tests (acceptance criteria validation, run once per story)

**Coverage Reporting:**

```bash
# Unit test coverage
pytest tests/unit/ --cov=flows --cov-report=html

# Integration test validation
pytest tests/integration/ -v
```

**Acceptance:** All unit tests pass, integration test succeeds, manual checklist complete for all 6 acceptance criteria.
