-- Analysis: Projection Mapping Diagnostics
-- Run with: dbt compile --select projection_mapping_diagnostics
-- Then: duckdb dbt/ff_analytics/target/dev.duckdb < dbt/ff_analytics/target/compiled/.../projection_mapping_diagnostics.sql
--
-- Provides detailed diagnostics on player ID mapping for projections

with raw_data as (
  select
    player,
    pos,
    team,
    cast(player_id as integer) as player_id,
    week
  from read_parquet('{{ var("external_root", "data/raw") }}/ffanalytics/projections/dt=*/projections_consensus_*.parquet')
  where week = (select max(week) from read_parquet('{{ var("external_root", "data/raw") }}/ffanalytics/projections/dt=*/projections_consensus_*.parquet'))
),

mapping_summary as (
  select
    pos as position,
    count(*) as total_players,
    sum(case when player_id > 0 then 1 else 0 end) as mapped_players,
    sum(case when player_id <= 0 then 1 else 0 end) as unmapped_players,
    round(100.0 * sum(case when player_id > 0 then 1 else 0 end) / count(*), 1) as mapping_pct
  from raw_data
  group by pos
  order by pos
),

unmapped_samples as (
  select
    player,
    pos,
    team,
    player_id,
    -- Check if name has comma (FantasySharks format)
    case when player like '%,%' then 'Last, First' else 'First Last' end as name_format
  from raw_data
  where player_id <= 0
  order by pos, player
  limit 20
)

select 'MAPPING SUMMARY BY POSITION' as section, null as detail
union all
select '=' as section, null as detail
union all
select position as section,
       printf('%d / %d mapped (%.1f%%)', mapped_players, total_players, mapping_pct) as detail
from mapping_summary

union all
select '' as section, null as detail
union all
select 'SAMPLE UNMAPPED PLAYERS (First 20)' as section, null as detail
union all
select '=' as section, null as detail
union all
select printf('[%s] %s (%s)', pos, player, team) as section,
       printf('player_id=%d, format=%s', player_id, name_format) as detail
from unmapped_samples

union all
select '' as section, null as detail
union all
select 'RECOMMENDATIONS' as section, null as detail
union all
select '=' as section, null as detail
union all
select '1. If IDP mapping is 0%' as section, 'Check R script name normalization is working' as detail
union all
select '2. If mapping is <90%' as section, 'Check for new name formats or player name issues' as detail
union all
select '3. If staging has 0 IDP records' as section, 'Check staging model is not filtering player_id=-1' as detail
