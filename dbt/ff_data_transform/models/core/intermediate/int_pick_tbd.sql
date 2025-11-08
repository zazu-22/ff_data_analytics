{{ config(materialized="ephemeral") }}

/*
TBD (To Be Determined) picks extraction from transactions.

Purpose: Extract future-year picks that have been traded before draft order is finalized.
These picks have unknown slot numbers until the regular season ends and standings are set.

Grain: One row per TBD pick referenced in transactions

Dependencies:
- {{ ref('stg_sheets__transactions') }} - Source of pick_id references

Key Logic:
- TBD picks use format: YYYY_R#_TBD (e.g., "2027_R1_TBD")
- These represent picks traded before the owning team's final standings are known
- Slot number and overall pick are placeholders (99) until finalized
- Once finalized, the pick_id changes from TBD to the actual slot (e.g., 2027_R1_P05)

Example Timeline:
- 2025: Team trades "2027 1st round pick" → pick_id: 2027_R1_TBD
- 2026 season ends: Team finishes 5th place
- 2027 rookie draft: pick_id becomes 2027_R1_P05

Note: TBD picks are excluded from overall_pick numbering until finalized.
*/
with
    transaction_picks as (
        -- Get all unique pick_ids referenced in transactions
        select distinct pick_id
        from {{ ref("stg_sheets__transactions") }}
        where asset_type = 'pick' and pick_id like '%_TBD'
    ),

    tbd_parsed as (
        select
            pick_id,

            -- Parse season and round from pick_id format: YYYY_R#_TBD
            cast(regexp_extract(pick_id, '^(\d{4})_R', 1) as integer) as season,
            cast(regexp_extract(pick_id, '_R(\d+)_', 1) as integer) as round,

            -- Placeholder values until pick is finalized
            99 as overall_pick,
            99 as slot_number,

            'tbd' as pick_type,
            false as is_compensatory,

            -- Comp pick metadata (NULL for TBD picks)
            cast(null as varchar) as comp_source_player,
            cast(null as varchar) as comp_awarded_to_franchise,
            cast(null as integer) as comp_faad_transaction_id,
            cast(null as varchar) as comp_round_threshold,
            cast(null as integer) as faad_chronological_seq,

            'TBD - position unknown until standings finalized' as notes

        from transaction_picks
    )

select *
from tbd_parsed
