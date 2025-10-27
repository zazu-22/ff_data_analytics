{{ config(materialized='table') }}

/*
Stage Commissioner CONTRACTS_CUT sheet - dead cap obligations from past cuts.

Source: data/raw/commissioner/contracts_cut/ (parse_contracts output)
Output grain: one row per franchise per player per obligation year per snapshot date
Joins: dim_franchise (SCD Type 2 temporal), dim_player_id_xref

Key Transformations:
- Map gm (full name) → franchise_id via owner_name matching
- Map player name → player_id via dim_player_id_xref + dim_name_alias
- Add player_key composite identifier (prevents grain violations from unmapped players)
- Preserve year-by-year dead cap structure from source

Purpose:
This staging table represents the **source of truth** for dead cap obligations per
league rules. The Commissioner manually calculates dead cap using the league formula
(50% years 1-2, 25% years 3-5). This data serves as the validation baseline for
comparing against transaction-derived dead cap calculations in fact_contract_cuts.

Dead cap obligations persist across multiple years after a player is cut, so this
table will show players who may no longer be on any roster but still carry cap hits.

Relationship to Active Contracts:
- stg_sheets__contracts_active: Players currently on rosters
- stg_sheets__contracts_cut: Dead cap from players previously cut
- Combined = Total cap obligations per franchise
*/

with base as (
  select
    -- Franchise/owner
    gm as gm_full_name,

    -- Player identifiers
    player as player_name,

    -- Normalize player name for matching (strip formatting artifacts)
    replace(
      replace(
        replace(
          replace(player, ' (RS)', ''),  -- Remove "(RS)" suffix
          ' Jr.', ''
        ),  -- Remove " Jr." suffix
        ' Jr', ''
      ),  -- Remove " Jr" suffix
      '.', ''  -- Remove periods from initials (R.J. → RJ)
    ) as player_name_normalized,

    position,

    -- Dead cap measure
    year as obligation_year,
    dead_cap_amount,

    -- Snapshot metadata
    dt as snapshot_date

  from
    read_parquet(
      '{{ var("external_root", "data/raw") }}/commissioner/contracts_cut/dt=*/contracts_cut.parquet'
    )
  where     {{ latest_snapshot_only(var("external_root", "data/raw") ~ '/commissioner/contracts_cut/dt=*/contracts_cut.parquet') }}
),

with_franchise as (
  -- Map GM full name to franchise_id
  -- Extract key identifier from full name for matching (handles "Nick McCreary" → "McCreary")
  select
    -- Explicitly list base columns
    base.gm_full_name,
    base.player_name,
    base.player_name_normalized,
    base.position,
    base.obligation_year,
    base.dead_cap_amount,
    base.snapshot_date,

    -- Extract last name or key identifier for franchise matching
    case
      when base.gm_full_name like 'Nick McCreary' then 'McCreary'
      when base.gm_full_name like 'Nick Piper' then 'Piper'
      else split_part(base.gm_full_name, ' ', 1)  -- First name for others
    end as owner_key,

    fran.franchise_id,
    fran.franchise_name,
    fran.owner_name

  from base
  left join {{ ref('dim_franchise') }} fran
    on case
      when base.gm_full_name like 'Nick McCreary' then 'McCreary'
      when base.gm_full_name like 'Nick Piper' then 'Piper'
      else split_part(base.gm_full_name, ' ', 1)
    end = fran.owner_name
    -- Temporal join: obligation year should fall within franchise owner tenure
    and base.obligation_year between fran.season_start and fran.season_end
),

with_alias as (
  -- Apply name alias corrections (typos → canonical names)
  select
    wf.*,
    coalesce(alias.canonical_name, wf.player_name_normalized) as player_name_canonical

  from with_franchise wf
  left join {{ ref('dim_name_alias') }} alias
    on wf.player_name_normalized = alias.alias_name
),

transaction_player_ids as (
  -- Get authoritative player_id from transaction history with position info
  -- Need position to disambiguate players with same name (e.g., Josh Allen QB vs DB)
  -- DISTINCT ON player_name, player_id to handle position variations (e.g., Zaven Collins: LB/DL)
  select distinct
    lower(trim(player_name)) as player_name_lower,
    player_id
  from {{ ref('fact_league_transactions') }}
  where
    asset_type = 'player'
    and player_id is not null
),

crosswalk_candidates as (
  -- Get all potential matches from crosswalk with position filtering
  select
    wa.player_name_canonical,
    wa.position as source_position,
    xref.player_id,
    xref.mfl_id,
    xref.name,
    xref.position,

    -- Position match scoring
    case
      -- Exact position match
      when wa.position = xref.position then 100

      -- Generic defensive positions map to specific ones
      when
        wa.position in ('DB', 'DL', 'LB')
        and xref.position in ('DB', 'LB', 'DL', 'DE', 'DT', 'CB', 'S') then 80

      -- Active player check (exclude retired players)
      when xref.draft_year < extract(year from current_date) - 15 then 0

      else 0
    end as match_score

  from with_alias wa
  left join {{ ref('dim_player_id_xref') }} xref
    on (
      lower(trim(wa.player_name_canonical)) = lower(trim(xref.name))
      or lower(trim(wa.player_name_canonical)) = lower(trim(xref.merge_name))
    )
),

best_crosswalk_match as (
  -- Select best match per player using position-aware tiebreakers
  select
    player_name_canonical,
    source_position,
    -- Use MAX(player_id) as final tiebreaker (newer/younger/active player)
    max(player_id) as player_id,
    max(mfl_id) as mfl_id,
    max(name) as canonical_name
  from crosswalk_candidates
  where match_score > 0
  group by player_name_canonical, source_position
  qualify row_number() over (
    partition by player_name_canonical, source_position
    order by max(match_score) desc
  ) = 1
),

with_player_id as (
  -- Combine transaction-based and crosswalk-based player_id resolution
  select
    wa.*,

    -- Cascading player_id resolution:
    -- 1. Transaction history (authoritative, position-aware)
    -- 2. Crosswalk with position filtering
    coalesce(txn.player_id, xwalk.player_id) as player_id,

    xwalk.mfl_id,
    xwalk.canonical_name

  from with_alias wa
  left join transaction_player_ids txn
    on lower(trim(wa.player_name_canonical)) = txn.player_name_lower
  left join best_crosswalk_match xwalk
    on
      wa.player_name_canonical = xwalk.player_name_canonical
      and wa.position = xwalk.source_position
),

final as (
  -- Add player_key composite identifier and finalize
  select
    -- Franchise dimension
    franchise_id,
    franchise_name,
    owner_name,
    gm_full_name,

    -- Player dimension
    player_id,  -- mfl_id from crosswalk (-1 if unmapped)

    -- Player key logic (same pattern as stg_sheets__transactions):
    -- - Mapped players: player_key = player_id (mfl_id as varchar)
    -- - Unmapped players: player_key = player_name (preserves identity via raw name)
    case
      when coalesce(player_id, -1) != -1
        then cast(player_id as varchar)
      else coalesce(player_name, 'UNKNOWN_PLAYER')
    end as player_key,

    canonical_name,
    player_name,
    position,

    -- Dead cap measure
    obligation_year,
    dead_cap_amount,

    -- Validation flags
    coalesce(player_id is null or player_id = -1, false) as is_unmapped_player,

    coalesce(franchise_id is null, false) as is_unmapped_franchise,

    -- Metadata
    snapshot_date,
    extract(year from snapshot_date) as snapshot_year

  from with_player_id
)

select * from final
