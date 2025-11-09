{{ config(materialized="table", unique_key='player_id') }}

/*
Player dimension - conformed dimension for all player-based analysis.

Grain: One row per player (player_id as canonical identifier)
Source: dim_player_id_xref staging model (stg_nflverse__ff_playerids with deduplication logic)

SCD Type 1 (overwrite): team (current team assignment)
SCD Type 0 (immutable): draft_year, birthdate

Attributes include display name, position, team, and all provider ID mappings
for cross-platform integration.

Key Design Decision: player_id (sequential surrogate key) is the canonical identifier
used throughout the pipeline. mfl_id remains available as an attribute for provider
integration but is NOT the primary key.
*/
select
    -- Primary key (canonical player identifier - sequential from crosswalk)
    player_id,

    -- Display attributes
    name as display_name,
    merge_name as searchable_name,  -- Normalized for fuzzy matching
    position,
    team as current_team,

    -- Static attributes (SCD Type 0 - never changes)
    birthdate,
    draft_year,

    -- Provider ID mappings (19 platforms for cross-platform integration)
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
    nfl_id

from {{ ref("dim_player_id_xref") }}
