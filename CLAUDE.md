# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Fantasy Football Analytics data architecture project combining commissioner league data, NFL statistics, and market signals (dynasty format) using a batch-processing cloud-first stack. Primary consumers are Jupyter notebooks (local and Google Colab).

## Directory-Specific Guidance

For detailed context on specific areas, see:

- `dbt/ff_analytics/CLAUDE.md` - dbt modeling, testing, SQL style
- `tools/CLAUDE.md` - CLI utilities and workflows
- `scripts/CLAUDE.md` - Operational scripts by category
- `src/ingest/CLAUDE.md` - Provider integration patterns
- `.claude/skills/sprint-1-executor/` - Sprint 1 task execution skill

## Package Structure

- `src/ingest/` - Packaged ingestion modules (importable)
- `src/ff_analytics_utils/` - Shared utility functions

## Development Commands

### Python Environment

- **Package Manager**: UV (v0.8.8)
- **Python Version**: 3.13.6 (managed via .python-version)
- **dbt Version**: dbt-fusion 2.0.0-preview.32 (DuckDB adapter)

See `Makefile` for all targets: `make help`

## Key Components

| Component | Location | Purpose |
| --------------- | ------------------- | ----------------------------------------------------- |
| **Ingest** | `src/ingest/` | Provider data loaders (see `src/ingest/CLAUDE.md`) |
| **Tools** | `tools/` | CLI utilities (see `tools/CLAUDE.md`) |
| **Scripts** | `scripts/` | Operational runners (see `scripts/CLAUDE.md`) |
| **dbt Project** | `dbt/ff_analytics/` | Dimensional models (see `dbt/ff_analytics/CLAUDE.md`) |
| **Config** | `config/` | Projections, scoring rules |
| **Docs** | `docs/` | Specifications, architecture, guides |

## Data Layer Structure

- **Raw immutable snapshots**: `data/raw/<source>/<dataset>/dt=YYYY-MM-DD/`
- **Storage format**: Parquet with PyArrow, columnar optimized
- **Metadata**: Each load includes `_meta.json` with lineage
- **Cloud**: GCS (`gs://ff-analytics/{raw,stage,mart,ops}`)
- **Local dev**: Mirror cloud structure under `data/`

## Data Sources & Identity Resolution

| Source | Purpose | Authority |
| ------------------------- | -------------------------------- | -------------------- |
| Commissioner Google Sheet | League roster/contracts/picks | Authoritative |
| NFLverse/nflreadpy | NFL statistics | Primary stats source |
| FF Analytics | Projections | Fantasy projections source |
| Sleeper | League platform data | Integration |
| KTC | Dynasty valuations (1QB default) | Market signals |

**Entity Resolution**: Canonical player/team/franchise IDs via `dim_player_id_xref` crosswalk. See `docs/spec/kimball_modeling_guidance/kimbal_modeling.md` for patterns.

## Data Quality & Testing

- **Test framework**: `pytest` (`pytest -q`)
- **dbt tests**: Grain, referential integrity, freshness
- **Primary keys**: Defined in `src/ingest/<provider>/registry.py`
- **Idempotent**: All jobs retryable
- **Failure handling**: Last-known-good (LKG) pattern

**Debugging dbt Test Failures**:

When dbt tests fail (duplicates, relationship violations, etc.), **assume the issue is in our transformation code, not the source data**. Check in order:

1. Multiple snapshots being read (`dt=*` patterns without latest-only filtering)
2. Join logic creating many-to-many relationships
3. Missing deduplication (QUALIFY/DISTINCT) in staging models
4. Only after ruling out code issues should you inspect source data quality

## Critical Specifications

- Implementation details are documented in `docs/spec/`
- Most files are datestamped -- prefer the latest version when known
- Standalone sprints are documented in `docs/spec/sprint_<number>/`
- When in doubt, ask the user for guidance about the currently active plan
- See `docs/spec/kimball_modeling_guidance/kimbal_modeling.md` for dimensional modeling patterns for dbt
- See `docs/dev/repo_conventions_and_structure.md` for repo layout, naming, data paths

## Coding Conventions

- **Python**: PEP 8, 4-space indent, type hints; snake_case for modules/functions, PascalCase for classes
- **DataFrames**: Prefer Polars and PyArrow; write columnar Parquet
- **Notebooks**: Pattern `topic_action.ipynb`
- **Commits**: Conventional commits (`feat:`, `docs:`, `chore:`)

## Environment Variables & Security

- See `.env` for all environment variables
- **Security**: Never commit secrets; use repo secrets for CI
