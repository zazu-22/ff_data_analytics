{{ config(materialized='table') }}

/*
NFL team dimension - static reference for all NFL team-based analysis.

Grain: One row per NFL team (team_abbr as natural key)
Source: nflverse teams dataset

This dimension is fairly static - teams rarely change names, locations, or divisions.
Denormalized to include conference and division (Kimball pattern - avoid snowflaking).
*/

select
  -- Natural key (team abbreviation - stable across seasons)
  team_abbr as team_id,

  -- Team identity
  team_name,
  team_city,
  team_abbr,

  -- Hierarchical attributes (denormalized - no snowflaking)
  team_conf as conference,  -- AFC or NFC
  team_division as division,  -- North, South, East, West

  -- Additional attributes
  team_color,
  team_color2,
  team_logo_wikipedia,
  team_logo_espn,
  team_wordmark

from read_parquet(
  '{{ env_var("RAW_NFLVERSE_TEAMS_GLOB", "../../data/raw/nflverse/teams/dt=*/*.parquet") }}'
)
-- Deduplicate to ensure one row per team (take latest season if dataset partitioned by season)
qualify row_number() over (partition by team_abbr order by season desc) = 1
