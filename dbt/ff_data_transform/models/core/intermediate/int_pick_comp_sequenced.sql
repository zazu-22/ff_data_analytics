{{ config(materialized="ephemeral", unique_key='pick_id') }}

/*
Compensatory picks with chronological sequencing - Assigns pick numbers (P13+).

Purpose: Convert comp pick registry into dimensional format with proper pick_id numbering.
Comp picks are sequenced chronologically by FAAD transaction order per league rules.

Grain: One row per compensatory pick

Dependencies:
- {{ ref('int_pick_comp_registry') }} - Parsed FAAD comp picks

Key Logic:
- Comp picks come AFTER base picks (P13+) in each round
- Comp pick order determined by FAAD transaction chronological sequence
- First RFA signing that awards a comp → P13 in that round
- Second RFA signing that awards a comp → P14 in that round
- Etc.

Per League Constitution Section XI.N:
"All draft pick compensation picks are awarded immediately after a FAAD contract
is signed and in the order of the FAAD"
*/
with
    comp_registry as (select * from {{ ref("int_pick_comp_registry") }}),

    comp_sequenced as (
        select
            comp_season,
            comp_round,
            comp_faad_transaction_id,
            comp_source_player,
            comp_source_player_id,
            comp_awarded_to_franchise_id,
            comp_round_threshold,
            contract_apy,
            is_aav_round_valid,
            aav_validation_message,
            faad_award_sequence,

            -- Chronological sequence within each round (by persisted FAAD sequence)
            -- v2: Changed from ORDER BY comp_faad_transaction_id to use
            -- faad_award_sequence
            -- This ensures sequence is immutable even if transaction_ids are manually
            -- corrected
            row_number() over (
                partition by comp_season, comp_round order by faad_award_sequence
            ) as faad_chronological_seq,

            -- Slot number = 12 (base picks) + chronological sequence
            12 + row_number() over (partition by comp_season, comp_round order by faad_award_sequence) as slot_number

        from comp_registry
    ),

    comp_picks as (
        select
            -- Pick ID format: YYYY_R#_P##
            comp_season || '_R' || comp_round || '_P' || lpad(slot_number::varchar, 2, '0') as pick_id,

            comp_season as season,
            comp_round as round,

            -- Placeholder overall_pick (will be recalculated in final model to account
            -- for comps in prior rounds)
            999 as overall_pick,

            slot_number,

            'compensatory' as pick_type,
            true as is_compensatory,

            -- Comp pick metadata
            comp_source_player,
            comp_awarded_to_franchise_id as comp_awarded_to_franchise,
            comp_faad_transaction_id,
            comp_round_threshold,
            faad_chronological_seq,
            contract_apy,

            -- Notes with player context and validation
            case
                when not is_aav_round_valid
                then 'Comp for ' || comp_source_player || ' | ' || aav_validation_message
                else 'Comp for ' || comp_source_player
            end as notes

        from comp_sequenced
    )

select *
from comp_picks
