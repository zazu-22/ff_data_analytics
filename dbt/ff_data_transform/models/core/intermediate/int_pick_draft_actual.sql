{{ config(materialized="table", unique_key='pick_id') }}

/*
Actual rookie draft picks extracted from commissioner transactions.

Purpose: Capture the real draft order, player selections, and franchise ownership
directly from `rookie_draft_selection` transactions. This becomes the source of
truth for base picks once a draft is complete and enables TBD→actual lifecycle
transitions.

Grain: One row per draft pick (base + compensatory) per season.

Source Columns:
- stg_sheets__transactions.transaction_id (draft event id)
- round / pick_number columns from the commissioner sheet
- to_franchise_* columns identify the drafting franchise

Outputs:
- Canonical pick_id: YYYY_R#_P##
- overall_pick: sequential order within the season
- slot_number: order within the round (used to classify base vs compensatory)
- pick_type: 'base' for slots 1-12, 'compensatory' otherwise
- drafted player + franchise metadata
*/
with
    draft_selections as (
        select
            transaction_id as draft_transaction_id,
            season,
            coalesce(pick_round, try_cast(round as integer)) as round_number,
            try_cast(pick_number as integer) as pick_number_int,
            pick_overall_number,
            transaction_date,
            to_franchise_id as drafted_by_franchise_id,
            to_franchise_name as drafted_by_franchise_name,
            player_id as drafted_player_id,
            player_name as drafted_player_name,
            position as drafted_player_position
        from {{ ref("stg_sheets__transactions") }}
        where
            transaction_type = 'rookie_draft_selection'
            -- Include "no selection" picks (asset_type='unknown')
            -- These are legitimate picks where franchise chose not to draft
            -- (typically due to roster space constraints or lack of trade partners)
            -- They occupy a position in draft order and count toward base picks
            and asset_type in ('player', 'unknown')
            and season <= {{ var("latest_completed_draft_season") }}
    ),

    normalized as (
        select
            *,
            -- Prefer explicit pick_overall_number, fallback to pick_number,
            -- finally to transaction order within season.
            coalesce(pick_overall_number, pick_number_int) as declared_overall_pick
        from draft_selections
        where round_number is not null
    ),

    ordered as (
        select
            *,
            row_number() over (
                partition by season
                order by coalesce(declared_overall_pick, 9999), transaction_date, draft_transaction_id
            ) as overall_pick_rank
        from normalized
    ),

    slotted as (
        select *, row_number() over (partition by season, round_number order by overall_pick_rank) as slot_number
        from ordered
    )

select
    season,
    round_number as round,
    coalesce(declared_overall_pick, overall_pick_rank) as overall_pick,
    slot_number,
    case when slot_number <= 12 then 'base' else 'compensatory' end as pick_type,
    slot_number > 12 as is_compensatory,
    season || '_R' || round_number || '_P' || lpad(slot_number::varchar, 2, '0') as pick_id,
    draft_transaction_id,
    drafted_by_franchise_id,
    drafted_by_franchise_name,
    drafted_player_id,
    drafted_player_name,
    drafted_player_position,
    transaction_date as draft_timestamp,
    current_timestamp as ingested_at
from slotted
order by season, round, slot_number
