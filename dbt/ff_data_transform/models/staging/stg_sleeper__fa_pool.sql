-- Grain: player_key (one row per FA player)
-- Purpose: All available free agents with fantasy relevance
{{ config(materialized="view", unique_key=['player_key', 'asof_date']) }}

with
    fa_raw as (
        -- Read only players from the latest snapshot
        select fa.*
        from
            read_parquet(
                '{{ var("external_root") }}/sleeper/fa_pool/dt=*/fa_pool_*.parquet', hive_partitioning = true
            ) fa
        where
            {{
                snapshot_selection_strategy(
                    var("external_root") ~ "/sleeper/fa_pool/dt=*/fa_pool_*.parquet",
                    strategy="latest_only"
                )
            }}
    ),

    player_xref as (
        select player_id, mfl_id, sleeper_id, coalesce(name, merge_name) as player_name, position as xref_position
        from {{ ref("dim_player_id_xref") }}
    )

select
    -- Identity (map sleeper_id → mfl_id)
    coalesce(
        cast(xref.player_id as varchar), cast(xref.mfl_id as varchar), 'sleeper_' || fa.sleeper_player_id
    ) as player_key,
    xref.player_id,
    xref.mfl_id,
    fa.sleeper_player_id,

    -- Demographics
    coalesce(xref.player_name, fa.full_name) as player_name,
    coalesce(xref.xref_position, fa.position) as position,
    fa.team as nfl_team,
    fa.age,
    fa.years_exp as nfl_experience,

    -- Status
    fa.status as nfl_status,
    fa.injury_status,
    fa.fantasy_positions,  -- Array of eligible positions

    -- Metadata
    current_date as asof_date,
    'sleeper' as source_platform,

    -- Mapping flag
    coalesce(xref.player_id is not null, false) as is_mapped_to_dim_player

from fa_raw fa
left join player_xref xref on fa.sleeper_player_id = xref.sleeper_id

where
    -- Filter to fantasy-relevant positions
    fa.position in ('QB', 'RB', 'WR', 'TE', 'K', 'PK', 'DL', 'LB', 'DB', 'DEF', 'S', 'CB', 'DE', 'DT')
