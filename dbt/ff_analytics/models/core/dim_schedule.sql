{{ config(materialized='table') }}

/*
NFL game schedule dimension - one row per game for all temporal analysis.

Grain: One row per game (game_id as natural key)
Source: nflverse schedule dataset

Includes game timing, participating teams, results, and game context.
Used to resolve game_id for player stats and provide game-level attributes.
*/

select
  -- Primary key
  game_id,

  -- Temporal attributes
  season,
  week,
  game_type as season_type,  -- REG, POST, WC, DIV, CON, SB, PRE
  gameday as game_date,
  gametime,
  weekday,

  -- Participating teams
  home_team as home_team_id,
  away_team as away_team_id,

  -- Game results
  home_score,
  away_score,

  -- Result flags
  result,  -- Home team result: positive = win margin, negative = loss margin, 0 = tie

  -- Game context
  location,  -- Stadium
  roof,  -- dome, outdoors, closed, open
  surface,  -- grass, fieldturf, astroturf, etc.
  temp,  -- Temperature
  wind,  -- Wind speed

  -- Playoff context
  div_game,  -- Divisional game flag
  overtime,  -- OT flag

  -- Broadcasting
  stadium,
  stadium_id

from read_parquet(
  '{{ env_var("RAW_NFLVERSE_SCHEDULE_GLOB", "../../data/raw/nflverse/schedule/dt=*/*.parquet") }}'
)
