# Project Documentation Index

**Fantasy Football Data Analytics Platform**

**Generated:** 2025-11-18
**Workflow:** document-project v1.2.0 (Deep Scan)

______________________________________________________________________

## Project Overview

- **Type:** Monolith (Data Analytics/Engineering Pipeline)
- **Primary Language:** Python 3.13
- **Architecture:** ELT Data Pipeline with Kimball Dimensional Modeling
- **Database:** DuckDB (OLAP, external Parquet tables)

______________________________________________________________________

## Quick Reference

| Category            | Technology              | Version  |
| ------------------- | ----------------------- | -------- |
| **Language**        | Python                  | 3.13     |
| **Package Manager** | uv                      | Latest   |
| **Database**        | DuckDB                  | >=1.4.0  |
| **Transform**       | dbt                     | >=1.10.6 |
| **Data Processing** | Polars, Pandas, PyArrow | Latest   |
| **Cloud Storage**   | Google Cloud Storage    | >=3.4.0  |
| **Notebooks**       | Jupyter, Marimo         | Latest   |
| **Task Runner**     | just, Make              | -        |

**Architecture Pattern:** ELT Pipeline (Extract → Load → Transform)

- **Staging** → **Core** (Facts & Dimensions) → **Marts** (Analytics-ready)
- **Storage:** External Parquet files, DuckDB catalog
- **Modeling:** Kimball dimensional modeling

______________________________________________________________________

## Generated Documentation

### Data Architecture

- **[Data Models](./data-models-main.md)** - Complete data architecture (48 dbt models, Kimball dimensions & facts)

###Core Documentation

- [Project Overview](./project-overview.md) _(To be generated)_
- [Architecture Document](./architecture-main.md) _(To be generated)_
- [Source Tree Analysis](./source-tree-analysis.md) _(To be generated)_
- [Development Guide](./development-guide.md) _(To be generated)_
- [Deployment Guide](./deployment-guide.md) _(To be generated)_

______________________________________________________________________

## Existing Project Documentation

### Project-Level

- [README.md](../README.md) - Project overview
- [CLAUDE.md](../CLAUDE.md) - AI assistant context (project-level)
- [AGENTS.md](../AGENTS.md) - AI agents documentation

### Component-Specific Context

- [dbt Project CLAUDE.md](../dbt/ff_data_transform/CLAUDE.md) - dbt project context, SQL style guide, model patterns
- [Ingestion CLAUDE.md](../src/ingest/CLAUDE.md) - Data provider integration patterns
- [Scripts CLAUDE.md](../scripts/CLAUDE.md) - Operational scripts guide
- [Tools CLAUDE.md](../tools/CLAUDE.md) - CLI utilities
- [R Scripts CLAUDE.md](../scripts/R/CLAUDE.md) - R analysis scripts

### Component READMEs

- [Config README](../config/README.md) - Configuration management
- [dbt README](../dbt/ff_data_transform/README.md) - dbt project overview
- **dbt Model Layers:**
  - [Staging README](../dbt/ff_data_transform/models/staging/README.md) - Staging layer patterns
  - [Core README](../dbt/ff_data_transform/models/core/README.md) - Facts & dimensions
  - [Marts README](../dbt/ff_data_transform/models/marts/README.md) - Analytics marts
  - [Ops README](../dbt/ff_data_transform/models/ops/README.md) - Data quality & lineage
- [Seeds README](../dbt/ff_data_transform/seeds/README.md) - Reference data
- [Macros README](../dbt/ff_data_transform/macros/README.md) - SQL macros
- [Setup Scripts README](../scripts/setup/README.md) - Environment setup
- [Performance README](../scripts/performance/README.md) - Performance monitoring

### Architecture Decision Records (ADRs)

Located in `docs/adr/`:

- **ADR-004**: GitHub Actions for Sheets ingestion
- **ADR-005**: Commissioner sheet ingestion strategy
- **ADR-006**: GCS integration strategy
- **ADR-007**: Separate fact tables for actuals vs projections (2×2 model)
- **ADR-008**: League transaction history integration
- **ADR-009**: Single consolidated fact table for NFL stats
- **ADR-010**: MFL ID as canonical player identity
- **ADR-011**: Sequential surrogate player_id & League rules dimensional framework
- **ADR-012**: Name/position normalization for IDP
- **ADR-013**: FantasySharks IDP single-source dependency
- **ADR-014**: Pick identity resolution via overall pick number

### Specifications & Planning

- **[SPEC-1 v2.2](../docs/spec/SPEC-1_v_2.2.md)** - Main product specification
- **[SPEC-1 Implementation Checklist](../docs/spec/SPEC-1_v_2.3_implementation_checklist_v_0.md)** - Implementation tracking
- **[Kimball Modeling Guide](../docs/spec/kimball_modeling_guidance/kimbal_modeling.md)** - Dimensional modeling patterns
- **[Sprint 1 Plan](../docs/spec/sprint_1/00_SPRINT_PLAN.md)** - Sprint 1 overview (13 tasks)

### Code Review & Assessments

Located in `docs/reviews/`:

- **[Comprehensive Review Report](../docs/reviews/COMPREHENSIVE_REVIEW_REPORT.md)** - Overall review summary
- **[Security Audit Report](../docs/reviews/SECURITY_AUDIT_REPORT.md)** - Security assessment
- **[Performance Analysis Report](../docs/reviews/PERFORMANCE_ANALYSIS_REPORT.md)** - Performance review
- **[CI/CD & DevOps Assessment](../docs/reviews/CICD_DEVOPS_ASSESSMENT.md)** - CI/CD evaluation
- **[CI/CD Assessment Files](../docs/reviews/CI_CD_ASSESSMENT_FILES.md)** - Specific file reviews
- **[Documentation Review Phase 3](../docs/reviews/DOCUMENTATION_REVIEW_PHASE_3.md)** - Documentation quality assessment

### Investigation Reports

Located in `docs/investigations/` and `docs/findings/`:

- **IDP Data Investigation** (8 documents) - IDP stats source analysis
- **dim_pick Rebuild** (8 documents) - Pick identity resolution implementation
- **Sleeper Database Audit** - Sleeper API data structure analysis
- **Root Cause Analyses** - Various technical investigations

### Implementation Tickets

Located in `docs/implementation/multi_source_snapshot_governance/tickets/`:

- **P1-P6 Priority Tickets** - Multi-source snapshot governance implementation
- **CC Tickets** - Cross-cutting concerns (comparison testing, notebook audit)

______________________________________________________________________

## Getting Started

### For AI-Assisted Development

1. **Start here**: Read this index to understand project structure
2. **For brownfield PRD**: Reference [data-models-main.md](./data-models-main.md) for complete data architecture
3. **For context**: Check component-specific CLAUDE.md files for detailed guidance
4. **For decisions**: Review ADRs for architectural rationale

### For dbt Development

1. **Read**: [dbt/ff_data_transform/CLAUDE.md](../dbt/ff_data_transform/CLAUDE.md) - Complete dbt guide
2. **Commands**: Use `just dbt-run`, `just dbt-test`, `just dbt-compile` (NEVER manual `uv run dbt`)
3. **Modeling**: Follow [Kimball Modeling Guide](../docs/spec/kimball_modeling_guidance/kimbal_modeling.md)
4. **Style**: SQL style enforced by sqlfmt, sqlfluff, and dbt-opiner (see pre-commit hooks)

### For Data Ingestion

1. **Read**: [src/ingest/CLAUDE.md](../src/ingest/CLAUDE.md) - Provider integration patterns
2. **Add Source**: Create provider module in `src/ingest/<provider>/`
3. **Registry**: Define schema in `registry.py` with primary keys
4. **Staging**: Create dbt staging model `stg_<provider>__<dataset>.sql`

### Development Workflow

```bash
# Setup (first time)
uv sync                    # Install dependencies
just dbt-seed              # Load reference data

# Daily workflow
just dbt-run               # Run transformations
just dbt-test              # Run data quality tests
just dbt-compile           # Validate SQL syntax

# Quality checks
just quality-sql           # Run all SQL quality checks (format, lint, validate, dbt-opiner)
just lint                  # Python linting
just typecheck             # Type checking

# CI/CD
# Pre-commit hooks run automatically on commit (sqlfmt, sqlfluff, dbt-compile, dbt-opiner)
```

### Key Commands

See `justfile` for all commands: `just --list`

______________________________________________________________________

## Project Structure

```
ff_data_analytics/
├── src/
│   ├── ingest/              # Provider data ingestion modules
│   └── ff_analytics_utils/  # Shared utilities
├── dbt/ff_data_transform/   # dbt transformation project
│   ├── models/
│   │   ├── staging/         # 13 staging models (provider normalization)
│   │   ├── core/            # 23 core models (facts & dimensions)
│   │   └── marts/           # 12 mart models (analytics-ready)
│   ├── seeds/               # 17 reference data CSV files
│   └── macros/              # SQL macros and functions
├── scripts/                 # Operational scripts
│   ├── ingest/              # Ingestion runners
│   ├── seeds/               # Seed generation
│   ├── setup/               # Environment setup
│   └── R/                   # R analysis scripts
├── notebooks/               # Jupyter/Marimo analysis notebooks
├── data/                    # Data storage (Parquet files)
│   ├── raw/                 # Provider-specific raw data
│   ├── stage/               # Intermediate staging
│   ├── mart/                # Analytics marts
│   └── ops/                 # Operational metadata
├── config/                  # Configuration files
│   ├── projections/         # Projection configuration
│   ├── scoring/             # Fantasy scoring rules
│   └── gcs/                 # GCS bucket configuration
├── docs/                    # Technical documentation
│   ├── adr/                 # Architecture decisions (14 ADRs)
│   ├── spec/                # Specifications & planning
│   ├── reviews/             # Code review reports (6 reports)
│   ├── investigations/      # Technical investigations
│   ├── findings/            # Research findings
│   └── implementation/      # Implementation tickets
├── tests/                   # Python unit tests
├── tools/                   # CLI utilities
└── .github/workflows/       # CI/CD pipelines (2 workflows)
```

______________________________________________________________________

## Data Flow

```
Provider APIs
  ↓
Python Ingestion (src/ingest/)
  ↓
Raw Parquet (data/raw/<provider>/<dataset>/dt=YYYY-MM-DD/)
  ↓
dbt Staging (stg_<provider>__<dataset>)
  ↓
dbt Core (fct_*, dim_*)
  ↓
dbt Marts (mrt_*)
  ↓
Analysis (Jupyter/Marimo notebooks)
```

______________________________________________________________________

## Key Concepts

### Kimball Dimensional Modeling

- **Facts**: Measurable events (player stats, projections, transactions)
- **Dimensions**: Context (players, teams, franchises, contracts, picks)
- **Conformed Dimensions**: Single version of truth (e.g., dim_player)
- **Grain**: Explicitly declared and tested for every fact table

### 2×2 Analytics Model (ADR-007)

```
                 Real-World              Fantasy
Actuals          fct_player_stats    →   mrt_fantasy_actuals_weekly
Projections      fct_player_projections → mrt_fantasy_projections
```

### Identity Resolution

- **Players**: MFL ID (canonical) via crosswalk seed
- **Teams**: Standardized NFL team IDs
- **Franchises**: Dynasty league franchise mapping
- **Picks**: Overall pick number (1-432 for 12-team league)

### Data Quality

- **Grain Tests**: `unique_combination_of_columns` on all facts
- **FK Tests**: `relationships` on all dimension references
- **Not Null**: Required on all key fields
- **Freshness**: Source data recency checks

______________________________________________________________________

## Next Steps

1. **For new features**: Start with brownfield PRD workflow, reference this documentation
2. **For data modeling**: Read [Kimball guide](../docs/spec/kimball_modeling_guidance/kimbal_modeling.md) and [dbt CLAUDE.md](../dbt/ff_data_transform/CLAUDE.md)
3. **For code quality**: Review [comprehensive review report](../docs/reviews/COMPREHENSIVE_REVIEW_REPORT.md)
4. **For architecture decisions**: Check relevant ADRs in `docs/adr/`

______________________________________________________________________

**Documentation Workflow Status:** Initial deep scan complete (Steps 1-4)

**Missing Detailed Docs**: Some detailed documentation marked as _(To be generated)_ can be completed via the document-project workflow deep-dive mode if needed.
