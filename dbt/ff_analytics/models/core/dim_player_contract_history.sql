{{
  config(
    materialized='table',
    indexes=[
      {'columns': ['player_id']},
      {'columns': ['franchise_id']},
      {'columns': ['contract_start_season', 'contract_end_season']},
      {'columns': ['is_current']}
    ]
  )
}}

/*
Player contract history dimension - clean contract state over time.

Grain: One row per player per contract period per franchise
Source: fact_league_transactions (contract-creating events)
Architecture: Type 2 SCD dimension

This dimension derives clean contract state from the transaction event log,
enabling dead cap calculations, roster timeline reconstruction, and salary
cap analysis.

Key Design Decisions:
- Type 2 SCD with effective_date/expiration_date for contract validity
- Contract lifecycle: signed → [extended/restructured] → terminated
- Dead cap calculated using dim_cut_liability_schedule
- Rookie contracts identified and linked to dim_rookie_contract_scale
- Annual amounts calculated for cap roll-ups

Contract Lifecycle Events:
- Created by: rookie_draft_selection, faad, fasa
- Modified by: extension, restructure
- Transferred by: trade (to new franchise, contract continues)
- Terminated by: cut, trade away, expiration

Grain Example Rows:
player_id=12345, franchise_id=F001, contract_period=1 → Rookie contract 2020-2024
player_id=12345, franchise_id=F005, contract_period=2 → Trade-acquired 2024-2025
player_id=12345, franchise_id=F001, contract_period=3 → Re-signed FAAD 2025-2027

Type 2 SCD Fields:
- effective_date: When this contract state became active
- expiration_date: When it ended (9999-12-31 if still active)
- is_current: True if contract is currently active
*/

with contract_events as (
  -- Extract contract-creating and modifying events
  select
    transaction_id,
    transaction_id_unique,
    transaction_type,
    transaction_date,
    season as transaction_season,

    -- Asset identification
    player_id,
    player_name,
    position,

    -- Franchise ownership
    to_franchise_id as franchise_id,
    to_franchise_name as franchise_name,

    -- Contract terms
    contract_total,
    contract_years,
    contract_split_json,
    contract_split_array,

    -- Contract classification
    case
      when transaction_type = 'rookie_draft_selection' then 'rookie'
      when transaction_type = 'faad' then 'faad'
      when transaction_type = 'fasa' then 'fasa'
      when transaction_type in ('trade', 'trade_player') then 'trade_acquired'
      when transaction_type = 'extension' then 'extension'
      when transaction_type = 'restructure' then 'restructure'
      else 'other'
    end as contract_type,

    -- Rookie contract flag
    case
      when transaction_type = 'rookie_draft_selection' then true
      else false
    end as is_rookie_contract,

    -- Special transaction measures
    rfa_matched,
    faad_compensation

  from {{ ref('fact_league_transactions') }}
  where asset_type = 'player'
    and player_id is not null
    and player_id != -1  -- Exclude unmapped players
    and to_franchise_id is not null  -- Must have destination franchise (excludes waiver wire)
    and transaction_type in (
      'rookie_draft_selection',
      'faad',
      'fasa',
      'trade',
      'trade_player',
      'extension',
      'restructure'
    )
    and contract_total is not null  -- Must have contract terms
),

contract_periods as (
  -- Calculate contract validity periods
  select
    ce.*,

    -- Contract period identification
    row_number() over (
      partition by ce.player_id
      order by ce.transaction_date
    ) as contract_period,

    -- Validity dates (Type 2 SCD)
    ce.transaction_date as effective_date,

    -- Expiration date: next contract for this player, or 9999-12-31
    coalesce(
      lead(ce.transaction_date) over (
        partition by ce.player_id
        order by ce.transaction_date
      ) - interval '1 day',
      make_date(9999, 12, 31)
    ) as expiration_date,

    -- Is this the current contract?
    case
      when lead(ce.transaction_date) over (
        partition by ce.player_id
        order by ce.transaction_date
      ) is null then true
      else false
    end as is_current,

    -- Contract timeline
    ce.transaction_season as contract_start_season,
    ce.transaction_season + (ce.contract_years - 1) as contract_end_season,

    -- Calculated measures
    case
      when ce.contract_years > 0
        then round(ce.contract_total::numeric / ce.contract_years::numeric, 2)
      else null
    end as annual_amount

  from contract_events ce
),

with_dead_cap as (
  -- Calculate potential dead cap if cut today
  -- Uses dim_cut_liability_schedule for percentages by contract year
  select
    cp.*,

    -- Dead cap calculation (simplified - assumes even split if no split_array)
    -- In practice, use contract_split_array for accurate year-by-year amounts
    case
      when cp.is_current then (
        -- Sum remaining years' dead cap liability
        select sum(
          (cp.annual_amount * sch.dead_cap_pct)::int
        )
        from {{ ref('dim_cut_liability_schedule') }} sch
        where sch.contract_year <= cp.contract_years
      )
      else 0
    end as dead_cap_if_cut_today

  from contract_periods cp
)

select
  -- Surrogate key
  {{ dbt_utils.generate_surrogate_key([
    'player_id',
    'franchise_id',
    'contract_period'
  ]) }} as contract_history_key,

  -- Natural key
  player_id,
  franchise_id,
  contract_period,

  -- Player attributes (denormalized for convenience)
  player_name,
  position,
  franchise_name,

  -- Contract classification
  contract_type,
  is_rookie_contract,

  -- Contract terms
  contract_total,
  contract_years,
  annual_amount,
  contract_split_json,

  -- Contract timeline
  contract_start_season,
  contract_end_season,
  effective_date,
  expiration_date,
  is_current,

  -- Dead cap measures
  dead_cap_if_cut_today,

  -- Special transaction measures
  rfa_matched,
  faad_compensation,

  -- Audit trail (FK back to transaction event)
  transaction_id,
  transaction_id_unique,

  -- Metadata
  current_timestamp as loaded_at

from with_dead_cap
