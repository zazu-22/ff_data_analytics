{{ config(materialized='table') }}

/*
Staging model for nflverse ff_playerids with deduplication logic.

This replaces the seed-based approach (scripts/seeds/generate_dim_player_id_xref.py)
and ensures the crosswalk is always fresh from raw data.

Process:
1. Load raw nflverse ff_playerids data
2. Filter out team placeholder entries (those with only mfl_id, no other provider IDs)
3. Join with Sleeper players for birthdate validation
4. Deduplicate sleeper_id duplicates (match birthdate with Sleeper API, clear mismatches)
5. Deduplicate gsis_id duplicates (keep player with higher draft_year)
6. Deduplicate mfl_id duplicates (keep player with higher draft_year)
7. Assign sequential player_id (deterministic ordering)
8. Generate name_last_first variant
9. Track all corrections in xref_correction_status

Deduplication Philosophy:
- ALL player records are preserved (no rows deleted)
- Only duplicate provider IDs are cleared (not entire players)
- Cleared numeric IDs use sentinel value -1 (better observability than NULL)
- Cleared VARCHAR IDs use sentinel value 'DUPLICATE_CLEARED'
- This assumes duplicate IDs are data quality issues from the provider, not duplicate players

Grain: One row per player (after filtering and deduplication)
Source: nflverse ff_playerids dataset (~9,734 valid players after filtering)
*/

with raw_players as (
    select *
    from {{ source('nflverse', 'ff_playerids') }}
),

-- Filter out team placeholder entries (critical to prevent join explosions)
-- Keep only rows with at least one provider ID beyond mfl_id
filtered as (
    select *
    from raw_players
    where gsis_id is not null
       or sleeper_id is not null
       or espn_id is not null
       or yahoo_id is not null
       or pfr_id is not null
),

-- Load Sleeper players for birthdate validation (filter out team entries)
sleeper_players as (
    select
        sleeper_player_id,
        birth_date as sleeper_birth_date
    from {{ source('sleeper', 'players') }}
    where sleeper_player_id is not null
      -- Filter out team entries (non-numeric IDs like "HOU", "NE")
      and try_cast(sleeper_player_id as integer) is not null
),

-- Initial status column (default: original)
with_status as (
    select
        *,
        'original' as xref_correction_status
    from filtered
),

-- Find sleeper_id duplicates (exclude sentinel values)
sleeper_duplicates as (
    select sleeper_id
    from with_status
    where sleeper_id is not null
      and sleeper_id != -1  -- Exclude already-cleared IDs (though none should exist yet)
    group by sleeper_id
    having count(*) > 1
),

-- Join with Sleeper API for birthdate validation
with_sleeper_validation as (
    select
        ws.*,
        sp.sleeper_birth_date,
        case
            when ws.sleeper_id in (select sleeper_id from sleeper_duplicates)
                and sp.sleeper_birth_date is not null
                and ws.birthdate != sp.sleeper_birth_date
            then 'cleared_sleeper_duplicate'
            when ws.sleeper_id in (select sleeper_id from sleeper_duplicates)
                and sp.sleeper_birth_date is not null
                and ws.birthdate = sp.sleeper_birth_date
            then 'kept_sleeper_verified'
            else ws.xref_correction_status
        end as xref_correction_status
    from with_status ws
    left join sleeper_players sp
        on ws.sleeper_id = try_cast(sp.sleeper_player_id as integer)
),

-- Clear incorrect sleeper_id mappings (but keep the player!)
-- Use -1 as sentinel value for cleared numeric IDs (better observability than NULL)
sleeper_deduped as (
    select
        * exclude (sleeper_birth_date),
        case
            when xref_correction_status = 'cleared_sleeper_duplicate'
            then -1  -- Sentinel value: indicates ID was cleared due to duplicate
            else sleeper_id
        end as sleeper_id
    from with_sleeper_validation
),

-- Find gsis_id duplicates (exclude sentinel values)
gsis_duplicates as (
    select gsis_id
    from sleeper_deduped
    where gsis_id is not null
      and gsis_id != 'DUPLICATE_CLEARED'  -- Exclude already-cleared IDs
    group by gsis_id
    having count(*) > 1
),

-- Deduplicate gsis_id (keep player with higher draft_year)
gsis_ranked as (
    select
        *,
        case
            when gsis_id in (select gsis_id from gsis_duplicates)
            then dense_rank() over (
                partition by gsis_id
                order by draft_year desc nulls last
            )
            else 1
        end as _gsis_rank
    from sleeper_deduped
),

gsis_deduped as (
    select
        * exclude (_gsis_rank),
        case
            when _gsis_rank > 1 then 'DUPLICATE_CLEARED'  -- Sentinel value for VARCHAR IDs
            else gsis_id
        end as gsis_id,
        case
            when gsis_id in (select gsis_id from gsis_duplicates) and _gsis_rank > 1
            then 'cleared_gsis_duplicate'
            when gsis_id in (select gsis_id from gsis_duplicates) and _gsis_rank = 1
            then 'kept_gsis_newer'
            else xref_correction_status
        end as xref_correction_status
    from gsis_ranked
),

-- Find mfl_id duplicates (exclude sentinel values)
mfl_duplicates as (
    select mfl_id
    from gsis_deduped
    where mfl_id is not null
      and mfl_id != -1  -- Exclude already-cleared IDs
    group by mfl_id
    having count(*) > 1
),

-- Deduplicate mfl_id (keep player with higher draft_year)
mfl_ranked as (
    select
        *,
        case
            when mfl_id in (select mfl_id from mfl_duplicates)
            then dense_rank() over (
                partition by mfl_id
                order by draft_year desc nulls last
            )
            else 1
        end as _mfl_rank
    from gsis_deduped
),

mfl_deduped as (
    select
        * exclude (_mfl_rank),
        case
            when _mfl_rank > 1 then -1  -- Sentinel value: indicates ID was cleared due to duplicate
            else mfl_id
        end as mfl_id,
        case
            when mfl_id in (select mfl_id from mfl_duplicates) and _mfl_rank > 1
            then 'cleared_mfl_duplicate'
            when mfl_id in (select mfl_id from mfl_duplicates) and _mfl_rank = 1
            then 'kept_mfl_newer'
            else xref_correction_status
        end as xref_correction_status
    from mfl_ranked
),

-- Generate name_last_first variant (for FantasySharks projection matching)
with_name_variant as (
    select
        *,
        case
            when name like '% %' then
                split_part(name, ' ', 2) || ', ' || split_part(name, ' ', 1)
            else name
        end as name_last_first
    from mfl_deduped
),

-- Assign sequential player_id (deterministic ordering for stability)
with_player_id as (
    select
        *,
        row_number() over (
            order by mfl_id, gsis_id, name
        ) as player_id
    from with_name_variant
)

-- Select final columns matching seed schema (29 columns total)
select
    player_id,
    mfl_id,
    gsis_id,
    sleeper_id,
    espn_id,
    yahoo_id,
    pfr_id,
    fantasypros_id,
    pff_id,
    cbs_id,
    ktc_id,
    sportradar_id,
    fleaflicker_id,
    rotowire_id,
    rotoworld_id,
    stats_id,
    stats_global_id,
    fantasy_data_id,
    swish_id,
    cfbref_id,
    nfl_id,
    name,
    merge_name,
    name_last_first,
    position,
    team,
    birthdate,
    draft_year,
    xref_correction_status
from with_player_id
order by player_id

