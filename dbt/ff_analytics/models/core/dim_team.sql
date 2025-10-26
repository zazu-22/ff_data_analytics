{{ config(materialized='table') }}

/*
NFL team dimension - static reference for all NFL team-based analysis.

Grain: One row per NFL team (team_abbr as natural key)
Source: nflverse teams dataset + conference/division seed

This dimension is fairly static - teams rarely change names, locations, or divisions.
Denormalized to include conference and division (Kimball pattern - avoid snowflaking).
*/

with base_teams as (
  select
    team,
    "full" as team_name,
    location as team_city,
    season
  from
    read_parquet(
      '{{ env_var("RAW_NFLVERSE_TEAMS_GLOB", "data/raw/nflverse/teams/dt=*/*.parquet") }}'
    )
  -- Deduplicate to ensure one row per team (take latest season if dataset partitioned by season)
  qualify row_number() over (partition by team order by season desc) = 1
)

select
  -- Natural key (team abbreviation - stable across seasons)
  t.team as team_id,

  -- Team identity
  t.team_name,
  t.team_city,
  t.team as team_abbr,

  -- Hierarchical attributes (denormalized - no snowflaking)
  cd.conference,  -- AFC or NFC
  cd.division,    -- North, South, East, West

  -- Additional attributes (not in current nflverse endpoint)
  null as team_color,
  null as team_color2,
  null as team_logo_wikipedia,
  null as team_logo_espn,
  null as team_wordmark

from base_teams as t
left join {{ ref('dim_team_conference_division') }} as cd
  on t.team = cd.team_abbr
