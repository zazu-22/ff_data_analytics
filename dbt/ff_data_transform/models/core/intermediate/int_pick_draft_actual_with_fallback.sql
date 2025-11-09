{{ config(materialized="ephemeral", unique_key='pick_id') }}

/*
Draft Picks with Fallback Logic - Ensures complete base pick coverage.

Purpose: Provide base picks with fallback to generated picks for incomplete drafts.

Current State (v2 Phase 3):
- We do NOT have actual draft transaction data (rookie_draft_selection)
- Uses generated base picks from int_pick_base for all rounds
- pick_source = 'GENERATED' for all picks

Future State (when actual draft data available):
- Use actual draft data for complete rounds (12 base picks)
- Fall back to generated picks for incomplete rounds
- pick_source = 'ACTUAL' for draft data, 'GENERATED' for fallback

Grain: One row per base pick (12 picks per round)

Dependencies:
- {{ ref('int_pick_base') }} - Generated base picks (fallback source)
- {{ ref('int_pick_draft_validation') }} - Validation flags (future: determines fallback)

Key Logic:
- v2 Phase 3: All picks from int_pick_base (no actual draft data yet)
- Future: Conditional on validation.has_complete_base_picks
*/
with
    actual_picks as (
        select
            pick_id,
            season,
            round,
            overall_pick,
            slot_number,
            pick_type,
            'ACTUAL' as pick_source,
            draft_transaction_id,
            drafted_player_name as player_drafted,
            drafted_by_franchise_name as drafted_by_franchise
        from {{ ref("int_pick_draft_actual") }}
    ),

    base_picks_generated as (
        -- Generated base picks (12 teams × 5 rounds)
        select
            pick_id,
            season,
            round,
            overall_pick,
            slot_number,
            pick_type,
            'GENERATED' as pick_source,  -- All generated for now
            cast(null as integer) as draft_transaction_id,  -- No draft transactions yet
            cast(null as varchar) as player_drafted,
            cast(null as varchar) as drafted_by_franchise
        from {{ ref("int_pick_base") }}
        where season <= {{ var("latest_completed_draft_season") }}
    ),

    validation as (select * from {{ ref("int_pick_draft_validation") }}),

    actual_with_validation as (
        select ap.*, v.validation_status, v.validation_message, v.has_complete_base_picks
        from actual_picks ap
        left join validation v on ap.season = v.season and ap.round = v.round
    ),

    generated_with_validation as (
        select bp.*, v.validation_status, v.validation_message, v.has_complete_base_picks
        from base_picks_generated bp
        left join validation v on bp.season = v.season and bp.round = v.round
    ),

    generated_fallback as (
        -- Only include generated picks not already covered by actual data
        select g.*
        from generated_with_validation g
        left join actual_picks ap on g.pick_id = ap.pick_id
        where ap.pick_id is null
    )

select *
from actual_with_validation

union all

select *
from generated_fallback

order by season, round, slot_number
