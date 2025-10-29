-- Test: Ensure player ID mapping coverage is acceptable
-- Fails if overall mapping rate is <90% or IDP mapping is <85%

with raw_projections as (
  -- Read directly from raw parquet to see ALL records (before staging filter)
  select
    pos as position,
    cast(player_id as integer) as player_id
  from read_parquet('{{ var("external_root", "data/raw") }}/ffanalytics/projections/dt=*/projections_consensus_*.parquet')
),

mapping_stats as (
  select
    case
      when position in ('DL', 'LB', 'DB') then 'IDP'
      when position in ('QB', 'RB', 'WR', 'TE', 'K') then 'Offensive'
      else 'Other'
    end as position_group,
    count(*) as total_records,
    sum(case when player_id > 0 then 1 else 0 end) as mapped_records,
    round(100.0 * sum(case when player_id > 0 then 1 else 0 end) / count(*), 1) as mapping_pct
  from raw_projections
  where position in ('QB', 'RB', 'WR', 'TE', 'K', 'DL', 'LB', 'DB')
  group by position_group
),

validation as (
  select
    position_group,
    total_records,
    mapped_records,
    mapping_pct,
    case position_group
      when 'IDP' then 85.0  -- IDP can be slightly lower due to newer players
      when 'Offensive' then 90.0
      else 80.0
    end as min_acceptable_pct,
    case
      when mapping_pct < case position_group
                          when 'IDP' then 85.0
                          when 'Offensive' then 90.0
                          else 80.0
                         end then 'FAIL'
      else 'PASS'
    end as test_result
  from mapping_stats
)

-- Return rows where mapping is below threshold
select
  position_group,
  total_records,
  mapped_records,
  mapping_pct,
  min_acceptable_pct,
  test_result
from validation
where test_result = 'FAIL'
