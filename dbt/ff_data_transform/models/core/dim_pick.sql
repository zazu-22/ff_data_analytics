{{ config(materialized="table", tags=["core", "dimension"]) }}

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
    lifecycle_control as (
        -- v2: Lifecycle tracking for TBD → actual pick transitions
        select * from {{ ref("dim_pick_lifecycle_control") }}
    ),

    base_picks as (select * from {{ ref("int_pick_base") }}),

    comp_picks as (select * from {{ ref("int_pick_comp_sequenced") }}),

    tbd_picks as (select * from {{ ref("int_pick_tbd") }}),

    all_picks_unioned as (
        -- Base picks (P01-P12)
        select *
        from base_picks

        union all

        -- Compensatory picks (P13+)
        select *
        from comp_picks

        union all

        -- TBD picks (future picks with unknown position)
        select *
        from tbd_picks
    ),

    -- Recalculate overall_pick to account for comp picks in prior rounds
    overall_pick_final as (
        select
            pick_id,
            season,
            round,
            slot_number,
            pick_type,
            is_compensatory,
            comp_source_player,
            comp_awarded_to_franchise,
            comp_faad_transaction_id,
            comp_round_threshold,
            faad_chronological_seq,
            notes,

            -- Overall pick number accounting for all picks (base + comp) in proper
            -- sequence
            row_number() over (
                partition by season order by round, slot_number
            ) as overall_pick_recalculated

        from all_picks_unioned
        where pick_type in ('base', 'compensatory')  -- Exclude TBD from numbering
    ),

    final_with_overall as (
        -- Picks with recalculated overall_pick
        select
            pick_id,
            season,
            round,
            overall_pick_recalculated as overall_pick,
            slot_number,
            pick_type,
            is_compensatory,
            comp_source_player,
            comp_awarded_to_franchise,
            comp_faad_transaction_id,
            comp_round_threshold,
            faad_chronological_seq,
            notes
        from overall_pick_final

        union all

        -- TBD picks retain placeholder overall_pick (99)
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
            notes
        from all_picks_unioned
        where pick_type = 'tbd'
    )

select
    p.pick_id,
    p.season,
    p.round,
    p.overall_pick,
    p.slot_number,
    p.pick_type,
    p.is_compensatory,
    p.comp_source_player,
    p.comp_awarded_to_franchise,
    p.comp_faad_transaction_id,
    p.comp_round_threshold,
    p.faad_chronological_seq,

    -- v2: Lifecycle state (ACTUAL for historical, ACTIVE_TBD for prospective,
    -- SUPERSEDED for replaced)
    coalesce(
        lc.lifecycle_state,
        case when p.pick_type = 'tbd' then 'ACTIVE_TBD' else 'ACTUAL' end
    ) as lifecycle_state,

    -- v2: Prospective flag
    p.season > {{ var("latest_completed_draft_season") }} as is_prospective,

    -- v2: Lifecycle metadata
    lc.superseded_by_pick_id,
    lc.superseded_at,

    p.notes
from final_with_overall p
left join lifecycle_control lc on p.pick_id = lc.pick_id
where
    -- v2: Exclude SUPERSEDED TBD picks (soft-deleted)
    coalesce(lc.lifecycle_state, 'ACTUAL') != 'SUPERSEDED'
