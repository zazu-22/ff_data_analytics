-- Test: Ensure IDP projections are present in staging
-- Fails if any of DL, LB, DB positions are missing or have <100 records

with position_counts as (
  select
    position,
    count(*) as record_count
  from {{ ref('stg_ffanalytics__projections') }}
  where position in ('DL', 'LB', 'DB')
  group by position
),

expected_positions as (
  select 'DL' as position, 500 as min_expected_records
  union all
  select 'LB', 400
  union all
  select 'DB', 500
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
