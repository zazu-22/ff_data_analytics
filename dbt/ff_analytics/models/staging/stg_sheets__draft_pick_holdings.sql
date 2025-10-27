{{ config(materialized='table') }}

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

with raw as (
  select
    gm,
    year,
    round,
    source_type,
    original_owner,
    acquired_from,
    acquisition_note,
    trade_recipient,
    condition_flag,
    dt as snapshot_date
  from read_parquet(
    '{{ var("external_root", "data/raw") }}/commissioner/draft_picks/dt=*/*.parquet',
    hive_partitioning=true,
    union_by_name=true
  )
),

with_owner_keys as (
  select
    *,
    case
      when gm like 'Nick McCreary%' then 'McCreary'
      when gm like 'Nick Piper%' then 'Piper'
      else split_part(gm, ' ', 1)
    end as owner_key
  from raw
),

with_franchise as (
  select
    wok.*,
    fran.franchise_id,
    fran.franchise_name,
    fran.owner_name
  from with_owner_keys wok
  left join {{ ref('dim_franchise') }} fran
    on wok.owner_key = fran.owner_name
    and wok.year between fran.season_start and fran.season_end
),

classified as (
  select
    *,
    lower(coalesce(acquisition_note, '')) as acquisition_note_lower
  from with_franchise
),

enriched as (
  select
    c.*,
    case
      when source_type = 'trade_out' then 'trade_out'
      when acquisition_note_lower like 'compensation%' then 'compensatory'
      when acquisition_note_lower like 'comp%' then 'compensatory'
      when source_type = 'acquired' then 'acquired'
      when source_type = 'owned' then 'original'
      else 'unknown'
    end as pick_category,
    case
      when source_type = 'trade_out' then false
      when condition_flag then false
      else true
    end as is_current_holding,
    case
      when acquisition_note_lower like 'compensation%' then true
      when acquisition_note_lower like 'comp%' then true
      else false
    end as is_comp_pick,
    case
      when trade_recipient is null then null
      when trade_recipient like 'Nick McCreary%' then 'McCreary'
      when trade_recipient like 'Nick Piper%' then 'Piper'
      else split_part(trade_recipient, ' ', 1)
    end as trade_recipient_key,
    case
      when acquisition_note is null or acquisition_note = '' then owner_key
      when acquisition_note like 'Nick McCreary%' then 'McCreary'
      when acquisition_note like 'Nick Piper%' then 'Piper'
      else split_part(acquisition_note, ' ', 1)
    end as acquisition_owner_key
  from classified c
)

select
  snapshot_date,
  year,
  round,
  gm as gm_full_name,
  owner_key,
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
