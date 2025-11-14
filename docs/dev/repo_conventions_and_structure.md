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

- Root folder: `dbt/ff_data_transform/` (project name: `ff_data_transform`).
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
- **Dimensional modeling patterns**: Follow Kimball techniques documented in `docs/architecture/kimball_modeling_guidance/kimbal_modeling.md` for fact/dimension design, grain declaration, conformed dimensions, and SCDs.

### SQL Style & Linting

This project uses a **multi-tool approach** for SQL quality assurance:

1. **sqlfmt** (formatting) - Formats all SQL files for consistent indentation/spacing

   - Uses polyglot dialect (supports DuckDB syntax)
   - Fast and opinionated (minimal configuration)
   - Uses 4-space indentation (default, non-configurable)
   - Run: `make sqlfmt` (format) or `make sqlfmt-check` (check only)
   - Pre-commit hook: Formats SQL files automatically on commit

2. **SQLFluff** (selective linting) - Style/quality checks on standard SQL models

   - Configuration: `.sqlfluff`, `pyproject.toml`, and `.sqlfluffignore` (all used)
   - Templater: `dbt` (understands Jinja)
   - Dialect: `duckdb` (with limitations)
   - Uses 4-space indentation (configured to match sqlfmt)
   - **Exclusions**: Files with DuckDB-specific syntax are excluded from SQLFluff linting via `.sqlfluffignore`:
     - Staging models (`stg_*.sql`) - use `read_parquet()` with named parameters
     - Core models: `dim_player_contract_history.sql`, `fact_league_transactions.sql`, `int_pick_*.sql`
     - Mart models: `mart_contract_snapshot_current.sql`, `mart_real_world_actuals_weekly.sql`
   - **Note**: `.sqlfluffignore` patterns should be kept in sync with pre-commit hook exclude patterns (different syntax: glob vs regex, but same files)
   - Rules: Enforce lowercase keywords/identifiers/functions; allow raw column names in staging (ignore `RF04`, `CV06`)
   - Run: `make sqlcheck` (lint) or `make sqlfix` (auto-fix)
   - Pre-commit hook: Lints SQL files (with exclusions matching `.sqlfluffignore`)

3. **dbt compile** (syntax validation) - Validates SQL syntax using actual DuckDB parser

   - Catches real syntax errors regardless of linting exclusions
   - Uses dbt's compilation process (validates after Jinja templating)
   - Run: `make dbt-compile-check`
   - Pre-commit hook: Validates all models on SQL file changes

4. **dbt-opiner** (dbt best practices) - Enforces dbt project conventions

   - Checks naming, structure, and dbt-specific patterns
   - **Configuration**: `.dbt-opiner.yaml` (optional - uses defaults if not present)
   - **Exclusions**: Test files (`tests/*.sql`) are excluded via pre-commit hook - they're not dbt project nodes
   - Separate from SQL syntax/style concerns
   - Run: `make dbt-opiner-check`
   - Pre-commit hook: Checks dbt best practices on dbt file changes
   - **Note**: When using `--all-files`, dbt-opiner will report errors for test files (expected - they're excluded from linting)

**All-in-one**: `make sql-all` runs all four checks in sequence.

**Pre-commit workflow**: Format (sqlfmt) → Lint (SQLFluff) → Validate (dbt compile) → dbt practices (dbt-opiner)

**Why multiple tools?**

- SQLFluff's DuckDB dialect has incomplete support for DuckDB-specific syntax (parsing errors on valid SQL)
- sqlfmt handles formatting correctly for all DuckDB syntax
- dbt compile provides authoritative syntax validation using the actual DuckDB parser
- dbt-opiner focuses on dbt project structure and conventions (not SQL syntax)

### Excluded Files Reference

**SQLFluff Exclusions** (via `.sqlfluffignore` file):

| File Pattern                                                            | Reason for Exclusion                                                                                      |
| ----------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| `dbt/ff_data_transform/models/staging/stg_*.sql`                        | Use `read_parquet()` with named parameters (e.g., `hive_partitioning = true`) which SQLFluff cannot parse |
| `dbt/ff_data_transform/models/core/dim_player_contract_history.sql`     | Uses `list_sum()`, `list_concat()` - DuckDB-specific list functions                                       |
| `dbt/ff_data_transform/models/core/fact_league_transactions.sql`        | Uses interval arithmetic (e.g., `date + interval '1' year`) which SQLFluff misparses                      |
| `dbt/ff_data_transform/models/core/intermediate/int_pick_*.sql`         | Uses `regexp_matches()`, `regexp_extract()`, `make_date()`, `unnest()` - DuckDB-specific functions        |
| `dbt/ff_data_transform/models/marts/mart_contract_snapshot_current.sql` | Uses `cast(... as json)`, `unnest()` - DuckDB-specific JSON/array functions                               |
| `dbt/ff_data_transform/models/marts/mart_real_world_actuals_weekly.sql` | Uses `arbitrary()` - DuckDB-specific aggregation function                                                 |
| `dbt/ff_data_transform/tests/*.sql`                                     | Test files are not dbt project nodes (validated separately via `dbt test`)                                |

**dbt-opiner Exclusions** (via pre-commit hook):

| File Pattern                        | Reason for Exclusion                                                                                                     |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| `dbt/ff_data_transform/tests/*.sql` | Test files are not dbt project nodes - they're standalone SQL files executed by `dbt test`, not part of the dbt manifest |

**Note**: All excluded files are still validated via `dbt compile` (syntax validation) and `dbt test` (data quality tests). Only style/formatting linting is excluded.

## Ingest Module Structure

- `ingest/<provider>/` packages for each provider shim.
- Registry: central dataset map per provider (e.g., `ingest/nflverse/registry.py`).
- Shim/loader: unified entrypoint (e.g., `ingest/nflverse/shim.py`).
- Normalization only where required to maintain stable schemas; otherwise preserve raw field names for staging.

### Utility Helpers: DuckDB-First with Fallback Pattern

For crosswalks and reference data needed during ingestion (e.g., player IDs, name aliases, team mappings):

**Pattern**: DuckDB-first with source fallback (CSV or Parquet)

**Why this pattern?**

- **Performance**: DuckDB queries are faster than file parsing
- **Consistency**: All code uses same dbt-transformed data
- **Robustness**: Fallback ensures first-run works without `dbt seed`/`dbt run`
- **No hard dependency**: Ingestion layer can operate independently

**Implementation** (`src/ff_analytics_utils/<resource>_xref.py`):

```python
def get_<resource>_xref(
    *,
    source: str = "auto",  # 'duckdb', '<file_type>', or 'auto'
    duckdb_table: str = "main.dim_<resource>_xref",
    db_path: str | Path | None = None,
    <file>_path: str | Path | None = None,
    columns: Sequence[str] | None = None,
) -> pl.DataFrame:
    """Return crosswalk as Polars DataFrame.

    Args:
        source: 'duckdb', '<file_type>', or 'auto' (DuckDB first, fallback to file)
        duckdb_table: Fully qualified DuckDB table name
        db_path: Override DuckDB path (defaults to DBT_DUCKDB_PATH)
        <file>_path: Path to fallback file (CSV/Parquet)
        columns: Optional column subset
    """
    if source in {"auto", "duckdb"}:
        try:
            return fetch_table_as_polars(duckdb_table, columns=columns, db_path=db_path)
        except Exception as exc:
            if source == "duckdb":
                raise RuntimeError(...) from exc

    if source in {"auto", "<file_type>"}:
        try:
            # Read from CSV/Parquet fallback
            ...
        except Exception as exc:
            if source == "<file_type>":
                raise RuntimeError(...) from exc

    raise RuntimeError("Unable to load from DuckDB or fallback source")
```

**Examples**:

- `player_xref.py`: DuckDB → Parquet fallback (ingested data from NFLverse)
- `name_alias.py`: DuckDB → CSV fallback (manual seed)
- `defense_xref.py`: DuckDB → CSV fallback (manual seed) - *planned in P1-028*

**Bootstrap Process**:

1. First run: Ingestion uses file fallback (slower but works)
2. Then: `dbt seed` (for seeds) or `dbt run` (for models) materializes into DuckDB
3. Subsequent runs: Use DuckDB (faster)

**Benefits**:

- File is single source of truth (no duplication)
- dbt materializes it into DuckDB for performance
- Python utilities query DuckDB (fast) with file fallback (robust)
- No hard circular dependency, just optimization

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
