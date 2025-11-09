{{
    config(
        materialized="table",
        unique_key=['snapshot_date', 'gm_full_name', 'year', 'round', 'source_type', 'acquisition_note']
    )
}}

/*
Stage Commissioner draft pick holdings with franchise alignment and pick classification.

Source: data/raw/commissioner/draft_picks/ (parse_commissioner_sheet output)
Output grain: one row per GM (current or prior owner) per pick per snapshot partition
Highlights:
  - Map GM display names to franchise_id using dim_franchise tenure windows
  - Classify picks into original, acquired, compensatory, and trade_out buckets
  - Flag current holdings (excludes trade_out + pending contingencies)
  - Preserve acquisition/trade partner context for lineage analysis
*/
with
    raw as (
        select
            gm,
            gm_tab,
            year,
            round,
            source_type,
            original_owner,
            acquired_from,
            acquisition_note,
            trade_recipient,
            condition_flag,
            dt as snapshot_date
        from
            read_parquet(
                '{{ var("external_root", "data/raw") }}/commissioner/draft_picks/dt=*/*.parquet',
                hive_partitioning = true,
                union_by_name = true
            )
        where
            1 = 1
            and {{ snapshot_selection_strategy(
                var("external_root", "data/raw") ~ '/commissioner/draft_picks/dt=*/*.parquet',
                strategy='latest_only'
            ) }}
    ),

    with_franchise as (
        select raw.*, fran.franchise_id, fran.franchise_name, fran.owner_name
        from raw
        left join
            {{ ref("dim_franchise") }} fran
            on raw.gm_tab = fran.gm_tab
            and raw.year between fran.season_start and fran.season_end
    ),

    classified as (select *, lower(coalesce(acquisition_note, '')) as acquisition_note_lower from with_franchise),

    enriched as (
        select
            c.*,
            case
                when c.source_type = 'trade_out'
                then 'trade_out'
                when c.acquisition_note_lower like 'compensation%'
                then 'compensatory'
                when c.acquisition_note_lower like 'comp%'
                then 'compensatory'
                when c.source_type = 'acquired'
                then 'acquired'
                when c.source_type = 'owned'
                then 'original'
                else 'unknown'
            end as pick_category,
            case
                when c.source_type = 'trade_out' then false when c.condition_flag then false else true
            end as is_current_holding,
            case
                when c.acquisition_note_lower like 'compensation%'
                then true
                when c.acquisition_note_lower like 'comp%'
                then true
                else false
            end as is_comp_pick,
            -- Note: trade_recipient and acquisition_note contain franchise names from
            -- raw data
            -- These will need franchise mapping at query time if needed
            c.trade_recipient as trade_recipient_key,
            coalesce(nullif(c.acquisition_note, ''), split_part(c.gm, ' ', 1)) as acquisition_owner_key
        from classified c
    )

select
    snapshot_date,
    year,
    round,
    gm as gm_full_name,
    gm_tab,
    franchise_id,
    franchise_name,
    owner_name as franchise_owner_name,
    source_type,
    pick_category,
    original_owner,
    acquired_from,
    acquisition_note,
    acquisition_owner_key,
    trade_recipient,
    trade_recipient_key,
    condition_flag as is_pending,
    is_current_holding,
    is_comp_pick
from enriched
where pick_category != 'unknown'
