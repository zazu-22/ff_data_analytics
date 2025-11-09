{{
    config(
        materialized="table",
        unique_key=['player_key', 'game_id', 'stat_name', 'provider', 'measure_domain', 'stat_kind'],
        indexes=[
            {"columns": ["player_id"]},
            {"columns": ["game_id"]},
            {"columns": ["season", "week"]},
            {"columns": ["stat_name"]},
        ],
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
ADR-011: Uses sequential surrogate player_id as canonical identifier

Composite key: (player_id, game_id, stat_name, provider, measure_domain, stat_kind)
*/
-- Union all three staging sources
select
    player_id,
    player_key,
    game_id,
    season,
    week,
    season_type,
    position,
    stat_name,
    stat_value,
    measure_domain,
    stat_kind,
    provider
from {{ ref("stg_nflverse__player_stats") }}

union all

select
    player_id,
    player_key,
    game_id,
    season,
    week,
    season_type,
    position,
    stat_name,
    stat_value,
    measure_domain,
    stat_kind,
    provider
from {{ ref("stg_nflverse__snap_counts") }}

union all

select
    player_id,
    player_key,
    game_id,
    season,
    week,
    season_type,
    position,
    stat_name,
    stat_value,
    measure_domain,
    stat_kind,
    provider
from {{ ref("stg_nflverse__ff_opportunity") }}
