{{ config(materialized='table') }}

/*
Fantasy projections mart - weekly/season player projections with fantasy scoring applied.

Grain: One row per player per season per week per horizon per asof_date
Source: mart_real_world_projections (with scoring rules applied from dim_scoring_rule)

Part of 2×2 model:
- Real-world base: mart_real_world_projections (physical stats)
- Fantasy scoring: This mart (applies dim_scoring_rule dynamically)

League scoring: Half-PPR (no IDP in projections)
*/

with real_world as (
  select * from {{ ref('mart_real_world_projections') }}
),

scoring as (
  select
    stat_name,
    points_per_unit
  from {{ ref('dim_scoring_rule') }}
  where is_current = true
),

-- Pivot scoring rules into a single row for easy lookup
scoring_pivoted as (
  select
    max(case when stat_name = 'pass_yard_point' then points_per_unit end) as pass_yard_point,
    max(case when stat_name = 'pass_td' then points_per_unit end) as pass_td,
    max(case when stat_name = 'pass_int' then points_per_unit end) as pass_int,
    max(case when stat_name = 'rush_yard_point' then points_per_unit end) as rush_yard_point,
    max(case when stat_name = 'rush_td' then points_per_unit end) as rush_td,
    max(case when stat_name = 'rush_lost_fumble' then points_per_unit end) as rush_lost_fumble,
    max(case when stat_name = 'rec_reception' then points_per_unit end) as rec_reception,
    max(case when stat_name = 'rec_yard_point' then points_per_unit end) as rec_yard_point,
    max(case when stat_name = 'rec_td' then points_per_unit end) as rec_td,
    max(case when stat_name = 'rec_lost_fumble' then points_per_unit end) as rec_lost_fumble
  from scoring
)

select
  rw.*,

  -- Fantasy points calculation (data-driven from dim_scoring_rule)
  -- Offensive scoring only (projections don't include IDP)
  (rw.passing_yards * s.pass_yard_point)
  + (rw.passing_tds * s.pass_td)
  + (rw.interceptions * s.pass_int)  -- Negative value in seed

  + (rw.rushing_yards * s.rush_yard_point)
  + (rw.rushing_tds * s.rush_td)
  + (rw.fumbles_lost * s.rush_lost_fumble)  -- Negative value in seed

  + (rw.receptions * s.rec_reception)  -- Half-PPR from seed
  + (rw.receiving_yards * s.rec_yard_point)
  + (rw.receiving_tds * s.rec_td)
  + (rw.fumbles_lost * s.rec_lost_fumble)  -- Negative value in seed (using same fumble rule)

    as projected_fantasy_points

from real_world as rw
cross join scoring_pivoted as s
