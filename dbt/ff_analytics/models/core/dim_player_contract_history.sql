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

with all_contract_events as (
  -- Extract all contract-related events
  select
    transaction_id,
    transaction_id_unique,
    transaction_type,
    transaction_date,
    season as transaction_season,
    period_type,

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
      when transaction_type in ('faad_ufa_signing', 'faad_rfa_matched') then 'faad'
      when transaction_type in ('fasa_signing', 'offseason_ufa_signing') then 'fasa'
      when transaction_type = 'trade' then 'trade_acquired'
      when transaction_type = 'contract_extension' then 'extension'
      when transaction_type = 'franchise_tag' then 'franchise_tag'
      when transaction_type = 'waiver_claim' then 'waiver_claim'
      else 'other'
    end as contract_type,

    -- Rookie contract flag
    case
      when transaction_type = 'rookie_draft_selection' then true
      else false
    end as is_rookie_contract,

    -- Special transaction measures
    rfa_matched,
    faad_compensation,

    -- Check if there's an extension on the same date for this player
    max(case when transaction_type = 'contract_extension' then transaction_id end) over (
      partition by player_id, transaction_date
    ) as extension_id_on_same_date

  from {{ ref('fact_league_transactions') }}
  where asset_type = 'player'
    and player_id is not null
    and player_id != -1  -- Exclude unmapped players
    and to_franchise_id is not null  -- Must have destination franchise (excludes waiver wire)
    and transaction_type in (
      'rookie_draft_selection',
      'faad_ufa_signing',
      'faad_rfa_matched',
      'fasa_signing',
      'offseason_ufa_signing',
      'trade',
      'contract_extension',
      'franchise_tag',
      'waiver_claim'
    )
    and contract_total is not null  -- Must have contract terms
),

same_date_extensions as (
  -- Combine base contracts with extensions that occur on the same date
  -- The extension adds years to the END of the base contract
  select
    base.transaction_id,
    base.transaction_id_unique,
    base.transaction_type,
    base.transaction_date,
    base.transaction_season,
    coalesce(ext.period_type, base.period_type) as period_type,  -- Use extension's period_type, fall back to base
    base.player_id,
    base.player_name,
    base.position,
    base.franchise_id,
    base.franchise_name,

    -- Extension split_json contains full remaining schedule
    -- Calculate total and years from extension split if available, otherwise use base
    case
      when ext.contract_split_json is not null then
        -- Sum the extension split array to get actual total
        (select sum(unnest) from unnest(cast(json_extract(ext.contract_split_json, '$') as INTEGER[])))
      else base.contract_total
    end as contract_total,
    case
      when ext.contract_split_json is not null then
        -- Count years from extension split array
        len(cast(json_extract(ext.contract_split_json, '$') as INTEGER[]))
      else base.contract_years
    end as contract_years,
    coalesce(ext.contract_split_json, base.contract_split_json) as contract_split_json,
    coalesce(ext.contract_split_array, base.contract_split_array) as contract_split_array,

    base.contract_type,
    base.is_rookie_contract,
    base.rfa_matched,
    base.faad_compensation

  from all_contract_events base
  inner join all_contract_events ext
    on base.player_id = ext.player_id
    and base.transaction_date = ext.transaction_date
    and base.transaction_type != 'contract_extension'
    and ext.transaction_type = 'contract_extension'
),

standalone_contracts as (
  -- Contracts without same-date extensions
  select
    transaction_id,
    transaction_id_unique,
    transaction_type,
    transaction_date,
    transaction_season,
    period_type,
    player_id,
    player_name,
    position,
    franchise_id,
    franchise_name,
    contract_total,
    contract_years,
    contract_split_json,
    contract_split_array,
    contract_type,
    is_rookie_contract,
    rfa_matched,
    faad_compensation

  from all_contract_events
  where extension_id_on_same_date is null
),

contract_creating_events as (
  -- Union of combined same-date extensions and standalone contracts
  select * from same_date_extensions
  union all
  select * from standalone_contracts
),

contract_terminating_events as (
  -- Extract CUT and TRADE-AWAY events that terminate contracts
  select
    transaction_id,
    transaction_id_unique,
    transaction_type,
    transaction_date,
    player_id,
    from_franchise_id as franchise_id
  from {{ ref('fact_league_transactions') }}
  where asset_type = 'player'
    and player_id is not null
    and player_id != -1
    and transaction_type in ('cut', 'trade')  -- Both cut and trade-away terminate contracts
    and from_franchise_id is not null
),

contract_periods as (
  -- Calculate contract validity periods, considering both next contract and CUT events
  select
    ce.*,

    -- Contract period identification
    row_number() over (
      partition by ce.player_id
      order by ce.transaction_date
    ) as contract_period,

    -- Validity dates (Type 2 SCD)
    ce.transaction_date as effective_date,

    -- Find next contract date for this player
    lead(ce.transaction_date) over (
      partition by ce.player_id
      order by ce.transaction_date
    ) as next_contract_date,

    -- Find termination date for this player+franchise (CUT or TRADE-AWAY)
    -- Get the minimum termination date that is >= contract start and on same franchise
    (
      select min(term.transaction_date)
      from contract_terminating_events term
      where term.player_id = ce.player_id
        and term.franchise_id = ce.franchise_id
        and term.transaction_date >= ce.transaction_date
    ) as termination_date,

    -- Contract timeline
    -- Use split array length if available (handles extensions with full remaining schedule)
    -- Otherwise fall back to contract_years
    -- For offseason transactions, contract starts in the NEXT season
    case
      when ce.period_type = 'offseason' then ce.transaction_season + 1
      else ce.transaction_season
    end as contract_start_season,
    (case
      when ce.period_type = 'offseason' then ce.transaction_season + 1
      else ce.transaction_season
    end) + (
      coalesce(
        len(cast(json_extract(ce.contract_split_json, '$') as INTEGER[])),
        ce.contract_years
      ) - 1
    ) as contract_end_season,

    -- Calculated measures (use actual years from split if available)
    case
      when coalesce(
             len(cast(json_extract(ce.contract_split_json, '$') as INTEGER[])),
             ce.contract_years
           ) > 0
        then round(
          ce.contract_total::numeric /
          coalesce(
            len(cast(json_extract(ce.contract_split_json, '$') as INTEGER[])),
            ce.contract_years
          )::numeric,
          2
        )
      else null
    end as annual_amount

  from contract_creating_events ce
),

contract_periods_with_expiry as (
  -- Calculate expiration date and is_current based on terminations and next contracts
  select
    cp.*,

    -- Expiration date: earliest of (termination_date, next_contract_date - 1 day, or 9999-12-31)
    coalesce(
      least(
        cp.termination_date - interval '1 day',
        cp.next_contract_date - interval '1 day'
      ),
      cp.termination_date - interval '1 day',
      cp.next_contract_date - interval '1 day',
      make_date(9999, 12, 31)
    ) as expiration_date,

    -- Is this the current contract?
    -- Current if: no next contract AND no termination, OR termination/next contract is in the future
    case
      when cp.next_contract_date is null and cp.termination_date is null then true
      when cp.termination_date is not null and cp.termination_date <= current_date then false
      when cp.next_contract_date is not null and cp.next_contract_date <= current_date then false
      else true
    end as is_current

  from contract_periods cp
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

  from contract_periods_with_expiry cp
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
