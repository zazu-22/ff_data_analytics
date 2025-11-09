{{ config(materialized="table", unique_key='pick_id') }}

/*
Compensatory Pick Reconciliation - FAAD Awards vs Dimensional Picks

Purpose: Compare FAAD comp pick awards (source of truth) against comp picks
in dim_pick to identify discrepancies and data quality issues.

This is the KEY model for exposing the 2024 R2 issue and other discrepancies.

Grain: One row per compensatory pick (from either FAAD or dim_pick)

Dependencies:
- {{ ref('int_pick_comp_registry') }} - FAAD comp awards (authoritative)
- {{ ref('int_pick_comp_sequenced') }} - Comp picks sequenced for dim_pick
- {{ ref('dim_pick') }} - Final dimensional picks

Reconciliation States:
- MATCHED: FAAD award exists in dim_pick with matching sequence
- SEQUENCE_MISMATCH: Pick exists in both but different chronological order
- FAAD_AWARD_NOT_IN_DIM_PICK: FAAD awarded but missing from dim_pick
- DIM_PICK_WITHOUT_FAAD_AWARD: Comp pick in dim_pick but no FAAD record

Key Insight:
This will expose the 2024 R2 discrepancy:
- FAAD column shows 1 R2 comp pick
- Actual should have 2 R2 comp picks
- Reconciliation status: FAAD_AWARD_NOT_IN_DIM_PICK or data entry error
*/
with
    faad_comp_awards as (
        -- Authoritative source: FAAD Comp column from transactions
        select
            comp_faad_transaction_id,
            comp_season,
            comp_round,
            faad_award_sequence,
            comp_source_player,
            comp_awarded_to_franchise_id,
            comp_round_threshold,
            contract_apy,
            is_aav_round_valid,
            'FAAD_COMP_COLUMN' as source
        from {{ ref("int_pick_comp_registry") }}
        where comp_season <= {{ var("latest_completed_draft_season") }}
    ),

    dim_comp_picks as (
        -- Comp picks as they appear in dim_pick
        select
            pick_id,
            season,
            round,
            slot_number,
            faad_chronological_seq,
            comp_source_player,
            comp_awarded_to_franchise,
            comp_faad_transaction_id,
            'DIM_PICK' as source
        from {{ ref("dim_pick") }}
        where pick_type = 'compensatory' and season <= {{ var("latest_completed_draft_season") }}
    ),

    -- Full outer join to find all comp picks from both sources
    reconciliation as (
        select
            coalesce(faad.comp_season, dim.season) as season,
            coalesce(faad.comp_round, dim.round) as round,

            -- FAAD source fields
            faad.comp_faad_transaction_id as faad_transaction_id,
            faad.faad_award_sequence,
            faad.comp_source_player as faad_player,
            faad.comp_awarded_to_franchise_id as faad_franchise,
            faad.contract_apy as faad_apy,
            faad.comp_round_threshold,
            faad.is_aav_round_valid,

            -- dim_pick fields
            dim.pick_id as dim_pick_id,
            dim.slot_number as dim_slot,
            dim.faad_chronological_seq as dim_sequence,
            dim.comp_source_player as dim_player,
            dim.comp_awarded_to_franchise as dim_franchise,

            -- Reconciliation flags
            faad.comp_faad_transaction_id is not null as in_faad,
            dim.pick_id is not null as in_dim_pick,
            faad.faad_award_sequence = dim.faad_chronological_seq as sequence_matches

        from faad_comp_awards faad
        full outer join dim_comp_picks dim on faad.comp_faad_transaction_id = dim.comp_faad_transaction_id
    ),

    reconciliation_status as (
        select
            *,

            -- Determine reconciliation status
            case
                when in_faad and in_dim_pick and sequence_matches
                then 'MATCHED'
                when in_faad and in_dim_pick and not sequence_matches
                then 'SEQUENCE_MISMATCH'
                when in_faad and not in_dim_pick
                then 'FAAD_AWARD_NOT_IN_DIM_PICK'
                when not in_faad and in_dim_pick
                then 'DIM_PICK_WITHOUT_FAAD_AWARD'
                else 'UNKNOWN'
            end as reconciliation_status,

            -- Diagnostic message
            case
                when in_faad and in_dim_pick and sequence_matches
                then 'OK: FAAD award matches dim_pick'
                when in_faad and in_dim_pick and not sequence_matches
                then
                    'WARNING: Sequence mismatch - FAAD seq '
                    || faad_award_sequence::varchar
                    || ' vs dim_pick seq '
                    || dim_sequence::varchar
                when in_faad and not in_dim_pick
                then
                    'ERROR: FAAD awarded comp pick but missing from dim_pick - potential data entry error or missing transaction'
                when not in_faad and in_dim_pick
                then 'ERROR: Comp pick in dim_pick but no FAAD award record - check transaction history'
                else 'UNKNOWN STATUS'
            end as diagnostic_message,

            -- Severity for filtering
            case
                when in_faad and in_dim_pick and sequence_matches
                then 'INFO'
                when in_faad and in_dim_pick and not sequence_matches
                then 'WARNING'
                when in_faad and not in_dim_pick
                then 'ERROR'
                when not in_faad and in_dim_pick
                then 'ERROR'
                else 'UNKNOWN'
            end as severity

        from reconciliation
    )

select
    season,
    round,

    -- Reconciliation
    reconciliation_status,
    severity,
    diagnostic_message,

    -- FAAD source
    faad_transaction_id,
    faad_award_sequence,
    faad_player,
    faad_franchise,
    faad_apy,
    comp_round_threshold,
    is_aav_round_valid,

    -- dim_pick
    dim_pick_id,
    dim_slot,
    dim_sequence,
    dim_player,
    dim_franchise,

    -- Flags
    in_faad,
    in_dim_pick,
    sequence_matches,

    -- Audit
    current_timestamp as reconciled_at

from reconciliation_status
order by season, round, coalesce(faad_award_sequence, dim_sequence)
