{{ config(severity='warn') }}

-- Test: Alert if IDP projections come from too few sources (single point of failure)
-- Warns (not fails) if any IDP position has source_count < 2 for majority of players
--
-- CONTEXT: As of 2025-10-29, FantasySharks is our ONLY IDP source (see docs/findings/2025-10-29_idp_source_investigation.md)
-- This is an INDUSTRY LIMITATION, not a configuration issue:
--   - We scrape from ALL 9 sources (FantasyPros, NumberFire, FantasySharks, ESPN, FFToday, CBS, NFL, RTSports, Walterfootball)
--   - Only FantasySharks provides IDP stat projections (other sources have rankings only)
--   - IDP leagues are ~10% of fantasy market, so most sites don't invest in IDP projections
--
-- RISK: If FantasySharks goes down or changes format, we lose ALL IDP data
-- MITIGATION: Monitor closely, consider paid alternatives (Fantasy Nerds, IDP Guru) if needed

with latest_snapshot as (
  select max(dt) as latest_dt
  from read_parquet('{{ var("external_root", "data/raw") }}/ffanalytics/projections/dt=*/projections_consensus_*.parquet')
),

source_diversity as (
  select
    pos as position,
    source_count,
    count(*) as player_count,
    round(100.0 * count(*) / sum(count(*)) over (partition by pos), 1) as pct_of_position
  from read_parquet('{{ var("external_root", "data/raw") }}/ffanalytics/projections/dt=*/projections_consensus_*.parquet')
  where dt = (select latest_dt from latest_snapshot)
    and pos in ('DL', 'DB', 'LB')
  group by pos, source_count
),

single_source_positions as (
  select
    position,
    max(source_count) as max_sources,
    sum(case when source_count = 1 then player_count else 0 end) as single_source_players,
    sum(player_count) as total_players,
    round(100.0 * sum(case when source_count = 1 then player_count else 0 end) / sum(player_count), 1) as single_source_pct
  from source_diversity
  group by position
)

-- Return positions where >80% of players come from single source
-- This indicates single point of failure risk
select
  position,
  max_sources,
  single_source_players,
  total_players,
  single_source_pct,
  'WARN: Single source dependency' as alert_level
from single_source_positions
where single_source_pct > 80.0
order by position
