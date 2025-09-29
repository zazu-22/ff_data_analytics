# Staging Models

Use `stg_<provider>__<dataset>.sql` (double underscore between provider and dataset).

Normalization policy (ELT)

- Keep raw sources aligned with provider schemas in external storage.
- Apply minimal, consistent normalization in staging for downstream stability.
- Example: nflverse weekly identifiers
  - Normalize to `gsis_id` with `coalesce(cast(gsis_id as varchar), cast(player_id as varchar)) as gsis_id`
  - Rationale: some raw snapshots label GSIS-style IDs as `player_id`; staging presents a canonical key.

**Downstream dimensional modeling**: Staging models feed into core facts and dimensions. For patterns on surrogate keys, conformed dimensions, and entity resolution, see `../../../docs/architecture/kimball_modeling_guidance/kimbal_modeling.md`.
