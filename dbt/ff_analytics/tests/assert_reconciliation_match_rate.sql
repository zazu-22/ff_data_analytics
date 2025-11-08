{{
    config(
        severity = 'warn',
        tags = ['reconciliation', 'quality']
    )
}}

/*
Reconciliation: Match Rate Threshold (≥90%)

Purpose: Ensure at least 90% of comp picks MATCH between FAAD and dim_pick.

Why 90% threshold:
- Perfect 100% match is unlikely (data entry errors happen)
- 90% indicates healthy data quality
- Below 90% suggests systematic issues

Match Rate Calculation:
- MATCHED: FAAD award exists in dim_pick with correct sequence
- Total: All comp picks from either source

What constitutes a MATCH:
- Same FAAD transaction ID
- Same chronological sequence within round
- Pick exists in both FAAD registry and dim_pick

Non-matches to investigate:
- SEQUENCE_MISMATCH: Pick exists but wrong order
- FAAD_AWARD_NOT_IN_DIM_PICK: Missing from dim_pick
- DIM_PICK_WITHOUT_FAAD_AWARD: No FAAD record

Current State:
- This test may fail initially (known 2024 R2 issue)
- Use int_pick_comp_reconciliation to diagnose failures
*/

with reconciliation_stats as (
    select
        count(*) as total_comps,
        count(*) filter (where reconciliation_status = 'MATCHED') as matched_comps,
        count(*) filter (where reconciliation_status = 'FAAD_AWARD_NOT_IN_DIM_PICK') as faad_not_in_dim,
        count(*) filter (where reconciliation_status = 'DIM_PICK_WITHOUT_FAAD_AWARD') as dim_without_faad,
        count(*) filter (where reconciliation_status = 'SEQUENCE_MISMATCH') as sequence_mismatch,

        -- Match rate percentage
        round(
            100.0 * count(*) filter (where reconciliation_status = 'MATCHED') /
            nullif(count(*), 0),
            1
        ) as match_rate_pct
    from {{ ref('int_pick_comp_reconciliation') }}
),

threshold_check as (
    select
        *,
        90.0 as minimum_match_rate_pct,
        match_rate_pct >= 90.0 as meets_threshold
    from reconciliation_stats
)

select
    total_comps,
    matched_comps,
    faad_not_in_dim,
    dim_without_faad,
    sequence_mismatch,
    match_rate_pct,
    minimum_match_rate_pct,
    'Reconciliation match rate (' || match_rate_pct::varchar || '%) below 90% threshold' as issue,
    'Review int_pick_comp_reconciliation WHERE reconciliation_status != ''MATCHED'' for details' as recommendation
from threshold_check
where not meets_threshold
