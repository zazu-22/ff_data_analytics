{{
    config(
        severity = 'error',
        tags = ['critical', 'data_integrity', 'pre_rebuild']
    )
}}

/*
FAAD Award Sequence Immutability Test

Purpose: Ensure FAAD award sequences never change after ingestion.

Why This Matters:
- Comp pick ordering is determined by FAAD transaction chronology
- If sequences change retroactively, comp picks get reordered
- This breaks historical accuracy and comp pick slot assignments

How It Works:
- Compares current faad_award_sequence to baseline snapshot
- Baseline created at ingestion time: seed_faad_award_sequence_snapshot.csv
- Any mismatch indicates retroactive sequence change (ERROR)

When to Update Baseline:
- After each new FAAD completes (e.g., 2025 offseason)
- Export new sequences and append to snapshot seed
- Never modify historical sequences in the snapshot

Violation Example:
  transaction_id: 2762
  season: 2023
  current_sequence: 2 (was 1)
  expected_sequence: 1
  issue: "FAAD sequence changed retroactively - comp pick order corrupted"
*/

with current_faad_sequence as (
    select
        transaction_id,
        season,
        faad_award_sequence,
        player_name,
        faad_compensation_text
    from {{ ref('stg_sheets__transactions') }}
    where transaction_type = 'faad_ufa_signing'
        and faad_award_sequence is not null
        and season <= {{ var('latest_completed_draft_season') }}
),

expected_sequence as (
    -- Baseline snapshot of known-good sequences
    select
        transaction_id,
        season,
        faad_award_sequence as expected_faad_award_sequence
    from {{ ref('seed_faad_award_sequence_snapshot') }}
)

select
    cur.transaction_id,
    cur.season,
    cur.player_name,
    cur.faad_compensation_text,
    cur.faad_award_sequence as current_sequence,
    exp.expected_faad_award_sequence as expected_sequence,
    abs(cur.faad_award_sequence - exp.expected_faad_award_sequence) as sequence_delta,
    'FAAD sequence changed retroactively - comp pick order corrupted!' as issue
from current_faad_sequence cur
inner join expected_sequence exp
    on cur.transaction_id = exp.transaction_id
where cur.faad_award_sequence != exp.expected_faad_award_sequence
