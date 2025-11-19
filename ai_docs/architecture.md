# Architecture: Analytics Infrastructure Platform

**Project:** Fantasy Football Analytics Platform - Analytical Infrastructure MVP
**Date:** 2025-11-18
**Author:** Winston (Architect Agent)
**Status:** In Progress
**For:** Jason

______________________________________________________________________

## 1. Project Context & Understanding

### 1.1 Project Overview

**Type:** Data Analytics Infrastructure (Python + dbt + Prefect Orchestration)

**Mission:** Build analytical infrastructure enabling systematic competitive advantage in dynasty fantasy football through multi-dimensional player valuation, machine learning projections, and portfolio optimization.

**Scope:** 5 Epics (Epic 0-5) delivering core analytical engines - NOT user-facing decision support tools (those come in Phase 2).

### 1.2 Epic Breakdown

| Epic       | Name                            | Purpose                                                               | Key Outputs                                                            |
| ---------- | ------------------------------- | --------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| **Epic 0** | Prefect Foundation Setup        | Establish orchestration infrastructure FIRST                          | Prefect Cloud workspace, Discord alerts, task templates, flow patterns |
| **Epic 1** | VoR/WAR Valuation Engine        | Calculate Value over Replacement and contract efficiency              | `analytics.player_valuation` → `mrt_player_valuation`                  |
| **Epic 2** | Multi-Year Projection System    | Generate 2025-2029 projections with age curves and uncertainty        | `analytics.multi_year_projections` → `mrt_multi_year_projections`      |
| **Epic 3** | Cap Space Projection & Modeling | Multi-year cap scenarios, contract optimization, dead cap calculation | `analytics.cap_scenarios` → `mrt_cap_scenarios`                        |
| **Epic 4** | Dynasty Value Composite Score   | Integrate 6 dimensions into unified player valuation                  | `analytics.dynasty_value_composite` → `mrt_dynasty_value_composite`    |
| **Epic 5** | Integration & Validation        | End-to-end pipeline, backtesting, notebook consumption                | Prefect flows, backtesting scheduler, validation reports               |

### 1.3 Critical Non-Functional Requirements

**Performance:**

- End-to-end pipeline runtime: \<30 minutes
- VoR calculation refresh: \<10 minutes
- Incremental updates: \<2 minutes

**Accuracy (Backtested):**

- Projection MAE: \<20% on 1-year ahead (2020→2021, 2021→2022, 2022→2023)
- Cap modeling error: \<5% vs manual calculations
- VoR baseline consistency: Sum to expected league-wide totals

**Orchestration:**

- Prefect Cloud (SaaS) for orchestration
- Flows run locally during development (Mac)
- GCS storage for production Parquet
- Discord notifications on failures/regressions

**Testing:**

- 80%+ coverage for valuation engines
- 100% coverage for cap rule validation (deterministic, must be bug-free)

### 1.4 Novel Features & Unique Challenges

**Novel Features:**

1. **Multi-dimensional player valuation** - 6-factor dynasty value score integrating VoR, economics, age, scarcity, variance, and market signals
2. **Continuous backtesting flow** - Separate Prefect scheduler running weekly validation with automated Discord alerts on regression
3. **Contract economics integration** - $/WAR efficiency metrics, dead cap modeling (50%/50%/25%/25%/25% schedule), pro-rating constraints (150% geometric limits)
4. **Market inefficiency detection** - Internal valuations vs KTC consensus (target: ≥10 divergences >15% delta per week)

**Unique Challenges:**

1. **Small sample NFL data** (17 games/season) → Overfitting risk → TimeSeriesSplit validation mandatory, no shuffle=True
2. **Multiple data sources** - FFAnalytics projections, nflverse stats, KTC market signals, commissioner contracts
3. **Brownfield integration** - Must align with 48 existing dbt models (13 staging, 23 core, 12 marts)
4. **Contract-first handoffs** - Pydantic schemas enforce type-safe boundaries between Prefect tasks and dbt models

### 1.5 Integration with Existing Infrastructure

#### Existing dbt Models (Consumption Points)

**Analytics Will Consume:**

- `mrt_contract_snapshot_current` - Cap modeling input (active contracts, cap obligations)
- `mrt_fantasy_actuals_weekly` - VoR baseline calculation (replacement level determination)
- `mrt_real_world_actuals_weekly` - Aging curve derivation (position-specific trajectories)
- `fct_player_projections` - Multi-year projection input (FFAnalytics consensus)
- `dim_player` - Player identity resolution (canonical player_id)
- `dim_scoring_rule` - Fantasy scoring rules (Half-PPR + IDP)

**Analytics Will Produce (New Models):**

- `mrt_player_valuation` - VoR/WAR scores, contract efficiency metrics
- `mrt_multi_year_projections` - 2025-2029 projections with confidence intervals
- `mrt_cap_scenarios` - Multi-year cap space scenarios by franchise
- `mrt_dynasty_value_composite` - Unified 6-factor dynasty value scores

#### Existing Data Patterns (Will Extend)

**External Parquet Pattern (Staging Models):**

```sql
{{ config(
    materialized='table',
    external=true,
    partition_by=['season', 'week']
) }}
```

- 4+ staging models use this pattern
- Read from `data/raw/<provider>/<dataset>/dt=YYYY-MM-DD/`
- **Extension:** Analytics will write to `data/analytics/<model>/latest.parquet` (NEW directory)

**2×2 Analytics Model (ADR-007):**

```
                 Real-World Stats              Fantasy Points
Actuals          fct_player_stats    →        mrt_fantasy_actuals_weekly
Projections      fct_player_projections →     mrt_fantasy_projections
```

- Separate fact tables (actuals have game_id, projections have horizon)
- Real-world marts pivot from long to wide format
- Fantasy marts apply `dim_scoring_rule` via cross join

**dbt Conventions (Must Follow):**

- Grain testing: `unique_key` config + `unique_combination_of_columns` tests
- CTE pattern: `SELECT *` in CTEs, explicit columns in final SELECT (dbt-opiner O007 compliance)
- Materialization: `table` (in DuckDB), `external=true` for large datasets
- Position-specific logic: DuckDB `arbitrary()` function for grouped aggregates

#### Data Directory Structure

**Existing:**

```
data/
├── raw/          # Provider-specific raw Parquet (commissioner, ffanalytics, ktc, nflverse, sleeper)
├── stage/        # Intermediate staging
├── mart/         # Analytics marts (external Parquet outputs from dbt)
└── ops/          # Operational metadata
```

**New (Analytics Infrastructure):**

```
data/
└── analytics/    # Python analytics outputs (NEW)
    ├── player_valuation/
    │   └── latest.parquet
    ├── multi_year_projections/
    │   └── latest.parquet
    ├── cap_scenarios/
    │   └── latest.parquet
    └── dynasty_value_composite/
        └── latest.parquet
```

#### Integration Flow (Analytics → dbt)

```
Python Prefect Tasks (@task-decorated)
  ↓ writes Parquet
data/analytics/<model>/latest.parquet
  ↓ dbt reads as external table
dbt Sources (analytics schema) ← NEW SCHEMA
  source('analytics', 'player_valuation')
  source('analytics', 'multi_year_projections')
  source('analytics', 'cap_scenarios')
  source('analytics', 'dynasty_value_composite')
  ↓ dbt materializes
dbt Analytics Marts (mrt_*)
  mrt_player_valuation
  mrt_multi_year_projections
  mrt_cap_scenarios
  mrt_dynasty_value_composite
  ↓ reads
Jupyter Notebooks (existing consumption pattern)
```

**Key Integration Points:**

1. **Python → Parquet**: Prefect tasks write validated Polars DataFrames (Pydantic schema enforcement)
2. **Parquet → dbt sources**: External tables in `analytics` schema (mirrors staging pattern)
3. **dbt sources → marts**: Thin SQL layer for documentation, testing, and dbt lineage
4. **Marts → notebooks**: Analysts query marts (existing consumption pattern, no change)

### 1.6 Architectural Foundations (From Winston's Guidance)

#### Foundation 1: Prefect-First Development

**Decision:** Build Prefect orchestration infrastructure FIRST (Epic 0: Week 1, Days 1-2) before analytics code.

**Rationale:**

- Avoid 20-30 hours of retrofit work if analytics built standalone then wrapped in Prefect later
- Enable monitoring/alerting from Day 1 (no manual "remember to run X")
- Backtesting automated immediately as scheduled flow (continuous validation vs one-time)

**Implementation:**

- All analytics modules decorated as `@task` from Day 1
- Epic 0 deliverables: Prefect Cloud workspace, Discord webhook block, task/flow templates
- Snapshot governance flows provide proven patterns (error handling, retry logic, Discord notifications)

#### Foundation 2: External Parquet Data Flow

**Decision:** Python writes Parquet directly → dbt reads as external tables (NOT Python → DuckDB tables → dbt)

**Rationale:**

- Matches existing dbt external Parquet pattern (staging models already use this)
- No database write/read round-trip overhead
- Columnar efficiency (Parquet optimized for analytics)
- Simpler debugging (inspect Parquet files directly)

**Implementation:**

```python
@task
def calculate_vor(...) -> pl.DataFrame:
    # Validate against Pydantic schema
    results = [PlayerValuationOutput(...) for player in players]
    df = pl.DataFrame([r.model_dump() for r in results])

    # Write to Parquet
    df.write_parquet("data/analytics/player_valuation/latest.parquet")
    return df
```

```yaml
# dbt sources.yml
sources:
  - name: analytics
    schema: analytics
    tables:
      - name: player_valuation
        external:
          location: 'data/analytics/player_valuation/latest.parquet'
```

#### Foundation 3: Contract-First Design (Pydantic + Polars)

**Decision:** Define Pydantic schemas for ALL analytics task outputs, validate at task boundary.

**Rationale:**

- Schema drift caught at runtime (fails fast vs silent corruption)
- Type-safe handoffs between tasks (player_id always str, vor always float)
- dbt alignment via explicit schemas (Parquet columns match dbt source definitions)

**Implementation:**

```python
from pydantic import BaseModel
from datetime import date

class PlayerValuationOutput(BaseModel):
    player_id: str
    snapshot_date: date
    vor: float
    war: float
    replacement_level: float
    positional_scarcity_adjustment: float
    contract_efficiency_dollar_per_war: float | None

    class Config:
        frozen = True  # Immutable

@task
def calculate_vor(...) -> pl.DataFrame:
    # Business logic
    valuations = [...]

    # Schema validation
    validated = [PlayerValuationOutput(**v) for v in valuations]

    # Convert to Polars DataFrame
    return pl.DataFrame([v.model_dump() for v in validated])
```

#### Foundation 4: Continuous Backtesting Flow

**Decision:** Separate scheduled Prefect flow for backtesting (NOT one-time validation script).

**Rationale:**

- Automated monitoring vs manual "remember to validate"
- Catch model drift early (weekly validation with Discord alerts)
- Production deployment pattern (scheduled flow vs ad-hoc script)

**Implementation:**

```python
@flow(name="Weekly Backtesting Validation")
def backtesting_flow():
    # TimeSeriesSplit validation (2020→2021, 2021→2022, 2022→2023)
    results = run_timeseries_cv(...)
    mae = calculate_mae(results)

    if mae > THRESHOLD:
        send_discord_alert(f"⚠️ Model regression! MAE: {mae:.2%} (threshold: {THRESHOLD:.2%})")

    return results

# Scheduled via Prefect deployment
backtesting_flow.serve(
    name="weekly-backtesting",
    cron="0 9 * * 1"  # Monday 9am
)
```

______________________________________________________________________

## 2. Technology Stack & Decision Summary

### 2.1 Starter Template Assessment

**Decision:** No starter template required - Brownfield integration project.

**Rationale:** This is not a greenfield project requiring initialization. The Analytics Infrastructure extends an existing Python/dbt project with established patterns. The "foundation" is the existing codebase structure (`src/`, `dbt/`, `data/`, `tests/`), which already defines:

- Package management (uv 0.8.8)
- Python version (3.13.6 via .python-version)
- dbt setup (dbt-core 1.10.13 + dbt-duckdb 1.10.0)
- Task runner (justfile patterns)
- Testing framework (pytest)
- Code quality (ruff, pre-commit hooks)

**First Implementation Story:** Epic 0 Story 1 - Prefect Cloud workspace setup (not project initialization)

### 2.2 Core Technology Stack

| Category            | Technology                 | Version                      | Rationale                                           | Provided By                |
| ------------------- | -------------------------- | ---------------------------- | --------------------------------------------------- | -------------------------- |
| **Language**        | Python                     | 3.13.6                       | Existing project standard, compatible with all deps | Existing (.python-version) |
| **Package Manager** | uv                         | 0.8.8                        | Existing project standard, fast resolver            | Existing                   |
| **Database**        | DuckDB                     | >=1.4.0                      | Existing OLAP database, columnar analytics          | Existing                   |
| **Transform**       | dbt-core                   | 1.10.13                      | SQL transformation engine (Python-based)            | Existing                   |
| **dbt Adapter**     | dbt-duckdb                 | 1.10.0                       | dbt adapter for DuckDB integration                  | Existing                   |
| **Data Processing** | Polars                     | 1.35.2 (verified 2025-11-18) | High-performance DataFrames, columnar optimization  | **NEW**                    |
| **Data Processing** | PyArrow                    | Latest                       | Parquet I/O, columnar format                        | Existing                   |
| **Orchestration**   | Prefect                    | 3.6.2 (verified 2025-11-18)  | Cloud-native orchestration, Python-native flows     | **NEW** (Epic 0)           |
| **Validation**      | Pydantic                   | 2.12.4 (verified 2025-11-18) | Contract-first design, schema validation            | **NEW**                    |
| **ML/Stats**        | scikit-learn               | 1.7.2 (verified 2025-11-18)  | TimeSeriesSplit CV, regression models               | **NEW**                    |
| **ML/Stats**        | statsmodels                | Latest                       | Statistical models, time series                     | **NEW**                    |
| **Testing**         | pytest                     | Latest                       | Existing test framework                             | Existing                   |
| **Linting**         | ruff                       | Latest                       | Existing Python linter                              | Existing                   |
| **Task Runner**     | just                       | Latest                       | Existing command runner (replaces Make)             | Existing                   |
| **Notebooks**       | Jupyter                    | Latest                       | Existing analysis environment                       | Existing                   |
| **Cloud Storage**   | GCS (google-cloud-storage) | >=3.4.0                      | Existing cloud storage                              | Existing                   |
| **Alerts**          | Discord Webhooks           | N/A                          | Existing notification system                        | Existing (GitHub Actions)  |

**Version Verification Date:** 2025-11-18 (all "verified" versions checked against latest stable releases)

### 2.3 Architectural Decisions Summary

| Decision                   | Choice                                         | Affects               | Rationale                                                    |
| -------------------------- | ---------------------------------------------- | --------------------- | ------------------------------------------------------------ |
| **Orchestration Strategy** | Prefect-First (Epic 0 before analytics)        | All epics             | Avoid 20-30 hours retrofit work, monitoring from Day 1       |
| **Data Flow Pattern**      | Python → Parquet → dbt sources → marts         | All analytics outputs | Matches staging pattern, no DB round-trip                    |
| **Schema Validation**      | Pydantic schemas at task boundaries            | All Prefect tasks     | Type-safe handoffs, fail fast on schema drift                |
| **Backtesting Strategy**   | Separate scheduled Prefect flow                | Epic 2, Epic 5        | Continuous validation vs one-time, automated monitoring      |
| **Testing Framework**      | pytest (existing) + dbt tests                  | All epics             | Leverage existing patterns                                   |
| **ML Library**             | scikit-learn (simple models + TimeSeriesSplit) | Epic 2 projections    | Avoid overfitting, well-engineered features > complex models |
| **DataFrame Library**      | Polars (primary) + PyArrow                     | All analytics         | High performance, columnar efficiency                        |
| **Deployment Target**      | Prefect Cloud (SaaS) + local execution         | All flows             | Managed orchestration, local dev flexibility                 |
| **Storage**                | GCS (production) + local Parquet (dev)         | All outputs           | Existing GCS setup, mirror structure locally                 |
| **Notification**           | Discord webhooks (existing pattern)            | Prefect flows         | Reuse GitHub Actions Discord integration                     |

______________________________________________________________________

## 3. Project Structure & Epic Mapping

### 3.1 Source Tree

```
ff_data_analytics/
├── src/
│   ├── ff_analytics_utils/           # NEW: Analytics library modules
│   │   ├── __init__.py
│   │   ├── valuation/                # Epic 1: VoR/WAR Engine
│   │   │   ├── __init__.py
│   │   │   ├── vor.py                # VoR calculation
│   │   │   ├── war.py                # WAR estimation
│   │   │   ├── baselines.py          # Replacement level thresholds
│   │   │   └── positional_value.py   # Scarcity adjustments
│   │   ├── projections/              # Epic 2: Multi-Year Projections
│   │   │   ├── __init__.py
│   │   │   ├── multi_year.py         # 2025-2029 projection engine
│   │   │   ├── aging_curves.py       # Position-specific trajectories
│   │   │   └── opportunity.py        # Usage trend adjustments
│   │   ├── cap_modeling/             # Epic 3: Cap Space Projection
│   │   │   ├── __init__.py
│   │   │   ├── scenarios.py          # Multi-year cap projections
│   │   │   ├── contracts.py          # Pro-rating, structure validation
│   │   │   └── dead_cap.py           # 50%/50%/25%/25%/25% schedule
│   │   ├── composite/                # Epic 4: Dynasty Value Composite
│   │   │   ├── __init__.py
│   │   │   └── dynasty_value.py      # 6-factor composite score
│   │   └── schemas/                  # Pydantic output schemas
│   │       ├── __init__.py
│   │       ├── valuation.py          # PlayerValuationOutput, etc.
│   │       ├── projections.py        # MultiYearProjectionOutput
│   │       ├── cap.py                # CapScenarioOutput
│   │       └── composite.py          # DynastyValueOutput
│   └── ingest/                       # Existing ingestion modules
│       └── ...                       # (no changes)
│
├── flows/                            # NEW: Prefect orchestration
│   ├── __init__.py
│   ├── analytics_pipeline.py         # Main analytics flow (Epic 5)
│   ├── backtesting.py                # Backtesting validation flow (Epic 5)
│   └── tasks/                        # Reusable Prefect tasks
│       ├── __init__.py
│       ├── parquet_writer.py         # Write validated DataFrames
│       └── dbt_runner.py             # Trigger dbt commands
│
├── dbt/ff_data_transform/
│   ├── models/
│   │   ├── sources/
│   │   │   └── src_analytics.yml     # NEW: Analytics schema sources
│   │   ├── marts/
│   │   │   ├── mrt_player_valuation.sql           # NEW: Epic 1 output
│   │   │   ├── _mrt_player_valuation.yml
│   │   │   ├── mrt_multi_year_projections.sql     # NEW: Epic 2 output
│   │   │   ├── _mrt_multi_year_projections.yml
│   │   │   ├── mrt_cap_scenarios.sql              # NEW: Epic 3 output
│   │   │   ├── _mrt_cap_scenarios.yml
│   │   │   ├── mrt_dynasty_value_composite.sql    # NEW: Epic 4 output
│   │   │   └── _mrt_dynasty_value_composite.yml
│   │   └── ...                       # (existing models)
│   └── ...
│
├── data/
│   ├── raw/                          # Existing provider data
│   ├── analytics/                    # NEW: Python analytics outputs
│   │   ├── player_valuation/
│   │   │   └── latest.parquet
│   │   ├── multi_year_projections/
│   │   │   └── latest.parquet
│   │   ├── cap_scenarios/
│   │   │   └── latest.parquet
│   │   └── dynasty_value_composite/
│   │       └── latest.parquet
│   └── ...                           # (existing: stage, mart, ops)
│
├── tests/
│   ├── unit/
│   │   ├── test_vor.py               # NEW: Epic 1 tests
│   │   ├── test_war.py
│   │   ├── test_aging_curves.py      # NEW: Epic 2 tests
│   │   ├── test_multi_year.py
│   │   ├── test_dead_cap.py          # NEW: Epic 3 tests (100% coverage)
│   │   ├── test_contracts.py
│   │   └── test_dynasty_value.py     # NEW: Epic 4 tests
│   └── integration/
│       ├── test_analytics_pipeline.py # NEW: Epic 5 integration test
│       └── test_backtesting.py        # NEW: Epic 5 backtesting test
│
├── notebooks/                        # Existing analysis notebooks
│   └── ...                           # (consume new marts)
│
├── .prefect/                         # NEW: Prefect local config (gitignored)
├── justfile                          # Existing task runner
├── pyproject.toml                    # Existing Python config
└── README.md                         # (update with analytics docs)
```

### 3.2 Epic to Architecture Mapping

| Epic                                 | Code Location                                         | dbt Model Output              | Data Output                                             |
| ------------------------------------ | ----------------------------------------------------- | ----------------------------- | ------------------------------------------------------- |
| **Epic 0: Prefect Foundation**       | `flows/` directory setup, Prefect Cloud workspace     | N/A                           | N/A                                                     |
| **Epic 1: VoR/WAR Engine**           | `src/ff_analytics_utils/valuation/`                   | `mrt_player_valuation`        | `data/analytics/player_valuation/latest.parquet`        |
| **Epic 2: Multi-Year Projections**   | `src/ff_analytics_utils/projections/`                 | `mrt_multi_year_projections`  | `data/analytics/multi_year_projections/latest.parquet`  |
| **Epic 3: Cap Modeling**             | `src/ff_analytics_utils/cap_modeling/`                | `mrt_cap_scenarios`           | `data/analytics/cap_scenarios/latest.parquet`           |
| **Epic 4: Dynasty Value Composite**  | `src/ff_analytics_utils/composite/`                   | `mrt_dynasty_value_composite` | `data/analytics/dynasty_value_composite/latest.parquet` |
| **Epic 5: Integration & Validation** | `flows/analytics_pipeline.py`, `flows/backtesting.py` | All 4 marts materialized      | End-to-end pipeline validation                          |

______________________________________________________________________

## 4. Novel Architectural Patterns

### 4.1 Pattern: Prefect-First Development

**Problem:** Analytics code written standalone then wrapped in orchestration later requires significant refactoring (20-30 hours estimated).

**Solution:** Build Prefect infrastructure FIRST (Epic 0), then write all analytics as `@task`-decorated functions from Day 1.

**Implementation:**

```python
# Epic 0: Template pattern established
from prefect import task, flow
import polars as pl
from src.ff_analytics_utils.schemas.valuation import PlayerValuationOutput

@task(name="calculate-vor", retries=3, retry_delay_seconds=60)
def calculate_vor(league_settings: dict) -> pl.DataFrame:
    """Calculate VoR for all players."""
    # Business logic
    results = [...]

    # Pydantic validation
    validated = [PlayerValuationOutput(**r) for r in results]

    # Convert to Polars DataFrame
    return pl.DataFrame([v.model_dump() for v in validated])

@task(name="write-parquet")
def write_parquet(df: pl.DataFrame, output_path: str) -> None:
    """Write validated DataFrame to Parquet."""
    df.write_parquet(output_path)

@flow(name="analytics-pipeline")
def analytics_pipeline():
    """Main analytics orchestration flow."""
    # Epic 1
    vor_df = calculate_vor(league_settings={...})
    write_parquet(vor_df, "data/analytics/player_valuation/latest.parquet")

    # Epic 2 (depends on Epic 1)
    proj_df = calculate_projections(vor_df)
    write_parquet(proj_df, "data/analytics/multi_year_projections/latest.parquet")

    # Epic 3
    cap_df = calculate_cap_scenarios()
    write_parquet(cap_df, "data/analytics/cap_scenarios/latest.parquet")

    # Epic 4 (depends on all)
    composite_df = calculate_composite(vor_df, proj_df, cap_df)
    write_parquet(composite_df, "data/analytics/dynasty_value_composite/latest.parquet")

    # Trigger dbt materialization
    run_dbt_marts()
```

**Benefits:**

- Monitoring/alerting from Day 1 (Prefect UI shows task status, runtime, failures)
- Automatic retry logic (configurable per task)
- Dependency management (task ordering enforced)
- Artifact tracking (intermediate results logged)
- No retrofit work (20-30 hours saved)

**Epic Coverage:** All epics (Epic 0 foundation, Epics 1-5 implementation)

______________________________________________________________________

### 4.2 Pattern: Contract-First Design (Pydantic → Parquet → dbt)

**Problem:** Schema drift between Python analytics outputs and dbt models causes silent failures or integration breaks.

**Solution:** Define Pydantic schemas for all task outputs, validate at task boundary, write to Parquet with explicit schema matching dbt source definitions.

**Implementation:**

```python
# src/ff_analytics_utils/schemas/valuation.py
from pydantic import BaseModel, Field
from datetime import date

class PlayerValuationOutput(BaseModel):
    """Output schema for VoR/WAR valuation engine."""
    player_id: str = Field(..., description="Canonical player ID from dim_player")
    snapshot_date: date = Field(..., description="Date of valuation calculation")
    vor: float = Field(..., description="Value over Replacement (fantasy points above baseline)")
    war: float = Field(..., description="Wins Above Replacement (expected wins added)")
    replacement_level: float = Field(..., description="Position-specific replacement baseline (PPG)")
    positional_scarcity_adjustment: float = Field(..., description="Cross-positional value adjustment")
    contract_efficiency_dollar_per_war: float | None = Field(None, description="$/WAR (None for free agents)")

    class Config:
        frozen = True  # Immutable
        json_schema_extra = {
            "example": {
                "player_id": "12345",
                "snapshot_date": "2025-11-18",
                "vor": 125.5,
                "war": 2.3,
                "replacement_level": 12.5,
                "positional_scarcity_adjustment": 1.15,
                "contract_efficiency_dollar_per_war": 8.2
            }
        }

# flows/tasks/parquet_writer.py
from prefect import task
import polars as pl
from pydantic import BaseModel

@task
def write_parquet_with_schema(
    data: list[BaseModel],
    output_path: str,
    model_class: type[BaseModel]
) -> None:
    """Write Pydantic models to Parquet with schema validation."""
    # Convert to dict, then Polars DataFrame
    df = pl.DataFrame([item.model_dump() for item in data])

    # Write to Parquet
    df.write_parquet(output_path)

    # Log schema for debugging
    print(f"Written {len(df)} rows to {output_path}")
    print(f"Schema: {df.schema}")
```

```yaml
# dbt/ff_data_transform/models/sources/src_analytics.yml
version: 2

sources:
  - name: analytics
    description: Python analytics outputs (Prefect tasks)
    schema: analytics

    tables:
      - name: player_valuation
        description: VoR/WAR valuation engine output
        external:
          location: 'data/analytics/player_valuation/latest.parquet'
        columns:
          - name: player_id
            description: Canonical player ID from dim_player
            data_tests:
              - not_null
          - name: snapshot_date
            description: Date of valuation calculation
            data_tests:
              - not_null
          - name: vor
            description: Value over Replacement (fantasy points)
          - name: war
            description: Wins Above Replacement
          - name: replacement_level
            description: Position-specific replacement baseline
          - name: positional_scarcity_adjustment
            description: Cross-positional value adjustment
          - name: contract_efficiency_dollar_per_war
            description: $/WAR efficiency metric (NULL for free agents)
```

```sql
-- dbt/ff_data_transform/models/marts/mrt_player_valuation.sql
{{ config(
    materialized='table',
    unique_key=['player_id', 'snapshot_date']
) }}

/*
Player valuation mart - VoR/WAR scores with contract efficiency.

Grain: One row per player per snapshot date
Source: analytics.player_valuation (Python Prefect task output)
*/

select
    player_id,
    snapshot_date,
    vor,
    war,
    replacement_level,
    positional_scarcity_adjustment,
    contract_efficiency_dollar_per_war
from {{ source('analytics', 'player_valuation') }}
```

**Benefits:**

- Schema drift caught at runtime (Pydantic validation fails immediately)
- Type-safe handoffs (player_id always str, vor always float)
- dbt alignment (Parquet columns match dbt source YAML definitions exactly)
- Self-documenting (Pydantic docstrings → API docs, dbt YAML → data catalog)
- Refactor safety (changing schema requires updating Pydantic model, failing tests immediately)

**Epic Coverage:** Epics 1-4 (all analytics outputs), Epic 5 (integration validation)

______________________________________________________________________

### 4.3 Pattern: Continuous Backtesting Flow

**Problem:** One-time validation leaves model drift undetected; manual "remember to test" doesn't scale.

**Solution:** Separate Prefect flow scheduled weekly to run TimeSeriesSplit backtesting with automated Discord alerts on regression.

**Implementation:**

```python
# flows/backtesting.py
from prefect import flow, task
from prefect.blocks.discord import DiscordWebhook
from sklearn.model_selection import TimeSeriesSplit
import numpy as np

@task
def run_timeseries_cv(historical_data, projection_model, test_years):
    """Run TimeSeriesSplit cross-validation on historical data."""
    tscv = TimeSeriesSplit(n_splits=len(test_years))
    results = []

    for train_idx, test_idx in tscv.split(historical_data):
        train_data = historical_data[train_idx]
        test_data = historical_data[test_idx]

        # Train on historical data
        model = projection_model.fit(train_data)

        # Predict on holdout year
        predictions = model.predict(test_data)

        # Calculate MAE
        actuals = test_data['actual_ppg']
        mae = np.mean(np.abs(predictions - actuals))

        results.append({
            'test_year': test_data['season'].iloc[0],
            'mae': mae,
            'predictions': predictions,
            'actuals': actuals
        })

    return results

@task
def send_discord_alert(message: str):
    """Send Discord notification via webhook block."""
    discord_webhook = DiscordWebhook.load("ff-analytics-alerts")
    discord_webhook.notify(message)

@flow(name="Weekly Backtesting Validation")
def backtesting_flow():
    """Scheduled backtesting validation with regression alerts."""
    # Load historical data (2020-2023)
    historical_data = load_historical_projections_and_actuals()

    # Run TimeSeriesSplit CV
    test_years = [2021, 2022, 2023]
    results = run_timeseries_cv(
        historical_data,
        projection_model=MultiYearProjectionModel(),
        test_years=test_years
    )

    # Calculate overall MAE
    overall_mae = np.mean([r['mae'] for r in results])

    # Thresholds
    TARGET_MAE = 0.20  # 20% target from PRD
    WARNING_MAE = 0.25  # 25% warning threshold

    # Alert logic
    if overall_mae > WARNING_MAE:
        send_discord_alert(
            f"⚠️ **MODEL REGRESSION DETECTED**\n"
            f"Overall MAE: {overall_mae:.2%} (threshold: {TARGET_MAE:.2%})\n"
            f"Breakdown:\n"
            + "\n".join([f"- {r['test_year']}: {r['mae']:.2%}" for r in results])
        )
    elif overall_mae > TARGET_MAE:
        send_discord_alert(
            f"ℹ️ MAE above target: {overall_mae:.2%} (target: {TARGET_MAE:.2%})"
        )
    else:
        send_discord_alert(
            f"✅ Backtesting passed: MAE {overall_mae:.2%} (target: {TARGET_MAE:.2%})"
        )

    return results

# Deployment configuration
if __name__ == "__main__":
    backtesting_flow.serve(
        name="weekly-backtesting-validation",
        cron="0 9 * * 1",  # Monday 9am
        tags=["validation", "backtesting"],
        description="Weekly backtesting validation with Discord alerts"
    )
```

**Benefits:**

- Automated monitoring (no manual "remember to test")
- Early drift detection (catches regression within 1 week)
- Production pattern (scheduled flow vs ad-hoc script)
- Team visibility (Discord alerts notify all stakeholders)
- Historical tracking (Prefect UI logs all backtest results)

**Epic Coverage:** Epic 2 (projection model), Epic 5 (continuous validation)

______________________________________________________________________

## 5. Cross-Cutting Concerns & Implementation Patterns

### 5.1 Error Handling Strategy

**Principle:** Fail fast, fail loud, with enough context to debug.

**Patterns:**

1. **Pydantic Validation Errors (Schema Drift)**

   ```python
   try:
       validated = PlayerValuationOutput(**raw_data)
   except ValidationError as e:
       # Log full validation error with field details
       logger.error(f"Schema validation failed: {e.json()}")
       # Re-raise to fail the Prefect task
       raise
   ```

2. **Prefect Task Retries (Transient Failures)**

   ```python
   @task(retries=3, retry_delay_seconds=60)
   def fetch_ktc_values():
       # API calls, network requests (retry on transient failures)
       pass
   ```

3. **dbt Test Failures (Data Quality)**

   ```yaml
   # Fail pipeline if critical tests fail
   config:
     severity: error
     error_if: ">0"
   ```

4. **Discord Alerts (Critical Failures)**

   ```python
   @flow(on_failure=[send_failure_alert])
   def analytics_pipeline():
       pass  # Any unhandled exception triggers Discord alert
   ```

### 5.2 Logging Strategy

**Framework:** Python `logging` module + Prefect structured logs

**Levels:**

- `DEBUG`: Intermediate calculations, loop iterations
- `INFO`: Task start/complete, row counts, file paths
- `WARNING`: Non-critical issues (e.g., missing optional data)
- `ERROR`: Failures requiring investigation
- `CRITICAL`: System-wide failures

**Format:**

```python
import logging

logger = logging.getLogger(__name__)

@task
def calculate_vor():
    logger.info("Starting VoR calculation")
    logger.debug(f"League settings: {league_settings}")

    # Business logic
    results = [...]

    logger.info(f"Calculated VoR for {len(results)} players")
    return results
```

**Prefect Integration:** All `@task` logs automatically captured in Prefect UI with timestamps, context.

### 5.3 Testing Strategy

**Coverage Targets:**

- **Valuation engines:** 80%+ (Epic 1)
- **Cap rule validation:** 100% (Epic 3 - deterministic, must be bug-free)
- **Overall project:** 70%+

**Test Types:**

1. **Unit Tests (pytest)**

   ```python
   # tests/unit/test_vor.py
   def test_vor_calculation_known_inputs():
       """VoR for known player should match hand-calculated value."""
       player_stats = {'ppg': 20.5, 'position': 'RB'}
       league_settings = {'num_teams': 12, 'rb_slots': 2}

       vor = calculate_vor(player_stats, league_settings)

       # RB24 replacement level = 12.5 PPG
       expected_vor = (20.5 - 12.5) * 17  # 17-game season
       assert abs(vor - expected_vor) < 0.01
   ```

2. **Property-Based Tests (pytest-hypothesis)**

   ```python
   from hypothesis import given, strategies as st

   @given(st.floats(min_value=0, max_value=100))
   def test_war_always_positive(ppg):
       """WAR should never be negative for non-negative PPG."""
       war = calculate_war(ppg)
       assert war >= 0
   ```

3. **Integration Tests (pytest + dbt)**

   ```python
   # tests/integration/test_analytics_pipeline.py
   def test_end_to_end_pipeline():
       """Complete pipeline: Python → Parquet → dbt → query."""
       # Run Prefect flow
       state = analytics_pipeline()
       assert state.is_successful()

       # Run dbt materialization
       subprocess.run(["just", "dbt-run", "--select", "mrt_player_valuation"])

       # Query materialized mart
       conn = duckdb.connect("dbt/ff_data_transform/target/dev.duckdb")
       result = conn.execute("SELECT COUNT(*) FROM mrt_player_valuation").fetchone()
       assert result[0] > 500  # Should have 500+ players
   ```

4. **dbt Tests (grain, FK, not-null)**

   ```yaml
   # All new marts follow existing dbt test patterns
   data_tests:
     - dbt_utils.unique_combination_of_columns:
         arguments:
           combination_of_columns: [player_id, snapshot_date]
         config:
           severity: error
   ```

5. **Backtesting Validation (Epic 5)**

   - TimeSeriesSplit CV on 2020→2023 historical data
   - MAE < 20% target (PRD requirement)
   - Scheduled weekly via Prefect

### 5.4 Naming Conventions

**Python Modules:**

- snake_case: `vor.py`, `multi_year.py`, `aging_curves.py`
- Descriptive: What it does, not how (NOT `vor_calculator.py`, just `vor.py`)

**Python Functions:**

- snake_case: `calculate_vor()`, `get_replacement_baseline()`
- Verb-first: Action-oriented (`calculate`, `get`, `generate`, `validate`)

**Python Classes:**

- PascalCase: `PlayerValuationOutput`, `MultiYearProjectionEngine`
- Noun-focused: Domain entities or services

**Pydantic Schemas:**

- PascalCase + Output suffix: `PlayerValuationOutput`, `CapScenarioOutput`
- Match dbt source table: `PlayerValuationOutput` → `analytics.player_valuation`

**Prefect Tasks:**

- kebab-case names: `@task(name="calculate-vor")`
- Descriptive: Matches function name semantics

**Prefect Flows:**

- kebab-case names: `@flow(name="analytics-pipeline")`
- Hyphenated: Multi-word descriptive

**dbt Models:**

- Prefix + snake_case: `mrt_player_valuation`, `mrt_multi_year_projections`
- Mart prefix: All analytics outputs use `mrt_` (consistency with existing marts)

**dbt Sources:**

- Schema: `analytics` (new schema for Python outputs)
- Table names: Match Parquet filenames (snake_case)

**Parquet Files:**

- snake_case: `player_valuation/latest.parquet`
- No timestamps in filename: Always `latest.parquet` (immutable snapshot pattern)

**Directory Names:**

- snake_case: `cap_modeling/`, `multi_year_projections/`
- Descriptive: What domain, not generic (`valuation/` not `utils/`)

### 5.5 Code Organization Patterns

**Python Package Structure:**

- One module per epic: `valuation/`, `projections/`, `cap_modeling/`, `composite/`
- Shared schemas: `schemas/` (Pydantic models)
- Flat hierarchy: Avoid deep nesting (`valuation/vor.py` not `valuation/engines/vor/calculator.py`)

**Prefect Flow Organization:**

- One file per flow: `analytics_pipeline.py`, `backtesting.py`
- Shared tasks: `tasks/` directory (reusable across flows)

**dbt Model Layering:**

- Sources: `sources/src_analytics.yml` (Python output references)
- Marts: `marts/mrt_*.sql` (thin SQL layer for documentation/testing)
- No staging: Python outputs already normalized (skip staging layer)

**Test Organization:**

- Mirror source structure: `tests/unit/valuation/test_vor.py` matches `src/ff_analytics_utils/valuation/vor.py`
- Integration separate: `tests/integration/` (end-to-end tests)

### 5.6 Consistency Rules (AI Agent Alignment)

**Critical for Multi-Agent Development:**

1. **ALL analytics outputs write to `data/analytics/<model>/latest.parquet`**

   - Never vary path structure
   - Never add timestamps to filename
   - Always overwrite `latest.parquet`

2. **ALL Prefect tasks MUST be decorated with `@task`**

   - Never write standalone functions that run outside Prefect
   - Always include `name` parameter for Prefect UI clarity

3. **ALL analytics outputs MUST validate against Pydantic schema before writing Parquet**

   - Never skip schema validation
   - Never write raw dicts/DataFrames without Pydantic pass

4. **ALL dbt marts MUST define `unique_key` in config**

   - Never materialize tables without grain declaration
   - Always add `unique_combination_of_columns` test

5. **ALL cap modeling calculations MUST have 100% test coverage**

   - Never merge cap code without comprehensive tests
   - Dead cap schedule (50%/50%/25%/25%/25%) is deterministic, must be bug-free

6. **ALL backtesting MUST use TimeSeriesSplit (NO shuffle=True)**

   - Never use random CV splits
   - Small NFL sample (17 games) → overfitting risk → temporal validation mandatory

______________________________________________________________________

## 6. Data Architecture

### 6.1 Analytics Output Schemas

**Schema: `analytics` (NEW - Python task outputs)**

| Table                     | Grain                                                          | Columns                                                                                                                                                                                              | Size Estimate                       |
| ------------------------- | -------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------- |
| `player_valuation`        | player_id × snapshot_date                                      | 7 columns (player_id, snapshot_date, vor, war, replacement_level, scarcity_adj, contract_eff)                                                                                                        | ~500 players × snapshots            |
| `multi_year_projections`  | player_id × season × week × snapshot_date                      | 12 columns (player_id, season, week, projection_year, ppg_median, ppg_floor, ppg_ceiling, age_factor, opportunity_factor, ...)                                                                       | ~500 players × 5 years × 17 weeks   |
| `cap_scenarios`           | franchise_id × projection_year × scenario_name × snapshot_date | 9 columns (franchise_id, projection_year, scenario_name, base_cap, active_obligations, dead_cap, traded_cap_net, available_cap, ...)                                                                 | 12 franchises × 5 years × scenarios |
| `dynasty_value_composite` | player_id × snapshot_date                                      | 13 columns (player_id, snapshot_date, dynasty_value_score, vor_component, economics_component, age_component, scarcity_component, variance_component, market_component, ktc_value, value_delta, ...) | ~500 players × snapshots            |

### 6.2 Integration with Existing Dimensions

**Conformed Dimensions (Reuse from Existing dbt Models):**

- `dim_player` (player_id, display_name, position, current_team)
- `dim_franchise` (franchise_id, franchise_name, owner_name)
- `dim_scoring_rule` (stat_name, points_per_unit, is_current)
- `dim_team` (team_abbr, team_name, conference, division)

**Foreign Key Relationships:**

```sql
-- Analytics outputs reference existing dimensions
mrt_player_valuation.player_id → dim_player.player_id
mrt_cap_scenarios.franchise_id → dim_franchise.franchise_id
mrt_multi_year_projections.player_id → dim_player.player_id
```

### 6.3 Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│  Existing Data Sources (No Changes)                                 │
├─────────────────────────────────────────────────────────────────────┤
│  • nflverse (player stats, opportunity metrics)                     │
│  • FFAnalytics (projections, consensus)                             │
│  • KTC (dynasty values, market signals)                             │
│  • Commissioner Sheets (contracts, cap, picks)                      │
│  • Sleeper (rosters, transactions)                                  │
└─────────────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────────┐
│  Existing dbt Staging Models (No Changes)                           │
├─────────────────────────────────────────────────────────────────────┤
│  • stg_nflverse__player_stats                                       │
│  • stg_ffanalytics__projections                                     │
│  • stg_ktc_assets                                                   │
│  • stg_sheets__contracts_active                                     │
│  • stg_sleeper__rosters                                             │
└─────────────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────────┐
│  Existing dbt Core Models (Consumed by Analytics)                   │
├─────────────────────────────────────────────────────────────────────┤
│  • fct_player_stats (actuals)                                       │
│  • fct_player_projections (projections)                             │
│  • dim_player (identity)                                            │
│  • dim_scoring_rule (fantasy scoring)                               │
│  • mrt_contract_snapshot_current (cap modeling input)               │
│  • mrt_fantasy_actuals_weekly (VoR baseline input)                  │
│  • mrt_real_world_actuals_weekly (aging curves input)               │
└─────────────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────────┐
│  NEW: Python Analytics (Prefect Tasks)                              │
├─────────────────────────────────────────────────────────────────────┤
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  Epic 1: VoR/WAR Engine                                       │  │
│  │  → vor.py, war.py, baselines.py, positional_value.py         │  │
│  │  → Pydantic: PlayerValuationOutput                           │  │
│  │  → Output: data/analytics/player_valuation/latest.parquet    │  │
│  └───────────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  Epic 2: Multi-Year Projections                               │  │
│  │  → multi_year.py, aging_curves.py, opportunity.py            │  │
│  │  → Pydantic: MultiYearProjectionOutput                       │  │
│  │  → Output: data/analytics/multi_year_projections/latest.pqt  │  │
│  └───────────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  Epic 3: Cap Space Projection                                 │  │
│  │  → scenarios.py, contracts.py, dead_cap.py                   │  │
│  │  → Pydantic: CapScenarioOutput                               │  │
│  │  → Output: data/analytics/cap_scenarios/latest.parquet       │  │
│  └───────────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  Epic 4: Dynasty Value Composite                              │  │
│  │  → dynasty_value.py (6-factor composite)                     │  │
│  │  → Pydantic: DynastyValueOutput                              │  │
│  │  → Output: data/analytics/dynasty_value_composite/latest.pqt │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────────┐
│  NEW: dbt Analytics Sources (External Parquet)                      │
├─────────────────────────────────────────────────────────────────────┤
│  • source('analytics', 'player_valuation')                          │
│  • source('analytics', 'multi_year_projections')                    │
│  • source('analytics', 'cap_scenarios')                             │
│  • source('analytics', 'dynasty_value_composite')                   │
└─────────────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────────┐
│  NEW: dbt Analytics Marts (Thin SQL Layer)                          │
├─────────────────────────────────────────────────────────────────────┤
│  • mrt_player_valuation (SELECT * FROM source, + tests/docs)        │
│  • mrt_multi_year_projections (SELECT * FROM source, + tests/docs)  │
│  • mrt_cap_scenarios (SELECT * FROM source, + tests/docs)           │
│  • mrt_dynasty_value_composite (SELECT * FROM source, + tests/docs) │
└─────────────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────────┐
│  Existing Consumption Layer (No Changes)                            │
├─────────────────────────────────────────────────────────────────────┤
│  • Jupyter Notebooks (query marts)                                  │
│  • Marimo Notebooks (interactive analysis)                          │
│  • Ad-hoc DuckDB queries                                            │
└─────────────────────────────────────────────────────────────────────┘
```

______________________________________________________________________

## 7. Deployment Architecture

### 7.1 Orchestration Infrastructure

**Prefect Cloud (SaaS):**

- **Purpose:** Managed orchestration, scheduling, monitoring
- **Workspace:** `ff-analytics` (to be created in Epic 0)
- **Deployment:** Flows deployed via `prefect deploy`
- **Execution:** Flows run locally on Mac during development
- **Production:** Same local execution (no separate compute needed for MVP)

**Discord Integration:**

- **Webhook Block:** `ff-analytics-alerts` (created in Epic 0)
- **Usage:** Pipeline failures, backtesting alerts, validation warnings
- **Pattern:** Reuse existing GitHub Actions Discord integration patterns

**Scheduled Flows:**

| Flow                            | Schedule              | Purpose                                       |
| ------------------------------- | --------------------- | --------------------------------------------- |
| `analytics-pipeline`            | Manual trigger        | Main analytics refresh (on-demand during dev) |
| `weekly-backtesting-validation` | `0 9 * * 1` (Mon 9am) | Continuous model validation                   |

### 7.2 Storage Architecture

**Development (Local Mac):**

```
data/
├── raw/          # Existing provider data (unchanged)
├── analytics/    # NEW: Python task outputs (Parquet)
├── stage/        # Existing (unchanged)
├── mart/         # Existing (unchanged)
└── ops/          # Existing (unchanged)
```

**Production (GCS - Future):**

```
gs://ff-analytics/
├── raw/          # Existing pattern
├── analytics/    # NEW: Mirror local structure
│   ├── player_valuation/
│   ├── multi_year_projections/
│   ├── cap_scenarios/
│   └── dynasty_value_composite/
├── mart/         # Existing
└── ops/          # Existing
```

**Database (DuckDB):**

- **Location:** `dbt/ff_data_transform/target/dev.duckdb` (local file)
- **Schemas:** `main` (existing), `analytics` (NEW - external Parquet sources)
- **Materialization:** In-memory catalog only, data stored as external Parquet

### 7.3 Development Workflow

**Local Development:**

1. Run Prefect flow: `python flows/analytics_pipeline.py`
2. Prefect writes Parquet: `data/analytics/<model>/latest.parquet`
3. Run dbt materialization: `just dbt-run --select mrt_player_valuation+`
4. Query in notebooks: `duckdb.connect(...).execute("SELECT * FROM mrt_player_valuation")`

**Testing:**

1. Unit tests: `pytest tests/unit/`
2. Integration tests: `pytest tests/integration/`
3. dbt tests: `just dbt-test`
4. Backtesting: `python flows/backtesting.py`

**CI/CD (Future - Epic 5 Extension):**

- Pre-commit hooks: Existing (ruff, pytest)
- GitHub Actions: Run on PR (pytest, dbt compile, dbt test)
- Backtesting: Weekly scheduled (Prefect deployment)

______________________________________________________________________

## 8. Architecture Decision Records (ADRs)

### ADR-001: Prefect-First vs Post-MVP Orchestration

**Status:** Accepted

**Context:**
Analytics code could be written standalone (Python scripts) then wrapped in orchestration later, OR orchestration infrastructure could be built first with analytics designed as Prefect tasks from Day 1.

**Decision:**
Build Prefect infrastructure FIRST (Epic 0: Week 1, Days 1-2) before writing any analytics code. All analytics modules will be `@task`-decorated from Day 1.

**Rationale:**

1. **Avoid retrofit work:** Wrapping standalone scripts in Prefect later requires 20-30 hours of refactoring (estimated based on snapshot governance experience).
2. **Monitoring from Day 1:** Prefect UI shows task status, runtime, failures immediately (no manual log parsing).
3. **Backtesting automation:** Continuous validation flow integrated from start vs bolt-on later.
4. **Retry logic:** Transient failures (API timeouts, network issues) handled automatically via `@task(retries=3)`.
5. **Team experience:** Snapshot governance flows provide proven Prefect patterns (Discord alerts, error handling, artifact tracking).

**Consequences:**

- **Positive:**
  - 20-30 hours saved (no retrofit)
  - Monitoring/alerting from Day 1
  - Backtesting automated immediately
  - Consistent patterns across all analytics tasks
- **Negative:**
  - Epic 0 overhead (10 hours setup)
  - Learning curve for Prefect (mitigated by intermediate user skill level)
- **Neutral:**
  - Prefect Cloud dependency (SaaS, but managed service reduces ops burden)

**Alternatives Considered:**

1. **Standalone scripts + Cron:** Rejected - no monitoring, fragile scheduling, manual log parsing.
2. **Airflow:** Rejected - heavier weight, Python 2.7 legacy, less Pythonic than Prefect.
3. **Post-MVP Prefect:** Rejected - 20-30 hours retrofit work, monitoring not available during development.

**Related Patterns:** Contract-First Design (ADR-003), Continuous Backtesting (ADR-004)

______________________________________________________________________

### ADR-002: External Parquet Data Flow vs DuckDB-First

**Status:** Accepted

**Context:**
Python analytics outputs could write directly to DuckDB tables, then dbt would read from DuckDB. Alternatively, Python could write Parquet files, dbt reads as external tables, then materializes marts.

**Decision:**
Python writes Parquet → dbt reads as external tables → dbt materializes marts.

**Data Flow:**

```
Python @task → data/analytics/<model>/latest.parquet → dbt source (external) → dbt mart
```

**Rationale:**

1. **Existing pattern:** 4+ staging models already use `external=true` reading from `data/raw/`. This extends that pattern to `data/analytics/`.
2. **No DB round-trip:** Avoid Python → DuckDB write → DuckDB read overhead. Parquet is columnar, optimized for analytics.
3. **Simpler debugging:** Inspect Parquet files directly with `parquet-tools` or Polars. DuckDB tables require SQL queries.
4. **Immutable snapshots:** Parquet files are versioned/timestamped naturally. DuckDB tables require explicit versioning.
5. **GCS migration:** Future production deployment writes Parquet to GCS directly (no schema changes, just path swap).

**Consequences:**

- **Positive:**
  - Matches existing staging pattern (developers familiar)
  - No DuckDB round-trip overhead
  - Simpler debugging (Parquet inspection)
  - Cloud-ready (GCS Parquet path swap)
- **Negative:**
  - Two file writes per model (Python → Parquet, dbt → Parquet mart)
  - External table overhead (DuckDB reads Parquet on every query vs in-memory)
- **Neutral:**
  - Parquet schema evolution requires careful handling (Pydantic versioning)

**Alternatives Considered:**

1. **DuckDB-first:** Python → DuckDB table → dbt SELECT. Rejected - DuckDB write overhead, no existing pattern.
2. **Delta Lake:** Python → Delta format → dbt. Rejected - adds complexity, DuckDB Delta support immature.
3. **Direct mart writes:** Python → `data/mart/` (skip dbt). Rejected - lose dbt testing/documentation/lineage.

**Related Patterns:** Contract-First Design (ADR-003), existing `external=true` staging models

______________________________________________________________________

### ADR-003: Contract-First Design with Pydantic

**Status:** Accepted

**Context:**
Python analytics outputs could be written as raw Polars DataFrames to Parquet, OR outputs could be validated against Pydantic schemas before writing.

**Decision:**
Define Pydantic schemas for ALL analytics task outputs. Validate at task boundary BEFORE writing Parquet.

**Pattern:**

```python
# Define schema
class PlayerValuationOutput(BaseModel):
    player_id: str
    snapshot_date: date
    vor: float
    # ... all fields with types and descriptions

# Validate in @task
@task
def calculate_vor(...) -> pl.DataFrame:
    results = [...]
    validated = [PlayerValuationOutput(**r) for r in results]  # Fails if schema mismatch
    return pl.DataFrame([v.model_dump() for v in validated])
```

**Rationale:**

1. **Fail fast:** Schema drift caught at runtime immediately vs silent corruption discovered weeks later.
2. **Type safety:** `player_id` always `str`, `vor` always `float`. No duck typing ambiguity.
3. **dbt alignment:** Pydantic field names match dbt source YAML columns exactly (enforced by validation).
4. **Self-documenting:** Pydantic docstrings → API docs, dbt YAML → data catalog. Single source of truth.
5. **Refactor safety:** Changing schema requires updating Pydantic model → failing tests immediately → prevents silent breaks.

**Consequences:**

- **Positive:**
  - Schema drift caught immediately (fails task vs silent corruption)
  - Type-safe handoffs (Python → Parquet → dbt)
  - Self-documenting (Pydantic + dbt YAML aligned)
  - Refactor safety (breaking changes caught in tests)
- **Negative:**
  - Slight overhead (Pydantic validation ~1-5ms per row, negligible for 500 players)
  - Boilerplate (define schemas for all outputs, ~50 lines per schema)
- **Neutral:**
  - Schema evolution requires versioning (Pydantic V1/V2 migration, but controlled)

**Alternatives Considered:**

1. **Duck typing:** Raw DataFrames → Parquet. Rejected - no type safety, schema drift undetected.
2. **Pandera schemas:** DataFrame-level validation. Rejected - less Pythonic than Pydantic, worse IDE support.
3. **Manual validation:** Custom `assert` statements. Rejected - error-prone, inconsistent, no self-documentation.

**Related Patterns:** External Parquet Flow (ADR-002), dbt source definitions matching Pydantic schemas exactly

______________________________________________________________________

### ADR-004: Continuous Backtesting Flow vs One-Time Validation

**Status:** Accepted

**Context:**
Model validation could be done once at development time (2020→2023 backtest), OR validation could be continuous with scheduled backtesting flow detecting drift.

**Decision:**
Separate Prefect flow scheduled weekly (`0 9 * * 1`) to run TimeSeriesSplit backtesting with automated Discord alerts on regression.

**Pattern:**

```python
@flow(name="Weekly Backtesting Validation")
def backtesting_flow():
    results = run_timeseries_cv(...)
    mae = calculate_mae(results)
    if mae > THRESHOLD:
        send_discord_alert(f"⚠️ Model regression! MAE: {mae:.2%}")

backtesting_flow.serve(cron="0 9 * * 1")  # Monday 9am
```

**Rationale:**

1. **Catch drift early:** NFL rules change, coaching philosophies shift, player roles evolve. Historical patterns may not hold indefinitely.
2. **Automated monitoring:** No manual "remember to test" required. Scheduled flow runs weekly.
3. **Team visibility:** Discord alerts notify all stakeholders immediately (not buried in logs).
4. **Production pattern:** Scheduled flow vs ad-hoc script (consistent with Prefect-first architecture).
5. **PRD requirement:** Continuous validation aligned with "model retraining: annual cadence + in-season updates".

**Consequences:**

- **Positive:**
  - Early drift detection (within 1 week vs manual quarterly check)
  - Automated monitoring (no manual intervention)
  - Team visibility (Discord alerts)
  - Production-ready (scheduled deployment)
- **Negative:**
  - Compute overhead (backtesting ~5-10 min weekly, negligible)
  - Alert fatigue risk (mitigated by thresholds: only alert if >25% MAE)
- **Neutral:**
  - Historical data dependency (requires 2020-2023 actuals, already available)

**Alternatives Considered:**

1. **One-time validation:** Backtest once, ship. Rejected - no drift detection.
2. **Manual quarterly review:** Ad-hoc testing. Rejected - manual, inconsistent, no automation.
3. **CI/CD integration:** Run on every commit. Rejected - slow (5-10 min), blocks PRs unnecessarily.

**Related Patterns:** Prefect-First (ADR-001), TimeSeriesSplit validation (mandatory for small NFL samples)

______________________________________________________________________

## 9. Development Environment & Prerequisites

### 9.1 Prerequisites

**Required:**

- Python 3.13.6 (managed via .python-version)
- uv 0.8.8 (package manager)
- just (task runner, installed via brew/cargo)
- Git (version control)
- DuckDB CLI (optional, for ad-hoc queries)

**Optional:**

- Jupyter (notebook analysis)
- Marimo (interactive notebooks)
- VS Code + Python extension (recommended IDE)

### 9.2 Environment Setup

**Initial Setup:**

```bash
# Clone repository (assumed already done)
cd /Users/jason/code/ff_data_analytics

# Install dependencies
uv sync

# Create data/analytics directory
mkdir -p data/analytics

# Verify dbt connection
just dbt-compile
```

**Prefect Setup (Epic 0 Story 1):**

```bash
# Install Prefect
uv add prefect

# Login to Prefect Cloud
prefect cloud login

# Create workspace
prefect workspace create ff-analytics

# Create Discord webhook block
prefect block register --file blocks/discord_webhook.py
```

**Verification:**

```bash
# Run tests
pytest tests/unit/

# Run dbt
just dbt-run
just dbt-test

# Check quality
just quality-sql
just lint
just typecheck
```

### 9.3 Development Commands

**Analytics Development:**

```bash
# Run main analytics pipeline
python flows/analytics_pipeline.py

# Run backtesting validation
python flows/backtesting.py

# Run specific epic module
python -m src.ff_analytics_utils.valuation.vor
```

**dbt Development:**

```bash
# Materialize analytics marts
just dbt-run --select mrt_player_valuation+

# Test analytics marts
just dbt-test --select mrt_player_valuation

# View dbt docs
just dbt-docs
```

**Testing:**

```bash
# Unit tests
pytest tests/unit/ -v

# Integration tests
pytest tests/integration/ -v

# Coverage report
pytest --cov=src/ff_analytics_utils --cov-report=html
```

**Quality Checks:**

```bash
# All SQL quality checks
just quality-sql

# Python linting
just lint

# Type checking
just typecheck

# Pre-commit (run all hooks)
pre-commit run --all-files
```

______________________________________________________________________

## 10. Implementation Checklist

### 10.1 Epic 0: Prefect Foundation Setup

- [ ] **E0-S1:** Prefect Cloud workspace setup
  - [ ] Create `ff-analytics` workspace
  - [ ] Configure authentication (API keys)
  - [ ] Test deployment with simple flow
- [ ] **E0-S2:** Discord notification block
  - [ ] Create `ff-analytics-alerts` DiscordWebhook block
  - [ ] Test with sample alert
- [ ] **E0-S3:** Analytics flow templates
  - [ ] Template for data loading tasks (read dbt marts)
  - [ ] Template for analytics computation tasks (Pydantic validation)
  - [ ] Template for Parquet writer tasks
  - [ ] Template for dbt runner tasks
- [ ] **E0-S4:** Review snapshot governance flows
  - [ ] Document integration points
  - [ ] Extract reusable patterns (error handling, retry logic, Discord notifications)
  - [ ] Create sequence diagram (snapshot ingest → dbt staging → analytics → marts)

### 10.2 Epic 1: VoR/WAR Valuation Engine

- [ ] **E1-S1:** Replacement level baseline calculation
  - [ ] `baselines.py`: Position-specific thresholds (QB12, RB24, WR36, TE12)
  - [ ] Unit tests: Baselines match league roster depth
- [ ] **E1-S2:** VoR calculation engine
  - [ ] `vor.py`: Calculate VoR for all players
  - [ ] Unit tests: Top 10 players match hand-calculated examples
- [ ] **E1-S3:** WAR estimation
  - [ ] `war.py`: Convert fantasy points to wins above replacement
  - [ ] Unit tests: WAR methodology documented, conceptually aligns with Fantasy Points
- [ ] **E1-S4:** Positional scarcity adjustment
  - [ ] `positional_value.py`: Cross-positional value algorithm
  - [ ] Unit tests: RB/QB valued higher than WR/TE
- [ ] **E1-S5:** Contract economics integration
  - [ ] Calculate $/WAR and $/VoR efficiency metrics
  - [ ] Unit tests: Top 10 best/worst value rankings intuitively correct
- [ ] **E1-S6:** dbt mart: mrt_player_valuation
  - [ ] Create `mrt_player_valuation.sql`
  - [ ] Create `_mrt_player_valuation.yml` with tests
  - [ ] Verify queryable from notebooks
- [ ] **E1-S7:** Unit tests & validation
  - [ ] 80%+ coverage for VoR/WAR engines
  - [ ] Integration test: Python → Parquet → dbt → query

### 10.3 Epic 2: Multi-Year Projection System

- [ ] **E2-S1:** Aging curve derivation
  - [ ] `aging_curves.py`: Position-specific age curves from nflverse 2019-2024
  - [ ] Unit tests: RB cliff at Year 7, WR longevity to Year 10+, QB stable to Year 12+
- [ ] **E2-S2:** Opportunity trend analysis
  - [ ] `opportunity.py`: Usage trend adjustments (3-game, 5-game rolling averages)
  - [ ] Unit tests: Opportunity trends improve projection accuracy >5% MAE vs naive
- [ ] **E2-S3:** Multi-year projection engine
  - [ ] `multi_year.py`: Generate 2025-2029 projections
  - [ ] Unit tests: Projections for 500+ players, uncertainty increases with horizon
- [ ] **E2-S4:** Position-specific model tuning
  - [ ] Separate models for QB/RB/WR/TE with position-specific features
  - [ ] Unit tests: Position models outperform generic by >15% MAE
- [ ] **E2-S5:** Backtesting framework
  - [ ] TimeSeriesSplit validation (2020→2021, 2021→2022, 2022→2023)
  - [ ] Unit tests: \<20% MAE on 1-year ahead target achieved
- [ ] **E2-S6:** dbt mart: mrt_multi_year_projections
  - [ ] Create `mrt_multi_year_projections.sql`
  - [ ] Create `_mrt_multi_year_projections.yml` with tests
  - [ ] Verify queryable from notebooks
- [ ] **E2-S7:** Unit tests & validation
  - [ ] 80%+ coverage for projection engines
  - [ ] Backtesting validation passed

### 10.4 Epic 3: Cap Space Projection & Modeling

- [ ] **E3-S1:** Dead cap calculation engine
  - [ ] `dead_cap.py`: 50%/50%/25%/25%/25% schedule per league rules
  - [ ] Unit tests: 100% coverage, matches commissioner spreadsheet exactly
- [ ] **E3-S2:** Contract structure validator
  - [ ] `contracts.py`: Validate pro-rating constraints (150% geometric limits)
  - [ ] Unit tests: Catches illegal structures, allows legal structures
- [ ] **E3-S3:** Multi-year cap space projector
  - [ ] `scenarios.py`: Project 2025-2029 cap space
  - [ ] Unit tests: Shows $71M (2025-2026) → $158M (2027) → $250M (2029) progression
- [ ] **E3-S4:** Extension scenario modeling
  - [ ] Add extension scenario support
  - [ ] Unit tests: Extension scenarios quantify cap savings vs flexibility
- [ ] **E3-S5:** Contract efficiency benchmarking
  - [ ] Calculate $/WAR for all rostered players
  - [ ] Unit tests: Efficiency rankings intuitively correct, cut candidates actionable
- [ ] **E3-S6:** dbt mart: mrt_cap_scenarios
  - [ ] Create `mrt_cap_scenarios.sql`
  - [ ] Create `_mrt_cap_scenarios.yml` with tests
  - [ ] Verify queryable from notebooks
- [ ] **E3-S7:** Unit tests & validation
  - [ ] 100% coverage for cap modeling (deterministic, must be bug-free)
  - [ ] Edge case tests (5-year back-loaded, simultaneous cuts, traded cap)
- [ ] **E3-S8:** Commissioner validation
  - [ ] Cross-check cap projections vs commissioner spreadsheet
  - [ ] Unit tests: \<$5M error tolerance across all years

### 10.5 Epic 4: Dynasty Value Composite Score

- [ ] **E4-S1:** Variance component calculation
  - [ ] Calculate consistency ratings (std_dev / mean PPG)
  - [ ] Unit tests: High-variance = upside, low-variance = foundation
- [ ] **E4-S2:** Age component integration
  - [ ] Extract age-adjusted value from multi-year projections
  - [ ] Unit tests: 24-year-old valued higher than 29-year-old (same production)
- [ ] **E4-S3:** KTC market signal integration
  - [ ] Fetch KTC dynasty values via API
  - [ ] Unit tests: Weekly refresh, 500+ player coverage
- [ ] **E4-S4:** Composite score algorithm
  - [ ] `dynasty_value.py`: 6-factor composite (VoR 30%, economics 20%, age 20%, scarcity 15%, variance 10%, market 5%)
  - [ ] Unit tests: Top 100 players ranked in reasonable order
- [ ] **E4-S5:** Divergence analysis
  - [ ] Calculate delta (internal - KTC), flag arbitrage opportunities
  - [ ] Unit tests: ≥10 opportunities per week, top 20 manually reviewed for plausibility
- [ ] **E4-S6:** dbt mart: mrt_dynasty_value_composite
  - [ ] Create `mrt_dynasty_value_composite.sql`
  - [ ] Create `_mrt_dynasty_value_composite.yml` with tests
  - [ ] Verify queryable from notebooks
- [ ] **E4-S7:** Market calibration validation
  - [ ] Validate Spearman correlation with KTC (target: 0.6-0.8)
  - [ ] Unit tests: Top 20 divergences have plausible rationale
- [ ] **E4-S8:** Unit tests
  - [ ] 80%+ coverage for composite score logic

### 10.6 Epic 5: Integration & End-to-End Validation

- [ ] **E5-S1:** Parquet writer validation
  - [ ] Validate Python → Parquet → dbt source pattern
  - [ ] Integration test: Complete flow works (Prefect → Parquet → dbt → mart)
- [ ] **E5-S2:** dbt mart materialization
  - [ ] Create `src_analytics.yml` source definitions
  - [ ] Verify all 4 marts (`mrt_player_valuation`, `mrt_multi_year_projections`, `mrt_cap_scenarios`, `mrt_dynasty_value_composite`)
  - [ ] Integration test: `dbt run` succeeds, marts queryable
- [ ] **E5-S3:** dbt tests & documentation
  - [ ] Add grain uniqueness tests, not-null tests, FK tests
  - [ ] Column descriptions for all marts
  - [ ] Integration test: `dbt test` passes, `dbt docs generate` complete
- [ ] **E5-S4:** Analytics pipeline flow orchestration
  - [ ] Create `analytics_pipeline.py` main flow
  - [ ] Task dependencies properly chained (VoR → Projections → Cap → Composite → dbt)
  - [ ] Integration test: Single flow execution runs all tasks, Prefect UI shows task graph
- [ ] **E5-S5:** Integration testing
  - [ ] End-to-end test: Sample data → analytics → marts → query results
  - [ ] Integration test: Passes in CI/CD (future), runs locally
- [ ] **E5-S6:** Notebook consumption validation
  - [ ] Sample notebook consuming analytics marts
  - [ ] Integration test: Notebook runs without errors, visualizations render
- [ ] **E5-S7:** Performance optimization
  - [ ] Profile pipeline, optimize bottlenecks
  - [ ] Integration test: \<30 minute runtime end-to-end
- [ ] **E5-S8:** Backtesting flow & continuous validation
  - [ ] Create `backtesting.py` scheduled flow
  - [ ] TimeSeriesSplit validation, Discord alerts on regression
  - [ ] Integration test: Backtesting flow executes, Discord alert received, Prefect schedule active
- [ ] **E5-S9:** Documentation & README
  - [ ] Architecture diagram, usage instructions, validation results
  - [ ] Integration test: New user can run pipeline from README alone

______________________________________________________________________

## 11. Validation Results & Sign-Off

### 11.1 Coherence Checks

**✓ Decision Compatibility:**

- All technology versions verified current (2025-11-18)
- Python 3.13.6 compatible with Prefect 3.6.2, Polars 1.35.2, Pydantic 2.12.4, scikit-learn 1.7.2
- dbt-core 1.10.13 with dbt-duckdb 1.10.0 adapter compatible with DuckDB >=1.4.0
- All integrations align (external Parquet pattern, Pydantic → dbt schema alignment)

**✓ Epic Coverage:**

- All 5 epics mapped to architecture components
- Epic 0 → Prefect foundation (prerequisite for all)
- Epics 1-4 → Analytics modules + dbt marts
- Epic 5 → Integration validation + backtesting

**✓ Pattern Completeness:**

- Prefect-first pattern covers all analytics tasks
- Contract-first pattern covers all outputs (4 Pydantic schemas defined)
- Continuous backtesting pattern integrated (scheduled flow)
- External Parquet pattern extends existing staging approach

**✓ Integration Validation:**

- All existing dbt models identified and integration points documented
- No breaking changes to existing infrastructure
- New `data/analytics/` directory alongside existing `raw/`, `stage/`, `mart/`
- New `analytics` schema for external sources (non-invasive addition)

### 11.2 Architecture Completeness

**✓ All PRD Requirements Addressed:**

- Epic breakdown (Section 3.2)
- Technology stack with verified versions (Section 2.2)
- Novel patterns documented (Section 4)
- Cross-cutting concerns defined (Section 5)
- Project structure complete (Section 3.1)
- ADRs for key decisions (Section 8)

**✓ All Architectural Decisions Documented:**

- ADR-001: Prefect-First vs Post-MVP
- ADR-002: External Parquet vs DuckDB-First
- ADR-003: Contract-First Design with Pydantic
- ADR-004: Continuous Backtesting vs One-Time Validation

**✓ Implementation Patterns Defined:**

- Naming conventions (Python, Prefect, dbt, Parquet)
- Code organization (package structure, dbt layering)
- Error handling (fail fast, Prefect retries, Discord alerts)
- Logging (Python logging + Prefect structured logs)
- Testing (80%+ valuation, 100% cap modeling, dbt tests)

**✓ Consistency Rules for AI Agents:**

- 6 critical rules defined (Section 5.6)
- All outputs to `data/analytics/<model>/latest.parquet`
- All tasks decorated with `@task`
- All outputs validated against Pydantic schemas
- All dbt marts define `unique_key`
- 100% cap modeling test coverage
- TimeSeriesSplit validation mandatory

### 11.3 Document Quality

**✓ No Placeholder Text:**

- All sections filled with concrete details
- All decisions have verified versions (WebSearch 2025-11-18)
- All examples show actual code patterns
- All epic mappings complete

**✓ Version Column Specificity:**

- Python 3.13.6 (existing .python-version)
- Prefect 3.6.2 (verified 2025-11-18)
- Polars 1.35.2 (verified 2025-11-18)
- Pydantic 2.12.4 (verified 2025-11-18)
- scikit-learn 1.7.2 (verified 2025-11-18)
- All versions verified against latest stable releases

**✓ Source Tree Complete:**

- Detailed directory structure (Section 3.1)
- All new files/directories identified (NEW markers)
- All existing files preserved (no breaking changes)
- Epic mapping to code locations (Section 3.2)

______________________________________________________________________

## 12. Next Steps

**Architecture Complete ✅**

This architecture document provides the comprehensive technical blueprint for building the Analytics Infrastructure Platform. All architectural decisions are documented with ADRs, all integration points are identified, and all implementation patterns are defined for consistent AI-agent development.

**Recommended Next Workflow:** Implementation Readiness Validation

Run `/bmad:bmm:workflows:implementation-readiness` to validate that:

- PRD ✓ (complete)
- Architecture ✓ (this document)
- Epics + Stories (PRD Section 10 has breakdown, or run create-epics-and-stories)

**Then Proceed to Sprint Planning:**

Run `/bmad:bmm:workflows:sprint-planning` to:

- Extract epics/stories from PRD Section 10
- Create sprint status tracking file
- Begin Phase 4 implementation

**First Implementation Story:** Epic 0 Story 1 - Prefect Cloud workspace setup

______________________________________________________________________

_Generated by BMAD Decision Architecture Workflow v1.0 (YOLO Mode)_
_Date: 2025-11-18_
_For: Jason_
_Architecture Sign-Off: Winston (Architect Agent)_
