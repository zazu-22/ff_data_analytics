# AGENTS Guide

This guide summarizes how we expect LLM "agents" (and any contributor using autonomous tooling) to work inside the project. It reflects the **current implementation state** captured in the spec pack under `docs/spec/` (see `SPEC-1_v_2.3_implementation_checklist_v_0.md`, updated 2025-10-24) and will evolve as new tracks land. The project is still in development -- treat anything marked "[ ]" in the checklist as in-flight or future work.

## Current Implementation Snapshot

- **Phase 1 Seeds** - [x] Complete. Identity tables (`dim_player_id_xref`, `dim_franchise`, `dim_scoring_rule`, `dim_pick`, `dim_timeframe`, `dim_name_alias`) are materialized and tested (spec section 0, checklist section 1).
- **Phase 2 Track A (NFL Actuals)** - [x] ~95% implemented. nflverse shim + dbt models deliver `fact_player_stats`, `dim_player`, `dim_team`, `dim_schedule`, `mart_real_world_actuals_weekly`, `mart_fantasy_actuals_weekly`; follow-ups cover kicking stats and defensive tackle clean-up (checklist section 2).
- **Phase 2 Track B (Commissioner Sheets)** - [x] Complete. `src/ingest/sheets/commissioner_parser.py` normalizes roster/transactions into long-form tables with sample-backed tests (checklist section 2 Track B, ADR-008).
- **Phase 2 Track C (Market Data / KTC)** - [ ] Not started. Stub loader exists under `src/ingest/ktc/`; fetching, staging, and marts remain open (checklist section 5).
- **Phase 2 Track D (Projections)** - [x] Complete. R runner + dbt projections marts (`mart_real_world_projections`, `mart_fantasy_projections`, `mart_projection_variance`) are wired per checklist section 2 Track D.
- **Phase 3 / Ops** - [ ] Pending. Ops schema, change capture, notebooks, CI hardening, and compaction playbook remain to be implemented (checklist section 3 onward).

Consult `docs/spec/SPEC-1_v_2.2.md` for architecture intent and the v2.3 checklist for authoritative implementation status before making changes.

## Codebase Map

- `src/ingest/` - Provider loaders (Python-first) with registries and shared storage helpers. R fallbacks live under `scripts/R/`.
- `src/ff_analytics_utils/` - Reusable helpers (e.g., storage, validation).
- `tools/` - Developer utilities (`make_samples.py`, smoke tests).
- `dbt/ff_data_transform/` - DuckDB project with staging/core/mart layers plus seeds.
- `config/` - Projection configs, scoring rules, environment toggles.
- `docs/` - Spec, ADRs, analysis, architecture guidance.
- `notebooks/` - Prototypes and exploratory analysis (named `topic_action.ipynb`).
- `.github/workflows/` - `data-pipeline.yml` (batch orchestration) and `ingest_google_sheets.yml`.

Keep `PYTHONPATH=.` when running Python modules so `src/` packages resolve correctly.

## Daily Workflows

- **Environment setup**: `uv sync` (Python 3.13.6 via `.python-version`). Add packages with `uv add` / `uv add --dev`.
- **Sample generation**: `uv run python tools/make_samples.py nflverse --datasets players weekly --seasons 2024 --out ./samples`.
- **Run nflverse loader**: `uv run python -c "from ingest.nflverse.shim import load_nflverse; print(load_nflverse('players', seasons=[2024], out_dir='data/raw/nflverse'))"`.
- **dbt**: `make dbt-run` / `make dbt-test` (wrapped in `uv run` to ensure adapters and env vars) — outputs land in `dbt/ff_data_transform/target/dev.duckdb`.
- **Python tests**: `pytest -q` (fixtures in `samples/`). Ensure Sheets parsers and storage helpers stay covered.
- **Formatting & lint**: `uv run pre-commit run --all-files` (ruff, mdformat, sqlfmt, sqlfluff, yamllint, dbt compile, dbt-opiner, etc.).
  - **SQL formatting**: `make sqlfmt` formats all SQL files; `make sqlfmt-check` checks formatting
  - **SQL linting**: `make sqlcheck` runs SQLFluff (selective, excludes DuckDB-specific syntax files via `.sqlfluffignore`); `make sqlfix` auto-fixes
  - **SQL validation**: `make dbt-compile-check` validates SQL syntax using dbt compile
  - **dbt best practices**: `make dbt-opiner-check` checks dbt project conventions (config: `.dbt-opiner.yaml`)
  - **All SQL checks**: `make sql-all` runs format check + lint + compile + opiner

Prefer `uv run <cmd>` to ensure the pinned environment and hooks (e.g., specifying `UV_CACHE_DIR` when needed).

## Data Output & Storage Conventions

- **Layout**: `data/raw/<source>/<dataset>/dt=YYYY-MM-DD/` (local mirror of `gs://ff-analytics/{raw,stage,mart,ops}` per spec architecture section).
- **Artifacts**: Each load writes Parquet plus `_meta.json` manifest with lineage fields (`dataset`, `loader_path`, `source_version`, `row_count`, `asof_datetime`).
- **Engines**: Polars/PyArrow for DataFrames; DuckDB external tables for marts (see spec dbt-duckdb strategy section).
- **Identity**: Use `dim_player_id_xref` (mfl_id canonical) + `dim_name_alias` for resolving provider IDs; reject loads that break PK coverage.
- **Security**: Never commit credentials. Set `GOOGLE_APPLICATION_CREDENTIALS` or `GCS_SERVICE_ACCOUNT_JSON` for GCS/Sheets auth; keep `.env` local.

## Development Standards

- **Coding style**: PEP 8, 4-space indent, typed where practical; snake_case/PascalCase per convention.
- **Data modeling**: Follow Kimball guidance (`docs/architecture/kimball_modeling_guidance/kimbal_modeling.md`), especially for SCDs and fact grains.
- **Testing**: Validate PKs/non-null keys for loaders; dbt models require grain and referential tests. Keep sample fixtures small and representative.
- **Commits**: Conventional prefixes (`feat:`, `chore:`, `docs:`). Reference affected datasets and include sample output paths in PR descriptions.
- **CI**: `data-pipeline.yml` orchestrates scheduled runs; extend with new loaders/tests when Track C/Phase 3 components ship.

## High-Priority Follow-Ups (Open Items)

- Build full KTC ingestion pipeline (fetcher, storage, dbt staging & marts) and wire `tools/make_samples.py` to real data.
- Extend nflverse scoring coverage (kicking, defensive stats) and ensure `dim_scoring_rule` alignment.
- Implement ops schema + run ledger, freshness checks, and compaction guidance (spec data quality and ops section).
- Harden CI (Sheets copy, dbt run/test, LKG fallbacks) and add user-facing notebooks once Track C lands.

Re-check the v2.3 checklist before starting work -- statuses change frequently, and new ADRs may supersede older guidance.

## Reference Documents

- `docs/spec/SPEC-1_v_2.2.md` - Architectural blueprint (2x2 stat model, storage layout, security).
- `docs/spec/SPEC-1_v_2.3_implementation_checklist_v_0.md` - Source of truth for implementation progress and open items.
- `docs/dev/repo_conventions_and_structure.md` - Naming, layout, data path conventions.
- `docs/dev/how_to_use_the_sample_generator_tools_make_samples.md` - Sample generator usage notes.
- `CLAUDE.md` (root + package-specific variants) - Additional assistant-centric guidance.

Update this file whenever spec status or workflows change so autonomous agents stay in sync with reality.
