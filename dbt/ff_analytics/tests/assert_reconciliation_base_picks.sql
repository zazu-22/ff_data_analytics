{{
    config(
        severity = 'error',
        tags = ['reconciliation', 'quality', 'pre_rebuild']
    )
}}

/*
Reconciliation: Base Pick Count per Round

Purpose: Verify every historical round has exactly 12 base picks in dim_pick.

Why This Matters:
- Validates generated base picks are complete
- Ensures comp picks start at correct slot (P13+)
- Prevents mislabeling due to missing base picks

Expectation: 12 base picks per round × 5 rounds × 13 years (2012-2024) = 780 base picks

This test complements assert_12_base_picks_per_round by validating the
FINAL dim_pick output, not just the intermediate validation model.
*/

with base_picks_by_round as (
    select
        season,
        round,
        count(*) filter (where pick_type = 'base') as base_count
    from {{ ref('dim_pick') }}
    where season <= {{ var('latest_completed_draft_season') }}
        and lifecycle_state = 'ACTUAL'  -- Exclude TBD picks
    group by season, round
)

select
    season,
    round,
    base_count,
    '12 base picks required per round' as rule,
    'Found ' || base_count::varchar || ' base picks, expected 12' as issue
from base_picks_by_round
where base_count != 12
order by season, round
