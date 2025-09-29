# Repository Conventions & Structure

Purpose: establish consistent naming, directory layout, and data organization to keep the codebase clean, maintainable, and aligned to SPEC v2.2.

## Top‑Level Layout

- `ingest/`: Provider‑specific loaders/shims. Execution‑oriented modules, not packaged for distribution.
- `src/`: Reusable Python library code (`ff_analytics_utils`) shared by scripts and loaders.
- `scripts/`: Operational scripts and CLIs.
  - `scripts/R/`: R entrypoints (e.g., nflverse fallback, projections).
  - `scripts/ingest/`: ingestion utilities for Sheets, etc.
  - `scripts/troubleshooting/`, `scripts/setup/`, `scripts/debug/`.
- `tools/`: developer utilities (e.g., `make_samples.py`).
- `config/`: configuration (YAML/CSV) for projections, scoring, env.
- `data/`: local dev data mirrors cloud layout; immutable raw snapshots.
- `docs/`: spec, ADRs, architecture, dev guides, analytics.
- `.github/workflows/`: CI pipelines.

## Naming & Coding Conventions

- Python
  - Modules/files: `snake_case.py`; functions `snake_case`; classes `PascalCase`.
  - Avoid one‑letter vars; use type hints where practical.
  - Package namespace for reusable code: `src/ff_analytics_utils/...` (utilities), future: `src/ff_analytics/...` (domain).
- R scripts: `snake_case.R` with `<tool>_<verb>.R` or `<domain>_<action>.R`.
- CLI/scripts: `scripts/<domain>/<verb_noun>.py` (e.g., `copy_league_sheet.py`).
- Tests: `tests/test_*.py` grouped by module or feature.
- Docs
  - ADRs: `docs/adr/ADR-XXX-title.md`.
  - Spec: `docs/spec/SPEC-<n>_v_<version>.md` + change log.
  - Dev guides: `docs/dev/<topic>.md` (e.g., `how_to_use_the_sample_generator_tools_make_samples.md`).
  - Analytics/architecture: `docs/analytics/`, `docs/architecture/`.

## Data Layout & File Naming

- Partitioning (raw): `data/raw/<provider>/<dataset>/dt=YYYY-MM-DD/`.
- Parquet files: `<dataset>_<uuid8>.parquet` (opaque, append‑friendly).
- Sidecar meta: `_meta.json` with `dataset`, `asof_datetime` (UTC ISO), `loader_path`, `source_name`, `source_version`, `output_parquet`.
- Local dev mirrors cloud layout. Cloud targets (GCS): `gs://ff-analytics/{raw,stage,mart,ops}`.
- Stage/mart conventions (dbt external Parquet):
  - Stage: `gs://.../stage/<provider>/<dataset>/` (or domain‑specific folders if needed).
  - Mart: `gs://.../mart/<domain>/...` partitioned by model convention (e.g., `['season','week']`, `['asof_date']`).

## dbt Project Organization (duckdb + external Parquet)

- Root folder: `dbt/ff_analytics/` (project name: `ff_analytics`).
- Subfolders:
  - `models/`
    - `sources/` → `src_<provider>.yml` (source definitions)
    - `staging/` → `stg_<provider>__<dataset>.sql`
    - `core/` → facts/dims (`fact_*`, `dim_*`), scoring marts
    - `markets/` → KTC market value marts
    - `ops/` → run ledger, model metrics, data quality
  - `seeds/` → `dim_*`, dictionaries, scoring rules
  - `macros/` → freshness gates, helpers
  - `tests/` → generic tests if any
- Model naming
  - Staging: `stg_<provider>__<dataset>` (double underscore between provider and dataset).
  - Facts: `fact_<domain>_...`; Dims: `dim_<entity>`.
  - Views for convenience: `vw_<name>`.
- Config defaults (`dbt_project.yml`)
  - `+materialized: table`, `+external: true` (Parquet), partitions per folder: `core` (season/week), `markets` (asof_date).
  - `vars.external_root: gs://ff-analytics/mart`.
- Profiles (`profiles.yml`): DuckDB `:memory:` with `extensions: [httpfs]`.

## Ingest Module Structure

- `ingest/<provider>/` packages for each provider shim.
- Registry: central dataset map per provider (e.g., `ingest/nflverse/registry.py`).
- Shim/loader: unified entrypoint (e.g., `ingest/nflverse/shim.py`).
- Normalization only where required to maintain stable schemas; otherwise preserve raw field names for staging.

## Config Organization

- `config/projections/` → projections YAML + site weights CSV.
- `config/scoring/` → league scoring YAML.
- `config/gcs/` → environment‑specific bucket/prefix if needed.

## Notebooks

- Naming: `topic_action.ipynb` (e.g., `load_nflverse_data.ipynb`).
- Top cell sets `MARKET_SCOPE`, freshness banners sourced from marts/ops.

## Versioning & Breaking Changes

- Additive schema changes preferred. Breaking changes → versioned paths (e.g., `mart/fact_weekly_stats_v2/`) + compatibility views.
- Track in ADRs and CHANGELOG within `docs/spec/`.

## What Goes Where

- Reusable code → `src/ff_analytics_utils/...` (helpers used by scripts/loaders).
- Provider shims/loaders → `ingest/<provider>/...`.
- One‑off operational scripts → `scripts/` subfolders.
- Developer utilities → `tools/`.
- Data dictionaries or exports for local dev → `data/data_dictionaries/`, `data/raw/csv/...` (kept small, not authoritative).
