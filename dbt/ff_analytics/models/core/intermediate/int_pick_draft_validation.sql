{{ config(materialized="table") }}

/*
Draft Pick Validation - Validates completeness of base picks.

Purpose: Ensure each historical round has exactly 12 base picks to prevent
mislabeling of compensatory picks due to missing draft data.

Current State (v2 Phase 3):
- We generate all base picks via int_pick_base (12 teams × 5 rounds × years)
- We do NOT yet have actual draft transaction data (rookie_draft_selection)
- This model validates the generated base picks are complete

Future State (when actual draft data available):
- Will validate actual draft transactions have 12 base picks per round
- Incomplete rounds will trigger fallback to generated picks

Grain: One row per (season, round) combination

Dependencies:
- {{ ref('int_pick_base') }} - Generated base picks

Key Validation:
- Each round must have exactly 12 base picks (12-team league)
- Flags any incomplete or over-complete rounds
*/
with
    base_picks_by_round as (
        select
            season,
            round,
            count(*) as picks_in_round,
            min(slot_number) as first_slot,
            max(slot_number) as last_slot,
            count(*) filter (where slot_number <= 12) as base_picks_count,
            count(*) filter (where slot_number > 12) as comp_picks_count
        from {{ ref("int_pick_base") }}
        where season <= {{ var("latest_completed_draft_season") }}
        group by season, round
    ),

    validation_flags as (
        select
            season,
            round,
            picks_in_round,
            first_slot,
            last_slot,
            base_picks_count,
            comp_picks_count,

            -- Validation: Must have exactly 12 base picks
            base_picks_count = 12 as has_complete_base_picks,

            -- Validation status
            case
                when base_picks_count < 12
                then 'INCOMPLETE_BASE_PICKS'
                when base_picks_count > 12
                then 'TOO_MANY_BASE_PICKS'
                else 'VALID'
            end as validation_status,

            -- Diagnostic message
            case
                when base_picks_count < 12
                then
                    'Missing '
                    || (12 - base_picks_count)::varchar
                    || ' base picks (expected 12, found '
                    || base_picks_count::varchar
                    || ')'
                when base_picks_count > 12
                then
                    'Extra '
                    || (base_picks_count - 12)::varchar
                    || ' picks in base range (expected 12, found '
                    || base_picks_count::varchar
                    || ')'
                else 'Complete: 12 base picks present'
            end as validation_message,

            -- Source of picks (generated vs actual)
            'GENERATED' as pick_source  -- v2: Will be 'ACTUAL' when draft transactions available

        from base_picks_by_round
    )

select
    season,
    round,
    picks_in_round,
    first_slot,
    last_slot,
    base_picks_count,
    comp_picks_count,
    has_complete_base_picks,
    validation_status,
    validation_message,
    pick_source,

    -- Audit metadata
    current_timestamp as validated_at

from validation_flags
order by season, round
