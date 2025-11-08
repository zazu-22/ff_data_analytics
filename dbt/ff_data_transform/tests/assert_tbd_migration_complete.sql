{{
    config(
        severity = 'warn',
        tags = ['lifecycle', 'quality']
    )
}}

/*
TBD Pick Migration Completeness

Purpose: Verify TBD picks are superseded when draft completes for that season.

When This Applies:
- Only for seasons that have completed drafts
- Currently: No actual draft data yet, so this test will pass trivially
- Future: When actual draft data available, will validate TBD → actual transitions

Lifecycle Flow:
1. TBD pick created: 2025_R1_TBD, lifecycle_state = ACTIVE_TBD
2. 2025 draft completes: Actual picks created (e.g., 2025_R1_P05)
3. TBD superseded: lifecycle_state = SUPERSEDED, superseded_by_pick_id = 2025_R1_P05
4. dim_pick filters: SUPERSEDED picks excluded, only actual picks appear

Expected Behavior:
- Completed seasons (≤ latest_completed_draft_season): No ACTIVE_TBD picks
- Future seasons (> latest_completed_draft_season): ACTIVE_TBD picks allowed

Current State:
- No actual draft data yet, so all TBD picks are correctly ACTIVE_TBD
- This test will only fail when we add actual draft data but forget to supersede TBDs
*/

with completed_seasons as (
    -- Seasons where draft should be finalized
    select distinct season
    from {{ ref('dim_pick') }}
    where season <= {{ var('latest_completed_draft_season') }}
        and pick_type != 'tbd'  -- Only seasons with actual picks
),

tbd_picks_in_completed_seasons as (
    select
        lc.pick_id,
        lc.season,
        lc.round,
        lc.lifecycle_state,
        lc.superseded_by_pick_id,
        lc.superseded_at
    from {{ ref('dim_pick_lifecycle_control') }} lc
    inner join completed_seasons cs
        on lc.season = cs.season
    where lc.pick_id like '%_TBD'
)

select
    pick_id,
    season,
    round,
    lifecycle_state,
    superseded_by_pick_id,
    'TBD pick not superseded despite draft completing for season ' || season::varchar as issue,
    'Expected lifecycle_state=SUPERSEDED with superseded_by_pick_id populated' as expected
from tbd_picks_in_completed_seasons
where lifecycle_state != 'SUPERSEDED'
order by season, round
