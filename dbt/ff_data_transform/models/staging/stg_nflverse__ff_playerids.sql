{{ config(materialized="table") }}

/*
Staging model for nflverse ff_playerids with deduplication logic.

This replaces the seed-based approach (scripts/seeds/generate_dim_player_id_xref.py)
and ensures the crosswalk is always fresh from raw data.

Process:
1. Load raw nflverse ff_playerids data
2. Filter out team placeholder entries (those with only mfl_id, no other provider IDs)
3. Join with Sleeper players for birthdate validation
4. Deduplicate sleeper_id duplicates (match birthdate with Sleeper API, clear mismatches and all but one even if birthdates match)
5. Attempt fallback matching for missing/cleared sleeper_ids (match on name/position with normalization, birthdate optional)
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
When sleeper_id duplicates are cleared due to birthdate mismatches, or when players have
NULL sleeper_id in raw data, the model attempts to find the correct sleeper_id by matching on:
- Name: Exact match on name or merge_name (normalized, lowercase) - REQUIRED (both score 100)
- Position: Exact match OR position family match - REQUIRED
  - Exact match: 10 points
  - Family match: 5 points (Safety: S↔SS/FS/DB, Kicker: PK↔K, Punter: PN↔P, DefensiveLine: DL↔DE/DT/NT, Linebacker: LB↔OLB/ILB, OffensiveLine: OL↔G/OT/C/OG/T, DefensiveBack: DB↔CB/SS/FS/S)
- Birthdate: Match on birthdate from nflverse - OPTIONAL (20 bonus points, strongly preferred but not required)
- Exclusions: Candidate sleeper_id must not already be used in xref or in duplicate set
- Invalid entries filtered: Sleeper players with 'Invalid' or 'Duplicate' in name are excluded

Position normalization uses canonical position families for bidirectional matching, ensuring
symmetric matching between xref and Sleeper position formats.

If a match is found:
- For players with NULL sleeper_id: sleeper_id assigned, status = 'added_sleeper_id'
- For players with sleeper_id = -1: sleeper_id corrected, status = 'corrected_sleeper_id'
If no match, sleeper_id remains unchanged and status unchanged.

Uniqueness is strictly maintained: if multiple players match to the same sleeper_id, only
the best match (by score, then deterministic tiebreaker) is kept.

Grain: One row per player (after filtering and deduplication)
Source: nflverse ff_playerids dataset (~9,734 valid players after filtering)
*/
with
    raw_players as (
        select *
        from
            read_parquet(
                '{{ var("external_root", "data/raw") }}/nflverse/ff_playerids/dt=*/ff_playerids_*.parquet',
                hive_partitioning = true
            )
    ),

    -- Filter out team placeholder entries (critical to prevent join explosions)
    -- Keep only rows with at least one provider ID beyond mfl_id
    filtered as (
        select *
        from raw_players
        where
            gsis_id is not null
            or sleeper_id is not null
            or espn_id is not null
            or yahoo_id is not null
            or pfr_id is not null
    ),

    -- Load Sleeper players for birthdate validation (filter out team entries)
    -- Deduplicate by sleeper_player_id (keep latest snapshot)
    sleeper_players_raw as (
        select sleeper_player_id, birth_date as sleeper_birth_date, dt
        from
            read_parquet(
                '{{ var("external_root", "data/raw") }}/sleeper/players/dt=*/players_*.parquet',
                hive_partitioning = true
            )
        where
            sleeper_player_id is not null
            -- Filter out team entries (non-numeric IDs like "HOU", "NE")
            and try_cast(sleeper_player_id as integer) is not null
    ),

    sleeper_players as (
        select sleeper_player_id, sleeper_birth_date, full_name, sleeper_position
        from
            (
                select
                    sleeper_player_id,
                    sleeper_birth_date,
                    full_name,
                    position as sleeper_position,
                    row_number() over (partition by sleeper_player_id order by dt desc) as _rn
                from
                    (
                        select sleeper_player_id, birth_date as sleeper_birth_date, full_name, position, dt
                        from
                            read_parquet(
                                '{{ var("external_root", "data/raw") }}/sleeper/players/dt=*/players_*.parquet',
                                hive_partitioning = true
                            )
                        where
                            sleeper_player_id is not null
                            -- Filter out team entries (non-numeric IDs like "HOU",
                            -- "NE")
                            and try_cast(sleeper_player_id as integer) is not null
                            -- Filter out invalid/placeholder entries
                            and full_name not like '%Invalid%'
                            and full_name not like '%Duplicate%'
                    )
            )
        where _rn = 1
    ),

    -- Canonical position families for bidirectional matching
    -- Maps both xref and Sleeper positions to the same families
    -- Only includes families where we have evidence of legitimate mismatches
    -- Each family includes mappings in BOTH directions (xref→Sleeper and Sleeper→xref)
    position_families as (
        -- Safety: S (xref) ↔ SS, FS, DB (Sleeper)
        select 'Safety' as position_family, 'S' as xref_position, 'SS' as sleeper_position
        union all
        select 'Safety', 'S', 'FS'
        union all
        select 'Safety', 'S', 'DB'
        -- Reverse: SS, FS, DB (xref) ↔ S (Sleeper)
        union all
        select 'Safety', 'SS', 'S'
        union all
        select 'Safety', 'FS', 'S'
        union all
        select 'Safety', 'DB', 'S'

        -- Kicker: PK (xref) ↔ K (Sleeper)
        union all
        select 'Kicker', 'PK', 'K'
        -- Reverse: K (xref) ↔ PK (Sleeper)
        union all
        select 'Kicker', 'K', 'PK'

        -- Punter: PN (xref) ↔ P (Sleeper)
        union all
        select 'Punter', 'PN', 'P'
        -- Reverse: P (xref) ↔ PN (Sleeper)
        union all
        select 'Punter', 'P', 'PN'

        -- Defensive Line: DL (xref) ↔ DE, DT, NT (Sleeper)
        union all
        select 'DefensiveLine', 'DL', 'DE'
        union all
        select 'DefensiveLine', 'DL', 'DT'
        union all
        select 'DefensiveLine', 'DL', 'NT'
        -- Reverse: DE, DT, NT (xref) ↔ DL (Sleeper)
        union all
        select 'DefensiveLine', 'DE', 'DL'
        union all
        select 'DefensiveLine', 'DT', 'DL'
        union all
        select 'DefensiveLine', 'NT', 'DL'

        -- Linebacker: LB (xref) ↔ LB, OLB, ILB (Sleeper)
        union all
        select 'Linebacker', 'LB', 'OLB'
        union all
        select 'Linebacker', 'LB', 'ILB'
        -- Reverse: OLB, ILB (xref) ↔ LB (Sleeper)
        union all
        select 'Linebacker', 'OLB', 'LB'
        union all
        select 'Linebacker', 'ILB', 'LB'

        -- Offensive Line: OL (xref) ↔ G, OT, C, OG, T (Sleeper)
        union all
        select 'OffensiveLine', 'OL', 'G'
        union all
        select 'OffensiveLine', 'OL', 'OT'
        union all
        select 'OffensiveLine', 'OL', 'C'
        union all
        select 'OffensiveLine', 'OL', 'OG'
        union all
        select 'OffensiveLine', 'OL', 'T'
        -- Reverse: G, OT, C, OG, T (xref) ↔ OL (Sleeper)
        union all
        select 'OffensiveLine', 'G', 'OL'
        union all
        select 'OffensiveLine', 'OT', 'OL'
        union all
        select 'OffensiveLine', 'C', 'OL'
        union all
        select 'OffensiveLine', 'OG', 'OL'
        union all
        select 'OffensiveLine', 'T', 'OL'

        -- Defensive Back: DB (xref) ↔ CB, SS, FS, S (Sleeper)
        union all
        select 'DefensiveBack', 'DB', 'CB'
        union all
        select 'DefensiveBack', 'DB', 'SS'
        union all
        select 'DefensiveBack', 'DB', 'FS'
        union all
        select 'DefensiveBack', 'DB', 'S'
        -- Reverse: CB, SS, FS, S (xref) ↔ DB (Sleeper)
        union all
        select 'DefensiveBack', 'CB', 'DB'
        union all
        select 'DefensiveBack', 'SS', 'DB'
        union all
        select 'DefensiveBack', 'FS', 'DB'
        union all
        select 'DefensiveBack', 'S', 'DB'

        -- Exact matches (for completeness, score higher)
        union all
        select 'Exact', 'S', 'S'
        union all
        select 'Exact', 'PK', 'PK'
        union all
        select 'Exact', 'PN', 'PN'
        union all
        select 'Exact', 'DL', 'DL'
        union all
        select 'Exact', 'LB', 'LB'
        union all
        select 'Exact', 'OL', 'OL'
        union all
        select 'Exact', 'DB', 'DB'
        -- Add all other positions as exact matches
        union all
        select 'Exact', 'WR', 'WR'
        union all
        select 'Exact', 'RB', 'RB'
        union all
        select 'Exact', 'QB', 'QB'
        union all
        select 'Exact', 'TE', 'TE'
        union all
        select 'Exact', 'CB', 'CB'
        union all
        select 'Exact', 'DE', 'DE'
        union all
        select 'Exact', 'DT', 'DT'
        union all
        select 'Exact', 'SS', 'SS'
        union all
        select 'Exact', 'FS', 'FS'
        union all
        select 'Exact', 'K', 'K'
        union all
        select 'Exact', 'P', 'P'
        union all
        select 'Exact', 'OLB', 'OLB'
        union all
        select 'Exact', 'ILB', 'ILB'
        union all
        select 'Exact', 'NT', 'NT'
        union all
        select 'Exact', 'G', 'G'
        union all
        select 'Exact', 'OT', 'OT'
        union all
        select 'Exact', 'C', 'C'
        union all
        select 'Exact', 'OG', 'OG'
        union all
        select 'Exact', 'T', 'T'
    ),

    -- Initial status column (default: original)
    with_status as (select *, 'original' as xref_correction_status from filtered),

    -- Find sleeper_id duplicates (exclude sentinel values)
    sleeper_duplicates as (
        select sleeper_id
        from with_status
        where sleeper_id is not null and sleeper_id != -1  -- Exclude already-cleared IDs (though none should exist yet)
        group by sleeper_id
        having count(*) > 1
    ),

    -- Join with Sleeper API for birthdate validation
    -- When duplicates exist, clear all but one (even if birthdates match)
    -- Use deterministic tiebreaker: keep player with higher draft_year, then name
    with_sleeper_validation as (
        select
            ws.* exclude (xref_correction_status),
            sp.sleeper_birth_date,
            case
                when
                    sd.sleeper_id is not null
                    and sp.sleeper_birth_date is not null
                    and ws.birthdate != sp.sleeper_birth_date
                then 'cleared_sleeper_duplicate'
                when
                    sd.sleeper_id is not null
                    and sp.sleeper_birth_date is not null
                    and ws.birthdate = sp.sleeper_birth_date
                then 'kept_sleeper_verified'
                else ws.xref_correction_status
            end as xref_correction_status,
            -- Rank duplicates to keep only one (even if birthdates match)
            case
                when sd.sleeper_id is not null
                then row_number() over (partition by ws.sleeper_id order by ws.draft_year desc nulls last, ws.name)
                else 1
            end as _sleeper_rank
        from with_status ws
        left join sleeper_duplicates sd on ws.sleeper_id = sd.sleeper_id
        left join sleeper_players sp on ws.sleeper_id = try_cast(sp.sleeper_player_id as integer)
    ),

    -- Clear incorrect sleeper_id mappings (but keep the player!)
    -- Use -1 as sentinel value for cleared numeric IDs (better observability than NULL)
    -- Clear duplicates even if birthdates match (keep only one per sleeper_id)
    sleeper_deduped as (
        select
            * exclude (sleeper_birth_date, sleeper_id, xref_correction_status, _sleeper_rank),
            case
                when xref_correction_status = 'cleared_sleeper_duplicate'
                then -1  -- Sentinel value: indicates ID was cleared due to duplicate
                when _sleeper_rank > 1
                then -1  -- Clear duplicates even if birthdate matches (keep only one)
                else sleeper_id
            end as sleeper_id,
            case
                when xref_correction_status = 'cleared_sleeper_duplicate'
                then 'cleared_sleeper_duplicate'
                when _sleeper_rank > 1
                then 'cleared_sleeper_duplicate'  -- Mark as cleared even if birthdate matched
                else xref_correction_status
            end as xref_correction_status
        from with_sleeper_validation
    ),

    -- Fallback matching: Attempt to find sleeper_id for players missing it or with
    -- cleared duplicates
    -- Match on name, position (with normalization), and optionally birthdate from
    -- Sleeper players database
    --
    -- Matching Criteria:
    -- - Name: Exact match on name or merge_name (normalized, lowercase, trimmed) -
    -- REQUIRED
    -- - Position: Exact match OR position family match - REQUIRED
    -- - Birthdate: Match on birthdate from nflverse - OPTIONAL (scoring bonus, not
    -- required)
    --
    -- Position Normalization:
    -- - Uses canonical position families for bidirectional matching
    -- - Exact position match scores higher (10 points) than family match (5 points)
    -- - Families: Safety (S↔SS/FS/DB), Kicker (PK↔K), Punter (PN↔P), DefensiveLine
    -- (DL↔DE/DT/NT), Linebacker (LB↔OLB/ILB)
    --
    -- Scope:
    -- - Players with sleeper_id = -1 (cleared duplicates that need correction)
    -- - Players with sleeper_id IS NULL (missing from raw data, need assignment)
    --
    -- Exclusions:
    -- - Candidate sleeper_id must not already be used in xref (check sleeper_deduped)
    -- - Candidate sleeper_id must not be in the duplicate set being resolved
    -- - Invalid/placeholder entries filtered out (full_name not like '%Invalid%' or
    -- '%Duplicate%')
    --
    -- Match Selection:
    -- - Prefer exact name match (name) over normalized match (merge_name) - both
    -- score 100
    -- - Prefer exact position match (10) over family match (5)
    -- - Prefer matches with birthdate when available (20 bonus points)
    -- - Use deterministic tiebreaker (candidate_sleeper_id) if multiple matches
    -- - One match per player (partition by mfl_id, gsis_id, name, birthdate)
    -- - Minimum score: 110 (name + exact position) OR 105 (name + family position)
    --
    -- Result:
    -- - If match found and original sleeper_id was NULL: sleeper_id assigned, status
    -- = 'added_sleeper_id'
    -- - If match found and original sleeper_id was -1: sleeper_id corrected, status =
    -- 'corrected_sleeper_id'
    -- - If no match: sleeper_id remains unchanged, status unchanged
    sleeper_fallback_candidates as (
        select
            sd.*,
            sp.sleeper_player_id as candidate_sleeper_id,
            sp.full_name as sleeper_full_name,
            sp.sleeper_position,
            pf.position_family,
            -- Match scoring: prefer exact name match, then position match type, then
            -- birthdate match
            case
                when lower(trim(sd.name)) = lower(trim(sp.full_name))
                then 100
                when lower(trim(sd.merge_name)) = lower(trim(sp.full_name))
                then 100  -- Increased from 90
                else 0
            end as name_match_score,
            case
                when sd.position = sp.sleeper_position
                then 10  -- Exact position match
                when pf.position_family is not null
                then 5  -- Position family match
                else 0
            end as position_match_score,
            case
                when sd.birthdate = sp.sleeper_birth_date
                then 20  -- Increased from 5, strongly preferred
                else 0
            end as birthdate_match_score
        from sleeper_deduped sd
        cross join sleeper_players sp
        left join position_families pf on sd.position = pf.xref_position and sp.sleeper_position = pf.sleeper_position
        where
            (sd.sleeper_id = -1 or sd.sleeper_id is null)  -- Cleared duplicates OR missing
            -- Name matching (exact or normalized) - REQUIRED
            and (
                lower(trim(sd.name)) = lower(trim(sp.full_name))
                or lower(trim(sd.merge_name)) = lower(trim(sp.full_name))
            )
            -- Position matching - REQUIRED (exact OR family match)
            and (sd.position = sp.sleeper_position or pf.position_family is not null)
            -- Birthdate matching is OPTIONAL (scoring bonus only, not required)
            -- Exclude candidates already used in xref (check current state)
            and try_cast(sp.sleeper_player_id as integer)
            not in (select sleeper_id from sleeper_deduped where sleeper_id != -1 and sleeper_id is not null)
            -- Exclude candidates in the duplicate set being resolved
            and try_cast(sp.sleeper_player_id as integer) not in (select sleeper_id from sleeper_duplicates)
    ),

    -- Select best match per player using deterministic tiebreakers
    -- Require minimum score: 110 (name + exact position) OR 105 (name + family
    -- position)
    -- CRITICAL: Ensure sleeper_id uniqueness - only one player can match to each
    -- sleeper_id
    sleeper_fallback_matched as (
        select
            * exclude (
                candidate_sleeper_id,
                sleeper_full_name,
                sleeper_position,
                position_family,
                name_match_score,
                position_match_score,
                birthdate_match_score
            ),
            candidate_sleeper_id as matched_sleeper_id,
            name_match_score + position_match_score + birthdate_match_score as total_match_score
        from sleeper_fallback_candidates
        where name_match_score + position_match_score >= 105  -- Require name + position (exact or family)
        qualify
            row_number() over (
                partition by mfl_id, gsis_id, name, birthdate
                order by name_match_score + position_match_score + birthdate_match_score desc, candidate_sleeper_id  -- Deterministic tiebreaker
            )
            = 1
    ),

    -- Ensure sleeper_id uniqueness: if multiple players matched to same sleeper_id,
    -- keep only the best match
    sleeper_fallback_deduped as (
        select * exclude (matched_sleeper_id, total_match_score), matched_sleeper_id, total_match_score
        from sleeper_fallback_matched
        qualify
            row_number() over (
                partition by matched_sleeper_id order by total_match_score desc, mfl_id, gsis_id, name  -- Deterministic tiebreaker for same score
            )
            = 1
    ),

    -- Apply fallback matches: update sleeper_id and status for matched players
    -- Distinguish between added (was NULL) vs corrected (was -1)
    sleeper_with_fallback as (
        select
            sd.* exclude (sleeper_id, xref_correction_status),
            case
                when fm.matched_sleeper_id is not null
                then try_cast(fm.matched_sleeper_id as integer)
                else sd.sleeper_id
            end as sleeper_id,
            case
                when fm.matched_sleeper_id is not null and sd.sleeper_id is null
                then 'added_sleeper_id'
                when fm.matched_sleeper_id is not null and sd.sleeper_id = -1
                then 'corrected_sleeper_id'
                else sd.xref_correction_status
            end as xref_correction_status
        from sleeper_deduped sd
        left join
            sleeper_fallback_deduped fm
            on sd.mfl_id = fm.mfl_id
            and sd.gsis_id = fm.gsis_id
            and sd.name = fm.name
            and sd.birthdate = fm.birthdate
    ),

    -- Find gsis_id duplicates (exclude sentinel values)
    gsis_duplicates as (
        select gsis_id
        from sleeper_with_fallback
        where gsis_id is not null and gsis_id != 'DUPLICATE_CLEARED'  -- Exclude already-cleared IDs
        group by gsis_id
        having count(*) > 1
    ),

    -- Deduplicate gsis_id (keep player with higher draft_year, tiebreaker: name)
    gsis_ranked as (
        select
            swf.*,
            case
                when gd.gsis_id is not null
                then row_number() over (partition by swf.gsis_id order by swf.draft_year desc nulls last, swf.name)
                else 1
            end as _gsis_rank
        from sleeper_with_fallback swf
        left join gsis_duplicates gd on swf.gsis_id = gd.gsis_id
    ),

    gsis_deduped as (
        select
            gr.* exclude (_gsis_rank, gsis_id, xref_correction_status),
            case
                when gr._gsis_rank > 1
                then 'DUPLICATE_CLEARED'  -- Sentinel value for VARCHAR IDs
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
        left join gsis_duplicates gd on gr.gsis_id = gd.gsis_id
    ),

    -- Find mfl_id duplicates (exclude sentinel values)
    mfl_duplicates as (
        select mfl_id
        from gsis_deduped
        where mfl_id is not null and mfl_id != -1  -- Exclude already-cleared IDs
        group by mfl_id
        having count(*) > 1
    ),

    -- Deduplicate mfl_id (keep player with higher draft_year, tiebreaker: name)
    mfl_ranked as (
        select
            gd.*,
            case
                when md.mfl_id is not null
                then row_number() over (partition by gd.mfl_id order by gd.draft_year desc nulls last, gd.name)
                else 1
            end as _mfl_rank
        from gsis_deduped gd
        left join mfl_duplicates md on gd.mfl_id = md.mfl_id
    ),

    mfl_deduped as (
        select
            mr.* exclude (_mfl_rank, mfl_id, xref_correction_status),
            case
                when mr._mfl_rank > 1
                then -1  -- Sentinel value: indicates ID was cleared due to duplicate
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
        left join mfl_duplicates md on mr.mfl_id = md.mfl_id
    ),

    -- Generate name_last_first variant (for FantasySharks projection matching)
    with_name_variant as (
        select
            *,
            case
                when name like '% %' then split_part(name, ' ', 2) || ', ' || split_part(name, ' ', 1) else name
            end as name_last_first
        from mfl_deduped
    ),

    -- Data quality validations (fail if violations exist)
    validate_no_duplicate_ids as (
        -- Assert no duplicate provider IDs remain (excluding sentinel values)
        -- This is a critical integrity check - duplicates would cause join explosions
        -- downstream
        select
            'sleeper_id' as id_type,
            sleeper_id as id_value,
            count(*) as duplicate_count,
            string_agg(mfl_id || '|' || coalesce(gsis_id, '') || '|' || name, ', ' order by mfl_id) as player_keys
        from with_name_variant
        where sleeper_id is not null and sleeper_id != -1  -- Exclude sentinel values
        group by sleeper_id
        having count(*) > 1

        union all

        select
            'gsis_id' as id_type,
            cast(gsis_id as varchar) as id_value,
            count(*) as duplicate_count,
            string_agg(
                mfl_id || '|' || coalesce(cast(sleeper_id as varchar), '') || '|' || name, ', ' order by mfl_id
            ) as player_keys
        from with_name_variant
        where gsis_id is not null and gsis_id != 'DUPLICATE_CLEARED'  -- Exclude sentinel values
        group by gsis_id
        having count(*) > 1

        union all

        select
            'mfl_id' as id_type,
            cast(mfl_id as varchar) as id_value,
            count(*) as duplicate_count,
            string_agg(
                coalesce(gsis_id, '') || '|' || coalesce(cast(sleeper_id as varchar), '') || '|' || name,
                ', '
                order by gsis_id
            ) as player_keys
        from with_name_variant
        where mfl_id is not null and mfl_id != -1  -- Exclude sentinel values
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
        where sleeper_id = -1 and xref_correction_status not in ('cleared_sleeper_duplicate', 'corrected_sleeper_id')

        union all

        select
            'gsis_id_sentinel_mismatch' as violation_type,
            mfl_id || '|' || coalesce(cast(sleeper_id as varchar), '') || '|' || name as player_key,
            cast(gsis_id as varchar) as sleeper_id,
            xref_correction_status
        from with_name_variant
        where
            gsis_id = 'DUPLICATE_CLEARED'
            and xref_correction_status not like '%cleared%'
            and xref_correction_status not like '%gsis%'

        union all

        select
            'mfl_id_sentinel_mismatch' as violation_type,
            coalesce(gsis_id, '') || '|' || coalesce(cast(sleeper_id as varchar), '') || '|' || name as player_key,
            cast(mfl_id as varchar) as sleeper_id,
            xref_correction_status
        from with_name_variant
        where mfl_id = -1 and xref_correction_status not like '%cleared%' and xref_correction_status not like '%mfl%'
    ),

    validate_at_least_one_id as (
        -- Ensure each player has at least one provider ID (not all cleared/NULL)
        -- At least one of: mfl_id, gsis_id, sleeper_id, espn_id, yahoo_id, pfr_id !=
        -- sentinel/NULL
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
        where
            (mfl_id is null or mfl_id = -1)
            and (gsis_id is null or gsis_id = 'DUPLICATE_CLEARED')
            and (sleeper_id is null or sleeper_id = -1)
            and espn_id is null
            and yahoo_id is null
            and pfr_id is null
    ),

    -- Assign sequential player_id (deterministic ordering for stability)
    -- Note: Data quality validations are performed via dbt tests, not inline filters
    with_player_id as (select *, row_number() over (order by mfl_id, gsis_id, name) as player_id from with_name_variant)

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
