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

## Package Structure

- `src/ingest/` - Packaged ingestion modules (importable)
- `src/ff_analytics_utils/` - Shared utility functions

## Development Commands

### Python Environment

- **Package Manager**: UV (v0.8.8)
- **Python Version**: 3.13.6 (managed via .python-version)
- **dbt Version**: dbt-fusion 2.0.0-preview.32 (DuckDB adapter)
- **Setup**: `uv sync`
- **Add dependency**: `uv add <package>`
- **Run with uv**: `uv run python <script.py>`

### Quick Start

```bash
# 1. Setup
uv sync

# 2. Generate samples
make samples-nflverse

# 3. Run dbt models (uv-wrapped env)
make dbt-run  # uv run env ...

# 4. Test
make dbt-test  # uv run env ...
```

See `Makefile` for all targets: `make help`

## Current Implementation Status

Per SPEC-1 v2.3 (updated 2025-10-24):

- **Phase 1 Seeds**: ✅ Complete (6/8 seeds, 2 optional) - All tracks unblocked
  - dim_player_id_xref (12,133 players, 19 provider IDs)
  - dim_franchise, dim_pick, dim_scoring_rule, dim_timeframe, dim_name_alias
- **Track A (NFL Actuals)**: 95% Complete - nflverse → fact_player_stats → weekly marts ✅
- **Track B (League Data)**: 100% Complete - TRANSACTIONS → fact_league_transactions ✅
- **Track C (Market Data)**: 0% - KTC integration stub only
- **Track D (Projections)**: 100% Complete - FFanalytics → fact_player_projections → projection marts ✅

**Test Coverage**: 147/149 dbt tests passing (98.7%)

See implementation checklist for detailed status by component.

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
| Sleeper | League platform data | Integration |
| KTC | Dynasty valuations (1QB default) | Market signals |

**Entity Resolution**: Canonical player/team/franchise IDs via `dim_player_id_xref` crosswalk. See Kimball guide for patterns.

## Data Quality & Testing

- **Test framework**: `pytest` (`pytest -q`)
- **dbt tests**: Grain, referential integrity, freshness
- **Primary keys**: Defined in `src/ingest/<provider>/registry.py`
- **Idempotent**: All jobs retryable
- **Failure handling**: Last-known-good (LKG) pattern

## Critical Specifications

| Document | Purpose |
| ---------------------------------------------------------------- | --------------------------------------------------------------------- |
| `docs/spec/SPEC-1_v_2.2.md` | Complete data architecture (2×2 stat model, trade valuation, lineage) |
| `docs/architecture/kimball_modeling_guidance/kimbal_modeling.md` | Dimensional modeling patterns for dbt |
| `docs/dev/repo_conventions_and_structure.md` | Repo layout, naming, data paths |
| `docs/spec/SPEC-1_v_2.3_implementation_checklist_v_0.md` | Implementation status and sequencing (updated 2025-10-24) |

## Coding Conventions

- **Python**: PEP 8, 4-space indent, type hints; snake_case for modules/functions, PascalCase for classes
- **DataFrames**: Prefer Polars and PyArrow; write columnar Parquet
- **Notebooks**: Pattern `topic_action.ipynb`
- **Commits**: Conventional commits (`feat:`, `docs:`, `chore:`)

## Environment Variables & Security

Required in `.env` (see `.env.template`):

- `GOOGLE_APPLICATION_CREDENTIALS` or `GOOGLE_APPLICATION_CREDENTIALS_JSON`
- `SLEEPER_LEAGUE_ID`
- `COMMISSIONER_SHEET_ID`, `LEAGUE_SHEET_COPY_ID`
- `GCS_BUCKET` (for cloud operations)

**Security**: Never commit secrets; use repo secrets for CI
