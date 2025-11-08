{{
    config(
        severity = 'error',
        tags = ['critical', 'data_integrity', 'pre_rebuild']
    )
}}

/*
No Duplicate Pick IDs in dim_pick

Purpose: Ensure pick_id is unique in dim_pick (primary key constraint).

Why This Matters:
- pick_id is the natural key for dim_pick
- Duplicates break FK relationships in fact tables
- Indicates logic errors in pick generation or lifecycle management

Potential Causes of Duplicates:
1. TBD picks not properly filtered when superseded
2. Multiple sources generating same pick_id
3. Lifecycle control logic error

If This Test Fails:
- Check lifecycle_state distribution
- Verify SUPERSEDED picks are filtered in dim_pick WHERE clause
- Review dim_pick_lifecycle_control for duplicates
*/

with pick_id_counts as (
    select
        pick_id,
        count(*) as occurrence_count,
        string_agg(distinct lifecycle_state, ', ') as states,
        string_agg(distinct pick_type, ', ') as types
    from {{ ref('dim_pick') }}
    group by pick_id
)

select
    pick_id,
    occurrence_count,
    states,
    types,
    'Duplicate pick_id in dim_pick - violates uniqueness constraint' as issue
from pick_id_counts
where occurrence_count > 1
order by occurrence_count desc, pick_id
