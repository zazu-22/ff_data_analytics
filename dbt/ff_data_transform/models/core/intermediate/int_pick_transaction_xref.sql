{{ config(materialized="table") }}

/*
Pick transaction crosswalk - Matches transaction pick references to canonical dim_pick pick_ids.

Purpose: Resolve pick_id references in transactions by matching on (season, round, overall_pick).
The Commissioner sheet contains overall pick numbers (1-60+), but pick_ids in transactions use
those numbers incorrectly combined with round numbers. This model creates the correct mapping.

Grain: One row per pick transaction reference

Dependencies:
- {{ ref('stg_sheets__transactions') }} - Transaction pick references with overall_pick numbers
- {{ ref('dim_pick') }} - Canonical pick dimension with correctly calculated overall_pick

Key Logic:
- Match on (season, round, overall_pick) to find canonical pick
- Handle both finalized picks (with numbers) and TBD picks (no numbers)
- Validate matches and flag mismatches for data quality review

Example Matching:
Transaction references pick_id_raw="2020_R2_P23" (Round 2, overall pick 23)
  → Match to dim_pick where season=2020, round=2, overall_pick=23
  → Find canonical pick_id="2020_R2_P11" (Round 2, Slot 11)
  → Why different? Because R1 had 5 comp picks, making 17 total R1 picks
  → So overall pick 23 = 23 - 17 = 6th pick in R2... wait, that's not right either
  → Actually: overall pick 23 means the 23rd pick in the draft sequence
  → With our dim_pick properly sequenced by ROW_NUMBER, pick 23 gets matched

Validation:
- is_overall_match: TRUE if overall pick numbers align
- is_raw_id_match: TRUE if raw pick_id equals canonical (unlikely for comp picks)
- has_canonical_match: TRUE if we found a match in dim_pick
*/
with
    transaction_picks as (
        select
            transaction_id_unique,
            transaction_id,
            asset_type,
            pick_season,
            pick_round,
            pick_overall_number,
            pick_id_raw,
            pick_id as pick_id_original  -- For backward compat tracking

        from {{ ref("stg_sheets__transactions") }}
        where asset_type = 'pick'
    ),

    canonical_picks as (
        select pick_id, season, round, overall_pick, slot_number, pick_type, is_compensatory

        from {{ ref("dim_pick") }}
        where pick_type != 'tbd'  -- Match on finalized picks only
    ),

    -- Match finalized picks by (season, round, overall_pick)
    matched_by_overall as (
        select
            tp.transaction_id_unique,
            tp.transaction_id,
            tp.pick_season,
            tp.pick_round,
            tp.pick_overall_number,
            tp.pick_id_raw,
            tp.pick_id_original,

            -- Canonical pick from dim_pick
            cp.pick_id as pick_id_canonical,
            cp.overall_pick as overall_pick_canonical,
            cp.slot_number as slot_number_canonical,
            cp.pick_type,
            cp.is_compensatory,

            -- Validation flags
            tp.pick_overall_number = cp.overall_pick as is_overall_match,
            tp.pick_id_raw = cp.pick_id as is_raw_id_match,
            cp.pick_id is not null as has_canonical_match,

            -- Match quality note
            case
                when cp.pick_id is null
                then 'NO MATCH FOUND'
                when tp.pick_id_raw = cp.pick_id
                then 'EXACT MATCH'
                when tp.pick_overall_number = cp.overall_pick
                then 'OVERALL MATCH (ID CORRECTED)'
                else 'MISMATCH'
            end as match_status,

            'overall' as match_method

        from transaction_picks tp
        left join
            canonical_picks cp
            on tp.pick_season = cp.season
            and tp.pick_round = cp.round
            and tp.pick_overall_number = cp.overall_pick
        where tp.pick_overall_number is not null  -- Only finalized picks
    ),

    -- Fallback: Try matching by slot number for unmatched picks
    -- Some sheet entries incorrectly use slot numbers instead of overall pick numbers
    matched_by_slot as (
        select
            tp.transaction_id_unique,
            tp.transaction_id,
            tp.pick_season,
            tp.pick_round,
            tp.pick_overall_number,
            tp.pick_id_raw,
            tp.pick_id_original,

            -- Match by treating overall_number as slot_number
            cp.pick_id as pick_id_canonical,
            cp.overall_pick as overall_pick_canonical,
            cp.slot_number as slot_number_canonical,
            cp.pick_type,
            cp.is_compensatory,

            -- Validation flags (overall won't match since we matched on slot)
            false as is_overall_match,
            tp.pick_id_raw = cp.pick_id as is_raw_id_match,
            cp.pick_id is not null as has_canonical_match,

            'SLOT MATCH (OVERALL NUMBER WAS ACTUALLY SLOT)' as match_status,
            'slot_fallback' as match_method

        from transaction_picks tp
        inner join
            canonical_picks cp
            on tp.pick_season = cp.season
            and tp.pick_round = cp.round
            and tp.pick_overall_number = cp.slot_number  -- KEY: Match overall_number to slot_number
        where
            tp.pick_overall_number is not null
            -- Only for picks that didn't match by overall
            and tp.transaction_id_unique
            not in (select transaction_id_unique from matched_by_overall where has_canonical_match)
    ),

    -- Combine primary and fallback matches, prioritizing overall matches
    matched_finalized as (
        select
            transaction_id_unique,
            transaction_id,
            pick_season,
            pick_round,
            pick_overall_number,
            pick_id_raw,
            pick_id_original,
            pick_id_canonical,
            overall_pick_canonical,
            slot_number_canonical,
            pick_type,
            is_compensatory,
            is_overall_match,
            is_raw_id_match,
            has_canonical_match,
            match_status
        from matched_by_overall
        where has_canonical_match  -- Successfully matched by overall

        union all

        select
            transaction_id_unique,
            transaction_id,
            pick_season,
            pick_round,
            pick_overall_number,
            pick_id_raw,
            pick_id_original,
            pick_id_canonical,
            overall_pick_canonical,
            slot_number_canonical,
            pick_type,
            is_compensatory,
            is_overall_match,
            is_raw_id_match,
            has_canonical_match,
            match_status
        from matched_by_slot  -- Fallback matches

        union all

        select
            transaction_id_unique,
            transaction_id,
            pick_season,
            pick_round,
            pick_overall_number,
            pick_id_raw,
            pick_id_original,
            pick_id_canonical,
            overall_pick_canonical,
            slot_number_canonical,
            pick_type,
            is_compensatory,
            is_overall_match,
            is_raw_id_match,
            has_canonical_match,
            match_status
        from matched_by_overall
        where not has_canonical_match  -- Still unmatched
    ),

    -- Handle TBD picks separately (match on season/round only, no overall pick yet)
    tbd_picks_dim as (select pick_id, season, round, pick_type from {{ ref("dim_pick") }} where pick_type = 'tbd'),

    matched_tbd as (
        select
            tp.transaction_id_unique,
            tp.transaction_id,
            tp.pick_season,
            tp.pick_round,
            tp.pick_overall_number,
            tp.pick_id_raw,
            tp.pick_id_original,

            -- TBD picks match on season/round only
            tbd.pick_id as pick_id_canonical,
            cast(null as integer) as overall_pick_canonical,
            cast(null as integer) as slot_number_canonical,
            tbd.pick_type,
            false as is_compensatory,

            -- TBD picks have no overall match to validate
            cast(null as boolean) as is_overall_match,
            tp.pick_id_raw = tbd.pick_id as is_raw_id_match,
            tbd.pick_id is not null as has_canonical_match,

            'TBD PICK' as match_status

        from transaction_picks tp
        inner join tbd_picks_dim tbd on tp.pick_season = tbd.season and tp.pick_round = tbd.round
        where tp.pick_overall_number is null  -- Only TBD transactions
    ),

    -- Combine finalized and TBD picks
    all_matched as (
        select *
        from matched_finalized

        union all

        select *
        from matched_tbd
    ),

    -- v2: Add lifecycle mapping to migrate TBD references to actual picks
    lifecycle_control as (
        select pick_id, lifecycle_state, superseded_by_pick_id from {{ ref("dim_pick_lifecycle_control") }}
    ),

    picks_with_lifecycle as (
        select
            m.*,
            lc.lifecycle_state,
            lc.superseded_by_pick_id,

            -- v2: Canonical pick after lifecycle migration
            -- If TBD pick is superseded, use the actual pick; otherwise use original
            -- canonical
            coalesce(lc.superseded_by_pick_id, m.pick_id_canonical) as pick_id_final,

            -- Migration note for audit
            case
                when lc.lifecycle_state = 'SUPERSEDED'
                then 'TBD pick migrated to actual pick: ' || lc.superseded_by_pick_id
                else null
            end as lifecycle_migration_note

        from all_matched m
        left join lifecycle_control lc on m.pick_id_canonical = lc.pick_id
    )

select
    transaction_id_unique,
    transaction_id,
    pick_season,
    pick_round,
    pick_overall_number,
    pick_id_raw,
    pick_id_original,
    pick_id_canonical,
    pick_id_final,  -- v2: Use this for FK relationships
    overall_pick_canonical,
    slot_number_canonical,
    pick_type,
    is_compensatory,
    is_overall_match,
    is_raw_id_match,
    has_canonical_match,
    match_status,
    lifecycle_state,  -- v2: Lifecycle tracking
    lifecycle_migration_note  -- v2: Migration audit
from picks_with_lifecycle
