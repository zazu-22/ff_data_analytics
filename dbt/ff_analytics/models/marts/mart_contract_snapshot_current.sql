{{ config(materialized='table') }}

/*
Contract snapshot mart - current contract obligations by year (transaction-derived).

Grain: One row per player per franchise per contract period per obligation year
Source: dim_player_contract_history (expands contract_split_array into year-by-year rows)

This mart expands each player's current contract into individual year rows, showing:
- Annual cap hit for each obligation year
- Remaining contract value from each year forward
- Dead cap liability if cut before that year
- Contract metadata (type, rookie flag, effective dates)

Extension Handling:
The contract_split_array already contains the full remaining schedule per league
accounting conventions. Extensions show the complete remaining schedule in their
split arrays (e.g., 6-6-24 = 2 base years + 1 extension year), so we use them as-is
without additional merge logic.

Use Cases:
- Salary cap planning: What are my obligations for 2025, 2026, etc.?
- Dead cap analysis: What's my liability if I cut Player X before 2026?
- Contract timeline: When does Player Y's contract expire?
- Rookie contract tracking: Which contracts are approaching extension decisions?

Grain Example Rows:
player_id=12345, franchise_id=F001, contract_period=2, obligation_year=2025 → Year 1 of 3-year deal
player_id=12345, franchise_id=F001, contract_period=2, obligation_year=2026 → Year 2 of 3-year deal
player_id=12345, franchise_id=F001, contract_period=2, obligation_year=2027 → Year 3 of 3-year deal
*/

with current_contracts as (
  -- Get only current active contracts that haven't fully expired
  -- Filter: is_current = true AND contract hasn't fully expired yet
  select
    contract_history_key,
    player_id,
    player_name,
    position,
    franchise_id,
    franchise_name,
    contract_period,
    contract_type,
    is_rookie_contract,
    contract_total,
    contract_years,
    annual_amount,
    contract_split_json,
    contract_start_season,
    contract_end_season,
    effective_date,
    expiration_date,
    is_current,
    dead_cap_if_cut_today,
    rfa_matched,
    faad_compensation,
    transaction_id_unique,
    loaded_at
  from {{ ref('dim_player_contract_history') }}
  where is_current = true
    -- Only include contracts with future years (end season >= current year)
    and contract_end_season >= year(current_date)
),

expanded_years as (
  -- Expand contract_split_json into individual year rows
  -- Use DuckDB's list functions to parse JSON array and unnest
  select
    cc.contract_history_key,
    cc.player_id,
    cc.player_name,
    cc.position,
    cc.franchise_id,
    cc.franchise_name,
    cc.contract_period,
    cc.contract_type,
    cc.is_rookie_contract,
    cc.contract_total,
    cc.contract_years,
    cc.annual_amount,
    cc.contract_start_season,
    cc.contract_end_season,
    cc.effective_date,
    cc.expiration_date,
    cc.is_current,
    cc.dead_cap_if_cut_today,
    cc.rfa_matched,
    cc.faad_compensation,
    cc.transaction_id_unique,
    cc.loaded_at,
    cc.contract_split_json,  -- Pass through for later use

    -- Parse JSON array and unnest to create one row per year
    -- contract_split_json format: "[6, 6, 24]" or "[12, 8, 8, 8, 8]"
    -- Cast JSON to INTEGER[] list first, then unnest
    unnest(cast(json_extract(cc.contract_split_json, '$') as INTEGER[])) as annual_cap_hit,

    -- Generate year position (1, 2, 3, ...) for each row
    unnest(generate_series(1, len(cast(json_extract(cc.contract_split_json, '$') as INTEGER[])))) as year_position

  from current_contracts cc
  where cc.contract_split_json is not null
),

with_calculated_fields as (
  -- Add calculated fields: obligation_year, remaining value, dead cap
  select
    ey.*,

    -- Calculate obligation year (contract start + position - 1)
    (ey.contract_start_season + ey.year_position - 1) as obligation_year,

    -- Calculate years remaining from this year forward (including this year)
    (len(cast(json_extract(contract_split_json, '$') as INTEGER[])) - ey.year_position + 1) as years_remaining,

    -- Join to cut liability schedule for dead cap calculation
    sch.dead_cap_pct,
    sch.notes as dead_cap_note

  from expanded_years ey
  left join {{ ref('dim_cut_liability_schedule') }} sch
    on ey.year_position = sch.contract_year
),

with_remaining_value as (
  -- Calculate remaining contract value from each year forward
  select
    cf.*,

    -- Sum of all cap hits from this year forward (including this year)
    sum(cf.annual_cap_hit) over (
      partition by cf.player_id, cf.franchise_id, cf.contract_period
      order by cf.year_position
      rows between current row and unbounded following
    ) as remaining_contract_value,

    -- Dead cap if cut before this year starts
    -- Formula: annual_cap_hit * dead_cap_pct for this year and all future years
    sum(cf.annual_cap_hit * coalesce(cf.dead_cap_pct, 0)) over (
      partition by cf.player_id, cf.franchise_id, cf.contract_period
      order by cf.year_position
      rows between current row and unbounded following
    ) as dead_cap_if_cut_before_year

  from with_calculated_fields cf
)

select
  -- Grain columns (composite natural key)
  player_id,
  franchise_id,
  contract_period,
  obligation_year,

  -- Player attributes (denormalized for convenience)
  player_name,
  position,
  franchise_name,

  -- Contract classification
  contract_type,
  is_rookie_contract,

  -- Year-specific measures
  year_position,                    -- Position within this contract (1, 2, 3, ...)
  annual_cap_hit,                   -- Cap hit for this specific year
  years_remaining,                  -- Years left from this year forward
  remaining_contract_value,         -- Sum of cap hits from this year forward

  -- Dead cap measures
  dead_cap_if_cut_before_year,      -- Liability if cut before this year starts
  dead_cap_pct,                     -- Percentage used in calculation (from schedule)
  dead_cap_note,                    -- Explanation from schedule

  -- Contract timeline
  contract_start_season,
  contract_end_season,
  effective_date,
  expiration_date,
  is_current,

  -- Contract totals (for reference)
  contract_total,
  contract_years,
  annual_amount,                    -- Average annual value (may differ from annual_cap_hit)

  -- Special transaction measures
  rfa_matched,
  faad_compensation,

  -- Audit trail
  contract_history_key,             -- FK to dim_player_contract_history
  transaction_id_unique,            -- FK to fact_league_transactions

  -- Metadata
  loaded_at,
  current_timestamp as snapshot_at

from with_remaining_value
where obligation_year >= year(current_date)  -- Only show current and future years
order by player_name, obligation_year
