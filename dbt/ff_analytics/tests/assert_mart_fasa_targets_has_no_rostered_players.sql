-- Ensure mart_fasa_targets excludes players who are currently rostered
with rostered_players as (
  select fa.player_id,
    fa.player_name,
    c.franchise_id,
    c.obligation_year
  from { { ref('mart_fasa_targets') } } fa
    inner join { { ref('mart_contract_snapshot_current') } } c on fa.player_id = c.player_id
    and c.obligation_year = YEAR(CURRENT_DATE)
)
select *
from rostered_players
