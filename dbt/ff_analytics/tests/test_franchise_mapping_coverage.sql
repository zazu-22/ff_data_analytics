with commissioner_sources as (
  select distinct gm as gm_name,
    gm_tab,
    'contracts_active' as source
  from { { source('sheets_raw', 'contracts_active') } }
  union
  select distinct gm,
    gm_tab,
    'contracts_cut'
  from { { source('sheets_raw', 'contracts_cut') } }
  union
  select distinct gm,
    gm_tab,
    'cap_space'
  from { { source('sheets_raw', 'cap_space') } }
  union
  select distinct gm,
    gm_tab,
    'draft_picks'
  from { { source('sheets_raw', 'draft_picks') } }
),
mapped_franchises as (
  select distinct gm_tab
  from { { ref('dim_franchise') } }
  where is_current_owner = true
),
unmapped as (
  select c.gm_name,
    c.gm_tab,
    c.source,
    case
      when c.gm_tab is null
      or c.gm_tab = '' then 'Missing gm_tab in raw commissioner data'
      else 'gm_tab not found in dim_franchise (update seed or ingestion)'
    end as error_msg
  from commissioner_sources c
    left join mapped_franchises m on c.gm_tab = m.gm_tab
  where m.gm_tab is null
)
select *
from unmapped
