{{ config(materialized='view') }}

/*
Pick valuation dimension with provisional position estimates.

Purpose: Assign market values to draft picks, including conditional/TBD picks.

Grain: One row per pick_id (including TBD provisionals)

Key Logic:
- Base picks: Use actual overall_pick for overall pick number
- Compensatory picks: Place after base picks in same round
- TBD picks: Estimate position based on current/prior season standings

Dependencies:
- {{ ref('dim_pick') }} - Base pick catalog
- Sleeper standings (future): Current season standings for provisional picks
- KTC market values (future): Pick valuation by overall pick number

Provisional Methods:
- 'mid_round': Assume middle of round (slot 6-7 out of 12)
- 'prior_standings': Use previous season final standings
- 'current_standings': Use current season standings (updates weekly)
*/

with pick_base as (
  select
    pick_id,
    season,
    round,
    overall_pick,
    pick_type,
    notes
  from {{ ref('dim_pick') }}
),

overall_pick_number as (
  -- Calculate overall draft position (1-60 base, 61+ for comp picks)
  select
    pick_id,
    season,
    round,
    overall_pick,
    pick_type,
    notes,

    -- Overall pick number accounts for comp picks in prior rounds
    row_number() over (
      partition by season
      order by round, overall_pick
    ) as overall_pick_number,

    -- Within-round position
    row_number() over (
      partition by season, round
      order by overall_pick
    ) as round_pick_number

  from pick_base
  where pick_type != 'conditional'  -- Exclude TBD picks from base numbering
),

-- TODO: Add Sleeper standings integration for provisional picks
-- For now, TBD picks use overall_pick=99 as placeholder
tbd_provisional as (
  select
    pick_id,
    season,
    round,
    overall_pick,
    pick_type,
    notes,

    -- Provisional overall number: Mid-round estimate
    -- Assumes 6 picks before and 6 after (slot 7 of 12)
    ((round - 1) * 12) + 7 as overall_pick_number,

    7 as round_pick_number  -- Mid-round estimate

  from pick_base
  where pick_type = 'conditional'
),

combined as (
  select * from overall_pick_number
  union all
  select * from tbd_provisional
)

select
  pick_id,
  season,
  round,
  overall_pick,
  pick_type,
  overall_pick_number,
  round_pick_number,

  -- Provisional flag for KTC value lookup
  case
    when pick_type = 'conditional' then true
    else false
  end as is_provisional,

  -- TODO: Join to KTC pick values
  -- For now, return null - will populate when KTC integration is complete
  cast(null as double) as ktc_value_1qb,
  cast(null as double) as ktc_value_sf,

  notes

from combined
