-- Grain: franchise_id, season
-- Source: data/raw/commissioner/cap_space/dt=*/cap_space.parquet
-- Purpose: Stage cap space data from Commissioner Sheet
{{ config(materialized="view") }}

with
    cap_raw as (
        select *
        from {{ source("sheets_raw", "cap_space") }}
        -- Get only the latest snapshot per franchise/season (dt partition)
        qualify row_number() over (partition by gm_tab, season order by dt desc) = 1
    ),

    franchise_xref as (
        select franchise_id, gm_tab, season_start, coalesce(season_end, 9999) as season_end
        from {{ ref("dim_franchise") }}
    )

select
    fx.franchise_id,
    cr.season,
    cr.available_cap_space::int as available_cap_space,
    cr.dead_cap_space::int as dead_cap_space,
    cr.traded_cap_space::int as traded_cap_space,
    250 as base_cap,
    current_date as asof_date

from cap_raw cr
inner join
    franchise_xref fx
    on cr.gm_tab = fx.gm_tab  -- Clean join on tab name!
    and cr.season between fx.season_start and fx.season_end
