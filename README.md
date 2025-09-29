# FF Analytics — Data Architecture & Analytics

[![Spec](https://img.shields.io/badge/SPEC-v2.2-brightgreen)](docs/spec/SPEC-1_v_2.2.md)
[![Conventions](https://img.shields.io/badge/Conventions-Repo%20Structure-blue)](docs/dev/repo_conventions_and_structure.md)
[![Data Pipeline CI](https://img.shields.io/badge/CI-Data%20Pipeline-lightgrey)](.github/workflows/data-pipeline.yml)

## Quick Links

- SPEC: docs/spec/SPEC-1_v_2.2.md
- Conventions & Structure: docs/dev/repo_conventions_and_structure.md
- Sample Generator Guide: docs/dev/how_to_use_the_sample_generator_tools_make_samples.md

## Getting Started

- Python: `pip install uv && uv sync`
- R: see `scripts/R/` for runners and `renv.lock` for pins
- Generate samples: `uv run python tools/make_samples.py`

## Repo Structure (high level)

- `ingest/` — provider shims/loaders (execution code)
- `src/ff_analytics_utils/` — reusable helpers (library code)
- `scripts/` — operational scripts (R runners, ingest, troubleshooting)
- `tools/` — developer utilities (sample generator)
- `config/` — projections, scoring, env
- `data/` — local dev data (raw/stage/mart/ops)
- `dbt/ff_analytics/` — dbt project (duckdb + external Parquet)
- `docs/` — spec, ADRs, dev guides, analytics

## Contributing

- Read AGENTS guide: `AGENTS.md` (developer workflows, commands, expectations)
- Read Claude guide: `CLAUDE.md` (LLM/code assistant tips for this repo)
- Follow repo conventions: `docs/dev/repo_conventions_and_structure.md`
- Set up pre-commit: `uv run pre-commit install` then `uv run pre-commit run --all-files`
- Useful make targets: `make samples-nflverse`, `make dbt-run`, `make dbt-test`, `make sqlfix`
