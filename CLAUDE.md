# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Fantasy Football Analytics data architecture project combining commissioner league data, NFL statistics, and market signals (dynasty format) using a batch-processing cloud-first stack. Primary consumers are Jupyter notebooks (local and Google Colab).

## Directory-Specific Guidance

For detailed context on specific areas, see:

- `dbt/ff_data_transform/CLAUDE.md` - dbt modeling, testing, SQL style
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

See `justfile` for all targets: `just help` or `just --list`

### Running dbt Commands

**CRITICAL**: ALWAYS use `just` commands for dbt/duckdb operations. NEVER run `uv run dbt` commands directly.

#### Command Rules:

1. **Use `just` commands ONLY** - Never run `uv run dbt` directly
2. **Run from repo root** - All commands assume you're in `/Users/jason/code/ff_data_analytics`
3. **Never set environment variables manually** - The justfile handles `EXTERNAL_ROOT` and `DBT_DUCKDB_PATH` automatically
4. **Pass arguments after the command** - Example: `just dbt-run --select model_name`

#### Available Commands:

- `just dbt-run [args]` - Run dbt models
- `just dbt-test [args]` - Run dbt tests
- `just dbt-compile` - Validate SQL syntax
- `just dbt-seed [args]` - Load seed data
- `just dbt-xref` - Build player ID crosswalk

#### Why Use Just?

The justfile automatically:

- Sets `EXTERNAL_ROOT` to absolute path (`$PROJECT_ROOT/data/raw`)
- Sets `DBT_DUCKDB_PATH` to absolute path (`$PROJECT_ROOT/dbt/ff_data_transform/target/dev.duckdb`)
- Loads `.env` variables via `dotenv-load`
- Creates target directories if missing
- Uses correct project/profiles directories

#### Wrong vs Right:

❌ **WRONG - Never do this:**

```bash
# Don't manually set environment variables
EXTERNAL_ROOT="$(pwd)/data/raw" DBT_DUCKDB_PATH="..." uv run dbt run

# Don't cd into subdirectories
cd dbt/ff_data_transform && uv run dbt run

# Don't export variables manually
export EXTERNAL_ROOT="$(pwd)/data/raw" && uv run dbt run

# Don't use raw uv run dbt commands
uv run dbt run --project-dir dbt/ff_data_transform --profiles-dir dbt/ff_data_transform
```

✅ **RIGHT - Always do this:**

```bash
# Simple - from repo root
just dbt-run

# With model selection
just dbt-run --select stg_sheets__contracts_active

# Run tests
just dbt-test

# Compile only
just dbt-compile
```

## Key Components

| Component       | Location                 | Purpose                                                    |
| --------------- | ------------------------ | ---------------------------------------------------------- |
| **Ingest**      | `src/ingest/`            | Provider data loaders (see `src/ingest/CLAUDE.md`)         |
| **Tools**       | `tools/`                 | CLI utilities (see `tools/CLAUDE.md`)                      |
| **Scripts**     | `scripts/`               | Operational runners (see `scripts/CLAUDE.md`)              |
| **dbt Project** | `dbt/ff_data_transform/` | Dimensional models (see `dbt/ff_data_transform/CLAUDE.md`) |
| **Config**      | `config/`                | Projections, scoring rules                                 |
| **Docs**        | `docs/`                  | Specifications, architecture, guides                       |

## Data Layer Structure

- **Raw immutable snapshots**: `data/raw/<source>/<dataset>/dt=YYYY-MM-DD/`
- **Storage format**: Parquet with PyArrow, columnar optimized
- **Metadata**: Each load includes `_meta.json` with lineage
- **Cloud**: GCS (`gs://ff-analytics/{raw,stage,mart,ops}`)
- **Local dev**: Mirror cloud structure under `data/`

## Data Sources & Identity Resolution

| Source                    | Purpose                          | Authority                  |
| ------------------------- | -------------------------------- | -------------------------- |
| Commissioner Google Sheet | League roster/contracts/picks    | Authoritative              |
| NFLverse/nflreadpy        | NFL statistics                   | Primary stats source       |
| FF Analytics              | Projections                      | Fantasy projections source |
| Sleeper                   | League platform data             | Integration                |
| KTC                       | Dynasty valuations (1QB default) | Market signals             |

**Entity Resolution**: Canonical player/team/franchise IDs via `dim_player_id_xref` crosswalk. See `docs/spec/kimball_modeling_guidance/kimbal_modeling.md` for patterns.

## Data Quality & Testing

- **Test framework**: `pytest` (`pytest -q`)
- **dbt tests**: Grain, referential integrity, freshness
- **Primary keys**: Defined in `src/ingest/<provider>/registry.py`
- **Idempotent**: All jobs retryable
- **Failure handling**: Last-known-good (LKG) pattern

**Testing Mindset**:

- All test failures are your responsibility - broken windows theory applies
- Never delete a failing test; fix the underlying issue or discuss with user
- Tests must comprehensively cover functionality
- Test output must be pristine to pass - no unexpected errors in logs

**Debugging dbt Test Failures**:

When dbt tests fail, **assume the issue is in our transformation code, not the source data**. Use systematic debugging:

1. Read the test failure message completely
2. Check for multiple snapshots being read (`dt=*` patterns without latest-only filtering)
3. Check join logic creating many-to-many relationships
4. Check missing deduplication (QUALIFY/DISTINCT) in staging models
5. Only after ruling out code issues should you inspect source data quality

## Critical Specifications

- Implementation details are documented in `docs/spec/`
- Most files are datestamped -- prefer the latest version when known
- Standalone sprints are documented in `docs/spec/sprint_<number>/`
- When in doubt, ask the user for guidance about the currently active plan
- See `docs/spec/kimball_modeling_guidance/kimbal_modeling.md` for dimensional modeling patterns for dbt
- See `docs/dev/repo_conventions_and_structure.md` for repo layout, naming, data paths

## Coding Conventions

**Python**:

- Style: PEP 8, 4-space indent, type hints required
- Naming: snake_case for modules/functions, PascalCase for classes
- Avoid temporal names: No "new\_", "improved\_", "legacy\_" prefixes
- DataFrames: Prefer Polars and PyArrow; write columnar Parquet

**SQL/dbt**: See `dbt/ff_data_transform/CLAUDE.md` for comprehensive SQL style guide

**Notebooks**: Pattern `topic_action.ipynb` (e.g., `projections_analysis.ipynb`)

**Commits**: Conventional commits format (`feat:`, `fix:`, `docs:`, `chore:`)

- One logical change per commit
- Descriptive commit messages focusing on "why"

## Environment Variables & Security

- See `.env` for all environment variables
- **direnv support**: The project uses direnv with a `.envrc` file that automatically loads all `.env` variables when you `cd` into the project directory
- **Security**: Never commit secrets; use repo secrets for CI
