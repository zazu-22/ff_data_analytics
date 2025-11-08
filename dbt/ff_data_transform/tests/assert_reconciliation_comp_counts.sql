{{
    config(
        severity = 'warn',
        tags = ['reconciliation', 'quality', 'pre_rebuild']
    )
}}

/*
Reconciliation: Comp Pick Counts - FAAD vs dim_pick

Purpose: Compare comp pick counts between FAAD awards and dim_pick per round.

Why WARN not ERROR:
- FAAD Comp column is authoritative but may have data entry errors
- Known issue: 2024 R2 has discrepancy (this test will expose it!)
- Variance is informative, not necessarily invalid

What This Test Will Show:
- Rounds where FAAD and dim_pick agree (good!)
- Rounds with discrepancies (investigate in int_pick_comp_reconciliation)
- Specifically: 2024 R2 discrepancy should appear here

Use int_pick_comp_reconciliation for detailed root cause analysis.
*/

with faad_comp_counts as (
    select
        comp_season as season,
        comp_round as round,
        count(*) as faad_comp_count
    from {{ ref('int_pick_comp_registry') }}
    where comp_season <= {{ var('latest_completed_draft_season') }}
    group by comp_season, comp_round
),

dim_comp_counts as (
    select
        season,
        round,
        count(*) as dim_comp_count
    from {{ ref('dim_pick') }}
    where pick_type = 'compensatory'
        and lifecycle_state = 'ACTUAL'
        and season <= {{ var('latest_completed_draft_season') }}
    group by season, round
)

select
    coalesce(f.season, d.season) as season,
    coalesce(f.round, d.round) as round,
    coalesce(f.faad_comp_count, 0) as faad_comp_count,
    coalesce(d.dim_comp_count, 0) as dim_comp_count,
    abs(coalesce(f.faad_comp_count, 0) - coalesce(d.dim_comp_count, 0)) as count_delta,
    'Comp pick count mismatch - check int_pick_comp_reconciliation for details' as issue
from faad_comp_counts f
full outer join dim_comp_counts d
    on f.season = d.season and f.round = d.round
where coalesce(f.faad_comp_count, 0) != coalesce(d.dim_comp_count, 0)
order by season, round
