{{ config(materialized="view") }}

/*
Stage Commissioner TRANSACTIONS sheet with dimension joins and validation flags.

Source: data/raw/commissioner/transactions/ (parse_transactions output)
Output grain: one row per transaction event per asset
Joins: dim_timeframe, dim_franchise (SCD Type 2 temporal), dim_player_id_xref

Key Transformations:
- Map timeframe_string → transaction_date
- Map owner_name → franchise_id (temporal join on season)
- Add player_key composite identifier (prevents grain violations from unmapped players)
- Calculate contract validation flags
- Cast split_array to JSON text for DuckDB compatibility

Contract Validation Notes:
- Extensions intentionally have len(split_array) > contract_years
- This is league accounting: Contract=extension only, Split=full remaining schedule
- See docs/analysis/TRANSACTIONS_contract_validation_analysis.md
*/
with
    latest_partition as (
        -- Get the most recent partition date to avoid reading duplicate snapshots
        select max(dt) as latest_dt
        from
            read_parquet(
                '{{ var("external_root", "data/raw") }}/commissioner/transactions/dt=*/*.parquet',
                hive_partitioning = true
            )
    ),

    base as (
        select
            -- Primary keys
            transaction_id_unique,
            transaction_id,

            -- Transaction classification
            transaction_type_refined,
            asset_type,

            -- Time/context
            "Time Frame" as timeframe_string,
            season,
            period_type,
            week,
            sort_sequence,

            -- Parties (owner names → will join to franchise_id)
            "From" as from_owner_name,
            "To" as to_owner_name,

            -- Pick attributes
            "Original Order" as pick_original_owner,
            "Round" as round,
            "Pick" as pick_number,

            -- Asset identifiers
            "Position" as position,
            "Player" as player_name,
            player_id,  -- mfl_id from crosswalk (-1 if unmapped, null if not player)

            -- Pick identifiers (raw from sheet - will be canonicalized via xref)
            pick_id,  -- Raw combined format (backward compat)
            pick_season,
            pick_round,
            pick_overall_number,
            pick_id_raw,

            -- Contract fields (raw)
            "Contract" as contract_raw,
            "Split" as split_raw,
            total as contract_total,
            years as contract_years,
            split_array,

            -- Special fields
            "RFA Matched" as rfa_matched_raw,
            "FAAD Comp" as faad_comp_raw,
            faad_award_sequence,  -- v2: Immutable FAAD sequence (persisted at ingestion)
            "Type" as transaction_type_raw

        from
            read_parquet(
                '{{ var("external_root", "data/raw") }}/commissioner/transactions/dt=*/*.parquet',
                hive_partitioning = true
            )
        cross join latest_partition
        where dt = latest_partition.latest_dt
    ),

    draft_boundaries as (
        -- Identify rookie draft transaction ID ranges for each season
        -- Needed to distinguish early vs late offseason periods
        select
            season,
            min(transaction_id) as draft_start_id,
            max(transaction_id) as draft_end_id
        from
            read_parquet(
                '{{ var("external_root", "data/raw") }}/commissioner/transactions/dt=*/*.parquet',
                hive_partitioning = true
            )
        cross join
            lateral(
                select max(dt) as latest_dt
                from
                    read_parquet(
                        '{{ var("external_root", "data/raw") }}/commissioner/transactions/dt=*/*.parquet',
                        hive_partitioning = true
                    )
            ) lp
        where dt = lp.latest_dt and period_type = 'rookie_draft'
        group by season
    ),

    with_timeframe as (
        -- Join to dim_timeframe to get transaction_date
        select
            base.*,
            tf.timeframe_string as timeframe_canonical,
            next_draft.draft_start_id as next_draft_start_id,
            next_draft.draft_end_id as next_draft_end_id,

            -- Derive transaction_date from timeframe
            -- Offseason has TWO phases that share the same label (e.g., "2022
            -- Offseason"):
            -- 1. Early Offseason: After season ends, BEFORE next year's draft → March
            -- (season+1)
            -- 2. Late Offseason: AFTER next year's draft, BEFORE FAAD → August
            -- (season+1)
            -- We distinguish them by transaction_id relative to next season's draft
            -- boundaries
            --
            -- Chronological order for August events:
            -- Aug 1:  Rookie Draft
            -- Aug 10: Late Offseason (post-draft signings/cuts)
            -- Aug 15: FAAD (Free Agent Auction Draft)
            case
                when base.period_type = 'rookie_draft'
                then make_date(base.season, 8, 1)  -- Aug 1 (rookie draft)
                when
                    base.period_type = 'offseason'
                    and base.transaction_id
                    < coalesce(next_draft.draft_start_id, 999999)
                then make_date(base.season + 1, 3, 1)  -- Early offseason: Mar 1 (free agency)
                when
                    base.period_type = 'offseason'
                    and base.transaction_id > coalesce(next_draft.draft_end_id, 0)
                then make_date(base.season + 1, 8, 10)  -- Late offseason: Aug 10 (post-draft, pre-FAAD)
                when base.period_type = 'faad'
                then make_date(base.season, 8, 15)  -- Aug 15 (FAAD)
                when base.period_type = 'preseason'
                then date_trunc('week', make_date(base.season, 9, 1))  -- Sep 1 (preseason)
                when
                    base.period_type in ('regular', 'deadline')
                    and base.week is not null
                -- Regular season: week-based calculation
                -- NFL regular season typically starts first Thursday after Labor Day
                -- (early Sep)
                then
                    date_trunc('week', make_date(base.season, 9, 7))
                    + interval (base.week - 1) week
                else make_date(base.season, 1, 1)  -- Fallback: Jan 1
            end as transaction_date

        from base
        left join
            {{ ref("dim_timeframe") }} tf on base.timeframe_string = tf.timeframe_string
        left join draft_boundaries next_draft on base.season + 1 = next_draft.season  -- Join to NEXT season's draft
    ),

    with_franchises as (
        -- Join to dim_franchise (SCD Type 2 temporal join on season)
        -- Offseason transactions occur in calendar year season+1, so we need to adjust
        -- the season lookup for franchise ownership (e.g., "2024 Offseason" → season
        -- 2025)
        select
            wtf.*,

            -- From franchise (null for waiver wire sources)
            from_fran.franchise_id as from_franchise_id,
            from_fran.franchise_name as from_franchise_name,

            -- To franchise (null for waiver wire destinations)
            to_fran.franchise_id as to_franchise_id,
            to_fran.franchise_name as to_franchise_name

        from with_timeframe wtf

        -- Left join for "From" owner (handles Waiver Wire as null)
        left join
            {{ ref("dim_franchise") }} from_fran
            on wtf.from_owner_name = from_fran.owner_name
            and case
                when wtf.period_type = 'offseason' then wtf.season + 1 else wtf.season
            end
            between from_fran.season_start and from_fran.season_end

        -- Left join for "To" owner (handles Waiver Wire as null)
        left join
            {{ ref("dim_franchise") }} to_fran
            on wtf.to_owner_name = to_fran.owner_name
            and case
                when wtf.period_type = 'offseason' then wtf.season + 1 else wtf.season
            end
            between to_fran.season_start and to_fran.season_end
    ),

    with_player_key as (
        -- Add player_key composite identifier
        -- Pattern: same as stg_nflverse__player_stats to prevent grain violations
        -- from unmapped players
        select
            wf.*,

            -- Player key logic:
            -- - Mapped players: player_key = cast(player_id as varchar)
            -- - Unmapped players: player_key = player_name (preserves identity via
            -- raw name)
            -- - Non-players: player_key = transaction_id_unique (defensive fail-safe
            -- for picks/cap)
            case
                when wf.asset_type = 'player' and coalesce(wf.player_id, -1) != -1
                then cast(wf.player_id as varchar)
                when wf.asset_type = 'player' and coalesce(wf.player_id, -1) = -1
                then coalesce(wf.player_name, 'UNKNOWN_' || wf.transaction_id_unique)
                when wf.asset_type = 'pick'
                then coalesce(wf.pick_id, 'PICK_' || wf.transaction_id_unique)
                when wf.asset_type = 'defense'
                then coalesce(wf.player_name, 'DEFENSE_' || wf.transaction_id_unique)
                when wf.asset_type = 'cap_space'
                then 'CAP_' || wf.transaction_id_unique
                else 'UNKNOWN_' || wf.transaction_id_unique
            end as player_key

        from with_franchises wf
    ),

    final as (
        -- Calculate validation flags and finalize
        select
            -- Primary keys
            transaction_id_unique,
            transaction_id,
            player_key,  -- Composite identifier for grain enforcement

            -- Transaction classification
            transaction_type_refined as transaction_type,
            asset_type,

            -- Time dimension
            transaction_date,
            extract(year from transaction_date) as transaction_year,
            season,
            period_type,
            week,
            sort_sequence,
            timeframe_string,

            -- Franchise dimensions (role-playing)
            from_franchise_id,
            from_franchise_name,
            to_franchise_id,
            to_franchise_name,

            -- Asset dimensions
            player_id,
            player_name,
            position,

            -- Pick identifiers (raw from parser, will be canonicalized via xref)
            pick_id,  -- Raw combined format (backward compat)
            pick_season,
            pick_round,
            pick_overall_number,
            pick_id_raw,
            pick_original_owner,
            round,
            pick_number,

            -- Contract measures
            contract_total,
            contract_years,

            -- Contract split as JSON text for DuckDB
            -- DuckDB supports json_extract, list functions on JSON text
            case
                when split_array is not null then cast(split_array as json) else null
            end as contract_split_json,

            -- Keep array for validation in staging
            split_array as contract_split_array,

            -- Contract validation flags
            case
                when contract_years is not null and split_array is not null
                then len(split_array) != contract_years
                else false
            end as has_contract_length_mismatch,

            case
                when contract_total is not null and split_array is not null
                then list_sum(split_array) != contract_total
                else false
            end as has_contract_sum_mismatch,

            -- Validation notes
            case
                when
                    transaction_type = 'contract_extension'
                    and contract_years is not null
                    and split_array is not null
                    and len(split_array) > contract_years
                then
                    'Extension shows full remaining schedule (expected per league accounting)'
                when
                    contract_total is not null
                    and split_array is not null
                    and abs(list_sum(split_array) - contract_total) > 5
                then 'Large sum mismatch (>$5) - review with commissioner'
                when
                    contract_total is not null
                    and split_array is not null
                    and list_sum(split_array) != contract_total
                then 'Minor rounding variance (±$1-2)'
                else null
            end as validation_notes,

            -- Special transaction fields
            case
                when rfa_matched_raw = 'yes'
                then true
                when rfa_matched_raw = '-' or rfa_matched_raw is null
                then false
                else null
            end as rfa_matched,

            -- FAAD compensation: try to cast to integer, null if non-numeric (e.g.,
            -- "2nd to Piper")
            try_cast(nullif(faad_comp_raw, '-') as integer) as faad_compensation,

            -- Keep raw value for non-numeric compensation (draft picks, etc.)
            case
                when faad_comp_raw != '-' and try_cast(faad_comp_raw as integer) is null
                then faad_comp_raw
                else null
            end as faad_compensation_text,

            -- Raw fields for reference
            contract_raw,
            split_raw,
            transaction_type_raw,
            from_owner_name,
            to_owner_name

        from with_player_key
    )

select *
from final
