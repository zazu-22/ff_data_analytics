{{
  config(
    materialized='table',
    indexes=[
      {'columns': ['player_id']},
      {'columns': ['game_id']},
      {'columns': ['season', 'week']},
      {'columns': ['stat_name']}
    ]
  )
}}

/*
Consolidated fact table for all NFL player statistics.

Grain: One row per player per game per stat per provider
Sources:
  - stg_nflverse__player_stats (~50 base stat types)
  - stg_nflverse__snap_counts (6 snap stat types)
  - stg_nflverse__ff_opportunity (32 opportunity stat types)

Total: ~88 stat types

ADR-009: Single consolidated fact table avoids fact-to-fact joins
ADR-010: Uses mfl_id as canonical player_id

Composite key: (player_id, game_id, stat_name, provider, measure_domain, stat_kind)
*/

-- Union all three staging sources
select * from {{ ref('stg_nflverse__player_stats') }}

union all

select * from {{ ref('stg_nflverse__snap_counts') }}

union all

select * from {{ ref('stg_nflverse__ff_opportunity') }}
