# Staging Models

Use `stg_<provider>__<dataset>.sql` (double underscore between provider and dataset).

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
