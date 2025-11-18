# Data Models Documentation

**Project:** Fantasy Football Data Analytics Platform
**Database:** DuckDB (OLAP, external Parquet tables)
**Modeling Approach:** Kimball Dimensional Modeling
**Generated:** 2025-11-18

______________________________________________________________________

## Overview

The data architecture follows **Kimball dimensional modeling** principles with a layered ELT approach:

- **Extract**: Python modules ingest data from multiple providers (NFL statistics, projections, commissioner data, market signals)
- **Load**: Raw data stored as Parquet files in `data/raw/` (local) and GCS (cloud)
- **Transform**: dbt models transform data through staged layers

______________________________________________________________________

## dbt Model Layers

### Transformation Pipeline

```
Raw Data (Parquet)
    ↓
Staging Models (13 models)
  - Normalize provider-specific schemas
  - Apply data type conversions
  - Basic filtering and renaming
    ↓
Core Models (23 models: 13 base + 10 intermediate)
  - Facts: Player stats, projections, transactions
  - Dimensions: Players, teams, franchises, contracts, picks
  - Intermediate: Complex transformations, grain changes
    ↓
Marts (12 models)
  - Analytics-ready datasets
  - 2×2 model: (actuals/projections) × (real-world/fantasy)
  - Business logic applied (scoring rules, valuations)
```

### Model Counts by Layer

| Layer            | Model Count | Purpose                          |
| ---------------- | ----------- | -------------------------------- |
| **Staging**      | 13          | Provider-specific normalization  |
| **Core**         | 13          | Reusable facts and dimensions    |
| **Intermediate** | 10          | Complex transformations          |
| **Marts**        | 12          | Analytics-ready datasets         |
| **Total**        | **48**      | Complete transformation pipeline |

______________________________________________________________________

## Kimball Dimensional Model Components

### Facts (Core Layer)

Facts capture measurable events and metrics:

- **Player Statistics**: Game-level performance data (88 stat types, 6.3M rows)
- **Player Projections**: Weekly/season forecasts (13 stat types)
- **League Transactions**: Roster moves, trades, free agent acquisitions
- **Contract Snapshots**: Historical contract state over time

**Grain**: One row per player per game (stats) or player per week (projections)

### Dimensions (Core Layer)

Dimensions provide context and enable slicing:

- **dim_player**: Canonical player master (identity resolution via crosswalk)
- **dim_team**: NFL teams
- **dim_franchise**: Dynasty league franchises
- **dim_schedule**: NFL game schedule
- **dim_asset**: Draft picks and player valuations
- **dim_contract**: Contract terms and rules
- **dim_scoring_rule**: Fantasy scoring configuration

**Conformed Dimensions**: All facts reference the same dimension tables (e.g., `dim_player`)

### Intermediate Models (10 models)

Complex transformations between staging and core:

- Pick identity resolution
- Contract history assembly
- Player attribute enrichment
- Grain transformations

______________________________________________________________________

## 2×2 Analytics Framework (ADR-007)

The project implements a **2×2 model** for player performance analysis:

```
                 Real-World Stats              Fantasy Points
                 ────────────────              ──────────────
Actuals          fct_player_stats        →    mrt_fantasy_actuals_weekly
                 (per-game grain)              (apply dim_scoring_rule)

Projections      fct_player_projections  →    mrt_fantasy_projections
                 (weekly/season grain)         (apply dim_scoring_rule)
```

**Key Design Decision**: Actuals and projections use **separate fact tables** because:

- Actuals have per-game grain with `game_id` (required for NFL analysis)
- Projections have weekly/season grain with `horizon` (no meaningful game_id)
- Unified table would require nullable composite keys (anti-pattern)

**Analytics Marts**:

- **Real-world**: `mrt_real_world_actuals_weekly`, `mrt_real_world_projections`
- **Fantasy**: `mrt_fantasy_actuals_weekly`, `mrt_fantasy_projections`
- **Variance**: `mrt_projection_variance` (actuals vs projections)

______________________________________________________________________

## Data Identity Resolution

### Player Identity (ADR-010, ADR-011)

**Challenge**: Multiple data sources use different player identifiers

**Solution**: Crosswalk seed `dim_player_id_xref` maps:

- MFL ID (canonical) ←→ gsis_id (nflverse) ←→ sleeper_id ←→ player_name

**Surrogate Key**: Sequential `player_id` (-1 for unmapped players)

**player_key Pattern**: Fallback identity using raw provider IDs when crosswalk mapping unavailable

### Pick Identity (ADR-014)

**Challenge**: Draft picks traded across seasons need stable identity

**Solution**: Use `overall_pick_number` as natural key (1-432 for 12-team league)

- Overall pick number is immutable across trades
- Resolved via registry seed combining draft history + future projections

______________________________________________________________________

## Reference Data (Seeds)

17 CSV seed files provide reference data:

- **Identity Resolution**: `dim_player_id_xref`, `dim_team_xref`, `dim_franchise_mapping`
- **Pick Registry**: `dim_pick_registry` (overall pick numbers 1-432)
- **Scoring Rules**: Fantasy scoring configuration
- **Contract Rules**: Cap rules, roster limits

______________________________________________________________________

## Data Quality & Testing

### Test Strategy

| Test Type                       | Purpose                 | Count          |
| ------------------------------- | ----------------------- | -------------- |
| `not_null`                      | Key fields populated    | Extensive      |
| `unique`                        | Surrogate keys unique   | All dimensions |
| `relationships`                 | Foreign keys valid      | All fact FKs   |
| `unique_combination_of_columns` | Grain enforcement       | All facts      |
| `accepted_values`               | Controlled vocabularies | Enums, flags   |

**Grain Enforcement**: Every fact table has a grain uniqueness test

**Foreign Key Integrity**: All dimension references validated via `relationships` tests

______________________________________________________________________

## Storage Strategy

### External Parquet Tables

- **Materialization**: All large models use external Parquet (`external=true`)
- **DuckDB Catalog**: In-memory schema only (no data in .duckdb file)
- **Data Location**:
  - Local: `data/raw/`, `data/stage/`, `data/mart/`
  - Cloud: `gs://ff-analytics/{raw,stage,mart}`
- **Partitioning**: Season/week for time-series data

### Benefits

- Columnar compression (10x+ space savings)
- Fast analytical queries (OLAP-optimized)
- Separation of catalog and data (portable, cloud-ready)
- Interoperability with Polars, Pandas, PyArrow

______________________________________________________________________

## Data Lineage

```
Provider APIs (nflverse, ffanalytics, Sleeper, KTC, Google Sheets)
    ↓
Python Ingestion (src/ingest/)
    ↓
Raw Parquet (data/raw/<provider>/<dataset>/dt=YYYY-MM-DD/)
    ↓
dbt Staging Models (stg_<provider>__<dataset>)
    ↓
dbt Core Models (fct_*, dim_*)
    ↓
dbt Marts (mrt_*)
    ↓
Analysis (Jupyter notebooks)
```

**Metadata**: Each ingestion includes `_meta.json` with lineage info

**Idempotency**: All jobs retryable (overwrite with latest)

**Freshness**: Tracked via dbt freshness tests

______________________________________________________________________

## Model Naming Conventions

| Prefix                      | Layer        | Example                                       |
| --------------------------- | ------------ | --------------------------------------------- |
| `stg_<provider>__<dataset>` | Staging      | `stg_nflverse__player_stats`                  |
| `dim_<entity>`              | Dimension    | `dim_player`, `dim_team`                      |
| `fct_<process>`             | Fact         | `fct_player_stats`, `fct_league_transactions` |
| `int_<description>`         | Intermediate | `int_pick_comp_registry`                      |
| `mrt_<name>`                | Mart         | `mrt_fantasy_actuals_weekly`                  |

**Note**: Uses `fct_` not `fact_`, `mrt_` not `mart_` (dbt-opiner compliance)

______________________________________________________________________

## Architecture Decisions

**Key ADRs**:

- **ADR-007**: Separate fact tables for actuals vs projections (grain incompatibility)
- **ADR-009**: Single consolidated fact table for NFL stats (88 stat types, long format)
- **ADR-010**: MFL ID as canonical player identity
- **ADR-011**: Sequential surrogate player_id with -1 for unmapped
- **ADR-014**: Pick identity resolution via overall pick number

______________________________________________________________________

## Data Refresh Strategy

- **NFL Statistics**: Weekly during season, historical backfill
- **Projections**: Weekly updates from ffanalytics
- **Commissioner Data**: Manual Google Sheets updates (automated ingestion)
- **Market Signals**: Daily KTC valuations (1QB default)
- **Sleeper League**: Real-time sync via WebSocket API

**Orchestration**: GitHub Actions workflows + manual `just` commands
