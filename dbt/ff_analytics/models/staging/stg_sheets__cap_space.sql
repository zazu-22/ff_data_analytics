-- Grain: franchise_id, season
-- Source: data/raw/commissioner/cap_space/dt=*/cap_space.parquet
-- Purpose: Stage cap space data from Commissioner Sheet

{{ config(
    materialized='view'
) }}

with cap_raw as (
  select
    *,
    -- Extract first name from full GM name (e.g., "Jason Shaffer" → "Jason")
    SPLIT_PART(gm, ' ', 1) as gm_first_name
  from {{ source('sheets_raw', 'cap_space') }}
),

franchise_xref as (
  select
    franchise_id,
    owner_name,
    season_start,
    COALESCE(season_end, 9999) as season_end
  from {{ ref('dim_franchise') }}
)

select
  fx.franchise_id,
  cr.season,
  cr.available_cap_space::int as available_cap_space,
  cr.dead_cap_space::int as dead_cap_space,
  cr.traded_cap_space::int as traded_cap_space,
  250 as base_cap,
  CURRENT_DATE as asof_date

from cap_raw cr
inner join franchise_xref fx
  on
    cr.gm_first_name = fx.owner_name
    and cr.season between fx.season_start and fx.season_end
