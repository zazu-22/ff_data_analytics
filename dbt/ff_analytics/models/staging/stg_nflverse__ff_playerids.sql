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
5. Attempt fallback matching for cleared sleeper_ids (match on name/position/birthdate from Sleeper DB)
6. Deduplicate gsis_id duplicates (keep player with higher draft_year)
7. Deduplicate mfl_id duplicates (keep player with higher draft_year)
8. Assign sequential player_id (deterministic ordering)
9. Generate name_last_first variant
10. Track all corrections in xref_correction_status
11. Validate data quality (no duplicate IDs, sentinel usage, at least one ID per player)

Deduplication Philosophy:
- ALL player records are preserved (no rows deleted)
- Only duplicate provider IDs are cleared (not entire players)
- Cleared numeric IDs use sentinel value -1 (better observability than NULL)
- Cleared VARCHAR IDs use sentinel value 'DUPLICATE_CLEARED'
- This assumes duplicate IDs are data quality issues from the provider, not duplicate players

Fallback Matching:
When sleeper_id duplicates are cleared due to birthdate mismatches, the model attempts
to find the correct sleeper_id by matching on:
- Name: Exact match on name or merge_name (normalized, lowercase)
- Position: Exact match on position
- Birthdate: Match on birthdate from nflverse (since Sleeper birthdate didn't match)
- Exclusions: Candidate sleeper_id must not already be used in xref or in duplicate set

If a match is found, sleeper_id is corrected and status set to 'corrected_sleeper_id'.
If no match, sleeper_id remains -1 and status is 'cleared_sleeper_duplicate'.

Grain: One row per player (after filtering and deduplication)
Source: nflverse ff_playerids dataset (~9,734 valid players after filtering)
*/

with raw_players as (
    select *
    from read_parquet(
        '{{ var("external_root", "data/raw") }}/nflverse/ff_playerids/dt=*/ff_playerids_*.parquet',
        hive_partitioning = true
    )
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
-- Deduplicate by sleeper_player_id (keep latest snapshot)
sleeper_players_raw as (
    select
        sleeper_player_id,
        birth_date as sleeper_birth_date,
        dt
    from read_parquet(
        '{{ var("external_root", "data/raw") }}/sleeper/players/dt=*/players_*.parquet',
        hive_partitioning = true
    )
    where sleeper_player_id is not null
      -- Filter out team entries (non-numeric IDs like "HOU", "NE")
      and try_cast(sleeper_player_id as integer) is not null
),

sleeper_players as (
    select
        sleeper_player_id,
        sleeper_birth_date,
        full_name,
        sleeper_position
    from (
        select
            sleeper_player_id,
            sleeper_birth_date,
            full_name,
            position as sleeper_position,
            row_number() over (
                partition by sleeper_player_id
                order by dt desc
            ) as _rn
        from (
            select
                sleeper_player_id,
                birth_date as sleeper_birth_date,
                full_name,
                position,
                dt
            from read_parquet(
                '{{ var("external_root", "data/raw") }}/sleeper/players/dt=*/players_*.parquet',
                hive_partitioning = true
            )
            where sleeper_player_id is not null
              -- Filter out team entries (non-numeric IDs like "HOU", "NE")
              and try_cast(sleeper_player_id as integer) is not null
        )
    )
    where _rn = 1
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
        ws.* exclude (xref_correction_status),
        sp.sleeper_birth_date,
        case
            when sd.sleeper_id is not null
                and sp.sleeper_birth_date is not null
                and ws.birthdate != sp.sleeper_birth_date
            then 'cleared_sleeper_duplicate'
            when sd.sleeper_id is not null
                and sp.sleeper_birth_date is not null
                and ws.birthdate = sp.sleeper_birth_date
            then 'kept_sleeper_verified'
            else ws.xref_correction_status
        end as xref_correction_status
    from with_status ws
    left join sleeper_duplicates sd
        on ws.sleeper_id = sd.sleeper_id
    left join sleeper_players sp
        on ws.sleeper_id = try_cast(sp.sleeper_player_id as integer)
),

-- Clear incorrect sleeper_id mappings (but keep the player!)
-- Use -1 as sentinel value for cleared numeric IDs (better observability than NULL)
sleeper_deduped as (
    select
        * exclude (sleeper_birth_date, sleeper_id),
        case
            when xref_correction_status = 'cleared_sleeper_duplicate'
            then -1  -- Sentinel value: indicates ID was cleared due to duplicate
            else sleeper_id
        end as sleeper_id
    from with_sleeper_validation
),

-- Fallback matching: Attempt to find correct sleeper_id for cleared duplicates
-- Match on name, position, and birthdate from Sleeper players database
--
-- Matching Criteria:
-- - Name: Exact match on name or merge_name (normalized, lowercase, trimmed)
-- - Position: Exact match on position
-- - Birthdate: Match on birthdate from nflverse (since Sleeper birthdate didn't match)
--
-- Exclusions:
-- - Candidate sleeper_id must not already be used in xref (check sleeper_deduped)
-- - Candidate sleeper_id must not be in the duplicate set being resolved
--
-- Match Selection:
-- - Prefer exact name match (name) over normalized match (merge_name)
-- - Use deterministic tiebreaker (sleeper_player_id) if multiple matches
-- - One match per cleared sleeper_id (partition by mfl_id, gsis_id, name, birthdate)
--
-- Result:
-- - If match found: sleeper_id corrected, status = 'corrected_sleeper_id'
-- - If no match: sleeper_id remains -1, status = 'cleared_sleeper_duplicate'
sleeper_fallback_candidates as (
    select
        sd.*,
        sp.sleeper_player_id as candidate_sleeper_id,
        sp.full_name as sleeper_full_name,
        sp.sleeper_position,
        -- Match scoring: prefer exact name match, then position match, then birthdate match
        case
            when lower(trim(sd.name)) = lower(trim(sp.full_name)) then 100
            when lower(trim(sd.merge_name)) = lower(trim(sp.full_name)) then 90
            else 0
        end as name_match_score,
        case
            when sd.position = sp.sleeper_position then 10
            else 0
        end as position_match_score,
        case
            when sd.birthdate = sp.sleeper_birth_date then 5
            else 0
        end as birthdate_match_score
    from sleeper_deduped sd
    cross join sleeper_players sp
    where sd.sleeper_id = -1  -- Only attempt fallback for cleared sleeper_ids
      and sd.birthdate is not null  -- Require birthdate for matching
      -- Name matching (exact or normalized)
      and (
          lower(trim(sd.name)) = lower(trim(sp.full_name))
          or lower(trim(sd.merge_name)) = lower(trim(sp.full_name))
      )
      -- Position matching
      and sd.position = sp.sleeper_position
      -- Birthdate matching (use nflverse birthdate since Sleeper didn't match)
      and sd.birthdate = sp.sleeper_birth_date
      -- Exclude candidates already used in xref (check current state)
      and try_cast(sp.sleeper_player_id as integer) not in (
          select sleeper_id
          from sleeper_deduped
          where sleeper_id != -1
            and sleeper_id is not null
      )
      -- Exclude candidates in the duplicate set being resolved
      and try_cast(sp.sleeper_player_id as integer) not in (
          select sleeper_id
          from sleeper_duplicates
      )
),

-- Select best match per player using deterministic tiebreakers
sleeper_fallback_matched as (
    select
        * exclude (candidate_sleeper_id, sleeper_full_name, sleeper_position, name_match_score, position_match_score, birthdate_match_score),
        candidate_sleeper_id as matched_sleeper_id,
        name_match_score + position_match_score + birthdate_match_score as total_match_score
    from sleeper_fallback_candidates
    qualify row_number() over (
        partition by mfl_id, gsis_id, name, birthdate
        order by
            name_match_score + position_match_score + birthdate_match_score desc,
            candidate_sleeper_id  -- Deterministic tiebreaker
    ) = 1
),

-- Apply fallback matches: update sleeper_id and status for matched players
sleeper_with_fallback as (
    select
        sd.* exclude (sleeper_id, xref_correction_status),
        case
            when fm.matched_sleeper_id is not null
            then try_cast(fm.matched_sleeper_id as integer)
            else sd.sleeper_id
        end as sleeper_id,
        case
            when fm.matched_sleeper_id is not null
            then 'corrected_sleeper_id'
            else sd.xref_correction_status
        end as xref_correction_status
    from sleeper_deduped sd
    left join sleeper_fallback_matched fm
        on sd.mfl_id = fm.mfl_id
        and sd.gsis_id = fm.gsis_id
        and sd.name = fm.name
        and sd.birthdate = fm.birthdate
),

-- Find gsis_id duplicates (exclude sentinel values)
gsis_duplicates as (
    select gsis_id
    from sleeper_with_fallback
    where gsis_id is not null
      and gsis_id != 'DUPLICATE_CLEARED'  -- Exclude already-cleared IDs
      group by gsis_id
      having count(*) > 1
),

-- Deduplicate gsis_id (keep player with higher draft_year, tiebreaker: name)
gsis_ranked as (
    select
        swf.*,
        case
            when gd.gsis_id is not null
            then row_number() over (
                partition by swf.gsis_id
                order by swf.draft_year desc nulls last, swf.name
            )
            else 1
        end as _gsis_rank
    from sleeper_with_fallback swf
    left join gsis_duplicates gd
        on swf.gsis_id = gd.gsis_id
),

gsis_deduped as (
    select
        gr.* exclude (_gsis_rank, gsis_id, xref_correction_status),
        case
            when gr._gsis_rank > 1 then 'DUPLICATE_CLEARED'  -- Sentinel value for VARCHAR IDs
            else gr.gsis_id
        end as gsis_id,
        case
            when gd.gsis_id is not null and gr._gsis_rank > 1
            then 'cleared_gsis_duplicate'
            when gd.gsis_id is not null and gr._gsis_rank = 1
            then 'kept_gsis_newer'
            else gr.xref_correction_status
        end as xref_correction_status
    from gsis_ranked gr
    left join gsis_duplicates gd
        on gr.gsis_id = gd.gsis_id
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

-- Deduplicate mfl_id (keep player with higher draft_year, tiebreaker: name)
mfl_ranked as (
    select
        gd.*,
        case
            when md.mfl_id is not null
            then row_number() over (
                partition by gd.mfl_id
                order by gd.draft_year desc nulls last, gd.name
            )
            else 1
        end as _mfl_rank
    from gsis_deduped gd
    left join mfl_duplicates md
        on gd.mfl_id = md.mfl_id
),

mfl_deduped as (
    select
        mr.* exclude (_mfl_rank, mfl_id, xref_correction_status),
        case
            when mr._mfl_rank > 1 then -1  -- Sentinel value: indicates ID was cleared due to duplicate
            else mr.mfl_id
        end as mfl_id,
        case
            when md.mfl_id is not null and mr._mfl_rank = 1
            then 'kept_mfl_newer'
            when md.mfl_id is not null and mr._mfl_rank > 1
            then 'cleared_mfl_duplicate'
            else mr.xref_correction_status
        end as xref_correction_status
    from mfl_ranked mr
    left join mfl_duplicates md
        on mr.mfl_id = md.mfl_id
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

-- Data quality validations (fail if violations exist)
validate_no_duplicate_ids as (
    -- Assert no duplicate provider IDs remain (excluding sentinel values)
    -- This is a critical integrity check - duplicates would cause join explosions downstream
    select
        'sleeper_id' as id_type,
        sleeper_id as id_value,
        count(*) as duplicate_count,
        string_agg(mfl_id || '|' || coalesce(gsis_id, '') || '|' || name, ', ' order by mfl_id) as player_keys
    from with_name_variant
    where sleeper_id is not null
      and sleeper_id != -1  -- Exclude sentinel values
    group by sleeper_id
    having count(*) > 1
    
    union all
    
    select
        'gsis_id' as id_type,
        cast(gsis_id as varchar) as id_value,
        count(*) as duplicate_count,
        string_agg(mfl_id || '|' || coalesce(cast(sleeper_id as varchar), '') || '|' || name, ', ' order by mfl_id) as player_keys
    from with_name_variant
    where gsis_id is not null
      and gsis_id != 'DUPLICATE_CLEARED'  -- Exclude sentinel values
    group by gsis_id
    having count(*) > 1
    
    union all
    
    select
        'mfl_id' as id_type,
        cast(mfl_id as varchar) as id_value,
        count(*) as duplicate_count,
        string_agg(coalesce(gsis_id, '') || '|' || coalesce(cast(sleeper_id as varchar), '') || '|' || name, ', ' order by gsis_id) as player_keys
    from with_name_variant
    where mfl_id is not null
      and mfl_id != -1  -- Exclude sentinel values
    group by mfl_id
    having count(*) > 1
),

validate_sentinel_usage as (
    -- Ensure sentinels only used where status indicates clearing
    -- sleeper_id = -1 only when status contains 'cleared' or 'corrected'
    -- gsis_id = 'DUPLICATE_CLEARED' only when status contains 'cleared'
    -- mfl_id = -1 only when status contains 'cleared'
    select
        'sleeper_id_sentinel_mismatch' as violation_type,
        mfl_id || '|' || coalesce(gsis_id, '') || '|' || name as player_key,
        sleeper_id,
        xref_correction_status
    from with_name_variant
    where sleeper_id = -1
      and xref_correction_status not in ('cleared_sleeper_duplicate', 'corrected_sleeper_id')
    
    union all
    
    select
        'gsis_id_sentinel_mismatch' as violation_type,
        mfl_id || '|' || coalesce(cast(sleeper_id as varchar), '') || '|' || name as player_key,
        cast(gsis_id as varchar) as sleeper_id,
        xref_correction_status
    from with_name_variant
    where gsis_id = 'DUPLICATE_CLEARED'
      and xref_correction_status not like '%cleared%'
      and xref_correction_status not like '%gsis%'
    
    union all
    
    select
        'mfl_id_sentinel_mismatch' as violation_type,
        coalesce(gsis_id, '') || '|' || coalesce(cast(sleeper_id as varchar), '') || '|' || name as player_key,
        cast(mfl_id as varchar) as sleeper_id,
        xref_correction_status
    from with_name_variant
    where mfl_id = -1
      and xref_correction_status not like '%cleared%'
      and xref_correction_status not like '%mfl%'
),

validate_at_least_one_id as (
    -- Ensure each player has at least one provider ID (not all cleared/NULL)
    -- At least one of: mfl_id, gsis_id, sleeper_id, espn_id, yahoo_id, pfr_id != sentinel/NULL
    select
        'no_provider_ids' as violation_type,
        mfl_id || '|' || coalesce(gsis_id, '') || '|' || name as player_key,
        name,
        mfl_id,
        gsis_id,
        sleeper_id,
        espn_id,
        yahoo_id,
        pfr_id
    from with_name_variant
    where (mfl_id is null or mfl_id = -1)
      and (gsis_id is null or gsis_id = 'DUPLICATE_CLEARED')
      and (sleeper_id is null or sleeper_id = -1)
      and espn_id is null
      and yahoo_id is null
      and pfr_id is null
),

-- Assign sequential player_id (deterministic ordering for stability)
with_player_id as (
    select
        *,
        row_number() over (
            order by mfl_id, gsis_id, name
        ) as player_id
    from with_name_variant
    -- Fail if any validation violations exist
    where not exists (select 1 from validate_no_duplicate_ids)
      and not exists (select 1 from validate_sentinel_usage)
      and not exists (select 1 from validate_at_least_one_id)
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

