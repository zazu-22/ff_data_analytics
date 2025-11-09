{{ config(
  materialized = "table",
  tags = ["core", "dimension"],
  unique_key = 'pick_id'
) }}
/*
 Complete draft pick dimension including base and compensatory picks.

 Purpose: Unified pick dimension for all draft picks (base, compensatory, and TBD).
 Replaces the previous seed-based dim_pick with a fully generated model.

 Grain: One row per draft pick (pick_id unique)

 Sources:
 - {{ ref('int_pick_base') }} - Base picks P01-P12 (standings-based)
 - {{ ref('int_pick_comp_sequenced') }} - Compensatory picks P13+ (FAAD awards)
 - {{ ref('int_pick_tbd') }} - Future picks with unknown position

 Architecture: Type 1 Slowly Changing Dimension (Kimball)
 - pick_id is immutable natural key
 - TBD picks transition to actual picks when finalized (new row, old row removed)

 Key Design Decisions:
 - Base picks: Generated for all years 2012-2030, all rounds 1-5, slots P01-P12
 - Comp picks: Extracted from FAAD Comp column, sequenced chronologically
 - TBD picks: Parsed from transaction references, placeholders until finalized
 - overall_pick: Recalculated to account for comp picks in prior rounds

 Pick Numbering Rules (per League Constitution Section XI):
 - Base picks P01-P12: Ordered by previous season standings/playoff results
 - P01-P06: Non-playoff teams (worst to best by potential points)
 - P07-P08: Play-in round losers
 - P09-P10: Semi-final losers
 - P11: Runner-up
 - P12: Champion
 - Comp picks P13+: Ordered chronologically by FAAD transaction sequence
 - All comp picks come at END of each round (after P12)
 - Sequenced by RFA signing order during FAAD

 Compensatory Pick Rules (per League Constitution Section XI.M-N):
 - Awarded to team that LOST an RFA in FAAD
 - Round determined by contract AAV:
 - R1: $25+ per year
 - R2: $15-24 per year
 - R3: $10-14 per year
 - System ends after 2026 offseason

 Example Pick Progression:
 - 2024 R1: P01-P12 (base) + P13-P17 (5 comp picks) = 17 total picks
 - Comp pick order: P13 (1st FAAD RFA), P14 (2nd FAAD RFA), etc.
 */
with
    lifecycle_control as (select * from {{ ref("dim_pick_lifecycle_control") }}),
    comp_metadata as (
        select
            pick_id,
            season,
            round,
            overall_pick,
            slot_number,
            pick_type,
            is_compensatory,
            comp_source_player,
            comp_awarded_to_franchise,
            comp_faad_transaction_id,
            comp_round_threshold,
            faad_chronological_seq,
            contract_apy,
            notes
        from {{ ref("int_pick_comp_sequenced") }}
    ),
    actual_picks as (
        select
            ap.pick_id,
            ap.season,
            ap.round,
            ap.overall_pick,
            ap.slot_number,
            ap.pick_type,
            ap.pick_type = 'compensatory' as is_compensatory,
            cmp.comp_source_player,
            cmp.comp_awarded_to_franchise,
            cmp.comp_faad_transaction_id,
            cmp.comp_round_threshold,
            cmp.faad_chronological_seq,
            cmp.contract_apy as rfa_contract_aav,
            cmp.comp_source_player as rfa_player_name,
            cmp.comp_awarded_to_franchise as awarded_to_franchise_id,
            case
                when ap.pick_type = 'compensatory'
                then
                    'Comp pick awarded via FAAD sequence ' || coalesce(cast(cmp.faad_chronological_seq as varchar), '?')
                else 'Actual draft pick'
            end as notes,
            false as is_prospective
        from {{ ref("int_pick_draft_actual_with_fallback") }} ap
        left join comp_metadata cmp on ap.pick_id = cmp.pick_id
        where ap.pick_type != 'compensatory' or cmp.pick_id is not null
    ),
    prospective_base as (
        select
            pick_id,
            season,
            round,
            overall_pick,
            slot_number,
            pick_type,
            is_compensatory,
            comp_source_player,
            comp_awarded_to_franchise,
            comp_faad_transaction_id,
            comp_round_threshold,
            faad_chronological_seq,
            cast(null as double) as rfa_contract_aav,
            comp_source_player as rfa_player_name,
            comp_awarded_to_franchise as awarded_to_franchise_id,
            notes,
            true as is_prospective
        from {{ ref("int_pick_base") }}
        where season > {{ var("latest_completed_draft_season") }}
    ),
    prospective_comp as (
        select
            pick_id,
            season,
            round,
            overall_pick,
            slot_number,
            pick_type,
            is_compensatory,
            comp_source_player,
            comp_awarded_to_franchise,
            comp_faad_transaction_id,
            comp_round_threshold,
            faad_chronological_seq,
            contract_apy as rfa_contract_aav,
            comp_source_player as rfa_player_name,
            comp_awarded_to_franchise as awarded_to_franchise_id,
            notes,
            true as is_prospective
        from comp_metadata
        where season > {{ var("latest_completed_draft_season") }}
    ),
    structured_picks as (
        select *
        from actual_picks
        union all
        select *
        from prospective_base
        union all
        select *
        from prospective_comp
    ),
    tbd_picks as (
        select
            pick_id,
            season,
            round,
            overall_pick,
            slot_number,
            pick_type,
            is_compensatory,
            comp_source_player,
            comp_awarded_to_franchise,
            comp_faad_transaction_id,
            comp_round_threshold,
            faad_chronological_seq,
            null as rfa_contract_aav,
            null as rfa_player_name,
            null as awarded_to_franchise_id,
            notes,
            true as is_prospective
        from {{ ref("int_pick_tbd") }}
    ),
    final_picks as (
        select *
        from structured_picks
        union all
        select *
        from tbd_picks
    )
select
    fp.pick_id,
    fp.season,
    fp.round,
    fp.overall_pick,
    fp.slot_number,
    fp.pick_type,
    fp.is_compensatory,
    fp.comp_source_player,
    fp.comp_awarded_to_franchise,
    fp.comp_faad_transaction_id,
    fp.comp_round_threshold,
    fp.faad_chronological_seq,
    -- v2: Lifecycle state (ACTUAL for historical, ACTIVE_TBD for prospective,
    -- SUPERSEDED for replaced)
    coalesce(lc.lifecycle_state, case when fp.is_prospective then 'ACTIVE_TBD' else 'ACTUAL' end) as lifecycle_state,
    -- v2: Prospective flag
    fp.is_prospective,
    -- v2: Lifecycle metadata
    lc.superseded_by_pick_id,
    lc.superseded_at,
    fp.rfa_player_name,
    fp.awarded_to_franchise_id,
    fp.rfa_contract_aav,
    fp.notes,
    fp.comp_faad_transaction_id as faad_transaction_id
from final_picks fp
left join lifecycle_control lc on fp.pick_id = lc.pick_id
where  -- v2: Exclude SUPERSEDED TBD picks (soft-deleted)
    coalesce(lc.lifecycle_state, 'ACTUAL') != 'SUPERSEDED'
