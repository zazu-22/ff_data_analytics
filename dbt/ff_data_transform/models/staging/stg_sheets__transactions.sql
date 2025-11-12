{{ config(materialized="table", unique_key='transaction_id_unique') }}

/*
Stage Commissioner TRANSACTIONS sheet with dimension joins and validation flags.

Source: data/raw/commissioner/transactions/ (parse_transactions output)
Output grain: one row per transaction event per asset
Joins: dim_timeframe, dim_franchise (SCD Type 2 temporal), dim_player_id_xref

Key Transformations:
- Map timeframe_string → transaction_date
- Map owner_name → franchise_id (temporal join on season)
- Map player_name → player_id via resolve_player_id_from_name macro (position-aware)
- Add player_key composite identifier (prevents grain violations from unmapped players)
- Calculate contract validation flags
- Cast split_array to JSON text for DuckDB compatibility

Player ID Resolution:
- Uses resolve_player_id_from_name macro for consistent disambiguation logic
- Position column provides context (e.g., DL → matches both DE and DT)
- Ensures all sheets staging models use identical player_id resolution

Contract Validation Notes:
- Extensions intentionally have len(split_array) > contract_years
- This is league accounting: Contract=extension only, Split=full remaining schedule
- See docs/analysis/TRANSACTIONS_contract_validation_analysis.md
*/
with
    raw_transactions as (
        select
            transaction_id_unique,
            transaction_id,
            transaction_type_refined,
            asset_type,
            "Time Frame" as timeframe_string,
            season,
            period_type,
            week,
            sort_sequence,
            "From" as from_owner_name,
            "To" as to_owner_name,
            "Original Order" as pick_original_owner,
            "Round" as round,
            "Pick" as pick_number,
            "Position" as position,
            "Player" as player_name,
            pick_id,
            pick_season,
            pick_round,
            pick_overall_number,
            pick_id_raw,
            "Contract" as contract_raw,
            "Split" as split_raw,
            total as contract_total,
            years as contract_years,
            split_array,
            "RFA Matched" as rfa_matched_raw,
            "FAAD Comp" as faad_comp_raw,
            faad_award_sequence,
            "Type" as transaction_type_raw
        from
            read_parquet(
                '{{ var("external_root", "data/raw") }}/commissioner/transactions/dt=*/*.parquet',
                hive_partitioning = true,
                union_by_name = true
            )
        where
            1 = 1
            and {{ snapshot_selection_strategy(
                var("external_root", "data/raw") ~ '/commissioner/transactions/dt=*/*.parquet',
                strategy='latest_only'
            ) }}
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
    ),

    draft_boundaries as (
        -- Identify rookie draft transaction ID ranges for each season
        -- Needed to distinguish early vs late offseason periods
        select
            rt.season as draft_season, min(rt.transaction_id) as draft_start_id, max(rt.transaction_id) as draft_end_id
        from raw_transactions rt
        where rt.period_type = 'rookie_draft'
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

    with_corrections as (
        -- Apply data quality corrections from seed
        -- Currently handles swap_from_to corrections (transactions 2657, 2658)
        select wtf.*, coalesce(corr.correction_type = 'swap_from_to', false) as needs_from_to_swap
        from with_timeframe wtf
        left join
            {{ ref('corrections_stg_sheets__transactions') }} corr
            on wtf.transaction_id = corr.transaction_id
            and corr.correction_type = 'swap_from_to'
        -- For swap corrections, we only need one row per transaction (not per field)
        qualify row_number() over (partition by wtf.transaction_id order by corr.transaction_id nulls last) = 1
    ),

    with_normalized_names as (
        -- Normalize player names for matching
        select
            wc.*,
            replace(
                replace(replace(replace(wc.player_name, ' (RS)', ''), ' Jr.', ''), ' Jr', ''), '.', ''
            ) as player_name_normalized
        from with_corrections wc
    ),

    with_alias as (
        -- Apply name alias corrections
        select wn.*, coalesce(alias.canonical_name, wn.player_name_normalized) as player_name_canonical
        from with_normalized_names wn
        left join {{ ref("dim_name_alias") }} alias on wn.player_name_normalized = alias.alias_name
    ),

    -- Resolve player_id using macro with position context
    {{ resolve_player_id_from_name(
        source_cte='with_alias',
        player_name_col='player_name_canonical',
        position_context_col='position',
        context_type='position'
    ) }},

    with_player_id as (
        -- Merge player_id resolution back with source data
        -- List all columns explicitly to preserve types (esp. split_array BIGINT[])
        select
            wa.transaction_id_unique,
            wa.transaction_id,
            wa.transaction_type_refined,
            wa.asset_type,
            wa.timeframe_string,
            wa.season,
            wa.period_type,
            wa.week,
            wa.sort_sequence,
            wa.from_owner_name,
            wa.to_owner_name,
            wa.pick_original_owner,
            wa.round,
            wa.pick_number,
            wa.position,
            wa.player_name,
            wa.pick_id,
            wa.pick_season,
            wa.pick_round,
            wa.pick_overall_number,
            wa.pick_id_raw,
            wa.contract_raw,
            wa.split_raw,
            wa.contract_total,
            wa.contract_years,
            wa.split_array,
            wa.rfa_matched_raw,
            wa.faad_comp_raw,
            wa.faad_award_sequence,
            wa.transaction_type_raw,
            wa.timeframe_canonical,
            wa.next_draft_start_id,
            wa.next_draft_end_id,
            wa.transaction_date,
            wa.needs_from_to_swap,
            wa.player_name_normalized,
            wa.player_name_canonical,
            pid.player_id,
            pid.mfl_id,
            pid.canonical_name
        from with_alias wa
        left join
            with_player_id_lookup pid
            on wa.player_name_canonical = pid.player_name_canonical
            and wa.position = pid.position
    ),

    final as (
        select
            wp.transaction_id_unique as transaction_id_unique,
            wp.transaction_id as transaction_id,
            case
                when wp.asset_type = 'player' and wp.player_id is not null
                then cast(wp.player_id as varchar)
                when wp.asset_type = 'player' and wp.player_id is null
                then coalesce(cast(wp.player_name as varchar), 'UNKNOWN_' || cast(wp.transaction_id_unique as varchar))
                when wp.asset_type = 'pick'
                then coalesce(cast(wp.pick_id as varchar), 'PICK_' || cast(wp.transaction_id_unique as varchar))
                when wp.asset_type = 'defense'
                then coalesce(cast(wp.player_name as varchar), 'DEFENSE_' || cast(wp.transaction_id_unique as varchar))
                when wp.asset_type = 'cap_space'
                then 'CAP_' || cast(wp.transaction_id_unique as varchar)
                else 'UNKNOWN_' || cast(wp.transaction_id_unique as varchar)
            end as player_key,
            wp.transaction_type_refined as transaction_type,
            wp.asset_type as asset_type,
            wp.transaction_date as transaction_date,
            extract(year from wp.transaction_date) as transaction_year,
            wp.season as season,
            wp.period_type as period_type,
            wp.week as week,
            wp.sort_sequence as sort_sequence,
            wp.timeframe_string as timeframe_string,
            -- Apply FROM/TO swap for corrections (transactions 2657, 2658)
            case
                when wp.needs_from_to_swap then to_fran.franchise_id else from_fran.franchise_id
            end as from_franchise_id,
            case
                when wp.needs_from_to_swap then to_fran.franchise_name else from_fran.franchise_name
            end as from_franchise_name,
            case
                when wp.needs_from_to_swap then from_fran.franchise_id else to_fran.franchise_id
            end as to_franchise_id,
            case
                when wp.needs_from_to_swap then from_fran.franchise_name else to_fran.franchise_name
            end as to_franchise_name,
            wp.player_id as player_id,
            wp.player_name as player_name,
            wp.position as position,
            wp.pick_id as pick_id,
            wp.pick_season as pick_season,
            wp.pick_round as pick_round,
            wp.pick_overall_number as pick_overall_number,
            wp.pick_id_raw as pick_id_raw,
            wp.pick_original_owner as pick_original_owner,
            wp.round as round,
            wp.pick_number as pick_number,
            try_cast(wp.contract_total as bigint) as contract_total,
            try_cast(wp.contract_years as bigint) as contract_years,
            case when wp.split_array is not null then cast(wp.split_array as json) else null end as contract_split_json,
            wp.split_array as contract_split_array,
            case
                when try_cast(wp.contract_years as bigint) is not null and wp.split_array is not null
                then len(wp.split_array) != try_cast(wp.contract_years as bigint)
                else false
            end as has_contract_length_mismatch,
            case
                when try_cast(wp.contract_total as bigint) is not null and wp.split_array is not null
                then list_sum(wp.split_array) != try_cast(wp.contract_total as bigint)
                else false
            end as has_contract_sum_mismatch,
            case
                when
                    wp.transaction_type_refined = 'contract_extension'
                    and try_cast(wp.contract_years as bigint) is not null
                    and wp.split_array is not null
                    and len(wp.split_array) > try_cast(wp.contract_years as bigint)
                then 'Extension shows full remaining schedule (expected per league accounting)'
                when
                    try_cast(wp.contract_total as bigint) is not null
                    and wp.split_array is not null
                    and abs(list_sum(wp.split_array) - try_cast(wp.contract_total as bigint)) > 5
                then 'Large sum mismatch (>$5) - review with commissioner'
                when
                    try_cast(wp.contract_total as bigint) is not null
                    and wp.split_array is not null
                    and list_sum(wp.split_array) != try_cast(wp.contract_total as bigint)
                then 'Minor rounding variance (±$1-2)'
                else null
            end as validation_notes,
            case
                when wp.rfa_matched_raw = 'yes'
                then true
                when wp.rfa_matched_raw = '-' or wp.rfa_matched_raw is null
                then false
                else null
            end as rfa_matched,
            try_cast(nullif(wp.faad_comp_raw, '-') as integer) as faad_compensation,
            case
                when wp.faad_comp_raw != '-' and try_cast(wp.faad_comp_raw as integer) is null
                then wp.faad_comp_raw
                else null
            end as faad_compensation_text,
            wp.contract_raw as contract_raw,
            wp.split_raw as split_raw,
            wp.transaction_type_raw as transaction_type_raw,
            wp.from_owner_name as from_owner_name,
            wp.to_owner_name as to_owner_name,
            wp.faad_award_sequence as faad_award_sequence
        from with_player_id wp
        left join
            {{ ref("dim_franchise") }} from_fran
            on wp.from_owner_name = from_fran.owner_name
            and case when wp.period_type = 'offseason' then wp.season + 1 else wp.season end
            between from_fran.season_start and from_fran.season_end
        left join
            {{ ref("dim_franchise") }} to_fran
            on wp.to_owner_name = to_fran.owner_name
            and case when wp.period_type = 'offseason' then wp.season + 1 else wp.season end
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
