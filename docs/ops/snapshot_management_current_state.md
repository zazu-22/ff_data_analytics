# Snapshot Management — Current State

**Last Updated**: 2025-11-20
**Status**: Active

## Overview

This document describes how snapshot selection works in the FF Analytics data pipeline as of November 2025.

## Snapshot Selection Strategies

### Macro-Based Selection (Current Standard)

All 13 staging models now use the `snapshot_selection_strategy` macro for flexible, parameterized snapshot selection. The macro supports three strategies:

**1. `latest_only` (Default)**

- Filters to MAX(dt) from source data
- Ensures idempotent reads when multiple snapshots exist
- Used by: Sheets (5 models), KTC (1 model), FFAnalytics (1 model), Sleeper (2 models), NFLverse ff_opportunity (1 model), NFLverse ff_playerids (1 model)

Models using `latest_only`:

- `stg_sheets__cap_space` — Latest salary cap snapshot
- `stg_sheets__contracts_active` — Latest active contracts
- `stg_sheets__contracts_cut` — Latest cut player history
- `stg_sheets__draft_pick_holdings` — Latest draft pick inventory
- `stg_sheets__transactions` — Latest transaction history
- `stg_ktc_assets` — Latest KTC dynasty valuations (1QB default)
- `stg_ffanalytics__projections` — Latest fantasy projections
- `stg_sleeper__fa_pool` — Latest free agent pool
- `stg_sleeper__rosters` — Latest roster data
- `stg_nflverse__ff_opportunity` — Latest fantasy opportunity metrics (consistency with other latest_only models)
- `stg_nflverse__ff_playerids` — Latest player ID mappings

**2. `baseline_plus_latest`**

- Selects baseline snapshot (historical anchor) + latest snapshot
- Maintains historical continuity while incorporating new data
- Used by: NFLverse player_stats (1 model), NFLverse snap_counts (1 model)

Models using `baseline_plus_latest`:

- `stg_nflverse__player_stats` — Baseline (2025-10-01) + latest weekly stats
- `stg_nflverse__snap_counts` — Baseline (2025-10-01) + latest snap counts

**Baseline Configuration** (via dbt vars in `dbt_project.yml`):

```yaml
vars:
  NFLVERSE_BASELINE_DT: '2025-10-01'  # Fallback for all NFLverse datasets
  NFLVERSE_WEEKLY_BASELINE_DT: '2025-10-01'  # Specific override for weekly
  NFLVERSE_SNAP_BASELINE_DT: '2025-10-01'  # Specific override for snap_counts
```

**Fallback Pattern**: Models use `var('NFLVERSE_WEEKLY_BASELINE_DT', var('NFLVERSE_BASELINE_DT', '2025-10-01'))` to allow dataset-specific overrides while maintaining a common default.

**3. `all`**

- No dt filter applied (reads all snapshots)
- Best for: Backfills, historical analysis, debugging
- Currently not used in production models

**Benefits of Macro-Based Approach**:

- Eliminates hardcoded dates in SQL
- Automatic pickup of new snapshots
- Configurable via dbt vars
- Single source of truth for snapshot selection logic

### Legacy Hardcoded Dates

**Status**: None — All 13 staging models have been migrated to macro-based selection as of Phase 1 completion (2025-11-13).

## Snapshot Lifecycle

Snapshots progress through four states tracked in the snapshot registry:

1. **pending** — Loaded but not yet validated
2. **current** — Active in production models
3. **historical** — Retained for continuity (e.g., baseline snapshots)
4. **archived** — Kept for audit but not used in models

**Registry Location**: `dbt/ff_data_transform/seeds/snapshot_registry.csv`

**Registry Structure**:

- `source` — Provider name (sheets, nflverse, ktc, ffanalytics, sleeper)
- `dataset` — Dataset identifier
- `snapshot_date` — Snapshot date (YYYY-MM-DD)
- `status` — Lifecycle state (current, historical, pending, archived)
- `coverage_start_season`, `coverage_end_season` — NFLverse season range
- `row_count` — Number of rows (extracted from `_meta.json` manifests)
- `notes` — Human-readable description

**Current Inventory** (as of 2025-11-18):

- **Total snapshots**: 100 (96 current, 4 historical baselines)
- **FFAnalytics**: 5 snapshots
- **KTC**: 10 snapshots
- **NFLverse**: 27 snapshots (4 historical baselines)
- **Sheets**: 36 snapshots
- **Sleeper**: 22 snapshots

## Legacy Sample Data

**Status**: No archival needed in current environment.

**Rationale**:

- `data/raw/` directory is gitignored (runtime data only)
- No committed sample artifacts exist in repository
- Test fixtures in `samples/` directory working correctly (2/2 tests passing)

**Sample Generation Tool**: `tools/make_samples.py` is preserved for creating samples when exploring new sources.

**Policy**: Samples from fully integrated sources (nflverse, sheets) are no longer needed for active development. The sample generation tool is retained for new source exploration.

## Common Operations

### Check Current Snapshots

Query the registry seed to see what snapshots are currently active:

```bash
# Load registry seed
just dbt-seed --select snapshot_registry

# Query registry with DuckDB CLI
duckdb dbt/ff_data_transform/target/dev.duckdb

# Within DuckDB:
SELECT
    source,
    dataset,
    snapshot_date,
    status,
    row_count,
    notes
FROM main.snapshot_registry
WHERE status = 'current'
ORDER BY source, dataset, snapshot_date DESC;
```

**Alternative**: Use the snapshot coverage analysis tool:

```bash
uv run python tools/analyze_snapshot_coverage.py --sources all --format json
```

### Add New Snapshot

Follow this workflow when adding a new snapshot:

1. **Load data** to `data/raw/<source>/<dataset>/dt=YYYY-MM-DD/`
2. **Write `_meta.json` manifest** with snapshot metadata:
   ```json
   {
     "snapshot_date": "2025-11-20",
     "source": "sheets",
     "dataset": "contracts_active",
     "row_count": 890,
     "load_timestamp": "2025-11-20T12:34:56Z",
     "extractor_version": "1.0.0"
   }
   ```
3. **Update registry seed**: Add new entry with `status='pending'` in `dbt/ff_data_transform/seeds/snapshot_registry.csv`
4. **Validate**: Run `uv run python tools/validate_manifests.py --sources <source>`
5. **Promote**: Change status from `pending` to `current` in registry
6. **Reload seed**: Run `just dbt-seed --select snapshot_registry --full-refresh`

### Retire Old Snapshot

Follow this workflow when retiring a snapshot:

1. **Update registry**: Change status from `current` to `archived` in `snapshot_registry.csv`
2. **Reload seed**: Run `just dbt-seed --select snapshot_registry --full-refresh`
3. **Optional**: Move data to cold storage (if using cloud storage)
4. **Update baseline_dt var**: If retiring a baseline snapshot, update the baseline_dt variable in `dbt_project.yml`

### Validate Snapshot Manifests

Check that all snapshot manifests are valid and fresh:

```bash
# Validate all sources
uv run python tools/validate_manifests.py --sources all

# Validate specific source
uv run python tools/validate_manifests.py --sources sheets

# Check freshness only
uv run python tools/validate_manifests.py --sources all --freshness-only

# Custom freshness thresholds (in hours)
uv run python tools/validate_manifests.py --sources sheets --max-age 48
```

**Freshness Validation** (replaces dbt source freshness):

- Pre-dbt validation: Runs before dbt compile/run
- Configurable thresholds per source
- Exits with error code 1 if stale data detected
- Designed for CI/CD integration

**Default Freshness Thresholds**:

- **sheets**: 24 hours (daily league updates)
- **nflverse**: 72 hours (weekly NFL schedule)
- **sleeper**: 24 hours (daily roster changes)
- **ktc**: 72 hours (weekly trade value updates)
- **ffanalytics**: 168 hours (weekly projections)

### Analyze Snapshot Coverage

Generate comprehensive snapshot coverage reports:

```bash
# Full analysis with all features
uv run python tools/analyze_snapshot_coverage.py \
    --sources all \
    --format json \
    --output-file snapshot_coverage_report.json

# Human-readable summary
uv run python tools/analyze_snapshot_coverage.py \
    --sources nflverse \
    --format summary

# Check specific features
uv run python tools/analyze_snapshot_coverage.py \
    --sources nflverse \
    --row-deltas  # Row count changes between snapshots
    --gap-detection  # Season/week coverage gaps
    --player-mapping  # Player ID resolution rates
```

**Analysis Features**:

- **Row Deltas**: Compares row counts between consecutive snapshots, flags anomalies
- **Gap Detection**: Identifies missing seasons/weeks in NFLverse datasets
- **Player Mapping**: Calculates player ID resolution rates (join to `dim_player_id_xref`)
- **Baseline Awareness**: Understands baseline_plus_latest strategy for gap detection

## Configuration

### dbt Variables

Baseline dates use a fallback pattern for consistency:

```yaml
# dbt_project.yml
vars:
  NFLVERSE_BASELINE_DT: '2025-10-01'  # Fallback for all NFLverse datasets
  NFLVERSE_WEEKLY_BASELINE_DT: '2025-10-01'  # Specific override for weekly
  NFLVERSE_SNAP_BASELINE_DT: '2025-10-01'  # Specific override for snap_counts
```

**Fallback Pattern**: Models use `var('NFLVERSE_WEEKLY_BASELINE_DT', var('NFLVERSE_BASELINE_DT', '2025-10-01'))` to allow dataset-specific overrides while maintaining a common default.

**Why Fallback Pattern?**

- Centralized default baseline for all NFLverse datasets
- Dataset-specific overrides available when needed (e.g., different baselines for weekly vs seasonal stats)
- Maintains consistency across models

### Environment Variables

External data paths are configured via environment variables (set automatically by `justfile`):

```bash
# External data root (set by justfile)
EXTERNAL_ROOT="$PWD/data/raw"

# DuckDB database path (set by justfile)
DBT_DUCKDB_PATH="$PWD/dbt/ff_data_transform/target/dev.duckdb"
```

**IMPORTANT**: Always use `just` commands for dbt operations. The justfile automatically sets these environment variables with correct absolute paths. Never set them manually.

### Macro Reference

The `snapshot_selection_strategy` macro is defined in `dbt/ff_data_transform/macros/snapshot_selection.sql`.

**Signature**:

```sql
{% macro snapshot_selection_strategy(source_glob, strategy='latest_only', baseline_dt=none) %}
```

**Parameters**:

- `source_glob` — Path pattern for parquet files (e.g., `var("external_root") ~ "/nflverse/weekly/dt=*/*.parquet"`)
- `strategy` — Selection strategy: `latest_only`, `baseline_plus_latest`, or `all`
- `baseline_dt` — Required for `baseline_plus_latest` strategy (e.g., `'2025-10-01'`)

**Usage Examples**:

```sql
-- Latest only (default)
SELECT * FROM read_parquet(
    {{ snapshot_selection_strategy(
        var("external_root") ~ "/sheets/contracts_active/dt=*/*.parquet",
        strategy="latest_only"
    ) }},
    hive_partitioning=true
)

-- Baseline + latest (NFLverse historical continuity)
SELECT * FROM read_parquet(
    {{ snapshot_selection_strategy(
        var("external_root") ~ "/nflverse/weekly/dt=*/*.parquet",
        strategy="baseline_plus_latest",
        baseline_dt=var('NFLVERSE_WEEKLY_BASELINE_DT', var('NFLVERSE_BASELINE_DT', '2025-10-01'))
    ) }},
    hive_partitioning=true
)

-- All snapshots (backfills, debugging)
SELECT * FROM read_parquet(
    {{ snapshot_selection_strategy(
        var("external_root") ~ "/sheets/transactions/dt=*/*.parquet",
        strategy="all"
    ) }},
    hive_partitioning=true
)
```

## Migration Status

**Phase 1 Foundation**: ✅ COMPLETE (2025-11-13)

All 13 staging models migrated from hardcoded dates or `dt=*` wildcards to macro-based selection:

- ✅ **NFLverse** (4 models): player_stats, snap_counts, ff_opportunity, ff_playerids
- ✅ **Sheets** (5 models): cap_space, contracts_active, contracts_cut, draft_pick_holdings, transactions
- ✅ **Sleeper** (2 models): fa_pool, rosters
- ✅ **KTC** (1 model): assets
- ✅ **FFAnalytics** (1 model): projections

**Data Quality Improvements**:

- ✅ Eliminated 2,088 duplicate rows across multiple models
- ✅ Fixed 195 duplicates in FFAnalytics projections (P1-016)
- ✅ Fixed 1,893 duplicates in Sleeper staging (P1-013)
- ✅ All staging models now have stable, idempotent snapshot selection

**Phase 2 Governance**: ✅ 5/7 COMPLETE (71%)

- ✅ **P2-001**: Snapshot registry seed created
- ✅ **P2-002**: Registry populated with 100 snapshots from all 5 sources
- ✅ **P2-003**: Row delta reporting added to analyze_snapshot_coverage.py
- ✅ **P2-004**: Gap detection added to analyze_snapshot_coverage.py
- ✅ **P2-005**: Manifest validation tool created (validate_manifests.py)
- ✅ **P2-006B**: Freshness validation integrated into validate_manifests.py
- ⏳ **P2-007**: Remaining freshness tests (pending)

**Phase 3 Documentation**: ⏳ IN PROGRESS (1/8 complete)

- ✅ **P3-001**: SPEC v2.3 checklist updated
- 🔄 **P3-002**: This document (snapshot_management_current_state.md)
- ⏳ **P3-003**: Ingestion triggers documentation
- ⏳ **P3-004**: Data freshness documentation
- ⏳ **P3-005**: Orchestration architecture
- ⏳ **P3-006**: CI transition plan
- ⏳ **P3-007**: Cloud storage migration
- ⏳ **P3-008**: dbt model documentation updates

## Future State (Not Yet Implemented)

The following capabilities are planned but not yet implemented:

### Phase 4: Orchestration (Planned)

- Prefect flows for automated snapshot ingestion (5 sources)
- Registry updates integrated into ingestion flows
- Automated freshness validation as pre-run checks

### Phase 5: CI Planning (Planned)

- Parallel run strategy (old vs new snapshot governance)
- Rollback procedures
- Validation criteria and comparison process

### Phase 6: Cloud Blueprint (Planned)

- GCS bucket layout and lifecycle policies
- IAM requirements and service account setup
- DuckDB GCS configuration for cloud-native reads

**Note**: This document describes the current state as of November 2025. For future plans, see `docs/implementation/multi_source_snapshot_governance/2025-11-07_plan_v_2_0.md`.

## References

### Tools & Scripts

- **Snapshot registry seed**: `dbt/ff_data_transform/seeds/snapshot_registry.csv`
- **Selection macro**: `dbt/ff_data_transform/macros/snapshot_selection.sql`
- **Validation tool**: `tools/validate_manifests.py`
- **Coverage analysis**: `tools/analyze_snapshot_coverage.py`
- **Sample generation**: `tools/make_samples.py` (preserved for new source exploration)
- **Registry maintenance**: `tools/update_snapshot_registry.py`

### Documentation

- **Implementation plan**: `docs/implementation/multi_source_snapshot_governance/2025-11-07_plan_v_2_0.md`
- **Task checklist**: `docs/implementation/multi_source_snapshot_governance/2025-11-07_tasks_checklist_v_2_0.md`
- **Ticket tracking**: `docs/implementation/multi_source_snapshot_governance/tickets/00-OVERVIEW.md`
- **Registry maintenance guide**: `docs/implementation/multi_source_snapshot_governance/REGISTRY_MAINTENANCE.md`
- **SPEC v2.3**: `docs/spec/SPEC-1_v_2.3_implementation_checklist_v_0.md`

### Related Guides

- **dbt project guide**: `dbt/ff_data_transform/CLAUDE.md`
- **Repository conventions**: `docs/dev/repo_conventions_and_structure.md`
- **Kimball modeling**: `docs/spec/kimball_modeling_guidance/kimbal_modeling.md`

## Questions & Troubleshooting

### How do I know which snapshot is being used?

Query the compiled SQL to see the actual dt filter:

```bash
just dbt-compile --select stg_sheets__contracts_active
cat dbt/ff_data_transform/target/compiled/ff_data_transform/models/staging/stg_sheets__contracts_active.sql | grep "dt ="
```

### Why am I getting duplicate rows?

Check if the model is using `latest_only` strategy:

```bash
grep -A 5 "snapshot_selection_strategy" dbt/ff_data_transform/models/staging/stg_<model>.sql
```

If using `dt=*` without the macro, the model hasn't been migrated yet.

### How do I override the baseline date for testing?

Set the dbt variable at runtime:

```bash
just dbt-run --select stg_nflverse__player_stats --vars '{"NFLVERSE_WEEKLY_BASELINE_DT": "2025-09-01"}'
```

### How do I backfill historical data?

Temporarily change the strategy to `all`:

```sql
-- In staging model (temporary change)
WHERE {{ snapshot_selection_strategy(source_glob, strategy="all") }}
```

Then run the model, and revert the change.

### How do I check if a snapshot is fresh?

Use the validation tool with specific source:

```bash
uv run python tools/validate_manifests.py --sources sheets --max-age 24
```

### Where do I report issues with snapshot selection?

- **Data quality issues**: Create ticket in `docs/implementation/multi_source_snapshot_governance/tickets/`
- **Macro bugs**: Report in CLAUDE.md or create ADR
- **Tooling issues**: Check `tools/CLAUDE.md` or create issue

## Changelog

**2025-11-20**: Initial version created (P3-002)

- Documented current state as of November 2025
- All 13 staging models using macro-based selection
- Phase 1 Foundation complete
- Phase 2 Governance 5/7 complete
- Phase 3 Documentation in progress
