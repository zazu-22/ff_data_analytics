{{ config(materialized="ephemeral") }}

/*
Base draft picks generator - P01 through P12 for all years and rounds.

Purpose: Generate the "natural" 12-team draft structure without compensatory picks.
These are the picks determined by final standings and playoff results.

Grain: One row per base pick (12 picks × 5 rounds × 19 years = 1,140 picks)

Dependencies: None (standalone generator)

Key Logic:
- Years: 2012-2030 (19 years)
- Rounds: 1-5 (standard since 2025, was 4 rounds 2018-2024, was 5 rounds 2012-2017)
- Slots: P01-P12 (12 teams)
- overall_pick: Provisional calculation ignoring comps (will be recalculated in final model)

Note: This model generates ALL possible picks. Historical draft structure variations
(4 vs 5 rounds) are handled in final assembly based on actual usage.
*/
with
    years as (
        -- Generate series of draft years
        select unnest(generate_series(2012, 2030)) as season
    ),

    rounds as (
        -- Generate all 5 rounds
        -- Note: Some years used 4 rounds (2018-2024), but we generate all 5
        -- and filter in downstream models based on actual usage
        select unnest([1, 2, 3, 4, 5]) as round
    ),

    slots as (
        -- Generate 12 pick slots per round (12-team league)
        select unnest(generate_series(1, 12)) as slot_number
    ),

    base_picks as (
        select
            -- Pick ID format: YYYY_R#_P##
            season
            || '_R'
            || round
            || '_P'
            || lpad(slot_number::varchar, 2, '0') as pick_id,

            season,
            round,

            -- Provisional overall pick number (will be recalculated to account for
            -- comps)
            ((round - 1) * 12) + slot_number as overall_pick,

            slot_number,

            'base' as pick_type,
            false as is_compensatory,

            -- Comp pick metadata (NULL for base picks)
            cast(null as varchar) as comp_source_player,
            cast(null as varchar) as comp_awarded_to_franchise,
            cast(null as integer) as comp_faad_transaction_id,
            cast(null as varchar) as comp_round_threshold,
            cast(null as integer) as faad_chronological_seq,

            '' as notes

        from years
        cross join rounds
        cross join slots
    )

select *
from base_picks
