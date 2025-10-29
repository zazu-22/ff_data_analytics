-- Test: Ensure staging model is NOT filtering out IDP players
-- This test catches if the "WHERE player_id > 0" filter is re-introduced
--
-- Compares raw parquet record counts to staging model record counts
-- Fails if staging has significantly fewer IDP records than raw
--
-- NOTE: Raw data uses fantasy positions (DL, DB, LB) but staging uses NFL positions
-- (DE, DT, CB, S, LB) due to position-aware mapping from dim_position_translation

with latest_snapshot as (
  select max(dt) as latest_dt
  from read_parquet('{{ var("external_root", "data/raw") }}/ffanalytics/projections/dt=*/projections_consensus_*.parquet')
),

raw_counts as (
  select
    case
      when pos in ('DL', 'LB', 'DB') then 'IDP'
      when pos in ('QB', 'RB', 'WR', 'TE', 'K') then 'Offensive'
      else 'Other'
    end as position_group,
    count(*) as raw_record_count
  from read_parquet('{{ var("external_root", "data/raw") }}/ffanalytics/projections/dt=*/projections_consensus_*.parquet')
  where pos in ('QB', 'RB', 'WR', 'TE', 'K', 'DL', 'LB', 'DB')
    and dt = (select latest_dt from latest_snapshot)
  group by position_group
),

staging_counts as (
  select
    case
      -- NFL defensive positions from position-aware mapping
      when position in ('DE', 'DT', 'LB', 'CB', 'S') then 'IDP'
      when position in ('QB', 'RB', 'WR', 'TE', 'K', 'PK') then 'Offensive'
      else 'Other'
    end as position_group,
    count(*) as staging_record_count
  from {{ ref('stg_ffanalytics__projections') }}
  group by position_group
),

comparison as (
  select
    r.position_group,
    r.raw_record_count,
    coalesce(s.staging_record_count, 0) as staging_record_count,
    round(100.0 * coalesce(s.staging_record_count, 0) / r.raw_record_count, 1) as retention_pct,
    case
      -- Allow 10% loss for legitimate filtering (bad data, etc.)
      -- But flag if >10% loss (suggests filtering bug)
      when coalesce(s.staging_record_count, 0) < (r.raw_record_count * 0.90) then 'FAIL'
      else 'PASS'
    end as test_result
  from raw_counts r
  left join staging_counts s on r.position_group = s.position_group
)

-- Return rows where retention is too low
select
  position_group,
  raw_record_count,
  staging_record_count,
  retention_pct,
  test_result
from comparison
where test_result = 'FAIL'
