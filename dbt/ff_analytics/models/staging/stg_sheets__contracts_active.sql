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

    position,

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
    base.position,
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
  -- Defenses can be in D/ST, BN, or IDP BN positions
  select
    wa.*,
    team.team_abbr as defense_team_abbr,
    case when team.team_abbr is not null then true else false end as is_defense

  from with_alias wa
  left join {{ ref('dim_team') }} team
    on wa.player_name = team.team_name
),

with_player_id as (
  -- Map player name to player_id via dim_player_id_xref
  select
    wd.*,

    -- Join to player crosswalk using canonical name (skip defenses)
    case when wd.is_defense then null else xref.player_id end as player_id,
    xref.mfl_id,
    xref.name as canonical_name

  from with_defense wd
  left join {{ ref('dim_player_id_xref') }} xref
    on (not wd.is_defense)
    and (lower(trim(wd.player_name_canonical)) = lower(trim(xref.name))
         or lower(trim(wd.player_name_canonical)) = lower(trim(xref.merge_name)))
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
    position,

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
