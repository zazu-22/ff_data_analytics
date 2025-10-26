{{
  config(
    materialized='table',
    indexes=[
      {'columns': ['player_id']},
      {'columns': ['pick_id']},
      {'columns': ['transaction_date']},
      {'columns': ['from_franchise_id']},
      {'columns': ['to_franchise_id']},
      {'columns': ['transaction_type', 'asset_type']},
      {'columns': ['season', 'period_type']}
    ]
  )
}}

/*
League transaction history fact table - raw event log.

Grain: One row per transaction event per asset
Sources: stg_sheets__transactions
Architecture: Transaction fact table (Kimball) - immutable event log

This table preserves source data fidelity with validation flags.
Contract Extensions intentionally have length mismatches (see validation_notes).

Deferred to Phase 3:
- dim_player_contract_history: Clean contract state derived from this event log

Key Design Decisions:
- Degenerate dimensions: transaction_type, asset_type (no separate dimension tables)
- Role-playing dimensions: from_franchise_id, to_franchise_id (both FK to dim_franchise)
- Complex measures: contract_split_json (variable-length arrays as JSON)
- Data quality: Validation flags preserve source issues for analysis

Grain Example Rows:
transaction_id=3910, player_key=12345, asset_type=player → Cut of one player
transaction_id=2145, player_key=67890, asset_type=player → Trade with 3 players
transaction_id=2145, player_key=2025_R1_P04, asset_type=pick → Same trade, pick involved

Composite Key: transaction_id_unique (PK)
*/

with rookie_draft_calendar_years as (
  -- Identify draft calendar year for each player to enable chronological safeguards
  -- Prevents impossible transaction sequences (e.g., traded before being drafted)
  select
    player_id,
    min(transaction_date) as draft_date,
    year(min(transaction_date)) as draft_calendar_year
  from {{ ref('stg_sheets__transactions') }}
  where
    transaction_type = 'rookie_draft_selection'
    and asset_type = 'player'
    and player_id is not null
  group by player_id
),

base_transactions as (
  select
    t.*,
    rd.draft_date,
    rd.draft_calendar_year
  from {{ ref('stg_sheets__transactions') }} as t
  left join rookie_draft_calendar_years as rd on t.player_id = rd.player_id
)

select
  -- Degenerate dimensions (stored in fact, no separate dim table)
  transaction_id_unique,  -- Primary key
  transaction_id,         -- Groups multi-asset trades
  player_key,             -- Composite identifier (prevents grain violations)
  transaction_type,       -- Refined type (rookie_draft_selection, cut, trade, etc.)
  asset_type,             -- player, pick, defense, cap_space, unknown

  -- Time dimension
  transaction_date,

  -- CHRONOLOGICAL SAFEGUARD: Corrected date for proper sequencing
  -- Rule: Offseason transactions in rookie draft calendar year must occur AFTER draft
  -- This prevents impossible sequences like "traded before being drafted"
  case
    when
      draft_calendar_year is not null
      and year(transaction_date) = draft_calendar_year
      and period_type = 'offseason'
      and transaction_date < draft_date
      and transaction_type != 'rookie_draft_selection'
      then draft_date + interval '1 hour'  -- Force to sequence after draft
    else transaction_date
  end as transaction_date_corrected,

  -- Flag indicating chronological correction was applied
  coalesce(
    draft_calendar_year is not null
    and year(transaction_date) = draft_calendar_year
    and period_type = 'offseason'
    and transaction_date < draft_date
    and transaction_type != 'rookie_draft_selection', false
  ) as was_sequence_corrected,

  transaction_year,       -- Partition key for large-scale queries
  season,
  period_type,
  week,
  sort_sequence,
  timeframe_string,       -- Original timeframe from sheet (degenerate)

  -- Role-playing franchise dimensions
  from_franchise_id,      -- FK to dim_franchise (null for waiver wire source)
  from_franchise_name,    -- Denormalized for convenience
  to_franchise_id,        -- FK to dim_franchise (null for waiver wire destination)
  to_franchise_name,      -- Denormalized for convenience

  -- Asset dimensions (nullable by asset_type)
  player_id,              -- FK to dim_player_id_xref (when asset_type='player')
  player_name,            -- Denormalized player name
  position,               -- Player position
  pick_id,                -- FK to dim_pick (when asset_type='pick')
  pick_original_owner,    -- Original franchise that owned the pick
  round,                  -- Draft round (e.g., "R1", "R2")
  pick_number,            -- Pick number (e.g., "P04", "P12")

  -- Contract measures (semi-additive)
  contract_total,         -- Total contract value (whole dollars)
  contract_years,         -- Contract length (1-5 years)
  contract_split_json,    -- Year-by-year cap hits as JSON array
  contract_split_array,   -- Keep array for validation in fact table

  -- Data quality flags
  has_contract_length_mismatch,   -- True for Extensions (expected)
  has_contract_sum_mismatch,      -- True for rounding variance or errors
  validation_notes,               -- Explanation of validation issues

  -- Special transaction measures
  rfa_matched,                -- RFA match indicator (boolean)
  faad_compensation,          -- FAAD RFA compensation amount (integer, null if text)
  faad_compensation_text,     -- FAAD compensation text (e.g., "2nd to Piper" for pick)

  -- Raw fields for audit trail
  contract_raw,           -- Original Contract field (e.g., "49/3")
  split_raw,              -- Original Split field (e.g., "6-6-10-13-13")
  transaction_type_raw,   -- Original Type field from sheet
  from_owner_name,        -- Original owner name from sheet
  to_owner_name           -- Original owner name from sheet

from base_transactions
