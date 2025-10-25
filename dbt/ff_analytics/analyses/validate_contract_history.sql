/*
Validation script: Cross-reference dim_player_contract_history with fact_league_transactions

Purpose: Ensure contract history accurately reflects the transaction event log

Validation checks:
1. Current contracts match most recent transaction
2. No gaps in contract periods
3. Dead cap calculations are reasonable
4. Contract dates align with transaction dates
5. All contract-creating transactions have history entries
*/

-- Check 1: Current contracts should match most recent transaction
with most_recent_transactions as (
  select
    player_id,
    max(transaction_date) as last_transaction_date,
    count(*) as total_transactions
  from {{ ref('fact_league_transactions') }}
  where asset_type = 'player'
    and player_id is not null
    and player_id != -1
    and to_franchise_id is not null
    and transaction_type in (
      'rookie_draft_selection',
      'faad',
      'fasa',
      'trade',
      'trade_player',
      'extension',
      'restructure'
    )
    and contract_total is not null
  group by player_id
),

current_contracts as (
  select
    player_id,
    franchise_id,
    contract_type,
    effective_date,
    contract_total,
    contract_years,
    is_current
  from {{ ref('dim_player_contract_history') }}
  where is_current = true
)

select
  'Check 1: Current Contract Dates' as validation_check,
  count(*) as total_current_contracts,
  count(case when cc.effective_date = mrt.last_transaction_date then 1 end) as matching_dates,
  count(case when cc.effective_date != mrt.last_transaction_date then 1 end) as mismatched_dates,
  round(
    count(case when cc.effective_date = mrt.last_transaction_date then 1 end)::numeric
    / count(*)::numeric * 100,
    2
  ) as match_pct
from current_contracts cc
join most_recent_transactions mrt on cc.player_id = mrt.player_id

union all

-- Check 2: Contract period gaps (should not skip numbers)
select
  'Check 2: Contract Period Gaps' as validation_check,
  count(distinct player_id) as total_players,
  count(case when gap_size > 0 then 1 end) as players_with_gaps,
  max(gap_size) as max_gap_size,
  null as match_pct
from (
  select
    player_id,
    contract_period,
    lag(contract_period) over (partition by player_id order by contract_period) as prev_period,
    contract_period - lag(contract_period) over (partition by player_id order by contract_period) - 1 as gap_size
  from {{ ref('dim_player_contract_history') }}
) gaps
where prev_period is not null

union all

-- Check 3: Reasonable dead cap values (should be <= contract_total)
select
  'Check 3: Dead Cap Reasonableness' as validation_check,
  count(*) as total_current_contracts,
  count(case when dead_cap_if_cut_today <= contract_total then 1 end) as reasonable_dead_cap,
  count(case when dead_cap_if_cut_today > contract_total then 1 end) as excessive_dead_cap,
  round(
    count(case when dead_cap_if_cut_today <= contract_total then 1 end)::numeric
    / count(*)::numeric * 100,
    2
  ) as match_pct
from {{ ref('dim_player_contract_history') }}
where is_current = true
  and dead_cap_if_cut_today is not null

union all

-- Check 4: Contract year alignment (end >= start)
select
  'Check 4: Contract Year Alignment' as validation_check,
  count(*) as total_contracts,
  count(case when contract_end_season >= contract_start_season then 1 end) as valid_dates,
  count(case when contract_end_season < contract_start_season then 1 end) as invalid_dates,
  round(
    count(case when contract_end_season >= contract_start_season then 1 end)::numeric
    / count(*)::numeric * 100,
    2
  ) as match_pct
from {{ ref('dim_player_contract_history') }}

union all

-- Check 5: All contract transactions have history entries
select
  'Check 5: Transaction Coverage' as validation_check,
  count(*) as total_contract_transactions,
  count(ch.transaction_id_unique) as transactions_with_history,
  count(*) - count(ch.transaction_id_unique) as missing_history_entries,
  round(
    count(ch.transaction_id_unique)::numeric / count(*)::numeric * 100,
    2
  ) as match_pct
from {{ ref('fact_league_transactions') }} ft
left join {{ ref('dim_player_contract_history') }} ch
  on ft.transaction_id_unique = ch.transaction_id_unique
where ft.asset_type = 'player'
  and ft.player_id is not null
  and ft.player_id != -1
  and ft.to_franchise_id is not null
  and ft.transaction_type in (
    'rookie_draft_selection',
    'faad',
    'fasa',
    'trade',
    'trade_player',
    'extension',
    'restructure'
  )
  and ft.contract_total is not null

order by validation_check
