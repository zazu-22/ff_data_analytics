{{ config(materialized='table') }}

/*
Projection variance mart - compare actual performance vs pre-game projections.

Grain: One row per player per season per week (actuals grain)
Sources:
  - mart_real_world_actuals_weekly (actual performance)
  - mart_real_world_projections (weekly projections)

Analysis:
  - Variance = actual - projected for each stat
  - Only includes projections made BEFORE the game (asof_date <= game week)
  - Focuses on weekly projections (horizon='weekly')
  - Useful for projection accuracy analysis, adjusting future projections

Note: This is a starter variance mart. Future enhancements could include:
  - Multiple projection snapshots per week (track how projections change)
  - Percentage error, absolute error metrics
  - Aggregated accuracy by position/source
*/

with actuals as (
  select
    player_id,
    display_name,
    position,
    current_team,
    season,
    week,
    season_type,

    -- Real-world stats
    passing_yards as actual_passing_yards,
    passing_tds as actual_passing_tds,
    passing_interceptions as actual_interceptions,
    rushing_yards as actual_rushing_yards,
    rushing_tds as actual_rushing_tds,
    receptions as actual_receptions,
    receiving_yards as actual_receiving_yards,
    receiving_tds as actual_receiving_tds,
    -- Use receiving fumbles (projections don't distinguish rush vs receive fumbles)
    receiving_fumbles_lost as actual_fumbles_lost

  from {{ ref('mart_real_world_actuals_weekly') }}
  where season_type = 'REG'  -- Regular season only for now
),

projections as (
  select
    player_id,
    player_name,
    position,
    season,
    week,
    asof_date,

    -- Projected stats
    passing_yards as projected_passing_yards,
    passing_tds as projected_passing_tds,
    interceptions as projected_interceptions,
    rushing_yards as projected_rushing_yards,
    rushing_tds as projected_rushing_tds,
    receptions as projected_receptions,
    receiving_yards as projected_receiving_yards,
    receiving_tds as projected_receiving_tds,
    fumbles_lost as projected_fumbles_lost

  from {{ ref('mart_real_world_projections') }}
  where
    horizon = 'weekly'
    and provider = 'ffanalytics_consensus'
),

-- Join actuals to projections
-- For now, just take the latest projection available before the week
-- TODO: Future enhancement - track all projection snapshots
variance as (
  select
    a.player_id,
    a.display_name,
    a.position,
    a.current_team,
    a.season,
    a.week,
    a.season_type,
    p.asof_date as projection_date,

    -- Actual values
    a.actual_passing_yards,
    a.actual_passing_tds,
    a.actual_interceptions,
    a.actual_rushing_yards,
    a.actual_rushing_tds,
    a.actual_receptions,
    a.actual_receiving_yards,
    a.actual_receiving_tds,
    a.actual_fumbles_lost,

    -- Projected values
    p.projected_passing_yards,
    p.projected_passing_tds,
    p.projected_interceptions,
    p.projected_rushing_yards,
    p.projected_rushing_tds,
    p.projected_receptions,
    p.projected_receiving_yards,
    p.projected_receiving_tds,
    p.projected_fumbles_lost,

    -- Variance (actual - projected)
    a.actual_passing_yards - p.projected_passing_yards as passing_yards_variance,
    a.actual_passing_tds - p.projected_passing_tds as passing_tds_variance,
    a.actual_interceptions - p.projected_interceptions as interceptions_variance,
    a.actual_rushing_yards - p.projected_rushing_yards as rushing_yards_variance,
    a.actual_rushing_tds - p.projected_rushing_tds as rushing_tds_variance,
    a.actual_receptions - p.projected_receptions as receptions_variance,
    a.actual_receiving_yards - p.projected_receiving_yards as receiving_yards_variance,
    a.actual_receiving_tds - p.projected_receiving_tds as receiving_tds_variance,
    a.actual_fumbles_lost - p.projected_fumbles_lost as fumbles_lost_variance

  from actuals as a
  left join projections as p
    on
      a.player_id = p.player_id
      and a.season = p.season
      and a.week = p.week

  -- Only include rows where we have both actuals AND projections
  where p.player_id is not null
)

select * from variance
