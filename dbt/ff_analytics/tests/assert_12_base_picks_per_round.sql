{{
    config(
        severity = 'error',
        tags = ['critical', 'data_integrity', 'pre_rebuild']
    )
}}

/*
12 Base Picks Per Round Validation Test

Purpose: Ensure every historical round has exactly 12 base picks.

Why This Matters:
- 12-team league requires 12 base picks per round
- Missing picks cause comp picks to be mislabeled as base picks
- Slot numbering depends on complete base pick coverage

Violation Example:
  season: 2023
  round: 2
  base_picks_count: 11
  validation_status: INCOMPLETE_BASE_PICKS
  validation_message: "Missing 1 base picks (expected 12, found 11)"
  issue: "Round missing base picks - comp picks may be mislabeled"

When This Fails:
- Check int_pick_draft_validation for detailed diagnostics
- If actual draft data: missing transaction in rookie_draft_selection
- If generated data: bug in int_pick_base generation logic

Fix:
- Actual draft data: Add missing transaction or use fallback
- Generated data: Fix int_pick_base generation (should never fail)
*/

with validation as (
    select
        season,
        round,
        base_picks_count,
        has_complete_base_picks,
        validation_status,
        validation_message,
        pick_source
    from {{ ref('int_pick_draft_validation') }}
    where season >= 2012  -- Earliest reliable data
        and season <= {{ var('latest_completed_draft_season') }}
)

select
    season,
    round,
    base_picks_count,
    validation_status,
    validation_message,
    pick_source,
    'Round missing base picks - comp picks may be mislabeled!' as issue
from validation
where not has_complete_base_picks
