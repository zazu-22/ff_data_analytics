{{
    config(
        materialized="table",
        indexes=[
            {"columns": ["player_id"]},
            {"columns": ["franchise_id"]},
            {"columns": ["contract_start_season", "contract_end_season"]},
            {"columns": ["is_current"]},
        ],
    )
}}

/*
Player contract history dimension - clean contract state over time.

Grain: One row per player per contract period per franchise
Source: fact_league_transactions (contract-creating events)
Architecture: Type 2 SCD dimension

This dimension derives clean contract state from the transaction event log,
enabling dead cap calculations, roster timeline reconstruction, and salary
cap analysis.

Key Design Decisions:
- Type 2 SCD with effective_date/expiration_date for contract validity
- Contract lifecycle: signed → [extended/restructured] → terminated
- Dead cap calculated using dim_cut_liability_schedule
- Rookie contracts identified and linked to dim_rookie_contract_scale
- Annual amounts calculated for cap roll-ups

Contract Lifecycle Events:
- Created by: rookie_draft_selection, faad, fasa
- Modified by: extension, restructure
- Transferred by: trade (to new franchise, contract continues)
- Terminated by: cut, trade away, expiration

Grain Example Rows:
player_id=12345, franchise_id=F001, contract_period=1 → Rookie contract 2020-2024
player_id=12345, franchise_id=F005, contract_period=2 → Trade-acquired 2024-2025
player_id=12345, franchise_id=F001, contract_period=3 → Re-signed FAAD 2025-2027

Type 2 SCD Fields:
- effective_date: When this contract state became active
- expiration_date: When it ended (9999-12-31 if still active)
- is_current: True if contract is currently active
*/
with
    all_contract_events as (
        -- Extract all contract-related events
        select
            transaction_id,
            transaction_id_unique,
            transaction_type,
            transaction_date,
            transaction_date_corrected,  -- Use corrected date for chronological ordering
            season as transaction_season,
            period_type,

            -- Asset identification
            player_id,
            player_name,
            position,

            -- Franchise ownership
            to_franchise_id as franchise_id,
            to_franchise_name as franchise_name,

            -- Contract terms
            contract_total,
            contract_years,
            contract_split_json,
            contract_split_array,

            -- Contract classification
            case
                when transaction_type = 'rookie_draft_selection'
                then 'rookie'
                when transaction_type in ('faad_ufa_signing', 'faad_rfa_matched')
                then 'faad'
                when transaction_type in ('fasa_signing', 'offseason_ufa_signing')
                then 'fasa'
                when transaction_type = 'trade'
                then 'trade_acquired'
                when transaction_type = 'contract_extension'
                then 'extension'
                when transaction_type = 'franchise_tag'
                then 'franchise_tag'
                when transaction_type = 'waiver_claim'
                then 'waiver_claim'
                else 'other'
            end as contract_type,

            -- Rookie contract flag
            coalesce(
                transaction_type = 'rookie_draft_selection', false
            ) as is_rookie_contract,

            -- Special transaction measures
            rfa_matched,
            faad_compensation,

            -- Check if there's an extension on the same date for this player
            -- AND there's also a base contract on the same date (otherwise it's
            -- standalone)
            case
                when
                    max(
                        case
                            when transaction_type = 'contract_extension' then 1 else 0
                        end
                    ) over (partition by player_id, transaction_date)
                    = 1
                    and max(
                        case
                            when transaction_type != 'contract_extension' then 1 else 0
                        end
                    ) over (partition by player_id, transaction_date)
                    = 1
                then
                    max(
                        case
                            when transaction_type = 'contract_extension'
                            then transaction_id
                        end
                    ) over (partition by player_id, transaction_date)
            end as extension_id_on_same_date

        from {{ ref("fact_league_transactions") }}
        where
            asset_type = 'player'
            and player_id is not null
            and player_id != -1  -- Exclude unmapped players
            and to_franchise_id is not null  -- Must have destination franchise (excludes waiver wire)
            and transaction_type in (
                'rookie_draft_selection',
                'faad_ufa_signing',
                'faad_rfa_matched',
                'fasa_signing',
                'offseason_ufa_signing',
                'trade',
                'contract_extension',
                'franchise_tag',
                'waiver_claim'
            )
            and contract_total is not null  -- Must have contract terms
    ),

    enriched_contract_events as (
        -- Enrich contract events, handling incomplete extension contract_split_json
        -- Some extensions (especially 2024+ rookies) only record the 4th year option
        -- amount
        -- We need to merge remaining base years with the extension year
        select
            ace.*,

            -- For extensions with single-year splits, find the preceding rookie
            -- contract
            case
                when
                    ace.transaction_type = 'contract_extension'
                    and len(
                        cast(json_extract(ace.contract_split_json, '$') as integer[])
                    )
                    = 1
                    and ace.contract_total in (24, 20, 16, 12, 8, 4)  -- 4th year option rates
                then
                    (
                        select prev.contract_split_json
                        from all_contract_events prev
                        where
                            prev.player_id = ace.player_id
                            and prev.transaction_date_corrected
                            < ace.transaction_date_corrected
                            and prev.contract_type = 'rookie'
                            and prev.contract_years = 3
                        order by prev.transaction_date_corrected desc
                        limit 1
                    )
            end as preceding_rookie_split_json,

            -- Calculate years elapsed since rookie contract start
            -- Use contract start seasons (accounting for offseason logic) not
            -- transaction seasons
            case
                when
                    ace.transaction_type = 'contract_extension'
                    and len(
                        cast(json_extract(ace.contract_split_json, '$') as integer[])
                    )
                    = 1
                    and ace.contract_total in (24, 20, 16, 12, 8, 4)
                then
                    (
                        select
                            -- Extension start season - rookie start season = years
                            -- elapsed
                            (
                                case
                                    when ace.period_type = 'offseason'
                                    then ace.transaction_season + 1
                                    else ace.transaction_season
                                end
                            ) - (
                                case
                                    when prev.period_type = 'offseason'
                                    then prev.transaction_season + 1
                                    else prev.transaction_season
                                end
                            )
                        from all_contract_events prev
                        where
                            prev.player_id = ace.player_id
                            and prev.transaction_date_corrected
                            < ace.transaction_date_corrected
                            and prev.contract_type = 'rookie'
                            and prev.contract_years = 3
                        order by prev.transaction_date_corrected desc
                        limit 1
                    )
            end as years_elapsed_since_rookie_start

        from all_contract_events ace
    ),

    enriched_contract_events_with_merged_splits as (
        -- Merge remaining base years with extension year for incomplete extensions
        select
            ece.*,

            -- Build full remaining schedule for incomplete extensions
            case
                when
                    ece.preceding_rookie_split_json is not null
                    and ece.years_elapsed_since_rookie_start is not null
                then
                    -- Slice remaining base years and append extension year
                    list_concat(
                        cast(
                            json_extract(
                                ece.preceding_rookie_split_json, '$'
                            ) as integer[]
                        )[ece.years_elapsed_since_rookie_start + 1:],
                        cast(json_extract(ece.contract_split_json, '$') as integer[])
                    )
                else cast(json_extract(ece.contract_split_json, '$') as integer[])
            end as final_contract_split_array,

            -- Update contract_split_json with merged array
            case
                when
                    ece.preceding_rookie_split_json is not null
                    and ece.years_elapsed_since_rookie_start is not null
                then
                    to_json(
                        list_concat(
                            cast(
                                json_extract(
                                    ece.preceding_rookie_split_json, '$'
                                ) as integer[]
                            )[ece.years_elapsed_since_rookie_start + 1:],
                            cast(
                                json_extract(ece.contract_split_json, '$') as integer[]
                            )
                        )
                    )
                else ece.contract_split_json
            end as merged_contract_split_json

        from enriched_contract_events ece
    ),

    final_enriched_events as (
        -- Replace contract_split_json with merged version
        -- Include all columns but override contract_split_json and
        -- contract_split_array with merged versions
        select
            ecm.* exclude (
                contract_split_json,
                contract_split_array,
                merged_contract_split_json,
                final_contract_split_array,
                preceding_rookie_split_json,
                years_elapsed_since_rookie_start
            ),
            ecm.merged_contract_split_json as contract_split_json,  -- Use merged version
            ecm.final_contract_split_array as contract_split_array  -- Use merged version
        from enriched_contract_events_with_merged_splits ecm
    ),

    same_date_extensions as (
        -- Combine base contracts with extensions that occur on the same date
        -- Pattern A: Extension split contains FULL remaining schedule from extension
        -- date forward
        -- Pattern B: Extension split contains only ADDED years appended to base
        select
            base.transaction_id,
            base.transaction_id_unique,
            base.transaction_type,
            base.transaction_date,
            base.transaction_date_corrected,  -- Pass through corrected date
            -- For Pattern A (full remaining), use extension season/period since split
            -- starts from extension date
            -- For Pattern B (added only), use base season/period since we're
            -- concatenating
            case
                when
                    ext.contract_years
                    < len(cast(json_extract(ext.contract_split_json, '$') as integer[]))
                then ext.transaction_season
                else base.transaction_season
            end as transaction_season,
            case
                when
                    ext.contract_years
                    < len(cast(json_extract(ext.contract_split_json, '$') as integer[]))
                then ext.period_type
                else base.period_type
            end as period_type,
            base.player_id,
            base.player_name,
            base.position,
            base.franchise_id,
            base.franchise_name,

            -- Extension handling: Two patterns exist in the data
            -- Pattern A: Extension split contains FULL remaining schedule
            -- (contract_years < split_length)
            -- Example: base [6,6,6] → ext [6,6,24] with contract_years=1
            -- Pattern B: Extension split contains only ADDED years (contract_years ==
            -- split_length)
            -- Example: base [6,6,6] → ext [24] with contract_years=1
            -- Detect pattern by comparing contract_years to split array length
            case
                when ext.contract_split_json is null
                then base.contract_total
                when ext.contract_years < len(ext_splits.ext_split)
                -- Pattern A: Extension has full remaining schedule, use extension total
                then list_sum(ext_splits.ext_split)
                else
                    -- Pattern B: Extension is added years only, sum base + extension
                    base.contract_total + ext.contract_total
            end as contract_total,
            case
                when ext.contract_split_json is null
                then base.contract_years
                when ext.contract_years < len(ext_splits.ext_split)
                -- Pattern A: Extension has full remaining schedule, count from
                -- extension
                then len(ext_splits.ext_split)
                else
                    -- Pattern B: Extension is added years only, sum base + extension
                    -- years
                    base.contract_years + ext.contract_years
            end as contract_years,
            case
                when ext.contract_split_json is null
                then base.contract_split_json
                when ext.contract_years < len(ext_splits.ext_split)
                -- Pattern A: Extension has full remaining schedule, use as-is
                then ext.contract_split_json
                else
                    -- Pattern B: Extension is added years only, concatenate
                    to_json(list_concat(base_splits.base_split, ext_splits.ext_split))
            end as contract_split_json,
            case
                when ext.contract_split_array is null
                then base.contract_split_array
                when ext.contract_years < len(ext_splits.ext_split)
                -- Pattern A: Use extension array
                then ext.contract_split_array
                else
                    -- Pattern B: Concatenate arrays (fall back to parsed splits if
                    -- JSON-only)
                    coalesce(
                        list_concat(
                            base.contract_split_array, ext.contract_split_array
                        ),
                        list_concat(base_splits.base_split, ext_splits.ext_split)
                    )
            end as contract_split_array,

            base.contract_type,
            base.is_rookie_contract,
            base.rfa_matched,
            base.faad_compensation

        from final_enriched_events base
        inner join
            final_enriched_events ext
            on base.player_id = ext.player_id
            and base.transaction_date = ext.transaction_date
            and base.transaction_type != 'contract_extension'
            and ext.transaction_type = 'contract_extension'
        cross join
            lateral(
                select
                    cast(
                        json_extract(base.contract_split_json, '$') as integer[]
                    ) as base_split
            ) base_splits
        cross join
            lateral(
                select
                    cast(
                        json_extract(ext.contract_split_json, '$') as integer[]
                    ) as ext_split
            ) ext_splits
    ),

    standalone_contracts as (
        -- Contracts without same-date extensions
        select
            transaction_id,
            transaction_id_unique,
            transaction_type,
            transaction_date,
            transaction_date_corrected,  -- Pass through corrected date
            transaction_season,
            period_type,
            player_id,
            player_name,
            position,
            franchise_id,
            franchise_name,
            contract_total,
            contract_years,
            contract_split_json,
            contract_split_array,
            contract_type,
            is_rookie_contract,
            rfa_matched,
            faad_compensation

        from final_enriched_events
        where extension_id_on_same_date is null
    ),

    contract_creating_events as (
        -- Union of combined same-date extensions and standalone contracts
        select *
        from same_date_extensions
        union all
        select *
        from standalone_contracts
    ),

    contract_terminating_events as (
        -- Extract CUT, TRADE-AWAY, AMNESTY CUT, and WAIVER RELEASE events that
        -- terminate contracts
        select
            transaction_id,
            transaction_id_unique,
            transaction_type,
            transaction_date,
            player_id,
            from_franchise_id as franchise_id
        from {{ ref("fact_league_transactions") }}
        where
            asset_type = 'player'
            and player_id is not null
            and player_id != -1
            and (
                -- Cut, amnesty cut, and trade-away terminate contracts
                transaction_type in ('cut', 'amnesty_cut', 'trade')
                -- Waiver releases also terminate contracts (waiver_claim with NULL
                -- destination)
                or (transaction_type = 'waiver_claim' and to_franchise_id is null)
            )
            and from_franchise_id is not null
    ),

    contract_periods as (
        -- Calculate contract validity periods, considering both next contract and CUT
        -- events
        select
            ce.*,

            -- Contract period identification
            -- Order by transaction_id as well for deterministic ordering of same-date
            -- contracts
            -- Use transaction_date_corrected for chronologically correct sequencing
            row_number() over (
                partition by ce.player_id
                order by ce.transaction_date_corrected, ce.transaction_id
            ) as contract_period,

            -- Validity dates (Type 2 SCD)
            ce.transaction_date as effective_date,

            -- Find next contract date for this player
            -- Order by transaction_id as well to handle same-date contracts
            -- deterministically
            -- Use transaction_date_corrected for chronologically correct sequencing
            lead(ce.transaction_date) over (
                partition by ce.player_id
                order by ce.transaction_date_corrected, ce.transaction_id
            ) as next_contract_date,

            -- Get next contract's start season to check if it starts AFTER current
            -- contract ends
            lead(
                case
                    when ce.period_type = 'offseason'
                    then ce.transaction_season + 1
                    else ce.transaction_season
                end
            ) over (
                partition by ce.player_id
                order by ce.transaction_date_corrected, ce.transaction_id
            ) as next_contract_start_season,

            -- Find termination date for this player+franchise (CUT or TRADE-AWAY)
            -- Get the minimum termination date that is AFTER contract start
            -- (chronologically)
            -- For same-date transactions, use transaction_id for proper sequencing
            (
                select min(term.transaction_date)
                from contract_terminating_events term
                where
                    term.player_id = ce.player_id
                    and term.franchise_id = ce.franchise_id
                    and (
                        term.transaction_date > ce.transaction_date
                        or (
                            term.transaction_date = ce.transaction_date
                            and term.transaction_id > ce.transaction_id
                        )
                    )
            ) as termination_date,

            -- Contract timeline
            -- Use split array length if available (handles extensions with full
            -- remaining schedule)
            -- Otherwise fall back to contract_years
            -- For offseason transactions, contract starts in the NEXT season
            -- The contract_split_json already contains the correct year-by-year
            -- schedule for extensions
            case
                when ce.period_type = 'offseason'
                then ce.transaction_season + 1
                else ce.transaction_season
            end as contract_start_season,
            (
                case
                    when ce.period_type = 'offseason'
                    then ce.transaction_season + 1
                    else ce.transaction_season
                end
            ) + (
                coalesce(
                    len(cast(json_extract(ce.contract_split_json, '$') as integer[])),
                    ce.contract_years
                )
                - 1
            ) as contract_end_season,

            -- Calculated measures (use actual years from split if available)
            case
                when
                    coalesce(
                        len(
                            cast(json_extract(ce.contract_split_json, '$') as integer[])
                        ),
                        ce.contract_years
                    )
                    > 0
                then
                    round(
                        cast(ce.contract_total as numeric) / cast(
                            coalesce(
                                len(
                                    cast(
                                        json_extract(
                                            ce.contract_split_json, '$'
                                        ) as integer[]
                                    )
                                ),
                                ce.contract_years
                            ) as numeric
                        ),
                        2
                    )
            end as annual_amount

        from contract_creating_events ce
    ),

    contract_periods_with_expiry as (
        -- Calculate expiration date and is_current based on terminations and next
        -- contracts
        select
            cp.*,

            -- Expiration date: handle same-date contracts, terminations, and natural
            -- end dates
            -- Fix for Bug #2: Same-date sign-and-trade contracts were creating
            -- inverted dates
            -- (e.g., effective_date = 2024-01-01, next_contract = 2024-01-01,
            -- old logic: expiration = 2024-01-01 - 1 day = 2023-12-31, BEFORE
            -- effective!)
            -- Fix for 4th year options: Don't terminate rookie contract when option
            -- starts in future season
            case
                -- Same-date next contract: expire at END of effective_date (not before)
                when cp.next_contract_date = cp.effective_date
                then cp.effective_date
                -- Same-date termination: expire at END of effective_date (not before)
                when cp.termination_date = cp.effective_date
                then cp.effective_date
                -- Termination exists: use earlier of termination or natural end
                when cp.termination_date is not null
                then
                    least(
                        cp.termination_date - interval '1 day',
                        make_date(cp.contract_end_season, 12, 31)
                    )
                -- Next contract exists BUT starts in a future season (e.g., 4th year
                -- option):
                -- Let current contract expire at natural end, don't terminate early
                when
                    cp.next_contract_date is not null
                    and cp.next_contract_start_season is not null
                    and cp.next_contract_start_season > cp.contract_end_season
                then make_date(cp.contract_end_season, 12, 31)
                -- Next contract exists and starts in same/earlier season: use earlier
                -- of next_contract or natural end
                when cp.next_contract_date is not null
                then
                    least(
                        cp.next_contract_date - interval '1 day',
                        make_date(cp.contract_end_season, 12, 31)
                    )
                -- No next contract or termination: expire at natural end date
                else make_date(cp.contract_end_season, 12, 31)
            end as expiration_date,

            -- Is this the current contract?
            -- Current if: no next contract AND no termination, OR termination/next
            -- contract is in the future
            -- Special case: if next contract starts in a future season (4th year
            -- option), current contract remains active
            case
                when cp.next_contract_date is null and cp.termination_date is null
                then true
                when
                    cp.termination_date is not null
                    and cp.termination_date <= current_date
                then false
                -- If next contract starts in future season, current contract is still
                -- active (check end season)
                when
                    cp.next_contract_date is not null
                    and cp.next_contract_start_season is not null
                    and cp.next_contract_start_season > cp.contract_end_season
                then cp.contract_end_season >= year(current_date)  -- Active if end season hasn't passed
                -- Otherwise, not current if next contract already started
                when
                    cp.next_contract_date is not null
                    and cp.next_contract_date <= current_date
                then false
                else true
            end as is_current

        from contract_periods cp
    ),

    with_dead_cap as (
        -- Calculate potential dead cap if cut today
        -- Uses dim_cut_liability_schedule for percentages by contract year
        select
            cp.*,

            -- Dead cap calculation (simplified - assumes even split if no split_array)
            -- In practice, use contract_split_array for accurate year-by-year amounts
            case
                when cp.is_current
                then
                    (
                        -- Sum remaining years' dead cap liability
                        select sum(cast((cp.annual_amount * sch.dead_cap_pct) as int))
                        from {{ ref("dim_cut_liability_schedule") }} sch
                        where sch.contract_year <= cp.contract_years
                    )
                else 0
            end as dead_cap_if_cut_today

        from contract_periods_with_expiry cp
    )

select
    -- Surrogate key
    {{
        dbt_utils.generate_surrogate_key(
            ["player_id", "franchise_id", "contract_period"]
        )
    }} as contract_history_key,

    -- Natural key
    player_id,
    franchise_id,
    contract_period,

    -- Player attributes (denormalized for convenience)
    player_name,
    position,
    franchise_name,

    -- Contract classification
    contract_type,
    is_rookie_contract,

    -- Contract terms
    contract_total,
    contract_years,
    annual_amount,
    contract_split_json,

    -- Contract timeline
    contract_start_season,
    contract_end_season,
    effective_date,
    expiration_date,
    is_current,

    -- Dead cap measures
    dead_cap_if_cut_today,

    -- Special transaction measures
    rfa_matched,
    faad_compensation,

    -- Audit trail (FK back to transaction event)
    transaction_id,
    transaction_id_unique,

    -- Metadata
    current_timestamp as loaded_at

from with_dead_cap
