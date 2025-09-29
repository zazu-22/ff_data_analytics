# Repository Guidelines

## Project Structure & Module Organization

- `ingest/`: dataset registry (`registry.py`) and loader shim (`shim.py`) that write Parquet to `data/raw/<source>/<dataset>/dt=YYYY-MM-DD/`.
- `tools/`: developer utilities (e.g., `make_samples.py`).
- `scripts/R/`: R runners (`nflverse_load.R`, `ffanalytics_run.R`).
- `notebooks/`: exploration and ETL prototypes.
- `config/`: YAML/CSV configs (projections, scoring).
- `docs/`: architecture, analytics, and dev docs.
- `.github/workflows/`: CI pipelines.

## Build, Test, and Development Commands

- Setup (Python 3.13.6 via `.python-version`): `pip install uv && uv sync`.
- Run nflverse loader: `python -c "from ingest.nflverse.shim import load_nflverse; print(load_nflverse('players', seasons=[2024], out_dir='data/raw/nflverse'))"`.
- Run projections (R): `Rscript scripts/R/ffanalytics_run.R --config config/projections/ffanalytics_projections_config.yaml --scoring config/scoring/sleeper_scoring_rules.yaml`.
- Notebooks: `jupyter lab` (install via project deps) for local analysis.

## Dependency Management (uv)

- Add runtime deps: `uv add pandas polars pyarrow`.
- Add dev deps: `uv add --dev pre-commit ruff mdformat mdformat-gfm yamllint nbqa sqlfluff sqlfluff-templater-dbt dbt-duckdb`.
- Sync and run: `uv sync`; execute tools via `uv run <cmd>` (e.g., `uv run ruff format .`).
- Install Git hook: `uv run pre-commit install` (then `uv run pre-commit run --all-files`).

### Makefile shortcuts

- `make samples-nflverse` — generate minimal nflverse samples
- `make dbt-run` / `make dbt-test` — run/test dbt locally (DuckDB)
- `make quickstart-local` — samples → dbt run → dbt test
- `make sqlfix` — manual sqlfluff auto-fix for dbt models

## Coding Style & Naming Conventions

- Python: PEP 8, 4‑space indent, type hints where practical; snake_case for modules/functions, PascalCase for classes.
- DataFrames: prefer Polars and PyArrow; write columnar Parquet; avoid implicit type casts.
- Notebooks: name `topic_action.ipynb` (e.g., `notebooks/load_nflverse_data.ipynb`).

## Testing Guidelines

- Use `pytest` with `tests/` and `test_*.py` naming.
- For loaders, validate schema/keys (see `ingest/registry.py: primary_keys`) and non‑null key coverage.
- Run locally: `pytest -q` (add fixtures for small CSV/Parquet samples where feasible).

## Commit & Pull Request Guidelines

- Conventional commits (seen in history): `feat:`, `docs:`, `chore:`, `init:`.
- Example: `feat: add nflverse weekly loader with Parquet output`.
- PRs: clear description, linked issues, sample output path(s), config diffs, and screenshots/plots when touching analytics.

## Security & Configuration Tips

- Store secrets in `.env`; never commit keys/tokens. Use repo secrets for CI.
- Make `out_dir` explicit for local runs; avoid writing to cloud buckets during tests.

## Architecture & CI

- Data layout: immutable, partitioned Parquet under `data/raw/<source>/<dataset>/dt=YYYY-MM-DD/` (+ `_meta.json` sidecar from the loader). See spec: `docs/spec/SPEC-1_v_2.2.md`.
- Dimensional modeling: Apply Kimball techniques per `docs/architecture/kimball_modeling_guidance/kimbal_modeling.md` when designing facts, dimensions, and marts in dbt.
- CI: `.github/workflows/data-pipeline.yml` runs nflverse Mondays 08:00 UTC and projections Tuesdays 08:00 UTC; supports manual dispatch.

## dbt Project

- Location: `dbt/ff_analytics/` (DuckDB + external Parquet)
- Profiles: see `dbt/ff_analytics/profiles.example.yml` (env toggles `DBT_TARGET`, `DBT_THREADS`)
- SQL linting: SQLFluff with dbt templater; staging models allow raw-aligned names; manual fix via `make sqlfix`.

Note: dbt build artifacts are ignored (`dbt/**/target`, `dbt/**/logs`).

## Contributing & Conventions

- Conventions: See `docs/dev/repo_conventions_and_structure.md` for repo layout, naming, data paths, and dbt organization.
- Pre-commit: `uv run pre-commit install` then `uv run pre-commit run --all-files` before pushing.
- SQL style: SQLFluff (dbt templater, DuckDB dialect). Staging allows raw-aligned names (ignores `RF04`, `CV06`); core can be stricter.
- Make targets: `make samples-nflverse`, `make dbt-run`, `make dbt-test`, `make sqlfix`.

## Sample Data

- Generate samples: `uv run python tools/make_samples.py`. Reference: `docs/dev/how_to_use_the_sample_generator_tools_make_samples.md`.
