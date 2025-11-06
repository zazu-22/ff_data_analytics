with commissioner_sources as (
  select distinct gm as gm_name, 'contracts_active' as source
  from {{ source('sheets_raw', 'contracts_active') }}

  union

  select distinct gm, 'contracts_cut'
  from {{ source('sheets_raw', 'contracts_cut') }}

  union

  select distinct gm, 'cap_space'
  from {{ source('sheets_raw', 'cap_space') }}

  union

  select distinct gm, 'draft_picks'
  from {{ source('sheets_raw', 'draft_picks') }}
),

mapped_gms as (
  select distinct owner_name || ' ' || gm_tab as expected_pattern
  from {{ ref('dim_franchise') }}
  where is_current_owner = true
),

unmapped as (
  select
    c.gm_name,
    c.source,
    'Unmapped GM - add to dim_franchise' as error_msg
  from commissioner_sources c
  left join mapped_gms m on c.gm_name like '%' || m.expected_pattern || '%'
  where m.expected_pattern is null
)

select * from unmapped
