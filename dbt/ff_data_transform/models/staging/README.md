# Staging Models

**Purpose**: Clean and standardize raw source data, preparing it for dimensional modeling.

Use `stg_<provider>__<dataset>.sql` (double underscore between provider and dataset).

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

| Source   | Dataset     | Baseline Date | Coverage  | Notes                        |
| -------- | ----------- | ------------- | --------- | ---------------------------- |
| nflverse | weekly      | 2025-10-01    | 2020-2024 | Complete through 2024 season |
| nflverse | snap_counts | 2025-10-01    | 2020-2024 | Complete through 2024 season |

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

### Schema Evolution

Models that read evolving schemas use `union_by_name=true`:

```sql
select * from read_parquet(
    '{{ ... }}',
    union_by_name=true  -- Handle new columns added in later snapshots
)
```

This allows DuckDB to handle new columns gracefully (fills with NULL for snapshots missing the column).

## Normalization Policy (ELT)

- **Keep raw sources aligned with provider schemas** in external storage (`data/raw/`)
- **Apply minimal, consistent normalization** in staging for downstream stability
- **Staging models perform**:
  - Provider ID → canonical ID mapping via crosswalk (dim_player_id_xref staging model)
  - NULL filtering (document percentages in comments)
  - Long-form unpivots (wide → tall for fact tables)
  - Data quality filters

## Player Identity Resolution Pattern

All nflverse staging models follow this pattern:

```sql
-- base CTE: Keep raw provider IDs
select
  w.player_id as gsis_id_raw,  -- Preserve original column name
  ...

-- crosswalk CTE: Map to canonical mfl_id + create player_key
select
  base.* exclude (position),
  coalesce(xref.player_id, -1) as player_id,  -- Canonical mfl_id
  coalesce(base.position, xref.position) as position,  -- Fallback to xref
  -- Composite key for grain uniqueness
  case
    when coalesce(xref.player_id, -1) != -1
      then cast(xref.player_id as varchar)
    else coalesce(base.gsis_id_raw, 'UNKNOWN_' || base.game_id)
  end as player_key  -- Uses raw ID when unmapped
from base
left join {{ ref('dim_player_id_xref') }} xref
  on base.gsis_id_raw = xref.gsis_id
```

**Key principles**:

- `player_id`: Canonical business key (mfl_id), use for FK relationships
- `player_key`: Composite technical key for grain enforcement
- Unmapped players: `player_id = -1`, `player_key = raw_provider_id`
- Position fallback: Use crosswalk when raw data has NULL

## Data Quality Documentation

Every staging model documents:

- **NULL filtering**: Percentage and row count filtered
- **Crosswalk coverage**: Mapping success rate
- **Data characteristics**: Known issues, patterns

Example:

```sql
-- Data quality filters: Exclude records missing required identifiers
-- player_id (gsis_id): ~0.12% of raw data has NULL (113/97,415 rows)
--   These are unidentifiable players with no position info
--   Cannot perform player-level analysis without player identification
where w.player_id is not null
```

**Downstream dimensional modeling**: Staging models feed into core facts and dimensions. For patterns on surrogate keys, conformed dimensions, and entity resolution, see `../../../docs/architecture/kimball_modeling_guidance/kimbal_modeling.md`.

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
just dbt-test --select staging.*
```

## References

- Snapshot selection macro: `macros/snapshot_selection.sql`
- Snapshot registry: `seeds/snapshot_registry.csv`
- Ops docs: `docs/ops/snapshot_management_current_state.md`
