{{ config(materialized='table') }}

/*
Stage Commissioner CONTRACTS_ACTIVE sheet with dimension joins and player mapping.

Source: data/raw/commissioner/contracts_active/ (parse_contracts output)
Output grain: one row per player per franchise per obligation year per snapshot date
Joins: dim_franchise (SCD Type 2 temporal), dim_player_id_xref

Key Transformations:
- Map gm (full name) → franchise_id via owner_name matching
- Map player name → player_id via dim_player_id_xref
- Add player_key composite identifier (prevents grain violations from unmapped players)
- Preserve year-by-year obligation structure from source

Purpose:
This staging table serves as the "source of truth" for validating reconstructed
contract obligations derived from dim_player_contract_history. The raw contracts_active
data from the Commissioner sheet shows the current state of all roster obligations,
which we can compare against our computed view from transaction history.
*/

with base as (
  select
    -- Franchise/owner
    gm as gm_full_name,

    -- Player identifiers
    player as player_name,

    -- Normalize player name for matching (strip formatting artifacts)
    -- Use REPLACE instead of nested regexp_replace to avoid dbt execution issues
    replace(
      replace(
        replace(
          replace(player, ' (RS)', ''),  -- Remove "(RS)" suffix
          ' Jr.', ''),  -- Remove " Jr." suffix
        ' Jr', ''),  -- Remove " Jr" suffix
      '.', ''  -- Remove periods from initials (R.J. → RJ)
    ) as player_name_normalized,

    roster_slot,

    -- Contract attributes
    rfa,
    franchise,
    year as obligation_year,
    amount as cap_hit,

    -- Snapshot metadata
    dt as snapshot_date

  from read_parquet(
    '{{ var("external_root", "data/raw") }}/commissioner/contracts_active/dt=*/*.parquet'
  )
),

with_franchise as (
  -- Map GM full name to franchise_id
  -- Extract key identifier from full name for matching (handles "Nick McCreary" → "McCreary")
  select
    -- Explicitly list base columns (avoid * expansion issues)
    base.gm_full_name,
    base.player_name,
    base.player_name_normalized,
    base.roster_slot,
    base.rfa,
    base.franchise,
    base.obligation_year,
    base.cap_hit,
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
    -- Temporal join: contract year should fall within franchise owner tenure
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

with_defense as (
  -- Map defense names to team identifiers
  -- Defenses can be in D/ST, BN, or IDP BN roster slots
  select
    wa.*,
    team.team_abbr as defense_team_abbr,
    case when team.team_abbr is not null then true else false end as is_defense

  from with_alias wa
  left join {{ ref('dim_team') }} team
    on wa.player_name = team.team_name
),

transaction_player_ids as (
  -- Get authoritative player_id from transaction history (position-aware matching already done)
  select distinct
    lower(trim(player_name)) as player_name_lower,
    player_id
  from {{ ref('fact_league_transactions') }}
  where asset_type = 'player'
    and player_id is not null
),

crosswalk_candidates as (
  -- Get all potential matches from crosswalk with position filtering
  select
    wd.player_name_canonical,
    wd.roster_slot,
    xref.player_id,
    xref.mfl_id,
    xref.name,
    xref.position,

    -- Cascading tiebreaker logic
    case
      -- Active player check (exclude retired players)
      when xref.draft_year < extract(year from current_date) - 15 then 0

      -- Position match based on roster slot
      when wd.roster_slot = 'QB' and xref.position = 'QB' then 100
      when wd.roster_slot = 'RB' and xref.position = 'RB' then 100
      when wd.roster_slot = 'WR' and xref.position = 'WR' then 100
      when wd.roster_slot = 'TE' and xref.position = 'TE' then 100
      when wd.roster_slot = 'K' and xref.position = 'K' then 100

      -- FLEX must be RB/WR/TE
      when wd.roster_slot = 'FLEX' and xref.position in ('RB', 'WR', 'TE') then 90

      -- IDP slots must be defensive
      when wd.roster_slot = 'IDP BN' and xref.position in ('DB', 'LB', 'DL', 'DE', 'DT', 'CB', 'S') then 80
      when wd.roster_slot = 'IDP TAXI' and xref.position in ('DB', 'LB', 'DL', 'DE', 'DT', 'CB', 'S') then 80
      when wd.roster_slot = 'DB' and xref.position in ('DB', 'CB', 'S') then 100
      when wd.roster_slot = 'DL' and xref.position in ('DL', 'DE', 'DT') then 100
      when wd.roster_slot = 'LB' and xref.position = 'LB' then 100

      -- BN, TAXI, IR can be any position - prefer offensive
      when wd.roster_slot in ('BN', 'TAXI', 'IR') and xref.position in ('QB', 'RB', 'WR', 'TE', 'K') then 50
      when wd.roster_slot in ('BN', 'TAXI', 'IR') then 25

      else 0
    end as match_score

  from with_defense wd
  left join {{ ref('dim_player_id_xref') }} xref
    on (not wd.is_defense)
    and (lower(trim(wd.player_name_canonical)) = lower(trim(xref.name))
         or lower(trim(wd.player_name_canonical)) = lower(trim(xref.merge_name)))
  where wd.is_defense = false
),

best_crosswalk_match as (
  -- Select best match per player using cascading tiebreakers
  select
    player_name_canonical,
    roster_slot,
    -- Use MAX(player_id) as final tiebreaker (newer/younger/active player)
    max(player_id) as player_id,
    max(mfl_id) as mfl_id,
    max(name) as canonical_name
  from crosswalk_candidates
  where match_score > 0
  group by player_name_canonical, roster_slot
  qualify row_number() over (
    partition by player_name_canonical, roster_slot
    order by max(match_score) desc
  ) = 1
),

with_player_id as (
  -- Combine transaction-based and crosswalk-based player_id resolution
  select
    wd.*,

    -- Cascading player_id resolution:
    -- 1. Transaction history (authoritative, position-aware)
    -- 2. Crosswalk with position filtering
    case
      when wd.is_defense then null
      else coalesce(txn.player_id, xwalk.player_id)
    end as player_id,

    xwalk.mfl_id,
    xwalk.canonical_name

  from with_defense wd
  left join transaction_player_ids txn
    on lower(trim(wd.player_name_canonical)) = txn.player_name_lower
  left join best_crosswalk_match xwalk
    on wd.player_name_canonical = xwalk.player_name_canonical
    and wd.roster_slot = xwalk.roster_slot
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
    -- - Defenses: player_key = 'DEF_' || team_abbr
    -- - Mapped players: player_key = player_id (mfl_id as varchar)
    -- - Unmapped players: player_key = player_name (preserves identity via raw name)
    case
      when is_defense then 'DEF_' || defense_team_abbr
      when coalesce(player_id, -1) != -1
        then cast(player_id as varchar)
      else coalesce(player_name, 'UNKNOWN_PLAYER')
    end as player_key,

    canonical_name,
    player_name,
    roster_slot,

    -- Contract measures
    obligation_year,
    cap_hit,

    -- Contract attributes
    rfa,
    franchise,

    -- Validation flags
    case when is_defense then false  -- Defenses are mapped via team_abbr
         when player_id is null or player_id = -1 then true
         else false
    end as is_unmapped_player,

    case when franchise_id is null
      then true
      else false
    end as is_unmapped_franchise,

    -- Metadata
    snapshot_date,
    extract(year from snapshot_date) as snapshot_year

  from with_player_id
)

select * from final
