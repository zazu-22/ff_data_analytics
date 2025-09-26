# WARP.md

This file provides guidance to AI agents in Warp terminal when working with this fantasy football data analytics repository.

## Project Overview

Fantasy Football Analytics data architecture project combining commissioner league data, NFL statistics, and market signals (dynasty format) using a batch-processing cloud-first stack. Primary consumers are Jupyter notebooks (local and Google Colab).

## Quick Start Commands

### Environment Setup

```bash
# Check Python version (should be 3.13.6)
python --version

# Install UV package manager if not present
pip install uv

# Setup project dependencies
uv sync

# Activate virtual environment
source .venv/bin/activate
```

### Common Development Tasks

#### Data Ingestion

```bash
# Load NFL player data for current season
uv run python -c "from ingest.shim import load_nflverse; print(load_nflverse('players', seasons=[2024], out_dir='data/raw/nflverse'))"

# Generate sample data for testing
uv run python tools/make_samples.py

# Run R-based projections
Rscript scripts/R/ffanalytics_run.R --config config/projections/ffanalytics_projections_config.yaml --scoring config/scoring/sleeper_scoring_rules.yaml
```

#### Jupyter Notebooks

```bash
# Start JupyterLab server
jupyter lab

# Key notebooks to explore:
# - notebooks/load_nflverse_data.ipynb
# - notebooks/keep_trade_cut_ingest.ipynb
# - notebooks/sheets_to_csv_gdrive.ipynb
```

#### Testing & Quality

```bash
# Run all tests
pytest -q

# Format code
uv run ruff format .

# Install pre-commit hooks
uv run pre-commit install
uv run pre-commit run --all-files
```

## Architecture Patterns

### Data Layer Structure

- **Raw immutable snapshots**: All source data preserved with timestamps (UTC)
- **Path pattern**: `data/raw/<source>/<dataset>/dt=YYYY-MM-DD/`
- **Storage format**: Parquet files optimized for analytics queries
- **Batch processing**: Twice daily at 08:00 and 16:00 UTC via GitHub Actions

### Key Components

- **`ingest/`**: Dataset registry and unified loader interface
- **`tools/`**: Developer utilities and sample generators
- **`scripts/R/`**: R-based data processing runners
- **`notebooks/`**: Jupyter notebooks for exploration and ETL
- **`config/`**: YAML configuration files
- **`docs/spec/`**: Architecture specifications (see SPEC-1_v_2.2.md)

## AI Agent Guidelines

### When Working with Data

1. **Always specify `out_dir`** explicitly to avoid writing to cloud buckets during testing
1. **Use Polars/PyArrow** for DataFrame operations, avoid pandas where possible
1. **Validate schemas** using primary keys defined in `ingest/registry.py`
1. **Generate samples** with `tools/make_samples.py` for development/testing

### Code Conventions

- **Python**: PEP 8, 4-space indent, type hints where practical
- **Naming**: snake_case for modules/functions, PascalCase for classes
- **Notebooks**: Use pattern `topic_action.ipynb`
- **Commits**: Use conventional commits (`feat:`, `docs:`, `chore:`, `init:`)

### Testing Approach

- **Framework**: pytest with `test_*.py` naming in `tests/` directory
- **Validation**: Check schema, primary keys, and non-null coverage
- **Fixtures**: Create small CSV/Parquet samples where feasible
- **Idempotency**: All operations should be retryable without corruption

### Security Considerations

- **Never commit** API keys, tokens, or credentials
- **Use `.env`** for local secrets, repo secrets for CI
- **Explicit paths** for data output to prevent accidental cloud writes

### Data Sources

1. **Commissioner Google Sheet**: Authoritative league data
1. **NFLverse/nflreadpy**: NFL statistics and player data
1. **Sleeper**: League platform data
1. **KTC**: Keep/Trade/Cut dynasty valuations
1. **Injuries**: Player availability data

### Common File Patterns

```bash
# Data files
ls data/raw/nflverse/players/dt=*/
ls data/raw/ktc/values/dt=*/

# Configuration
cat config/projections/ffanalytics_projections_config.yaml
cat config/scoring/sleeper_scoring_rules.yaml

# Documentation
cat docs/spec/SPEC-1_v_2.2.md
cat docs/dev/how_to_use_the_sample_generator_tools_make_samples.md
```

### Debugging & Troubleshooting

```bash
# Check data pipeline status
ls -la data/raw/*/

# Validate loader output
python -c "import polars as pl; df = pl.scan_parquet('data/raw/nflverse/players/dt=2024-*/'); print(df.collect().head())"

# Check environment
uv run python -c "import sys; print(sys.version)"
which python
```

### Working with Notebooks

- **Location**: All notebooks in `/notebooks/` directory
- **Kernel**: Use project's virtual environment kernel
- **Data paths**: Reference data with relative paths from repo root
- **Outputs**: Save analysis results to appropriate `data/processed/` subdirs

## Environment Variables

Required in `.env` file:

- Google API credentials for Sheets access
- Sleeper API keys (if applicable)
- Discord webhook for notifications (optional)

## CI/CD Integration

- **GitHub Actions**: `.github/workflows/data-pipeline.yml`
- **Schedule**: Monday 08:00 UTC (NFLverse), Tuesday 08:00 UTC (projections)
- **Manual triggers**: Via workflow_dispatch

## Related Documentation

- `README.md`: Basic project information
- `CLAUDE.md`: Detailed Claude Code guidance
- `AGENTS.md`: Repository guidelines for AI agents
- `docs/spec/SPEC-1_v_2.2.md`: Complete architecture specification
