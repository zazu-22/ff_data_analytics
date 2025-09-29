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
- Top-level `ingest/` - Legacy location (deprecated, use `src/ingest/`)

## Development Commands

### Python Environment

- **Package Manager**: UV (v0.8.8)
- **Python Version**: 3.13.6 (managed via .python-version)
- **Setup**: `uv sync`
- **Add dependency**: `uv add <package>`
- **Run with uv**: `uv run python <script.py>`

### Quick Start

```bash
# 1. Setup
uv sync

# 2. Generate samples
make samples-nflverse

# 3. Run dbt models
make dbt-run

# 4. Test
make dbt-test
```

See `Makefile` for all targets: `make help`

## Key Components

| Component       | Location            | Purpose                                               |
| --------------- | ------------------- | ----------------------------------------------------- |
| **Ingest**      | `src/ingest/`       | Provider data loaders (see `src/ingest/CLAUDE.md`)    |
| **Tools**       | `tools/`            | CLI utilities (see `tools/CLAUDE.md`)                 |
| **Scripts**     | `scripts/`          | Operational runners (see `scripts/CLAUDE.md`)         |
| **dbt Project** | `dbt/ff_analytics/` | Dimensional models (see `dbt/ff_analytics/CLAUDE.md`) |
| **Config**      | `config/`           | Projections, scoring rules                            |
| **Docs**        | `docs/`             | Specifications, architecture, guides                  |

## Data Layer Structure

- **Raw immutable snapshots**: `data/raw/<source>/<dataset>/dt=YYYY-MM-DD/`
- **Storage format**: Parquet with PyArrow, columnar optimized
- **Metadata**: Each load includes `_meta.json` with lineage
- **Cloud**: GCS (`gs://ff-analytics/{raw,stage,mart,ops}`)
- **Local dev**: Mirror cloud structure under `data/`

## Data Sources & Identity Resolution

| Source                    | Purpose                          | Authority            |
| ------------------------- | -------------------------------- | -------------------- |
| Commissioner Google Sheet | League roster/contracts/picks    | Authoritative        |
| NFLverse/nflreadpy        | NFL statistics                   | Primary stats source |
| Sleeper                   | League platform data             | Integration          |
| KTC                       | Dynasty valuations (1QB default) | Market signals       |

**Entity Resolution**: Canonical player/team/franchise IDs via `dim_player_id_xref` crosswalk. See Kimball guide for patterns.

## Data Quality & Testing

- **Test framework**: `pytest` (`pytest -q`)
- **dbt tests**: Grain, referential integrity, freshness
- **Primary keys**: Defined in `src/ingest/<provider>/registry.py`
- **Idempotent**: All jobs retryable
- **Failure handling**: Last-known-good (LKG) pattern

## Critical Specifications

| Document                                                         | Purpose                                                               |
| ---------------------------------------------------------------- | --------------------------------------------------------------------- |
| `docs/spec/SPEC-1_v_2.2.md`                                      | Complete data architecture (2×2 stat model, trade valuation, lineage) |
| `docs/architecture/kimball_modeling_guidance/kimbal_modeling.md` | Dimensional modeling patterns for dbt                                 |
| `docs/dev/repo_conventions_and_structure.md`                     | Repo layout, naming, data paths                                       |
| `docs/spec/SPEC-1_v_2.2_implementation_checklist_v_1.md`         | Implementation status and sequencing                                  |

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
