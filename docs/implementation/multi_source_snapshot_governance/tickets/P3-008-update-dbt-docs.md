# Ticket P3-008: Update dbt Model Documentation

**Phase**: 3 - Documentation\
**Estimated Effort**: Small (1-2 hours)\
**Dependencies**: P1-002, P1-003 (models should be updated first)

## Objective

Add inline comments to dbt staging models explaining snapshot selection strategy and update staging layer README with snapshot governance overview.

## Context

This ticket ensures dbt model files themselves are self-documenting regarding snapshot governance. Future developers should be able to understand the selection strategy without reading external docs.

## Tasks

- [ ] Add comments to `stg_nflverse__player_stats` explaining snapshot strategy (baseline_plus_latest, fallback baseline_dt pattern)
- [ ] Add comments to `stg_nflverse__snap_counts` explaining snapshot strategy (baseline_plus_latest, fallback baseline_dt pattern)
- [ ] Add comments to `stg_nflverse__ff_opportunity` explaining snapshot strategy (latest_only, uses snapshot_selection_strategy macro for consistency)
- [ ] Update `dbt/ff_data_transform/models/staging/README.md` with snapshot governance overview
- [ ] Document baseline date choices and rationale

## Acceptance Criteria

- [ ] All staging models have snapshot strategy comments
- [ ] Comments explain WHY strategy chosen (not just WHAT)
- [ ] README provides staging layer overview including governance
- [ ] Baseline date rationale documented

## Implementation Notes

**Files to Update**:

1. `dbt/ff_data_transform/models/staging/nflverse/stg_nflverse__player_stats.sql`
2. `dbt/ff_data_transform/models/staging/nflverse/stg_nflverse__snap_counts.sql`
3. `dbt/ff_data_transform/models/staging/nflverse/stg_nflverse__ff_opportunity.sql`
4. `dbt/ff_data_transform/models/staging/README.md` (create if doesn't exist)

**Comment Style**:

```sql
/*
 * Snapshot Selection Strategy: baseline_plus_latest
 *
 * This model uses the baseline_plus_latest strategy to maintain historical
 * continuity while automatically picking up new snapshots. The baseline
 * snapshot (2025-10-01) provides complete 2020-2024 season data, while
 * the latest snapshot captures in-progress 2025 season.
 *
 * Baseline Date Rationale:
 *   2025-10-01 was chosen as baseline because it contains complete data
 *   through the 2024 season and represents a stable, validated snapshot.
 *
 * See: dbt/ff_data_transform/macros/snapshot_selection.sql
 * See: docs/ops/snapshot_management_current_state.md
 */

with source as (
  select * from read_parquet(
    '{{ env_var("RAW_NFLVERSE_WEEKLY_GLOB", "data/raw/nflverse/weekly/dt=*/*.parquet") }}'
  )
  where 1=1
    {{ snapshot_selection_strategy(
        env_var("RAW_NFLVERSE_WEEKLY_GLOB", "data/raw/nflverse/weekly/dt=*/*.parquet"),
        strategy='baseline_plus_latest',
        baseline_dt=var('NFLVERSE_BASELINE_DT', '2025-10-01')
    ) }}
)
```

**README Structure**:

`dbt/ff_data_transform/models/staging/README.md`

````markdown
# Staging Models

**Purpose**: Clean and standardize raw source data, preparing it for dimensional modeling.

## Snapshot Governance

Staging models use macro-based snapshot selection to eliminate hardcoded dates and enable automatic pickup of new snapshots.

### Selection Strategies

1. **baseline_plus_latest**: Select baseline snapshot + latest (for historical continuity)
   - Used by: `stg_nflverse__player_stats`, `stg_nflverse__snap_counts`
   - Rationale: Maintains complete historical data while capturing current season

2. **latest_only**: Select only the most recent snapshot
   - Used by: `stg_nflverse__ff_opportunity`
   - Rationale: Fantasy opportunity metrics only need current season
   - Note: Uses `snapshot_selection_strategy` macro (not direct `latest_snapshot_only` helper) for consistency

3. **all**: Load all snapshots (for backfills)
   - Used by: (none currently)
   - Rationale: Historical analysis requiring all snapshots

### Baseline Snapshots

| Source | Dataset | Baseline Date | Coverage | Notes |
|--------|---------|--------------|----------|-------|
| nflverse | weekly | 2025-10-01 | 2020-2024 | Complete through 2024 season |
| nflverse | snap_counts | 2025-10-01 | 2020-2024 | Complete through 2024 season |

**Why these dates?**
- Chosen as stable, validated snapshots with complete multi-season coverage
- Provide continuity when new snapshots have incomplete current-season data
- Can be updated once per season (e.g., 2026-01-15 for 2025 season completion)

### Configuration

Baseline dates configured via dbt vars:

```yaml
# dbt_project.yml
vars:
  NFLVERSE_BASELINE_DT: '2025-10-01'  # Fallback for all NFLverse datasets
  NFLVERSE_WEEKLY_BASELINE_DT: '2025-10-01'  # Specific override for weekly
  NFLVERSE_SNAP_BASELINE_DT: '2025-10-01'  # Specific override for snap_counts
```

**Fallback Pattern**: Models use `var('NFLVERSE_WEEKLY_BASELINE_DT', var('NFLVERSE_BASELINE_DT', '2025-10-01'))` to allow dataset-specific overrides while maintaining a common default.
````

### Schema Evolution

Models that read evolving schemas use `union_by_name=true`:

```sql
select * from read_parquet(
    '{{ ... }}',
    union_by_name=true  -- Handle new columns added in later snapshots
)
```

This allows DuckDB to handle new columns gracefully (fills with NULL for snapshots missing the column).

## Model Naming

- `stg_<source>__<entity>`: Staging model pattern
- One-to-one with source tables (no joins in staging)
- Light transformations only (renaming, casting, basic cleaning)

## Testing

All staging models have:

- Primary key tests (unique, not_null)
- Referential integrity tests (foreign keys to dims)
- Freshness tests (via source YAML)

Run tests:

```bash
cd dbt/ff_data_transform
uv run dbt test --select staging.*
```

## References

- Snapshot selection macro: `macros/snapshot_selection.sql`
- Snapshot registry: `seeds/snapshot_registry.csv`
- Ops docs: `docs/ops/snapshot_management_current_state.md`

````

## Testing

1. **Read comments**: Verify clarity and accuracy
2. **Test dbt compilation**: Ensure comments don't break SQL
3. **README accuracy**: Cross-check against actual implementation

```bash
# Test compilation
cd dbt/ff_data_transform
uv run dbt compile --select staging.nflverse.*
````

## References

- Plan: `../2025-11-07_plan_v_2_0.md` - Phase 3 Activity (lines 426-429)
- Checklist: `../2025-11-07_tasks_checklist_v_2_0.md` - Phase 3 dbt Docs (lines 259-262)
- Model files: `dbt/ff_data_transform/models/staging/nflverse/`
