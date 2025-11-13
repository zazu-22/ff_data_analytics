{{
    config(
        materialized="table",
        unique_key=['franchise_id', 'player_key', 'obligation_year', 'snapshot_date']
    )
}}

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
with
    base as (
        select
            -- Franchise/owner
            gm as gm_full_name,
            gm_tab,

            -- Player identifiers
            player as player_name,

            -- Normalize player name for matching (strip formatting artifacts)
            -- Use REPLACE instead of nested regexp_replace to avoid dbt execution
            -- issues
            replace(
                replace(
                    replace(
                        replace(player, ' (RS)', ''),  -- Remove "(RS)" suffix
                        ' Jr.',
                        ''
                    ),  -- Remove " Jr." suffix
                    ' Jr',
                    ''
                ),  -- Remove " Jr" suffix
                '.',
                ''  -- Remove periods from initials (R.J. → RJ)
            ) as player_name_normalized,

            roster_slot,

            -- Contract attributes
            rfa,
            franchise,
            year as obligation_year,
            amount as cap_hit,

            -- Snapshot metadata
            dt as snapshot_date

        from read_parquet('{{ var("external_root", "data/raw") }}/commissioner/contracts_active/dt=*/*.parquet')
        where
            {{
                snapshot_selection_strategy(
                    var("external_root", "data/raw")
                    ~ "/commissioner/contracts_active/dt=*/*.parquet",
                    strategy='latest_only'
                )
            }}
    ),

    with_franchise as (
        -- Map GM full name to franchise_id
        -- Extract key identifier from full name for matching (handles "Nick McCreary"
        -- → "McCreary")
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

            fran.franchise_id,
            fran.franchise_name,
            fran.owner_name

        from base
        left join
            {{ ref("dim_franchise") }} fran
            on base.gm_tab = fran.gm_tab  -- Clean join on tab name
            -- Temporal join: contract year should fall within franchise owner tenure
            and base.obligation_year between fran.season_start and fran.season_end
    ),

    with_alias as (
        -- Apply name alias corrections (typos → canonical names)
        -- DISTINCT to handle duplicate entries in dim_name_alias seed
        select distinct wf.*, coalesce(alias.canonical_name, wf.player_name_normalized) as player_name_canonical

        from with_franchise wf
        left join {{ ref("dim_name_alias") }} alias on wf.player_name_normalized = alias.alias_name
    ),

    with_defense as (
        -- Map defense names to team identifiers
        -- Defenses can be in D/ST, BN, or IDP BN roster slots
        select wa.*, team.team_abbr as defense_team_abbr, coalesce(team.team_abbr is not null, false) as is_defense

        from with_alias wa
        left join {{ ref("dim_team") }} team on wa.player_name = team.team_name
    ),

    -- Resolve player_id using centralized macro with roster_slot context
    {{ resolve_player_id_from_name(
        source_cte='with_defense',
        player_name_col='player_name_canonical',
        position_context_col='roster_slot',
        context_type='roster_slot'
    ) }},

    with_player_id as (
        -- Join defense data with player_id lookup from macro
        select
            wd.*,
            -- Defense handling: NULL player_id for defense teams
            case when wd.is_defense then null else pid.player_id end as player_id,
            pid.mfl_id,
            pid.canonical_name

        from with_defense wd
        left join
            with_player_id_lookup pid
            on wd.player_name_canonical = pid.player_name_canonical
            and wd.roster_slot = pid.roster_slot
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
            player_id,  -- canonical player_id from crosswalk/transactions (-1 if unmapped)

            -- Player key logic (same pattern as stg_sheets__transactions):
            -- - Defenses: player_key = 'DEF_' || team_abbr
            -- - Mapped players: player_key = cast(player_id as varchar)
            -- - Empty players: player_key = 'EMPTY_' || roster_slot || '_' ||
            -- row_number (for weekly pickup placeholders)
            -- - Unmapped players: player_key = player_name (preserves identity via
            -- raw name)
            case
                when is_defense
                then 'DEF_' || defense_team_abbr
                when coalesce(player_id, -1) != -1
                then cast(player_id as varchar)
                when player_name = ''
                then
                    'EMPTY_'
                    || roster_slot
                    || '_'
                    || cast(
                        row_number() over (
                            partition by franchise_id, roster_slot, obligation_year, snapshot_date order by cap_hit desc
                        ) as varchar
                    )
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
            case
                when is_defense
                then false  -- Defenses are mapped via team_abbr
                when player_id is null or player_id = -1
                then true
                else false
            end as is_unmapped_player,

            coalesce(franchise_id is null, false) as is_unmapped_franchise,

            -- Metadata
            snapshot_date,
            extract(year from snapshot_date) as snapshot_year

        from with_player_id
    )

select
    -- Franchise dimension
    franchise_id,
    franchise_name,
    owner_name,
    gm_full_name,

    -- Player dimension
    player_id,
    player_key,
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
    is_unmapped_player,
    is_unmapped_franchise,

    -- Metadata
    snapshot_date,
    snapshot_year

from final
