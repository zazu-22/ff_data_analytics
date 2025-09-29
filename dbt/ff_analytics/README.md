# ff_analytics dbt Project (DuckDB + external Parquet)

Badges

- [Spec v2.2](../../docs/spec/SPEC-1_v_2.2.md)
- [Repo Conventions](../../docs/dev/repo_conventions_and_structure.md)

## Structure

- `models/`
  - `sources/`: source definitions per provider
  - `staging/`: `stg_<provider>__<dataset>.sql`
  - `core/`: facts/dims and scoring marts
  - `markets/`: KTC market value marts
  - `ops/`: run ledger, model metrics, data quality
- `seeds/`: dictionaries, scoring rules, id xrefs
- `macros/`: freshness gates and helpers

## Defaults

- `dbt_project.yml` sets external Parquet writes and partitions per domain.

## Dimensional Modeling

For guidance on designing facts, dimensions, and marts using Kimball techniques, see `../../docs/architecture/kimball_modeling_guidance/kimbal_modeling.md`.
