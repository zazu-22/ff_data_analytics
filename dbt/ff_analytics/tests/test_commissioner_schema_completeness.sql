with schema_check as (
  select
    'contracts_active' as table_name,
    count(*) filter (where column_name = 'gm_tab') as has_gm_tab
  from (
    describe select * from {{ source('sheets_raw', 'contracts_active') }} limit 1
  )

  union all

  select
    'contracts_cut',
    count(*) filter (where column_name = 'gm_tab')
  from (
    describe select * from {{ source('sheets_raw', 'contracts_cut') }} limit 1
  )

  union all

  select
    'cap_space',
    count(*) filter (where column_name = 'gm_tab')
  from (
    describe select * from {{ source('sheets_raw', 'cap_space') }} limit 1
  )

  union all

  select
    'draft_picks',
    count(*) filter (where column_name = 'gm_tab')
  from (
    describe select * from {{ source('sheets_raw', 'draft_picks') }} limit 1
  )
),

failures as (
  select
    table_name,
    'Missing gm_tab column - re-run ingestion' as error
  from schema_check
  where has_gm_tab = 0
)

select * from failures
