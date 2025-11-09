{{ config(materialized="table") }}

/*
Pick Lifecycle Control - Manages TBD → Actual Pick Transitions

Purpose: Track lifecycle states of draft picks, especially TBD picks that
transition to actual picks when draft order is finalized.

Current State (v2 Phase 4):
- We do NOT have actual draft transaction data yet
- All TBD picks remain in ACTIVE_TBD state
- Infrastructure ready for future actual draft data

Future State (when actual draft data available):
- TBD picks transition to SUPERSEDED when draft completes
- superseded_by_pick_id points to the actual pick that replaced TBD
- Transactions can migrate from TBD to actual picks automatically

Grain: One row per pick that has lifecycle tracking (primarily TBD picks)

Lifecycle States:
- ACTIVE_TBD: TBD pick currently in use (draft order not finalized)
- SUPERSEDED: TBD pick replaced by actual pick (soft-delete)
- ACTUAL: Pick from actual draft data (future state)

Why Soft-Delete vs Hard-Delete:
- Preserves audit trail of TBD → actual transitions
- Allows transactions to reference superseded picks with migration pointers
- Enables "what TBDs existed before draft?" historical queries

Example Timeline:
  2025 Season: 2025_R1_TBD created, lifecycle_state = ACTIVE_TBD
  2026 Draft:  2025_R1_P05 created (team finished 5th)
  Post-Draft:  2025_R1_TBD superseded, superseded_by_pick_id = 2025_R1_P05
*/
with
    tbd_picks_created as (
        -- All TBD picks ever created (from transaction references)
        select distinct
            pick_id as tbd_pick_id,
            season,
            round,
            'ACTIVE_TBD' as lifecycle_state,
            current_timestamp as created_at,
            cast(null as timestamp) as superseded_at,
            cast(null as varchar) as superseded_by_pick_id
        from {{ ref("int_pick_tbd") }}
    ),

    actual_picks_created as (
        -- Actual picks from completed drafts (rookie_draft_selection transactions)
        select season, round, pick_id as actual_pick_id, draft_transaction_id, draft_timestamp as created_at
        from {{ ref("int_pick_draft_actual") }}
    ),

    -- Match TBD picks to their actual pick replacements
    -- Currently no matches since actual_picks_created is empty
    tbd_to_actual_mapping as (
        select
            tbd.tbd_pick_id,
            tbd.season,
            tbd.round,
            tbd.created_at,
            act.actual_pick_id as superseded_by_pick_id,
            act.created_at as superseded_at,
            case when act.actual_pick_id is not null then 'SUPERSEDED' else 'ACTIVE_TBD' end as lifecycle_state
        from tbd_picks_created tbd
        left join actual_picks_created act on tbd.season = act.season and tbd.round = act.round
    )

select
    tbd_pick_id as pick_id,
    season,
    round,
    lifecycle_state,
    created_at,
    superseded_at,
    superseded_by_pick_id,

    -- Audit flag for transactions still referencing TBD
    case
        when lifecycle_state = 'SUPERSEDED' then 'WARN: Transactions should migrate to ' || superseded_by_pick_id
    end as migration_note,

    -- v2 metadata
    'v2_lifecycle_control' as control_version,
    current_timestamp as last_updated

from tbd_to_actual_mapping
order by season, round
