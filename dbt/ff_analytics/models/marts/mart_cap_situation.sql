-- Grain: franchise_id, season
-- Purpose: Comprehensive cap space view with reconciliation

{{ config(
    materialized='table'
) }}

with cap_reported as (
  select * from {{ ref('stg_sheets__cap_space') }}
),

active_contracts as (
  select
    franchise_id,
    obligation_year as season,
    SUM(cap_hit) as active_contracts_total
  from {{ ref('stg_sheets__contracts_active') }}
  group by franchise_id, obligation_year
),

dead_cap_calculated as (
  select
    franchise_id,
    obligation_year as season,
    SUM(dead_cap_amount) as dead_cap_total
  from {{ ref('stg_sheets__contracts_cut') }}
  group by franchise_id, obligation_year
),

franchise_dim as (
  select
    franchise_id,
    franchise_name,
    owner_name,
    division
  from {{ ref('dim_franchise') }}
  where is_current_owner
)

select
  fd.franchise_id,
  fd.franchise_name,
  fd.owner_name,
  fd.division,
  cr.season,

  -- Base
  cr.base_cap,

  -- Reported (from sheets)
  cr.available_cap_space as cap_space_available_reported,
  cr.dead_cap_space as dead_cap_reported,
  cr.traded_cap_space as traded_cap_net,

  -- Calculated (from contracts)
  COALESCE(ac.active_contracts_total, 0) as active_contracts_total,
  COALESCE(dc.dead_cap_total, 0) as dead_cap_calculated,

  -- Reconciliation
  (cr.base_cap + cr.traded_cap_space - COALESCE(ac.active_contracts_total, 0) - COALESCE(dc.dead_cap_total, 0))
    as cap_space_available_calculated,
  (
    cr.available_cap_space
    - (cr.base_cap + cr.traded_cap_space - COALESCE(ac.active_contracts_total, 0) - COALESCE(dc.dead_cap_total, 0))
  ) as reconciliation_difference,

  -- Final values (use reported per Commissioner)
  cr.available_cap_space as cap_space_available,

  -- Metadata
  cr.asof_date

from cap_reported cr
inner join franchise_dim fd on cr.franchise_id = fd.franchise_id
left join active_contracts ac
  on cr.franchise_id = ac.franchise_id and cr.season = ac.season
left join dead_cap_calculated dc
  on cr.franchise_id = dc.franchise_id and cr.season = dc.season

order by fd.franchise_name, cr.season
