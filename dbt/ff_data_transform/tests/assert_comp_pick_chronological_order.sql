-- Compensatory picks within a round must be in chronological order by FAAD transaction_id
-- Verifies that slot_number (P13, P14, P15...) matches FAAD award order
select
    pick_id,
    season,
    round,
    slot_number,
    faad_transaction_id,
    lag(faad_transaction_id) over (partition by season, round order by slot_number) as prev_faad_transaction_id,
    'Comp pick out of chronological order' as issue
from {{ ref('dim_pick') }}
where pick_type = 'comp'
    and faad_transaction_id < lag(faad_transaction_id) over (partition by season, round order by slot_number)
