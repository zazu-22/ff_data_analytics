# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Fantasy Football Analytics data architecture project combining commissioner league data, NFL statistics, and market signals (dynasty format) using a batch-processing cloud-first stack. Primary consumers are Jupyter notebooks (local and Google Colab).

## Development Commands

### Python Environment

- **Package Manager**: UV (v0.8.8)
- **Python Version**: 3.13.6 (managed via .python-version)
- **Setup & Install dependencies**: `uv sync` (creates venv and installs from pyproject.toml)
- **Add new dependency**: `uv add <package>` (e.g., `uv add pandas`)
- **Activate virtual environment**: `source .venv/bin/activate`
- **Run with uv**: `uv run python -c "from ingest.shim import load_nflverse; print(load_nflverse('players', seasons=[2024], out_dir='data/raw/nflverse'))"`

### Jupyter Notebooks

- **Start JupyterLab**: `jupyter lab`
- **Primary notebooks location**: `/notebooks/`
  - `load_nflverse_data.ipynb` - NFL data loading via nflreadpy
  - `keep_trade_cut_ingest.ipynb` - KTC dynasty valuations
  - `sheets_to_csv_gdrive.ipynb` - Google Sheets commissioner data

### R Scripts

- **FFAnalytics projections**: `Rscript scripts/R/ffanalytics_run.R --config config/projections/ffanalytics_projections_config.yaml --scoring config/scoring/sleeper_scoring_rules.yaml`
- **NFLverse data load**: `Rscript scripts/R/nflverse_load.R`

## Architecture Decisions

### Data Layer Structure

- **Raw immutable snapshots**: All source data preserved with timestamps (UTC) for time-travel/backfill
- **Data path pattern**: `data/raw/<source>/<dataset>/dt=YYYY-MM-DD/` (e.g., `data/raw/nflverse/players/dt=2024-09-24/`)
- **Batch processing schedule**: Twice daily at 08:00 and 16:00 UTC via GitHub Actions
- **Storage format**: Parquet files optimized for analytics queries, columnar format with PyArrow
- **Schema-on-read**: Flexible data exploration without rigid schemas

### Key Components

**Ingest Layer** (`/ingest/`)

- `registry.py`: Dataset specifications mapping logical names to loaders (nflreadpy/nflreadr)
- `shim.py`: Unified loader interface between Python and R implementations

**Configuration** (`/config/`)

- `projections/ffanalytics_projections_config.yaml`: FFAnalytics projection settings
- `scoring/sleeper_scoring_rules.yaml`: League-specific scoring rules

**GitHub Actions** (`.github/workflows/data-pipeline.yml`)

- Monday 08:00 UTC: NFLverse weekly data update
- Tuesday 08:00 UTC: FFAnalytics projections update
- Manual triggers via workflow_dispatch

### Data Sources & Identity Resolution

**Core Sources**:

1. Commissioner Google Sheet (authoritative league data)
1. NFLverse/nflreadpy (NFL statistics and player data)
1. Sleeper (league platform data)
1. KTC (Keep/Trade/Cut dynasty valuations, 1QB default)
1. Injuries and depth charts

**Entity Resolution**: Canonical player/team/franchise IDs resolved across providers using staging guards and alias mapping.

## Data Quality & Testing

- **Test framework**: `pytest` with test files in `tests/` directory following `test_*.py` naming
- **Run tests**: `pytest -q` (add fixtures for small CSV/Parquet samples where feasible)
- **Primary keys enforcement**: Each dataset in registry.py defines unique keys for validation
- **Loader validation**: Verify schema/keys and non-null key coverage
- **Idempotent operations**: All ingestion jobs are retryable without data corruption
- **Failure handling**: Last-known-good (LKG) pattern for resilience

## Critical Specifications

Refer to `/docs/spec/SPEC-1_v_2.2.md` for the complete data architecture specification including:

- 2×2 stat model (actual vs projected × real-world vs fantasy)
- Trade valuation system for players + draft picks
- Data lineage and metadata tracking
- Schema evolution strategy
- Security and IAM requirements

## Working with Sample Data

Use the sample generator tool for development/testing:

- `python tools/make_samples.py`
- See `/docs/dev/how_to_use_the_sample_generator_tools_make_samples.md` for detailed usage

## Coding Conventions

- **Python**: PEP 8, 4-space indent, type hints where practical; snake_case for modules/functions, PascalCase for classes
- **DataFrames**: Prefer Polars and PyArrow; write columnar Parquet; avoid implicit type casts
- **Notebooks**: Name with pattern `topic_action.ipynb` (e.g., `load_nflverse_data.ipynb`)
- **Commits**: Use conventional commits (`feat:`, `docs:`, `chore:`, `init:`)
  - Example: `feat: add nflverse weekly loader with Parquet output`

## Environment Variables & Security

Required in `.env`:

- Google API credentials for Sheets access
- Sleeper API keys (if applicable)
- Discord webhook for notifications (optional)

**Security notes**:

- Never commit keys/tokens; use repo secrets for CI
- Make `out_dir` explicit for local runs; avoid writing to cloud buckets during tests
