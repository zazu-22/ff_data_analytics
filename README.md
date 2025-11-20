# FF Analytics — Data Architecture & Analytics

[![Spec](https://img.shields.io/badge/SPEC-v2.2-brightgreen)](docs/spec/SPEC-1_v_2.2.md)
[![Conventions](https://img.shields.io/badge/Conventions-Repo%20Structure-blue)](docs/dev/repo_conventions_and_structure.md)
[![Data Pipeline CI](https://img.shields.io/badge/CI-Data%20Pipeline-lightgrey)](.github/workflows/data-pipeline.yml)

## Quick Links

- SPEC: docs/spec/SPEC-1_v_2.2.md
- Conventions & Structure: docs/dev/repo_conventions_and_structure.md
- Kimball Dimensional Modeling Guide: docs/architecture/kimball_modeling_guidance/kimbal_modeling.md
- Sample Generator Guide: docs/dev/how_to_use_the_sample_generator_tools_make_samples.md
- Polars DataFrame Patterns: docs/dev/polars_dataframes.md
- dbt Project Overview: dbt/ff_data_transform/README.md
- Staging Norms: dbt/ff_data_transform/models/staging/README.md
- CI: .github/workflows/data-pipeline.yml, .github/workflows/ingest_google_sheets.yml
- Projections Config: config/projections/ffanalytics_projections_config.yaml
- Scoring Rules (Sleeper): config/scoring/sleeper_scoring_rules.yaml

## Getting Started

- Python: `pip install uv && uv sync`
- R: see `scripts/R/` for runners and `renv.lock` for pins
- Generate samples: `uv run python tools/make_samples.py`

### Prefect Cloud Workspace Setup

**Workspace:** `ff-analytics`
**Dashboard:** [https://app.prefect.cloud](https://app.prefect.cloud)

1. Install Prefect: `uv add prefect` (already in pyproject.toml)
2. Authenticate: `uv run prefect cloud login` (interactive)
3. Add API key to `.env` file: `PREFECT_API_KEY=<your-key>`
4. Verify setup: `uv run python flows/test_workspace_setup.py`

**Required Environment Variables:**

- `PREFECT_API_KEY` — API key from Prefect Cloud (stored in `.env`, auto-loaded via direnv)

## Repo Structure (high level)

- `ingest/` — provider shims/loaders (execution code)
- `src/ff_analytics_utils/` — reusable helpers (library code)
- `scripts/` — operational scripts (R runners, ingest, troubleshooting)
- `tools/` — developer utilities (sample generator)
- `flows/` — Prefect flows for orchestration (local execution, Cloud UI monitoring)
- `config/` — projections, scoring, env
- `data/` — local dev data (raw/stage/mart/ops)
- `dbt/ff_data_transform/` — dbt project (duckdb + external Parquet)
- `docs/` — spec, ADRs, dev guides, analytics

## Contributing

- Read AGENTS guide: `AGENTS.md` (developer workflows, commands, expectations)
- Read Claude guide: `CLAUDE.md` (LLM/code assistant tips for this repo)
- Follow repo conventions: `docs/dev/repo_conventions_and_structure.md`
- Set up pre-commit: `uv run pre-commit install` then `uv run pre-commit run --all-files`
- Useful just commands: `just ingest-quick`, `just dbt-run`, `just dbt-test`, `just sql-fix` (run `just help` for full list)
- `just dbt-run` / `just dbt-test` wrap `uv run` with the project env (EXTERNAL_ROOT + DuckDB path prewired).

## Cloud Storage (GCS) Output Support

- The nflverse Python shim now writes to both local paths and `gs://` URIs.
- Credentials: set `GOOGLE_APPLICATION_CREDENTIALS` (path) or `GCS_SERVICE_ACCOUNT_JSON` (inline JSON).
- Example: `uv run python -c "from ingest.nflverse.shim import load_nflverse; print(load_nflverse('players', seasons=[2024], out_dir='gs://<bucket>/raw/nflverse'))"`
- Smoke test: `uv run python tools/smoke_gcs_write.py --dest gs://<bucket>/test/ff_analytics`
