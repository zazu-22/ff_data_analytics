{{ config(materialized="table", unique_key='pick_id') }}

/*
Pick Lifecycle Control - Manages TBD → Actual Pick Transitions

Purpose: Track lifecycle states of draft picks, especially TBD picks that
transition to actual picks when draft order is finalized.

Current State (P1-020 Fix):
- TBD → Actual matching NOT YET IMPLEMENTED
- All TBD picks remain in ACTIVE_TBD state indefinitely
- superseded_by_pick_id and superseded_at are always NULL
- Downstream models (dim_pick, int_pick_transaction_xref) handle NULL values correctly

Implementation Needed:
TBD → Actual matching requires franchise ownership tracking:
1. Determine which franchise owned the TBD pick at creation time
2. Match to the actual pick that franchise received in that season/round
3. Cannot match on (season, round) alone - creates Cartesian products (1 TBD × N actual picks)

Example: 2023_R1_TBD cannot match to all 21 actual picks in 2023 R1
         Need to know which franchise's R1 pick it was, then match to their specific pick

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
    tbd_picks as (
        -- All TBD picks ever created (from transaction references)
        -- These remain in ACTIVE_TBD state until TBD → Actual matching is implemented
        select distinct
            pick_id as tbd_pick_id,
            season,
            round,
            'ACTIVE_TBD' as lifecycle_state,
            current_timestamp as created_at,
            cast(null as timestamp) as superseded_at,
            cast(null as varchar) as superseded_by_pick_id
        from {{ ref("int_pick_tbd") }}
    )

select
    tbd_pick_id as pick_id,
    season,
    round,
    lifecycle_state,
    created_at,
    superseded_at,
    superseded_by_pick_id,

    -- Migration note (always NULL until TBD → Actual matching implemented)
    case
        when lifecycle_state = 'SUPERSEDED' then 'WARN: Transactions should migrate to ' || superseded_by_pick_id
    end as migration_note,

    -- v2 metadata
    'v2_lifecycle_control' as control_version,
    current_timestamp as last_updated

from tbd_picks
order by season, round
