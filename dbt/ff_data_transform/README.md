# ff_data_transform dbt Project

**Data Platform**: DuckDB + external Parquet
**Architecture**: Kimball dimensional modeling with 2×2 stat model (actual vs projected × real-world vs fantasy)

## Quick Links

- **Specification**: [SPEC-1 v2.3](../../docs/spec/SPEC-1_v_2.2.md)
- **Repository Conventions**: [repo_conventions_and_structure.md](../../docs/dev/repo_conventions_and_structure.md)
- **Dimensional Modeling Guide**: [kimball_modeling.md](../../docs/architecture/kimball_modeling_guidance/kimbal_modeling.md)
- **Project Context**: [CLAUDE.md](./CLAUDE.md) (developer guidance)

## Project Structure

```text
dbt/ff_data_transform/
├── models/
│   ├── sources/          # Source definitions (YAML only)
│   ├── staging/          # Normalized staging models (8 models)
│   ├── core/             # Facts and dimensions (8 models)
│   ├── marts/            # Analytics-ready marts (7 models)
│   ├── markets/          # Market signal marts (planned)
│   └── ops/              # Data quality/lineage (planned)
├── seeds/                # Reference data (12 seeds)
├── macros/               # Reusable SQL functions
├── tests/                # Custom data tests
├── analyses/             # Ad-hoc analyses
└── target/               # Compiled SQL and DuckDB database
```

## Model Organization

### Schema Documentation Pattern

This project follows **per-model YAML documentation** (dbt best practice):

- Each model has its own `_<model_name>.yml` file
- YAML files live alongside SQL models in the same directory
- Underscore prefix groups documentation with models in file listings
- Example: `stg_ktc_assets.sql` + `_stg_ktc_assets.yml`

**Benefits**:

- Easier navigation (docs next to models)
- Reduced merge conflicts (separate files per model)
- Clearer ownership and code reviews
- Better scalability as project grows

### Model Layers

#### Sources (`models/sources/`)

Provider-specific source definitions (YAML only, no SQL):

- `src_nflverse.yml` - NFL stats (player_stats, snap_counts, ff_opportunity)
- `src_ffanalytics.yml` - Consensus projections
- `src_sheets.yml` - Commissioner league data (transactions, contracts)

#### Staging (`models/staging/`)

Normalized, long-form staging models with player ID crosswalks:

- `stg_nflverse__player_stats` - 71 stat types unpivoted
- `stg_nflverse__snap_counts` - 6 snap stats
- `stg_nflverse__ff_opportunity` - 38 opportunity metrics
- `stg_ffanalytics__projections` - Consensus projections
- `stg_sheets__transactions` - League transactions with validation
- `stg_sheets__contracts_active` - Current roster contracts
- `stg_sheets__contracts_cut` - Dead cap obligations
- `stg_ktc_assets` - Dynasty market values (players + picks)

#### Core (`models/core/`)

Kimball-style facts and dimensions:

**Facts**:

- `fct_player_stats` - Consolidated stats (2.7M rows, 109 stat types)
- `fct_player_projections` - Weekly/season projections
- `fct_league_transactions` - Transaction history (4,474 events)
- `fct_asset_market_values` - KTC market value snapshots

**Dimensions**:

- `dim_player` - Player attributes with crosswalk
- `dim_team` - NFL teams
- `dim_schedule` - Game schedule
- `dim_asset` - Unified players + picks
- `dim_player_contract_history` - Contract lifecycle (Type 2 SCD)

#### Marts (`models/marts/`)

Analytics-ready marts implementing 2×2 stat model:

**Real-World Stats**:

- `mrt_real_world_actuals_weekly` - Physical stats (no scoring)
- `mrt_real_world_projections` - Projected stats (no scoring)

**Fantasy Scoring**:

- `mrt_fantasy_actuals_weekly` - Actual fantasy points (half-PPR + IDP)
- `mrt_fantasy_projections` - Projected fantasy points (half-PPR)

**Analysis**:

- `mrt_projection_variance` - Actuals vs projections comparison

**Contracts**:

- `mrt_contract_snapshot_current` - Transaction-derived contracts by year
- `mrt_contract_snapshot_history` - Commissioner sheet snapshots

#### Markets (`models/markets/`)

Market signal analytics (planned):

- KTC trade value trends
- Dynasty rankings analysis

#### Ops (`models/ops/`)

Operational models (planned):

- Data freshness monitoring
- Load history tracking
- Test results over time

## Configuration

**Profile**: `ff_duckdb` (defined in `profiles.yml`)
**Target**: `local` (default) or `ci`
**Materialization**: External Parquet (large models) + views (staging)
**Database**: `target/dev.duckdb` (DuckDB file-based)
**External Root**: `../../data/raw` (via `EXTERNAL_ROOT` env var)

See [CLAUDE.md](./CLAUDE.md) for detailed configuration and usage.

## Running dbt

From repository root:

```bash
# Run all models
make dbt-run

# Run tests
make dbt-test

# Load seed data
make dbt-seed

# Fix SQL style issues
make sqlfix
```

## Test Coverage

**Total**: 278 data tests (98.6% passing)

**Test Types**:

- Grain uniqueness (fact tables)
- Foreign key relationships
- Accepted values (enums)
- Not null (required fields)
- Custom data quality tests

## Key Features

### 2×2 Stat Model (ADR-007)

Separates real-world stats from fantasy scoring, actuals from projections:

- Enables NFL analysis independent of fantasy scoring
- Supports multiple scoring systems without duplicating stats
- Clear separation of concerns (measurement vs valuation)

### Consolidated Fact Table (ADR-009)

Single `fct_player_stats` combines:

- Base player stats (71 types)
- Snap counts (6 types)
- Opportunity metrics (38 types)
- Total: 109 stat types, 2.7M rows

### Player Identity Resolution (ADR-010)

- Canonical ID: `mfl_id` from `dim_player_id_xref` crosswalk
- Maps 19 provider IDs (gsis_id, pfr_id, sleeper_id, etc.)
- Composite `player_key` prevents grain violations for unmapped players

### External Parquet Storage

- All large models write to external Parquet files
- DuckDB catalog is in-memory only (fast, disposable)
- Cloud-ready architecture (GCS integration via `external_location`)

## Dependencies

- **dbt**: 1.10.13 (dbt-fusion preview with DuckDB adapter)
- **DuckDB**: 1.9.6
- **Python**: 3.13.6 (managed via uv)
- **dbt Packages**: dbt-utils (see `packages.yml`)

## Resources

- **dbt Docs**: `dbt docs generate && dbt docs serve`
- **Compiled SQL**: `target/compiled/ff_data_transform/`
- **Database**: Query directly with `duckdb target/dev.duckdb`
