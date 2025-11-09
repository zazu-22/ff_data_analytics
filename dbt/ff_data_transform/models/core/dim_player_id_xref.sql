{{ config(materialized="table") }}

/*
Player ID crosswalk - backward compatibility model for dim_player_id_xref.

This model provides backward compatibility for all models that reference
dim_player_id_xref via ref('dim_player_id_xref').

**Source**: stg_nflverse__ff_playerids (staging model with deduplication logic)
**Migration**: Previously a seed (CSV), now a staging model for always-fresh data
**Migration date**: 2025-11-06

All downstream models continue to work without modification.
*/
select
    player_id,
    mfl_id,
    gsis_id,
    sleeper_id,
    espn_id,
    yahoo_id,
    pfr_id,
    fantasypros_id,
    pff_id,
    cbs_id,
    ktc_id,
    sportradar_id,
    fleaflicker_id,
    rotowire_id,
    rotoworld_id,
    stats_id,
    stats_global_id,
    fantasy_data_id,
    swish_id,
    cfbref_id,
    nfl_id,
    name,
    merge_name,
    name_last_first,
    position,
    team,
    birthdate,
    draft_year,
    xref_correction_status
from {{ ref("stg_nflverse__ff_playerids") }}
