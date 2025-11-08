{{ config(materialized="ephemeral") }}

/*
Compensatory pick registry - Extracts comp pick awards from FAAD Comp column.

Purpose: Parse transaction FAAD Comp column to identify all compensatory picks awarded
for RFA (Restricted Free Agent) signings during FAAD (Free Agent Auction Draft).

Grain: One row per compensatory pick award

Dependencies:
- {{ ref('stg_sheets__transactions') }} - Source of FAAD Comp column
- {{ ref('dim_franchise') }} - For franchise name → ID mapping

Key Logic:
- FAAD Comp format (two variants):
  - Historical: "YYYY Rnd" (e.g., "2024 1st", "2023 3rd")
  - Prospective: "Rnd to Owner" (e.g., "1st to Joe", "2nd to Piper")
- Comp pick round determined by contract AAV:
  - R1: $25+ per year
  - R2: $15-24 per year
  - R3: $10-14 per year
- Comp picks awarded to team that LOST the RFA (to_franchise_id)

Data Quality:
- Validates contract AAV matches comp round assignment
- Flags mismatches for investigation (e.g., JP Jessie Bates R2→R3 issue)
*/
with
    faad_transactions as (
        select
            transaction_id,
            transaction_date,
            from_franchise_id,  -- Team that signed the RFA
            to_franchise_id,  -- Team that lost the RFA (receives comp)
            player_id,
            player_name as comp_source_player,
            faad_compensation_text,
            faad_award_sequence,
            contract_total,
            contract_years,
            -- Calculate average annual value
            case
                when contract_years > 0 then contract_total / contract_years else 0
            end as contract_apy

        from {{ ref("stg_sheets__transactions") }}
        where
            transaction_type = 'faad_ufa_signing'
            and faad_compensation_text is not null
            and faad_compensation_text != '-'
    ),

    parsed_comps as (
        select
            transaction_id as comp_faad_transaction_id,
            transaction_date,
            comp_source_player,
            player_id as comp_source_player_id,
            from_franchise_id as signing_franchise_id,
            to_franchise_id as comp_awarded_to_franchise_id,
            faad_compensation_text,
            faad_award_sequence,
            contract_apy,

            -- Parse season from FAAD Comp column
            case
                -- Historical format: "YYYY Rnd" (e.g., "2024 1st")
                when regexp_matches(faad_compensation_text, '^\d{4} \d')
                then
                    cast(
                        regexp_extract(faad_compensation_text, '^(\d{4})', 1) as integer
                    )

                -- Prospective format: "Rnd to Owner" - draft is next year
                when regexp_matches(faad_compensation_text, '^\d(?:st|nd|rd|th) to')
                then year(transaction_date) + 1

                else null
            end as comp_season,

            -- Parse round from FAAD Comp column
            case
                when regexp_matches(faad_compensation_text, '1st')
                then 1
                when regexp_matches(faad_compensation_text, '2nd')
                then 2
                when regexp_matches(faad_compensation_text, '3rd')
                then 3
                when regexp_matches(faad_compensation_text, '4th')
                then 4
                when regexp_matches(faad_compensation_text, '5th')
                then 5
                else null
            end as comp_round,

            -- Extract owner name from prospective format "Rnd to Owner"
            case
                when regexp_matches(faad_compensation_text, ' to (.+)$')
                then trim(regexp_extract(faad_compensation_text, ' to (.+)$', 1))
                else null
            end as comp_awarded_to_owner_name,

            -- Determine expected comp round based on contract AAV (per league
            -- constitution)
            case
                when contract_apy >= 25
                then 1
                when contract_apy >= 15
                then 2
                when contract_apy >= 10
                then 3
                else 4  -- Below R3 threshold
            end as comp_round_expected_by_aav,

            -- Comp round threshold description
            case
                when contract_apy >= 25
                then 'R1: $25+/yr'
                when contract_apy >= 15
                then 'R2: $15-24/yr'
                when contract_apy >= 10
                then 'R3: $10-14/yr'
                else 'Below threshold: <$10/yr'
            end as comp_round_threshold

        from faad_transactions
    ),

    -- Get franchise information for comp recipient
    franchise_mapping as (
        select franchise_id, owner_name from {{ ref("dim_franchise") }}
    ),

    validated_comps as (
        select
            pc.*,

            -- Join franchise data
            fm.franchise_id as comp_awarded_to_franchise_id_verified,
            fm.owner_name as comp_awarded_to_owner_verified,

            -- Data quality validation: Does FAAD Comp round match AAV threshold?
            pc.comp_round = pc.comp_round_expected_by_aav as is_aav_round_valid,

            -- AAV validation message
            case
                when pc.comp_round != pc.comp_round_expected_by_aav
                then
                    'MISMATCH: FAAD shows R'
                    || pc.comp_round
                    || ' but AAV $'
                    || round(pc.contract_apy, 1)
                    || '/yr suggests R'
                    || pc.comp_round_expected_by_aav
                else 'Valid'
            end as aav_validation_message

        from parsed_comps pc
        left join
            franchise_mapping fm on pc.comp_awarded_to_franchise_id = fm.franchise_id
        where
            -- Filter to valid parsed records only
            pc.comp_season is not null and pc.comp_round is not null
    )

select
    comp_faad_transaction_id,
    transaction_date,
    comp_season,
    comp_round,
    comp_source_player,
    comp_source_player_id,
    signing_franchise_id,

    -- Use verified franchise_id from franchise mapping, fallback to transaction data
    coalesce(
        comp_awarded_to_franchise_id_verified, comp_awarded_to_franchise_id
    ) as comp_awarded_to_franchise_id,

    comp_awarded_to_owner_name,
    comp_awarded_to_owner_verified,
    contract_apy,
    comp_round_threshold,
    comp_round_expected_by_aav,
    is_aav_round_valid,
    aav_validation_message,
    faad_compensation_text as faad_comp_original

from validated_comps
