-- Test: Ensure IDP projections are present in staging
-- Fails if any NFL defensive positions are missing or have <100 records
-- NOTE: Projections use NFL positions (DE, DT, CB, S) not fantasy positions (DL, DB)
-- due to position-aware mapping from dim_position_translation

with position_counts as (
  select
    position,
    count(*) as record_count
  from {{ ref('stg_ffanalytics__projections') }}
  where position in ('DE', 'DT', 'LB', 'CB', 'S')
  group by position
),

expected_positions as (
  select 'DE' as position, 100 as min_expected_records
  union all
  select 'DT', 100
  union all
  select 'LB', 100
  union all
  select 'CB', 100
  union all
  select 'S', 100
),

validation as (
  select
    e.position,
    coalesce(p.record_count, 0) as actual_records,
    e.min_expected_records,
    case
      when coalesce(p.record_count, 0) < e.min_expected_records then 'FAIL'
      else 'PASS'
    end as test_result
  from expected_positions e
  left join position_counts p on e.position = p.position
)

-- Return rows where test fails (dbt will fail if any rows returned)
select
  position,
  actual_records,
  min_expected_records,
  test_result
from validation
where test_result = 'FAIL'
