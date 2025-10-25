/*
Spot check: Compare dim_player_contract_history with actual roster samples

Purpose: Validate specific player contracts against sample roster sheets

Sample data location: samples/sheets/{GM}/{GM}.parquet
Test cases from Jason's roster:
- C.J. Stroud: $2 (2025) + $8 (2026) = $10 total, 2 years, RFA
- De'Von Achane: $2 (2025) + $8 (2026) = $10 total, 2 years, RFA
- CeeDee Lamb: $58×4 years = $233 total, RFA + Franchise
- Jordan Mason: $8×4 years = $32 total
*/

-- First, let's see all current contracts for players on Jason's roster
select
  ch.player_name,
  ch.position,
  ch.franchise_name,
  ch.contract_type,
  ch.contract_total,
  ch.contract_years,
  ch.annual_amount,
  ch.contract_start_season,
  ch.contract_end_season,
  ch.is_current,
  ch.rfa_matched
from {{ ref('dim_player_contract_history') }} ch
where ch.franchise_name = 'Jason'
  and ch.is_current = true
order by ch.position, ch.player_name
