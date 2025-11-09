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
    actual_picks_by_round as (
        select
            season,
            round,
            count(*) as picks_in_round,
            min(slot_number) as first_slot,
            max(slot_number) as last_slot,
            count(*) filter (where slot_number <= 12) as base_picks_count,
            count(*) filter (where slot_number > 12) as comp_picks_count,
            'ACTUAL' as pick_source
        from {{ ref("int_pick_draft_actual") }}
        group by season, round
    ),

    generated_picks_by_round as (
        select
            season,
            round,
            count(*) as picks_in_round,
            min(slot_number) as first_slot,
            max(slot_number) as last_slot,
            count(*) filter (where slot_number <= 12) as base_picks_count,
            count(*) filter (where slot_number > 12) as comp_picks_count,
            'GENERATED' as pick_source
        from {{ ref("int_pick_base") }}
        where season <= {{ var("latest_completed_draft_season") }}
        group by season, round
    ),

    combined as (
        select
            coalesce(a.season, g.season) as season,
            coalesce(a.round, g.round) as round,
            coalesce(a.picks_in_round, g.picks_in_round) as picks_in_round,
            coalesce(a.first_slot, g.first_slot) as first_slot,
            coalesce(a.last_slot, g.last_slot) as last_slot,
            coalesce(a.base_picks_count, g.base_picks_count) as base_picks_count,
            coalesce(a.comp_picks_count, g.comp_picks_count) as comp_picks_count,
            coalesce(a.pick_source, g.pick_source) as pick_source
        from actual_picks_by_round a
        full outer join generated_picks_by_round g on a.season = g.season and a.round = g.round
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
            pick_source,

            base_picks_count = 12 as has_complete_base_picks,

            case
                when base_picks_count < 12
                then 'INCOMPLETE_BASE_PICKS'
                when base_picks_count > 12
                then 'TOO_MANY_BASE_PICKS'
                else 'VALID'
            end as validation_status,

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
            end as validation_message

        from combined
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
