{{
    config(
        materialized="table",
        unique_key=['franchise_id', 'player_key', 'obligation_year', 'snapshot_date']
    )
}}

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
with
    base as (
        select
            -- Franchise/owner
            gm as gm_full_name,
            gm_tab,

            -- Player identifiers
            player as player_name,

            -- Normalize player name for matching (strip formatting artifacts)
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

            position,

            -- Dead cap measure
            year as obligation_year,
            dead_cap_amount,

            -- Snapshot metadata
            dt as snapshot_date

        from
            read_parquet('{{ var("external_root", "data/raw") }}/commissioner/contracts_cut/dt=*/contracts_cut.parquet')
        where
            {{
                snapshot_selection_strategy(
                    var("external_root", "data/raw")
                    ~ "/commissioner/contracts_cut/dt=*/contracts_cut.parquet",
                    strategy='latest_only'
                )
            }}
    ),

    with_franchise as (
        -- Map GM full name to franchise_id
        -- Extract key identifier from full name for matching (handles "Nick McCreary"
        -- → "McCreary")
        select
            -- Explicitly list base columns
            base.gm_full_name,
            base.player_name,
            base.player_name_normalized,
            base.position,
            base.obligation_year,
            base.dead_cap_amount,
            base.snapshot_date,

            fran.franchise_id,
            fran.franchise_name,
            fran.owner_name

        from base
        left join
            {{ ref("dim_franchise") }} fran
            on base.gm_tab = fran.gm_tab  -- Clean join on tab name
            -- Temporal join: obligation year should fall within franchise owner tenure
            and base.obligation_year between fran.season_start and fran.season_end
    ),

    with_alias as (
        -- Apply name alias corrections (typos → canonical names)
        -- DISTINCT to handle duplicate entries in dim_name_alias seed
        select distinct wf.*, coalesce(alias.canonical_name, wf.player_name_normalized) as player_name_canonical

        from with_franchise wf
        left join {{ ref("dim_name_alias") }} alias on wf.player_name_normalized = alias.alias_name
    ),

    -- Resolve player_id using centralized macro with position context
    {{ resolve_player_id_from_name(
        source_cte='with_alias',
        player_name_col='player_name_canonical',
        position_context_col='position',
        context_type='position'
    ) }},

    with_player_id as (
        -- Join player data with player_id lookup from macro
        select wa.*, pid.player_id, pid.mfl_id, pid.canonical_name

        from with_alias wa
        left join
            with_player_id_lookup pid
            on wa.player_name_canonical = pid.player_name_canonical
            and wa.position = pid.position
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
            -- - Mapped players: player_key = cast(player_id as varchar)
            -- - Unmapped players: player_key = player_name (preserves identity via
            -- raw name)
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
    position,

    -- Dead cap measure
    obligation_year,
    dead_cap_amount,

    -- Validation flags
    is_unmapped_player,
    is_unmapped_franchise,

    -- Metadata
    snapshot_date,
    snapshot_year

from final
