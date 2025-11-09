-- Grain: one row per rostered player in latest Sleeper snapshot
-- Purpose: Normalize Sleeper roster feed for roster parity checks
{{ config(materialized="view", unique_key=['roster_id', 'player_id']) }}
with
    raw_rosters as (
        select *
        from read_parquet('{{ var("external_root") }}/sleeper/rosters/dt=*/rosters_*.parquet', hive_partitioning = true)
        where
            {{ snapshot_selection_strategy(
                var("external_root") ~ '/sleeper/rosters/dt=*/rosters_*.parquet',
                strategy='latest_only'
            ) }}
    ),

    expanded as (
        select r.league_id, r.roster_id, r.owner_id, r.dt, p.player as sleeper_player_id
        from raw_rosters r
        cross join unnest(r.players) p(player)
        where p.player ~ '^[0-9]+$'
    ),

    player_xref as (
        select player_id, mfl_id, sleeper_id, coalesce(name, merge_name) as player_name, position as xref_position
        from {{ ref("dim_player_id_xref") }}
    ),

    roster_players as (
        select
            e.league_id,
            e.roster_id,
            e.owner_id,
            e.dt as asof_date,
            e.sleeper_player_id,
            xref.player_id,
            xref.mfl_id,
            xref.player_name,
            xref.xref_position
        from expanded e
        left join player_xref xref on xref.sleeper_id = try_cast(e.sleeper_player_id as integer)
    )

select
    player_id,
    mfl_id,
    sleeper_player_id,
    player_name,
    xref_position as position,
    league_id,
    roster_id,
    owner_id,
    asof_date,
    'sleeper' as source_platform,
    coalesce(player_id is not null, false) as is_mapped_to_dim_player
from roster_players
where player_id is not null
