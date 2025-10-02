{{ config(materialized='table') }}

/*
Player dimension - conformed dimension for all player-based analysis.

Grain: One row per player (mfl_id as canonical player_id)
Source: dim_player_id_xref seed (nflverse ff_playerids with 19 provider ID mappings)

SCD Type 1 (overwrite): team (current team assignment)
SCD Type 0 (immutable): draft_year, birthdate

Attributes include display name, position, team, and all provider ID mappings
for cross-platform integration.
*/

select
  -- Primary key (canonical player identifier per ADR-010)
  mfl_id as player_id,

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

from {{ ref('dim_player_id_xref') }}
