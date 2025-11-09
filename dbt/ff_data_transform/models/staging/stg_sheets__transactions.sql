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
    raw_transactions as (
        select *
        from
            read_parquet(
                '{{ var("external_root", "data/raw") }}/commissioner/transactions/dt=*/*.parquet',
                hive_partitioning = true,
                union_by_name = true
            ) as raw(
                transaction_id_unique,
                transaction_id,
                transaction_type_refined,
                asset_type,
                timeframe_string,
                season,
                period_type,
                week,
                sort_sequence,
                from_owner_name,
                to_owner_name,
                pick_original_owner,
                round,
                pick_number,
                position,
                player_name,
                player_id,
                pick_id,
                pick_season,
                pick_round,
                pick_overall_number,
                pick_id_raw,
                contract_raw,
                split_raw,
                contract_total,
                contract_years,
                split_array,
                rfa_matched_raw,
                faad_comp_raw,
                faad_award_sequence,
                transaction_type_raw,
                dt
            )
    ),

    latest_partition as (
        -- Get the most recent partition date to avoid reading duplicate snapshots
        select max(dt) as latest_dt from raw_transactions
    ),

    base as (
        select
            -- Primary keys
            rt.transaction_id_unique,
            rt.transaction_id,

            -- Transaction classification
            rt.transaction_type_refined,
            rt.asset_type,

            -- Time/context
            rt.timeframe_string as timeframe_string,
            rt.season,
            rt.period_type,
            rt.week,
            rt.sort_sequence,

            -- Parties (owner names → will join to franchise_id)
            rt.from_owner_name as from_owner_name,
            rt.to_owner_name as to_owner_name,

            -- Pick attributes
            rt.pick_original_owner as pick_original_owner,
            rt.round as round,
            rt.pick_number as pick_number,

            -- Asset identifiers
            rt.position as position,
            rt.player_name as player_name,
            rt.player_id,  -- mfl_id from crosswalk (-1 if unmapped, null if not player)

            -- Pick identifiers (raw from sheet - will be canonicalized via xref)
            rt.pick_id,  -- Raw combined format (backward compat)
            rt.pick_season,
            rt.pick_round,
            rt.pick_overall_number,
            rt.pick_id_raw,

            -- Contract fields (raw)
            rt.contract_raw as contract_raw,
            rt.split_raw as split_raw,
            rt.contract_total as contract_total,
            rt.contract_years as contract_years,
            rt.split_array,

            -- Special fields
            rt.rfa_matched_raw as rfa_matched_raw,
            rt.faad_comp_raw as faad_comp_raw,
            -- v2: Immutable FAAD sequence (persisted at ingestion)
            rt.faad_award_sequence,
            rt.transaction_type_raw as transaction_type_raw

        from raw_transactions rt
        cross join latest_partition lp
        where rt.dt = lp.latest_dt
    ),

    draft_boundaries as (
        -- Identify rookie draft transaction ID ranges for each season
        -- Needed to distinguish early vs late offseason periods
        select
            rt.season as draft_season, min(rt.transaction_id) as draft_start_id, max(rt.transaction_id) as draft_end_id
        from raw_transactions rt
        cross join latest_partition lp
        where rt.dt = lp.latest_dt and rt.period_type = 'rookie_draft'
        group by rt.season
    ),

    with_timeframe as (
        -- Calculate transaction_date and join draft boundaries
        select
            -- All columns from base (explicit aliases to avoid sqlglot parser
            -- ambiguity with joined tables)
            base.transaction_id_unique as transaction_id_unique,
            base.transaction_id as transaction_id,
            base.transaction_type_refined as transaction_type_refined,
            base.asset_type as asset_type,
            base.timeframe_string as timeframe_string,
            base.season as season,
            base.period_type as period_type,
            base.week as week,
            base.sort_sequence as sort_sequence,
            base.from_owner_name as from_owner_name,
            base.to_owner_name as to_owner_name,
            base.pick_original_owner as pick_original_owner,
            base.round as round,
            base.pick_number as pick_number,
            base.position as position,
            base.player_name as player_name,
            base.player_id as player_id,
            base.pick_id as pick_id,
            base.pick_season as pick_season,
            base.pick_round as pick_round,
            base.pick_overall_number as pick_overall_number,
            base.pick_id_raw as pick_id_raw,
            base.contract_raw as contract_raw,
            base.split_raw as split_raw,
            base.contract_total as contract_total,
            base.contract_years as contract_years,
            base.split_array as split_array,
            base.rfa_matched_raw as rfa_matched_raw,
            base.faad_comp_raw as faad_comp_raw,
            base.faad_award_sequence as faad_award_sequence,
            base.transaction_type_raw as transaction_type_raw,

            -- Additional columns from joins/aliases
            base.timeframe_string as timeframe_canonical,
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
                    base.period_type = 'offseason' and base.transaction_id < coalesce(next_draft.draft_start_id, 999999)
                then make_date(base.season + 1, 3, 1)  -- Early offseason: Mar 1 (free agency)
                when base.period_type = 'offseason' and base.transaction_id > coalesce(next_draft.draft_end_id, 0)
                then make_date(base.season + 1, 8, 10)  -- Late offseason: Aug 10 (post-draft, pre-FAAD)
                when base.period_type = 'faad'
                then make_date(base.season, 8, 15)  -- Aug 15 (FAAD)
                when base.period_type = 'preseason'
                then date_trunc('week', make_date(base.season, 9, 1))  -- Sep 1 (preseason)
                when base.period_type in ('regular', 'deadline') and base.week is not null
                -- Regular season: week-based calculation
                -- NFL regular season typically starts first Thursday after Labor Day
                -- (early Sep)
                then date_trunc('week', make_date(base.season, 9, 7)) + interval (base.week - 1) week
                else make_date(base.season, 1, 1)  -- Fallback: Jan 1
            end as transaction_date

        from base
        left join draft_boundaries next_draft on base.season + 1 = next_draft.draft_season  -- Join to NEXT season's draft
    ),

    final as (
        select
            wtf.transaction_id_unique as transaction_id_unique,
            wtf.transaction_id as transaction_id,
            case
                when wtf.asset_type = 'player' and coalesce(wtf.player_id, -1) != -1
                then cast(wtf.player_id as varchar)
                when wtf.asset_type = 'player' and coalesce(wtf.player_id, -1) = -1
                then coalesce(wtf.player_name, 'UNKNOWN_' || wtf.transaction_id_unique)
                when wtf.asset_type = 'pick'
                then coalesce(wtf.pick_id, 'PICK_' || wtf.transaction_id_unique)
                when wtf.asset_type = 'defense'
                then coalesce(wtf.player_name, 'DEFENSE_' || wtf.transaction_id_unique)
                when wtf.asset_type = 'cap_space'
                then 'CAP_' || wtf.transaction_id_unique
                else 'UNKNOWN_' || wtf.transaction_id_unique
            end as player_key,
            wtf.transaction_type_refined as transaction_type,
            wtf.asset_type as asset_type,
            wtf.transaction_date as transaction_date,
            extract(year from wtf.transaction_date) as transaction_year,
            wtf.season as season,
            wtf.period_type as period_type,
            wtf.week as week,
            wtf.sort_sequence as sort_sequence,
            wtf.timeframe_string as timeframe_string,
            from_fran.franchise_id as from_franchise_id,
            from_fran.franchise_name as from_franchise_name,
            to_fran.franchise_id as to_franchise_id,
            to_fran.franchise_name as to_franchise_name,
            wtf.player_id as player_id,
            wtf.player_name as player_name,
            wtf.position as position,
            wtf.pick_id as pick_id,
            wtf.pick_season as pick_season,
            wtf.pick_round as pick_round,
            wtf.pick_overall_number as pick_overall_number,
            wtf.pick_id_raw as pick_id_raw,
            wtf.pick_original_owner as pick_original_owner,
            wtf.round as round,
            wtf.pick_number as pick_number,
            wtf.contract_total as contract_total,
            wtf.contract_years as contract_years,
            case
                when wtf.split_array is not null then cast(wtf.split_array as json) else null
            end as contract_split_json,
            wtf.split_array as contract_split_array,
            case
                when wtf.contract_years is not null and wtf.split_array is not null
                then len(wtf.split_array) != wtf.contract_years
                else false
            end as has_contract_length_mismatch,
            case
                when wtf.contract_total is not null and wtf.split_array is not null
                then list_sum(wtf.split_array) != wtf.contract_total
                else false
            end as has_contract_sum_mismatch,
            case
                when
                    wtf.transaction_type_refined = 'contract_extension'
                    and wtf.contract_years is not null
                    and wtf.split_array is not null
                    and len(wtf.split_array) > wtf.contract_years
                then 'Extension shows full remaining schedule (expected per league accounting)'
                when
                    wtf.contract_total is not null
                    and wtf.split_array is not null
                    and abs(list_sum(wtf.split_array) - wtf.contract_total) > 5
                then 'Large sum mismatch (>$5) - review with commissioner'
                when
                    wtf.contract_total is not null
                    and wtf.split_array is not null
                    and list_sum(wtf.split_array) != wtf.contract_total
                then 'Minor rounding variance (±$1-2)'
                else null
            end as validation_notes,
            case
                when wtf.rfa_matched_raw = 'yes'
                then true
                when wtf.rfa_matched_raw = '-' or wtf.rfa_matched_raw is null
                then false
                else null
            end as rfa_matched,
            try_cast(nullif(wtf.faad_comp_raw, '-') as integer) as faad_compensation,
            case
                when wtf.faad_comp_raw != '-' and try_cast(wtf.faad_comp_raw as integer) is null
                then wtf.faad_comp_raw
                else null
            end as faad_compensation_text,
            wtf.contract_raw as contract_raw,
            wtf.split_raw as split_raw,
            wtf.transaction_type_raw as transaction_type_raw,
            wtf.from_owner_name as from_owner_name,
            wtf.to_owner_name as to_owner_name,
            wtf.faad_award_sequence as faad_award_sequence
        from with_timeframe wtf
        left join
            {{ ref("dim_franchise") }} from_fran
            on wtf.from_owner_name = from_fran.owner_name
            and case when wtf.period_type = 'offseason' then wtf.season + 1 else wtf.season end
            between from_fran.season_start and from_fran.season_end
        left join
            {{ ref("dim_franchise") }} to_fran
            on wtf.to_owner_name = to_fran.owner_name
            and case when wtf.period_type = 'offseason' then wtf.season + 1 else wtf.season end
            between to_fran.season_start and to_fran.season_end
    )

select
    f.transaction_id_unique,
    f.transaction_id,
    f.player_key,
    f.transaction_type,
    f.asset_type,
    f.transaction_date,
    f.transaction_year,
    f.season,
    f.period_type,
    f.week,
    f.sort_sequence,
    f.timeframe_string,
    f.from_franchise_id,
    f.from_franchise_name,
    f.to_franchise_id,
    f.to_franchise_name,
    f.player_id,
    f.player_name,
    f.position,
    f.pick_id,
    f.pick_season,
    f.pick_round,
    f.pick_overall_number,
    f.pick_id_raw,
    f.pick_original_owner,
    f.round,
    f.pick_number,
    f.contract_total,
    f.contract_years,
    f.contract_split_json,
    f.contract_split_array,
    f.has_contract_length_mismatch,
    f.has_contract_sum_mismatch,
    f.validation_notes,
    f.rfa_matched,
    f.faad_compensation,
    f.faad_compensation_text,
    f.contract_raw,
    f.split_raw,
    f.transaction_type_raw,
    f.from_owner_name,
    f.to_owner_name,
    f.faad_award_sequence
from final f
